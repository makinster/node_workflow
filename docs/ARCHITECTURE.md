# AttackOfTheNodes Architecture

AttackOfTheNodes is a Python workflow engine with a Textual terminal UI. The guiding metaphor is a factory floor with a control room: backend services execute and coordinate node pipelines, while the frontend renders, edits, and observes them in the terminal.

## Big Picture

A workflow is a recipe made of connected nodes. When a run starts, a `Supervisor` walks from the start node through the graph. If a node forks execution, `MasterState` spawns one supervisor per branch. Supervisors share a per-run `MemoryBank`, collect durable outputs through `OutputManager`, and report lifecycle events back to `MasterState` via `EventBus`.

The execution pipeline is:

1. Load workflow structure from disk.
2. Validate reachable nodes and connections.
3. Start root supervisor at the start node.
4. Execute nodes sequentially along a path.
5. Write transient port data to `MemoryBank`.
6. Spawn branch supervisors when a node signals branching.
7. Pause for human input or recovery decisions when needed.
8. Finalize outputs and run state when all supervisors terminate.

## Backend Components

### `persistence.py`

Intentionally dumb flat-file I/O. All paths are anchored to the project root via `Path(__file__).resolve().parent.parent`. No schema interpretation or workflow logic lives here.

Data directories:

- `workflows/` — serialized workflow blueprints, one JSON file per workflow.
- `settings/` — global key/value configuration.
- `run_history/` — summaries of completed or errored runs.
- `run_outputs/` — collected output data from completed runs.
- `run_errors/` — structured error logs per run.

### `ConfigurationManager`

The settings board. Loads settings from `settings/settings.json`, caches them in memory, and serves future reads from cache. `DEFAULT_SETTINGS` acts as both defaults and schema; only known keys can be set.

Key settings:

- `max_branch_depth`: hard ceiling for nested branch spawning.
- `node_timeout_seconds`: per-node execution timeout passed to supervisors.

### `EventBus`

In-process pub/sub dispatcher. Components `subscribe(event_name, callback)` and `publish(event_name, payload)`. All inter-component signals travel through the event bus.

Key events:

- `WORKFLOW_STATE_UPDATE` — run state changed (IDLE / RUNNING / PAUSED / WAITING_FOR_INPUT / FINISHED / ERROR).
- `WORKFLOW_DIRTY` — workflow structure was modified.
- `SUPERVISOR_REGISTER` — a new supervisor started.
- `SUPERVISOR_STATE_UPDATE` — a supervisor changed state.
- `SUPERVISOR_REQUEST_BRANCH` — a node requested a branch spawn.
- `SUPERVISOR_TERMINATING` — a supervisor finished.
- `SUPERVISOR_ERROR` — a supervisor encountered an unrecoverable error.
- `BREAKPOINT_HIT` — execution hit a node with its breakpoint flag set.
- `NODE_TIMING_UPDATE` — a node finished executing; carries elapsed seconds.
- `RECOVERY_OPTIONS_AVAILABLE` — a node errored; waiting for recovery decision.
- `USER_INPUT_NEEDED` — a node is waiting for human input.
- `MEMORY_UPDATE` — memory bank state changed.
- `RUN_HISTORY_UPDATED` — a run was recorded.

### `WorkflowMap`

The live blueprint manager. Caches the active workflow in memory as a dict of node dicts. Exposes:

- Traversal: start-node discovery, next-node lookup, input-source lookup, BFS reachability.
- Node CRUD: add from `NodeFactory` templates, delete, update config and alias.
- Connection management: connect/disconnect ports, tombstone swaps.
- Dirty tracking: mutations set dirty state; saves clear it.
- Persistence: reads/writes JSON through `persistence.py`.

### `NodeFactory`

The parts catalog. Imports node classes, builds a registry of type string → class, and exposes metadata for the UI and validator.

Primary operations:

- `create_node(node_type, node_id, config)` → `Node`
- `create_config_template(node_type)` → `dict`
- `get_node_types_metadata()` → `list[dict]`
- `is_valid_node_type(node_type)` → `bool`

### Node Classes

Each node lives under `backend/nodes/` and extends `Node`. Nodes are intentionally graph-ignorant: they receive pre-resolved inputs, read their config, and signal through context.

Each node defines:

- Class-level metadata: `node_type`, `display_name`, `description`, `category`, `input_ports`, `output_ports`, `default_config`, `config_schema`, `ui_hints`.
- `async execute(context: NodeContext) -> None`.

Execution context:

```python
context = NodeContext(
    node_id,
    branch_id,
    run_id,
    inputs,                          # dict: port → upstream value
    memory_bank,
    signal_done(payload),            # advance; payload may carry data or branches
    signal_error(error),             # trigger recovery flow
    signal_waiting_for_input(prompt) -> Awaitable[str],
    wait_for_nodes(node_ids, timeout) -> Awaitable[None],
)
```

Branching is requested through `signal_done`:

```python
context.signal_done({
    "data": {},
    "branches": [
        {"output_port": "path_a", "initial_data": {"input": value}},
        {"output_port": "path_b", "initial_data": {"input": value}},
    ],
})
```

Current node types:

| Category | Nodes |
|---|---|
| Flow | StartNode, EndNode, BranchNode, ConditionalNode, WaitUntilNode |
| Data | SetVariableNode, GetVariableNode, ConcatNode |
| IO | TextOutputNode, UserTextInputNode, FileReaderNode |
| AI | ChatCompletionNode, ImageGenerationNode, EmbeddingNode |
| Debug | LoggerNode, SleepNode, CounterNode, EchoNode, ProbeNode, ErrorNode, MemorySnapshotNode, RandomBranchNode, DeepBranchNode, NoOpNode, RepeatCounterNode, TombstoneNode, VariableSetterNode, VariableReaderNode |

### `MemoryBank`

The shared whiteboard for one run. Two stores:

- **Persistent store**: named variables shared by all supervisors for the whole run. Read/written by nodes through `context.memory_bank`.
- **Transient store**: point-to-point data passing keyed as `(source_node_id, port_name)`. Written by the supervisor after each node; read by the supervisor when preparing inputs for the next node.

Both stores are cleared on run start and blank between runs. Persistent changes broadcast `MEMORY_UPDATE`.

### `OutputManager`

The collection bin for durable workflow outputs. Accumulates output items in memory keyed by `run_id`, then `finalize_run()` batch-saves them to `run_outputs/` and evicts the in-memory list. `get_outputs_for_run()` lazy-loads from disk for historical views.

### `ErrorHandler`

Central structured error logger. `log_error()` appends an error record to an in-memory cache, persists it to `run_errors/`, and broadcasts `ERROR_LOGGED`. `finalize_run()` evicts the in-memory cache after a run is recorded. `get_errors_for_run()` lazy-loads from disk.

Each error record contains: unique ID, timestamp, category, message, type, traceback, and context (run/node/branch).

### `RunHistory`

Stores summaries of completed or errored runs. Capped at `_MAX_IN_MEMORY = 500` entries in memory; older records remain on disk. `list_runs()` returns the in-memory list newest-first.

Run records contain: run_id, workflow_id, workflow_name, started_at, ended_at, final_state, error_count, output_count, node_timings.

### `Supervisor`

The line worker. Executes one path through the graph and owns branch-local state.

Constructed with run_id, branch_id, depth, start_node_id, WorkflowMap, MemoryBank, EventBus, ErrorHandler, and callbacks for `mark_node_completed` and `wait_for_nodes`.

Run loop:

1. Check stop and pause flags.
2. Check for a breakpoint on the current node; pause if set.
3. Fetch node instance from WorkflowMap.
4. Prepare inputs from transient memory or initial branch data.
5. Execute node and capture result via `perf_counter`-wrapped `node.execute(context)`.
6. Emit `NODE_TIMING_UPDATE` with elapsed seconds.
7. If an error, publish recovery options and await a decision (RETRY / SKIP / TERMINATE_BRANCH / TERMINATE_WORKFLOW).
8. On success, call `mark_node_completed(node_id)`.
9. Write outputs to transient memory; spawn branches if signaled.
10. Advance to next node or terminate.

### `MasterState`

The floor manager. Does not execute nodes; it coordinates supervisors.

Starting a run:

1. Generate `run_id`.
2. Clear `MemoryBank`, `OutputManager`, supervisor tracking, `node_timings`, and `completed_nodes`.
3. Find the workflow start node.
4. Create and task root supervisor.
5. Broadcast `WORKFLOW_STATE_UPDATE(RUNNING)`.

Supervisor event routing handles:

- `SUPERVISOR_REGISTER` — track supervisor instance.
- `SUPERVISOR_TERMINATING` — remove supervisor; check run completion.
- `SUPERVISOR_REQUEST_BRANCH` — enforce `max_branch_depth`; create child supervisor.
- `SUPERVISOR_STATE_UPDATE` — track waiting-for-input state.
- `SUPERVISOR_ERROR` — transition to ERROR state; record run.
- `BREAKPOINT_HIT` — pause all active supervisors.
- `NODE_TIMING_UPDATE` — accumulate elapsed seconds per node into `node_timings`.
- `TERMINATE_WORKFLOW_REQUESTED` — stop all supervisors; record run as ERROR.

WaitUntil coordination:

- `mark_node_completed(node_id)` — adds node to `completed_nodes`, notifies all waiters via an `asyncio.Condition`.
- `wait_until_nodes_completed(target_ids, timeout)` — awaits the condition until all targets are in `completed_nodes`.

Run completion occurs when `_supervisors` and `_supervisor_tasks` are both empty. MasterState then finalizes outputs, records the run, and broadcasts `WORKFLOW_STATE_UPDATE(FINISHED)`.

### `SaveManager`

The archivist. Assembles complete save objects combining WorkflowMap structure, MemoryBank state, and ConfigurationManager settings. Handles load/save/delete/duplicate/export/import of workflows.

### `Validator`

The inspector. Performs a DFS from the start node and checks:

- Node type exists in `NodeFactory`.
- Connection sources and targets exist.
- Tombstone nodes (pending replacements) are flagged as errors.

After traversal, any unvisited node is unreachable and reported as a warning. Return shape:

```python
{"errors": [...], "warnings": [...]}
```

Each error and warning includes `node_id` so the UI can highlight the affected node.

## Frontend Components (Textual TUI)

### `App` (`AttackOfTheNodesApp`)

Root Textual application. Created by `main.py` alongside all backend services. Subscribes to 10 backend events on startup (once, for the session lifetime). Manages the screen stack and routes user commands to backend services.

### `EditorScreen`

The blueprint view. Shows a `NodeList` (left panel) and a details panel (right). Priority-bound keys: `A` add, `I` insert, `E`/`Enter` edit, `X`/`Backspace` delete, `V` validate, `L`/`O` library, `?` help. `Ctrl+S` save, `Ctrl+R` run at app level.

### `ExecutionScreen`

Live run view showing node statuses (running / waiting / done / errored) during workflow execution.

### Modals and Screens

- `NodeSelectorScreen` — pick a node type to add.
- `NodeConfigScreen` — edit alias, config fields, memory bank inputs/outputs, wait targets, and view connections. Uses `CommandInput`/`CommandTextArea` for keyboard-first field editing.
- `ConfirmScreen` — yes/no confirmation dialog.
- `ErrorDetailsScreen` — displays structured errors; doubles as recovery decision dialog.
- `BranchSelectorScreen` — choose which branch path to view in the editor.
- `WorkflowLibraryScreen` — browse, load, duplicate, delete, export, and import workflows.
- `SettingsScreen` — edit configuration key/value settings.
- `UserInputScreen` — prompts for string input during a running workflow.
- `HelpScreen` — key binding reference.

### `CommandInput` / `CommandTextArea`

Mode-switching form widgets. In command mode, `w`/`s` navigate fields, `e`/`Enter` begins editing, `Esc` ends editing. In edit mode, all keys go to the text input. Prevents accidental edits when navigating config forms.

## Implementation Invariants

- Nodes are graph-ignorant: they receive pre-resolved inputs through `NodeContext`.
- `WorkflowMap` owns live workflow shape and dirty state.
- `SaveManager` is the only component that assembles complete save payloads.
- `MemoryBank` is ephemeral per run; `OutputManager` is the durable output record.
- `EventBus` is the only inter-component communication mechanism.
- All data paths anchor to `Path(__file__).resolve().parent.parent` via `persistence.py`.
- Per-run in-memory caches (`OutputManager._outputs_by_run`, `ErrorHandler._errors_by_run`) are evicted after a run is finalized.
- `RunHistory._runs` is capped at 500 entries in memory; disk retains full history.
- `MasterState` and `App` are created once per session; their bus subscriptions register once and remain for the session lifetime.

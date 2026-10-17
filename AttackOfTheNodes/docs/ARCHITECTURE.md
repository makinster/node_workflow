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

Intentionally dumb flat-file I/O. No schema interpretation or workflow logic lives here.

All data paths hang off one data directory, `DATA_DIR`: the project folder by
default, or `$AOTN_DATA_DIR` when set (the CLI's `--data-dir` sets it). It is
read once at import, so it must be set before the backend is imported.
`SECRETS_DIR` (`secrets/`) and `LOGS_DIR` (`logs/`) live there too.

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
- `node_timeout_seconds`: passed to supervisors, but it bounds very little.
  It only applies when a node calls `wait_for_nodes`/`wait_for_merge` with
  `timeout=None`; Wait Until and Merge pass an explicit `0.0` (wait
  indefinitely), and no node execution is wrapped in a timeout. Timeouts stay
  per node (for example Wait Until's own `timeout_seconds`).

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
- Optional `resolve_input_ports(config)` classmethod, the input mirror (Merge
  reads `input_slots` slots; `get_input_ports()` and the validator use it).
- Optional `resolve_output_ports(config)` classmethod when the ports depend on
  config (Branch keeps the first `branch_count` paths). `output_ports` stays the
  type's full list; `NodeFactory.node_output_ports(node_data)` is the one way to
  ask which ports a saved node has (validator, editor, node config, tombstone
  restore).
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
    run_session,                     # RunSession; None when no session is active
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
| Flow | StartNode, EndNode, BranchNode, BranchEndNode, ConditionalNode, MergeNode, WaitUntilNode |
| Data | SetVariableNode, GetVariableNode, ConcatNode |
| IO | TextOutputNode, UserTextInputNode, FileReaderNode |
| AI | ChatCompletionNode, ImageGenerationNode, EmbeddingNode |
| Debug / Utility | LoggerNode, SleepNode, CounterNode, EchoNode, ProbeNode, ErrorNode, MemorySnapshotNode, RandomBranchNode, DeepBranchNode, NoOpNode, RepeatCounterNode, VariableSetterNode, VariableReaderNode |
| Editor (save-only) | TombstoneNode — save-persistent deleted-node record; always a validation error; never executable |

### `RunSession`

Per-run resource lifecycle manager. Created by `MasterState` at run start,
threaded through `NodeContext` as `context.run_session`, and closed by
`MasterState._record_run` on every terminal path (FINISHED, supervisor error,
forced termination).

Holds Python handles that cannot be JSON-serialized:

- **File handles**: opened via `open_file(path, mode)`, cached by resolved path
  and mode so multiple readers of the same file share one handle.
- **Arbitrary resource handles**: stored with `register_resource(key, handle,
  close_hook=None)` and retrieved with `get_resource(key)` (planned).

Workflow saves store only portable strings (file paths, session key names).
Handles are reconstructed at runtime through `RunSession`.

**Run-owned temporary files (R4, ESP32 slice).** `new_run_file(name)` reserves
a path under `<data dir>/run_files/<run_id>/` (`persistence.RUN_FILES_DIR`,
created on first use) with lifetime `run`; `run_file_reference(path)` builds
the `file` ref (`lifetime: "run"`), and `keep_file(ref)` marks it `kept`.
`MasterState._record_run` calls `close_all(delete_run_files=succeeded)`, where
succeeded means FINISHED, no unhandled errors and no user Stop (the same runs
that exit 0; D10: an error routed along an error path is logged with
`handled: true` and does not count). Otherwise every run file is kept for debugging. `file` refs
without `lifetime` mean `kept`, so older refs are unchanged.

**Typed vault reference resolution.** When a `MemoryBank` vault entry carries
`type: "file"` or `type: "ai_session"`, the entry holds a string `ref_key`,
not the handle itself. Nodes resolve the handle by calling
`context.run_session.get_resource(ref_key)`. The type tag determines which
lookup path applies. Input dropdowns in node config filter by the declared
input type so only compatible vault entries are offered.

**AI session handles.** Any LLM node that opts into session persistence
registers a session handle (provider client + message history) in `RunSession`
under a user-supplied key and writes `(type: ai_session, ref_key)` to the
vault. Downstream nodes retrieve and continue the session through the same
key. Message history accumulates in the session object in `RunSession`;
`MemoryBank` holds only the reference key.

`validate_path(path)` checks whether a file path is accessible before the node
runs (used by the `Validator` for `path_hint: "file"` schema fields).

### `MemoryBank`

The shared whiteboard for one run. Two stores:

- **Persistent store**: named variables (vault) shared by all supervisors for
  the whole run. Read/written by nodes through `context.memory_bank`. Every
  vault entry carries a `type` field: `string`, `number`, `boolean`, `file`, or
  `ai_session`. Simple types are pure JSON values. `file` and `ai_session`
  entries store a type tag and a string reference key resolved through
  `RunSession.get_resource`.
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
7. If an error, publish recovery options and await a decision (RETRY / SKIP / TERMINATE_BRANCH / TERMINATE_WORKFLOW). A payload routed to an unconnected `error` port counts as an error. In an unattended run the policy action is applied without waiting, input requests fail, and breakpoints are skipped.
8. On success, save the completed node ID before changing the current node.
9. Handle the payload: publish transient outputs, select the route or spawn
   branches, and update the current node ID.
10. Only then await `mark_node_completed(saved_node_id)` and report delivery.
    Continue or terminate as selected.

**Ordering invariant:** outputs must be available before completion wakes a
cross-branch waiter. Never mark the next node completed accidentally by reading
the changed current-node ID. `tests/test_wait_until_vault.py` covers the wait/Vault
ordering contract.

### `MasterState`

The floor manager. Does not execute nodes; it coordinates supervisors.

Starting a run:

1. Cancel and await any supervisor tasks left over from the previous run.
2. Generate `run_id`; store the run's unattended policy (`None` for the TUI).
3. Clear `MemoryBank`, `OutputManager`, supervisor tracking, `node_timings`, and `completed_nodes`.
4. Find the workflow start node.
5. Create and task root supervisor.
6. Broadcast `WORKFLOW_STATE_UPDATE(RUNNING)`.

Supervisor event routing handles:

- `SUPERVISOR_REGISTER` — track supervisor instance.
- `SUPERVISOR_TERMINATING` — remove supervisor; check run completion.
- `SUPERVISOR_REQUEST_BRANCH` — enforce `max_branch_depth`; create child supervisor.
- `SUPERVISOR_STATE_UPDATE` — track waiting-for-input state.
- `SUPERVISOR_ERROR` — transition to ERROR state; record run.
- `BREAKPOINT_HIT` — pause all active supervisors.
- `NODE_TIMING_UPDATE` — accumulate elapsed seconds per node into `node_timings`.
- `TERMINATE_WORKFLOW_REQUESTED` — stop all supervisors; record run as ERROR.

`stop()` requests stop on every supervisor and then cancels their tasks, so a
supervisor parked on a wait is released.

Per-run state lives in a `RunContext` (`backend/run_context.py`), created
once per run: memory bank reference, `RunSession`, `WaitRegistry`, node
timings, branch and merge groups, delivery tracking, live supervisors,
`run_id`/`parent_run_id`, the unattended policy and the start time. Each
supervisor gets `mark_node_completed`, `wait_for_nodes`, `wait_for_merge` and
`report_node_outcome` callables bound to **its own** run, so a stale
supervisor can never mark completions in another run. `MasterState` keeps
`completed_nodes`, `node_timings` and `run_context` as read-only views of the
current run.

The memory bank is still the one shared instance the TUI displays, cleared at
run start; per-run memory instances belong to the parallel-runs work (step 6).

WaitUntil coordination (`backend/wait_registry.py`):

- `mark_node_completed(node_id)` — marks key `("node", node_id)` completed in
  the run's `WaitRegistry`; completion is sticky for the run and releases every
  waiter whose keys are now all complete.
- `wait_until_nodes_completed(target_ids, timeout)` — parks on one Future per
  wait. It ends `completed`, `unreachable` (raises `TargetUnreachableError`
  naming the target) or `stopped` (raises `WaitStoppedError`; never a raised
  `CancelledError` from the registry). A positive timeout raises
  `asyncio.TimeoutError`.
- Delivery tracking: each supervisor reports a node visit's final state
  (`completed`, `failed`, `skipped`) and the targets it routed to.
- Structural unreachable rule (D5), re-evaluated whenever a node finishes, a
  supervisor terminates or a wait is registered, and never on a timeout. A
  target can no longer complete when no live supervisor is at it or can reach
  it, and either its own latest visit failed or was skipped, or none of its
  incoming connections' sources routed to it and no live supervisor can still
  reach any of them. A source that never ran and cannot be reached is settled
  (step 3's D9 marks it skipped). A target with no incoming connections is
  therefore unreachable at once. A required input that is never delivered
  stays a data error, not unreachability.
- Known limits (not deadlock detection): a target reachable only through the
  parked waiter itself, or behind a Merge whose group includes the waiter's
  branch, still waits forever. A Merge plus waiter deadlock also exists on
  earlier code.
- Merge keeps its own barrier (now held in the `RunContext`); it already
  releases when a sibling branch ends.

Run completion occurs when `_supervisors` and `_supervisor_tasks` are both empty. MasterState then finalizes outputs, records the run, and broadcasts `WORKFLOW_STATE_UPDATE(FINISHED)`.

### `SaveManager`

The archivist. Assembles complete save objects combining WorkflowMap structure, MemoryBank state, and ConfigurationManager settings. Handles load/save/delete/duplicate/export/import of workflows.

### `Validator`

The inspector. Performs a DFS from the start node and checks:

- Node type exists in `NodeFactory`.
- Connection sources and targets exist.
- Connection ports are declared by source and target node metadata.
- Tombstone nodes are flagged as errors with original node name and connection context from stored config.
- Derived `input_sources` reference existing node ids.
- Memory-bank input keys are declared by some node's `membank_outputs`.
- Schema fields hinted with `path_hint: "file"`: empty required path is an
  error; path missing on disk is a warning.
- Typed vault reference ordering (planned): error if no node declares the vault
  key; warning if the declaring node is on a parallel branch with unguaranteed
  execution order. Applies to all vault types including `file` and `ai_session`.

After traversal, any unvisited node is unreachable and reported as a warning. Return shape:

```python
{"errors": [...], "warnings": [...]}
```

Each error and warning includes `node_id` so the UI can highlight the affected node.

### Errors and skips (`backend/node_errors.py`, step 3)

- **D7 codes.** Each node declares `error_definitions`; `NodeFactory` adds the
  default generic `node_error` first. Engine codes use `engine.*`. The
  supervisor codes every failure, logs it once, then routes the versioned
  error payload along a connected `error` port, or to an Error Mux placed
  inline after the node (its normal output feeds the mux's `input`;
  `Supervisor._inline_error_route`). A mux catches only codes one of its
  branches lists, or any code when "Any other error" is on (route logic in
  `node_errors.mux_routes` / `mux_route_for_code` / `mux_forward_for`). A
  routed failure is published as node status `recovered` (with the code as
  `reason`), not `errored`; otherwise the failure falls
  through to recovery / the run's policy. `error` is accepted
  as an output port on every node by the validator. The editor always shows it
  on nodes that list it (HTTP Request, JSON Path); any other node shows its
  error path while a stored `show_error_path` is on or once that path is
  wired (`frontend/error_paths.py`, P3). Since UX4 the UI no longer offers a
  toggle for it (U10): the Errors section's **Add Error Resolver Node** button
  inserts an Error Mux inline after the node instead (default alias "Error
  Resolver"), or **Open Error Resolver Node** opens the mux that already
  catches it (`error_mux_ui.inline_mux_for`). Cancelling the first edit of a
  freshly inserted mux removes it and restores the wiring (U8).
- **D8.** Node config keeps Connections and adds an Errors section.
- **D9.** `RunContext.skip_candidates()` plus `MasterState._spread_skips()`
  mark nodes skipped with a reason whenever an outcome is reported or a
  supervisor ends; skipped nodes count as finished (D5) but never completed.

### `RunService` (`backend/run_service.py`)

The one in-process API clients use to run workflows (step 2 of the
distributed plan): `load(reference)` (saved id, saved name, or a workflow
`.json` path; loading never changes settings), `validate()`,
`start(inputs=, recovery_policy=, input_provider=, validate=True)` (validates
first and refuses with `WorkflowValidationError`), `subscribe()` (returns an
unsubscribe function), `submit_input()`, `submit_recovery()`, `pause()`,
`resume()`, `stop()`, `wait()` and `result()`. `RunResult` is
JSON-serializable and maps to shared exit codes (0 finished, including runs
whose errors were all routed along error paths, 1 finished with unhandled
errors, 2 failed, 3 invalid or unstartable, 4 not found or unloadable, 130
stopped). A run stopped through the service reports `STOPPED` even though the
engine records `FINISHED` (no engine `STOPPED` state yet). `RunService.create()`
builds a full backend stack with no frontend import. The CLI uses it; the TUI
still drives `MasterState`'s public methods directly (unchanged behavior).

### Run policies (`backend/run_policies.py`, D1)

`RecoveryPolicy.decide(RecoveryRequest)` and `InputProvider.provide(InputRequest)`
are supplied by whoever starts a run. With none, the run is attended: the
engine publishes `RECOVERY_OPTIONS_AVAILABLE` / `USER_INPUT_NEEDED` and waits
for a client. A policy whose `pause_at_breakpoints` is False also skips
breakpoints. `start_workflow(unattended=...)` from step 1 is shorthand for
`TerminatePolicy(mode)` plus `NoInputProvider`, the first `RecoveryPolicy`.

### Logging (`backend/logging_setup.py`)

`configure_logging(configuration)` is shared by every client: WARNING and
above to stderr, plus a daily rotating file under the data directory's
`logs/` when `log_to_file_enabled` is set. `main.configure_logging` remains
as a thin wrapper.

## Frontend Components (Textual TUI)

### `App` (`AttackOfTheNodesApp`)

Root Textual application. Created by `main.py` alongside all backend services. Subscribes to backend events on startup (once, for the session lifetime). Manages the screen stack and routes user commands to backend services.

### `EditorScreen`

The blueprint view. Shows a `NodeList` (left panel) and a details panel
(right). Priority-bound keys include `W/S` for row movement, `A/D` for branch
view cycling, `E`/`Enter` to edit or activate selector rows, `I` to insert
after the highlighted row, `X`/`Backspace` to delete or tombstone, `F` for the
File/workflow menu, `O` for options, `H` for help, and `V` for validation.
`Ctrl+S` saves and `Ctrl+R` runs at app level.

Editor-specific topology adapters live here, not in backend nodes. Current
adapter behavior includes:

- Hiding an empty Start node until the first real node is added.
- Soft-deleting nodes visually while editing; saving materializes each deletion
  as a `tombstone_node` with the original type, alias, config, and connections
  stored in config for undo-after-reload and validator repair context.
- Repairing older save files that stored invalid `Merge.input` connections by
  mapping them to the upstream branch port.
- Reconciling checked merge branch closures into real
  `BranchEnd.default -> Merge.path_*` graph edges.
- Rendering Merge Beacon rows red while open and green when connected to a Merge.

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

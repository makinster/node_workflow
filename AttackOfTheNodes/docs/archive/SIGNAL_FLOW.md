> Superseded by [ARCHITECTURE](../ARCHITECTURE.md) on 2026-10-17.
> Historical document retained whole; old status, permissions and designs below
> are not current instructions. See [Current State](../CURRENT_STATE.md).

# Backend Responsibilities and Signal Flow

This document captures the operational wiring for AttackOfTheNodes: who owns what, which components trade data, and which events move through the system.

## Component Responsibilities

### `persistence.py`

Responsibilities:

- Raw JSON file I/O for five data directories: `workflows/`, `settings/`, `run_history/`, `run_outputs/`, `run_errors/`.
- Does not interpret workflow schema or business meaning.
- All paths anchored to project root via `Path(__file__).resolve().parent.parent`.

Data trades:

- Called directly by `WorkflowMap`, `OutputManager`, `ErrorHandler`, `RunHistory`, and `ConfigurationManager`.
- Returns raw dicts; callers own interpretation.

Signals: none.

### `ConfigurationManager`

Responsibilities:

- Load and cache settings from `settings/settings.json` on first access.
- Validate setting keys against `DEFAULT_SETTINGS`.
- Serve repeated reads from memory.

Data trades:

- Provides `max_branch_depth`, `node_timeout_seconds`, `last_active_workflow_id` to execution and save services. (`node_timeout_seconds` only applies to a `wait_for_nodes`/`wait_for_merge` call made with `timeout=None`; Wait Until and Merge pass `0.0`, and node execution itself is never timed out.)
- Persists updated settings through `persistence.py`.

Signals: none.

### `EventBus`

Responsibilities:

- In-process pub/sub dispatch.
- `subscribe(event_name, callback)`, `publish(event_name, payload)`, `unsubscribe(event_name, callback)`.

Data trades:

- Receives subscriptions from `MasterState` (8 events) and `App` (10 events) at startup.
- Receives `publish` calls from `Supervisor`, `MasterState`, `MemoryBank`, `ErrorHandler`, `RunHistory`, and `WorkflowMap`.

Signals: all events flow through `EventBus`.

### `WorkflowMap`

Responsibilities:

- Maintain active workflow in memory as `dict[node_id, node_data]`.
- Track dirty state; mutations set dirty, saves clear it.
- Provide executable node instances through `NodeFactory`.
- Handle node add, delete, config updates, tombstone swaps.
- Traverse graph: start-node discovery, next-node lookup, input-source lookup, BFS reachability (`nodes_reachable_from`).

Data trades:

- Receives load/save instructions from `SaveManager`.
- Uses `persistence.py` for raw workflow JSON.
- Uses node instances, config templates, and metadata from `NodeFactory`.
- Sends node instances and adjacency details to `Supervisor`.
- Sends workflow structure to `Validator` and `SaveManager`.

Signals: publishes `WORKFLOW_DIRTY` on mutations.

### `NodeFactory`

Responsibilities:

- Registry from node type string to node class.
- Create executable node instances.
- Generate default node config templates.
- Provide node metadata and port definitions for UI.

Data trades:

- Receives requests from `WorkflowMap` and `Validator`.
- Returns instances, config templates, metadata, and type existence checks.

Signals: none.

### Node Classes

Responsibilities:

- Execute node-specific work.
- Accept inputs and runtime context from a supervisor.
- Report done, error, waiting, or branching state through context signals.
- Read/write shared memory through `context.memory_bank`.

Data trades:

- Receive `NodeContext` from `Supervisor`.
- Send execution outcomes back through `context.signal_done`, `context.signal_error`, `context.signal_waiting_for_input`, or `context.wait_for_nodes`.

Signals sent through context:

- `signal_done(payload)` — `payload` may carry `data` (port values) and/or `branches`.
- `signal_error(error)` — triggers the supervisor recovery flow.
- `signal_waiting_for_input(prompt)` → awaitable str — suspends supervisor until input arrives.
- `wait_for_nodes(node_ids, timeout)` → awaitable — suspends until target nodes complete.

### `MemoryBank`

Responsibilities:

- Persistent store: named variables shared across all supervisors for one run.
- Transient store: port data keyed `(source_node_id, port_name)`, written by supervisor after node execution.
- Both stores cleared on run start.

Data trades:

- Receives transient writes from `Supervisor` after each node.
- Receives persistent reads/writes from nodes through `context.memory_bank`.
- Provides values to `Supervisor` when preparing inputs for the next node.

Signals: publishes `MEMORY_UPDATE` on persistent store changes.

### `OutputManager`

Responsibilities:

- Collect output-node data during a run, keyed by `run_id`.
- `finalize_run(run_id)`: persist to `run_outputs/`, evict from memory, return values.
- `get_outputs_for_run(run_id)`: lazy-load from disk for historical views.

Data trades:

- Receives output writes from `MasterState._check_run_completion`.
- Persists through `persistence.py`.

Signals: none directly (outputs visible via `MasterState.run_outputs` after finalization).

### `ErrorHandler`

Responsibilities:

- Centralized structured error logging.
- `log_error()`: append to in-memory cache, persist to `run_errors/`, broadcast.
- `finalize_run(run_id)`: evict in-memory cache after run is recorded.
- `get_errors_for_run(run_id)`: lazy-load from disk.

Data trades:

- Receives errors from `Supervisor._request_recovery`.
- Saves errors through `persistence.py`.

Signals: publishes `ERROR_LOGGED` on each error, `ERRORS_CLEARED` on clear.

### `RunHistory`

Responsibilities:

- Store run summaries in `run_history/` and maintain a capped in-memory list.
- `_MAX_IN_MEMORY = 500`: in-memory list never exceeds this; disk retains full history.
- Records include: run_id, workflow_id, workflow_name, started_at, ended_at, final_state, error_count, output_count, node_timings.

Data trades:

- Receives `record_run(summary)` calls from `MasterState._record_run`.
- Persists through `persistence.py`.

Signals: publishes `RUN_HISTORY_UPDATED` after each new record.

### `Supervisor`

Responsibilities:

- Walk one execution path through the workflow.
- Maintain branch-local state: current node, state enum, stop/pause flags, pending futures.
- Fetch nodes, prepare inputs, execute nodes, time execution, handle output, advance.
- Manage breakpoints: pause before a node if `node_data["breakpoint"]` is set.
- Pause for user input via `signal_waiting_for_input`.
- Implement error recovery: log error, publish recovery options, await decision, apply RETRY / SKIP / TERMINATE_BRANCH / TERMINATE_WORKFLOW.
- Call `mark_node_completed(node_id)` after each successful execution.

Data trades:

- Receives control signals (`request_pause`, `request_resume`, `request_stop`) from `MasterState`.
- Fetches node instances and adjacency from `WorkflowMap`.
- Reads/writes `MemoryBank`.
- Reports errors through `ErrorHandler`.
- Sends node execution context.

Signals sent to `MasterState` via EventBus:

- `SUPERVISOR_REGISTER` — emitted on `run()` start.
- `SUPERVISOR_STATE_UPDATE` — emitted on state changes.
- `SUPERVISOR_REQUEST_BRANCH` — emitted when a node signals branches.
- `SUPERVISOR_TERMINATING` — emitted when the path ends or is stopped.
- `BREAKPOINT_HIT` — emitted before executing a node with `breakpoint: True`.
- `NODE_TIMING_UPDATE` — emitted after every node execution with elapsed seconds.
- `RECOVERY_OPTIONS_AVAILABLE` — emitted when a node errors; carries recovery options.
- `USER_INPUT_NEEDED` — emitted when `signal_waiting_for_input` is called.
- `TERMINATE_WORKFLOW_REQUESTED` — emitted when TERMINATE_WORKFLOW recovery action is chosen.
- Node-emitted events via `context.emit_event(name, payload)` — the
  supervisor wires `NodeContext.publish_event` and stamps
  `run_id`/`branch_id`/`node_id` into every payload. Current event:
  `FILE_VIEW_REQUESTED` (FO3; carries `path`, `ref_key`, `render`).
  Fire-and-forget: execution never waits on a subscriber, and headless runs
  simply have none.

### `MasterState`

Responsibilities:

- Manage all active supervisors.
- Spawn branch supervisors and enforce `max_branch_depth`.
- Maintain run state machine: IDLE, RUNNING, PAUSED, WAITING_FOR_INPUT, FINISHED, ERROR.
- Route user input and recovery decisions back to waiting supervisors.
- Detect run completion (all supervisors gone).
- Coordinate WaitUntil: track `completed_nodes` via `asyncio.Condition`.
- Handle breakpoints: pause all supervisors when `BREAKPOINT_HIT` fires.
- Accumulate per-node timing from `NODE_TIMING_UPDATE`.
- Broadcast execution state through `EventBus`.

Data trades:

- Receives run/control commands from `App` actions.
- Receives supervisor events from `EventBus`.
- Reads branch-depth and timeout settings from `ConfigurationManager`.
- Sends `mark_node_completed` and `wait_for_nodes` callbacks to supervisors on construction.
- Calls `OutputManager.finalize_run`, `ErrorHandler.get_errors_for_run`, `RunHistory.record_run`, and `ErrorHandler.finalize_run` on run completion.

Signals published:

- `WORKFLOW_STATE_UPDATE` — on every state transition.

### `Validator`

Responsibilities:

- DFS from start node; report blocking errors and advisory warnings.
- Verify node type exists in `NodeFactory`.
- Verify connection targets and sources exist.
- Verify each connection uses declared source and target ports.
- Flag tombstone nodes as errors.
- Validate derived node and memory-bank input sources.
- Report unreachable (loose) nodes as warnings.

Data trades:

- Receives validate requests from `EditorScreen.action_validate_workflow`.
- Reads workflow structure from `WorkflowMap`.
- Checks node registration through `NodeFactory`.

Signals: none. Returns `{"success": bool, "errors": [...], "warnings": [...]}`.

### `SaveManager`

Responsibilities:

- Orchestrate save/load/delete/duplicate/export/import of workflows.
- Assemble complete save payloads from `WorkflowMap` and `MemoryBank`.
- Update `last_active_workflow_id` in `ConfigurationManager` on load.

Data trades:

- Receives save/load requests from `App` actions.
- Reads workflow structure from `WorkflowMap`.
- Persists through `persistence.py`.

Signals: none. Returns success/failure.

### `App` (`AttackOfTheNodesApp`)

Responsibilities:

- Root Textual application; manages screen stack.
- Subscribe to backend events on startup.
- Route backend events to the active screen (`refresh_from_backend`).
- Coalesce run telemetry: those events update App display state and mark the
  screen dirty; one refresh runs per `REFRESH_COALESCE_SECONDS` (75 ms).
  Events that need the user or change the run state refresh at once and
  flush any pending refresh (`App.flush_refresh()`, also the test hook).
- Route user key commands to backend services.
- Open/close modals for user input, recovery, and settings.

Signals consumed (subscribed once at startup):

- `WORKFLOW_DIRTY` → refresh editor (immediate)
- `WORKFLOW_STATE_UPDATE` → update `workflow_state`, trigger resets (immediate)
- `NODE_EXECUTION_UPDATE` → update node statuses (coalesced)
- `NODE_TIMING_UPDATE` → update live node timings (coalesced)
- `SUPERVISOR_REGISTER` → track supervisor in `supervisors` dict (coalesced)
- `SUPERVISOR_STATE_UPDATE` → update branch positions (coalesced)
- `SUPERVISOR_TERMINATING` → mark supervisor as done (coalesced)
- `USER_INPUT_NEEDED` → open `UserInputScreen` modal (immediate)
- `FILE_VIEW_REQUESTED` → open `FileViewerScreen` modal (ignored while one
  is already open; execution does not wait)
- `ERROR_OCCURRED` → refresh (immediate)
- `ERROR_LOGGED` → refresh (immediate)
- `RECOVERY_OPTIONS_AVAILABLE` → open `ErrorDetailsScreen` modal (immediate)
- `MEMORY_UPDATE` → refresh (coalesced)

A linear run publishes about 5 events per node; before coalescing each one
rebuilt the execution screen synchronously inside the engine's publish call.

## Scenario Flows

### User Starts a Workflow

```
User presses Ctrl+R
  -> App.action_run_workflow()
  -> App switches to ExecutionScreen
  -> App creates asyncio task for _start_workflow()
  -> MasterState.start_workflow()
     -> WorkflowMap.find_start_node_id()
     -> MasterState clears MemoryBank, OutputManager, node_timings, completed_nodes
     -> Supervisor created with mark_node_completed, wait_for_nodes, node_timeout_seconds
     -> asyncio.create_task(supervisor.run())
     -> SUPERVISOR_REGISTER fires -> MasterState tracks supervisor
     -> WORKFLOW_STATE_UPDATE(RUNNING) fires -> App.workflow_state = "RUNNING"
```

### Node Completes on a Simple Path

```
Supervisor._run_loop iteration
  -> WorkflowMap.get_node_instance(current_node_id)
  -> Supervisor._prepare_inputs from MemoryBank transient store
  -> node.execute(context) wrapped in perf_counter
  -> node calls context.signal_done({"data": {"default": value}})
  -> NODE_TIMING_UPDATE fires -> MasterState accumulates node_timings
  -> MasterState.mark_node_completed(node_id) -> completed_nodes updated, Condition notified
  -> Supervisor writes transient outputs to MemoryBank
  -> Supervisor advances current_node_id via WorkflowMap.find_next_node_id
```

### Node Requests User Input

```
node calls context.signal_waiting_for_input(prompt) -> awaitable
  -> Supervisor stores Future, sets state WAITING_FOR_INPUT
  -> USER_INPUT_NEEDED fires -> App opens UserInputScreen modal
  -> SUPERVISOR_STATE_UPDATE fires -> App.node_statuses updated
  -> User submits input through UserInputScreen
  -> App._submit_user_input_from_modal -> MasterState.submit_user_input(branch_id, value)
  -> MasterState -> supervisor.submit_user_input(value)
  -> Supervisor resolves pending Future; node.execute resumes
  -> Supervisor state returns to RUNNING
```

### Node Signals Error (Recovery Flow)

```
node calls context.signal_error(error)
  -> Supervisor._request_recovery(error, inputs)
  -> ErrorHandler.log_error -> persists, broadcasts ERROR_LOGGED
  -> Supervisor stores recovery Future, sets state AWAITING_RECOVERY
  -> RECOVERY_OPTIONS_AVAILABLE fires -> App opens ErrorDetailsScreen modal
  -> User picks action (RETRY / SKIP / TERMINATE_BRANCH / TERMINATE_WORKFLOW)
     (SKIP marks the node skipped and ends the branch; downstream skips spread)
  -> App._submit_recovery_from_modal -> MasterState.submit_recovery_action
  -> MasterState -> supervisor.submit_recovery_action(action)
  -> Supervisor resolves recovery Future; applies action
```

### Command-Line Run (`aotn run`)

```
aotn run <workflow> [--data-dir DIR] [--policy P] [--input K=V] [--json]
  -> main.main routes "run" to aotn_cli.main (no Textual import on this path)
  -> --data-dir sets AOTN_DATA_DIR before the backend is imported
  -> RunService.create(); configure_logging(settings)
  -> RunService.load(id | name | file.json)   (not found / unloadable -> exit 4)
  -> policies: stdin RecoveryPolicy + InputProvider when stdin is a terminal
     and no --policy; otherwise TerminatePolicy(--policy or
     terminate_workflow) + NoInputProvider
  -> RunService.start(...) validates first   (invalid / unstartable -> exit 3)
  -> ERROR_LOGGED -> "error: <alias> (<node_id>): <message>" on stderr
  -> RunService.wait() -> RunResult
     -> outputs on stdout (or the result as JSON with --json)
     -> summary on stderr; exit 0 / 1 (unhandled errors) / 2 (failed)
  -> SIGINT (POSIX loops) -> RunService.stop(); result STOPPED, exit 130
  -> interactive prompts read stdin in a daemon thread, one prompt at a time
```

### Node Fails: Error Codes, `error` Port, Recovery (step 3)

```
node raises / signal_error(exc)   or   signal_done({"data": {"error": msg,
                                       "code": c}, "output_port": "error"})
  -> node reports `errored`
  -> Supervisor gives the failure a code: declared (NodeError / data.code),
     engine (engine.upstream_unreachable, engine.unattended_input) or the
     default node_error
  -> ErrorHandler.log_error(..., code) -> persisted, ERROR_LOGGED (once)
  -> `error` port connected?
     -> Error Mux that lists the code, or any non-mux node:
        transient (node, "error") = versioned payload; route there;
        node outcome failed (delivered to the handler); `default` path is
        skipped as not_taken
     -> otherwise (unconnected, or a mux without the code):
        recovery (RECOVERY_OPTIONS_AVAILABLE with `code`) or the run's policy
```

A failure is never routed down `default`.

### Unattended Run

```
MasterState.start_workflow(unattended="terminate_branch" | "terminate_workflow")
  -> every Supervisor of the run gets the policy
  -> node error: ErrorHandler.log_error (persisted, ERROR_LOGGED), then the
     policy action is applied without RECOVERY_OPTIONS_AVAILABLE
  -> input request: node fails with UnattendedInputError -> policy
  -> breakpoint: skipped, no BREAKPOINT_HIT
```

The TUI passes nothing (attended); the step 2 run service turns this value
into the first `RecoveryPolicy`. Since step 1b a Wait Until whose target can
no longer complete fails instead of waiting, so it follows the policy too.

### User Stops A Run

```
MasterState.stop()
  -> RunContext.wait_registry.stop(): waiters get a `stopped` result
  -> supervisor.request_stop() for each supervisor
  -> cancel each supervisor task (except one that is itself terminating the
     workflow)
  -> a node mid-execution or parked in Wait Until / Merge / input is released
     -> NODE_EXECUTION_UPDATE(stopped), SUPERVISOR_TERMINATING
  -> run completes (still recorded as FINISHED; there is no STOPPED state yet)

MasterState.start_workflow()
  -> serialized by a lock, so overlapping starts cannot lose track of a task
  -> cancels and awaits leftover supervisor tasks first, so a stale waiter
     can never wake inside the new run
```

A task cancelled before its first step never publishes
`SUPERVISOR_TERMINATING`; a done-callback removes it and re-checks run
completion. Cancelling does not stop work already handed to a thread
(`asyncio.to_thread`, e.g. a Chat Completion API call or a File Output
write): that work finishes in the background even though the node shows
`stopped`.

### Node Requests Branching

```
node calls context.signal_done({"data": {}, "branches": [...]})
  -> Supervisor._spawn_branches for each branch
  -> SUPERVISOR_REQUEST_BRANCH fires for each branch
  -> MasterState._on_request_branch checks max_branch_depth
  -> Child Supervisor created for each branch
  -> asyncio.create_task(child.run()) for each
  -> Each child emits SUPERVISOR_REGISTER
  -> Children run independently; each emits SUPERVISOR_TERMINATING when done
  -> Last SUPERVISOR_TERMINATING with empty supervisors triggers run completion
```

### Editor Connects Or Repairs Merge Inputs

```
User inserts/adds a node that targets a Merge node
  -> EditorScreen._connect_new_node()
  -> Editor derives containing upstream branch port
  -> WorkflowMap.connect(source.default, merge.path_*)
  -> Validator sees declared merge input port

Older save contains source.default -> merge.input
  -> EditorScreen.refresh_from_backend()
  -> _repair_merge_input_ports()
  -> disconnect merge.input
  -> reconnect source.default -> merge.path_* based on upstream branch
```

### Merge Config Closes A Merge Beacon

```
User checks a Merge Beacon path in Merge config
  -> NodeConfigScreen returns branches_to_close + carry_forward_branch_id
  -> EditorScreen saves merge config
  -> _sync_merge_branch_end_connections()
  -> WorkflowMap.connect(branch_end.default, merge.path_*)
  -> Editor refresh rebuilds rows
  -> NodeCard sees _branch_end_connected_to_merge and renders connected styling
```

### Breakpoint Hit

```
Supervisor._pause_for_breakpoint_if_needed
  -> WorkflowMap.get_node_data -> checks node_data["breakpoint"]
  -> BREAKPOINT_HIT fires
  -> MasterState._on_breakpoint_hit -> requests_pause on all active supervisors
  -> MasterState sets PAUSED state -> WORKFLOW_STATE_UPDATE(PAUSED) fires
  -> Supervisor pauses at resume_event
  -> User resumes via App.master_state.resume()
  -> Supervisors resume; skip_breakpoint_once_for prevents immediate re-pause
```

### WaitUntil Node

```
WaitUntilNode.execute
  -> context.wait_for_nodes(target_ids, timeout) -> awaitable
     -> Supervisor calls the wait callable bound to its own RunContext
     -> RunContext.wait_registry.wait_for_all([("node", id), ...])
        -> on registration MasterState evaluates the unreachable rule (D5)
  -> other supervisors finish nodes:
     -> report_node_outcome(node, completed|failed|skipped, delivered_to)
        -> RunContext delivery tracking; MasterState re-evaluates pending keys
     -> mark_node_completed -> WaitRegistry.mark_completed(("node", id))
  -> a supervisor terminates -> pending keys re-evaluated
  -> all targets completed: wait returns, WaitUntilNode signals done
  -> a target can no longer complete: TargetUnreachableError naming it
     -> WaitUntilNode signals error -> recovery (or the unattended policy)
  -> run stopped: WaitStoppedError; the supervisor discards the result
```

### Run Completion

```
Last SUPERVISOR_TERMINATING fires
  -> MasterState._check_run_completion
  -> _supervisors and _supervisor_tasks both empty
  -> read output_log from MemoryBank persistent store
  -> OutputManager.store_output_log -> finalize_run -> persists, evicts from memory
  -> MasterState.run_outputs set to returned values
  -> WORKFLOW_STATE_UPDATE(FINISHED) fires
  -> MasterState._record_run("FINISHED")
     -> ErrorHandler.get_errors_for_run -> captures error count
     -> RunHistory.record_run (with node_timings, no raw outputs)
     -> ErrorHandler.finalize_run -> evicts error cache
```

## Dependency Graph

```
main.py
  -> creates: EventBus, NodeFactory, WorkflowMap, MemoryBank,
              ConfigurationManager, OutputManager, MasterState, SaveManager
  -> creates: App(bus, factory, workflow_map, memory_bank, master, save_manager)

App
  -> subscribes to 10 EventBus events
  -> owns screen stack: EditorScreen, ExecutionScreen, modals
  -> delegates run/save/load commands to MasterState, SaveManager, WorkflowMap

MasterState
  -> subscribes to 8 EventBus events
  -> creates Supervisors on run start and branch requests
  -> calls into OutputManager, ErrorHandler, RunHistory on completion

Supervisor
  -> calls WorkflowMap (node instances, adjacency)
  -> calls MemoryBank (transient reads/writes)
  -> calls ErrorHandler (log_error)
  -> publishes 8 event types to EventBus
  -> calls MasterState callbacks (mark_node_completed, wait_for_nodes)

WorkflowMap
  -> calls persistence.py
  -> calls NodeFactory (create_node, get_node_instance)

SaveManager
  -> calls WorkflowMap, MemoryBank, ConfigurationManager
  -> calls persistence.py

OutputManager, ErrorHandler, RunHistory
  -> call persistence.py

NodeFactory
  -> imports node classes from backend/nodes/
```

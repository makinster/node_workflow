# AttackOfTheNodes Project Context

This workspace contains AttackOfTheNodes, a Python workflow engine and Textual terminal UI for building, running, pausing, branching, and inspecting node-based pipelines.

## Documentation Entry Point

Start with `AttackOfTheNodes/docs/README.md`. It gives the current read order
and marks which older reference docs may still contain historical
Chrome-extension or tkinter language. Before making backend changes for
editor/UI behavior, read `AttackOfTheNodes/docs/BACKEND_FRONTEND_BOUNDARY.md`.

## Mental Model

Think of the project as a factory floor with a control room:

- The backend is the factory floor. Nodes are machines arranged into workflows, and supervisors walk execution paths through those nodes.
- The frontend is the control room. It displays workflow structure, execution state, memory, outputs, errors, and settings — all in the terminal via Textual.
- A workflow is a recipe: nodes plus connections. Execution starts at a start node, follows connections, and can fork into branch supervisors.
- All supervisors in a run share one `MemoryBank` and report to `MasterState` through the `EventBus`.

## Core Backend Components

- `persistence.py`: flat JSON file I/O for `workflows/`, `settings/`, `run_history/`, `run_outputs/`, `run_errors/`. No schema interpretation.
- `ConfigurationManager`: settings cache and schema gatekeeper using `DEFAULT_SETTINGS`.
- `EventBus`: in-process pub/sub dispatcher. All inter-component signals use this.
- `WorkflowMap`: live workflow cache. Owns node CRUD, traversal, connections, dirty tracking, and persistence.
- `NodeFactory`: registry for executable node classes, config templates, and metadata.
- Node classes: isolated machines extending `Node`; they only know their config, inputs, and execution `NodeContext`.
- `MemoryBank`: per-run shared whiteboard with persistent variables and transient port data keyed `(source_node_id, port_name)`.
- `OutputManager`: collects output-node results during a run; evicts from memory after `finalize_run()`.
- `ErrorHandler`: centralized structured error logging per run; evicts from memory after `finalize_run()`.
- `RunHistory`: run summaries capped at 500 entries in memory; full history on disk.
- `Supervisor`: stateful worker that executes one path through a workflow graph.
- `MasterState`: conductor that starts runs, tracks supervisors, handles branching, pause/resume, breakpoints, node timing, WaitUntil coordination, and run completion.
- `SaveManager`: assembles complete save/load payloads across WorkflowMap, MemoryBank, and persistence.
- `Validator`: DFS preflight from start node; errors on invalid types/connections, warns on loose nodes.

## Core Frontend Components (Textual TUI)

- `App` (`AttackOfTheNodesApp`): root Textual app, subscribes to backend events, manages screen stack.
- `EditorScreen`: workflow editor with node list and details panel.
- `ExecutionScreen`: live run view with node status highlights.
- `NodeConfigScreen`: edit node config with keyboard-first `CommandInput`/`CommandTextArea` widgets; supports memory bank input/output declarations and WaitUntil target selection.
- Modals: NodeSelector, Confirm, ErrorDetails, BranchSelector, WorkflowLibrary, Settings, UserInput, Help.
- `NodeList`, `StatusBar`: editor widgets.
- `CommandInput` / `CommandTextArea`: mode-switching form widgets (`w`/`s` navigate, `e`/Enter edit, Esc end edit).

## Important Behavioral Rules

- Nodes are graph-ignorant; they receive pre-resolved inputs through `NodeContext` and signal back through context callbacks.
- `WorkflowMap` owns live workflow shape and dirty state.
- `MemoryBank` is ephemeral per run; `OutputManager` is the durable output record.
- `EventBus` is the only inter-component communication channel.
- All data paths anchor to `Path(__file__).resolve().parent.parent` via `persistence.py`.
- Branching happens when a node calls `context.signal_done({"branches": [...]})`. `MasterState` spawns one supervisor per branch and enforces `max_branch_depth`.
- User input nodes suspend a supervisor until the frontend sends the answer back through `MasterState.submit_user_input`.
- `WaitUntilNode` suspends a supervisor until all configured node IDs have completed in the current run, coordinated through `MasterState.wait_until_nodes_completed`.
- Breakpoints pause all active supervisors when `BREAKPOINT_HIT` fires; single-step resumes skip the same breakpoint once.
- `MasterState` and `App` are singletons created once per session; their bus subscriptions register once and remain for the session lifetime.
- Per-run memory caches (`OutputManager._outputs_by_run`, `ErrorHandler._errors_by_run`) are evicted after `finalize_run()` to prevent accumulation.

## Current Node Types

| Category | Types |
|---|---|
| Flow | `start_node`, `end_node`, `branch_node`, `conditional_node`, `merge_node`, `branch_end_node`, `wait_until_node` |
| Data | `set_variable_node`, `get_variable_node`, `concat_node` |
| IO | `text_output_node`, `user_text_input_node`, `file_reader_node` |
| AI | `chat_completion_node`, `image_generation_node`, `embedding_node` |
| Debug | `logger_node`, `sleep_node`, `counter_node`, `echo_node`, `probe_node`, `error_node`, `memory_snapshot_node`, `random_branch_node`, `deep_branch_node`, `no_op_node`, `repeat_counter_node`, `tombstone_node`, `variable_setter_node`, `variable_reader_node` |

`tombstone_node` is currently registered as the visual placeholder inserted when
a node is deleted. It is a known boundary-cleanup target: future work should move
this editor-only placeholder behavior into frontend adapter state so the backend
remains reusable by other frontends. See
`AttackOfTheNodes/docs/BACKEND_FRONTEND_BOUNDARY.md`.

## Key Events (EventBus)

`WORKFLOW_STATE_UPDATE`, `WORKFLOW_DIRTY`, `SUPERVISOR_REGISTER`, `SUPERVISOR_STATE_UPDATE`, `SUPERVISOR_TERMINATING`, `SUPERVISOR_REQUEST_BRANCH`, `SUPERVISOR_ERROR`, `BREAKPOINT_HIT`, `NODE_TIMING_UPDATE`, `RECOVERY_OPTIONS_AVAILABLE`, `TERMINATE_WORKFLOW_REQUESTED`, `USER_INPUT_NEEDED`, `ERROR_OCCURRED`, `ERROR_LOGGED`, `ERRORS_CLEARED`, `MEMORY_UPDATE`, `RUN_HISTORY_UPDATED`

## Entry Point

```bash
# Install
pip install -r AttackOfTheNodes/requirements.lock
pip install -e AttackOfTheNodes/

# Run
aotn
```

For the current docs map, see `AttackOfTheNodes/docs/README.md`.
For the active build plan, see `AttackOfTheNodes/docs/MASTER_BUILD_PLAN.md`.
For backend/frontend separation rules, see
`AttackOfTheNodes/docs/BACKEND_FRONTEND_BOUNDARY.md`.

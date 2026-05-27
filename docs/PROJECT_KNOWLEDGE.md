# AttackOfTheNodes — Project Knowledge

**Document purpose:** Single-source reference for the project's current state, architecture, and direction. Read this first when starting a new chat or onboarding a collaborator.

**Current major decision:** Continue with the local Python/tkinter prototype while keeping the backend UI-agnostic. A future Textual UI remains possible, but this repository currently implements tkinter.

---

## What This Project Is

AttackOfTheNodes is a workflow execution engine and local UI for building, running, pausing, branching, recovering, and inspecting node-based pipelines.

Users build directed graphs of processing nodes that pass data between each other. A workflow is a recipe; each node is a step; supervisors walk the graph, execute nodes in order, and spawn child supervisors when a branch node asks for parallel paths. All supervisors in a run share one `MemoryBank`.

The project began as a Chrome-extension architecture concept and is currently implemented as a local Python application. Real API integration is deferred to v1.0. Until then, AI-style nodes produce configurable placeholder text that mimics what real responses would look like.

The audience is technical users building automation pipelines, tool chains, and branching logic. Workflows can include file reading, variables, conditional routing, user prompts, output logging, and placeholder AI calls.

---

## Current State

The proof-of-concept backend and tkinter UI are implemented under `attackofthenodes_v05/`.

Implemented milestones:

- **v0.5:** backend foundation, execution engine, memory/output inspection, and test scenarios.
- **v0.6:** tkinter editor foundation, node selector/config modals, save/load, connection editing.
- **v0.7:** execution UI, run/pause/stop controls, supervisor selection, queued user-input modal.
- **v0.8:** structured error handler, recovery options, error modal, run history.
- **v0.9:** `ConfigurationManager`, `OutputManager`, `SaveManager`, settings UI, workflow settings UI, import/export/duplicate/delete, multi-workflow session cache, per-workflow dirty tracking, optional auto-save.
- **v0.95:** placeholder AI nodes, utility/data nodes, dedicated user input/file reader, bookmarks, Jump To navigation, validation highlighting.
- **v0.99 surface:** startup loads last active workflow, keyboard shortcuts, Help/About modals, settings-driven rotating-file logging.

Important boundary: this is a strong local prototype, not a packaged production release. Real API credential encryption, real API dispatch, PyInstaller/pip packaging, CI, and broad pytest coverage remain deferred.

---

## Technology Stack

- Python 3.10 or later.
- tkinter for the currently implemented UI.
- asyncio for node execution and supervisor tasks.
- JSON files for workflows, settings, run history, run outputs, and run errors.
- No third-party backend dependencies.

The execution model is single-threaded asyncio. Supervisors are scheduled as asyncio tasks. Nodes can pause for user input through futures without blocking the whole app.

---

## Current File Structure

```text
attackofthenodes_v05/
  main.py
  demo_execution.py
  test_execution.py
  test_error_recovery.py
  test_v09_managers.py
  test_v095_nodes.py
  backend/
    configuration_manager.py
    error_handler.py
    events.py
    event_bus.py
    master_state.py
    memory_bank.py
    node_base.py
    node_factory.py
    output_manager.py
    persistence.py
    run_history.py
    save_manager.py
    supervisor.py
    validator.py
    workflow_map.py
    nodes/
      __init__.py
      branch_node.py
      chat_completion_node.py
      concat_node.py
      conditional_node.py
      embedding_node.py
      end_node.py
      file_reader_node.py
      get_variable_node.py
      image_generation_node.py
      set_variable_node.py
      start_node.py
      text_output_node.py
      user_text_input_node.py
  frontend/
    app.py
    async_tk.py
    controls_panel.py
    editor_panel.py
    execution_panel.py
    node_card.py
    toolbar.py
    ui_state.py
    modals/
      common.py
      error_details.py
      help.py
      memory_viewer.py
      node_config.py
      node_selector.py
      output_viewer.py
      run_history.py
      settings.py
      user_input.py
      workflow_library.py
      workflow_settings.py
  workflows/
  settings/
  run_history/
  run_errors/
  run_outputs/
  logs/
```

Project reference docs:

- `docs/ARCHITECTURE.md`
- `docs/SIGNAL_FLOW.md`
- `docs/V05_BUILD_PLAN.md`
- `docs/PROJECT_KNOWLEDGE.md`

---

## Backend Architecture

The backend is organized into discrete components with strict separation of concerns.

### Persistence

`backend/persistence.py` wraps JSON file I/O. It knows nothing about workflow semantics. It provides workflow CRUD plus generic JSON record helpers for settings, run history, run outputs, and run errors.

Paths are anchored to the package root so the app works regardless of the current working directory.

### Event Bus

`backend/event_bus.py` provides synchronous publish/subscribe messaging. Components subscribe to named events, and publishers send payloads. Callback exceptions are logged and swallowed so one broken subscriber does not stop dispatch.

### Node Base

`backend/node_base.py` defines:

- `Node`
- `NodeContext`

Every node declares class-level metadata:

- `node_type`
- `display_name`
- `description`
- `input_ports`
- `output_ports`
- `default_config`
- `config_schema`

Every node implements `async execute(context)`.

`NodeContext` includes:

- current node, branch, and run ids
- prepared `inputs`
- `memory_bank`
- `signal_done`
- `signal_error`
- `signal_waiting_for_input`

### Node Factory

`backend/node_factory.py` registers every class listed in `backend/nodes/__init__.py`. It exposes:

- `create_node`
- `create_config_template`
- `get_node_types_metadata`
- `is_valid_node_type`
- `get_registered_types`

Adding a node means creating a node file and registering the class in `ALL_NODE_CLASSES`.

### Workflow Map

`backend/workflow_map.py` holds loaded workflows in memory. It preserves an active-workflow API for existing code and now also keeps a cache of open workflows keyed by workflow id.

Responsibilities:

- active workflow identity and dirty state
- per-workflow dirty state in cache
- node CRUD
- bookmark updates
- connection/disconnection
- start node lookup
- input/output graph traversal
- save serialization shape
- switch/close open workflows
- Jump To filters

Workflows persist nodes as plain JSON objects keyed by node id.

### Memory Bank

`backend/memory_bank.py` holds run-scoped data:

- persistent named variables
- transient point-to-point port data keyed as `node_id__port_name`

Persistent writes publish `MEMORY_UPDATE`. Both stores clear at run start.

### Supervisor

`backend/supervisor.py` walks one execution path through the graph.

Loop shape:

1. Check pause/stop flags.
2. Fetch node instance from `WorkflowMap`.
3. Prepare inputs from `MemoryBank` transient data.
4. Await `node.execute(context)`.
5. Handle `signal_done`, `signal_error`, user input, or missing signal.
6. Write output data to transient memory.
7. Spawn child supervisors for branch payloads.
8. Follow explicit `next_node_id`, selected `output_port`, or default output connection.
9. Publish terminating when done.

Recovery flow is implemented. Recoverable node errors publish `RECOVERY_OPTIONS_AVAILABLE` and wait for a recovery future.

Supported recovery actions:

- `RETRY`
- `SKIP`
- `TERMINATE_BRANCH`
- `TERMINATE_WORKFLOW`

### Master State

`backend/master_state.py` coordinates supervisors and owns the workflow run state.

Responsibilities:

- start workflow
- pause/resume/stop
- supervisor registration/tracking
- branch spawning with max-depth enforcement from `ConfigurationManager`
- user input routing
- recovery action routing
- run completion detection
- output finalization through `OutputManager`
- run history recording
- event broadcasting

### Validator

`backend/validator.py` statically checks loaded workflows:

- exactly one start node
- registered node types
- connection targets/sources exist
- unreachable nodes as warnings

Errors block execution. Warnings are advisory.

### Error Handler

`backend/error_handler.py` creates structured error records with:

- id
- timestamp
- category
- message/type
- traceback
- run id
- node id
- branch id
- context

Errors are cached and persisted under `run_errors/`.

### Run History

`backend/run_history.py` persists completed/error run summaries under `run_history/`.

### Output Manager

`backend/output_manager.py` stores outputs by run id and persists finalized outputs under `run_outputs/`.

### Save Manager

`backend/save_manager.py` coordinates save/load/import/export/duplicate/delete/rename. UI code should prefer `SaveManager` over calling persistence directly.

### Configuration Manager

`backend/configuration_manager.py` loads and persists settings under `settings/settings.json`. `DEFAULT_SETTINGS` is the schema gatekeeper.

Current settings include:

- `max_branch_depth`
- `node_timeout_seconds`
- `auto_save_enabled`
- `auto_save_interval_seconds`
- `last_active_workflow_id`
- `default_workflow_name_prefix`
- `log_level`
- `log_to_file_enabled`
- `log_retention_days`

---

## Node Library

Current registered node types: 13.

Flow/control:

- `start_node`
- `end_node`
- `branch_node`
- `conditional_node`

I/O and user interaction:

- `text_output_node`
- `user_text_input_node`
- `file_reader_node`

AI placeholders:

- `chat_completion_node`
- `image_generation_node`
- `embedding_node`

Variables and utility:

- `set_variable_node`
- `get_variable_node`
- `concat_node`

### BranchNode

`branch_node` can:

- spawn both paths
- spawn path A only
- spawn path B only
- perform string-match routing using:
  - `match_value`
  - `match_mode`
  - `case_sensitive`
  - `on_match`
  - `on_no_match`

When it emits branches, `MasterState` spawns child supervisors.

### ConditionalNode

`conditional_node` chooses one output port on the same supervisor path. It does not spawn branch supervisors.

Supported condition types:

- `equals`
- `not_equals`
- `contains`
- `regex`

---

## Frontend Architecture

The implemented frontend is tkinter.

### App

`frontend/app.py` is the root `tk.Tk` window. It wires backend services, owns `UIState`, subscribes to backend events, starts `AsyncTkPump`, and swaps editor/execution panels by mode.

Startup behavior:

- attempts to load `last_active_workflow_id`
- otherwise creates an untitled workflow with a Start node

### Async Pump

`frontend/async_tk.py` lets tkinter and asyncio cooperate by periodically advancing an asyncio loop with `after(...)`.

### UI State

`frontend/ui_state.py` mirrors a small Zustand-style store:

- mode
- workflow run state
- current workflow id/name
- dirty state
- modal stack
- active supervisors
- selected supervisor
- validation status
- node statuses

### Toolbar

`frontend/toolbar.py` includes:

- workflow name/dirty indicator
- Workflow library
- Workflow Settings
- Save
- Run
- Errors badge
- Settings
- Help
- About
- New

### Editor Panel

`frontend/editor_panel.py` renders node cards vertically.

Implemented editor features:

- node click opens config
- delete buttons
- branch view dropdown under branch nodes
- bookmark markers
- validation highlighting
- scroll-to-node support

### Controls Panel

`frontend/controls_panel.py` is mode-aware.

Editor mode:

- Validate
- Save
- Load
- Add Node
- Run
- Jump To filter/list

Execution mode:

- Pause/Resume
- Stop
- supervisor selector
- View Memory
- View Output
- Run History

Workflow state is color-coded.

### Execution Panel

`frontend/execution_panel.py` renders the workflow with live node status highlighting for the selected supervisor.

### Modals

Implemented modals:

- node selector
- node config
- workflow library
- workflow settings
- settings
- user input
- memory viewer
- output viewer
- run history
- error details/recovery
- help
- about

Modal grab behavior uses `safe_grab()` to avoid WSL/tkinter “window not viewable” crashes.

---

## Signal Flow

### Start Workflow

1. UI calls `MasterState.start_workflow()`.
2. Master validates loaded state and start node.
3. Master generates `run_id`.
4. `MemoryBank` clears.
5. Root `Supervisor` is created and scheduled.
6. Supervisor publishes `SUPERVISOR_REGISTER`.
7. Master tracks it.
8. Master publishes `WORKFLOW_STATE_UPDATE`.

### Node Execution

1. Supervisor fetches node instance from `WorkflowMap`.
2. Supervisor prepares inputs from `MemoryBank.read_transient`.
3. Node executes with `NodeContext`.
4. Node calls `signal_done`, `signal_error`, or awaits user input.
5. Supervisor writes output data to transient memory.
6. Supervisor advances by:
   - explicit `next_node_id`
   - selected `output_port`
   - default output connection
   - branch spawn request

### User Input

1. Node awaits `context.signal_waiting_for_input(prompt)`.
2. Supervisor creates a future and publishes user-input events.
3. UI opens `UserInputModal`.
4. User submits.
5. Master routes value to the waiting supervisor.
6. Future resolves and node execution resumes.

### Branching

1. Node returns `branches`.
2. Supervisor resolves each branch output port to a target node.
3. Supervisor publishes `SUPERVISOR_REQUEST_BRANCH`.
4. Master checks max depth.
5. Master creates child supervisors.
6. Children run independently.

### Error Recovery

1. Node raises or signals error.
2. Supervisor logs through `ErrorHandler`.
3. Supervisor publishes recovery options.
4. UI opens `ErrorDetailsModal`.
5. User selects recovery action.
6. Master routes action to supervisor.
7. Supervisor retries, skips, terminates branch, or terminates workflow.

---

## Current Validation Commands

From `C:\Users\makin\OneDrive\Documents\node_workflow`:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_error_recovery.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_v09_managers.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_v095_nodes.py
```

To launch on Windows:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\main.py
```

To launch from WSL:

```bash
/mnt/c/Users/makin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe attackofthenodes_v05/main.py
```

If using WSL’s system Python instead, tkinter may need to be installed separately.

---

## Roadmap

### Implemented

- v0.5 backend proof of concept
- v0.6 UI foundation
- v0.7 execution UI
- v0.8 inspection/error recovery
- v0.9 workflow management and backend polish
- v0.95 extended node library and editor navigation
- v0.99 prototype surface features

### Deferred

- Real API integration via an `ApiManager`.
- Credential encryption.
- Real output-node semantics beyond current output log/output manager behavior.
- Merge node / branch recombination.
- Internal checkpointing and crash recovery.
- Full graph canvas with drag positioning and visual connection creation.
- Comprehensive pytest suite with coverage target.
- CI.
- Packaging as pip package or executable.

### v1.0 Direction

Replace placeholder AI node execute bodies with real API calls through a new `ApiManager`. The UI and workflow persistence shape should not need redesign for that swap.

---

## Key Architectural Decisions

- Backend remains UI-agnostic.
- Event bus mediates state changes and UI updates.
- Components keep strict single responsibilities.
- Supervisors execute paths; MasterState coordinates supervisors.
- MemoryBank is ephemeral working memory; OutputManager is durable run output storage.
- Workflow JSON is a compatibility contract.
- Loose/unreachable nodes are saved and loaded but not executed.
- Asyncio is the concurrency model; no threading is currently used.
- UI should call service/facade methods rather than reaching into persistence directly.

---

## Open Questions

- Whether to keep evolving tkinter or pivot to Textual later.
- How much of the original Chrome-extension architecture should be revived after the Python prototype matures.
- Exact `ApiManager` credential model and encryption UX.
- Whether output nodes should become distinct from `EndNode`/`TextOutputNode`.
- When to implement internal checkpointing and crash recovery.
- Whether branch recombination should use a `MergeNode` or a broader coordination primitive.

---

## How To Continue This Project

Start by reading this document, then inspect:

- `docs/V05_BUILD_PLAN.md` for implementation history.
- `docs/ARCHITECTURE.md` for the long-term conceptual architecture.
- `docs/SIGNAL_FLOW.md` for component interactions.

For backend work, preserve the component boundaries. For UI work, prefer adding adapter methods or frontend glue rather than changing backend contracts for convenience. For new nodes, follow the existing node pattern: metadata, ports, defaults, schema, async execute, registration in `ALL_NODE_CLASSES`, and a focused smoke test if behavior is nontrivial.

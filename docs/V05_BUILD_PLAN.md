# AttackOfTheNodes v0.5 Python Proof Of Concept Build Plan

This document is the implementation reference for the Python proof of concept. The goal is a minimal but architecturally faithful workflow engine that can build, save, load, and execute connected offline nodes.

## Philosophy

Preserve structure, simplify implementation. Components should keep their long-term responsibilities even when their v0.5 internals are small. Do not collapse `WorkflowSupervisor` into `WorkflowMasterState`, or persistence into workflow logic, just because the first workflow is linear.

## Technology

- Python 3.10 or later.
- tkinter for the UI.
- asyncio for node execution and supervisor loops.
- JSON files in `workflows/` for persistence.
- No third-party dependencies.

## Required v0.5 Shape

Backend:

- Node base and individual node classes.
- Node factory.
- Workflow map.
- Memory bank.
- Supervisor.
- Master state.
- Persistence.
- Simple validator.
- Simple structured error list.

Frontend:

- App window.
- Editor panel.
- Execution panel.
- Controls panel.
- Node card helper.
- Small modal set.
- Event bus connecting backend and frontend.

Simplified or deferred:

- `SaveManager` and `HandleUI` are folded into direct calls for v0.5.
- `OutputManager` is an in-memory list on `MasterState`.
- `Validator` is a simple function.
- `ErrorHandler` is a simple logger/list.
- No API manager, encryption, Chrome extension, service worker, auto-save, checkpointing, crash recovery, subworkflows, or multi-workflow cache.

## Target File Structure

```text
attackofthenodes_v05/
  main.py
  backend/
    __init__.py
    events.py
    event_bus.py
    node_base.py
    nodes/
      __init__.py
      start_node.py
      text_output_node.py
      branch_node.py
      end_node.py
    node_factory.py
    workflow_map.py
    memory_bank.py
    supervisor.py
    master_state.py
    persistence.py
    validator.py
  frontend/
    __init__.py
    app.py
    editor_panel.py
    execution_panel.py
    controls_panel.py
    node_card.py
    modals.py
    ui_state.py
  workflows/
```

## Phase 1 Scope

Phase 1 establishes the foundation:

- Persistence functions for workflow JSON.
- Event bus.
- Node base and `NodeContext`.
- Node factory.
- Registered node files.
- Concrete `StartNode`.
- Placeholder phase-2 nodes with metadata.
- A `main.py` smoke test that saves/loads a workflow, publishes an event, verifies factory registration, and validates a start node config.

## Acceptance Notes

At the end of phase 1, running `attackofthenodes_v05/main.py` should:

- Create `attackofthenodes_v05/workflows/` if absent.
- Save and load a test workflow.
- List available workflows.
- Publish and receive a test event.
- Register all four node types.
- Instantiate and validate a `StartNode`.

## Phase 2 Scope

Phase 2 adds the execution layer:

- `MemoryBank` with persistent and transient stores.
- `WorkflowMap` for one loaded workflow, node CRUD, connections, and execution lookups.
- `Supervisor` with an async graph-walking run loop.
- `MasterState` for run lifecycle, supervisor tracking, branching, pause/resume/stop, user input routing, and completion detection.
- `Validator` for start-node checks, registered node type checks, connection integrity, and loose-node warnings.
- Real execution behavior for `TextOutputNode`, `BranchNode`, and `EndNode`.
- `NodeContext.inputs`, populated by the supervisor before each node executes.
- `main.py` Phase 2 demo.
- `test_execution.py` acceptance scenarios for linear execution, user input, and branching.

Phase 2 has been validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\main.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
```

## Phase 3 Scope

Phase 3 adds the first tkinter UI layer:

- `frontend/ui_state.py` for centralized UI state.
- `frontend/app.py` for the main window, toolbar, backend wiring, and mode switching.
- `frontend/editor_panel.py` for a scrollable vertical node-card editor.
- `frontend/controls_panel.py` for Validate, Save, Load, and Add Node actions.
- `frontend/node_card.py` for canvas-rendered node cards.
- `frontend/modals.py` for node selection, node config editing, and workflow loading.
- `frontend/execution_panel.py` as a placeholder for Phase 4 live execution UI.
- `main.py` now launches the Phase 3 tkinter editor.
- `demo_execution.py` preserves the command-line Phase 2 execution demo.

Phase 3 editor behavior:

- Starts with an untitled workflow containing a Start node.
- Add Node opens the node selector modal.
- Added nodes are auto-connected to the current linear tail when possible.
- Clicking a node opens the config modal.
- Validate runs the backend validator and reports errors/warnings.
- Save writes the current workflow JSON through `WorkflowMap`.
- Load opens a saved workflow list from the workflows directory.

Phase 3 has been validated without launching a GUI display by compiling the package
and re-running backend execution checks:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\demo_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
```

To launch the UI locally:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\main.py
```

## Phase 4 Scope

Phase 4 connects the tkinter UI to the async execution layer:

- `App` now owns an asyncio loop and pumps it from tkinter with `after(...)`.
- The Controls panel is mode-aware:
  - Editor mode: Validate, Save, Load, Add Node, Run.
  - Execution mode: Pause/Resume, Stop, Supervisor selector.
- The Run action validates the workflow and starts `MasterState.start_workflow()`.
- The Pause/Resume and Stop actions call through to `MasterState`.
- `App` subscribes to supervisor lifecycle events:
  - `SUPERVISOR_REGISTER`
  - `SUPERVISOR_STATE_UPDATE`
  - `SUPERVISOR_TERMINATING`
  - `USER_INPUT_NEEDED`
  - `ERROR_OCCURRED`
- `ExecutionPanel` now renders workflow nodes and highlights statuses:
  - `running`
  - `waiting`
  - `done`
  - `error`
  - `idle`
- `UserInputModal` opens when a node calls `signal_waiting_for_input`.
- Supervisor selection updates the execution panel label and current branch focus.

Phase 4 has been validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import sys; sys.path.insert(0, 'attackofthenodes_v05'); import frontend.app, frontend.execution_panel, frontend.controls_panel, frontend.modals; print('frontend imports ok')"
```

## Phase 5 Scope

Phase 5 completes the v0.5 proof of concept inspection layer:

- `MemoryViewerModal` shows the `MemoryBank` persistent and transient stores.
- The memory viewer subscribes to `MEMORY_UPDATE` and refreshes while open.
- `OutputViewerModal` shows final run output lines.
- `MasterState` snapshots `output_log` into `run_outputs` when all supervisors finish.
- Controls panel includes `View Memory` and `View Output`.
- The app opens memory and output viewers from both editor and execution modes.

Phase 5 has been validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\demo_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import sys; sys.path.insert(0, 'attackofthenodes_v05'); import frontend.app, frontend.modals, frontend.controls_panel; print('frontend imports ok')"
```

At this point v0.5 has all planned proof-of-concept phases:

- Phase 1: foundation.
- Phase 2: backend execution.
- Phase 3: workflow editor UI.
- Phase 4: execution UI wiring.
- Phase 5: memory/output inspection.

## Textual TUI Spinoff Status

The project pivoted from the tkinter UI to a Textual terminal UI. The original
backend phase work remains intact; the new frontend lives under
`attackofthenodes_v05/frontend/screens/`, `frontend/widgets/`, and
`frontend/styles.tcss`.

Checked off:

- Textual app shell launches from `main.py`.
- Editor screen renders the active workflow path.
- Node selector modal adds nodes.
- Node config modal edits alias and schema-driven config fields.
- Multi-output nodes render an editor-level `Branch Select` row.
- Branch selector switches the visible branch path without deleting hidden
  branch nodes.
- Adding nodes keeps focus on the newly added node and inserts into the visible
  path when needed.
- Execution screen starts runs, displays status, and can stop/return to editor.
- User input, memory, output, error recovery, workflow library, settings, and
  help modal screens are wired.
- Workflow library supports local load, new, duplicate, and delete.
- Workflow delete, dirty workflow load, and dirty new-workflow actions now ask
  for confirmation before discarding data.
- Execution recent output now uses a `RichLog` scrollback widget with markup
  disabled.
- Node config now supports connection editing through remove controls and
  input/output endpoint selectors.
- Workflow library supports JSON import/export through path prompt modals.
- Editor now exposes `I` as an explicit insert shortcut, using the same
  downstream-preserving insertion behavior as the smart add path.
- Editor validation is available with `V`; validation errors and warnings render
  as structured cards with node id, issue type, description, and jump-to-node
  actions.
- Settings persist through `ConfigurationManager`.

Still to add or harden:

- Richer file-picker ergonomics for import/export paths if direct path entry
  becomes too limiting.

## v0.6 Roadmap Alignment

The v0.6 Basic UI Foundation roadmap has been formalized in code while
preserving later prototype features already present:

- Added `frontend/async_tk.py` as the single tkinter/asyncio integration shim.
- Expanded `frontend/ui_state.py` with `UI_STATE_CHANGED`, modal stack state, and setter methods.
- Added `frontend/toolbar.py` for the persistent top toolbar.
- Refactored the old monolithic `frontend/modals.py` file into a package:
  - `frontend/modals/node_selector.py`
  - `frontend/modals/node_config.py`
  - `frontend/modals/workflow_library.py`
  - `frontend/modals/user_input.py`
  - `frontend/modals/memory_viewer.py`
  - `frontend/modals/output_viewer.py`
- Added v0.6 connection editing to `NodeConfigModal`:
  - output-port dropdowns for connecting to another node
  - existing connection list
  - disconnect buttons
- Added `WorkflowMap.disconnect(...)`.
- Updated `App` to use `AsyncTkPump`, `Toolbar`, and the modal package.

Validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import sys; sys.path.insert(0, 'attackofthenodes_v05'); import frontend.app, frontend.async_tk, frontend.toolbar; from frontend.modals import NodeConfigModal, WorkflowLibraryModal; print('v0.6 imports ok')"
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\demo_execution.py
```

## v0.7 Roadmap Alignment

The v0.7 Execution UI roadmap has been aligned with the current prototype:

- `ExecutionPanel` now includes its own supervisor dropdown at the top.
- Supervisor dropdown entries show `branch_id @ current_node`.
- Selecting a supervisor updates `UIState.selected_supervisor_id`.
- `ControlsPanel` now has a dedicated workflow state label.
- Workflow states are color-coded:
  - gray: `IDLE`
  - blue: `RUNNING`
  - yellow: `PAUSED` and `WAITING_FOR_INPUT`
  - green: `FINISHED`
  - red: `ERROR`
- User input prompts are queued so only one `UserInputModal` is open at a time.
- Closing/canceling a user input modal submits an empty string so the supervisor unblocks.
- The existing Run/Pause/Resume/Stop wiring remains active through `MasterState`.

Validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import sys; sys.path.insert(0, 'attackofthenodes_v05'); import frontend.app, frontend.execution_panel, frontend.controls_panel; print('v0.7 imports ok')"
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
```

## v0.8 Roadmap Alignment

The v0.8 Inspection and Error Handling milestone has been started and the core
recovery path is implemented:

- Added `backend/error_handler.py`.
  - Structured error records include id, timestamp, category, message, type,
    traceback, run id, node id, branch id, and context.
  - Errors are persisted under `run_errors/`.
  - `ERROR_LOGGED` and `ERRORS_CLEARED` events are published.
- Added `backend/run_history.py`.
  - Completed/error run summaries are persisted under `run_history/`.
  - Summaries include workflow identity, run id, timestamps, final state,
    error count, output count, and outputs.
- Added recovery events and supervisor state:
  - `RECOVERY_OPTIONS_AVAILABLE`
  - `TERMINATE_WORKFLOW_REQUESTED`
  - `SupervisorState.AWAITING_RECOVERY`
- `Supervisor` now supports recoverable node errors.
  - Logs the error through `ErrorHandler`.
  - Publishes recovery options.
  - Waits for a recovery action.
  - Supports `RETRY`, `SKIP`, `TERMINATE_BRANCH`, and `TERMINATE_WORKFLOW`.
- `MasterState` now exposes:
  - `submit_recovery_action(branch_id, action)`
  - `error_handler`
  - `run_history`
- Added frontend modals:
  - `frontend/modals/error_details.py`
  - `frontend/modals/run_history.py`
- Toolbar now has an error-count badge button.
- Controls panel now has a Run History button.
- Added `test_error_recovery.py` to exercise the recovery flow.

Validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_error_recovery.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import sys; sys.path.insert(0, 'attackofthenodes_v05'); import frontend.app; from frontend.modals import ErrorDetailsModal, RunHistoryModal; print('v0.8 imports ok')"
```

## Conditional Branching Update

`BranchNode` now supports string-match conditional routing in addition to the
older manual branch modes.

Config fields:

- `condition`: `string_match`, `always_branch`, `path_a_only`, or `path_b_only`.
- `match_value`: string compared against the incoming `input`.
- `match_mode`: `equals` or `contains`.
- `case_sensitive`: boolean.
- `on_match`: `path_a` or `path_b`.
- `on_no_match`: `path_a` or `path_b`.

Behavior:

- Reads the previous node output from `context.inputs["input"]`.
- Converts it to a string.
- Compares it to `match_value`.
- Spawns only the configured matching or non-matching output port.

The config modal now renders schema fields with `options` as dropdowns, making
branch setup less typo-prone in the UI.

Validated with two new acceptance scenarios:

- matching input routes only to `on_match`.
- non-matching input routes only to `on_no_match`.

## v0.9 Architectural Polish

The v0.9 service extraction and workflow management slice is complete:

- Added `backend/configuration_manager.py`.
  - Settings are persisted under `settings/settings.json`.
  - `DEFAULT_SETTINGS` constrains valid keys.
  - `max_branch_depth` now drives branch-depth enforcement in `MasterState`.
- Added `backend/output_manager.py`.
  - Run outputs are collected by run id.
  - Finalized outputs are persisted under `run_outputs/`.
  - `MasterState` now finalizes output through `OutputManager`.
- Added `backend/save_manager.py`.
  - Coordinates current workflow save/load.
  - Supports optional memory-state save/load.
  - Supports import/export helpers.
  - Updates `last_active_workflow_id` through `ConfigurationManager`.
- Updated `WorkflowMap`.
  - Added `load_data(...)`.
  - Added `get_workflow_data_for_save()`.
  - Added `mark_saved()`.
- Updated app construction to pass:
  - `ConfigurationManager`
  - `OutputManager`
  - `SaveManager`
- UI save/load now routes through `SaveManager` when available.
- Added `frontend/modals/settings.py`.
  - Edits persisted global settings.
  - Numeric, boolean, and string settings render with appropriate controls.
- Added `frontend/modals/workflow_settings.py`.
  - Rename, duplicate, export, and delete actions for the active workflow.
- Expanded `frontend/modals/workflow_library.py`.
  - Load, delete, duplicate, export, import, and switch between open workflows.
- Updated `WorkflowMap`.
  - Maintains an in-memory cache of open workflows keyed by workflow id.
  - Tracks dirty state per cached workflow.
  - Supports switching and closing cached workflows.
- Added optional auto-save from `App`, controlled by settings.
- Startup now attempts to load `last_active_workflow_id`.

Validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q attackofthenodes_v05
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_execution.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_error_recovery.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_v09_managers.py
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import sys; sys.path.insert(0, 'attackofthenodes_v05'); from backend.configuration_manager import ConfigurationManager; from backend.output_manager import OutputManager; from backend.save_manager import SaveManager; import frontend.app; print('v0.9 manager imports ok')"
```

## v0.95 Extended Node Library And Editor Enhancements

The v0.95 feature slice is implemented in proof-of-concept form:

- Added placeholder AI-style nodes:
  - `chat_completion_node`
  - `image_generation_node`
  - `embedding_node`
- Added workflow utility nodes:
  - `set_variable_node`
  - `get_variable_node`
  - `concat_node`
  - `conditional_node`
  - `user_text_input_node`
  - `file_reader_node`
- Added bookmark support:
  - `WorkflowMap.set_bookmark(...)`
  - node config bookmark checkbox
  - star marker on node cards
- Added Jump To navigation in the controls panel.
  - Filters: all, start, branches, bookmarks, outputs.
- Added validation highlighting in the editor panel.
  - Error nodes show red card state.
  - Warning nodes show yellow card state.
- Existing branch node view selector remains available under branch nodes.

Validated with:

```powershell
C:\Users\makin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe attackofthenodes_v05\test_v095_nodes.py
```

Notes:

- Visual connections remain intentionally simple vertical/branch-aware lines.
  Full draggable Bezier graph editing remains future work.
- The AI-style nodes are placeholders by design; v1.0 replaces their execute
  bodies with real API calls.

## v0.99 Production Readiness Surface

The v0.99 readiness slice is implemented for the local prototype:

- Session startup loads the last active workflow when present.
- Keyboard shortcuts are wired:
  - Ctrl+S save
  - Ctrl+R run
  - Ctrl+Shift+R stop
  - Ctrl+N new workflow
  - Ctrl+O / Ctrl+L workflow library
  - Escape closes the focused modal/window
- Added in-app help and about modals:
  - `frontend/modals/help.py`
  - generated node type reference
  - shortcuts and troubleshooting tabs
- Logging is configured from settings:
  - console warnings and above
  - optional rotating log file under `logs/`
  - configurable log level and retention settings
- Added focused smoke tests for v0.9 and v0.95.

Still intentionally deferred beyond the local prototype:

- Real API credential encryption and API dispatch.
- PyInstaller/pip packaging.
- Full pytest coverage target and CI wiring.
- Drag-to-position graph editing and full connection editor canvas.

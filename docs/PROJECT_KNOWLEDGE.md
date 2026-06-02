# AttackOfTheNodes Project Knowledge

**Purpose:** current-state reference for collaborators and future agents.
For implementation order and roadmap status, prefer `MASTER_BUILD_PLAN.md`.
For latest completed work, prefer `SESSION_LOG.md`.

## Current State

AttackOfTheNodes is a Python workflow engine with a Textual terminal UI. The
active app lives in `attackofthenodes_v05/`. The older Chrome-extension,
JavaScript, and tkinter designs are historical only.

The backend is a reusable workflow engine. It owns workflow structure,
validation, execution, branching, run state, memory, outputs, errors, settings,
and JSON persistence. It must not import from `frontend/`.

The frontend is a Textual control room. It owns editor presentation, command
navigation, modal screens, visual tombstones, notifications, and other
UI-specific adapter behavior.

## Runtime And Entry Point

- Python: 3.12+ (`pyproject.toml`), currently exercised on Python 3.14.
- UI: Textual 8.2.x.
- Execution: asyncio supervisors and in-process event bus.
- Persistence: local JSON folders under `attackofthenodes_v05/`.
- Start app: from `attackofthenodes_v05/`, run `../.venv/bin/python main.py`
  or activate the venv and run `python main.py`.
- Main tests: `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v`.

## Mental Model

A workflow is a directed graph of nodes. Execution starts at a Start node and a
`Supervisor` walks the graph. Branch-capable nodes can request multiple branch
supervisors through `MasterState`. All supervisors in one run share one
`MemoryBank`. Nodes receive prepared inputs and a `NodeContext`; they do not
inspect frontend state.

Merge behavior is editor-assisted and runtime-coordinated:

- Branch nodes expose branch paths such as `path_a`, `path_b`, etc.
- Branch labels are user-configurable and displayed in the editor.
- Branch End nodes mark branch completion points. They show red while open and
  green when their `default` output connects to a Merge node.
- Merge config chooses branches to close and one selected branch output to carry
  forward.
- The Textual editor adapter repairs legacy `Merge.input` connections into the
  correct branch path input (`path_a` through `path_e`) when refreshing older
  saves.

## Backend Components

- `backend/persistence.py`: raw JSON file I/O. It does not interpret workflow
  semantics.
- `backend/configuration_manager.py`: settings cache and schema guard using
  `DEFAULT_SETTINGS`.
- `backend/workflow_map.py`: active workflow cache, node CRUD, connections,
  dirty tracking, traversal helpers, serialization, tombstone swaps, and
  breakpoint flags.
- `backend/node_factory.py`: registry of node classes, default configs, and
  metadata.
- `backend/node_base.py`: `Node`, `NodeContext`, metadata validation, config
  schema contract, category support, and runtime callbacks.
- `backend/memory_bank.py`: per-run persistent variables and transient port
  data.
- `backend/output_manager.py`: collects durable outputs and evicts per-run
  in-memory output data during finalization.
- `backend/error_handler.py`: structured per-run errors and run cleanup.
- `backend/run_history.py`: capped in-memory run summaries plus durable JSON.
- `backend/supervisor.py`: executes one graph path, handles pause/stop,
  breakpoints, user input, recovery, branch requests, node timings, and
  completion callbacks.
- `backend/master_state.py`: starts/stops runs, coordinates supervisors,
  handles branch spawning, merge arrivals, WaitUntil completions, global pause,
  user input, output/error finalization, and run history.
- `backend/save_manager.py`: save/load/delete/duplicate/import/export workflow
  orchestration and derived `input_sources`.
- `backend/validator.py`: static checks for start node, node types,
  connection endpoints, declared ports, tombstones, derived input sources,
  membank declarations, and unreachable warnings.
- `backend/utils/try_catch.py`: Go-style async result/error helper for new async
  UI paths.

## Frontend Components

- `frontend/app.py`: Textual root app, backend event subscription, global key
  commands, workflow file actions, run routing, and modal orchestration.
- `frontend/screens/editor.py`: workflow editor, branch path display, node
  add/insert/delete/config, validation, tombstone replacement, breakpoint
  toggles, merge connection repair, and branch-end display state.
- `frontend/screens/execution.py`: live run view, run state indicator, node
  statuses/timings, memory/output/error/user-input modals, and recent output
  scrollback.
- `frontend/screens/node_config.py`: command-mode node config editor, generated
  schema fields, memory-bank I/O sections, wait target selection, merge branch
  selection, and topology-derived previews.
- `frontend/screens/node_selector.py`: add/insert node type selector with
  filter input.
- `frontend/screens/branch_selector.py`: active branch path selector.
- `frontend/screens/workflow_library.py`: workflow load/new/duplicate/delete
  plus import/export path prompts.
- `frontend/screens/settings.py`: settings editor.
- `frontend/screens/user_input.py`: runtime input prompt.
- `frontend/screens/memory_viewer.py`, `output_viewer.py`, `error_details.py`,
  `help.py`, `confirm.py`: viewer and modal support screens.
- `frontend/widgets/command_input.py`: command-first text input and text area.
- `frontend/widgets/command_navigation.py`: shared command modal focus,
  activation, dropdown, edit-mode, and scroll-to-focus helpers.
- `frontend/widgets/list_navigation.py`: shared list selector highlight/move
  helpers.
- `frontend/widgets/dynamic_sections.py`: checkbox/count-driven config section
  helpers.
- `frontend/widgets/form_generator.py`: node config schema to Textual widgets.
- `frontend/widgets/node_list.py` and `node_card.py`: editor/execution node row
  rendering.
- `frontend/notifications.py`: standard user-facing notification copy.

## Node Metadata Contract

New nodes should be supported by metadata and schema before custom frontend
logic is added:

- `node_type`
- `display_name`
- `description`
- `category`
- `input_ports`
- `output_ports`
- `default_config`
- `config_schema`
- optional `ui_hints`

The form generator supports text, number, boolean, select, multiselect,
multiline, code-like fields, placeholders, validators, height hints, grouped
tabs, and branch-label fields for multi-output nodes.

## Registered Node Families

- Flow: Start, End, Branch, Branch End, Conditional, Merge, Wait Until.
- Data: Set Variable, Get Variable, Concat, debug variable setter/reader.
- IO: Text Output, User Text Input, File Reader.
- AI placeholders: Chat Completion, Image Generation, Embedding.
- Debug/utility: Tombstone, Echo, Logger, Sleep, Counter, Memory Snapshot,
  Probe, Error, Random Branch, Deep Branch, No Op, Repeat Counter.

## Current UI Rules

- Command-mode modals use `W/S` and arrows for navigation, `E`/Enter to
  activate, and `Esc`/`Ctrl+Q` to leave edit/dropdown mode before closing.
- Text fields enter typing mode on click. Generated config fields still require
  activation when reached by keyboard unless a screen opts into
  `auto_edit_on_focus`.
- Screen-level letter bindings that must work while a list has focus use
  `Binding(..., priority=True)`.
- Node editor mouse behavior: one click selects; two clicks opens config or
  branch selector.
- Node config screens should be schema-generated except for topology-derived
  structural sections such as merge branch selection and wait target selection.
- Backend behavior should not be added solely to make Textual presentation
  easier; frontend adapters own those repairs and visuals.

## Runtime Data

Runtime JSON is stored under the app package:

- `workflows/`
- `settings/`
- `run_history/`
- `run_outputs/`
- `run_errors/`
- `logs/`

These are operational data folders, not source architecture.

## Open Cleanup Areas

- Phase 10.5 backend/frontend boundary cleanup: migrate editor tombstones away
  from backend execution concepts.
- Frontend audit phases FA-6/FA-7: viewer long-content safety and visual/help
  alignment.
- Branch health visualization: distinguish valid branch endings, unmerged
  Branch End markers, and floating branches.
- Later UI phases: cursor model, key remap, editor rework, file modal/config
  tabs, visual identity, acceleration/help rewrite.

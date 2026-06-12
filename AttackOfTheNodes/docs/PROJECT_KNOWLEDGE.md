# AttackOfTheNodes Project Knowledge

**Purpose:** current-state reference for collaborators and future agents.
For implementation order and roadmap status, prefer `MASTER_BUILD_PLAN.md`.
For latest completed work, prefer `SESSION_LOG.md`.

## Current State

AttackOfTheNodes is a Python workflow engine with a Textual terminal UI. The
active app lives in `AttackOfTheNodes/`. The older Chrome-extension,
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
- Persistence: local JSON folders under `AttackOfTheNodes/`.
- Start app: from `AttackOfTheNodes/`, run `../.venv/bin/python main.py`
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
- Merge Beacon nodes mark branch completion points. They show red while open and
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
- `backend/run_session.py`: per-run resource session created by `MasterState`
  and threaded through `NodeContext` as `context.run_session`. Holds open file
  handles and AI session handles keyed by a string reference. API:
  `open_file(path, mode)`, `register_resource(key, handle, close_hook)`,
  `get_resource(key)`, `validate_path(path)`, `close_all()`.
  Typed vault references (type `file` or `ai_session`) carry a reference key
  that nodes resolve through `get_resource`.
- `backend/utils/try_catch.py`: Go-style async result/error helper for new async
  UI paths.

## Data Flow Patterns

**Transient payloads** are JSON values written to `MemoryBank` keyed by
`(source_node_id, port_name)` after each node executes. The `Supervisor`
reads them back when preparing inputs for the next node. They are scoped to
one run and do not survive between runs.

**Vault (MemoryBank persistent store)** holds named JSON values readable by
any node in any branch. Every vault entry carries a `type` field alongside
its value. Simple types (`string`, `number`, `boolean`) are pure JSON values.
Typed handle entries (`file`, `ai_session`) store the type tag and a string
reference key; the actual Python handle lives in `RunSession` and is retrieved
with `context.run_session.get_resource(ref_key)`. Input source dropdowns
filter by declared type, so a `file` input only shows `file` vault entries.

**RunSession handles** are Python objects (file handles, AI provider sessions)
that cannot be JSON-serialized. They live in `RunSession`, which is created
fresh per run by `MasterState` and closed on every terminal path. Nodes
access handles through `context.run_session`. Workflow saves store only
portable strings (file paths, session key names); handles are reconstructed at
runtime.

**AI session continuation** uses config-driven vault output on any LLM node
that opts in. The first node with a given session key starts the session and
writes an `(type: ai_session, ref_key: <key>)` vault entry. Downstream LLM
nodes that select the same vault key retrieve the session from `RunSession` and
append their turn. Message history accumulates in the session object in
`RunSession`; `MemoryBank` holds only the reference key.

## Frontend Components

- `frontend/app.py`: Textual root app, backend event subscription, global key
  commands, workflow file actions, run routing, and modal orchestration.
- `frontend/screens/editor.py`: workflow editor, branch path display, node
  add/insert/delete/config, validation, tombstone replacement, breakpoint
  toggles, merge connection repair, and Merge Beacon display state.
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
- Phase 17 planned identity metadata: primary family, subcategory tags,
  `icon_name`, and `color_hint`

The form generator supports text, number, boolean, select, multiselect,
multiline, code-like fields, placeholders, validators, height hints, grouped
tabs, and branch-label fields for multi-output nodes.

Current implementation note: `Node` defines optional `icon_name`, `tags`, and
`color_hint`, but `NodeFactory.get_node_types_metadata()` does not yet expose
category/tag/icon/color fields. Phase 17 should expose portable identity
metadata before the frontend selector depends on it.

## Registered Node Families

- Flow: Start, End, Branch, Merge Beacon, Conditional, Merge, Wait Until.
- Data: Set Variable, Get Variable, Concat, debug variable setter/reader.
- IO: Text Output, User Text Input, File Reader.
- AI placeholders: Chat Completion, Image Generation, Embedding.
- Debug/utility: Tombstone, Echo, Logger, Sleep, Counter, Memory Snapshot,
  Probe, Error, Random Branch, Deep Branch, No Op, Repeat Counter.

## Planned Node Taxonomy

Phase 17 introduces user-facing primary families for the upcoming node overhaul:

- Inputs: external-source inputs such as text in, file read, web scrape, and
  user text input.
- Flow Control: branch, conditional branch, merge, wait, loop, and branch-shape
  nodes.
- Outputs: user-facing or durable workflow outputs, including branch-ending
  outputs.
- Complex: nested workflows and unique nodes that do not fit the other
  families cleanly.

Nodes can also carry multiple subcategories such as Triggered, File I/O,
Internet, AI, Passive Output, Active Output, Parallel, Conditional, Runtime
Resource, and Utility. Selector filters and editor row identity should use this
metadata without changing runtime semantics.

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
  Merge Beacon markers, and floating branches.
- Phase 17: node visual identity and selector taxonomy.
- Later UI phases: acceleration/help rewrite.

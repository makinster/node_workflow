# AttackOfTheNodes Comprehensive Build Plan

**Last updated:** 2026-06-08
**Project root:** `AttackOfTheNodes/`
**Runtime:** Python 3.14, Textual 8.2.7, asyncio, JSON persistence
**Current branch context:** Textual TUI spinoff; tkinter frontend is obsolete.

This is the active build plan and handoff source for the project. It merges the
current phase plan, the Textual TUI design notes, the agent working rules, and
the older architecture docs into one current-state reference.

Start with `docs/README.md` for the documentation map. The current reference
docs have been refreshed for the Python/Textual build; `V05_BUILD_PLAN.md`
remains historical proof-of-concept history. When documents conflict, prefer
this file, then `docs/AGENT_HANDOFF.md`, then `docs/SESSION_LOG.md`, then
`docs/TUI_DESIGN.md`.
For frontend-specific audit and standardization work, also read
`docs/FRONTEND_AUDIT_BUILD_PLAN.md`. Before backend changes motivated by UI
behavior, read `docs/BACKEND_FRONTEND_BOUNDARY.md`.

---

## 1. Current Mental Model

Think of AttackOfTheNodes as a factory floor with a control room:

- The backend is the factory floor. Nodes are machines arranged in directed
  workflows, and supervisors walk execution paths through those nodes.
- The frontend is the control room. It displays workflow structure, execution
  state, memory, outputs, errors, settings, and editing surfaces.
- A workflow is a recipe: nodes plus connections. Execution starts at a start
  node, follows output connections, and can fork into multiple supervisors.
- All supervisors in a run share one `MemoryBank` and report back through
  `WorkflowMasterState` and the event bus.

The active frontend is Textual. The old tkinter modules and any older
browser/IndexedDB/HandleUI references are historical only.

---

## 2. Active Architecture

### Backend

- `backend/persistence.py`: local JSON persistence for workflows, settings,
  run history, run outputs, and run errors.
- `backend/configuration_manager.py`: settings cache and schema gatekeeper.
- `backend/workflow_map.py`: live workflow cache, node CRUD, connection
  operations, dirty tracking, traversal helpers, and save serialization.
- `backend/node_factory.py`: executable node registry and config templates.
- `backend/node_base.py`: `Node`, `NodeContext`, metadata validation, config
  schema contract, and node category support.
- `backend/memory_bank.py`: per-run persistent variables and transient port
  data.
- `backend/output_manager.py`: durable output collection and finalization.
- `backend/supervisor.py`: one execution path through the graph.
- `backend/master_state.py`: run coordinator, branch spawning, global pause,
  user input routing, run completion, and run history recording.
- `backend/save_manager.py`: assembles complete workflow save/export data.
- `backend/validator.py`: preflight validation and derived input-source checks.
- `backend/error_handler.py`: structured error logging and run cleanup.
- `backend/field_types.py` and `backend/node_category.py`: shared schema and
  node-classification constants.

Backend code must stay UI-agnostic. Do not import from `frontend/`.

### Frontend

The live UI is a Textual app:

```text
frontend/
  app.py
  styles.tcss
  ui_state.py
  screens/
    editor.py
    execution.py
    branch_selector.py
    node_selector.py
    node_config.py
    confirm.py
    workflow_library.py
    user_input.py
    memory_viewer.py
    output_viewer.py
    error_details.py
    settings.py
    help.py
  widgets/
    form_generator.py
    node_list.py
    node_card.py
    status_bar.py
```

Frontend code adapts to backend services through screen-level adapters and
widgets. UI convenience belongs in the frontend unless there is a genuine engine
capability missing.

### Execution Flow

1. Load or create a workflow in `WorkflowMap`.
2. Validate structure with `validator.py`.
3. Start a run through `WorkflowMasterState`.
4. Root `WorkflowSupervisor` starts at the start node.
5. Supervisors prepare node inputs from transient memory and branch data.
6. Nodes execute and signal completion, error, wait, or branches.
7. Branching nodes request branch supervisors through master state.
8. Nodes write transient data and optional memory-bank outputs.
9. Output nodes and end nodes feed run output records.
10. Master state finalizes output, errors, and run history when supervisors end.

---

## 3. Standing Instructions

Before coding:

1. Read `docs/README.md`.
2. Read `docs/AGENT_HANDOFF.md`.
3. Read `docs/SESSION_LOG.md` for the latest completed phase.
4. Read the phase-specific docs:
   - Frontend work: `docs/TUI_DESIGN.md`.
   - Frontend audit/standardization work:
     `docs/FRONTEND_AUDIT_BUILD_PLAN.md`.
   - Backend/frontend boundary work:
     `docs/BACKEND_FRONTEND_BOUNDARY.md`.
   - Engine work: this file plus the relevant backend modules.
   - Docs modernization: `docs/PROJECT_BACKLOG.md`.

While coding:

- Keep backend and frontend boundaries strict.
- Do not add backend behavior purely for Textual editor convenience. Use
  frontend adapters/helpers for visual placeholders, focus/navigation, list
  compaction, notifications, and other presentation-only behavior.
- Use `backend.utils.try_catch.try_catch` for new async UI/event paths.
- Textual screen-level letter actions that must fire while a list has focus use
  `Binding(..., priority=True)`.
- Text-heavy modals should avoid single-letter close/save bindings. Prefer
  `Esc`, `Ctrl+S`, `Ctrl+Enter`, and visible buttons.
- New node UI must start from the node class metadata: `input_ports`,
  `output_ports`, `default_config`, `config_schema`, optional `ui_hints`, and
  optional `category`. Add a frontend helper/schema extension before writing a
  one-off node config screen.
- Command-mode modals should use shared widgets/helpers (`CommandInput`,
  `CommandTextArea`, `command_navigation.py`, `form_generator.py`) instead of
  duplicating focus, dropdown, and activation logic.
- Do not dual-maintain derived graph metadata. Derive it from connections and
  node config at save/validate time.
- Keep modules concise. Validation is the safety net; avoid heavy runtime
  coupling unless a phase explicitly calls for it.

After coding, from `AttackOfTheNodes/` with the venv active:

```bash
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```

If normal pytest capture fails in this WSL/OneDrive workspace, keep
`pytest.ini` configured with `addopts = -s`.

Append a short entry to `docs/SESSION_LOG.md` for every phase or notable patch.

---

## 4. Current Status

| Phase | Title | Status |
|---|---|---|
| 0 | Memory leak fixes | Done |
| 1 | Forward-reachability helper | Done (`dfafea1`) |
| 2 | Dependency list + validation | Done (`38969a7`) |
| 3 | Membank I/O + registry + descriptions | Done (`9fa1b2a`) |
| 4 | Delete + insert nodes | Done (`51f9a74`) |
| 4.5 | Config modal and selector usability | Done (`0d53c04`) |
| 5 | Config tabs | Done |
| 5.5 | Keyboard nav hardening + config modal UX | Done |
| 6 | Breakpoints | Done |
| 7 | Per-node execution timing | Done |
| 8 | Completion registry + wait-until node | Done |
| 9 | Merge dynamic list + lineage barrier | Done |
| FA-0 | Frontend source audit + risk map | Done |
| FA-1 | Shared command modal foundation | Done |
| FA-2 | Selector list navigation standardization | Done |
| FA-3 | Schema generator expansion | Done |
| FA-4 | Dynamic config section helpers | Done |
| FA-5 | Notification helper | Done |
| 10 | Documentation modernization | Done |
| 10.5 | Backend/frontend boundary cleanup | Done |
| 11 | Real AI node execution | Deferred |
| 12 | Packaging and release hardening | Deferred |
| 13 | Cursor model foundation | Done |
| 14 | Key binding remap | Done |
| 15 | Editor rework | Done |
| 16 | File modal + node config tabs | In Progress |
| 17 | Node visual identity | Planned |
| 18 | Acceleration + help rewrite | Planned |
| 19 | Nested workflows: built-in subworkflow node | Planned |
| 20 | Nested workflows: user-created subworkflows | Planned |

Sequencing:

- Phases 10, 10.5, 13, 14, and 15 are complete. Phase 16 is in progress.
- Phase 17 can proceed after 14/15.
  Phase 18 depends on 13–17. Phases 19–20
  depend on Phase 9 and each other.

---

## 5. Completed Work Reference

### Phase 0 — Memory Leak Fixes

- `output_manager.finalize_run()` clears per-run in-memory outputs.
- `error_handler.finalize_run(run_id)` clears per-run error state.
- `master_state._record_run()` no longer duplicates large output payloads in
  run history and finalizes error state.
- `run_history` caps in-memory runs at `_MAX_IN_MEMORY = 500`.
- Four leak-regression tests were added.

### Phase 1 — Forward Reachability

- Added `WorkflowMap.nodes_reachable_from(node_id) -> set[str]`.
- Traverses output connections forward.
- Excludes the starting node.
- Ignores missing targets; validation reports broken references separately.
- Handles cycles and self-loops safely.
- Covered by focused branching/cycle regression tests.

### Phase 2 — Dependency List + Validation

- Save/export/duplicate derive `input_sources` from incoming node connections
  and defensive reads of `config["membank_inputs"]`.
- `validator.py` flags missing derived node sources and undeclared membank
  inputs.
- Connections and config remain the source of truth.

Example saved shape:

```python
"input_sources": [
    {"type": "node", "source_id": "node_A", "port": "default"},
    {"type": "membank", "source_id": "session_id"}
]
```

### Phase 3 — Membank I/O + Registry

- `NodeConfigScreen` manages memory-bank outputs and inputs separately from core
  schema config.
- `membank_outputs` stores id plus description records.
- `membank_inputs` stores selected ids.
- Registry scans declared outputs across the workflow.
- Input dropdown filters downstream-only writers with
  `nodes_reachable_from(current_node)`.
- Port-edge mutation moved out of config modal.

Example config:

```python
"membank_outputs": [{"id": "user_name", "description": "Name entered by user"}],
"membank_inputs": ["session_id"]
```

### Phase 4 — Delete + Insert Nodes

- `A` adds at the visible tail or selected branch path.
- `I` inserts immediately after the highlighted node or active branch row.
- Insert rewires `source -> old_target` into `source -> new -> old_target`.
- Delete no longer cascades branch subtrees.
- Tombstones remain as the visual "rewire me" cue.

### Phase 4.5 — Config and Selector Usability

- Node config modals put memory-bank reads at the top and writes at the bottom.
- Core node settings render between reads and connections.
- Text-heavy config windows avoid single-letter quit/save. `W`/`S` navigate,
  `E` activates the highlighted field for typing, and `Esc` exits edit mode or
  closes/cancels when already in navigation mode.
- Branch/router nodes generate `<port>_label` fields from `output_ports`; editor
  display uses those labels instead of raw port ids.
- Node selector highlights the top filtered result when tabbing into the list.
- Arrow keys move the active highlight cleanly.
- Variable write nodes can pass input through to output by default.

### Phase 5 — Config Tabs

- `frontend/widgets/form_generator.py` groups schema fields by their existing
  optional `group` key.
- Multi-group schemas render as Textual `TabbedContent` / `TabPane` sections.
- Single-group schemas stay flat so simple nodes do not get an empty or noisy
  tab bar.
- Numeric zero values now render as `"0"` instead of a blank field.
- Schema-generated `Select` fields now use `allow_blank=False` by default so
  Textual does not inject a blank "Select" row ahead of real node options.
- Tests cover pure grouping behavior plus mounted Textual grouped and
  single-group forms.

### Phase 5.5 — Keyboard Navigation Hardening and Config Modal UX

- `Ctrl+Q` now exits text-field edit mode instead of closing the whole app.
  `AttackOfTheNodesApp.check_action` blocks the App-level `"back"` action when a
  `CommandInput` or `CommandTextArea` is in edit mode.
- `#node-config-scroll` (`VerticalScroll`) has `can_focus = False` so clicking
  labels inside the scrollable area does not steal keyboard focus.
- Memory-bank outputs are count-driven declarations. Each declaration renders a
  compact `Output Description:` `CommandInput` plus a bounded multiline `Output:`
  `CommandTextArea` so long values wrap safely without breaking the modal.
- Branch/router nodes hide memory-bank output controls because their outputs are
  graph branches, not value declarations.
- Navigation section headers have a dedicated `nav-section` CSS class. When
  keyboard navigation lands on a non-interactive header it gets the
  `nav-highlight` CSS class (blue highlight + scroll). The `_nav_widget`
  instance variable tracks which non-interactive widget is currently highlighted.
- `.generated-form { height: auto; }` and `.generated-form-page { height: auto; }`
  added to `styles.tcss`. This is the critical fix: `Vertical` defaults to
  `height: 1fr` which collapses to zero inside `VerticalScroll`.
- `_schema_with_generated_branch_labels` generates label fields from node
  `output_ports` so future router ports such as `path_c` work without custom UI
  code.
- `_ancestor_visible(widget)` helper filters out widgets inside `display=False`
  containers from the keyboard nav list.
- `scroll_to_widget` called directly on `#node-config-scroll` instead of
  `widget.scroll_visible()` for reliable nested-widget scrolling.
- `frontend/widgets/command_navigation.py` owns command-mode activation for
  generated/config widgets: text fields require `E` before editing, dropdowns
  open with their first real option highlighted, `W`/`S` and arrows move inside
  expanded dropdowns, and `E`/Enter commits the highlighted option.
- Schema-generated `Select` fields use `allow_blank=False` unless a future
  schema explicitly models blank/optional selection. This prevents the injected
  "Select" row from stealing highlight/navigation.

### Frontend Command UI Contract

- Prefer schema-generated fields from backend node metadata. If a node needs
  custom UI, first ask whether a field schema extension or frontend helper would
  make it generic.
- Text entry uses `CommandInput` / `CommandTextArea`: focus highlights the field,
  `E` enters typing mode, `Esc` exits typing mode, and `W`/`S` remain navigation
  in command mode.
- Selects and selection lists use `command_navigation.py`; screens should not
  duplicate private Textual overlay handling.
- `SelectOverlay` owns focus while a dropdown is expanded and has its own
  `_on_key` for type-to-search. Priority screen bindings cannot reach it from
  outside. The fix is `_install_select_overlay_command_bindings()` in
  `command_navigation.py`, which wraps `SelectOverlay._on_key` at import time so
  W/S/arrows/E/Enter/Ctrl+Q are handled before type-to-search. A
  `_command_navigation_key_patch` sentinel prevents double-patching in tests.
- To commit a `Select` value programmatically, use `commit_highlighted_select`
  from `command_navigation.py`. Do not call `action_select()` from outside the
  overlay; it does not close reliably from non-overlay context.
- Screens with keyboard-only workflows must call `scroll_to_widget` or an
  equivalent helper whenever focus moves to an off-screen widget.
- Common notifications should use `frontend/notifications.py` helpers instead
  of ad hoc `app.notify(...)` strings. Frontend source now routes common
  notifications through that helper.

### Recurring Frontend Bug Patterns

These are the common/adjacent bugs seen repeatedly during recent UI work:

- **Widget defaults leaking through.** Textual controls have useful defaults that
  can be wrong for command-mode workflows: blank `Select` rows, focusable scroll
  containers, `Vertical` height defaults inside `VerticalScroll`, and overlay
  highlight persistence. Wrap or normalize these in helpers.
- **Per-screen key handling drift.** Similar modals implemented `W/S`, arrows,
  `E`, `Esc`, and text-field editing differently. New screens should reuse
  command-navigation helpers first.
- **Invisible or stale focus.** Keyboard navigation can land on hidden widgets,
  labels without a selected state, or widgets below the viewport. Always filter
  hidden ancestors, show a visible highlight for non-interactive stops, and
  scroll the active target into view.
- **Dynamic config sections not remounting predictably.** Checkbox/count-driven
  sections must preserve typed values, mount/remove rows immediately, and use
  stable ids/classes so tests and keyboard nav can find them.
- **Custom node config leakage.** Special cases such as branch labels, merge
  branch selection, previous-output preview, and memory-bank declarations should
  become generic schema helpers or well-named frontend adapters, not scattered
  per-node screens.
- **Graph edges mixed with value config.** Ports and branch paths are editor
  structure; memory-bank output declarations are values. Keep the UI separation
  strict or users see irrelevant fields like memory outputs on branch/merge
  router nodes.
- **Long text and terminal constraints.** Outputs, descriptions, prompts, and
  future AI fields may be long. Use bounded multiline widgets and scrollable
  sections instead of fixed compact rows.
- **Notification copy fragmentation.** Frontend screens now route common
  notifications through `frontend/notifications.py`. Future richer toast work
  should build on that helper for duration and de-duplication.

### Node UI Standardization Contract

Adding a normal node should not require frontend file edits. The node class
should provide enough metadata for the UI to render, validate, and explain it.

Required node metadata:

- `node_type`: stable saved identifier.
- `display_name`: human-facing selector/editor name.
- `description`: concise behavior description.
- `category`: selector grouping and future visual identity.
- `input_ports` / `output_ports`: graph structure. Multi-output ports are branch
  paths and get generated `<port>_label` fields.
- `default_config`: complete defaults, including false/zero values.
- `config_schema`: field-level UI contract for generated config.

Supported schema keys today:

- `type`: one of `string`, `integer`, `float`, `number`, `boolean`, `select`,
  `multiselect`, `multiline`, or `code`.
- `label`: user-facing field label. Defaults to the field name.
- `description`: compact help text shown near the field.
- `required`: validation/display hint.
- `options`: required for `select` and `multiselect`.
- `group`: optional tab/section grouping.

Optional UI metadata:

- `ui_hints.pass_through`: display-only hint that the node forwards upstream
  input to its output.
- Future hints should be generic, documented here, and rendered in
  `form_generator.py` or a shared config helper.

Frontend defaults:

- `string` / `integer` / `float` / `number` -> `CommandInput`.
- `multiline` / `code` -> `CommandTextArea`.
- `boolean` -> `Checkbox`.
- `select` or any field with `options` -> `Select` with no blank injected row.
- `multiselect` -> `SelectionList`.
- Multiple schema `group`s -> tabs; one group -> flat form.

Escalation rule:

- If a new node needs a UI that cannot be represented by this contract, add the
  smallest generic schema key or frontend helper that would help the next
  similar node too. Only use node-specific config screens for structural graph
  tools such as merge branch selection where the UI derives from workflow
  topology rather than node-local config alone.

### Phase 6 — Breakpoints

- Node data now has a persisted `breakpoint` boolean.
- `WorkflowMap` can set one breakpoint or clear all breakpoints.
- The editor toggles the selected node with `B` and clears all with `Ctrl+B`.
- Node cards show a breakpoint marker on nodes with breakpoints.
- Supervisors publish `BREAKPOINT_HIT` and pause before executing the marked
  node.
- `MasterState` handles breakpoint hits as a global freeze by reusing the
  existing pause/resume machinery.
- Tests cover breakpoint persistence, pause-before-execute behavior, and resume
  through completion.

### Phase 7 — Per-Node Execution Timing

- Supervisors bracket each `node.execute()` with `perf_counter()`.
- `NODE_TIMING_UPDATE` publishes live timing records with run, branch, node, and
  elapsed seconds.
- `MasterState` aggregates per-run `node_timings` and stores them in run
  history records.
- The Textual app mirrors live timing updates for the execution screen.
- Node cards can render timing badges; execution shows live run timings and the
  editor shows average timings from stored run history.
- Tests cover timing events, master-state aggregation, and run-history
  persistence.

### Phase 8 — Completion Registry + Wait-Until Node

- `MasterState` now owns a per-run `completed_nodes` registry plus an
  `asyncio.Condition`.
- Supervisors mark nodes complete after successful execution and expose a
  completion wait callback through `NodeContext`.
- Added `WaitUntilNode`, registered as a flow node, which waits for configured
  node ids and passes input through after all targets complete.
- Wait-until timeouts use explicit node config when provided, otherwise the
  supervisor/global node timeout path.
- Node config now renders wait targets as a selectable list derived from current
  workflow structure, excluding self and downstream targets.
- Tests cover cross-branch gating order and the wait-target filter.

### Phase 9 — Merge Dynamic List + Lineage Barrier

- Added `BranchEndNode` as the saved/backend type for the user-facing **Merge
  Beacon** marker. The saved `node_type` remains `branch_end_node` for
  compatibility.
- Added `MergeNode` as a flow node with `path_a` through `path_e` inputs and one
  `default` output.
- MasterState now tracks branch groups with a counter-style lineage fallback:
  spawned branches are pending until they arrive at a merge or terminate.
- Merge arrivals store their available input values. Once the group is accounted
  for, only the branch carrying the selected input continues; sibling arrivals
  terminate at the merge.
- Merge config derives the branch-close list from current workflow structure on
  every config open. It lists Merge Beacons that exist anywhere in the workflow,
  including nested branch trees, except beacons on the same branch path as the
  merge node. Rows are labeled `Branch: <branch alias>`. The UI is intentionally
  tolerant of incomplete workflows and does not require validation to refresh.
- Merge config stores `branches_to_close`, `carry_forward_branch_id`,
  `selected_branch_id`, and `selected_input_port`. The last two fields remain
  for backend compatibility with the current single-forward runtime.
- The merge config UI is custom and minimal: no previous-output preview, no
  memory-bank inputs/outputs, no timeout field, and no merge output
  name/description fields. It renders a multi-select branches-to-close list, a
  carry-forward dropdown populated from the selected branches, and selected
  branch output details. v1 enforces one selected branch output.
- Merge Beacon is a no-config utility marker. It appears red while open and green
  when connected to a Merge node; opening config shows the connected merge and
  branch status only.
- Future merge versions may add multi-output/combine behavior, but v1 forwards
  one selected branch input to the next node.
- Future merge runtime work should support complicated multi-depth branch trees
  and long waits for selected Merge Beacons. Add a per-merge timeout override
  when the engine phase revisits merge waiting; this belongs in runtime config,
  not the editor-only list builder.
- Tests cover slow/fast parallel branch merging, multi-close merge config, and
  keyboard navigation inside branch config dropdowns.

### UX Patch — Dynamic Config Sections

- Node config modals use a scrollable body (`#node-config-scroll` VerticalScroll)
  so longer config surfaces remain reachable in small terminal windows.
- Memory-bank output rows are count-driven: the "Number of outputs" counter
  immediately adds/removes visible rows. Each row renders a compact
  `Output Description:` `CommandInput` plus a bounded multiline `Output:`
  `CommandTextArea` for long values.
- Branch/router nodes suppress the memory-bank output section entirely because
  their outputs are graph branches, not value declarations.
- The count-driven pattern should be reused for future optional config sections
  that are enabled by checkboxes or numeric counts.

### Frontend Audit Phases FA-0 through FA-5

- **FA-0**: Full source audit of `frontend/screens/` and `frontend/widgets/`.
  Produced the screen matrix in `docs/FRONTEND_AUDIT_BUILD_PLAN.md` classifying
  each surface by type, helpers used, known risks, and next action.
- **FA-1**: `frontend/widgets/command_navigation.py` expanded into a reusable
  command-mode toolkit: focus discovery, movement, activation, select/list
  helpers, and edit-mode action blocking. `SettingsScreen`, `UserInputScreen`,
  and `PathPromptScreen` migrated. `SelectOverlay._on_key` monkey-patched at
  module import time so W/S/arrows/E/Ctrl+Q work correctly inside any expanded
  `Select` dropdown without requiring per-screen handlers. `commit_highlighted_select`
  commits the highlighted option deterministically and closes the overlay.
- **FA-2**: `frontend/widgets/list_navigation.py` added for ListView highlight
  clamping, focus, scroll-visible, and W/S/arrow movement. `NodeSelectorScreen`,
  `BranchSelectorScreen`, and `WorkflowLibraryScreen` migrated.
- **FA-3**: `frontend/widgets/form_generator.py` expanded with `placeholder`,
  numeric `min`/`max`, string `min_length`/`max_length`, `height` for
  multiline/code fields, `language` hints, and multiselect default selections.
  New nodes can use richer fields without screen code changes.
- **FA-4**: `frontend/widgets/dynamic_sections.py` added for count clamping and
  visible-row value preservation for checkbox/count-driven config sections.
  Shared dynamic selection helpers for stale-selection filtering, default
  select-all, and selected-value normalization. Memory-bank outputs, memory-bank
  inputs, wait targets, and merge branch-close selectors all use the helper.
- **FA-5**: `frontend/notifications.py` added with named notification helpers
  for common workflow, editor, execution, settings, and import/export outcomes.
  `editor.py`, `app.py`, and `execution.py` now route common notifications
  through the helper. Editor notifications restore node-list focus and the last
  highlighted row after transient toasts. A regression guards against direct
  `.notify(...)` calls in frontend source outside `notifications.py`.

---

## 6. Remaining Implementation Plan

### Phase 10 — Documentation Modernization

**Files:** `docs/PROJECT_KNOWLEDGE.md`, `docs/ARCHITECTURE.md`,
`docs/SIGNAL_FLOW.md`, `docs/FILE_TREE.md`, `docs/V05_BUILD_PLAN.md`.
**Depends on:** none.

Current status:

- `docs/README.md` is the docs entry point and read-order guide.
- `docs/BACKEND_FRONTEND_BOUNDARY.md` records the reusable-backend policy and
  tombstone migration plan.
- `docs/PROJECT_KNOWLEDGE.md`, `ARCHITECTURE.md`, `SIGNAL_FLOW.md`, and
  `FILE_TREE.md` have been refreshed for the Python/Textual implementation.
- `docs/V05_BUILD_PLAN.md` is labeled historical.

Goal:

Turn the docs folder into a reliable current-state reference by removing the
split-brain Chrome-extension/tkinter language from active docs.

Requirements:

- Rewrite `PROJECT_KNOWLEDGE.md` around the Python/Textual implementation.
- Rewrite `ARCHITECTURE.md` around local JSON persistence and current backend
  classes, not IndexedDB/Dexie/JS classes.
- Rewrite `SIGNAL_FLOW.md` around Textual screens, event bus, supervisor events,
  memory/output/error flows, and modal routing.
- Regenerate `FILE_TREE.md` from the current project while excluding caches,
  logs, run artifacts, and venvs.
- Mark `V05_BUILD_PLAN.md` as historical proof-of-concept history, or split its
  current Textual notes into this plan and archive the rest.

Done when:

- A new agent can read the docs folder without being told which documents are
  stale.
- `AGENT_HANDOFF.md` points to this plan as the main source of truth.

Status: complete.

### Phase 10.5 — Backend / Frontend Boundary Cleanup

**Files:** `frontend/editor_workflow_adapter.py` or equivalent,
`frontend/screens/editor.py`, `frontend/widgets/node_list.py`,
`backend/workflow_map.py`, `backend/validator.py`,
`backend/nodes/debug/tombstone_node.py`.
**Depends on:** docs boundary plan and current tombstone tests.

Goal:

Keep the backend reusable across future frontends by moving editor-only visual
behavior into frontend adapters.

Read first: `docs/BACKEND_FRONTEND_BOUNDARY.md`.

Scope:

- Add a frontend-owned tombstone/editor placeholder adapter.
- Keep backend deletion as pure graph mutation.
- Move stale timing invalidation to frontend display logic.
- Decommission backend `tombstone_node`, `replace_with_tombstone()`, and
  tombstone-specific validator copy after adapter tests are green.
- Decide whether `position` and `bookmarked` are portable workflow metadata or
  editor-specific metadata.

Done when:

- Editor deletion/replacement still works with tests.
- Backend no longer needs an executable tombstone node for Textual UX.
- Documentation states which workflow fields are engine schema vs. editor
  schema.

### Phase 11 — Real AI Node Execution

**Files:** `backend/nodes/chat_completion_node.py`,
`backend/nodes/image_generation_node.py`,
`backend/nodes/embedding_node.py`, configuration/API helpers.

Requirements:

- Keep existing placeholder behavior available for offline/dev mode.
- Add async HTTP execution with `httpx` or `aiohttp`.
- API keys come from configuration/settings, not hardcoded values.
- Surface provider errors through the normal node error path.
- Add tests using mocked HTTP responses.

Done when:

- AI nodes can run against configured providers.
- Offline placeholder mode remains usable.
- Failures appear in the normal error UI.

### Phase 12 — Packaging and Release Hardening

Requirements:

- Clean dependency files and environment setup.
- Add CI test command documentation.
- Decide how to handle generated run artifacts and logs.
- Add packaging/run instructions for Windows and WSL.
- Expand test coverage beyond `tests/test_debug_nodes.py`.

Done when:

- A fresh checkout can install, test, and launch from documented commands.
- Runtime artifacts are excluded from normal commits.

---

### Phase 13 — Cursor Model Foundation

**Files:** `frontend/app.py`, `frontend/widgets/` (new cursor mixin),
`frontend/styles.tcss`, all screens incrementally.
**Depends on:** none (foundational).

Replace Tab-focus traversal with an app-owned `CursorState`. The navigable set
contains only interactive widgets — static text, labels, and containers are
skipped, which is the direct fix for the silent no-move keypresses seen in
Phase 5.5. WASD is primary movement, arrows as backup, E to edit, Esc to exit
edit mode. Status bar shows `[NAV]` / `[EDIT]` mode indicator.

Generalizes the ad-hoc W/S, A/D, E handling already in `NodeConfigScreen`
(Phase 5.5) into a shared base mixin every screen inherits. Nothing in the
existing plan covers a navigation model; this is net-new and foundational.

Done when:

- The cursor lands only on editable widgets on every screen.
- No silent keypresses: every WASD / arrow press either moves the cursor or is
  visibly blocked.
- WASD and arrows both work identically.

---

### Phase 14 — Key Binding Remap

**Files:** `frontend/app.py`, `frontend/screens/editor.py`,
`frontend/screens/execution.py`, `frontend/screens/help.py`.
**Depends on:** Phase 13.

Establishes the current editor key grammar: E to select/edit, I to insert-after,
X/backspace to delete, and A/D as left/right branch-view navigation. Up/down
arrows mirror W/S. Left/right arrows mirror A/D. Ctrl+left/Ctrl+right mirror
Ctrl+A/Ctrl+D for cycling incomplete branch views.
Retires A as add and removes Ctrl+I add-at-branch-end.

Supersedes the binding table in `TUI_DESIGN.md`. Keeps Phase 4/4.5
insert-rewiring behavior; only the keys change. No single-letter binding may
collide with WASD navigation.

Done when:

- Bindings are consistent across all screens.
- No single-letter collision with the WASD model: W/S are vertical movement,
  A/D are horizontal branch movement.
- Help screen reflects the final map.

---

### Phase 15 — Editor Rework

**Files:** `frontend/screens/editor.py`, `frontend/widgets/node_card.py`,
`frontend/widgets/node_list.py`, `frontend/widgets/status_bar.py`,
`backend/workflow_map.py` (branch name field).
**Depends on:** Phase 14.

Top-bar split: File/Run/Validate actions on the right; editor-specific hints on
the bottom bar. Right panel becomes a Quick View summary instead of full config
(E opens full config modal). Human-readable-name-first display convention with
generated id trailing in parentheses. Editable branch names default to "Branch N"
and round-trip through save.

Current progress:

- Quick View has been simplified to short `Name`, `Kind`, `Step`, `Breakpoint`,
  and `About` lines instead of full config/connection dumps.
- Quick View now lists configured node I/O as `Inputs` and `Outputs`, each split
  into `Transient` graph-port data and `Memory` named memory-bank data. Empty
  categories render as `none`.
- Pass-through nodes such as Sleep display the upstream node that originally
  produced the transient data, not the passive pass-through step.
- Editor rows, selected-node names, and node config titles use
  `Alias (node_id)`.
- Branch node defaults are `Branch 1` / `Branch 2`, editable through branch node
  config.
- Main editor chrome is intentionally sparse: `f file | o options | h help`,
  with detailed navigation in context-aware Help.
- Editor rows hide generated ids and status icons. Tombstones render as
  `Deleted: <original node name>`.
- Editor Quick View I/O uses `Transient Source`, output-name/description lines,
  and matching Memory name/description lines.
- Help is context-aware and the main editor chrome stays short.
- `A/D` cycles all branch views in branch-node creation order; `Ctrl+A/D`
  cycles incomplete branch views only. Both roll over.
- Merge Beacon rows stop branch traversal, expose a selector row for jumping to
  merge branches, and do not visually show downstream merge-branch nodes under
  the beacon branch.

Branch naming is a small backend touch: one optional string per branch edge in
`workflow_map`, extending the Phase 4.5 `path_a_label` work into user-editable
names.

Done when:

- Quick View shows an at-a-glance summary without opening config.
- Quick View uses friendly configured/default data names for transient and
  memory inputs/outputs.
- Branch names are editable and persist across save/load.
- Editor rows show only the node name; config/detail titles may still include
  generated ids for disambiguation.

Status: complete.

---

### Phase 16 — File Modal + Node Config Tabs

**Files:** new `frontend/screens/file_modal.py`, `frontend/screens/node_config.py`,
`frontend/widgets/form_generator.py`, `frontend/screens/settings.py`.
**Depends on:** Phases 14, 15.

File modal consolidates New/Open/Save/Save As/Export/Import plus Run/Validate
as secondary actions. The first pass keeps the existing Workflow Library screen
but removes visible workflow ids, marks the loaded workflow, de-duplicates names
as `Name (2)`, keeps only a bottom Cancel button, and makes list-bottom W/S
movement cycle cleanly to and from Cancel. Export/import path prompts return to
the File menu when canceled.

Node config gains transient output name/description overrides from node port
metadata, with buttons stacked vertically for W/S navigation. Future passes add
fixed tabs (CORE / PARAMETERS / ADVANCED / CONNECTIONS, optional LAST RUN via
`RichLog`), Space to enable optional fields, and A/D to move between parallel
fields. Settings gains an API Keys placeholder menu before real secret storage.

Current progress:

- First File menu usability slice is landed: visible workflow ids removed,
  duplicate names disambiguated, loaded workflow marked, bottom Cancel retained,
  and import/export prompt cancel returns to File.
- Workflow import/export now tries a frontend OS file picker first, then falls
  back to typed path entry. A separate file-manager reveal helper exists for
  future output/asset convenience.
- Typed path fallback prompts include a Browse action when picker metadata is
  available, so users can explicitly reopen the OS picker from the prompt.
- Node config can override transient output names/descriptions from node port
  metadata.
- Node config Save/Cancel and path-prompt Confirm/Cancel controls are stacked
  vertically for W/S movement.
- Settings includes an API Keys placeholder behind `K`.
- Remaining Phase 16 work is the broader fixed tab layout and any deeper file
  modal consolidation beyond the current Workflow Library/File screen.

Builds directly on Phase 5 (group→tabs already exists in `form_generator`) and
the existing connection editor. Consolidates the scattered standalone modals into
tabbed containers.

Done when:

- File modal replaces the toolbar L/O bindings.
- Workflow lists are name-first, id-free, keyboard navigable, and cancel-safe.
- Node config can override transient output names/descriptions.
- An LLM-style node with many optional fields stays fully keyboard-navigable.
- Settings tabs include an API keys section.

Status: in progress.

---

### Phase 17 — Node Visual Identity

**Files:** `frontend/widgets/node_card.py`, `frontend/styles.tcss`,
`backend/node_category.py` (or a frontend symbol registry).
**Depends on:** Phase 13.

Per-category colors, a per-type glyph, size-by-category (utility compact,
complex expanded), and category border weight. Variable row heights feed back
into the Phase 13 cursor scroll math.

Extends `node_card` and its existing validation color states. Category metadata
already exists in the backend; no backend logic changes required. Independent
of key-binding work — parallelizable with Phase 15.

Done when:

- Categories are distinguishable at a glance.
- Utility nodes are visibly smaller than complex ones.
- The Phase 13 cursor handles variable row heights correctly.

---

### Phase 18 — Acceleration + Help Rewrite

**Files:** `frontend/widgets/` (cursor mixin), `frontend/styles.tcss`,
`frontend/screens/help.py`, `frontend/screens/settings.py` (toggle).
**Depends on:** Phases 13–17.

Hold-to-accelerate ramp on repeated W/S navigation, a dim trail at peak speed,
a settings toggle to disable acceleration, a full help screen rewrite organized
by screen context, and a regression sweep for stray non-interactive nav stops.

Finishing layer. The help screen becomes the source of truth for bindings,
replacing the `TUI_DESIGN.md` key list.

Done when:

- Long lists scroll fast under hold-to-accelerate.
- Help matches the shipped bindings exactly.
- No uneditable nav stops remain anywhere in the app.

---

### Phase 19 — Nested Workflows: Built-in Subworkflow Node

**Files:** new `backend/nodes/subworkflow_node.py`, `backend/supervisor.py`,
`backend/master_state.py`, `backend/validator.py`, `backend/workflow_map.py`,
`backend/save_manager.py`, `frontend/screens/node_config.py`.
**Depends on:** Phase 9 (lineage/parent-child coordination). Soft dependency on
Phase 16 for the config UI.

A `SubworkflowNode` loads a workflow by id, spawns a child supervisor, and
pauses the parent supervisor until the child completes — reusing the Phase 9
lineage barrier rather than inventing a parallel wait path. Maps the embedded
workflow's start/end nodes to the node's own I/O ports. Includes a cycle check
and depth limit.

Extends the existing branch-spawn + `max_branch_depth` machinery in
`master_state` / `supervisor`. Net-new pieces: `is_subworkflow` flag, a
`validate_and_prepare_subworkflow` path, and a node-facing way to spawn a child
supervisor. Sits after Phase 9 because it reuses that coordination; it formalizes
the "nested branch spawning" that `max_branch_depth` already anticipates.

Done when:

- A node runs an embedded workflow as a single step, visible as a nested
  supervisor on the execution screen.
- Cycles are rejected at validation time.
- Depth stays within the configured bound.

---

### Phase 20 — Nested Workflows: User-Created Subworkflows

**Files:** `backend/node_factory.py`, `backend/save_manager.py`,
`backend/validator.py`, `backend/persistence.py`,
`frontend/screens/node_selector.py`, `frontend/screens/workflow_library.py`.
**Depends on:** Phase 19.

A dynamic subworkflow registry alongside `NodeFactory`, a publish-workflow-as-node
flow, an export/import dependency policy (bundle the dependency vs. require it
present), and re-validation of parent workflows when an embedded subworkflow is
edited.

Extends `NodeFactory`'s static registry with a dynamic layer and `SaveManager`'s
export/import. The dependency-bundling and version-drift decisions are the gating
design calls and must be settled before any implementation begins.

Done when:

- A saved workflow appears as a node in the node selector.
- Embedding works end to end.
- The export dependency policy is implemented.
- Editing a subworkflow flags its dependent parent workflows as needing
  re-validation.

---

## 7. UI Rules Captured from Testing

- Config windows with multiple text fields should not use single-letter quit or
  save shortcuts.
- Memory-bank reads belong above core settings; memory-bank writes belong at the
  bottom.
- Dynamic memory-bank output fields should render as reliable full-width fields
  in the scrollable config modal; avoid compact row layouts that can collapse in
  terminal viewports.
- Memory-bank output declarations use two user-facing fields:
  `Output Description:` and `Output:`. Keep `Output Description:` compact and
  render `Output:` as a bounded multiline field because real workflow values may
  be long.
- When showing selectable memory-bank inputs, lead with the upstream
  `Output Description:` text so users can recognize what they are reading
  before seeing the output key.
- Branch labels are user-facing names and should replace raw `path_a`/`path_b`
  where the editor displays branch paths.
- Branch/router nodes name their paths through generated `<port>_label` config
  fields. These labels come from node `output_ports` and should work for future
  ports like `path_c` without custom UI code. Branch/router nodes should not
  show memory-bank output controls.
- When filtering in add/insert selectors, tabbing into the list should highlight
  the first visible item automatically.
- Arrow keys should move the visible highlight whenever a highlighted list is on
  screen.
- Text fields should be keyboard-selectable before they are editable: `W`/`S`
  keep moving between controls until the user presses `E` to activate a field.
- `Esc` inside an active text field exits editing mode first; a second `Esc`
  may close the modal.
- Command-mode text fields need distinct selected and editing visual states.
  Mouse-clicking a text field should enter editing mode immediately.
- Focus changes near the bottom of scrollable modals should scroll the active
  control into view.
- Utility/write nodes that primarily update memory should support pass-through
  so input can continue to downstream nodes.
- Nodes define config UI through their class-level `config_schema`. Fields can
  declare `type`, `label`, `description`, `required`, `options`, and `group`;
  the frontend generator chooses the widget. Nodes can also expose `ui_hints`
  for display-only behavior notes such as passive pass-through.
- A brand-new workflow may keep its backend start node hidden until the first
  user node is placed; the start node should reappear after it is connected.
- Config screens may offer opt-in previews of upstream transient output, but
  preview toggles are inspection UI unless a node explicitly documents runtime
  config semantics.
- Ports are graph edges. Edit them in the editor, not in the general config
  form.
- `Ctrl+Q` / `Esc` inside an active text field must exit editing mode first, not
  dismiss the modal. Implement this at the App level with `check_action` blocking
  `"back"` when a `CommandInput` or `CommandTextArea` is in edit mode. Screen-level
  `check_action` alone is insufficient because returning `False` does not stop
  propagation to App-level priority bindings.
- `VerticalScroll` containers that act as scroll viewports should have
  `can_focus = False`. If a scroll container is focusable, clicking labels or
  statics inside it can grab focus silently, breaking keyboard navigation.
- `Vertical` inside `VerticalScroll` defaults to `height: 1fr`, which collapses
  to zero. Dynamic form containers must use `height: auto` in CSS. Apply
  `.generated-form { height: auto; }` for any form-builder output container.
- Keyboard navigation section headers should use a dedicated CSS class (e.g.
  `nav-section`) distinct from per-field labels. Use this class to identify
  nav-stop headers reliably without relying on position or parent hierarchy.
- When navigation lands on a non-interactive widget (section header, static text),
  apply a visible highlight CSS class instead of silently moving through it. Track
  the highlighted non-interactive widget in an instance variable so nav knows its
  current position.
- Call `scroll_to_widget(target, animate=False)` directly on the scroll container
  widget rather than `target.scroll_visible()`. The latter traverses ancestors
  and fails when the target is nested inside a non-scrollable `Vertical` inside
  a `VerticalScroll`.
- When a schema has a multi-group structure that would normally trigger
  `TabbedContent`, check whether tabs are appropriate for the context. Branch
  and router labels are generated from `output_ports`; keep that generation
  generic so future ports do not require custom frontend screens.
- Filter hidden widgets from keyboard nav lists using an `_ancestor_visible`
  check that walks the parent chain looking for `display=False` containers.
  Widgets inside collapsed sections appear in the DOM query results but should
  not receive keyboard focus or nav highlight.
- Memory-bank output declarations for typical nodes are count-driven rows with
  `Output Description:` and `Output:`. Keep descriptions compact; render outputs
  as bounded multiline fields because real workflow values can be long.
- Dropdowns should open with the first real option highlighted every time. Do
  not rely on Textual overlay persistence.
- Selection lists should toggle the highlighted item, not the first item or the
  whole list.
- Every new keyboard-friendly modal should have at least one regression or smoke
  test covering open, move, activate, edit/select, escape edit mode, and save or
  cancel.

---

## 8. Parallel Branching Model

Branch nodes are intended to support parallel branch execution, not only manual
single-path selection.

- Runtime branching happens when a node signals multiple branches.
- `WorkflowMasterState` spawns one supervisor per branch.
- The editor's branch selector is only an editing/navigation view of one branch
  path at a time.
- Future merge/wait features must preserve true runtime parallelism and avoid
  UI-only assumptions about a single selected branch.

---

## 9. Test Plan

Use this baseline after every implementation phase:

```bash
cd AttackOfTheNodes
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```

Expected latest known signal:

- 46 tests passing after FA-5 notification helper + SelectOverlay keyboard fix.
  Test suite does not include Textual mounted-widget tests for nav highlight
  behavior; verify those manually with the TUI smoke test.

For docs-only changes:

```bash
git diff --check
```

Manual TUI smoke tests to keep revisiting:

- `python main.py` launches.
- Node selector groups and search work.
- Sleep node exposes editable duration.
- Branch labels render in editor branch rows.
- `A` adds and `I` inserts after the highlighted node.
- Config text fields accept normal typing.
- `Ctrl+R` starts a run; execution view updates live.
- `Esc` from execution stops/returns cleanly.
- Opening any node config: `W`/`S` navigates all fields; section headers highlight
  in blue with no invisible stops between sections.
- `E` activates a text field; `Ctrl+Q`/`Esc` exits editing without closing modal.
- Checking "Writes to memory bank" and changing `Number of outputs` immediately
  adds/removes visible `Output Description:` and `Output:` fields.
- Branch/router node config hides memory-bank output controls and branch label
  fields are accessible via keyboard nav.

---

## 10. Git Workflow

- Work on the current branch unless the user requests otherwise.
- The worktree may contain unrelated dirty/untracked migration files. Do not
  revert them.
- Stage only files touched for the current phase or docs update.
- Commit with a focused message.
- Keep `docs/SESSION_LOG.md` current.

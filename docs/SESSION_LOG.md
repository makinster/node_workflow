# AttackOfTheNodes Session Log

## 2026-06-02 — Frontend Standardization Review

- Reviewed recent frontend bugs strategically. The shared pattern is not one
  dropdown bug; it is repeated drift around focus state, command-mode key
  handling, Textual widget defaults, dynamic config sections, and custom UI
  escaping the schema generator.
- Expanded `MASTER_BUILD_PLAN.md` with recurring frontend bug patterns and a
  Node UI Standardization Contract. The contract makes the intended path clear:
  normal nodes should be supported by metadata (`config_schema`, ports,
  category, defaults, and optional `ui_hints`) without frontend file edits.
- Added backlog projects for schema-driven node UI expansion and a unified
  toast/alert helper.
- Updated `AGENT_HANDOFF.md` so future work keeps using
  `command_navigation.py`, avoids blank `Select` rows by default, and adds
  generic helpers before custom node-specific config screens.

Verification:

- Docs-only pass; no code tests run.

## 2026-06-01 — Dropdown Navigation Polish and Command UI Helper

- Fixed generated node config dropdowns so option-backed fields do not include
  Textual's blank `Select` row. Branch dropdowns now open with the first real
  option highlighted.
- Added `frontend/widgets/command_navigation.py` as the shared command-mode
  helper for dropdown opening, dropdown movement, deterministic select commit,
  checkbox/list activation, and text-field edit blocking.
- Migrated `NodeConfigScreen` select activation/navigation to the shared helper.
  `W`/`S` and arrows now move inside an expanded dropdown; `E`/Enter commits the
  highlighted option without leaving the dropdown stuck.
- Strengthened the branch dropdown regression test to assert top-row highlight,
  up/down movement, deterministic selection, and top-row reset on reopen.
- Added frontend style guidance to `MASTER_BUILD_PLAN.md` and backlog notes for
  broader helper migration plus a unified toast/alert wrapper.

Verification:

- `python -m pytest tests/test_debug_nodes.py::test_node_config_select_activates_from_keyboard -v`
- `python -m compileall -q .`
- `python -m pytest tests/test_debug_nodes.py -v`
- Result: 38 passed.

## 2026-06-01 — Phase 9 Merge Node and Branch Barrier

- Added `BranchEndNode` as an optional no-config utility marker. Merge config now
  derives open branch paths directly from workflow structure, so Branch End is
  not required for the list to populate.
- Added `MergeNode` as a registered flow node. It waits for sibling branch
  arrivals and emits one selected input through its `default` output.
- Added a MasterState counter-style lineage fallback: branch groups track pending
  branch ids, arrivals at merge, and branch terminations. Nested branch spawns
  inherit the same group.
- Merge config now uses a custom minimal layout: multi-select branches-to-close
  list, carry-forward dropdown, and selected output details. It removes
  previous-output preview, memory-bank sections, timeout, and merge output
  name/description fields.
- The branch selector is populated from open workflow branch paths, including
  paths not yet wired into the merge. The carry-forward dropdown is populated
  from the selected close-list branches and v1 still forwards one selected
  input.
- Branch End rows render red while open and green when their output is connected
  to a Merge node. Opening Branch End config shows the connected merge/branch
  status and no editable fields.
- Branch-node dropdowns now open from keyboard activation (`E` / Enter) while
  using command-mode navigation, and `w/s` or arrows move within expanded
  dropdowns before returning to screen-level focus movement.
- Non-selected branch arrivals terminate at the merge after the barrier releases;
  only the branch carrying the selected input continues downstream.
- Restored dynamic memory-bank output rows in node config and fixed command-mode
  navigation so non-interactive section highlights clear stale text-field focus.
- Future merge work may support combining or forwarding multiple outputs, but
  this phase intentionally keeps the runtime output to one selected input.

Verification:

- `python -m compileall -q .`
- `python -m pytest tests/test_debug_nodes.py -v`
- Result: 38 passed.

## 2026-06-01 — Keyboard Navigation and Config Modal UX Hardening

### Ctrl+Q closes whole app while editing a text field

- Added `check_action` to `AttackOfTheNodesApp` to block the App-level `"back"`
  action when a `CommandInput` or `CommandTextArea` is in edit mode. Screen-level
  `check_action` was insufficient because returning `False` there does not prevent
  the App-level priority binding from also firing.
- `Ctrl+Q` now exits edit mode on the focused field and stays in the modal
  instead of dismissing the whole app.

### VerticalScroll stealing focus on click

- Set `can_focus = False` on the `#node-config-scroll` VerticalScroll in
  `NodeConfigScreen.on_mount`. This prevents the scroll container from grabbing
  focus when the user clicks a label or static text inside it, which previously
  caused keyboard navigation to break silently.

### Memory bank outputs: safe dynamic rows

- Kept the "Number of outputs" counter and fixed the dynamic rendering path so
  the modal adds/removes visible rows immediately.
- Each memory-bank output row now renders a compact `Output Description:`
  `CommandInput` and a bounded multiline `Output:` `CommandTextArea`.
- The multiline output field is sized for long values while descriptions and the
  output count stay compact.
- Branch/router nodes hide memory-bank output controls because their outputs are
  graph branches, not value declarations.

### Nav highlight system for non-interactive section headers

- Added `nav-section` CSS class to the six true section-header `Label` widgets
  in `NodeConfigScreen.compose`. These are the only Labels that should appear as
  nav stops.
- Per-field labels generated by `form_generator.build_form` use only
  `form-label` and never `nav-section`, making the distinction reliable.
- Added `_nav_widget` instance variable to track the currently highlighted
  non-interactive widget. When navigation lands on a section header, the header
  gets the `nav-highlight` CSS class (blue highlight) so the user can see that
  their key press registered.
- `_move_keyboard_focus` uses `_nav_widget` as the current position reference
  when a non-interactive item is highlighted and clears the highlight before
  moving to the next stop.
- Added `.nav-highlight { background: #1a3a5c; color: #7ec8e3; text-style: bold; }`
  to `styles.tcss`.

### Form fields invisible at zero height (root cause fix)

- `Vertical` in Textual 8.x defaults to `height: 1fr`. Inside a `VerticalScroll`
  fractional units have no meaning, collapsing the container to zero height.
  Form fields were present in the DOM and nav list but invisible.
- Fixed with `.generated-form { height: auto; }` and
  `.generated-form-page { height: auto; }` in `styles.tcss`.

### Branch/router label generation

- Branch label fields are generated from node `output_ports` using
  `<port>_label`, so future router ports such as `path_c` work without custom UI
  code.
- The editor reads those configured labels when displaying branch rows instead
  of showing raw port ids.

### Hidden widget nav filtering

- Added `_ancestor_visible(widget) -> bool` to `NodeConfigScreen` that walks the
  parent chain and returns `False` if any ancestor has `display=False`.
- `_keyboard_focus_widgets` uses this check to exclude widgets inside
  `display=False` containers (e.g. the description row inside `#membank-output-rows`
  when "Writes to memory bank" is unchecked).

### Reliable scroll-to-widget for nested content

- Replaced `target.scroll_visible(animate=False)` with
  `self.query_one("#node-config-scroll").scroll_to_widget(target, animate=False)`.
- `scroll_visible` traverses ancestors to find a ScrollView but fails when the
  widget is nested inside a non-scrollable `Vertical` inside `VerticalScroll`.
  Calling `scroll_to_widget` directly on the scroll container is reliable in
  all cases.

- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Schema-Driven Branch Config and Command Field UX

- Added node `ui_hints` metadata to factory output so nodes can describe UI
  behavior without custom frontend config screens.
- Added a Sleep node pass-through hint and displayed it in node config so users
  know the previous output is forwarded unchanged.
- Generated branch-name fields from multi-output node ports and hid memory-bank
  output controls for branch/router nodes.
- Generalized editor branch labels so any output port can use
  `<port>_label`, including future `path_c`-style ports.
- Updated node config help text to the keyboard-first wording and added visual
  selected-vs-editing styles for command-mode text fields.
- Mouse-clicking a command-mode textbox now enters typing mode immediately.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Compact Output Count and Description Fields

- Kept the actual `Output:` field as a bounded multiline text area for long
  values.
- Returned `Number of outputs` and `Output Description:` to compact fields so
  the config modal uses less vertical space.
- Updated the dynamic output-row regression test for the compact description
  field and compact output count styling.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Long Output Text Areas + Description-First Inputs

- Changed memory-bank output declarations to render bounded multiline text
  areas for both `Output Description:` and `Output:` so long values wrap safely
  inside the config modal.
- Kept backward compatibility with existing `id`-based saved configs while also
  saving the clearer `output` key for future code.
- Updated revealed memory-bank input choices to lead with the output
  description, then show the output key.
- Extended tests for long descriptions, multiline output fields, saved output
  data, and `output`-key registry compatibility.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Visible Dynamic Memory Output Fields

- Changed dynamically revealed memory-bank output rows from a compact horizontal
  row into stacked full-width fields so Textual does not collapse the inputs
  while only showing the scrollbar.
- Added styling for memory-bank output fields and extended the mounted config
  regression test to assert the revealed fields have visible layout.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Escape Leaves Text Editing

- Updated command-mode text fields so `Esc` exits editing mode and keeps the
  field selected instead of closing the surrounding modal.
- Added regression coverage proving a field can be activated with `E`, typed
  into, exited with `Esc`, and then return to `W`/`S` navigation.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Keyboard-First Text Field Navigation

- Added command-mode text widgets so text fields can be selected with keyboard
  navigation without immediately consuming `W`/`S` as typed characters.
- Updated the add/insert node selector to open on the node list with the first
  node highlighted; `W` moves to the filter row and `E` activates typing.
- Applied the same `E`-to-edit pattern to node config fields, generated schema
  inputs, multiline text areas, settings, user-input prompts, and import/export
  path prompts.
- Added keyboard regression coverage for node selector filter activation and
  node config input activation.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Empty Start View + Previous Output Preview

- Hid the backend-only start node in an otherwise empty editor view so a new
  workflow presents as empty and invites the user to add the first real node.
- Kept the hidden start node as the connection source for `A` add and `I`
  insert, then rendered it again once the first user node is connected.
- Added a dynamic config-modal checkbox that reveals the selected node's first
  upstream transient output when a run has captured one.
- Updated empty node-list copy to point users at `A` for adding a node.
- Added regression tests for the empty-start editor behavior and previous-output
  preview helper.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-06-01 — Dynamic Node Config Output Rows

- Made the node config modal body scrollable so longer config sections are
  reachable inside the terminal viewport.
- Reworked memory-bank output declarations to render dynamically from the
  "Writes to memory bank" checkbox and output count instead of always showing a
  fixed set of rows.
- Preserved typed output ids/descriptions when the output count changes and
  disabled the count field while writes are off.
- Raised the supported memory-bank output row cap to 20 for richer node
  configurations.
- Added a mounted Textual regression test for toggling writes, growing/shrinking
  output rows, and preserving entered output text.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-31 — Phase 8 Completion Registry + Wait-Until Node

- Added a per-run completion registry to `MasterState` with an
  `asyncio.Condition` for waiters.
- Supervisors now mark nodes complete after successful execution and provide a
  `NodeContext.wait_for_nodes()` callback to nodes.
- Added and registered `WaitUntilNode`, which waits for configured target node
  ids and passes input through when all targets have completed.
- Added wait-target config helpers that list eligible targets from workflow
  structure and exclude self/downstream nodes to avoid obvious deadlocks.
- Added tests for cross-branch wait gating and target filtering.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-31 — Phase 7 Per-Node Execution Timing

- Added `NODE_TIMING_UPDATE` events from supervisors around every
  `node.execute()` call.
- Aggregated timing totals per node on `MasterState` and persisted
  `node_timings` into run history records.
- Mirrored live timings in the Textual app so execution node cards can show
  elapsed time during a run.
- Added editor average timing display based on stored run history.
- Added a regression test proving timing events are emitted and persisted for a
  workflow containing `SleepNode`.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-31 — Phase 6 Breakpoints

- Added persisted node breakpoint flags plus `WorkflowMap.set_breakpoint()` and
  `clear_all_breakpoints()`.
- Added editor breakpoint controls: `B` toggles the selected node and `Ctrl+B`
  clears all breakpoints; node cards show a breakpoint marker.
- Added `BREAKPOINT_HIT`; supervisors publish it before executing a marked node,
  and `MasterState` reuses the existing global pause/resume path.
- Updated in-app help text for breakpoint keys and the newer text-field-safe
  node config shortcuts.
- Added tests for breakpoint persistence and pause-before-execution/resume
  behavior.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-31 — Phase 5 Config Tabs

- Updated the schema form generator so fields sharing a single `group` render as
  a simple flat form, while multi-group schemas render as Textual tabs.
- Preserved field order within each group and kept the existing schema contract;
  no new backend schema concept was added.
- Fixed form rendering edge cases found during mounted Textual tests: numeric
  zero values now display as `0`, and blank selects use Textual's `Select.NULL`
  sentinel.
- Added tests for grouping behavior and mounted tabbed/single-group forms.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-31 — Comprehensive Build Plan Merge

- Rewrote `docs/MASTER_BUILD_PLAN.md` as the comprehensive current-state build
  plan, merging the active phase plan, Textual TUI notes, agent working rules,
  architecture model, UI testing feedback, and remaining roadmap.
- Updated `docs/AGENT_HANDOFF.md` so future agents treat `MASTER_BUILD_PLAN.md`
  as the source of truth and understand that older Chrome/tkinter language is
  historical until Phase 10.
- Updated `docs/PROJECT_BACKLOG.md` to clarify that docs modernization should
  refresh older reference docs against the comprehensive plan.
- Verification:
  - `git diff --check`

## 2026-05-31 — Config Modal Usability Patch

- Reordered node config modals so memory-bank reads are above core node
  settings and memory-bank writes are at the bottom.
- Removed `Q` and other single-letter navigation/save bindings from the
  text-heavy node config modal so typing in fields works normally.
- Added branch label config fields (`path_a_label`, `path_b_label`) and editor
  display support so branch rows can show names instead of raw `path_a/path_b`.
- Improved node selector keyboard behavior: tab focuses the node list and the
  top filtered item is highlighted immediately; arrow keys move the highlighted
  item.
- Added pass-through defaults to variable writer nodes so utility writes can
  preserve input as output.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-30 — Phase 1 Reachability Helper

- Treated `docs/MASTER_BUILD_PLAN.md` Phase 0 memory-leak fixes as complete.
- Added `WorkflowMap.nodes_reachable_from(node_id) -> set[str]` for downstream
  graph reachability. The helper excludes the starting node, ignores missing
  targets, and is cycle-safe.
- Added a focused branching-graph regression test to
  `tests/test_debug_nodes.py`.
- Added repo-local handoff/backlog docs so future sessions can start from the
  current Textual build state instead of pasted chat context.
- Verification:
  - `python -m compileall -q .`
  - `python tests/test_debug_nodes.py`

## 2026-05-30 — Phase 2 Dependency List + Validation

- Replaced `docs/MASTER_BUILD_PLAN.md` with the updated build handoff that marks
  Phase 0 and Phase 1 complete and makes Phase 2/3 sequencing explicit.
- Installed `pytest` and `pytest-asyncio` in the project venv and added
  `pytest.ini` with `asyncio_mode = auto`.
- Added derived `input_sources` to workflow save/export/duplicate data. The
  cache is derived from node input connections plus defensive reads of
  `config["membank_inputs"]`.
- Added validation for missing derived node input sources and missing membank
  declarations.
- Added focused tests for save-file `input_sources`, missing node input sources,
  and missing membank input sources.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-30 — Phase 4 Delete + Insert Nodes

- Split editor add/insert intent: `A` keeps add-at-tail behavior, while `I`
  inserts after the highlighted node or active branch row.
- Insert rewiring disconnects the highlighted node's old downstream edge,
  connects highlighted -> new node, then connects new node -> old downstream.
- Removed cascade subtree deletion from editor delete; tombstones remain as the
  visible "choose a replacement" cue and downstream branch nodes are retained.
- Added focused tests for insert-between rewiring and no-cascade tombstone
  deletion.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-30 — Phase 3 Membank I/O + Registry

- Removed port-edge mutation controls from `NodeConfigScreen`; connections are
  shown read-only there and remain an editor-path responsibility.
- Added memory-bank output controls that store `membank_outputs` as id +
  description records.
- Added memory-bank input controls that store selected ids in `membank_inputs`.
- Added a frontend registry helper that scans declared `membank_outputs` and
  filters downstream-only writers with `WorkflowMap.nodes_reachable_from()`.
- Added a focused registry/filter regression test.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

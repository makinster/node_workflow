# AttackOfTheNodes Session Log

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

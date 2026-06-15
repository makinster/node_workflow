# AttackOfTheNodes Session Log

This active log keeps recent/current entries only. Full older history was
collapsed into `archive/SESSION_LOG_HISTORY.md` during the documentation
overhaul.

## 2026-06-15 — Phase 17 Editor Node Borders

- Replaced inline family bracket characters in editor node rows with plain
  alias and family/subcategory text.
- Added Textual ASCII borders to identity-mode `NodeCard` rows so each editor
  node appears as its own bordered text box.
- Kept family colors, quiet utility styling, validation/breakpoint/execution
  state priority, and Merge Beacon open/connected health colors.
- Updated Phase 17 UI docs to describe bordered node boxes instead of bracket
  columns.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_card or editor_depth or editor_identity_rows"` (3 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"` (9 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_card or editor_depth"` (2 passed after ASCII border follow-up)
  - `git diff --check`

## 2026-06-14 — Phase 17 Status And UI Gap Docs

- Corrected active docs that prematurely marked Phase 17 complete. Phase 17 is
  still active while current frontend/backend support gaps are being triaged.
- Updated `MASTER_BUILD_PLAN.md`, `PHASE_17_NODE_VISUAL_IDENTITY.md`,
  `PROJECT_KNOWLEDGE.md`, `PROJECT_BACKLOG.md`, and `AGENT_HANDOFF.md`.
- Documented the current backend features without full Textual UI support:
  historical run browsing, schema-driven file pickers for `path_hint: "file"`,
  memory-state save/load options, workflow rename/open-workflow/bookmark
  controls, and persisted error clearing.
- Refreshed stale metadata notes: `NodeFactory.get_node_types_metadata()` now
  exposes the Phase 17 identity metadata used by selector filters and editor
  rows.
- Verification:
  - `git diff --check`
  - stale-status `rg` scan for completed-Phase-17 wording and old metadata-gap
    copy (no active-doc matches)

## 2026-06-10 — Frontend Deleted-Node Model

- Reworked editor delete behavior so a normal delete is visual-only: the
  original node stays in `WorkflowMap` while the editor stores deleted-row
  overlay state keyed by node id.
- Added deleted-row rendering in the Phase 17 two-line bracket style, with
  restore-aware controls (`x delete | z undo | e new node`) and a no-restore
  variant that hides `z undo`.
- Added editor actions for deleted rows: `z` undo restores the visual original,
  `e`/Enter opens replacement through the node selector, and a second `x`
  permanently removes the node and prunes merge-beacon config when needed.
- Before save/validate/run, soft-deleted rows materialize to `branch_end_node`
  with `_system_role: "deleted_node_branch_end"` and nested `deleted_node`
  restore metadata; materialization drops outgoing connections so execution
  stops safely at the placeholder.
- Saved/loaded marked branch-end placeholders render as friendly deleted rows,
  and original connections/config can be restored when restore data exists.
- Refreshed `BACKEND_FRONTEND_BOUNDARY.md` and `PROJECT_BACKLOG.md` to note
  that new deletes no longer write `tombstone_node`; legacy registration remains
  a future old-save compatibility cleanup.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "deleting_merge_beacon_prunes or deleted or tombstone or node_card or editor_depth or node_selector"` (11 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (129 passed)
  - `git diff --check`

## 2026-06-10 — Deleted-Node Save Contract Audit (no code changes)

- Audited whether the visual-deleted-node model (frontend-only delete while
  editing; save materializes deleted rows into `branch_end_node` with a
  `_system_role: "deleted_node_branch_end"` + `deleted_node` config marker)
  works against today's backend. Result: yes, with zero backend changes.
- Wrote the contract into `BACKEND_FRONTEND_BOUNDARY.md` ("Deleted-Node
  Save Contract"). Key findings:
  - SaveManager save/export/duplicate and WorkflowMap load/save preserve
    arbitrary JSON-serializable node config unchanged; import rewrites only
    id/name.
  - The marker must live in node config: top-level save keys are dropped by
    `WorkflowMap.save`/`get_workflow_data_for_save()`.
  - The validator ignores extra config keys, but original
    `membank_inputs`/`membank_outputs` must be nested inside `deleted_node`
    or they will be validated at top level.
  - Execution stops cleanly at a materialized beacon with no outgoing
    connection (supervisor advances to `None`; merge groups discard
    terminated branches). Materialization must drop outgoing connections or
    execution silently continues downstream.
  - Port-shape caveat: `branch_end_node` declares only `input`/`default`;
    surviving connections on other port names produce blocking
    port-validity errors.
  - Optional future hardening: ~8-line validator warning for marked nodes.
- Verification:
  - `git diff --check`

## 2026-06-10 — Phase 17 Tombstone Selector Follow-Up

- Hid editor-only `tombstone_node` metadata from `NodeSelectorScreen` so users
  cannot add a "Deleted Node" placeholder while backend tombstone
  decommission remains gated.
- Kept the filter frontend-owned: `NodeFactory` may still expose transitional
  tombstone metadata because the editor adapter still needs the registered
  type until Phase B cleanup.
- Extended selector coverage to assert `tombstone_node` is absent from the
  selector source set and from search results.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector"` (1 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"` (8 passed)
  - `git diff --check`

## 2026-06-10 — Tombstone Boundary Audit Refresh (planning only)

- Audited the actual tombstone footprint against
  `BACKEND_FRONTEND_BOUNDARY.md` and found the doc stale: Phase A is done.
  `frontend/editor_workflow_adapter.py` owns placeholder create/remove/
  replace, and `replace_with_tombstone()`, tombstone-specific
  `replace_node_type()`, and backend-written `_timing_invalidated` are
  already gone from the backend.
- Rewrote the boundary doc's audit and migration plan: Phase A marked done
  with its one transitional dependency (the adapter still writes
  `type: "tombstone_node"`, so backend registration is still required), and
  Phase B reduced to a concrete five-step decommission list covering
  `backend/nodes/debug/tombstone_node.py`, `backend/nodes/__init__.py`,
  the validator's tombstone error block, the `node_identity.py` entry, and
  an old-save loading decision.
- Added an explicit coordination gate: Phase B must not start while Phase 17
  selector/editor work is in flight, because it touches Phase 17 metadata,
  the selector's metadata source, and ~26 tombstone test references.
- Noted the known wart that `tombstone_node` currently appears in node-type
  metadata as an addable "Deleted Node".
- Synced the boundary cleanup section of `PROJECT_BACKLOG.md` to the
  refreshed audit. No code changes.
- Verification:
  - `git diff --check`

## 2026-06-10 — RunSession Edge-Case Audit

- Audited the RunSession integration paths and added focused tests for three
  previously untested load-bearing behaviors in `tests/test_run_session.py`:
  - two file readers of the same path in one run share the cached handle and
    both receive full contents (guards the `seek(0)` re-read behavior);
  - back-to-back runs each get a fresh session with the new run's id, and
    both sessions end up closed;
  - `open_file` transparently replaces a cached handle that was closed
    externally.
- Documented a write-mode caveat in `RUNTIME_RESOURCE_SESSION.md`: a cached
  `"w"` handle only flushes at run end, so a future file writer node should
  flush after writes (or the session should flush before serving a same-path
  read handle).
- No runtime, frontend, or save-format changes.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_run_session.py -v` (10 passed)
  - `git diff --check`

## 2026-06-10 — RunSession Implementation

- Implemented the per-run resource session from
  `archive/plans/RUNTIME_RESOURCE_SESSION.md`:
  - New `backend/run_session.py`: `RunSession` with `open_file` (cached by
    resolved path + mode), `register_resource`/`get_resource` with optional
    close hooks, `validate_path`, and idempotent `close_all`.
  - `MasterState` creates the session in `start_workflow()`, passes it to
    root and branch supervisors, and closes it in `_record_run` so FINISHED,
    supervisor-error, and forced-termination paths all release resources.
  - `Supervisor` accepts `run_session` and passes it into `NodeContext`;
    `NodeContext.run_session` defaults to `None` so existing direct
    constructions keep working.
  - `Validator` gained a file-path pass for schema fields hinted with
    `path_hint: "file"`: empty required path is an error; a path missing on
    disk is a warning (an earlier node may create it during the run).
  - `FileReaderNode` is the first consumer: its `file_path` field carries
    `path_hint: "file"` and it reads through `context.run_session` when
    available.
- No frontend, persistence, or save-format changes. Workflow saves still
  store plain path strings.
- Updated `RUNTIME_RESOURCE_SESSION.md` status/implemented-files and the
  backlog entry.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_run_session.py -v` (7 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (121 passed)
  - `git diff --check`

## 2026-06-10 — Phase 17 Editor Row Identity

- Implemented editor row visual identity for normal node rows:
  - Editor rows now opt into two-line `NodeCard` rendering with fixed
    left/right frame columns.
  - The first line keeps the editable alias as the primary text.
  - The second line shows primary family plus one or two high-signal
    subcategories, truncating long identity text with an ellipsis.
  - Utility-tagged rows are visually quieter, while Merge Beacon open/connected
    health colors still take priority over decorative family colors.
- The editor attaches frontend-only identity display metadata from
  `NodeFactory.get_node_types_metadata()` to row display copies. Runtime node
  data and backend execution behavior were not changed.
- The right-side details panel now shows full `Family` and `Subcategories`
  lines for the selected node.
- Added focused coverage for:
  - row frame alignment and truncation;
  - full details-panel identity;
  - keyboard selection stability across taller editor rows and backend refresh;
  - existing Merge Beacon health, branch selector rows, and selector behavior.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_card or editor_depth or editor_identity_rows"` (3 passed)
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"` (8 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (126 passed)

## 2026-06-10 — Runtime Resource Session Design Note

- Created `archive/plans/RUNTIME_RESOURCE_SESSION.md`: backend-only design
  plan for a per-run `RunSession` object that holds file handles, streams,
  and future resource types during one workflow execution.
- Design covers: `RunSession` interface, lifecycle owned by `MasterState`
  (create at run start, `close_all()` before finalization), `NodeContext`
  receives session reference, file paths remain portable config strings in
  saves, validation rules for missing/inaccessible paths, why frontend file
  picking stays frontend-owned, and forward-compatibility for streams,
  browser sessions, and listeners.
- Likely new files when implemented: `backend/run_session.py`,
  `tests/test_run_session.py`; modified: `master_state.py`, `supervisor.py`,
  `node_base.py`, `validator.py`. No frontend or persistence changes.
- Updated `PROJECT_BACKLOG.md` "Later Project — Runtime Resources And Hidden
  Helper Nodes" to reference the new design doc and summarize `RunSession`.
- Verification:
  - `git diff --check`

## 2026-06-10 — Phase 17 Direction Alignment

- Added `PHASE_17_NODE_VISUAL_IDENTITY.md` as the active plan for node visual
  identity, selector taxonomy, subcategory filters, and editor row direction.
- Recorded follow-up design decisions: subcategory filters are `AND`
  checkboxes, selector search is activate-to-edit, filter lists differ per tab,
  editor rows should use aligned bracket columns with ellipsis truncation, and
  file access should eventually be owned by a run-scoped resource helper/session
  coordinated by `MasterState`.
- Marked the task-first docs overhaul complete and Phase 17 active in
  `MASTER_BUILD_PLAN.md`.
- Updated the task router, handoff, UI quick reference, TUI design notes,
  project knowledge, backlog, README, and file tree to point at the Phase 17
  taxonomy.
- Captured the then-open metadata exposure follow-up: `Node` had optional
  identity fields, and `NodeFactory.get_node_types_metadata()` still needed to
  expose category/tag/icon/color metadata before the selector could depend on
  it. This was later completed in the Phase 17 metadata exposure slice.
- Verification:
  - `git diff --check`
  - stale active-status `rg` scan for docs-overhaul-in-progress wording (no
    matches)
  - Phase 17 reference `rg` scan across active docs
  - `find AttackOfTheNodes/docs -type f -name '*.md' | sort`

## 2026-06-10 — Phase 17 Metadata Exposure

- Added transitional Phase 17 identity metadata for the registered node library:
  primary family, subcategory tags, icon name, and color hint.
- `NodeFactory.get_node_types_metadata()` now exposes `category`,
  `primary_family`, `legacy_category`, `tags`, `icon_name`, and `color_hint`
  without changing runtime execution behavior.
- Clarified the current saved `branch_node` as the user-facing **Parallel
  Branch** node: it duplicates incoming payloads across multiple branch paths,
  carries the `Parallel` subcategory, and does not claim the `Conditional`
  subcategory reserved for a later dedicated node.
- Added focused coverage proving the metadata contract for all registered nodes
  plus representative Inputs, Flow Control, Outputs, and Complex nodes.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_factory_exposes_phase_17_identity_metadata or node_selector or node_card or editor_depth or branch_end"`
  - `git diff --check`

## 2026-06-10 — Phase 17 Selector Taxonomy Slice

- Updated `NodeSelectorScreen` to use Phase 17 family tabs: Inputs,
  Flow Control, Outputs, and Complex.
- Added tab-specific subcategory checkbox filters derived from factory metadata.
  Multiple checked subcategories use `AND` semantics.
- Changed selector search to command-mode activation: opening the selector and
  `/` focus the field without auto-editing; `E`/Enter activates text editing.
- Initial selector focus now lands on the first visible subcategory checkbox
  for the active family, falling back to the node list if a family has no
  filters.
- Added focused selector coverage for family switching, tab-specific filter
  visibility, `AND` filtering, string-plus-subcategory filtering, and
  activate-to-edit search behavior.
- Updated `MASTER_BUILD_PLAN.md` with current RunSession state, completed
  Phase 17 selector/metadata work, remaining editor-row/details-panel work, and
  the next focused todo list.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_factory_exposes_phase_17_identity_metadata or branch_config_uses_parallel or branch_node_parallel or branch_node_default_labels"`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"`
  - `../.venv/bin/python -m pytest tests/ -v` (121 passed)
  - `git diff --check`

## 2026-06-09 — Documentation Overhaul

- Rebuilt the docs entry path around task-first reading from `README.md` and
  `TASK_INDEX.md`.
- Collapsed oversized active docs and archived full historical content under
  `docs/archive/`.
- Moved historical proof-of-concept and completed planning docs out of the
  default read path.
- Added `UI_QUICK_REFERENCE.md` as the short current UI/keybinding summary for
  routine frontend work, leaving `TUI_DESIGN.md` as the detailed reference.
- Corrected stale active-doc keybinding references and updated `AGENTS.md` to
  point agents at the task router.
- Added `DOCS_MIGRATION_NOTES.md` to explain moved/collapsed docs and archive
  decisions.
- Verification:
  - `git diff --check`
  - stale-reference `rg` scan from the implementation plan (no matches)
  - active-doc stale keybinding scan for old add/library shortcuts (no matches)
  - `find AttackOfTheNodes/docs -type f -name '*.md' | sort`
  - `wc -l AttackOfTheNodes/docs/*.md AttackOfTheNodes/docs/archive/*.md AttackOfTheNodes/docs/archive/plans/*.md`

## 2026-06-09 — Node Helper Generator And Focused Checks

- Added standalone developer tooling at `../aotn_node_helper/` for generating
  ordinary metadata-driven node files from JSON/YAML specs.
- Helper specs support `config_tabs`, matching the workflow where a node is
  described first and then fields are listed under tab headers such as `Source`,
  `Parameters`, and `Payloads`.
- Generated nodes update backend registration, create a node-specific focused
  test under `tests/generated/`, and can be checked with
  `../aotn_node_helper/check_node.py <node_type>`.
- Node Config honors schema `tab` hints, so generated fields can land in the
  fixed Source / Parameters / Payloads tabs without per-node frontend code.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_node_helper.py -v` (3 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "schema_tab_hints"` (1 passed, 109 deselected)
  - `../.venv/bin/python -m compileall -q .`
  - `./.venv/bin/python -m compileall -q aotn_node_helper`

## 2026-06-09 — Payload Reveal Consistency

- Added opt-in `Reveal upstream payload` controls to the Payloads tab and
  matching `Reveal Vault payload` previews for selected Vault inputs.
- Made revealed payload previews read-only command stops, standardized preview
  copy, and fixed long-tab scrolling back to the tab header.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "payloads_tab_reveals or fixed_tabs_are_keyboard or branch_config_uses_parallel or previous_output_preview or branch_payload_preview or selection_lists_exit"` (8 passed)
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v` (109 passed)

## 2026-06-09 — Node Config Copy, Scroll, And Payload Polish

- Polished Branch config copy and command text editing semantics.
- Improved Branch Payloads navigation/scrolling for 4-5 branch rows.
- Made inline selection lists exit at top/bottom with W/S or up/down.
- Branch seed display now treats the selected upstream dead-drop or Vault value
  as the branch port's visible payload.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "selection_lists_exit or previous_output_preview or quick_view or branch_payload_preview or branch_config_uses_parallel or command_inputs_require_activation or click_edit_and_textarea or editor_ctrl_s"` (13 passed)
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v` (108 passed)

## 2026-06-09 — Branch Config Payload Polish

- Shifted `branch_node` to the current Branch v1 UI: always-parallel branching,
  2-5 active spawn points, and per-branch payload seed selection.
- Kept legacy conditional Branch config keys readable/preserved for old saves
  but hidden from the current Branch config UI.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "membank_registry or select_activates or previous_output_preview or click_edit_and_textarea or branch_config_uses_parallel or branch_node_parallel"` (7 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v` (104 passed)

## Older Entries

See `archive/SESSION_LOG_HISTORY.md`.

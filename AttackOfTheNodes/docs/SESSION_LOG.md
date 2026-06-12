# AttackOfTheNodes Session Log

This active log keeps recent/current entries only. Full older history was
collapsed into `archive/SESSION_LOG_HISTORY.md` during the documentation
overhaul.

## 2026-06-12 — SecretsManager + Backend Build Plan (Phases 1–6)

### SecretsManager module

- Added `backend/secrets_manager.py`: plain-text JSON store at
  `secrets/secrets.json` (gitignored). Public API: `get_secret`, `set_secret`,
  `delete_secret`, `list_keys`, `has_key`, `reload`. Lazy-load with single
  trust boundary — only this module changes when encryption is added.
- Extended `NodeContext` in `node_base.py` with `secrets_manager` field and
  `context.get_secret(key)` convenience wrapper (returns `None` when no manager
  wired in).
- Wired `SecretsManager` through `MasterState.__init__` → both `Supervisor`
  creation sites → `NodeContext` kwargs. Nodes never call the manager directly;
  they call `context.get_secret(key_name)`.
- Created `secrets/` directory with `.gitkeep`; added
  `AttackOfTheNodes/secrets/secrets.json` to `.gitignore`.
- 18 tests in `tests/test_secrets_manager.py` (CRUD, persistence, lazy-load,
  reload, invalid-JSON fallback, NodeContext integration).

### Backend Build Plan Phases 1–6

**Phase 1 — Tombstone `editor_only` + validator port context**
- `node_identity.py`: added `"editor_only": True` to tombstone entry;
  `apply_transitional_node_identity` copies flag onto node class.
- `node_factory.py`: `get_node_types_metadata` exposes `editor_only` key.
- `validator.py`: tombstone error message appends
  `"(orphaned inputs: X; outputs: Y)"` when port config is present.
- Tests: `tests/test_tombstone_phase_b.py` (4 tests).

**Phase 2 — Legacy save migration**
- `frontend/editor_workflow_adapter.py`: added `migrate_legacy_deleted_node()`
  (pure function) and `EditorWorkflowAdapter.migrate_workflow_on_load()`.
  Converts `branch_end_node + _system_role: deleted_node_branch_end` to
  `tombstone_node` in-place without touching plain Merge Beacons.
- Tests: `tests/test_tombstone_migration.py` (7 tests).

**Phase 3 — Typed vault entries**
- `memory_bank.py`: `store_persistent` accepts `type_tag=None`;
  `read_persistent_by_type(type_tag)` added; state snapshot includes
  `persistent_type_tags`; backward compatible with old snapshots.
- `validator.py`: `_declared_membank_outputs` returns `Dict[str, Optional[str]]`
  (key → type_tag); warns on ai_session type mismatch.
- Tests: `tests/test_typed_vault.py` (9 tests).

**Phase 4 — LLM chat session in RunSession**
- `run_session.py`: `get_or_create_chat_session`, `append_chat_message`,
  `get_chat_history` (deep copy), `close_all` clears sessions.
- `validator.py`: warns when `use_chat_session: True` but `session_key` absent.
- Tests: appended to `tests/test_run_session.py` (8 new tests).

**Phase 5 — Parallel-branch vault race warnings**
- `validator.py`: added `_build_reverse_adjacency` and `_build_ancestor_set`
  (backward BFS). When all writers of a vault key are on parallel branches
  (none is an ancestor of the reader), emits a warning — not an error — to
  recommend a Wait Until node.
- Tests: `tests/test_validator_race_warnings.py` (6 tests).

**Phase 6 — Four utility nodes via aotn_node_helper**
- `backend/nodes/data/text_transform_node.py`: uppercase/lowercase/strip/title/reverse.
- `backend/nodes/data/json_path_node.py`: dot-path JSON extraction, `error` port.
- `backend/nodes/data/random_number_node.py`: integer/float in range, optional seed.
- `backend/nodes/io/http_request_node.py`: GET/POST via stdlib `urllib`, `error` port.
- Spec YAML files added to `aotn_node_helper/specs/`.
- `node_identity.py` extended with entries for all four nodes.
- Tests: `tests/generated/` (4 generated suites, mocked network for HTTP node).

---

## 2026-06-12 — Node Helper: Dynamic Forms, Standard Model Expansion, Config-UI Checks

- Implemented the dynamic-form schema keys planned in the Helper-Backed UI
  Standardization backlog:
  - `enabled_when`: field greys out unless a condition on other field values
    holds (mapping of field name to expected value; AND across entries, list
    values match any).
  - `visible_when`: hides the field, its label, and its description unless the
    condition holds.
  - `mutually_exclusive_with`: checking one boolean unchecks its declared
    partners; declarations are symmetric.
  - Implemented in `frontend/widgets/form_generator.py`
    (`evaluate_field_condition`, `apply_field_rules`,
    `mutual_exclusion_targets`, `schema_has_field_rules`); generated field
    labels/descriptions now carry `field-label-<name>` / `field-desc-<name>`
    ids so visibility rules can hide the whole block.
  - `NodeConfigScreen` applies rules at mount and on every generated-field
    change. Rules work across tabs: a Source tab selector can grey out a
    Parameters tab field, matching the NODE_STANDARDS greying behavior.
- Expanded `aotn_node_helper` with standard-model spec sections:
  - `input_sources`: expands each input into a `<name>_source` selector
    (Upstream payload / Vault / Configured), a gated `<name>_vault_key` field,
    and a gated Configured parameter field in the Parameters tab.
  - `output_routing`: expands into the mutually exclusive
    `transient_output` / `dead_drop_passthrough` pair plus optional
    `vault_write` / `vault_write_key` fields. Vault modes: `optional`,
    `default_on`, and `required_unless_transient` (locked on until transient
    output is checked — the Basic LLM node pattern).
  - Spec-time validation for rule keys: referenced fields must exist,
    mutual-exclusion participants must be booleans, standard fields must not
    collide with hand-written ones.
- Added `aotn_node_helper/check_ui.py <node_type>` and shared
  `aotn_node_helper/ui_checks.py`: mounts `NodeConfigScreen` and verifies
  every schema field renders, lands in its declared tab, participates in
  keyboard focus, and has correct rule state at mount. Structural nodes
  (branch/merge/branch-end) are rejected with a clear message.
- `create_node.py` now also emits `tests/generated/test_<node_type>_ui.py`
  (config-UI smoke test backed by `ui_checks`) when a spec uses `config_tabs`,
  `input_sources`, or `output_routing`.
- Added `aotn_node_helper/specs/example_file_instance_node.yaml` — the
  NODE_STANDARDS File Instance reference example expressed as a helper spec.
  Verified end-to-end: generated, check_node + check_ui + generated UI test
  all green. The generated node is REGISTERED in the project
  (`backend/nodes/io/example_file_instance_node.py`) for a live TUI pass of
  the dynamic config forms; remove it after the UI review if not kept.
- Registering the node surfaced a helper gap: generated nodes lacked Phase 17
  identity metadata, failing `test_node_factory_exposes_phase_17_identity_metadata`.
  Helper specs now require `primary_family` (Inputs / Flow Control / Outputs /
  Complex) and accept optional `tags` (validated against the Phase 17
  subcategory taxonomy), `icon_name`, and `color_hint` (defaults from the
  family color map). Generated nodes emit these as class metadata directly —
  no entry in the transitional `node_identity.py` table needed.
- Updated the node selector taxonomy test to include the registered example
  node in the Inputs family and File I/O filter expectations.
- Tests: new `tests/test_form_rules.py` (rule helpers + mounted
  NodeConfigScreen integration covering greying, visibility, and mutual
  exclusion both directions); extended `tests/test_node_helper.py` with
  standard-model expansion and validation cases. 11 focused tests pass.
- Known pre-existing flake (not from this change):
  `test_file_picker_export_and_import_paths` fails in a full-suite run but
  passes in isolation; reproduced identically on the clean tree.
- Docs updated: NODE_HELPER.md (standard sections, rule keys, check_ui,
  limitations/direction refresh), AGENT_START_GUIDE.md, NODE_STANDARDS.md
  (helper support note), PROJECT_BACKLOG.md (marked done items),
  PROJECT_KNOWLEDGE.md (form generator capabilities), FILE_TREE.md.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_node_helper.py tests/test_form_rules.py -v`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py` (121 passed +
    1 pre-existing flake)
  - `../.venv/bin/python -m compileall -q . ../aotn_node_helper`
  - `../aotn_node_helper/check_ui.py echo_node` / `logger_node` OK;
    `branch_node` correctly rejected as structural.

## 2026-06-11 — Node Standards Corrections: MemoryBank Model, Mutual Exclusion, JSON Payloads

- Corrected NODE_STANDARDS.md and PROJECT_KNOWLEDGE.md on three points:
  1. MemoryBank is always the underlying store for both transient and vault
     data. Transient uses ephemeral `(source_node_id, port_name)` keys; vault
     uses stable user-defined keys. The distinction is addressing scope, not
     separate storage systems.
  2. Transient output and vault write are not mutually exclusive. A node can
     write the same result to both simultaneously. The only mutual exclusion is
     "send my result as transient" vs "forward incoming transient unchanged
     (dead-drop passthrough)" — only one can occupy the transient port.
  3. Transient payloads are JSON and can carry any serializable value including
     large strings and LLM responses. The constraint is scope (path-scoped,
     not cross-branch), not size. Mentioned incremental document modification
     as a valid transient use case for LLM output.
- Clarified that active file I/O sessions are managed by the backend RunSession;
  files can serve as both inputs and outputs.
- Added "Later Project — Backend LLM Chat Session Persistence" to
  PROJECT_BACKLOG.md: session handles in RunSession, opt-in via session_key,
  shared history across nodes with the same key, validator warning if session
  not available.
- Updated docs: NODE_STANDARDS.md (input model note, output model mutual
  exclusion, data type scope, payloads tab diagram, LLM example notes,
  authoring checklist), PROJECT_KNOWLEDGE.md (Data Flow Patterns rewrite),
  PROJECT_BACKLOG.md (new LLM chat session backlog entry).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Node Design Standards Document

- Created `NODE_STANDARDS.md` as the authoritative reference for node I/O
  design before authoring any new node type.
- Documents the standard input source model: three mutually exclusive options
  per input (Upstream/transient, Vault, Configured). Selecting one greys out
  the other two in the form. Configured activates the matching Parameters tab
  field; Upstream or Vault selection greys that field out.
- Documents the standard output routing model: Transient output (send result
  downstream), Dead-drop passthrough (forward incoming payload unchanged,
  default for most nodes), and Vault write (save result under a named key,
  independent of transient/dead-drop choice). Transient and dead-drop are
  mutually exclusive per port; Vault write is independent.
- Documents data type scope: transient payloads carry only lightweight
  conditional data (bools, counters, flags); large strings, document text, and
  AI responses travel through the Vault or file I/O.
- Documents the standard Source / Parameters / Payloads / Connections tab
  structure with UI behavior rules for conditional field greying.
- Includes two reference examples:
  - File instance node: file path from upstream/vault/configured (mutually
    exclusive); bool transient output (success/failure); optional Vault write
    for error messages.
  - Basic LLM node: prompt from upstream/vault/configured (mutually exclusive);
    document/context from upstream or vault only (no configured option);
    dead-drop passthrough on by default; Vault write on by default and cannot
    be disabled unless transient output is active.
- Includes an authoring checklist: inputs, outputs, conditional fields, data
  types, mutual-exclusion rules, required vs optional Vault writes, and
  expected downstream pattern.
- Wired into `README.md` (task table and Read-First Files), `TASK_INDEX.md`
  (Add Or Change A Node route), and `AGENT_START_GUIDE.md` (Add A New Node
  section).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Tombstone Delete Semantics And Payload Design Context

- Clarified that node deletion is always single-node and non-cascading.
  Downstream nodes are never automatically deleted or modified. The tombstone
  sits in place as a swap-out and insert-staging placeholder; the graph beyond
  it remains intact. This is an editor-adapter invariant.
- Documented the transient payload vs vault (MemoryBank) design intent:
  transient payloads are primarily for conditional logic (booleans, counters,
  branch-decision flags); large strings, file contents, and shared data travel
  through the vault or file I/O. Many nodes consume from the vault directly and
  do not depend on the immediately upstream node's transient output.
- Added dead-drop context: the dead-drop option lets a node write a small
  conditional payload that a downstream node picks up without requiring a live
  transient connection through every intermediate node.
- Added restore severity context: because most data travels through the vault,
  tombstone restore-validation failures on transient ports are usually minor
  repairs, not broken workflows. The frontend alert should be informative but
  not alarming.
- Updated `PROJECT_KNOWLEDGE.md` (new "Data Flow Patterns" section, corrected
  Open Cleanup Areas entry) and `BACKEND_FRONTEND_BOUNDARY.md` (single-node
  delete rule and restore severity context added before the restore procedure).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Tombstone Restore Edge Cases And Connection Validation

- Specified tombstone restore validation rules for three categories of workflow
  drift that can occur between a node being deleted and a user triggering restore:
  (1) upstream output drift — source node removed or output port renamed/removed;
  (2) downstream input drift — target node removed, input port renamed/removed,
  or port now occupied by a different source; (3) memory bank drift — membank
  variables the deleted node depended on (`membank_inputs`) may no longer be
  declared by any surviving node.
- Restore procedure: always restore node type, alias, and config (never blocked).
  Validate each stored input connection and output connection before re-wiring.
  Leave failed connections unconnected. Surface a frontend alert after restore
  with named sections for input connection errors, output connection errors, and
  memory input warnings — each naming the original peer node alias, port, and
  failure reason. A partial restore is always preferred over leaving a tombstone.
- Edge case called out: branch-start nodes are particularly sensitive because the
  upstream branch node holds the dead-drop payload that seeds the branch. If the
  branch node's output port was renamed or its payload type changed since the
  delete, the connection will fail validation and the branch effectively remains
  broken until the user rewires it — the alert makes this visible.
- Updated `BACKEND_FRONTEND_BOUNDARY.md` (added "Tombstone restore — connection
  validation and partial restore" subsection) and `PROJECT_BACKLOG.md` (added
  restore validation spec to Phase B work items).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Tombstone Design Decision: Backend Type Stays

- Reviewed the Phase B tombstone decommission plan and decided to reverse it.
  `tombstone_node` will remain an intentional registered backend type, not a
  cleanup target.
- **What we had:** Phase A (done) moved frontend deletes to a visual-overlay
  model where saves materialized deleted nodes into `branch_end_node` records
  with a `_system_role: "deleted_node_branch_end"` marker. This worked with
  zero backend changes but had a key limitation: it is session-scoped. Saving
  after a delete, closing, and reopening loses undo context. The
  `branch_end_node` port shape also limits how much original connection data
  the validator can surface.
- **Why we switched:** The save file is the only persistence layer. Keeping
  full original node data (type, alias, config, input connections, output
  connections) in a `tombstone_node` record gives: (1) undo that survives
  save/reload, (2) validator errors that name the original node and describe
  its original connections as a repair guide, (3) meaningful port-validity
  errors from the stored original port shape.
- **New contract:** tombstone config stores `original_type`, `original_alias`,
  `original_config`, `original_inputs`, `original_outputs`. The validator
  tombstone error block should be extended to surface the original connection
  context. The node selector already excludes tombstone. Execution is already
  blocked on workflows containing tombstones.
- **Phase B redefined:** instead of decommissioning tombstone, Phase B now
  updates `editor_workflow_adapter.py` to write `tombstone_node` on save
  (not `branch_end_node`), migrates existing `_system_role` marked records on
  load, extends the validator error block, and confirms `editor_only` flagging
  in `node_identity.py`.
- Updated docs: `BACKEND_FRONTEND_BOUNDARY.md` (major rewrite of Phase B and
  Deleted-Node Save Contract sections), `PROJECT_BACKLOG.md` (Phase B
  redefined), `MASTER_BUILD_PLAN.md` (added Phase 10.6), `ARCHITECTURE.md`
  (tombstone table row and description), `AGENTS.md` (tombstone footnote).
- No code changes in this session — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-10 — Two-Line Selector Rows, Editor Selector Spacing

- Node selector rows are now two lines: line one is the display name plus the
  subcategories in parentheses (the family is omitted as redundant with the
  active tab), line two is the node description indented four spaces (truncated
  past 76 chars) for clear visual separation between nodes. Added
  `_node_row_text`, a `.node-select-row` height-2 style, and
  `#node-type-list ListItem { height: auto }`.
- Editor: removed the blank line below branch/merge selector rows. The
  trailing spacer (`node-row-spaced`) now only applies to node rows that are
  not immediately followed by a selector; selector rows never add a blank
  line below themselves. The next node hugs the selector.
- Tests: added
  `test_node_selector_rows_are_two_lines_with_indented_description`; extended
  `test_editor_identity_rows_fit_rendered_panel_width` with a node after the
  branch selector to assert no blank line below the selector.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/ -v` (134 passed)
  - `git diff --check`

## 2026-06-10 — Node Selector/Config Layout And Navigation Audit

Focused pass on the Node Selector and Node Config modals.

- Selector headspace: `Horizontal`/`Vertical` containers default to
  `height: 1fr`, so `#node-family-tabs` and `#node-subcategory-filters`
  stretched and left dead space between the tab row and filter bar, and the
  stretch clipped the last subcategory checkbox on short terminals. Added
  explicit `height: auto` for the tab row, filter, and subcategory block, and
  `height: 1fr; min-height: 4` for `#node-type-list` so the node list absorbs
  the remaining space and every checkbox renders fully.
- Config phantom-focus / "two presses, highlight vanished": the hidden payload
  preview widgets (collapsed `PayloadPreview`s with their own
  `display: false`) were still keyboard-focus stops because
  `_keyboard_focus_widgets` only checked ancestor visibility, not the widget's
  own display. Focusing a hidden widget shows no cursor, so it read as a lost
  highlight needing a second key press. Now skips widgets whose own
  `display` is False; revealed previews remain real stops.
- Selector list highlight: re-entering the node list with an unchanged index
  left no visible cursor because `ListView.watch_index` only fires on a
  changed value. `focus_list` now re-asserts the highlight (None then index)
  so stepping down from the last subcategory checkbox lands on the first node
  with a visible highlight.
- Tests: added `test_node_config_keyboard_skips_hidden_payload_previews`,
  `test_node_selector_layout_is_compact_and_checkboxes_fit` (asserts no
  tabs->filter gap and no clipped checkboxes at 30- and 22-row terminals), and
  `test_node_selector_down_from_last_checkbox_highlights_first_node`.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/ -v` (133 passed)
  - `git diff --check`

## 2026-06-10 — Blank Editor Fix, Selector Row Placement, No-Alias Rows

- Fixed the blank editor: the family-background change defined
  `NodeCard._render_content`, which silently shadowed Textual's internal
  `Widget._render_content` paint method (textual/widget.py), making every
  card render blank while still holding correct content. Renamed to
  `_card_content` with a warning comment. The regression test now asserts
  actual painted output via `render_line`, not just stored content —
  content-only assertions completely missed this bug.
- Branch selector and merge-beacon jump rows now sit directly below their
  node: `NodeList.refresh_rows` places the spacer line after each node's
  full row group (after the node row, or after its trailing selector rows)
  instead of unconditionally after every node row.
- Selector rows gained two leading spaces so their label column lines up
  with the framed node text above; updated the editor-depth test's pinned
  selector string.
- Identity rows with an empty alias now render `No alias` on the first
  line instead of falling back to the raw node type string (Merge Beacon
  and legacy tombstone naming keep their special-cased names).
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows or node_card or branch_end or deleted"` (3 passed in slice)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Identity Row Family Backgrounds

- Editor node rows now fill the framed segment (between and including the
  brackets) with the family color previously used for the font, and flip
  the segment font to dark high-contrast `#0d1117`:
  Inputs `#7ee787`, Flow Control `#8ab4f8`, Outputs `#f2cc60`,
  Complex `#c586c0`, Utility-tagged rows `#9aa7b3`.
- The gutter (depth number) stays unstyled, so the depth column and the
  right inset still show selection highlight. Merge Beacon health rows and
  deleted-node rows keep their existing color priority and get no family
  background.
- Styled rendering only applies to mounted cards; unmounted cards (unit
  tests) fall back to plain text because Rich content requires the app
  console.
- Extended the identity-row regression test to assert the framed spans
  carry the family background and dark foreground while gutter columns
  stay unstyled.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows or node_card or branch_end or deleted"` (3 passed in slice)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Identity Row Polish: Right Inset And Row Spacing

- Closing frames now sit `FRAME_RIGHT_INSET` (2) columns in from the right
  edge of the node-list panel instead of touching it.
- Editor node rows get one blank spacer line below them: `NodeList`
  tags node-row `ListItem`s with `node-row-spaced` (margin-bottom in
  `styles.tcss`). Branch select and merge beacon rows keep their
  single-line height with no spacer. The margin lives on the `ListItem`
  because item auto-height clips a child card's own margin.
- `NodeCard.on_mount` re-fits once after first layout via
  `call_after_refresh`, fixing rows that rendered at the unmounted
  fallback width inside `ListView`s when no Resize event fired.
- Extended `test_editor_identity_rows_fit_rendered_panel_width` to run the
  real `NodeList.refresh_rows` path with the real `styles.tcss`, asserting
  the right inset, the one-line spacer between node rows, and the
  unspaced single-line branch selector row.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows"` (3 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Phase 17 Reopened: Identity Row Width Fix

- Live-TUI verification showed Phase 17 editor rows were broken in real
  panels: identity rows padded text to a fixed 48-char width, so the
  node-list panel (narrower than ~58 columns with gutter and frames)
  soft-wrapped each row — the closing frame landed alone at column 0 of the
  next visual line and the family/subcategory identity line was pushed out
  of the two-line row entirely.
- Fixed `NodeCard` to fit framed text to the rendered card width:
  `_identity_text_width()` derives the text column from `content_size`
  (fallback to the old fixed width for unmounted cards), `_fit_text` takes
  the width as a parameter, and `on_resize` re-renders rows so frames track
  panel-width changes. Applies to identity rows and deleted-overlay rows.
- Added `test_editor_identity_rows_fit_rendered_panel_width`: mounts a
  `NodeCard` in a 40-column panel and asserts two lines, no line wider than
  the panel, aligned closing frames, and a visible family identity line.
- Reverted the premature Phase 17 completion claims in
  `MASTER_BUILD_PLAN.md`: phase status back to In progress with a
  live-TUI verification todo (manual editor check at several terminal
  widths) before the phase can close.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows or node_card or editor_depth or deleted"` (3 passed in slice)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Working-Tree Port From OneDrive Checkout

- Discovered that this date's agent sessions had been editing a second
  checkout of the repo under OneDrive
  (`C:\users\makin\onedrive\documents\node_workflow`) instead of the
  WSL-local tree. Both trees shared the same HEAD commit.
- Ported all session source changes (backend RunSession + validation,
  Phase 17 frontend identity/selector/deleted-node work, tests, and docs)
  from the OneDrive working tree into this tree.
- Hand-merged the five docs that had independent local changes
  (`FILE_TREE.md`, `PROJECT_BACKLOG.md`, `README.md`, `SESSION_LOG.md`,
  `TASK_INDEX.md`) so the local `NODE_HELPER.md` documentation work and
  the ported entries both survive. Local `.gitignore` and `NODE_HELPER.md`
  were kept as-is. Runtime artifacts (`run_errors/`, `run_history/`,
  `run_outputs/`) were not ported.
- Pre-merge copies of the locally dirty files are saved at
  `~/src/node_workflow_port_backup/`.
- Verification (run from this tree):
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/ -v`
  - `git diff --check`

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
- Captured the metadata gap: `Node` has optional identity fields, but
  `NodeFactory.get_node_types_metadata()` must expose category/tag/icon/color
  metadata before the selector can depend on it.
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

## 2026-06-10 — Node Helper Documentation And UI Standardization Notes

- Added `NODE_HELPER.md` as the detailed guide for `aotn_node_helper` specs,
  generated files, supported templates, config tabs, structural UI guardrails,
  and current limitations.
- Linked the helper guide from `README.md` and `TASK_INDEX.md` so node work can
  start from the short docs and dive into the helper details only when needed.
- Added a backlog project for helper-backed UI standardization: generated
  config UI checks, keyboard smoke tests, dynamic-section schema support, screen
  scaffolds, and screen/UI manifests.
- Verification:
  - `git diff --check`
  - `rg -n "NODE_HELPER|aotn_node_helper|Pending in this session|docs/README.md|docs/TASK_INDEX.md" AttackOfTheNodes/docs AGENTS.md`
  - `./.venv/bin/python -m pytest AttackOfTheNodes/tests/test_node_helper.py -q`
  - `./.venv/bin/python -m compileall -q AttackOfTheNodes`
  - `./.venv/bin/python -m compileall -q aotn_node_helper`

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

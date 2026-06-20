# AttackOfTheNodes Session Log

This active log keeps recent/current entries only. Full older history was
collapsed into `archive/SESSION_LOG_HISTORY.md` during the documentation
overhaul.

## 2026-06-19 — Docs: Reconcile Removed Subcategory Filter

- Follow-up to step 4: updated the UI docs that still described the removed
  subcategory filter-checkbox column. `UI_QUICK_REFERENCE.md` and `TUI_DESIGN.md`
  fully reconciled — no subcategory checkboxes, focus lands on the string filter,
  `tags` are freeform search keywords, details panel shows the per-port contract.
- `PHASE_17_NODE_VISUAL_IDENTITY.md` (the authoritative selector/visual-identity
  design doc, woven through with the subcategory concept): added a prominent
  "Revision — 2026-06-19" callout superseding the subcategory-filter design, and
  surgically fixed the most concrete false-existence claims (the per-tab filter
  table, the `tags` metadata description, the editor-row identity line, the
  details-panel statement). The deeper narrative rewrite is deliberately folded
  into the upcoming selector UI redesign rather than duplicated here.
- Branch `codex/docs-subcategory-reconcile` → fast-forwarded into `main`.

## 2026-06-19 — Track A Step 4 (owner-revised): Retire Subcategory Filter

- Continued on `codex/canonical-data-types` (after step 3). **Owner revised the
  adopted handoff:** the Category > Family > Type rename (§2.1/§3) is
  **cancelled** — the top tier keeps `primary_family` ("family") and the variant
  grouping keeps `group`. Instead, step 4 became **retiring the subcategory
  taxonomy** (`tags`), "never utilized correctly." Chosen scope (owner): remove
  the subcategory filter UI, keep `tags` as freeform search keywords.
- Frontend: removed the subcategory **filter-checkbox column** and all its
  machinery from `frontend/screens/node_selector.py` — the
  `#node-subcategory-filters` block, the `_selected_subcategories` filtering in
  `_apply_filter`, `on_checkbox_changed`, `_sync_subcategory_filter_visibility`,
  `_sync_selected_subcategories`, `_visible_subcategory_checkboxes`, the
  `TAB_FILTER_TAGS`/`ALL_FILTER_TAGS` constants, and the `Checkbox` import.
  `tags` still feed `_matches_query` (search). Dropped the matching
  `#node-subcategory-filters` rule from `styles.tcss`.
- Helper: dropped the rigid `VALID_TAGS` enforcement in
  `aotn_node_helper/generator.py`; tags are now freeform (any non-empty string).
- Tests: reworked the three selector tests in `test_debug_nodes.py` that
  depended on the filter checkboxes — renamed to drop "checkboxes/subcategory"
  and re-pointed navigation through the filter input; updated the runner list.
  Updated `test_node_helper.py` to assert freeform tags are accepted (was
  asserting rejection).
- Verified: `compileall -q .` clean; **full suite 331 passed**.
- Scope held: NO rename of `primary_family`/`group`/`category` (cancelled by
  owner); `tags` retained for search only. Docs: handoff Revision callout,
  `PROJECT_KNOWLEDGE.md`, `NODE_HELPER.md`. **Follow-up:** `PHASE_17_NODE_VISUAL_
  IDENTITY.md`, `TUI_DESIGN.md`, and `UI_QUICK_REFERENCE.md` still describe the
  removed subcategory filter UI and need a reconciliation pass.

## 2026-06-19 — Track A Step 3: Unified inputs:/outputs: Helper Spec

- Continued on `codex/canonical-data-types` (after step 2). Track A step 3 (§7):
  unified `inputs:` / `outputs:` helper-spec blocks carrying the full per-port
  contract, plus generator/check/test updates and one regenerated reference
  node. Read §7 precisely: it replaces `input_sources` + `input_port_metadata`
  (→ `inputs:`) and `output_port_metadata` (→ `outputs:`); node-level
  `output_routing` (Payloads config) is unchanged. Implemented additively so the
  six existing legacy specs keep generating.
- `aotn_node_helper/generator.py`: added `_expand_inputs_block` /
  `_expand_outputs_block` / `_contract_metadata`, and refactored the per-input
  source expansion into a shared `_input_source_fields` so the unified `inputs:`
  block and the legacy `input_sources` section emit byte-identical
  Source/Parameters fields. Port lists derive from the block keys; declaring a
  block alongside its legacy section (or `input_ports`/`output_ports`) is
  rejected. Port metadata now carries `data_type` / `required` / `sources`
  (inputs) and `data_type` / `required` / `to` / `pass_through` (outputs).
  Unknown port types **warn** (stderr), matching §5's soft-convention intent;
  `boolean` canonicalizes to `bool`. Added a local `CANONICAL_DATA_TYPES` mirror
  (kept in sync with `backend/data_types.py`, same pattern as `VALID_FAMILIES`).
  Render type hints for port metadata widened to `Dict[str, Dict[str, Any]]`;
  the generated focused test now asserts the per-port contract is exposed.
- Regenerated the reference node `example_file_instance_node` from the rewritten
  unified spec (`--force`). Diff confirms `config_schema` is **byte-for-byte
  unchanged** (round-trip equivalence — the `file_path_*` selectors are
  identical) while the port metadata gains the contract (`data_type` file/bool,
  `required`, `sources`/`to`, `pass_through`). Its input port is renamed
  `input → file_path` so the port name and source-field prefix are one name (the
  point of the unified model). `check_node` and `check_ui` both pass.
- Updated `tests/test_node_contract.py` (the step-2 assertion that the reference
  node had no declared type now asserts the declared bool/file contract).
  Added `tests/test_node_helper.py` cases: unified block emits the same
  selectors + adds contract, rejects legacy-section mix, rejects unknown `to`
  destinations, and warns (without raising) on an unknown port type.
- Verified: `compileall -q .` clean; helper + contract + data-type tests 26
  passed; **full suite 331 passed** (was 328; +3 new helper tests).
- Scope held: only ONE node regenerated (mass regeneration deferred, §11);
  Payloads routing still per-node via `output_routing` (per-port routing config
  is Track B step 7); no rename of `primary_family→category` / `group→family`
  (step 4). Docs: `NODE_HELPER.md` (new Unified inputs:/outputs: Blocks section).

## 2026-06-19 — Track A Step 2: Per-Port I/O Contract Fields

- Continued on `codex/canonical-data-types` (after the step 1 commit). Track A
  step 2 (§4/§6): add the per-port contract fields to node classes and expose
  them through `NodeFactory`, additive with documented defaults.
- `node_base.py`: documented the `input_port_metadata` / `output_port_metadata`
  contract (now `Dict[str, Dict[str, Any]]`) and added
  `_validate_port_data_types()`, called from `__init_subclass__`, which warns
  (not raises) via `data_types.validate_type` when a declared port `data_type`
  is outside the canonical set. This is the helper-facing validation surface the
  step 1 note promised, wired at class-definition time.
- `node_factory.py` `_port_metadata`: fills the §6 forward-compat defaults on
  exposure — absent `data_type` ⇒ `any`, absent `required` ⇒ `False` — and
  canonicalizes declared types (deprecated `boolean` ⇒ `bool`) via
  `coerce_type`. Existing nodes (which declare neither field) now expose
  `data_type: "any"` / `required: false` on every port with no node-file edits.
- Tests: `tests/test_node_contract.py` (defaults on every registered port,
  absent ⇒ any/optional, canonicalize+coerce, declared metadata survives
  exposure, unknown port type warns at class definition, canonical/alias types
  stay quiet). Verified: `compileall -q .` clean; `test_node_contract.py` +
  `test_data_types.py` 15 passed; `test_debug_nodes.py` + `test_node_helper.py`
  + `test_typed_vault.py` 150 passed; **full suite 328 passed**.
- Scope held: no node files regenerated (defaults are filled at exposure, so no
  per-node `required`/`data_type` were authored — that reference-node pass is
  step 3); `from:` / `to:` routing destinations are **not** exposed yet (they
  belong to the unified helper-spec step 3); validator does not yet consume
  `required` for incomplete-input detection (deferred with the frontend
  coloring per §6). No rename (step 4). Docs: `NODE_STANDARDS.md` (new Per-Port
  Contract Metadata section), `PROJECT_KNOWLEDGE.md` (metadata-exposure note).

## 2026-06-19 — Track A Step 1: Canonical Data-Type Module

- Branched `codex/canonical-data-types` from `main` @ `872ae66` (Add adopted
  Node Standardization Handoff doc). `git fetch` left the local base as the
  freshest reachable commit (SSL trust issue, per repo norm).
- Implemented `NODE_STANDARDIZATION_HANDOFF.md` Track A step 1 (§5): new
  `backend/data_types.py` is the single source of truth for the coarse
  data-type vocabulary shared by node port data types **and** typed vault-entry
  tags. Canonical set: `string`, `number`, `bool`, `var`, `file`, `ai_session`,
  `any`. `file`/`ai_session` are RunSession-backed reference types; `any` is the
  explicit permissive default (no silent untyped).
- **Reconciled** the vault-vs-port spelling conflict the handoff flagged: the
  typed-vault docs spelled boolean `boolean`; §5 (authoritative) uses `bool`.
  Canonical is now `bool`; `boolean` survives only as a deprecated alias that
  `canonicalize()` maps to `bool`, so older specs / saved workflows still
  resolve. No code stored the `boolean` literal (only docs + the `ai_session`
  literal in the validator), so the reconciliation is doc + alias only.
- Routed the one existing typed-vault consumer through the module: `validator.py`
  now compares against `DataType.AI_SESSION.value` instead of a free `"ai_session"`
  string. MemoryBank stores free `type_tag`s and is unchanged (no validation
  there); the validator is the meaningful single consumer today.
- Public surface: `DataType` enum, `CANONICAL_TYPES`, `REFERENCE_TYPES`,
  `DEFAULT_TYPE`, `LEGACY_ALIASES`, `UnknownDataTypeWarning`, and functions
  `is_valid_type`, `validate_type` (helper-facing — warns on unknown),
  `is_reference_type`, `canonicalize`, `coerce_type`, `port_data_types`,
  `vault_entry_types`, `unknown_types`.
- Tests: `tests/test_data_types.py` (canonical set, membership/validation,
  bool-not-boolean, reference types, explicit-`any` default, unknown-type
  warning, canonical-types-do-not-warn, vault/port lists agree). Verified:
  `compileall -q .` clean; `test_data_types.py` + `test_typed_vault.py` 18
  passed; `test_debug_nodes.py` 133 passed.
- Stayed in scope: no contract schema fields on node classes (step 2), no
  `primary_family→category` / `group→family` rename (step 4), no node
  regeneration or frontend selector edits. Docs touched: `NODE_STANDARDS.md`
  (Typed Vault Outputs), `PROJECT_KNOWLEDGE.md` (vault paragraph + Backend
  Components). Nothing required owner escalation — the only conflict (`boolean`
  vs `bool`) was resolved by the handoff itself.

## 2026-06-19 — Node Standardization Handoff Adopted

- Added `NODE_STANDARDIZATION_HANDOFF.md` (status: Adopted) — the design handoff
  consolidating the per-node I/O contract, Category > Family > Type rename,
  canonical data-type vocabulary, unified `inputs:`/`outputs:` helper spec, and
  master-detail selector into one implementation plan.
- Owner signed off the four §2 open decisions: (1) terminology rename approved,
  reusing the existing `category` key as canonical and retiring the
  `primary_family`/`legacy_category` aliases (`group → family`, `type`
  untouched); (2) drill-in family navigation; (3) one-line-per-port `to:`
  display in the detail panel; (4) no behavior badge — description carries
  behavior. Folded these into §2 (locked) and the affected body sections.
- Wired the router: README Document Directory row under Node Authoring + a
  `DOCS_MIGRATION_NOTES.md` "added" entry. Whitespace/LF clean.
- Not yet implemented — this is the plan. Next: Track A step 1 (canonical
  data-type module, §5). Track A step 4 (rename) runs after the contract schema
  work to avoid double-churning the same files.

## 2026-06-19 — Docs Audit: Taxonomy + Catalog Drift Fixes

- Ran the docs audit (active docs only) on `main` @ `2b681f2`. Verified
  environment: Python 3.14.4, Textual 8.2.7; registry has 35 nodes across 5
  families (Inputs, Outputs, Flow Control, Utility, Complex); backend has no
  `frontend` imports; `test_debug_nodes.py` 133 passed. Router integrity OK
  (all 19 active docs + 7 archive entries resolve).
- DRIFT (doc-vs-doc, Known Finding #1): `PROJECT_KNOWLEDGE.md` "Planned Node
  Taxonomy" listed four families with Utility as a subcategory. Reconciled to
  Phase 17's five families (Utility promoted) + four-tab / I/O-switch note.
  PHASE_17 is authoritative. Left the subcategory/`tags` concept intact
  (Known Finding #3 retirement still awaits owner decision).
- DRIFT (doc-vs-code): `NODE_CATALOG.md` omitted/mis-statused 4 live registered
  nodes. Added `http_request_node` (HTTP Request, Live) under Data Source;
  marked `text_transform_node` and `json_path_node` rows Live with `Maps from`;
  added `random_number_node` (Random Number, Live) under Data Transform.
- Did not edit `primary_family`/`tags` terminology in PROJECT_KNOWLEDGE or
  PHASE_17 (Known Findings #2 and #3 await owner decision).

## 2026-06-17 — Tabbed UI Keyboard Navigation Rework

- Branched `codex/keyboard-nav-rework` from `codex/textual-ui-overhaul`
  (commit `0bba5f6`, the just-committed Phase 17 visual overhaul), which is
  `main` + node-type-constants + the overhaul. `git fetch` is blocked by a
  local SSL trust issue, so the freshest reachable base was the local commit.
- WS1 — Row-based 2D navigation in the shared modules: added
  `group_widgets_into_rows` / `row_move_target` / `within_row_target` to
  `command_navigation.py` (rows grouped by nearest `Horizontal` ancestor, then
  by visual line, else one-per-row). `CommandScreenMixin` now moves W/S between
  rows (preserving column) and A/D within a row, gated so single-widget rows
  fall through to caret movement.
- WS1-apply — `node_config` and `node_selector` dropped A/D-as-tab-switch
  (including `CommandInput`'s `_run_screen_tab_action`); A/D is within-row. The
  selector I/O control is a two-button row (A/D between sides, E selects).
- WS2 — Number keys `1`–`5` jump tabs (gated to nav mode, no-op past the count);
  tab headers numbered `N - Label` in config and selector.
- WS3 — Verified the execution input prompt already uses `auto_edit_on_focus`.
- WS4 — `activate_command_widget` single-press toggles `Checkbox`/`Switch`.
- Stacked-widget audit (one-line rows of focusable widgets in command-mode
  screens): `node_selector` `node-family-tabs` (4 tab buttons) and
  `io-direction-row` (2-button I/O toggle). The simple modals
  (`confirm`/`error_details`/`user_input`) have `button-row` Horizontals but
  drive them with dedicated letter keys; the row model now also makes those
  navigable. `node_config` has no horizontal rows.
- Tests updated to the new contract and new tests added (row nav, within-row
  A/D, number jumps, digit-types-while-editing, single-press toggle). Full
  suite green: 311 passed.
- Flagged the selector family-taxonomy discrepancy (docs say Inputs/Outputs;
  code uses I/O + Utility) as a separate follow-up in `PROJECT_BACKLOG.md`.

## 2026-06-17 — Frontend Node-Type Constants Pass

- Started from branch `codex/node-type-constants` at `64dfb52`, after
  fast-forwarding `main` from `origin/main`.
- Added `frontend.node_types` as the frontend-owned home for structural node
  type identifiers used by editor/control-room behavior:
  `start_node`, `end_node`, `branch_node`, `branch_end_node`, `merge_node`,
  `text_output_node`, `tombstone_node`, and `wait_until_node`.
- Replaced repeated frontend literals in app startup, editor traversal/delete
  logic, editor workflow adapter tombstone/branch pruning logic, node config
  merge/wait/branch handling, node selector hiding, node card rendering, and
  node I/O display helpers.
- Preserved persisted workflow data shape: node `type` values remain the same
  strings. No branch pruning, merge deletion, tombstone restore, selector, or
  runtime logic was intentionally changed.
- Left test workflow fixture literals in place unless production imports
  benefited directly; those fixtures document saved/workflow data shapes.
- Deferred membank-registry consolidation and branch-port list consolidation
  to their separate passes.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "tombstone or branch_end or merge_node or node_selector or editor"` (41 passed)
  - `../.venv/bin/python -m pytest tests/test_branch_prune.py tests/test_branch_health.py tests/test_tombstone_restore.py tests/test_tombstone_migration.py tests/test_tombstone_phase_b.py -v` (58 passed)
  - `../.venv/bin/python -m pytest -q` (308 passed)

## 2026-06-16 — Frontend Review Cleanup Pass

- Started from branch `codex/frontend-review-cleanups` at `03e6432`, aligned
  with `origin/main` after PR #20.
- Continued the frontend convention review from the Pass 1/2/3 inventory.
- `EditorScreen._metadata_for_type()` and `NodeConfigScreen._metadata_for_type()`
  now delegate to the shared `frontend.node_io_display.metadata_for_type()`
  helper.
- `NodeConfigScreen` now uses the shared membank normalizers from
  `frontend.node_io_display` instead of maintaining duplicate definitions.
- Removed unused `EditorScreen._format_input_ports()` and
  `_format_output_ports()`.
- Deferred wider follow-ups to separate passes: node-type constants,
  membank-registry consolidation, branch-port list consolidation, and selector
  tab-name docs drift.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_config or editor_identity_rows or quick_view or payloads_tab or command_inputs"` (20 passed)
  - `../.venv/bin/python -m pytest tests -v` (308 passed)

## 2026-06-16 — Branch Pruning Ignores Unreachable Merge Feeds

- Continued debugging on branch `delete_branch_bug` after pulling
  `origin/delete_branch_bug`.
- Found a remaining branch-prune gap: `prune_branch_tombstone()` preserved a
  `merge_node` whenever any input source existed outside the pruned set, even
  if that source was itself unreachable from `start` after the branch tombstone
  was removed. That could leave merge tails alive in `_nodes`, and the
  validator would still report them as unreachable after the editor appeared to
  have pruned the branch.
- Fixed merge preservation to use post-prune reachability: simulate removing
  the branch tombstone and current prune set, add the kept-path upstream
  rewire, and only count merge input sources reachable in that future graph.
  Reachable alternate feeds still preserve the merge; loose/unreachable feeds
  no longer do.
- Added focused coverage for both cases in `tests/test_branch_prune.py`,
  including a validation assertion for the surviving-feed path.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_branch_prune.py -v` (15 passed)

## 2026-06-16 — Merge Delete Rewires Home Branch and Flags Open Beacons

- Reported as: deleting a `merge_node` made downstream nodes disappear from
  the usable path. Desired behavior is to delete only the merge node, bridge
  the branch where the merge lived to the immediate downstream node when ports
  are compatible, and disconnect Merge Beacon inputs from other branches so
  the user can rewire them manually.
- Fixed `EditorWorkflowAdapter.remove_placeholder()` with a merge-specific
  reconnect path: after `WorkflowMap.delete_node()` removes the merge and all
  beacon→merge references, the adapter reconnects the non-`branch_end_node`
  upstream input to the merge's direct downstream output if both ports are
  declared and currently open. Beacon branches are intentionally not rewired.
- `validate_workflow()` now uses backend branch-health derivation to warn when
  a branch reaches a Merge Beacon that is not connected to a merge node, so
  disconnected beacons left by merge deletion surface as repair work.
- Updated editor and branch-health tests for the new contract.
- Verification:
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_prune.py -v` (15 passed)

## 2026-06-16 — Branch Pruning Treats Output Nodes as Terminal Boundaries

- Reported as: deleting a branch could leave a `text_output_node` from the
  pruned branch alive in validation even though the editor no longer showed a
  reachable path to it.
- Decided against a mutable `valid_branch_end` config flag. The boundary is a
  node-type contract, so pruning now derives terminal behavior from node
  semantics: Outputs-family nodes, `text_output_node`, `end_node`, and Merge
  Beacons are inclusive branch-prune boundaries.
- Updated `prune_branch_tombstone()` so terminal nodes on non-kept branches are
  deleted but traversal does not continue past them. Merge Beacons remain a
  special terminal: they are deleted and any connected `merge_node` is still
  evaluated for orphan cleanup.
- Added a regression proving a pruned branch ending at `text_output_node`
  removes that output node and validation no longer reports it.
- Verification:
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_prune.py -v` (16 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)

## 2026-06-16 — Kept Merge Beacon Branch Drops Old Merge Output

- Reported as: simple branch workflow with path A containing a `merge_node` and
  path B containing a Merge Beacon connected to that merge. Deleting the branch
  node, keeping the Merge Beacon branch, and pruning the merge branch left the
  old merge connection in the kept beacon's later tombstone metadata; deleting
  the beacon then rendered the pruned merge below the tombstone.
- Root cause: branch-prune survival checks simulated future reachability by
  following the kept branch head's current outputs. For a kept Merge Beacon,
  that meant following its pre-prune output into the merge and treating the
  merge as still live.
- Fixed: Merge Beacons are now included in `_is_branch_prune_terminal()`.
  `prune_branch_tombstone()` disconnects outputs from the kept branch terminal
  before resolving pending merges, and the future-reachability simulation stops
  at terminal nodes. The kept beacon remains as an open terminal, while the
  old merge is pruned and cannot be captured in later tombstone
  `original_outputs`.
- Added a regression covering the exact keep-beacon/prune-merge sequence and
  later beacon tombstone materialization.
- Verification:
  - `.venv/bin/python -m pytest tests/test_branch_prune.py -v` (17 passed)
  - `.venv/bin/python -m pytest tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)
  - `.venv/bin/python -m compileall -q .`

## 2026-06-16 — Kept Merge Branch Preserves Merge Downstream Nodes

- Reported as the mirror case of the kept-beacon fix: path A contains a
  `merge_node` and downstream output node, path B contains a Merge Beacon
  connected to that merge. Deleting the branch node and keeping path A pruned
  the beacon branch, but also pruned the merge's downstream nodes.
- Root cause: pending merge cleanup only considered the merge's old input
  sources. In the kept-merge case, the old input source is the deleted branch
  node, but the future graph rewires the branch node's upstream directly into
  the merge. The cleanup therefore misclassified the kept merge as orphaned
  and cascaded into its downstream nodes.
- Fixed pending merge resolution to treat the kept branch head as live when it
  is the pending `merge_node` and it is reachable in the simulated future graph.
  The pruned Merge Beacon branch is still deleted; the kept merge and its
  downstream output chain remain intact.
- Added a regression for path A `merge_node -> text_output_node`, path B
  `Merge Beacon -> same merge`, keep path A.
- Verification:
  - `.venv/bin/python -m pytest tests/test_branch_prune.py -v` (18 passed)
  - `.venv/bin/python -m pytest tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)
  - `.venv/bin/python -m compileall -q .`

## 2026-06-16 — Insert Into Empty Branch Now Targets the Branch Being Viewed

- Reported as: switch to an empty parallel branch (`d`), insert a node — it
  visually shows up there, but switching away and back makes it disappear
  from that branch and reappear on a different one (whichever branch's port
  is declared first on the `branch_node`).
- Root cause: when the active branch path is empty, there is no node to
  select yet, so the selected row falls back to the `branch_node` itself with
  `kind: "node"` rather than `kind: "branch_select"`. `_source_for_insert_node()`
  has a correct `branch_select`-specific case that reads `active_branch_ports`,
  but the generic `kind: "node"` fallback just used the branch node's first
  declared output port unconditionally — ignoring which branch was actually
  being viewed.
- Fixed: in that fallback, when the selected node has multiple output ports
  (i.e. it's a branch node) and an active branch port is recorded for it, use
  that active port instead of always taking the first one.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest -q` (303 passed, includes new
    `test_editor_insert_into_empty_branch_uses_active_branch_port`)
  - Reproduced via a standalone Textual pilot script matching the reported key
    sequence exactly (create branch, fill path_a, `d` to path_b, insert, `a`
    back to path_a, `a` again) before and after the fix.

## 2026-06-16 — Branch Pruning No Longer Leaves Orphaned Merge Beacons or Merge Nodes

- Reported as: deleting a branch whose non-kept path fed a Merge Beacon (which
  in turn fed a `merge_node`) left a node behind that the validator flagged as
  unreachable, even after the workflow looked fully repaired in the editor.
- Root cause #1: `prune_branch_tombstone()`'s stop-type set included
  `branch_end_node`, treating Merge Beacons as permanent structure. A beacon
  belongs exclusively to the one branch it closes, so a beacon reached while
  pruning a non-kept branch must be deleted along with the rest of that
  branch, not preserved.
- Root cause #2 (cascading orphan): `merge_node` was an *unconditional* stop
  type. If the branch being pruned was a `merge_node`'s only remaining input,
  the merge_node was left behind fully disconnected from upstream — alive in
  the workflow but unreachable from start, with no way to fix it short of a
  manual node delete (re-typing it via the node selector keeps the same
  disconnected node, since type-swap doesn't restore connections).
- Fixed: `branch_end_node` removed from the stop-type set entirely. `merge_node`
  is now a *conditional* stop — pruning resolves each encountered merge_node by
  checking whether any of its current inputs come from a source outside the
  pruned set (and outside the branch tombstone itself). If none remain, the
  merge_node is pruned too, and pruning cascades through its own downstream
  nodes (re-applying the same check to any further merge_node reached that
  way). A merge_node with a genuinely surviving feed (another live branch)
  is still preserved untouched.
- Confirms the broader guarantee: pruned nodes go through
  `WorkflowMap.delete_node()`, which removes them from the same `_nodes` dict
  that gets serialized on save — a pruned node cannot reappear in a save file
  or in any validator output once `prune_branch_tombstone()` correctly
  identifies it for pruning.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest -q` (302 passed)
  - End-to-end repro matching the reported scenario (branch → kept path into
    merge_node path_a, pruned path → Merge Beacon → merge_node path_b → output):
    validator returns `{"success": true, "errors": [], "warnings": []}` after
    pruning, with only 3 nodes left in the workflow.

## 2026-06-16 — Merge Config No Longer Offers Downstream Branches to Close

- `merge_input_options()` listed every `branch_end_node` in the workflow as a
  candidate to close, including beacons whose owning branch point only starts
  *after* passing through the merge node being configured. Closing such a
  branch is structurally backwards (the branch doesn't exist yet at the point
  the merge runs).
- Root cause: `_branch_contexts_by_node()`'s DFS stops at every Merge Beacon,
  so neither a merge node nor anything downstream of it is ever assigned a
  branch context — `merge_input_options` had no signal to exclude beacons
  whose branch point is downstream of the merge.
- Fixed by computing the forward-reachable descendant set of the merge node
  being configured (`_descendant_node_ids`) and excluding any beacon whose
  context `branch_id` (the originating branch node) falls in that set.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest -q` (299 passed)

## 2026-06-16 — Merge Beacon Selector Colors Match Connected Merge Branch

- When a Merge Beacon (`branch_end_node`) is connected to a `merge_node`, the
  beacon's selector row text/connector line and its own gutter/numline color
  now match the branch that contains the merge node, instead of the beacon's
  own branch color.
- Added `_merge_node_branch_color_key()`, which reuses
  `_branch_choices_to_node()` to find the branch-port decisions leading to the
  merge node; the last decision's port plus `len(choices) - 1` reproduces the
  same `branch_path_color_key` that `_build_visible_rows` would assign if that
  branch were the active view.
- `_build_visible_rows` now resolves this key for non-placeholder beacons with
  a connected merge node, stores it on the node dict
  (`_editor_branch_color_key`) so `NodeCard` picks it up for the gutter, and
  passes it into `_merge_beacon_select_row` as the row's `active_color_key`.
  Falls back to `current_branch_color_key` when the beacon has no connected
  merge node.
- Merged cleanly on top of the same-session "Merge Node Delete +
  Stranded-Beacon Visibility Fix" change below, which restructured the same
  `branch_end_node` block; the manual resolution preserves both the
  placeholder fall-through fix and this color-key override.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "merge_beacon_selector or node_selector or node_card or editor_depth or branch_end or branch_keep or tombstone"` (18 passed)

## 2026-06-16 — Merge Node Delete + Stranded-Beacon Visibility Fix

Branch: `claude/editor-keyboard-focus-highlight-9fp46y`.

- **`merge_node` is now deletable:** removed `_is_protected_structural_node`
  (it only ever blocked `merge_node`). Deletion follows the plain single-node
  rule — `WorkflowMap.delete_node()` already scrubs connection references on
  both sides, so every Merge Beacon that fed the deleted merge node (and
  anything downstream of it) simply becomes disconnected. Nothing is
  auto-rewired; the user reconnects each beacon manually. Dropped the now-dead
  `cannot_delete_structural_node` notification.
- **Merge Beacon delete already matched spec:** verified
  `_prune_merge_config_for_beacon` / `_disconnect_beacon_merge_outputs` only
  severs the one beacon→merge connection (and that beacon's stale entry in
  `branches_to_close`), leaving other branches and the merge node untouched.
- **Fixed the "stranded node" bug:** `_build_visible_rows` had an unconditional
  `break` on `branch_end_node` rows, even when the beacon was only
  soft-tombstoned (first delete press). Soft-delete never touches backend
  connections, so this made everything past the beacon — including the
  `merge_node` and its downstream — disappear from the editor despite still
  being fully connected. Once the user then saved or validated,
  `materialize_deleted_nodes()` converted the beacon into a real tombstone and
  *did* drop its connection, so what looked like a pre-existing problem turned
  into an actual disconnect, with the tombstone flagged by the validator and
  the editor still not showing any of it. Fixed by only taking the
  beacon-select-row-and-break path when the beacon is not currently a
  placeholder; a soft-deleted beacon now falls through to normal single-port
  traversal so downstream nodes stay visible until the delete is made
  permanent (at which point the node is actually gone and stops showing up in
  validation, as expected).
- Tests: replaced `test_editor_merge_node_delete_stays_blocked` with
  `test_editor_merge_node_delete_disconnects_beacons`; added
  `test_editor_soft_deleted_beacon_keeps_downstream_visible`. Full suite: 299
  passed (`python -m pytest -q`).
- Updated `BACKEND_FRONTEND_BOUNDARY.md` and `PROJECT_KNOWLEDGE.md` to describe
  the Merge Beacon / `merge_node` delete contract instead of "stays blocked."

## 2026-06-16 — Editor Delete Fixes: Keyboard Focus, Gap Shift-Up, Branch Delete

Branch: `claude/editor-keyboard-focus-highlight-9fp46y`.

- **Keyboard focus highlight:** added `up`/`down` editor bindings (priority)
  routed through `_move_selection` so arrow keys skip non-selectable gap rows
  like `W`/`S` already did; added a `NodeList.watch_index` safety net that snaps
  off any gap row. Arrow-key navigation no longer loses the focus highlight on
  the `▼`/`➥` gap lines between node cards.
- **Delete no longer hides downstream nodes:** `_build_visible_rows` was breaking
  the moment it hit a placeholder, discarding the rest of the chain. Soft-deleted
  nodes keep their live connections, so they now fall through to normal port
  traversal; materialized tombstones (outgoing connections dropped on save)
  continue via `original_outputs`.
- **Permanent delete shifts downstream up:** `remove_placeholder` now captures the
  tombstone's upstream/downstream connections before `delete_node` and rewires
  upstream → downstream so the gap closes instead of orphaning the tail. Branch /
  start / merge tombstones are excluded (they have structural reconnection paths).
- **Branch-node delete now reachable:** `_is_protected_structural_node` no longer
  blocks `branch_node` (only `merge_node`). A connected branch now soft-tombstones
  on first delete and opens `BranchKeepSelectorScreen` on the second, wiring the
  previously-dead `prune_branch_tombstone()` flow into the UI. Documented the
  branch-delete exception to the single-node rule in `BACKEND_FRONTEND_BOUNDARY.md`
  and `PROJECT_KNOWLEDGE.md`.
- **Tombstone label** shortened from `Deleted node:` to `Deleted:` in the editor
  card.
- Tests: added `test_editor_branch_node_deletes_through_keep_selector` and
  `test_editor_merge_node_delete_stays_blocked`; updated label and shift-up
  assertions in `test_debug_nodes.py`. Full suite: 298 passed
  (`python -m pytest -q`, with `pytest-asyncio` for the generated async tests).

## 2026-06-15 — Editor Branch Connectors: Branch Border Coloring (explored, reverted)

- Attempted to color the ASCII box borders (`+`, `-`, `|`) of branching nodes
  and branch-end (merge beacon) nodes to mirror the branch path colors already
  used on branch-select cards and numline gutters.
- Branching node border was set to `active_color_key` (the downstream branch
  color); merge beacon border was set to a stable hash-derived color from the
  connected merge node's ID; `BranchSelectCard` and `MergeBeaconSelectCard`
  foregrounds were switched to the merge-node color when connected.
- Reverted (commit `b55b38fb5`) because the approach has a fundamental design
  mismatch: the branching node is a single static card in the editor, but the
  active branch color changes every time the user switches which branch is
  visible. Coloring the box border with the currently-active branch would make
  it flicker on every branch switch rather than conveying stable structural
  identity.
- **Design note for future attempts:** border color on a branching node can only
  work if it conveys something that does not change per branch switch — for
  example, the node's own family color, a depth-level color, or a color derived
  from the branching node's own identity rather than from the active branch port.
  The downstream numline and branch-select colors are per-path and are not
  suitable as a static node-box border color.

## 2026-06-15 — Editor Branch Connectors: Ten-Color Branch Paths

- Fast-forwarded local `main` from `899c155` to `3139181` before starting,
  per the session sync rule.
- Replaced the five-entry branch path color map with a ten-color palette tuned
  for the dark Textual editor background / `ansi-dark` style usage.
- Branch path rendering now uses frontend-only color keys so each branch node
  consumes the palette in sequence: five-path branch one uses colors 1-5,
  branch two uses colors 6-10, then the next branch cycles back.
- Kept raw port-name color lookup (`path_a`-`path_e`) working for existing
  manual rows and tests while editor-built rows use the richer sequence keys.
- Threaded the sequence color key through node gutters, gap arrows, branch
  selector rows, and Merge Beacon selector rows so one visible path segment
  stays consistently colored from branch start through branch end.

## 2026-06-15 — Editor Branch Connectors: Path Colors

- Added branch path coloring for up to five Branch outputs in editor selector
  connector rows. Rich renders the requested CSS colors via hex equivalents:
  lightseagreen, lightblue, steelblue, turquoise, turquoise.
- Branch and merge selector rows now draw `├──` / `└──` from the depth gutter
  into a node-column `─` line that ends with `⟶ [ Branch name ]`, with no
  pointer symbol.
- Connector stems align under the node-row `|` continuation marker, connector
  tails extend to the node-column line, and branch selector labels are centered
  under the node box while accounting for the arrow/bracket prefix.
- The connector gutter and node-column line are styled with the same branch
  path foreground color; selected-row backgrounds still begin after the depth
  gutter.
- Selector lines stop at the branch/merge label instead of continuing on the
  far side of the widget text.
- Downstream node rows carry the visible branch path as frontend-only display
  metadata so number-column numbers and `|` symbols use the branch path color.
- The initial visible path now starts as `path_a`, giving the start/first branch
  segment the same branch color treatment as Branch path 1.
- Branch and merge selector labels use square brackets instead of a right-side
  `|` because the closing bar read poorly in the terminal.
- Depth-number rows use standard non-zero-padded numbers left-aligned in the
  number/gutter column; branch symbols and `|` continuation markers are also
  left-justified there.
- Gap rows between nodes carry branch path color so the `|` immediately before
  a branch node matches the active branch path.
- Merge incoming `┤` now renders on the first continuation line of the merge
  node itself, so a merge directly after a Branch selector no longer collides
  with the Branch selector connector.
- Branch-colored `|` continuation markers render bold to better match branch
  path connector weight.
- Gap markers now reflect source-node outputs: `↓` for transient output,
  `↳` for one configured Vault output, or `➥N` for multiple Vault outputs,
  centered under the node box.
- Continued the gutter rule from the boxed node rows: numbered top rows show
  the depth number, while node box continuation rows use `|` in the number
  column.
- Focused checks: `../.venv/bin/python -m compileall -q .` and
  `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector
  or node_card or editor_depth or branch_end or editor_identity_rows or
  merge_beacon_selector"` (17 passed).

## 2026-06-15 — Editor Node Rows: Gutter, Default Background, Gap Arrows

- Moved the depth number/gutter outside the node text box by drawing the ASCII
  border inside `NodeCard` instead of using a whole-widget border.
- Moved the visible selection highlight off the full `ListItem` row and onto
  the node/jump box text area only, so the depth gutter does not get covered by
  the selected-row background.
- Removed decorative family color fills from node rows; node interiors now
  render on the default editor background.
- Added centered non-focusable `↓`/`↓↓` markers in the existing insertion gap
  between ordinary node rows. They are disabled ListView rows, so selection
  jumps over them.
- Centered branch and merge jump widgets under the node box; these replace the
  down-arrow gap marker when present.
- Focused checks: `../.venv/bin/python -m compileall -q .` and
  `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector
  or node_card or editor_depth or branch_end or editor_identity_rows"` (15
  passed).

## 2026-06-15 — Editor Node Rows: Textual ASCII Borders

- Fixed the Phase 17 editor node rows on `main`: the previous merge still had
  the older family bracket/frame rendering (`[ ]`, `< >`, `{ }`) in
  `frontend/widgets/node_card.py`.
- `NodeCard` identity rows render plain alias and family/subcategory text
  inside an ASCII text box. Deleted-node rows use the same plain-text-in-box
  treatment. Later same-day follow-up moved the depth gutter outside the box.
- Removed the old bracket-specific branch selector indent so branch selector
  labels line up with node text again.
- Updated active UI docs to prefer Textual ASCII node-card borders instead of
  fixed bracket columns.
- Focused checks: `../.venv/bin/python -m compileall -q .` and
  `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_card or
  editor_depth or editor_identity_rows"` (4 passed).

## 2026-06-15 — Documentation Sync: Backend/UI Gap List

- Fast-forwarded local `main` to `origin/main` after confirming the previous
  docs work had landed remotely through the `codex-textual-tui-spinoff` merge.
- Confirmed `README.md` routes Phase 17 and active docs correctly, and
  `MASTER_BUILD_PLAN.md` still marks Phase 17 in progress.
- Added an explicit `PROJECT_BACKLOG.md` section for backend features not yet
  surfaced in the Textual UI: run history browser, secrets management UI,
  tombstone restore report alerts, branch-health visualization, schema-driven
  file pickers for node config, memory snapshot save/load choices, workflow
  rename/bookmark controls, and error clearing controls.
- Linked that gap list from `MASTER_BUILD_PLAN.md`, `AGENT_HANDOFF.md`, and
  the README document directory so future agents do not need to rediscover it.

## 2026-06-13 — Backend & edit-time performance: two O(n^2) fixes

- Audit context: a backend execution-overhead study measured per-node cost
  over the real Supervisor/MasterState/EventBus/MemoryBank stack and found it
  small and linear (~15 us/node) relative to real node I/O — so rewriting the
  execution manager in C is not warranted. Two O(n^2) hot spots were found and
  fixed; remaining lower-leverage items are deferred to `PROJECT_BACKLOG.md`.
- `backend/memory_bank.py`: `MEMORY_UPDATE` now publishes a lightweight delta
  (e.g. `{"change": "set", "key": ...}`) instead of `get_state()`. Each
  persistent write previously deep-copied both the persistent and transient
  stores; since both grow over a run, per-write cost scaled with run size
  (O(n^2) overall). The sole subscriber (`app._on_backend_event`) ignores the
  payload and re-pulls `get_state()` on demand, so the live Memory Viewer and
  dead-drop preview are unchanged. Measured vault-writing chain (us/node):
  24.4/28.8/36.2 at n=500/1000/2000 → flat 16.9/15.1/15.3.
- `backend/workflow_map.py`: `_mark_dirty()` no longer calls
  `_sync_active_to_cache()`. That sync deep-copied the entire `_nodes` graph
  into the open-workflow cache on every editor mutation (add/connect/config/
  delete), making building/editing an N-node workflow O(n^2) — a 4000-node
  graph never finished constructing. The active workflow's live state is
  `self._nodes`; the cache is refreshed lazily before every path that reads it
  (switch/close/list) or replaces the active workflow (load/create/save), all
  of which already sync. Editing is now O(n): build ~2.5 us/edit and flat
  (1000/2000/4000/8000 nodes → 5.4/9.8/20.2/46.1 ms); a 4000-node workflow now
  builds (34ms) and runs to FINISHED (50ms).
- Diagnosis used a throwaway microbenchmark and a `faulthandler` stack dump
  (which pinned the edit-time deepcopy); benchmark scripts were not committed.
  Full suite: 284 passed.

## 2026-06-13 — Headless Plan H6: docs reconciliation + plan archived

- Updated `PROJECT_BACKLOG.md`: tombstone save (H1) and restore (H2) marked
  done under boundary cleanup (only the restore-alert UI remains, deferred);
  Secrets project reduced to the `SettingsScreen` tab (schema fields +
  validator wiring done, H3); branch-health derivation marked done with the
  editor colour pass remaining (H5); form-generator label/value and schema-key
  tests marked done (H4).
- `MASTER_BUILD_PLAN.md`: phase 10.6 → Done (restore-alert UI + Phase C
  metadata deferred); added an H1–H5 entry to Recently Completed.
- Archived `HEADLESS_BUILD_PLAN.md` → `archive/plans/`; moved its README
  directory row to the Archive table; logged the move in
  `DOCS_MIGRATION_NOTES.md`.
- Headless plan complete: H1–H6 done, full suite 284 passed. Remaining backlog
  work from this plan is UI-only and needs live-TUI verification.

## 2026-06-13 — Headless Plan H5: backend branch health derivation

- New `backend/branch_health.py`: pure-logic `derive_branch_health(all_nodes,
  output_node_types=None)` classifies each `branch_node` outgoing edge (one
  spawned parallel path) into `valid` / `ended_unmerged` / `floating` by
  walking the path forward — `merge_node` or output/end node or
  merge-connected Merge Beacon → valid; Merge Beacon not wired to a merge →
  ended_unmerged; dead end / cycle / unconnected port → floating. Nested
  `branch_node`s count as valid for the outer path and are classified on
  their own merits. Returns frozen `BranchHealth` dataclasses; states are
  module constants (`VALID`, `ENDED_UNMERGED`, `FLOATING`).
- `branch_health_by_port()` keys results by `(branch_node_id, port)` to match
  how editor branch rows are keyed, so the deferred FA-7 visual pass can map
  states to colours with O(1) lookups and no re-derivation.
- `output_types_from_factory(factory)` builds the valid-output-type set from
  node metadata (Outputs family + `end_node`, plus `text_output_node`), so
  the policy tracks the taxonomy; the function also works with no factory via
  `DEFAULT_OUTPUT_NODE_TYPES`. No frontend imports — backend stays UI-agnostic.
- Tests: `tests/test_branch_health.py` (14 tests) — one fixture per state,
  chain-to-output, direct-merge, mixed multi-port branch, nested branches,
  unconnected port, cycle, no-branch empty, the by-port mapping, and the
  factory/default output-type paths. Full suite: 284 passed.
- Visual surfacing in the editor (branch-health colours, FA-7 pass) stays
  deferred — it needs live-TUI verification.

## 2026-06-13 — Headless Plan H4: form generator label/value selects + key coverage

- `frontend/widgets/form_generator.py`: `_select_options()` now normalizes
  option entries — plain scalars (label == value, unchanged),
  `{"label": ..., "value": ...}` mappings, and 2-item sequences — so the
  backend reads stable machine values while the dropdown shows display
  labels. Applied to `select`, option-bearing string fields, and
  `multiselect` (initial selection matches by machine value). Value
  read-back needed no change: `Select.value` / `SelectionList.selected`
  already return the value half.
- Helper specs need no changes: `aotn_node_helper` copies field schemas
  verbatim, so YAML specs can declare label/value option dicts today.
- Tests: new `tests/test_form_generator.py` (12 tests) — option
  normalization shapes, label/value round-trips per widget type, and the
  previously untested schema keys: `label`/`required` star, `description`,
  `default`, `boolean` round-trip, integer `min`/`max` validator, string
  `min_length`/`max_length` validator, `code` `language`, and numeric
  coercion fallback. Full suite: 270 passed.

## 2026-06-13 — Headless Plan H3: secrets schema flags + editor wiring

- Secret-ref schema fields added (`"secret": True`, optional while execution
  is stubbed): `api_key_secret` on `chat_completion_node`, `embedding_node`,
  `image_generation_node`; `auth_token_secret` on `http_request_node`. The
  HTTP node actually uses it: when configured, the request sends
  `Authorization: Bearer <secret>` resolved via `context.get_secret()`. The
  helper spec `aotn_node_helper/specs/http_request_node.yaml` carries the
  field so regeneration keeps it.
- `main.py` now constructs a `SecretsManager` and passes it to `MasterState`
  (runtime path was previously unwired) and to the app.
- `frontend/app.py` / `EditorScreen` accept `secrets_manager`;
  `action_validate_workflow` forwards it to `validate_workflow`, so
  editor-triggered validation surfaces missing-key warnings live.
- Tests appended to `test_validator_secrets.py`: all four nodes declare the
  secret field, per-node missing-store-key warning, and a pilot test proving
  the editor wiring (details screen opens with a manager, clean without).
  Full suite: 258 passed.

## 2026-06-13 — Headless Plan H2: tombstone restore engine

- `frontend/editor_workflow_adapter.py`: new
  `EditorWorkflowAdapter.restore_tombstone(node_id)` implements the
  connection-validated restore procedure from `BACKEND_FRONTEND_BOUNDARY.md`.
  Node type/alias/config always come back; each stored input connection is
  reconnected only when the source node exists and still declares the output
  port; each stored output connection only when the target exists, declares
  the input port, and that port is not occupied by a different source;
  membank input declarations are restored with the config and flagged when no
  surviving node declares the variable.
- Returns a `TombstoneRestoreReport` dataclass (input_errors, output_errors,
  membank_warnings with node id/alias/port/reason) — plain data for the
  deferred frontend alert; no UI copy in the adapter.
- `undo_placeholder()` and `replace_placeholder()` (restore-original path)
  now route through `restore_tombstone()`, so editor undo also validates
  drift instead of blindly reconnecting; `replace_placeholder()` returns the
  report under `restore_report`. The blind `_restore_downstream_inputs`
  helper was removed.
- Tests: `tests/test_tombstone_restore.py` (11 tests) covers the clean path,
  every drift category (source gone, source port gone, target gone, target
  port occupied, membank source missing), rejection paths, the replace-modal
  report, and that a partial restore clears the validator's tombstone error.
  Full suite: 252 passed.

## 2026-06-13 — Headless Plan H1: tombstone direct save

- `frontend/editor_workflow_adapter.py`: `materialize_deleted_nodes()` now
  writes `tombstone_node` with the full original-data config (contract shape
  from `BACKEND_FRONTEND_BOUNDARY.md`: `original_type/display_name/alias/
  config/inputs/outputs` plus the port lists the validator reads). No save
  path writes `branch_end_node + _system_role` anymore.
- New module helpers `tombstone_config_from_metadata()` /
  `metadata_from_tombstone_config()` define the config↔metadata mapping in
  one place; `migrate_legacy_deleted_node()` now carries full restore data
  (alias, config, connections) instead of ports only, so legacy saves keep
  undo-after-reload.
- `is_materialized_placeholder()` recognizes `tombstone_node` (legacy marker
  still recognized until load migration runs); `placeholder_metadata()` reads
  tombstone config directly — editor rendering, undo, and replace flows work
  on the new format unchanged.
- Tests: tombstone round-trip + undo-after-materialize-with-fresh-adapter in
  `test_tombstone_phase_b.py`; full-data migration carry in
  `test_tombstone_migration.py`; materialize/save/loaded-marker tests in
  `test_debug_nodes.py` updated to the tombstone format, with a
  tombstone-format loaded-row render check added. Full suite: 241 passed.

## 2026-06-13 — Headless Build Plan created

- Added `docs/HEADLESS_BUILD_PLAN.md`: phased plan (H1–H6) covering the
  backlog work that is fully verifiable with `compileall` + `pytest`, with
  no live-TUI verification required — tombstone direct save (H1), tombstone
  restore engine per the 2026-06-11 design spec (H2), secrets schema flags +
  editor validator wiring (H3), form generator label/value selects + schema
  key test coverage (H4), backend branch health derivation (H5), and docs
  reconciliation (H6).
- Each phase lists tasks, likely files, focused pytest checks, and exit
  criteria; live-app work (Phase 17 verification, Secrets settings tab, AI
  session config UI, branch health indicators) is explicitly deferred and stays
  in `PROJECT_BACKLOG.md`.
- Added the new doc to the `README.md` Document Directory.

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

## 2026-06-12 — Taxonomy Revision Implementation: Selector Restructure, Group Picker, Metadata

Code session implementing the taxonomy revision documented below.

- `Node` base: new frontend-only ClassVars `group: Optional[str]` and
  `selector_section: Optional[str]`; `NodeFactory.get_node_types_metadata()`
  exposes both (None when unset).
- `node_identity.py`: five-family remap. Debug/data nodes moved to the new
  `Utility` family (Transform / Debug / Loop Helpers sections); Flow Control
  entries gained Branch/Merge/Wait-Timer groups under Branching/Timing
  sections; I/O-side and Complex entries gained their groups and sections per
  `NODE_CATALOG.md`. `FAMILY_COLOR_HINTS` gained `Utility: grey`.
- `node_card.py`: `Utility` family frame (`|`/`|`) and row background
  (the existing quiet `#9aa7b3`).
- `NodeSelectorScreen` restructured to the four-tab design:
  - Tabs `I/O`, `Flow Control`, `Utility`, `Complex`; the I/O tab has a
    Textual `Switch` row (Input/Output) above the filter that selects which
    family fills the list. Filters checked on one side no longer constrain
    the other side.
  - Filter checkboxes reduced to I/O (`File I/O`/`Internet`/`AI`) and
    Complex (`AI`); shown only when the active side actually has the tag.
  - The list renders three entry kinds: non-selectable section headers
    (skipped by W/S navigation, hidden while searching), single-line group
    entries with member counts, and two-line node rows. Single-member groups
    auto-promote to direct node rows.
  - `start_node` and `end_node` are hidden from the selector alongside
    `tombstone_node`.
  - String search dissolves groups and headers; matching node types render
    directly and the grouped view returns when the filter clears.
- New `frontend/screens/group_picker.py`: generic `GroupPickerScreen` modal
  parameterized by group name and member metadata; one node per line with the
  highlighted member's description below; `E`/Enter dismisses with the chosen
  type (selector then dismisses too), `ESC` pops only the picker.
- `aotn_node_helper/generator.py`: validates the five families, accepts
  `group` / `selector_section` spec fields (requiring a section when a group
  is declared, except on the flat Outputs side), and emits both as class
  metadata on generated nodes.
- `styles.tcss`: `#io-direction-row`, `.node-select-header`,
  `.node-select-group`, and group-picker styles.
- Tests: rewrote the selector taxonomy test for the new structure; added
  `test_node_selector_group_picker_flow` (open picker, ESC back, choose
  member closes both) and
  `test_node_selector_navigation_skips_section_headers`; updated the layout
  test for the switch row and family expectations in editor identity tests.
- Verification:
  - `python3 -m compileall -q . ../aotn_node_helper`
  - `python3 -m pytest tests/ -q` (147 passed; 1 pre-existing
    environment-only failure: generated example UI smoke test requires
    pytest-asyncio, absent in this container)
  - `../aotn_node_helper/check_ui.py echo_node` OK
- Remaining before Phase 17 close: live-TUI manual verification of the new
  selector and editor rows at several terminal widths.

## 2026-06-12 — Taxonomy Revision: Five Families, I/O Switch, Section Headers, Node Catalog

Design + documentation session (code implemented the same day — see the
entry above).

- Revised the Phase 17 taxonomy to five backend families — `Inputs`,
  `Outputs`, `Flow Control`, `Utility`, `Complex` — mapped onto four selector
  tabs. `Inputs`/`Outputs` share one `I/O` tab behind a Textual `Switch`
  (Input on one side, Output on the other) above the list; the switch is
  frontend-only presentation, so backend family metadata stays semantic.
- `Utility` is the new action-node family: UI Automation group (click, type,
  key press; screen-read variants deferred), Script Runner group (deferred,
  security gated — hidden from list and search until an explicit "allow
  script execution" setting is on), Data Transform group (set/get variable,
  concat, text ops, JSON, math, format text), Debug direct-adds (echo, probe,
  logger, sleep), and Loop Helper direct-adds (counter, accumulator, repeat
  limiter).
- AI became a subcategory tag, not a family. AI-flavored variants live in
  their natural groups (AI Conditional Branch under Flow Control → Branch,
  AI-Guided Read under File Reader); dedicated AI tools stay in Complex →
  AI Processing where the `AI` filter surfaces them.
- Filter checkboxes reduced to two tabs: I/O (`File I/O`/`Internet`/`AI`)
  and Complex (`AI`). Groups and in-list section headers do the organizing
  elsewhere. Headers are non-selectable rows keyboard navigation skips,
  hidden while a string filter is active or when empty.
- Removed Start/End from the user-facing taxonomy: Start is auto-generated;
  branches end through outputs (new standard "Terminate branch after
  completion" config option in `NODE_STANDARDS.md`), through merges, or
  through a new silent **End Branch** direct-add node in Flow Control.
- Designed the **AI Input** node (I/O Input side): seeds a chat session under
  a vault session key before the response is needed; default dead-drop
  passthrough with optional "Output AI response"; prompt can be customized
  mid-workflow before being passed in. Pattern documented in
  `NODE_STANDARDS.md`.
- Documented the AI model approach: capability-based AI nodes with curated
  supported-model lists (strictest for structured-output nodes such as AI
  Conditional Branch); a future fork point to per-model groups if supported
  models diverge.
- Added `selector_section: str | None` to the metadata direction alongside
  `group` — both frontend-only, exposed through `NodeFactory`.
- Created `NODE_CATALOG.md`: complete node inventory (Live / Planned /
  Deferred / Concept) with mappings from currently registered types, so no
  node idea is lost while non-critical nodes are deferred.
- Updated: `PHASE_17_NODE_VISUAL_IDENTITY.md` (rewritten for the revision),
  `NODE_STANDARDS.md` (terminate-branch standard, AI Input pattern),
  `NODE_HELPER.md` (five families, `group`/`selector_section` spec fields),
  `MASTER_BUILD_PLAN.md` (Phase 17 remaining work), `AGENT_HANDOFF.md`
  (direction summary), `README.md` (catalog directory row + task table).
- Verification:
  - `git diff --check`
  - `python3 -m pytest tests/ -q` (145 passed + 1 pre-existing generated-node
    flake, unchanged from before the docs edit)

## 2026-06-12 — Docs: README Document Directory Overhaul

- Rewrote `README.md` to give every document a clear "what it contains" and
  "when to open it" entry in a structured Document Directory table. Replaced
  the previous flat Read-First / Reference lists (which had overlapping entries
  and imprecise descriptions) with four organized sections: Roadmap and Session
  State, Node Authoring, Architecture and Boundaries, Frontend Reference, and
  Planning and Backlog.
- Archive section now explains when to open each archived file rather than just
  listing them.
- Documentation Rules in README now includes "add a row to the Document
  Directory when a new active doc is created."
- Added orienting intro to `TASK_INDEX.md` clarifying its role relative to
  README (README routes; TASK_INDEX gives the minimum reading set, likely files,
  and focused test commands).

## 2026-06-12 — Node Taxonomy: Core Simplification Rule, Full Expanded Taxonomy, Group Picker Design

- Documented the Core Simplification Rule for deciding node placement: variants
  with different port shapes → separate types; same ports + very different config
  → group with picker; minor config differences, same ports → one node + mode
  select; unique standalone node → direct-add. Rule is in both
  `PHASE_17_NODE_VISUAL_IDENTITY.md` and `NODE_STANDARDS.md`.
- Added Full Expanded Taxonomy to `PHASE_17_NODE_VISUAL_IDENTITY.md`:
  - INPUTS: Text Input group, File Reader group, Data Source group, Trigger group
    (with architecture note: triggers need a persistent listener process outside
    the supervisor model; config-only for now).
  - FLOW CONTROL: Branch group (separate types because port shapes differ),
    Merge group, Wait/Timer group, Loop Utility group, Merge Beacon (direct-add),
    Start/End (direct-add).
  - OUTPUTS: Text Output group, File Write group (File Write is one node with
    mode select — not separate Overwrite/Append types), Send/Notify group,
    User-Facing Prompt group.
  - COMPLEX: AI Processing group, Subworkflow group (reserved, phases 19/20),
    Data Transform group, Script Runner group (deferred; security gate required).
- Documented two-level group picker design in `PHASE_17_NODE_VISUAL_IDENTITY.md`:
  - Main selector shows group entries with member counts; counts reflect active
    subcategory filters; groups with filtered count 0 are hidden.
  - Group Picker second modal: generic/reusable, `ESC` returns to main selector,
    `E` adds and closes both modals, no filter input in the picker.
  - Auto-promotion: single-member groups become direct-add entries, no picker.
  - Search behavior: string filter dissolves groups; individual node types appear
    directly; groups re-form when filter is cleared.
- Added Keyboard Flows section: group-add flow, direct-add flow, search-first flow.
- Added Problems and Solutions Summary table.
- Added What Doesn't Need to Exist section.
- Added `group: str | None` metadata field design to Metadata Direction.
- Updated Completion Shape to include group picker criteria.
- Added "Design Or Update Node Taxonomy" task route to `TASK_INDEX.md`.
- Added taxonomy task row to `README.md` Choose Your Task table.
- Updated `MASTER_BUILD_PLAN.md` Phase 17 Done and Remaining sections.

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

## 2026-06-11 — Typed Vault Entries and AI Session Architecture

Architecture design session only. No runtime, frontend, or test changes.

- **Typed vault entries.** Decided that `MemoryBank` vault entries will carry
  a `type` field alongside their value. Types: `string`, `number`, `boolean`,
  `file`, `ai_session`. Simple types remain pure JSON. `file` and `ai_session`
  entries store a type tag and a string reference key; the actual Python handle
  lives in `RunSession` and is retrieved via `context.run_session.get_resource
  (ref_key)`.
- **RunSession as handle owner.** File handles and AI session objects are not
  JSON-serializable and must live in `RunSession`, not `MemoryBank`. `RunSession`
  already exists; the only addition needed is `get_resource(key)` to complement
  `register_resource(key, handle)`.
- **AI session as config-driven LLM node output.** No separate Chat Session
  Node. Any LLM node can opt into session persistence via a "keep active AI
  session" checkbox and a user-supplied session key. The first node with a given
  key starts the session and writes `(type: ai_session, ref_key)` to the vault;
  downstream nodes that select the same vault key continue the session. Message
  history stays in the session object in `RunSession`.
- **Input dropdown type filtering.** Config dropdowns that select a vault source
  filter by declared input type. Only `file` entries appear for file inputs;
  only `ai_session` entries appear for LLM continuation inputs.
- **Validator error/warning split for vault key ordering.** Error when no node
  in the workflow declares the key at all. Warning when the key is declared on
  a parallel branch with unguaranteed execution order. The validator must not
  infer timing from node count, type, or branch depth. Applies uniformly across
  all vault types.
- **Docs updated:** `PROJECT_BACKLOG.md` (new Near-Term section, extended
  RunSession remaining notes), `PROJECT_KNOWLEDGE.md` (RunSession backend
  component entry, new Data Flow Patterns section), `NODE_STANDARDS.md`
  (created; typed vault outputs, AI session config-driven pattern, validator
  rules), `MASTER_BUILD_PLAN.md` (new Later Roadmap bullet), `ARCHITECTURE.md`
  (RunSession subsection).

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
    state indicators still take priority over decorative styling.
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

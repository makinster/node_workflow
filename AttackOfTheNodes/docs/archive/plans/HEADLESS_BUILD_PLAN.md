# Headless Build Plan — Backlog Work Without Live-TUI Verification

**Created:** 2026-06-13
**Scope rule:** every phase here must be fully implementable and verifiable
with `compileall` + `pytest` (including Textual `run_test` pilot mounts).
Work that requires a human watching the running app — live rendering checks,
visual styling passes, keyboard feel — is explicitly out of scope and stays
in `PROJECT_BACKLOG.md` / Phase 17.

Execution rules:

- Work phases in order; each phase is independently committable.
- Per phase: implement, add focused tests, run the focused check, then log a
  `SESSION_LOG.md` entry and tick the phase checkbox here.
- Backend code must not import from `frontend` (see
  `BACKEND_FRONTEND_BOUNDARY.md`).
- When the whole plan completes, fold the outcome summary into
  `MASTER_BUILD_PLAN.md` / `PROJECT_BACKLOG.md` and archive this file under
  `archive/plans/` with a `DOCS_MIGRATION_NOTES.md` entry.

## Phase Checklist

- [x] H1 — Tombstone direct save (2026-06-13)
- [x] H2 — Tombstone restore engine (2026-06-13)
- [x] H3 — Secrets schema flags + editor validator wiring (2026-06-13)
- [x] H4 — Form generator: label/value selects + schema key coverage (2026-06-13)
- [x] H5 — Branch health derivation (backend) (2026-06-13)
- [x] H6 — Docs reconciliation (2026-06-13)

**Status: complete (2026-06-13).** H1–H5 implemented and verified (full suite
284 passed); this doc is archived under `archive/plans/`. Deferred UI pieces
(tombstone restore alert, Secrets settings tab, branch-health colours) are
tracked in `PROJECT_BACKLOG.md`.

---

## Phase H1 — Tombstone Direct Save

Goal: new saves write `tombstone_node` directly instead of the legacy
`branch_end_node + _system_role` marker. Completes the save half of
Phase B (see `BACKEND_FRONTEND_BOUNDARY.md` and the 2026-06-11 tombstone
design decision in `PROJECT_BACKLOG.md`).

Tasks:

1. In `frontend/editor_workflow_adapter.py`, change the deleted-node save
   path (currently writes `branch_end_node` with
   `config._system_role = DELETED_NODE_SYSTEM_ROLE`) to emit
   `tombstone_node` with the full original node data at config top level:
   original type, alias, config, input/output connections, membank inputs —
   matching the shape `migrate_legacy_deleted_node()` already produces.
2. Keep `migrate_workflow_on_load()` unchanged so old saves still migrate;
   add a test asserting migration is a no-op on the new format.
3. Round-trip test: delete a node → save → load → tombstone present with
   original data intact, validator reports the tombstone with orphaned-port
   context.

Likely files:

- `frontend/editor_workflow_adapter.py`
- `tests/test_tombstone_phase_b.py`, `tests/test_tombstone_migration.py`

Focused check:

```bash
../.venv/bin/python -m pytest tests/test_tombstone_phase_b.py tests/test_tombstone_migration.py -v
```

Exit criteria: no code path writes `_system_role = deleted_node_branch_end`
on save; legacy loads still migrate; round-trip covered.

## Phase H2 — Tombstone Restore Engine

Goal: implement tombstone restore with connection validation and partial
restore. The full design spec lives in `PROJECT_BACKLOG.md`
("Tombstone restore — connection validation, design spec 2026-06-11") —
implement it as written; do not re-design.

Tasks:

1. Add a restore function to `frontend/editor_workflow_adapter.py` (or an
   adjacent adapter module) that takes a workflow dict + tombstone node id
   and applies the 6-step procedure: always restore type/alias/config;
   reconnect each stored input/output connection only when the counterparty
   node and port still exist (and the target input port is unoccupied);
   restore membank input declarations regardless, flagging missing sources.
2. Return a structured restore report (plain dataclass/dict — no UI copy):
   input connection errors, output connection errors, membank warnings, each
   with original alias + port + reason. The alert screen that renders this
   report is a later, UI-verified task — out of scope here.
3. Tests per drift category: source gone, source port gone, target gone,
   target port gone, target port occupied, membank source missing, and the
   clean full-restore path.

Likely files:

- `frontend/editor_workflow_adapter.py`
- `tests/test_tombstone_restore.py` (new)

Focused check:

```bash
../.venv/bin/python -m pytest tests/test_tombstone_restore.py -v
```

Exit criteria: partial restore always succeeds for node identity/config;
every drift category yields the right report entry; no Textual imports in
the restore logic.

## Phase H3 — Secrets Schema Flags + Editor Validator Wiring

Goal: finish the headless half of the Secrets backlog project. The
`SettingsScreen` Secrets tab stays deferred (needs live UI verification).

Tasks:

1. Add `"secret": True` to the API-key config schema fields on
   `chat_completion_node`, `embedding_node`, `image_generation_node`, and
   the generated `http_request_node`.
2. Thread `SecretsManager` into `EditorScreen.action_validate_workflow`
   (`frontend/screens/editor.py`) so editor-triggered validation surfaces
   missing-key warnings, matching the wiring `MasterState` already uses.
3. Tests: validator emits error for empty required secret field, warning for
   key absent from store, skip when no manager — per node type touched.
   Reuse the patterns in `tests/test_validator_secrets.py`.

Likely files:

- `backend/nodes/chat_completion_node.py`, `embedding_node.py`,
  `image_generation_node.py`, `backend/nodes/io/` (http_request)
- `frontend/screens/editor.py`
- `tests/test_validator_secrets.py`

Focused check:

```bash
../.venv/bin/python -m pytest tests/test_validator_secrets.py tests/test_secrets_manager.py -v
```

Exit criteria: all API-key fields flagged; editor validation path receives a
`SecretsManager`; validator behavior covered per node.

## Phase H4 — Form Generator: Label/Value Selects + Schema Key Coverage

Goal: backend reads stable machine values from selects instead of display
strings, and every schema key in `form_generator.py` has a test.

Tasks:

1. Extend `_select_options()` in `frontend/widgets/form_generator.py` to
   accept label/value pairs (e.g. `{"label": ..., "value": ...}` entries)
   while keeping plain-string options backward compatible. Apply to both
   `select` and `multiselect`, and to the value read-back path
   (`Select`/`SelectionList` handling).
2. Audit the schema keys the generator honors (`tab`, `options`, `secret`,
   `path_hint`, `enabled_when`, `visible_when`, `mutually_exclusive_with`,
   field types, required/default) and add a test for any key lacking one.
3. Helper follow-up only if cheap: let `aotn_node_helper` specs emit
   label/value options. Otherwise note it in the backlog.

Likely files:

- `frontend/widgets/form_generator.py`
- `tests/test_form_rules.py` (extend) or `tests/test_form_generator.py` (new)

Focused check:

```bash
../.venv/bin/python -m pytest tests/test_form_rules.py -v -k "form"
```

Exit criteria: label/value selects round-trip machine values through save;
plain-string specs unchanged; schema key test matrix complete.

## Phase H5 — Branch Health Derivation (Backend)

Goal: the pure-logic half of Branch Health Visualization. Color surfacing in
`NodeCard` is deferred to the FA-7 visual pass (needs live UI verification).

Tasks:

1. Add a backend helper (new `backend/branch_health.py` or extend
   `backend/workflow_map.py`) that derives per-branch health from workflow
   structure alone — no stored UI state. Three states:
   - `valid`: branch ends in an end/output node or a connected Merge Beacon;
   - `ended_unmerged`: Merge Beacon exists but is not connected to a Merge
     node;
   - `floating`: no valid end and no Merge Beacon.
2. Return results keyed by branch/node id so a future editor adapter can map
   them to colors without re-deriving.
3. Tests: one workflow fixture per state, plus a mixed multi-branch fixture
   and a nested-branch case.

Likely files:

- `backend/branch_health.py` (new) or `backend/workflow_map.py`
- `tests/test_branch_health.py` (new)

Focused check:

```bash
../.venv/bin/python -m pytest tests/test_branch_health.py -v
```

Exit criteria: states derivable for every fixture; no frontend imports; API
documented well enough for the FA-7 pass to consume directly.

## Phase H6 — Docs Reconciliation

Goal: leave the docs truthful after H1–H5.

Tasks:

1. Update `PROJECT_BACKLOG.md`: mark tombstone save/restore done, move the
   Secrets project to UI-tab-only, mark branch-health logic done (visual
   surfacing remains), update the form-generator items.
2. Update `MASTER_BUILD_PLAN.md` phase 10.6 status and Recently Completed.
3. Final `SESSION_LOG.md` entry summarizing the plan outcome.
4. Archive this file to `archive/plans/` and log the move in
   `DOCS_MIGRATION_NOTES.md`; remove its row from `README.md`.

Focused check:

```bash
git diff --check
rg -n "HEADLESS_BUILD_PLAN" AttackOfTheNodes/docs
```

---

## Full-Suite Gate

Before declaring the plan complete, from `AttackOfTheNodes/`:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/ -v
```

## Explicitly Deferred (needs live app)

Tracked in `PROJECT_BACKLOG.md` / `MASTER_BUILD_PLAN.md`, not here:

- Phase 17 live-TUI verification (selector, editor rows, terminal widths).
- Secrets tab in `SettingsScreen`.
- "Keep active AI session" checkbox + vault write path + typed dropdown
  filtering on LLM node configs.
- Keyboard-only smoke suites and full keyboard simulation for generated UI.
- Branch health colors in the editor / FA-7 visual pass.
- Toast/alert system polish.

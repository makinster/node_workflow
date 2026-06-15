# AttackOfTheNodes Agent Handoff

## Current State

The active app is `AttackOfTheNodes/`, a Python/Textual workflow editor and
execution TUI backed by an asyncio workflow engine. Backend services stay
UI-agnostic; frontend behavior lives under `frontend/`.

The current active work is Phase 17: node visual identity and selector
taxonomy. Metadata exposure, selector tabs/filters, editor row identity, and
details-panel identity have landed, but the phase is still open while current
frontend/backend support gaps are being triaged into the roadmap.

## Start Here

1. `docs/README.md` — task router.
2. `docs/TASK_INDEX.md` — minimum docs, likely files, focused checks.
3. `docs/SESSION_LOG.md` — recent changes.
4. `docs/MASTER_BUILD_PLAN.md` — concise roadmap/status.
5. `docs/BACKEND_FRONTEND_BOUNDARY.md` — required before backend changes
   motivated by UI behavior.

## Current Documentation Shape

- Active docs are concise and current-state oriented.
- Full completed build-plan detail is archived in
  `docs/archive/BUILD_PLAN_HISTORY.md`.
- Full older session history is archived in
  `docs/archive/SESSION_LOG_HISTORY.md`.
- Historical tkinter/proof-of-concept planning is archived in
  `docs/archive/V05_BUILD_PLAN.md`.
- Completed/lower-priority planning docs are under `docs/archive/plans/`.
- `docs/DOCS_MIGRATION_NOTES.md` records why docs were moved or collapsed.
- `docs/PHASE_17_NODE_VISUAL_IDENTITY.md` records the active taxonomy and UI
  direction for selector/editor identity work.

## Project Status

Completed major phases:

- Runtime phases 0 through 9.
- Frontend audit/helper phases FA-0 through FA-5.
- Documentation modernization and backend/frontend boundary cleanup.
- Cursor model foundation, key binding remap, editor rework, and File/config
  polish through Phase 16.
- Node helper generator and focused generated-node test workflow.

Active product phase:

- Phase 17: Node visual identity and selector taxonomy.

Phase 17 direction:

- Primary selector families: Inputs, Flow Control, Outputs, Complex.
- Nodes can have multiple subcategory tags such as Triggered, File I/O,
  Internet, AI, Passive Output, Active Output, Parallel, Conditional, Runtime
  Resource, and Utility.
- The selector uses family tabs, a string filter, tab-specific subcategory
  controls, and a filtered node list.
- Editor rows use two-line rows showing alias first, then family and
  high-signal subcategories.

Current frontend/backend support gaps:

- No historical run browser for persisted run summaries, outputs, errors, and
  timings.
- No generic node-config file picker for schema fields with `path_hint: "file"`.
- No UI for `SaveManager` memory-state save/load options.
- No UI for workflow rename, cached open-workflow switching, or bookmark
  navigation.
- No UI for clearing persisted run errors.

Deferred:

- Real AI node execution.
- Packaging/release hardening.
- Nested workflow phases 19 and 20.

## Working Rules

- Do not revert unrelated dirty/untracked files.
- Use `TASK_INDEX.md` to choose the smallest useful reading set.
- Ordinary nodes should be metadata-driven and generated through
  `../aotn_node_helper/` when practical.
- Backend code must not import from `frontend`.
- Before UI-motivated backend changes, read `BACKEND_FRONTEND_BOUNDARY.md`.
- Before Phase 17 selector/editor work, read
  `PHASE_17_NODE_VISUAL_IDENTITY.md`.
- Use focused `pytest -k` checks for small fixes; run the full relevant suite
  before broad runtime/shared UI commits.
- Update `SESSION_LOG.md` and, for doc moves/collapses,
  `DOCS_MIGRATION_NOTES.md`.

## Verification Pattern

From `AttackOfTheNodes/`:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "<focused_behavior>"
```

For docs-only work from the workspace root:

```bash
git diff --check
rg -n "<stale-folder-or-phase-pattern>" AttackOfTheNodes/docs AGENTS.md
find AttackOfTheNodes/docs -type f -name '*.md' | sort
```

# AttackOfTheNodes Agent Handoff

## Current State

The active app is `attackofthenodes_v05/`, a Python/Textual workflow editor and
execution TUI backed by an asyncio workflow engine. The tkinter frontend is
obsolete. Backend services remain UI-agnostic; frontend behavior lives under
`frontend/screens/`, `frontend/widgets/`, and `frontend/styles.tcss`.

## Active Build Plan

Use `docs/MASTER_BUILD_PLAN.md` as the dependency-ordered plan. Phase 0 memory
leak fixes are complete. The next unfinished phase after this handoff is Phase 5
unless `docs/SESSION_LOG.md` says otherwise.

Completed from the master plan:

- Phase 0: Memory leak fixes.
- Phase 1: `WorkflowMap.nodes_reachable_from(node_id)`.
- Phase 2: derived `input_sources` at save/export/duplicate and input-source
  validation.
- Phase 3: membank output/input config sections and structure-derived registry.
- Phase 4: insert-after-highlight editor behavior and no-cascade tombstone
  deletion.

## Read First

- `docs/MASTER_BUILD_PLAN.md` for implementation order and contracts.
- `docs/SESSION_LOG.md` for completed phase notes.
- `docs/TUI_DESIGN.md` for current Textual frontend conventions.
- `docs/PROJECT_BACKLOG.md` for deferred cleanup work.

## Working Rules

- All new async code should use `backend.utils.try_catch.try_catch`.
- Backend code must not import from `frontend`.
- Textual screen-level letter actions that must fire while a list has focus
  should use `Binding(..., priority=True)`.
- Run verification from `attackofthenodes_v05/`:

```bash
python -m compileall -q .
python tests/test_debug_nodes.py
```

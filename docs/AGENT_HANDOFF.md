# AttackOfTheNodes Agent Handoff

## Current State

The active app is `attackofthenodes_v05/`, a Python/Textual workflow editor and
execution TUI backed by an asyncio workflow engine. The tkinter frontend is
obsolete. Backend services remain UI-agnostic; frontend behavior lives under
`frontend/screens/`, `frontend/widgets/`, and `frontend/styles.tcss`.

## Active Build Plan

Use `docs/MASTER_BUILD_PLAN.md` as the comprehensive source of truth. It merges
the active dependency-ordered phase plan, the Textual TUI state, the working
rules, and the current architecture model. Phase 0 memory leak fixes are
complete. The next unfinished phase after this handoff is Phase 6 unless
`docs/SESSION_LOG.md` says otherwise.

Completed from the master plan:

- Phase 0: Memory leak fixes.
- Phase 1: `WorkflowMap.nodes_reachable_from(node_id)`.
- Phase 2: derived `input_sources` at save/export/duplicate and input-source
  validation.
- Phase 3: membank output/input config sections and structure-derived registry.
- Phase 4: insert-after-highlight editor behavior and no-cascade tombstone
  deletion.
- Phase 5: grouped schema fields render as tabs when there is more than one
  group; simple configs stay flat.
- Phase 6: node breakpoints pause globally before execution and resume through
  the existing pause path.

Recent usability patch:

- Node config modals use text-field-safe bindings only: `Esc`, `Ctrl+S`,
  `Ctrl+Enter`, and buttons.
- Memory-bank reads render above core node settings; memory-bank writes render
  at the bottom.
- Branch nodes have configurable `path_a_label` and `path_b_label` display
  names.
- Node selector filtered lists highlight the first item when tabbing into the
  list.

Recent docs pass:

- `docs/MASTER_BUILD_PLAN.md` was rewritten as the comprehensive build plan.
- Older docs that mention Chrome-extension, IndexedDB/Dexie, JavaScript
  backends, or tkinter should be treated as historical until Phase 10 refreshes
  them.

Latest phase:

- Phase 6 breakpoints are complete. The next unfinished implementation phase is
  Phase 7 per-node execution timing.

## Read First

- `docs/MASTER_BUILD_PLAN.md` for current architecture, implementation order,
  contracts, and testing rules.
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

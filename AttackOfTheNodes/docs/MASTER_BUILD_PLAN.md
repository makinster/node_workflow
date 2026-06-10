# AttackOfTheNodes Master Build Plan

**Last updated:** 2026-06-09
**Project root:** `AttackOfTheNodes/`
**Runtime:** Python 3.14, Textual 8.2.7, asyncio, JSON persistence

This is the concise active roadmap. Completed phase details were collapsed into
`archive/BUILD_PLAN_HISTORY.md` during the documentation overhaul.

## Current State

AttackOfTheNodes is a Python workflow engine with a Textual terminal UI.
Workflows are directed node graphs. A `MasterState` starts runs, supervisors
walk execution paths, branching nodes spawn branch supervisors, and all
supervisors share a per-run `MemoryBank`.

The backend is UI-agnostic. Frontend-only behavior belongs under `frontend/`.
Read `BACKEND_FRONTEND_BOUNDARY.md` before adding backend code for editor/UI
needs.

## Current Documentation Task

The active docs goal is to keep a task-first documentation path:

- `README.md` routes agents by task.
- `TASK_INDEX.md` lists minimum docs, likely files, and focused checks.
- Detailed completed phase history lives in `archive/`.
- Historical tkinter/proof-of-concept material is archived, not deleted.

## Phase Status

| Phase | Title | Status |
|---|---|---|
| 0 | Memory leak fixes | Done |
| 1 | Forward-reachability helper | Done |
| 2 | Dependency list + validation | Done |
| 3 | Membank I/O + registry + descriptions | Done |
| 4 | Delete + insert nodes | Done |
| 4.5 | Config modal and selector usability | Done |
| 5 | Config tabs | Done |
| 5.5 | Keyboard nav hardening + config modal UX | Done |
| 6 | Breakpoints | Done |
| 7 | Per-node execution timing | Done |
| 8 | Completion registry + wait-until node | Done |
| 9 | Merge dynamic list + lineage barrier | Done |
| FA-0..FA-5 | Frontend standardization helpers | Done |
| 10 | Documentation modernization | Done |
| 10.5 | Backend/frontend boundary cleanup | Done |
| 11 | Real AI node execution | Deferred |
| 12 | Packaging and release hardening | Deferred |
| 13 | Cursor model foundation | Done |
| 14 | Key binding remap | Done |
| 15 | Editor rework | Done |
| 16 | File modal + node config tabs | Done |
| Docs | Task-first documentation overhaul | In progress |
| 17 | Node visual identity | Planned |
| 18 | Acceleration + help rewrite | Planned |
| 19 | Nested workflows: built-in subworkflow node | Planned |
| 20 | Nested workflows: user-created subworkflows | Planned |

## Recently Completed

- Node helper generator at `../aotn_node_helper/`.
- Generated node specs support `config_tabs` for Source / Parameters / Payloads.
- `NodeConfigScreen` honors schema `tab` hints.
- Focused generated-node tests live under `tests/generated/`.
- Branch config v1 supports 2-5 always-parallel spawn points and per-branch
  seed payloads.
- Merge Beacon is the user-facing name for persisted `branch_end_node`.
- File import/export uses picker-first behavior with typed-path fallback.

See `SESSION_LOG.md` for recent entries and `archive/SESSION_LOG_HISTORY.md`
for older entries.

## Next Planned Phase: Phase 17 — Node Visual Identity

Goal: make editor rows easier to scan without changing runtime behavior.

Planned behavior:

- Per-category colors derived from existing node metadata.
- Per-type or per-category glyphs on node rows.
- Utility/debug/pass-through nodes visually quieter than complex flow/AI nodes.
- Validation and Merge Beacon health colors remain clear.
- Cursor/highlight behavior stays stable with any visual row changes.

Likely files:

- `frontend/widgets/node_card.py`
- `frontend/widgets/node_list.py`
- `frontend/styles.tcss`
- `tests/test_debug_nodes.py`

Focused checks:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_card or editor_depth or branch_end"
```

## Later Roadmap

- **Phase 18 — Acceleration + help rewrite.** Hold-to-accelerate navigation,
  context-aware help polish, and a sweep for non-interactive nav stops.
- **Phase 19 — Built-in subworkflow node.** Run a saved workflow as a child
  supervisor from one node.
- **Phase 20 — User-created subworkflow nodes.** Publish workflows as reusable
  nodes with dependency/export policy.
- **Deferred AI integration.** Implement real AI node execution once UI and
  node authoring conventions stabilize.

## Standing Implementation Rules

- Start at `README.md`, then use `TASK_INDEX.md` for the task route.
- Keep backend/frontend boundaries strict.
- Prefer node metadata and helper specs over custom config UI.
- Use focused `pytest -k` slices for small fixes, then full suite before broad
  runtime/shared UI commits.
- Update `SESSION_LOG.md` after each completed change.
- Update `DOCS_MIGRATION_NOTES.md` when docs are moved, collapsed, archived, or
  deleted.

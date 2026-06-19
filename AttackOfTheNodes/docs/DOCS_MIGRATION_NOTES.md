# Documentation Migration Notes

This file explains documentation moves, collapses, archives, and deletions so
future agents understand why the docs tree changed.

## 2026-06-09 — Task-First Docs Overhaul

| Old location | New location | Action | Reason |
|---|---|---|---|
| `README.md` | `README.md` | Rewritten | Make the docs entry point a task router instead of a flat file list. |
| n/a | `TASK_INDEX.md` | Added | Provide task type -> minimum docs -> likely files -> focused checks. |
| n/a | `UI_QUICK_REFERENCE.md` | Added | Summarize current UI keys and command-mode rules so agents do not need the full 500-line TUI design doc for routine UI fixes. |
| `MASTER_BUILD_PLAN.md` | `archive/BUILD_PLAN_HISTORY.md` | Full copy archived | Keep completed phase detail available without forcing agents to read 1000+ lines by default. |
| `MASTER_BUILD_PLAN.md` | `MASTER_BUILD_PLAN.md` | Collapsed | Active file now contains current status, next roadmap, and links to history. |
| `SESSION_LOG.md` | `archive/SESSION_LOG_HISTORY.md` | Full copy archived | Preserve detailed historical session notes while keeping active log small. |
| `SESSION_LOG.md` | `SESSION_LOG.md` | Collapsed | Active file now keeps recent/current entries and points to full history. |
| `V05_BUILD_PLAN.md` | `archive/V05_BUILD_PLAN.md` | Archived | Historical Python/tkinter proof-of-concept plan; useful context but not part of the normal current-task path. |
| `FRONTEND_AUDIT_BUILD_PLAN.md` | `archive/plans/FRONTEND_AUDIT_BUILD_PLAN.md` | Archived | Completed frontend standardization plan; active rules now live in `AGENT_START_GUIDE.md`, `TUI_DESIGN.md`, and `TASK_INDEX.md`. |
| `USER_FRIENDLY_POLISH_BUILD_PLAN.md` | `archive/plans/USER_FRIENDLY_POLISH_BUILD_PLAN.md` | Archived | Planning context retained, but current roadmap summary lives in `MASTER_BUILD_PLAN.md`. |
| `AGENT_HANDOFF.md` | `AGENT_HANDOFF.md` | Rewritten | Reflect current documentation overhaul and the new docs entry flow. |
| `FILE_TREE.md` | `FILE_TREE.md` | Refreshed | Align file tree with archived docs and current tracked project shape. |

## 2026-06-13 — Headless Build Plan archived

| Old location | New location | Action | Reason |
|---|---|---|---|
| `HEADLESS_BUILD_PLAN.md` | `archive/plans/HEADLESS_BUILD_PLAN.md` | Archived | Plan H1–H5 implemented and verified (full suite 284 passed); kept as history. Active status folded into `MASTER_BUILD_PLAN.md` and `PROJECT_BACKLOG.md`; deferred UI follow-ups tracked in `PROJECT_BACKLOG.md`. README directory row moved from Planning/Backlog to Archive. |

## 2026-06-19 — Node Standardization Handoff added

| Old location | New location | Action | Reason |
|---|---|---|---|
| n/a | `NODE_STANDARDIZATION_HANDOFF.md` | Added | Consolidates the node-standardization design discussion into an adopted implementation plan (per-node I/O contract via `NodeFactory`, Category > Family > Type rename onto the canonical `category` key, canonical data-type vocab, unified helper spec, master-detail selector). §2 open decisions signed off 2026-06-19: rename approved reusing `category` (retire `primary_family`/`legacy_category` aliases, `group → family`); drill-in family nav; one-line-per-port `to:` display; no behavior badge. README Document Directory row added under Node Authoring. Its changes fold into `NODE_STANDARDS.md`, `PHASE_17_NODE_VISUAL_IDENTITY.md`, and `NODE_HELPER.md` when each track is implemented. |

## Deletions

No tracked documentation files were deleted in this pass. Historical and
completed planning files were archived instead.

Untracked root `docs/hello.txt` was intentionally not touched because it is
outside the tracked active docs tree and prior workflow asked to ignore
untracked unrelated files.

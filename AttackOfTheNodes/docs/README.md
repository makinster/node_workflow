# AttackOfTheNodes Docs

Start here. This docs folder is organized so agents can read the minimum
context needed for the task at hand, then open deeper references only when
needed.

The active project is the Python/Textual app in `AttackOfTheNodes/`. Historical
tkinter/proof-of-concept material lives under `docs/archive/`.

## Choose Your Task

| If you need to... | Read first | Then read if needed |
|---|---|---|
| Add or change a node | `AGENT_START_GUIDE.md`, `TASK_INDEX.md` | `PROJECT_KNOWLEDGE.md`, `ARCHITECTURE.md` |
| Fix frontend/UI behavior | `TASK_INDEX.md`, `UI_QUICK_REFERENCE.md` | `TUI_DESIGN.md`, `BACKEND_FRONTEND_BOUNDARY.md`, `PROJECT_BACKLOG.md` |
| Change backend/runtime behavior | `TASK_INDEX.md`, `ARCHITECTURE.md`, `SIGNAL_FLOW.md` | `PROJECT_KNOWLEDGE.md`, `BACKEND_FRONTEND_BOUNDARY.md` |
| Continue the roadmap | `AGENT_HANDOFF.md`, `MASTER_BUILD_PLAN.md` | `archive/BUILD_PLAN_HISTORY.md`, `SESSION_LOG.md` |
| Continue Phase 17 node identity | `PHASE_17_NODE_VISUAL_IDENTITY.md`, `TASK_INDEX.md` | `UI_QUICK_REFERENCE.md`, `TUI_DESIGN.md`, `BACKEND_FRONTEND_BOUNDARY.md` |
| Update docs | `README.md`, `TASK_INDEX.md`, `DOCS_MIGRATION_NOTES.md` | `archive/SESSION_LOG_HISTORY.md` |
| Check what changed recently | `SESSION_LOG.md` | `archive/SESSION_LOG_HISTORY.md` |

## Read-First Files

- `TASK_INDEX.md` — compact task router with likely code areas and focused
  checks.
- `AGENT_START_GUIDE.md` — practical checklist for common changes, especially
  node creation and config UI.
- `AGENT_HANDOFF.md` — current project state and next likely direction.
- `MASTER_BUILD_PLAN.md` — concise active roadmap and status.
- `SESSION_LOG.md` — recent session log. Older entries are archived.
- `BACKEND_FRONTEND_BOUNDARY.md` — read before moving UI behavior into backend
  services.
- `PHASE_17_NODE_VISUAL_IDENTITY.md` — active node taxonomy, selector filter,
  and editor row identity plan.

## Reference Files

- `ARCHITECTURE.md` — component responsibilities and invariants.
- `SIGNAL_FLOW.md` — runtime/event flow through backend and frontend.
- `PROJECT_KNOWLEDGE.md` — compact current-state project knowledge.
- `UI_QUICK_REFERENCE.md` — short current UI keys and command-mode rules.
- `TUI_DESIGN.md` — current Textual UI conventions.
- `FILE_TREE.md` — current tracked project file map.
- `PROJECT_BACKLOG.md` — deferred cleanup and future project ideas.

## Archive

- `archive/BUILD_PLAN_HISTORY.md` — full pre-overhaul build plan and completed
  phase details.
- `archive/SESSION_LOG_HISTORY.md` — full pre-overhaul session log.
- `archive/V05_BUILD_PLAN.md` — historical Python/tkinter proof-of-concept
  plan.
- `archive/plans/` — completed or lower-priority planning docs removed from
  the default read path.

## Documentation Rules

- Keep the default path small. Summarize in active docs and link to archives for
  deep history.
- Update `SESSION_LOG.md` after every completed change.
- Update `MASTER_BUILD_PLAN.md` when roadmap status or phase order changes.
- Update `TASK_INDEX.md` when task routes, helper commands, or focused checks
  change.
- Add an entry to `DOCS_MIGRATION_NOTES.md` when moving, collapsing, archiving,
  or deleting docs.

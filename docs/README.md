# AttackOfTheNodes Docs Index

Start here when entering the project. The current active app is the
Python/Textual build under `attackofthenodes_v05/`; older Chrome-extension and
tkinter material is historical unless explicitly labeled current.

## Read First

1. `AGENT_START_GUIDE.md`
   - Fast task checklist for adding nodes, screens, config fields, keybindings,
     tests, and docs updates.

2. `AGENT_HANDOFF.md`
   - Fast current-state summary.
   - Tells you what phase is next and which docs are authoritative.

3. `MASTER_BUILD_PLAN.md`
   - Current source of truth for architecture, completed phases, remaining
     roadmap, and test rules.

4. `SESSION_LOG.md`
   - Chronological record of what was actually changed and verified.

5. `BACKEND_FRONTEND_BOUNDARY.md`
   - Rules for keeping backend engine code reusable across future frontends.
   - Read before moving UI behavior into backend services.

## Phase-Specific Docs

- `TUI_DESIGN.md`
  - Current Textual UI conventions, screen structure, and keyboard behavior.

- `FRONTEND_AUDIT_BUILD_PLAN.md`
  - Frontend standardization and keyboard/navigation audit plan.

- `PROJECT_BACKLOG.md`
  - Deferred cleanup projects, including docs modernization and UI toolkit work.

## Current Reference Docs

These are current-state references refreshed during Phase 10:

- `ARCHITECTURE.md`
- `SIGNAL_FLOW.md`
- `PROJECT_KNOWLEDGE.md`
- `FILE_TREE.md`

## Historical Docs

- `V05_BUILD_PLAN.md`
  - Historical Python proof-of-concept build plan.
  - Useful for understanding how the project evolved, but not authoritative for
    current Textual UI implementation details.

## Documentation Rule

Every implementation phase should update:

- `SESSION_LOG.md` with what changed and how it was verified.
- `AGENT_HANDOFF.md` if the next-agent starting point changes.
- `MASTER_BUILD_PLAN.md` if roadmap status, boundaries, or phase ordering
  changes.

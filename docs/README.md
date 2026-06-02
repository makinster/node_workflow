# AttackOfTheNodes Docs Index

Start here when entering the project. Some older files still contain useful
history, but the current Textual/Python build has moved quickly, so read in
this order.

## Read First

1. `AGENT_HANDOFF.md`
   - Fast current-state summary.
   - Tells you what phase is next and which docs are authoritative.

2. `MASTER_BUILD_PLAN.md`
   - Current source of truth for architecture, completed phases, remaining
     roadmap, and test rules.

3. `SESSION_LOG.md`
   - Chronological record of what was actually changed and verified.

4. `BACKEND_FRONTEND_BOUNDARY.md`
   - Rules for keeping backend engine code reusable across future frontends.
   - Read before moving UI behavior into backend services.

## Phase-Specific Docs

- `TUI_DESIGN.md`
  - Current Textual UI conventions, screen structure, and keyboard behavior.

- `FRONTEND_AUDIT_BUILD_PLAN.md`
  - Frontend standardization and keyboard/navigation audit plan.

- `PROJECT_BACKLOG.md`
  - Deferred cleanup projects, including docs modernization and UI toolkit work.

## Reference Docs To Treat Carefully

These are useful, but may still contain historical language from the
Chrome-extension or tkinter eras. Prefer `MASTER_BUILD_PLAN.md` when they
conflict.

- `ARCHITECTURE.md`
- `SIGNAL_FLOW.md`
- `PROJECT_KNOWLEDGE.md`
- `V05_BUILD_PLAN.md`
- `FILE_TREE.md`

## Documentation Rule

Every implementation phase should update:

- `SESSION_LOG.md` with what changed and how it was verified.
- `AGENT_HANDOFF.md` if the next-agent starting point changes.
- `MASTER_BUILD_PLAN.md` if roadmap status, boundaries, or phase ordering
  changes.

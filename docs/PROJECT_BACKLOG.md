# AttackOfTheNodes Project Backlog

## Later Project — Documentation Modernization

The docs folder has split-brain history from the Chrome-extension concept,
tkinter prototype, and current Textual TUI. Keep this as a later focused docs
project, separate from the active master build plan.

Recommended cleanup:

- Refresh `PROJECT_KNOWLEDGE.md` so it is again safe as the current-state
  single-source overview.
- Rewrite `ARCHITECTURE.md` around the Python/Textual implementation instead of
  the older IndexedDB/Dexie/BackendBridge architecture.
- Rewrite `SIGNAL_FLOW.md` around local backend services, Textual screens, and
  the current event bus.
- Regenerate `FILE_TREE.md` from the current workspace and include the
  standardization/debug-node files.
- Keep historical tkinter roadmap material in `V05_BUILD_PLAN.md` clearly
  labeled as history, not current implementation guidance.


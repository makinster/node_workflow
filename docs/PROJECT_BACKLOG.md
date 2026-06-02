# AttackOfTheNodes Project Backlog

## Later Project — Documentation Modernization

The docs folder has split-brain history from the Chrome-extension concept,
tkinter prototype, and current Textual TUI. Keep this as a later focused docs
project, separate from the active master build plan.

`MASTER_BUILD_PLAN.md` is now the current comprehensive source of truth. The
remaining modernization task is to refresh the older reference docs so they stop
contradicting it.

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

## Later Project — Frontend Command UI Toolkit

Current config and modal UX should converge on small shared helpers instead of
per-screen key handling. `frontend/widgets/command_navigation.py` is the first
step and currently supports `NodeConfigScreen`.

Recommended cleanup:

- Migrate settings, workflow path prompts, node selector, branch selector, and
  other modal screens to the same command-navigation helper where practical.
- Add a small wrapper around `app.notify(...)` for a unified toast/alert system
  with consistent copy, severity, and duration.
- Keep schema-generated node config as the default path; extend field schemas or
  frontend render helpers before adding per-node custom modal logic.
- Add a focused keyboard-only smoke suite for common modal flows: open, move,
  activate, type, escape typing mode, save/cancel, and scroll to off-screen
  fields.

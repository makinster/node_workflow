# AttackOfTheNodes Project Backlog

## Later Project — Documentation Modernization

The docs folder has split-brain history from the Chrome-extension concept,
tkinter prototype, and current Textual TUI. Keep this as a later focused docs
project, separate from the active master build plan.

`docs/README.md` is now the entry point and `MASTER_BUILD_PLAN.md` is the
current comprehensive source of truth. The remaining modernization task is to
refresh the older reference docs so they stop contradicting it.

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

## Planned Project — Backend / Frontend Boundary Cleanup

The backend should remain reusable for future CLI, web, or API frontends. The
current Textual editor introduced tombstone behavior that is useful visually,
but not inherently an execution-engine concept.

Use `BACKEND_FRONTEND_BOUNDARY.md` as the plan.

Recommended cleanup:

- Move tombstone placeholders into a frontend editor adapter.
- Keep backend `WorkflowMap.delete_node()` as a pure graph operation.
- Remove or deprecate backend `replace_with_tombstone()` once the frontend
  adapter is covered by tests.
- Replace tombstone-specific backend validator copy with generic graph errors.
- Decide whether layout metadata such as `position` and navigation metadata
  such as `bookmarked` belong in portable workflow saves or editor sidecars.

## Later Project — Frontend Command UI Toolkit

Current config and modal UX should converge on small shared helpers instead of
per-screen key handling. `frontend/widgets/command_navigation.py` is the first
step and currently supports `NodeConfigScreen`. Use
`FRONTEND_AUDIT_BUILD_PLAN.md` as the implementation sequence for this work.

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

## Later Project — Schema-Driven Node UI Expansion

Goal: make adding a node feel like adding backend metadata, not hand-editing
frontend menus.

Recommended cleanup:

- Extend config schema only with generic keys: placeholder text, min/max/step for
  numeric fields, optional blank-select behavior, multiline height hints, and
  section visibility conditions.
- Add tests for every schema key in `frontend/widgets/form_generator.py`.
- Move branch-label generation and pass-through notes toward documented generic
  `ui_hints` where possible.
- Create a "node author checklist" in docs: metadata, schema, ports, categories,
  pass-through behavior, memory-bank declarations, and expected generated UI.
- Add a validation test that every registered node can mount its generated config
  without frontend custom code unless it is explicitly listed as a structural
  topology editor.

## Later Project — Unified Toast / Alert System

The app currently calls `app.notify(...)` directly from many screens. That is
fine for now, but it is already producing inconsistent wording and severity.

Recommended cleanup:

- Add a frontend alert helper with standard severities, duration defaults, and
  copy conventions.
- Route common actions through named helpers: saved, loaded, validation passed,
  missing selection, destructive action canceled, destructive action completed,
  run started/stopped, import/export failed.
- Add de-duplication for repeated keyboard mistakes such as "No node selected".
- Keep the helper frontend-only; backend services should continue publishing
  structured events, not UI copy.

# AttackOfTheNodes Project Backlog

## Completed Project — Documentation Modernization

The docs folder previously had split-brain history from the Chrome-extension
concept, tkinter prototype, and current Textual TUI. Phase 10 refreshed the
active reference docs and labeled the remaining historical proof-of-concept
material.

`docs/README.md` is now the entry point and `MASTER_BUILD_PLAN.md` is the
current comprehensive source of truth.

Completed cleanup:

- Refreshed `PROJECT_KNOWLEDGE.md` so it is again safe as the current-state
  single-source overview.
- Rewrote `ARCHITECTURE.md` around the Python/Textual implementation instead of
  the older IndexedDB/Dexie/BackendBridge architecture.
- Rewrote `SIGNAL_FLOW.md` around local backend services, Textual screens, and
  the current event bus.
- Regenerated `FILE_TREE.md` from the current workspace and included the
  standardization/debug-node files.
- Labeled historical tkinter roadmap material in `V05_BUILD_PLAN.md` clearly
  labeled as history, not current implementation guidance.

Ongoing rule: implementation phases should keep `SESSION_LOG.md` current and
update `MASTER_BUILD_PLAN.md` or `AGENT_HANDOFF.md` when roadmap status changes.

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

## Near-Term Project — Frontend Command UI Toolkit

Current config and modal UX should converge on small shared helpers instead of
per-screen key handling. `frontend/widgets/command_navigation.py` is the first
step and currently supports `NodeConfigScreen`. Use
`FRONTEND_AUDIT_BUILD_PLAN.md` as the implementation sequence for this work.

Recommended cleanup:

- Continue using shared command helpers for new modal screens. `SettingsScreen`,
  path prompts, user input, generated config fields, and modal selectors already
  have baseline helper coverage.
- Keep future notification copy routed through `frontend/notifications.py`.
- Keep schema-generated node config as the default path; extend field schemas or
  frontend render helpers before adding per-node custom modal logic.
- Add a focused keyboard-only smoke suite for common modal flows: open, move,
  activate, type, escape typing mode, save/cancel, and scroll to off-screen
  fields.

## Near-Term Project — Branch Health Visualization

Goal: make branch validity visible while editing, before users need to run full
validation.

Recommended cleanup:

- Derive branch health from workflow structure, not stored UI state.
- Represent at least three branch states:
  - valid branch ending: end/output node or connected Merge Beacon node;
  - branch ended but not merged: Merge Beacon exists but is not connected to a
    Merge node;
  - floating branch: no valid output/end node and no Merge Beacon.
- Surface those states in the editor with clear but restrained color: green for
  valid, yellow/orange for branch-ended-but-unmerged, and red/orange for
  floating/incomplete branches.
- Extend `NodeCard` or a future editor display adapter so branch-health color is
  separate from execution status icons.
- Fold this into the FA-7 visual pass: VS Code-like dark styling, readable node
  type colors, type-specific brackets/icons, larger editor rows, and dimmer
  command text fields when not editing.

## Later Project — Schema-Driven Node UI Expansion

Goal: make adding a node feel like adding backend metadata, not hand-editing
frontend menus.

Recommended cleanup:

- Redesign the node library into clearer categories and subcategories. Flow
  should eventually distinguish always-parallel branch nodes, conditional branch
  nodes, merge/wait nodes, and utility markers instead of forcing all branching
  behavior through one generic node.
- Extend config schema only with generic keys: placeholder text, min/max/step for
  numeric fields, optional blank-select behavior, multiline height hints, and
  section visibility conditions.
- Add tests for every schema key in `frontend/widgets/form_generator.py`.
- Move branch-label generation and pass-through notes toward documented generic
  `ui_hints` where possible.
- Simplify generated config surfaces: ordinary nodes should show only the fields
  they declare, semantic transient input/output metadata, memory-bank sections
  when enabled, and generic topology selectors when required.
- Create a "node author checklist" in docs: metadata, schema, ports, categories,
  pass-through behavior, memory-bank declarations, and expected generated UI.
- Add a validation test that every registered node can mount its generated config
  without frontend custom code unless it is explicitly listed as a structural
  topology editor.

## Later Project — Unified Toast / Alert System

The project has `frontend/notifications.py` and frontend screens route common
notifications through it. Add richer toast behavior on top of that helper.

Recommended cleanup:

- Add a frontend alert helper with standard severities, duration defaults, and
  copy conventions.
- Route common actions through named helpers: saved, loaded, validation passed,
  missing selection, destructive action canceled, destructive action completed,
  run started/stopped, import/export failed.
- Add de-duplication for repeated keyboard mistakes such as "No node selected".
- Keep the helper frontend-only; backend services should continue publishing
  structured events, not UI copy.

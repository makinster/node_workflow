# AttackOfTheNodes Agent Handoff

## Current State

The active app is `attackofthenodes_v05/`, a Python/Textual workflow editor and
execution TUI backed by an asyncio workflow engine. The tkinter frontend is
obsolete. Backend services remain UI-agnostic; frontend behavior lives under
`frontend/screens/`, `frontend/widgets/`, and `frontend/styles.tcss`.

## Documentation Entry Point

Start with `docs/README.md`. It separates current reference docs from
historical proof-of-concept material.

## Active Build Plan

Use `docs/MASTER_BUILD_PLAN.md` as the comprehensive source of truth. It merges
the active dependency-ordered phase plan, the Textual TUI state, the working
rules, and the current architecture model. Phases 0 through 10.5 plus the Phase
5.5 keyboard/config hardening pass are complete. Phase 13 cursor model
foundation is the next planned phase.

Completed from the master plan:

- Phase 0: Memory leak fixes.
- Phase 1: `WorkflowMap.nodes_reachable_from(node_id)`.
- Phase 2: derived `input_sources` at save/export/duplicate and input-source
  validation.
- Phase 3: membank output/input config sections and structure-derived registry.
- Phase 4: insert-after-highlight editor behavior and no-cascade tombstone
  deletion.
- Phase 5: grouped schema fields render as tabs when more than one group exists;
  simple configs stay flat.
- Phase 5.5: keyboard navigation hardening and config modal UX (see below).
- Phase 6: node breakpoints pause globally before execution and resume through
  the existing pause path.
- Phase 7: per-node execution timings publish live, render in the TUI, and
  persist into run history.
- Phase 8: completion registry and `WaitUntilNode` support cross-branch
  gating with downstream target filtering in config.
- Phase 9: `MergeNode` plus counter-style lineage barrier for branch
  recombination.
- Phase 10: documentation modernization for current Python/Textual references.
- Phase 10.5: backend/frontend boundary cleanup — removed unused backend tombstone
  methods, updated validator message, documented portable workflow fields.
- FA-0 through FA-5: frontend standardization audit and helper extraction.

Recent usability patch (Phase 5.5 — keyboard nav hardening):

- `Ctrl+Q`/`Esc` inside a text field exits edit mode instead of closing the
  modal. `AttackOfTheNodesApp.check_action` blocks `"back"` while editing.
- `#node-config-scroll` has `can_focus = False` to prevent focus stealing on
  click.
- Memory-bank outputs are count-driven declarations. Each row renders a compact
  `Output Description:` field plus a bounded multiline `Output:` field for long
  values.
- Nav section headers use `nav-section` CSS class; `_nav_widget` tracks the
  highlighted non-interactive stop; `.nav-highlight` makes it visible.
- `.generated-form { height: auto; }` — critical CSS fix; `Vertical` collapses
  to zero height inside `VerticalScroll` without this.
- Branch/router nodes generate label fields from `output_ports` and hide
  memory-bank output controls; editor branch rows use the configured labels
  instead of raw port ids.
- `_ancestor_visible` filters `display=False` containers from nav list.
- `scroll_to_widget` called directly on scroll container for reliable scrolling.
- `frontend/widgets/command_navigation.py` is the single place for command-mode
  activation, dropdown behavior, and `SelectOverlay._on_key` patching. Do not
  duplicate Textual overlay handling in individual screens.
- `SelectOverlay` key patch: `_install_select_overlay_command_bindings()` wraps
  `SelectOverlay._on_key` at import time so W/S/arrows/E/Ctrl+Q work inside any
  expanded dropdown without per-screen handlers. Use `commit_highlighted_select`
  to commit values from outside the overlay.
- Schema-generated dropdowns should not include Textual's blank `Select` row
  unless a future schema explicitly requests an optional blank value.

Frontend standardization FA phases (FA-0 through FA-5) completed 2026-06-02:

- `frontend/widgets/command_navigation.py` — shared command modal toolkit
- `frontend/widgets/list_navigation.py` — shared list selector helpers
- `frontend/widgets/dynamic_sections.py` — checkbox/count-driven section helpers
- `frontend/notifications.py` — named notification helpers
- `frontend/widgets/form_generator.py` expanded with `placeholder`, validators,
  `height`, `language`, and multiselect defaults

Frontend standardization direction:

- Normal new nodes should be UI-supported through node metadata:
  `display_name`, `description`, `category`, ports, `default_config`,
  `config_schema`, and optional `ui_hints`.
- Use generic schema/helper extensions before adding custom node-specific config
  screens.
- Known recurring UI bug classes are focus drift, hidden widgets in nav lists,
  scroll containers taking focus, dynamic config rows not remounting, dropdown
  overlay state persistence, and direct ad hoc `app.notify(...)` copy.

Recent docs pass:

- `docs/README.md` is the docs entry point.
- `docs/MASTER_BUILD_PLAN.md` is the comprehensive build plan.
- `docs/PROJECT_KNOWLEDGE.md`, `ARCHITECTURE.md`, `SIGNAL_FLOW.md`, and
  `FILE_TREE.md` have been refreshed for the current Python/Textual build.
- `docs/V05_BUILD_PLAN.md` is labeled as historical proof-of-concept history.

Latest phase:

- Phase 13 (cursor model foundation) is complete.
- Phase 14 (editor key binding remap) is complete.
  - `frontend/widgets/cursor_state.py` — lightweight `CursorState` with
    `mode` ("nav"/"edit"), `set_nav()`, `set_edit()`.
  - `frontend/widgets/command_screen_mixin.py` — `CommandScreenMixin` with W/S/
    up/down/E/Enter priority bindings injected via `__init_subclass__` so
    `DOMNode._merge_bindings` picks them up. Includes `check_action` guard
    that blocks nav while a text widget is editing, and `_sync_cursor_mode`
    that updates `app.cursor_state` and the `StatusBar` mode indicator.
  - `frontend/widgets/status_bar.py` — `set_mode(mode)` method added.
  - `frontend/app.py` — `cursor_state: CursorState` attribute added.
  - `SettingsScreen`, `UserInputScreen`, `PathPromptScreen`, `NodeConfigScreen`
    migrated to inherit `CommandScreenMixin`.
  - `CommandInput._on_key` calls `_sync_cursor_mode()` on screen after entering
    edit mode so cursor state stays in sync.
  - Key Textual constraint discovered: `CommandScreenMixin.BINDINGS` are skipped
    by `_merge_bindings` (plain Python class, not DOMNode). Fixed by injecting
    the nav bindings into the concrete subclass's `BINDINGS` in
    `__init_subclass__`, before `super().__init_subclass__()` calls
    `DOMNode._merge_bindings()`.
- 79 tests passing after the editor highlight persistence polish.
- The next planned phase is Phase 15 (editor rework).

Recently completed:
- Phase 14: Key binding remap — editor grammar uses W/S or up/down for vertical
  movement, A/D or left/right for open branch-view cycling, Ctrl+A/Ctrl+D or
  Ctrl+left/Ctrl+right for Branch End branch cycling, E to edit, I to insert
  after the highlight, Ctrl+I to add at branch end, and X/backspace to delete.

Planned future phases (see Section 6 of MASTER_BUILD_PLAN.md for full specs):
- Phase 15: Editor rework — Quick View right panel, human-readable-name-first,
  editable branch names, top-bar/bottom-bar split.
- Phase 16: File modal + node config tabs — consolidated File modal, fixed
  CORE/PARAMETERS/ADVANCED/CONNECTIONS tabs, tabbed settings with API keys.
- Phase 17: Node visual identity — per-category colors, per-type glyphs,
  size-by-category.
- Phase 18: Acceleration + help rewrite — hold-to-accelerate, context-organized
  help, regression sweep for nav stops.
- Phase 19: Nested workflows (built-in) — SubworkflowNode spawning a child
  supervisor, reusing Phase 9 lineage barrier.
- Phase 20: Nested workflows (user-created) — dynamic subworkflow registry,
  publish-workflow-as-node, export dependency policy.

## Read First

- `docs/MASTER_BUILD_PLAN.md` for current architecture, implementation order,
  contracts, and testing rules.
- `docs/BACKEND_FRONTEND_BOUNDARY.md` before backend changes motivated by
  editor/UI behavior.
- `docs/FRONTEND_AUDIT_BUILD_PLAN.md` before frontend audit or UI
  standardization work.
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

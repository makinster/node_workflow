# AttackOfTheNodes Agent Handoff

## Current State

The active app is `attackofthenodes_v05/`, a Python/Textual workflow editor and
execution TUI backed by an asyncio workflow engine. The tkinter frontend is
obsolete. Backend services remain UI-agnostic; frontend behavior lives under
`frontend/screens/`, `frontend/widgets/`, and `frontend/styles.tcss`.

## Active Build Plan

Use `docs/MASTER_BUILD_PLAN.md` as the comprehensive source of truth. It merges
the active dependency-ordered phase plan, the Textual TUI state, the working
rules, and the current architecture model. Phases 0 through 9 plus the Phase 5.5
keyboard/config hardening pass are complete. The next unfinished project phase
is Phase 10 documentation modernization unless `docs/SESSION_LOG.md` says
otherwise.

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
- `frontend/widgets/command_navigation.py` is the new shared place for
  command-mode activation and dropdown behavior. Do not duplicate Textual
  `Select` overlay handling in individual screens.
- Schema-generated dropdowns should not include Textual's blank `Select` row
  unless a future schema explicitly requests an optional blank value.

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

- `docs/MASTER_BUILD_PLAN.md` was rewritten as the comprehensive build plan.
- Older docs that mention Chrome-extension, IndexedDB/Dexie, JavaScript
  backends, or tkinter should be treated as historical until Phase 10 refreshes
  them.

Latest phase:

- Phase 9 (merge dynamic list + lineage barrier) is complete.
- Merge config uses a multi-select branches-to-close list plus a carry-forward
  dropdown. Merge output naming/description fields were intentionally removed.
- Branch End is no-config; editor rows are red while open and green when wired
  to a Merge node.
- Phase 5.5 (keyboard nav hardening) is complete.
- The next unfinished project phase is Phase 10 documentation modernization.
  For more implementation work, Phase 13 cursor model foundation is the next
  planned UI-heavy phase.

Planned future phases (see Section 6 of MASTER_BUILD_PLAN.md for full specs):

- Phase 13: Cursor model foundation — app-owned CursorState, WASD/arrow movement,
  no silent keypresses, [NAV]/[EDIT] status indicator.
- Phase 14: Key binding remap — final grammar (E/I/X/+/F/Ctrl+X), retires A and
  L/O standalone bindings.
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

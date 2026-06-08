# User-Friendly Polish Build Plan

This plan turns the remaining visual, navigation, copy, and discoverability work
into small implementation passes. The goal is not decoration first; it is making
the Textual app easier for an average computer user to read, predict, and use
with either keyboard or mouse.

Use this plan after the current Phase 15/16 editor and config work is stable.
It expands the Phase 17 and Phase 18 roadmap items in `docs/MASTER_BUILD_PLAN.md`.

## UX Principles

- Every key press should do something visible or give a clear notification.
- The highlighted item should never disappear silently.
- Text should be short, human-facing, and free of raw ids unless ids are useful
  for debugging or disambiguation.
- Keyboard and mouse should cooperate. Clicking should not put the keyboard into
  a broken focus state.
- New nodes should feel native through metadata and schema, not custom frontend
  code.
- Styling should improve scanning. Color and glyphs should communicate category,
  branch health, and run state without turning the editor into visual noise.

## Pass 1 — Copy And Language Cleanup

**Goal:** make the UI read like an app, not a debug console.

Files:

- `attackofthenodes_v05/frontend/screens/editor.py`
- `attackofthenodes_v05/frontend/screens/help.py`
- `attackofthenodes_v05/frontend/screens/node_config.py`
- `attackofthenodes_v05/frontend/screens/workflow_library.py`
- `attackofthenodes_v05/frontend/notifications.py`
- node metadata under `attackofthenodes_v05/backend/nodes/`

Tasks:

- Replace visible underscores with spaces in user-facing labels.
- Prefer `Name`, `Kind`, `Inputs`, `Outputs`, `Memory`, and `About` over
  implementation terms.
- Keep screen help short. Put only the bindings relevant to the current screen
  in Help.
- Audit notification copy so it says what happened and what the user can do next.
- Ensure each node has a friendly `display_name`, `description`, and
  `default_alias`.

Done when:

- A non-programmer can scan the editor and config windows without seeing raw
  Python-style names except where intentionally exposed.
- Help and notifications match the shipped keybindings.

Tests:

- Add focused tests for help text, editor Quick View copy, and notification
  helper messages.

## Pass 2 — Focus And Highlight Reliability

**Goal:** eliminate the class of bugs where keyboard controls stop working after
mouse use, alerts, scrolling, or screen transitions.

Files:

- `attackofthenodes_v05/frontend/screens/editor.py`
- `attackofthenodes_v05/frontend/widgets/command_screen_mixin.py`
- `attackofthenodes_v05/frontend/widgets/command_navigation.py`
- `attackofthenodes_v05/frontend/widgets/list_navigation.py`
- `attackofthenodes_v05/frontend/widgets/node_list.py`

Tasks:

- Make every command screen declare one canonical focus target after mount.
- Re-anchor focus before command actions that depend on a selected item.
- Keep exactly one visible highlight in editor lists and modal lists.
- Ensure transient notifications do not steal or clear focus.
- Keep text fields in nav mode visually different from edit mode.
- Add a small helper for "restore visible highlight or choose first valid item"
  and use it across list screens.

Done when:

- Mixing mouse clicks and keyboard controls cannot make `W/S/A/D/E` inert.
- Returning from run, file, config, help, and alert screens restores a visible
  highlight.

Tests:

- Add mounted regressions for editor, node selector, file menu, memory viewer,
  and config modal focus recovery.

## Pass 3 — Branch Health And Editor Signals

**Goal:** make workflow structure problems visible while editing.

Files:

- `attackofthenodes_v05/frontend/screens/editor.py`
- `attackofthenodes_v05/frontend/widgets/node_card.py`
- `attackofthenodes_v05/frontend/styles.tcss`
- optional frontend helper: `attackofthenodes_v05/frontend/branch_health.py`

Tasks:

- Derive branch health from workflow topology, not stored state.
- Represent three branch states:
  - valid: output/end node or Merge Beacon connected to a Merge;
  - ended but unmerged: Merge Beacon exists but is not connected to a Merge;
  - floating: no valid terminal and no Merge Beacon.
- Show branch health with restrained color in editor rows.
- Keep branch health separate from execution status.
- Make Merge Beacon color update after load, save, connect, disconnect, and merge
  config changes.

Done when:

- Users can tell which branches need attention before running validation.
- Existing save files refresh their branch status correctly after load.

Tests:

- Add topology tests for valid, unmerged, and floating branches.
- Add editor rendering tests for color/status class assignment.

## Pass 4 — Node Visual Identity

**Goal:** make node types recognizable at a glance.

Files:

- `attackofthenodes_v05/frontend/widgets/node_card.py`
- `attackofthenodes_v05/frontend/styles.tcss`
- `attackofthenodes_v05/backend/node_category.py`
- optional frontend helper: `attackofthenodes_v05/frontend/node_visuals.py`

Tasks:

- Add category colors using existing node category metadata.
- Add simple type glyphs or brackets for common categories:
  - Flow
  - Data
  - IO
  - AI
  - Debug
  - Utility
- Keep utility nodes compact.
- Give complex nodes slightly more visual weight only if the list remains easy
  to scan.
- Avoid overloading color: category color, branch health, and execution status
  must remain distinguishable.

Done when:

- The editor list is easier to scan without opening config.
- Variable row heights, if introduced, do not break cursor scrolling.

Tests:

- Add rendering tests for category classes and branch-health class coexistence.
- Add a keyboard scroll regression if row heights change.

## Pass 5 — Config Form Readability

**Goal:** make generated node config forms clear and predictable.

Files:

- `attackofthenodes_v05/frontend/screens/node_config.py`
- `attackofthenodes_v05/frontend/widgets/form_generator.py`
- `attackofthenodes_v05/frontend/widgets/dynamic_sections.py`
- node metadata under `attackofthenodes_v05/backend/nodes/`

Tasks:

- Keep ordinary nodes schema-driven.
- Use fixed config sections where helpful:
  - Core
  - Parameters
  - Inputs
  - Outputs
  - Memory
  - Last Run
- Make transient output name/description overrides clear and compact.
- Disable or dim output fields when pass-through is enabled.
- Keep long text safe with bounded multiline fields and scrollable sections.
- Prefer generic schema hints over node-specific UI code.

Done when:

- A new ordinary node can define metadata/schema and get a usable config screen.
- Long fields do not break modal layout.

Tests:

- Add mount tests for every supported schema type.
- Add tests that pass-through disables output declarations.
- Add tests that long descriptions/outputs remain scrollable.

## Pass 6 — File, Settings, And Help Polish

**Goal:** make secondary screens feel consistent.

Files:

- `attackofthenodes_v05/frontend/screens/workflow_library.py`
- `attackofthenodes_v05/frontend/screens/settings.py`
- `attackofthenodes_v05/frontend/screens/help.py`
- `attackofthenodes_v05/frontend/widgets/list_navigation.py`

Tasks:

- Finish File screen consolidation around New, Open, Save, Save As, Import, and
  Export.
- Keep workflow rows name-first and id-free.
- Keep one visible Cancel control at the bottom of modal screens.
- Make Settings tab-friendly before adding real API-key storage.
- Make Help context-aware per screen and authoritative for keybindings.
- Remove duplicate keybinding copy from screens when Help covers it.

Done when:

- File, Settings, and Help follow the same movement/activation/cancel rules as
  node config and node selector.

Tests:

- Add modal navigation tests for W/S, arrows, E, Enter, Esc, Ctrl+Q, and Ctrl+S
  where supported.

## Pass 7 — Navigation Acceleration

**Goal:** make large workflows and long modal lists fast without losing control.

Files:

- `attackofthenodes_v05/frontend/widgets/command_screen_mixin.py`
- `attackofthenodes_v05/frontend/widgets/list_navigation.py`
- `attackofthenodes_v05/frontend/screens/settings.py`
- `attackofthenodes_v05/frontend/styles.tcss`

Tasks:

- Add hold-to-accelerate for repeated W/S and arrow navigation.
- Add a setting to disable acceleration.
- Keep acceleration predictable: slow at first, faster only while held.
- Do not accelerate while text fields are editing.
- Add a small visual cue only if it helps and does not clutter the UI.

Done when:

- Long lists are comfortable with keyboard only.
- Acceleration never skips past the intended item immediately after a single
  key press.

Tests:

- Add deterministic key-repeat tests around list movement and boundaries.

## Pass 8 — Accessibility And Manual Smoke Checklist

**Goal:** lock down a usable baseline before adding bigger features.

Tasks:

- Create a keyboard-only smoke checklist in docs.
- Create a mouse-plus-keyboard smoke checklist in docs.
- Check half-screen terminal layout.
- Check common Windows Terminal / WSL behavior.
- Verify selected text copy with `Ctrl+C` where terminal support allows it.
- Verify `Ctrl+Q` only quits from editor and exits edit mode first elsewhere.
- Verify no modal has unreachable controls.

Done when:

- A new agent can manually smoke-test the UI in 10 minutes.
- The checklist catches the recurring focus, highlight, scroll, and edit-mode
  bugs seen during the frontend stabilization work.

## Suggested Order

1. Pass 2 — Focus And Highlight Reliability.
2. Pass 1 — Copy And Language Cleanup.
3. Pass 3 — Branch Health And Editor Signals.
4. Pass 5 — Config Form Readability.
5. Pass 6 — File, Settings, And Help Polish.
6. Pass 4 — Node Visual Identity.
7. Pass 7 — Navigation Acceleration.
8. Pass 8 — Accessibility And Manual Smoke Checklist.

This order prioritizes trust and predictability before visual style. Visual
identity lands after the editor is reliable enough that styling does not hide
behavior bugs.

## Verification Standard

For each pass:

```bash
cd attackofthenodes_v05
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v
```

Update `docs/SESSION_LOG.md` after implementation. Update
`docs/TUI_DESIGN.md` when behavior or keybindings change.

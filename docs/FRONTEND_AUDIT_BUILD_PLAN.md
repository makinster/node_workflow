# Frontend Audit and Standardization Build Plan

**Created:** 2026-06-02
**Scope:** `attackofthenodes_v05/frontend/`
**Goal:** audit the current Textual frontend, fix recurring UI bug classes, and
standardize the path from backend node metadata to usable UI.

This plan is intentionally incremental. Each phase should audit the current
state, improve one standardization layer, add focused coverage where practical,
and update this document with what was found.

---

## 1. Audit Thesis

Recent frontend bugs share a small set of causes:

- Textual widget defaults leaking into command-mode workflows.
- Each modal reimplementing keyboard navigation slightly differently.
- Focus moving invisibly to labels, hidden widgets, scroll containers, or
  off-screen controls.
- Dynamic config sections remounting unreliably or losing user-entered values.
- Node-specific config UI bypassing the schema generator.
- Direct `app.notify(...)` calls producing inconsistent alert behavior.

The standardization approach is:

1. Prefer backend node metadata and schema-generated config.
2. Route common keyboard/focus behavior through shared frontend helpers.
3. Treat custom per-node UI as a last resort for topology-derived editors such
   as merge branch selection.
4. Add small regression tests for every bug class as it is fixed.

---

## 2. Current Frontend Surfaces

### Root

- `frontend/app.py`: App bindings, screen routing, workflow actions,
  notifications, import/export/load/delete flows.
- `frontend/styles.tcss`: modal, editor, generated-form, node-card, and
  command-mode visual styling.
- `frontend/ui_state.py`: UI mirror store.

### Screens

- Main screens: `editor.py`, `execution.py`.
- Modal/action screens: `node_selector.py`, `node_config.py`,
  `branch_selector.py`, `confirm.py`, `workflow_library.py`, `settings.py`,
  `user_input.py`, `memory_viewer.py`, `output_viewer.py`, `error_details.py`,
  `help.py`.

### Widgets

- `form_generator.py`: backend config schema to Textual widgets.
- `command_input.py`: command-before-edit text fields.
- `command_navigation.py`: shared select/list/text/button activation helpers.
- `node_list.py`, `node_card.py`, `status_bar.py`.

### Known Historical Noise

The old tkinter modules and old `frontend/modals/` package are obsolete or
deleted in the active branch. Do not revive patterns from those files.

---

## 3. Standardization Targets

### A. Node UI Contract

A normal node should be UI-supported without frontend edits when it defines:

- `node_type`
- `display_name`
- `description`
- `category`
- `input_ports`
- `output_ports`
- `default_config`
- `config_schema`
- optional `ui_hints`

The generated UI should support:

- Text, number, boolean, select, multiselect, multiline, and code fields.
- Grouped fields as tabs only when there is more than one meaningful group.
- Generated branch labels from multi-output ports.
- Pass-through hints from generic `ui_hints`.
- Long-value-safe rendering for multiline fields.

### B. Command Navigation Contract

All keyboard-first modals should follow the same rules:

- `W`/`S` and arrows move focus/highlight in command mode.
- `E`/Enter activates the focused control.
- Text fields require activation before typing.
- `Esc` exits active typing mode before closing a modal.
- Select dropdowns open at the first real option every time.
- Selection lists toggle the highlighted item.
- Focus changes scroll the target into view.

Shared helpers should live in `frontend/widgets/`, not in individual screens.

### C. Dynamic Section Contract

Optional or count-driven sections must:

- Mount/remove visible rows immediately when toggles/counts change.
- Preserve typed values while row count changes.
- Use stable ids and classes.
- Exclude hidden rows from keyboard navigation.
- Remain reachable in a `VerticalScroll`.

### D. Alert Contract

The project currently uses direct `app.notify(...)` calls. Future work should
route common notifications through a frontend helper with standard names,
severity, duration, and copy.

---

## 4. Audit Phases

### Phase FA-0 — Inventory and Risk Map

**Files:** all `frontend/screens/*.py`, `frontend/widgets/*.py`,
`frontend/styles.tcss`, mounted Textual tests.

Tasks:

- Inventory each screen's bindings, command-mode behavior, focus model, scroll
  behavior, and direct notifications.
- Classify each screen:
  - `standard command modal`
  - `list selector`
  - `read-only viewer`
  - `main workflow screen`
  - `custom topology editor`
- Produce a table of gaps:
  - duplicate key handling
  - direct `app.notify`
  - missing `check_action`
  - missing scroll-to-focus
  - hidden widget risk
  - custom config logic that could be schema/helper driven

Done when:

- This document has an audited screen matrix.
- The next phases are ordered by bug risk, not by guesswork.

### Phase FA-1 — Shared Command Modal Foundation

**Files:** `frontend/widgets/command_navigation.py`, command-oriented screens.

Tasks:

- Expand `command_navigation.py` from helper functions into a small reusable
  focus/navigation toolkit.
- Migrate `SettingsScreen`, `PathPromptScreen`, `UserInputScreen`, and other
  simple command modals to the helper.
- Keep `NodeConfigScreen` as the reference implementation.
- Add focused tests for:
  - text field activate/edit/escape
  - select open/move/commit/reset
  - selection list highlight/toggle
  - focus scroll into view

Done when:

- Simple modals no longer duplicate command input activation or edit blocking.

### Phase FA-2 — Selector Standardization

**Files:** `node_selector.py`, `branch_selector.py`, `workflow_library.py`,
`node_list.py`.

Tasks:

- Standardize list selector behavior:
  - top item highlighted on open/filter
  - `W` from top returns to filter when applicable
  - `S` from filter enters list
  - arrows and `W/S` always move visible highlight
  - `E`/Enter selects highlighted item
- Add a shared selector helper if more than one screen needs the same behavior.
- Add tests for node selector, branch selector, and workflow library selector
  navigation.

Done when:

- List selector behavior is predictable across all modal lists.

### Phase FA-3 — Schema Generator Expansion

**Files:** `frontend/widgets/form_generator.py`,
`backend/field_types.py` only if a new generic schema key requires validation.

Tasks:

- Audit current node schemas and generated widgets.
- Add generic schema keys only where they help many nodes:
  - `placeholder`
  - `min`, `max`, `step`
  - `allow_blank`
  - `height`
  - `visible_if`
- Add tests for every supported key.
- Document a node-author checklist.

Done when:

- New ordinary nodes can add richer fields without touching screen code.

### Phase FA-4 — Dynamic Config Sections

**Files:** `node_config.py`, `form_generator.py`, possible new config helpers.

Tasks:

- Extract dynamic section patterns:
  - memory-bank outputs
  - memory-bank inputs
  - previous-output preview
  - wait targets
  - merge branch selection
- Keep topology-derived sections as adapters, but make mount/preserve/scroll
  behavior shared.
- Add tests for dynamic row value preservation and hidden-widget nav exclusion.

Done when:

- Adding a checkbox/count-driven section does not require rebuilding the modal
  navigation model.

### Phase FA-5 — Notification Helper

**Files:** new frontend alert helper, `app.py`, screens using `app.notify`.

Tasks:

- Create named notification helpers for common outcomes:
  - saved/loaded/imported/exported
  - validation passed/failed
  - no selection
  - destructive action canceled/completed
  - run started/stopped
  - missing dependency
- Standardize severity and copy.
- Optionally de-duplicate repeated keyboard errors.

Done when:

- Screens call the alert helper for common messages instead of ad hoc strings.

### Phase FA-6 — Viewer and Output Surfaces

**Files:** `execution.py`, `memory_viewer.py`, `output_viewer.py`,
`error_details.py`.

Tasks:

- Audit read-only surfaces for long content, scrollback, selection/filtering,
  and keyboard close behavior.
- Prefer `RichLog`, `DataTable`, or bounded scrollable widgets over plain
  unbounded `Static` where users inspect long data.
- Add tests or smoke scripts for nonblank rendering and long-content safety.

Done when:

- Long outputs, memory values, and errors remain inspectable without layout
  breakage.

### Phase FA-7 — Visual Identity and Help Alignment

**Files:** `styles.tcss`, `node_card.py`, `help.py`, `status_bar.py`.

Tasks:

- Align help text with the current keyboard model.
- Add visible `[NAV]` / `[EDIT]` or equivalent mode indicator when command-mode
  state becomes global.
- Standardize node category colors/glyphs.
- Confirm branch/end/merge/tombstone states are visually distinct.

Done when:

- The UI communicates current mode and node state without relying on memory.

---

## 5. Audit Screen Matrix

Fill this table during Phase FA-0.

| Screen / Widget | Type | Current Helpers | Known Risks | Next Action |
|---|---|---|---|---|
| `app.py` | root app | App-level `check_action` | direct `notify`, many workflow callbacks | Alert helper audit |
| `editor.py` | main screen | `NodeList`, priority bindings | branch path visibility, tombstone/merge visual states | Cursor model audit |
| `execution.py` | main screen | `RichLog`, `NodeList` | long output, run stop semantics | Viewer audit |
| `node_config.py` | command modal/topology adapters | `CommandInput`, `CommandTextArea`, `command_navigation`, `form_generator` | largest surface, dynamic sections | Reference implementation |
| `node_selector.py` | list selector | `CommandInput` | duplicated selector nav | Migrate to selector helper |
| `branch_selector.py` | list selector | `ListView` | different key grammar from node selector | Migrate to selector helper |
| `workflow_library.py` | list selector + path prompts | `CommandInput` | direct nav/copy, path prompt duplicate logic | Selector + command helper |
| `settings.py` | command modal | `CommandInput` | duplicate command nav | Migrate to command helper |
| `user_input.py` | command modal | `CommandInput` | duplicate edit blocking | Migrate to command helper |
| `memory_viewer.py` | read-only viewer | `Static` | long values, scrollability | Viewer audit |
| `output_viewer.py` | read-only/filter viewer | `Select`, `Static` | blank select defaults, long output | Viewer audit |
| `error_details.py` | read-only/action viewer | `Static`, `Button` | structured error actions | Viewer audit |
| `form_generator.py` | schema renderer | command widgets | schema key coverage | Schema expansion |
| `command_navigation.py` | command helper | select/list/text activation | private Textual overlay access | Centralize tests |

---

## 6. Verification Baseline

Run from `attackofthenodes_v05/`:

```bash
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```

Frontend audit phases should add focused tests before relying on manual smoke.
For UI behavior that cannot be asserted cleanly, record the manual smoke steps
in `docs/SESSION_LOG.md`.

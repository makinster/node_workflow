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

**Status:** in progress. Initial migration completed for `SettingsScreen`,
`UserInputScreen`, and `PathPromptScreen` on 2026-06-02.

Tasks:

- Expand `command_navigation.py` from helper functions into a small reusable
  focus/navigation toolkit. Initial helpers now cover command focus discovery,
  focus movement, activation, select movement, and edit-mode action blocking.
- Migrate `SettingsScreen`, `PathPromptScreen`, `UserInputScreen`, and other
  simple command modals to the helper. The first three are migrated; remaining
  candidates are selector/path variants and any future command modal.
- Keep `NodeConfigScreen` as the reference implementation.
- Add focused tests for:
  - text field activate/edit/escape
  - select open/move/commit/reset
  - selection list highlight/toggle
  - focus scroll into view

Done when:

- Simple modals no longer duplicate command input activation or edit blocking.
  Current remaining duplication is mostly selector-specific and belongs to
  FA-2.

### Phase FA-2 — Selector Standardization

**Files:** `node_selector.py`, `branch_selector.py`, `workflow_library.py`,
`node_list.py`.

**Status:** initial migration completed 2026-06-02 for modal list selectors.
`frontend/widgets/list_navigation.py` now centralizes ListView highlight
clamping, focusing, scrolling, and movement. `NodeSelectorScreen`,
`BranchSelectorScreen`, and `WorkflowLibraryScreen` use it.

Tasks:

- Standardize list selector behavior:
  - top item highlighted on open/filter
  - `W` from top returns to filter when applicable
  - `S` from filter enters list
  - arrows and `W/S` always move visible highlight
  - `E`/Enter selects highlighted item
- Add a shared selector helper if more than one screen needs the same behavior.
  Done for modal selectors.
- Add tests for node selector, branch selector, and workflow library selector
  navigation. Done.

Done when:

- List selector behavior is predictable across all modal lists.

### Phase FA-3 — Schema Generator Expansion

**Files:** `frontend/widgets/form_generator.py`,
`backend/field_types.py` only if a new generic schema key requires validation.

**Status:** in progress. Initial generator expansion completed 2026-06-02:
placeholders, numeric `min`/`max` validators, multiline/code `height`,
code-language hints, and multiselect default selections are supported without
screen-specific code.

Tasks:

- Audit current node schemas and generated widgets.
- Add generic schema keys only where they help many nodes:
  - `placeholder`
  - `min`, `max`
  - `allow_blank`
  - `height`
  - `visible_if`
- Add tests for every supported key.
- Document a node-author checklist.

Done when:

- New ordinary nodes can add richer fields without touching screen code.

Current supported schema keys:

| Key | Applies To | Effect |
|---|---|---|
| `type` | all fields | Chooses Textual widget: text/number/checkbox/select/selection list/text area |
| `label` | all fields | Visible field label |
| `description` | all fields | Small explanatory text below the label |
| `required` | all fields | Adds `*` to the label; backend validation remains node/schema responsibility |
| `default` | all fields | Used when current config lacks a value |
| `group` | all fields | Groups fields; multiple groups render as tabs |
| `options` | select/multiselect | Populates dropdown or selection list |
| `placeholder` | string/integer/float/number/multiline/code | Placeholder text before editing |
| `min`, `max` | integer/float/number | Textual validators on generated numeric inputs |
| `min_length`, `max_length` | string | Textual length validators on generated text inputs |
| `height` | multiline/code | Stable text-area height for long-value-safe rendering |
| `language` | code | TextArea language hint |

Node-author checklist:

- Define ordinary config fields in `config_schema`; avoid frontend screen edits
  unless the UI depends on workflow topology.
- Prefer generic `type`, `label`, `description`, `required`, `default`,
  `options`, and `group` before inventing a new key.
- Use `placeholder`, `min`, `max`, `min_length`, `max_length`, and `height`
  when the field needs stronger visual or validation hints.
- Use `ui_hints` for behavior copy such as pass-through notes that is not an
  editable config value.
- Keep topology-derived config, such as merge branch selection, in
  `NodeConfigScreen` adapters until FA-4 extracts a dynamic-section helper.

### Phase FA-4 — Dynamic Config Sections

**Files:** `node_config.py`, `form_generator.py`, possible new config helpers.

**Status:** in progress. Initial helper extraction completed 2026-06-02:
`frontend/widgets/dynamic_sections.py` now owns count clamping and visible-row
value preservation for checkbox/count-driven sections. Memory-bank output rows
use the helper. Dynamic selection lists now share stale-selection filtering,
default selection behavior, and selected-value normalization.

Tasks:

- Extract dynamic section patterns:
  - memory-bank outputs. Initial extraction done.
  - memory-bank inputs. Selection-row helper applied.
  - previous-output preview
  - wait targets. Selection-row helper applied.
  - merge branch selection. Selection-row helper applied for branch closures.
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

**FA-0 audit status:** initial source audit completed 2026-06-02 from direct
inspection of `frontend/screens/`, `frontend/widgets/`, `frontend/app.py`, and
mounted tests in `tests/test_debug_nodes.py`.

| Screen / Widget | Type | Current Helpers | Known Risks | Next Action |
|---|---|---|---|---|
| `app.py` | root app | App-level `check_action` blocks text-edit `"back"` | 20+ direct `notify` calls; workflow callbacks mix persistence, confirmation, and copy | FA-5 alert helper; later split action adapters |
| `editor.py` | main workflow screen | `NodeList`; priority bindings for editor actions; derived branch labels | many direct `notify` calls; cursor/nav model remains local; branch path display only shows one branch at a time | Phase 13 cursor audit, FA-5 alert helper |
| `execution.py` | main workflow screen/viewer | `RichLog`; `NodeList`; modal launch actions | direct `notify`; long output mostly safe via `RichLog`, but branch/memory summary still `Static` | FA-6 viewer audit |
| `node_config.py` | command modal + topology adapters | `CommandInput`, `CommandTextArea`, `command_navigation`, `form_generator`, `VerticalScroll` with `can_focus=False` | largest mixed surface; dynamic sections and merge topology logic still local; reference behavior not yet reusable enough | FA-1 reference extraction, FA-4 dynamic sections |
| `node_selector.py` | list selector with filter | `CommandInput`; `list_navigation` highlight/focus/move helper | filter/list grammar is now shared enough for modal selectors; local filter escape behavior remains intentional | Watch with FA-2 regressions |
| `branch_selector.py` | list selector | `ListView`; `list_navigation`; priority `W/S/E` bindings | active branch remains the initial highlight by design, rather than always top row | Watch with FA-2 regressions |
| `workflow_library.py` | list selector + path prompt | `ListView`; `list_navigation`; `CommandInput` in `PathPromptScreen`; path prompt uses `command_navigation` activation/blocking | selector keyboard movement is standardized; action/copy notifications remain ad hoc | FA-5 alert helper |
| `settings.py` | command modal | `CommandInput`; `command_navigation` activation/blocking/focus movement | migrated; still lacks global mode indicator | Watch during FA-7 |
| `user_input.py` | command modal | `CommandInput`; `command_navigation` activation/blocking | migrated; cancel semantics are sensitive because it can stop runs | Watch with focused regressions |
| `confirm.py` | confirmation modal | simple `Y/N/Esc` bindings | likely okay; should become standard destructive-action confirm component | FA-5 copy/severity audit |
| `memory_viewer.py` | read-only viewer | `DataTable` | stronger than initial plan assumed; still needs long-value smoke and keyboard close consistency | FA-6 viewer audit |
| `output_viewer.py` | read-only/filter viewer | `Select`; `Static` | uses raw `Select` outside `form_generator`; long output is plain `Static`; branch filter may inherit blank-select/default issues | FA-6 viewer audit, possibly command select helper |
| `error_details.py` | read-only/action viewer | `Static`; `Button` | structured validation cards are still plain text/static; jump/action affordances need consistency | FA-6 viewer/action audit |
| `help.py` | read-only modal | `Static` | help can drift from actual key grammar; should be generated/checked against command contract eventually | FA-7 help alignment |
| `form_generator.py` | schema renderer | `CommandInput`, `CommandTextArea`, `Select`, `SelectionList`, tabs | schema key coverage is thin; multiselect selected defaults need audit; optional blank/select behavior not schema-driven yet | FA-3 schema expansion |
| `command_navigation.py` | command helper | select/list/text/button activation | intentionally centralizes private Textual overlay access; not yet used by simple modals/selectors | FA-1 migration and tests |
| `command_input.py` | command text widgets | command-before-edit input/textarea | repeated `_run_screen_action` logic; App-level blocking still required for priority bindings | FA-1 helper consolidation |

## 6. FA-0 Prioritized Findings

1. **Command modal duplication was the first cleanup.**
   `SettingsScreen`, `UserInputScreen`, and `PathPromptScreen` now use shared
   `command_navigation` helpers for activation/blocking, and Settings uses
   shared command focus movement.
2. **Selector behavior now has a shared helper.** `NodeSelectorScreen`,
   `BranchSelectorScreen`, and `WorkflowLibraryScreen` use
   `list_navigation.py` for highlight clamping, focus, scrolling, and movement.
   Keep future modal selectors on this helper.
3. **Notifications need a wrapper.** Direct `notify` calls are concentrated in
   `app.py`, `editor.py`, and `execution.py`; this is a bounded FA-5 pass.
4. **Viewer surfaces are mixed but not all bad.** `memory_viewer.py` already uses
   `DataTable`, `execution.py` uses `RichLog`, but `output_viewer.py` and
   `error_details.py` still rely heavily on `Static`.
5. **Node UI standardization is mostly in place but needs schema expansion.**
   `form_generator.py` is the right path for ordinary nodes; upcoming work
   should add generic schema keys and tests rather than special screens.

---

## 7. Verification Baseline

Run from `attackofthenodes_v05/`:

```bash
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```

Frontend audit phases should add focused tests before relying on manual smoke.
For UI behavior that cannot be asserted cleanly, record the manual smoke steps
in `docs/SESSION_LOG.md`.

Latest known verification after FA-2 modal selector migration:

- `python -m compileall -q .`
- `python -m pytest tests/test_debug_nodes.py -v`
- Result: 42 passed.

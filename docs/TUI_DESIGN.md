# AttackOfTheNodes Terminal UI Design

## Pivot

AttackOfTheNodes is moving from the planned tkinter desktop UI to a Textual TUI.
The backend stays UI-agnostic and should remain untouched unless a genuine engine
bug is found. The frontend should adapt to the backend through thin adapters, not
by adding backend shortcuts for UI convenience.

## Framework

Use Textual: <https://textual.textualize.io>

Install development dependencies with:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Textual is async-native, which matches the supervisor run loop, master state
coordination, and future async node operations better than tkinter's pump model.

## Layout

The main app is a single Textual `App` with screens. The default screen is the
editor. Execution view will replace it automatically while a workflow is running.

Editor view:

```text
┌─ AttackOfTheNodes ──────────────────────────────────[IDLE]─────┐
│ Workflow: my_workflow *                  [^S Save] [^R Run]    │
├─ Nodes ──────────────────────────┬─ Details ────────────────────┤
│ ▶ [Start] Greet                  │ Selected: Greet              │
│ ├─[Counter] Count                │ Type: start_node             │
│ ├─[Logger] Trace                 │ Configuration:               │
│ ├─[Branch] Decide                │  Greeting *                  │
│ │ Branch Select: path_a          │   [Hello, world!          ▌] │
│ │ └─[Logger] PathA               │ Connections:                 │
│ └─[End] Done                     │  default → Count            │
├──────────────────────────────────┴──────────────────────────────┤
│ TAB: switch panel  SPACE: toggle  ENTER: edit  ?: help          │
└─────────────────────────────────────────────────────────────────┘
```

Execution view:

```text
┌─ AttackOfTheNodes ──────────────────────────[▶ RUNNING / 0:23]─┐
│ Workflow: my_workflow                    [⏸ Pause] [⏹ Stop]    │
├─ Execution ──────────────────────────┬─ Memory / Output ────────┤
│ ✓ [Start] Greet                       │ Memory:                  │
│ ✓ [Counter] Count          (n=3)      │  n: 3                    │
│ ▶ [Logger] Trace          ●●●         │ Recent Output:           │
│ ◌ [Branch] Decide                     │ [10:23:45] [TRACE] ...   │
│ ◌ [Logger] PathA                      │ [10:23:46] [COUNT] 3     │
│ ◌ [Logger] PathB                      │                          │
│ ◌ [End] Done                          │                          │
├───────────────────────────────────────┴──────────────────────────┤
│ ⏸ Pause  ⏹ Stop  M: Memory  O: Output  E: Errors  Q: Quit       │
└──────────────────────────────────────────────────────────────────┘
```

Node status icons:

- `◌` not visited
- `▶` executing
- `✓` completed
- `✗` errored
- `⏸` waiting for input

## Field Type Mapping

The schema-driven form generator should map backend field descriptors to Textual
widgets:

```text
FieldType.STRING       -> Input
STRING with options    -> Select
FieldType.MULTILINE    -> TextArea
FieldType.INTEGER      -> Input(type="integer")
FieldType.FLOAT        -> Input(type="number")
FieldType.BOOLEAN      -> Switch or Checkbox
FieldType.SELECT       -> Select
FieldType.MULTISELECT  -> SelectionList
FieldType.FILE_PATH    -> Input with file picker overlay
FieldType.CODE         -> TextArea
```

The form generator is the highest-leverage frontend component. It should take a
config schema and current values, return a widget container, and expose a getter
for updated values.

## Modal Screens

Use Textual `Screen` / `ModalScreen` classes:

- `node_selector.py`: add-node modal grouped by category, searchable.
- `node_config.py`: schema-generated edit form plus connections.
- `branch_selector.py`: modal opened from the editor's `Branch Select` row.
  Multi-output nodes render a selectable row immediately below the node. The row
  shows the currently visible output port; pressing Enter opens the branch
  selector. Switching branches hides the previously visible branch path and shows
  the selected branch path, keeping branch editing separated without deleting
  branch nodes.
- `user_input.py`: prompt shown when a supervisor waits for input.
- `memory_viewer.py`: memory bank variables and transient port data.
- `output_viewer.py`: scrollable output log.
- `error_details.py`: structured error details and recovery options.
- `workflow_library.py`: load, duplicate, export, and delete workflows.
- `settings.py`: configuration form.
- `help.py`: key binding reference.

## Key Bindings

Global bindings:

```text
ctrl+s        Save current workflow
ctrl+r        Run workflow
ctrl+shift+r  Stop running workflow
ctrl+n        New workflow
ctrl+o        Open workflow library
editor l/o    Open workflow library
ctrl+e        Open settings
?             Open help
q             Quit, prompting to save if dirty
escape        Close topmost modal or cancel action
q             Close topmost modal where supported
tab           Move focus forward
shift+tab     Move focus backward
```

Execution bindings:

```text
p  Pause/resume
s  Stop
m  Memory
o  Output
e  Errors
escape  Stop the active run and return to the editor
```

Every screen should keep a context-sensitive status bar visible at the bottom.

## File Structure

```text
frontend/
├── __init__.py
├── app.py
├── styles.tcss
├── screens/
│   ├── __init__.py
│   ├── editor.py
│   ├── execution.py
│   ├── node_selector.py
│   ├── node_config.py
│   ├── user_input.py
│   ├── memory_viewer.py
│   ├── output_viewer.py
│   ├── error_details.py
│   ├── workflow_library.py
│   ├── settings.py
│   └── help.py
├── widgets/
│   ├── __init__.py
│   ├── node_list.py
│   ├── node_card.py
│   ├── form_generator.py
│   └── status_bar.py
└── ui_state.py
```

## Milestones

1. Load or create a workflow, render nodes in a selectable list, and show details
   for the selected node. Done.
2. Add node selector and node config editing, using the schema form generator.
   Done.
3. Add execution view with live supervisor status updates and user input modal.
   Done.
4. Add memory, output, errors, workflow library, settings, and help modals.
   Done for the current TUI proof-of-concept: memory, output, error recovery,
   workflow library, settings, and help screens are wired.

## Progress Notes

- The spinoff branch keeps backend files untouched; all UI translation lives in
  `frontend/`.
- The app now mounts a Textual editor, adds nodes through `NodeSelectorScreen`,
  edits aliases/config through `NodeConfigScreen`, saves via `SaveManager`, and
  starts runs through the existing `MasterState`.
- The execution screen listens to existing backend events and renders node
  statuses, branch summaries, memory summaries, and recent outputs.
- User input and recovery events now open modal screens and submit back through
  `MasterState.submit_user_input` and `MasterState.submit_recovery_action`.
- Branch editing now has an editor navigation path: open a multi-output node,
  arrow down to the `Branch Select` row, press Enter, and choose the output port.
  Pressing `A` while the selector row is active adds a node to that branch.
- Adding a node now keeps editor focus on the node list and selects the newly
  added node. When adding into an existing visible path, the new node is inserted
  between the selected source and its previous downstream target.
- Leaving the execution screen stops active running, paused, or waiting runs
  before returning to the editor, so the next `Ctrl+R` starts a fresh run.
- The node configuration modal has top Save/Cancel buttons plus direct keyboard
  exits: `E` saves, `Esc` or `Q` closes, and `W/S` or `A/D` move focus.
- Workflow library is wired to load, create, duplicate, and delete workflows
  through existing persistence and `SaveManager` services. It is available from
  the editor with `L`, `O`, or global `Ctrl+O`.
- Settings are editable from the TUI and persisted through `ConfigurationManager`.
- Help is available in-app with the current keyboard model.
- The add-node modal preselects the first visible node type so keyboard focus has
  an immediate highlighted target when moving into the list.
- End-node output is read live from `MemoryBank.output_log` as well as finalized
  run outputs, so terminal output updates when the run finishes even if the
  workflow ends with an `EndNode`.
- Output display normalizes records, sorts by timestamp when present, and the
  output modal can filter by branch when branch metadata is available. Older
  string-only output entries appear under `unassigned`.
- User-input modal cancel now stops the active run, giving waiting workflows a
  clear escape hatch.
- Destructive workflow actions now confirm before proceeding: dirty new-workflow
  replacement, dirty workflow load, and workflow deletion.
- The execution screen recent-output panel now uses `RichLog` with markup
  disabled, so output has scrollback and bracketed node labels render literally.
- The node config modal now exposes connection editing: existing input/output
  edges can be removed, and new input/output edges can be added through endpoint
  selectors backed by `WorkflowMap.connect()` / `disconnect()`.
- Workflow library now supports JSON export and import through path prompt
  modals wired to `SaveManager.export_workflow()` and `import_workflow()`.
- Editor now exposes `I` as an explicit insert shortcut, using the same
  downstream-preserving insertion behavior as the smart add path.
- Editor validation is available with `V`; validation errors and warnings render
  as structured cards with node id, issue type, description, and jump-to-node
  actions.

## Remaining Work

- Add richer file-picker ergonomics for import/export paths if the terminal UI
  grows beyond direct path entry.

## Keyboard Navigation Rules

These rules come from tested failures in `NodeConfigScreen` and apply to any
scrollable modal with mixed interactive and non-interactive content.

- **Section headers need a dedicated CSS class.** Per-field labels from
  `form_generator.build_form` use `form-label`. Section-header labels must use
  a separate class (`nav-section`) so `_keyboard_focus_widgets` can distinguish
  them reliably without relying on parent hierarchy.

- **Non-interactive nav stops must show a visible highlight.** When keyboard
  navigation lands on a label or static text, apply `.nav-highlight` (blue
  background) so the user sees that their key press registered. Track the
  highlighted widget in an `_nav_widget` instance variable; use it as the
  current position reference instead of `self.app.focused`.

- **`Vertical` inside `VerticalScroll` needs `height: auto`.** Textual's
  `Vertical` defaults to `height: 1fr`, which collapses to zero height when
  placed inside a `VerticalScroll` (fractional units require a parent with a
  fixed height). Apply `.generated-form { height: auto; }` to any dynamically
  generated form container; without it, fields are in the DOM but invisible.

- **Use `scroll_to_widget` on the scroll container, not `scroll_visible` on
  the target.** `widget.scroll_visible()` walks the parent chain to find a
  ScrollView and fails when the widget is nested inside a non-scrollable
  `Vertical` inside a `VerticalScroll`. Call
  `self.query_one("#scroll-id").scroll_to_widget(target, animate=False)`
  directly.

- **Filter `display=False` ancestors from nav lists.** Widgets inside a
  container with `display=False` still appear in `query("*")` results. Use an
  `_ancestor_visible(widget)` helper that walks the parent chain and returns
  `False` if any ancestor has `display=False`.

- **`TabbedContent` adds nav-stop buttons.** Any `TabbedContent` creates `Tab`
  or `Button`-subclass tab-bar widgets. If those appear in `_keyboard_focus_widgets`
  they become phantom stops. Either exclude `TabbedContent` entirely for simple
  configs, or explicitly filter tab-bar widgets from the nav list.

- **`check_action` at the Screen level does not stop App-level bindings.**
  Returning `False` from `Screen.check_action` prevents that screen's action,
  but App-level `Binding(priority=True)` bindings still fire. Block modal-exit
  during text editing by adding `App.check_action` that returns `False` for
  `"back"` when a `CommandInput`/`CommandTextArea` is in edit mode.

- **`VerticalScroll` should not be focusable.** Set `can_focus = False` on
  scroll containers that act as viewports. If focusable, clicking text inside
  them transfers focus to the container, silently breaking W/S navigation.

## Learned Detours

- `SelectOverlay` owns focus while a `Select` dropdown is expanded and runs its
  own `_on_key` for type-to-search. Priority screen bindings and `check_action`
  do not reach it from outside. The only reliable fix is monkey-patching
  `SelectOverlay._on_key` at module import time (see
  `command_navigation._install_select_overlay_command_bindings`). Guard with a
  sentinel flag to prevent double-patching across test sessions.

- To commit a `Select` value from outside the overlay (e.g. from a screen action
  or helper): read `select_overlay(s).highlighted`, look up
  `s._options[index][1]`, assign to `s.value`, call `s.focus()`, then set
  `s.expanded = False`. Calling `action_select()` on the overlay from outside
  its own key handler does not reliably close the overlay.

- Ubuntu's externally managed Python blocks global `pip install`; use a local
  `.venv` and install requirements inside it.
- Textual `push_screen()` can race with immediate backend events if execution
  starts before the screen is mounted. The app now delays run start briefly and
  ignores refreshes on screens that are not mounted yet.
- The first `Log` widget attempt caused headless refresh hangs during tests.
  The execution screen now uses `RichLog` with markup disabled, which provides
  scrollback without treating node labels as markup.
- Textual modal exit should be redundant: `Esc` and `Q` are both bound on the
  new modals because fast keyboard escape matters in a TUI.
- Backend schemas use `type: string` with `options` in several nodes, so the
  form generator treats any non-boolean option list as a `Select`, even when the
  field type is not explicitly `select`.
- Switching screens while backend stop/completion events are still firing can
  briefly leave Textual without a current screen. The event refresh path now
  ignores that transition window instead of surfacing a stack error.
- To keep newly added nodes visible, inserting into an already-connected path
  needs a frontend adapter step: disconnect the old edge, connect source to the
  new node, then connect the new node to the old target. No backend shortcut was
  needed.
- Rich markup treats bracketed text like `[END]` as markup unless explicitly
  escaped. Output panels now render through `rich.text.Text` so workflow output
  appears literally.

## Design Guardrail

New node types should require zero UI code when they follow the standardization
contract: declare category and schema, implement execution, and register in the
node class list. The TUI should discover metadata and render forms dynamically.

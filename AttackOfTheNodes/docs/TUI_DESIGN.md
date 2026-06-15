# AttackOfTheNodes Terminal UI Design

## Pivot

AttackOfTheNodes uses a Textual TUI as the active frontend. The old tkinter
frontend is obsolete. The backend stays UI-agnostic and should remain reusable
by future frontends. The Textual app adapts to backend services through
frontend-owned screens, widgets, and adapters.

Before adding backend behavior for UI convenience, read
`docs/BACKEND_FRONTEND_BOUNDARY.md`.

## Framework

Use Textual: <https://textual.textualize.io>

Install development dependencies with:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r AttackOfTheNodes/requirements.lock
python -m pip install -e AttackOfTheNodes/
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

- `node_selector.py`: add-node modal grouped by Phase 17 family tabs:
  `Inputs`, `Flow Control`, `Outputs`, and `Complex`. It keeps a string match
  filter near the top, then shows tab-specific subcategory checkboxes
  such as `Triggered`, `File I/O`, `Internet`, `AI`, `Passive Output`,
  `Active Output`, `Parallel`, `Conditional`, `Runtime Resource`, and
  `Utility`. The initial keyboard highlight should land on the first
  subcategory control rather than the string filter. The string filter is
  activate-to-edit; `/` may jump to it, but selector open should not
  immediately put the user in typing mode. Subcategory filters use `AND`
  semantics, so selecting multiple filters shows nodes that match all selected
  tags. The filtered node list sits below the subcategory controls. Moving
  between tabs, filter controls, and list rows must autoscroll so the active
  control is fully visible.
- `node_config.py`: schema-generated edit form, memory-bank input/output
  declarations, and topology-derived selectors such as wait/merge controls.
  Port-edge mutation should stay in editor workflows, not generic config forms.
  Merge config lists current Merge Beacons from anywhere in the workflow,
  including nested branch trees, while excluding beacons on the merge node's own
  branch path. The list refreshes on config open and is tolerant of incomplete
  workflows; validation remains the authority for runnable correctness. Nested
  options show branch breadcrumbs (`Outer -> Inner`) so users can tell which
  branch path they are closing.
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
- `help.py`: context-specific key reference. Screens should pass enough context
  for Help to show only the relevant bindings and keep the main UI copy short.

## Key Bindings

Global bindings:

```text
ctrl+s        Save current workflow
ctrl+r        Run workflow
ctrl+n        New workflow
ctrl+o        Open workflow library
ctrl+e        Open settings
?             Open help
escape        Close topmost modal or cancel action
ctrl+q        Back / close; quits only from editor; blocked while text editing
ctrl+c        Copy mouse-selected screen text through Textual selection copy
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

Editor bindings:

```text
W/S or up/down         Move selection vertically
A/D or left/right     Cycle all branch views, grouped by branch node creation order
Ctrl+A/Ctrl+D         Cycle incomplete branch views only
Ctrl+left/Ctrl+right  Same as Ctrl+A/Ctrl+D
E or Enter            Edit selected node or open the highlighted branch selector
I                     Insert after the highlighted node
F                     File / workflow library
O                     Options
H                     Help
X or Backspace        Delete selected node or tombstone
B / Ctrl+B            Toggle selected breakpoint / clear all breakpoints
V                     Validate workflow
```

`A` is not an add-node shortcut. The editor treats WASD as left-hand arrows:
`W/S` move vertically and `A/D` move horizontally through branch views.
Plain `A/D` rolls through every branch path, showing all ports from one branch
node before moving to the next branch node in creation order. `Ctrl+A/D` uses
the same ordering but filters to incomplete branch paths. End nodes, output
nodes, merge nodes, and Merge Beacons connected to a Merge count as complete;
an unconnected Merge Beacon remains incomplete so it stays easy to find.
When cycling back to a branch, the editor restores the last highlighted node in
that branch when possible; otherwise it highlights the first visible node in
that branch path.

The editor bottom bar should stay very short:
`f file | o options | h help | ctrl+q quit`. Navigation details belong in Help,
not the main editor chrome. Do not duplicate these key hints in the right panel;
that panel should start with `Selected Node:`.
Help modals should have one navigable control at the bottom: a focused
`Cancel` button.

The editor node list shows a small depth counter at the left of each node row.
Start is `0`; each visible node below increments by one. When a branch is
selected, the branch path continues from the branch node's depth so switching
branches preserves vertical orientation.
Node rows should show the editable, user-facing alias only. Generated ids stay
out of the editor list and appear only in detail/config contexts where
disambiguation matters. Tombstones render as `Deleted: <original node name>`.
Phase 17 may expand node rows to two lines when space allows: the first line
emphasizes the user-facing alias, and the second line shows primary family plus
one or two high-signal subcategories. Editor node rows should render as
individual bordered text boxes, with family-specific border/color treatment
where useful and no literal bracket characters around the alias or identity
line. Long subcategory text may truncate with an ellipsis because the full list
is available in the right-side details panel.
Rows must not destabilize cursor movement, branch selector rows, validation
colors, breakpoint markers, execution state, or Merge Beacon health colors. The
right-side details panel should show the primary family and all subcategories
for the selected node.
The editor Quick View should summarize configured data flow without raw graph
noise. Show `Inputs` and `Outputs`. Under inputs, show `Transient Source:
<source node name>` and then `<output name>: <description>`, followed by Memory
entries in the same name/description format. Outputs use matching Transient and
Memory name/description lines. For pass-through utility nodes, trace display
back to the upstream node that actually created the transient data.
Node rows use a fixed-width depth gutter with extra padding before the node
name. Branch selector rows place the `☛` icon in the same gutter.
Branch output labels should default to `Branch 1`, `Branch 2`, and so on, while
remaining editable in the branch node config. Current Branch v1 is an
always-parallel spawner: users choose `2` to `5` spawn points, name each spawn
point, and choose which upstream dead-drop/Vault payload seeds each branch.
Downstream nodes should see the chosen branch seed as their previous dead-drop
payload. Config previews show the source chain as
`origin node -> (...) -> Branch`, then the payload name/type and a safe printable
preview when a prior run captured one.
Conditional branch fields are hidden until a later dedicated conditional-branch
pass.

The File menu should show workflow names without ids. Duplicate names are
displayed as `Name`, `Name (2)`, `Name (3)`, and the currently loaded workflow
is marked with `<-- Loaded Workflow`. Workflow actions are keyboard bindings;
the only bottom widget is `Cancel`. Moving down from the last workflow focuses
Cancel, and moving up from Cancel returns to the last workflow. Export/import
tries an OS file picker first, then falls back to a typed path prompt when the
picker is unavailable or errors. The fallback prompt includes a Browse control
when possible so users can retry the OS picker from inside the prompt. Canceling
either path returns to File.
Opening/revealing a folder in Explorer/Finder/xdg-open is a separate convenience
helper and must not be used as a substitute for choosing import/export paths.

Node config buttons are stacked vertically for W/S navigation. `Ctrl+S` saves
and closes. Config may expose dead-drop payload name/description overrides based
on node port metadata, stored in `transient_outputs`. Standard node configs use
fixed `Source`, `Parameters`, `Payloads`, and `Connections` tabs. W/S moves
vertically inside the active tab and then to Save/Cancel; it does not move into
the tab header and does not switch tabs. A/D and left/right switch tabs and move
focus to the first control in the new tab. When the first control in a tab is
focused, the scroll container should snap high enough that the tab header is
visible again; users should never lose the tab row behind a long Payloads
screen. While a command text field is actively editing, A/D and left/right
remain cursor-movement keys. Small text fields exit editing on Esc, Enter, or
Tab and keep the typed value for the modal-level Save. `Ctrl+Q` while editing is
the explicit revert-to-edit-start command. Large `CommandTextArea` fields keep
Tab inside the text area for content/indentation editing and use Esc or
Ctrl+Enter to leave edit mode while preserving text.

Payload previews are opt-in. Source and Payloads tabs may include `Reveal
upstream payload` and `Reveal Vault payload` checkboxes. Revealed previews use a
consistent shape: `Source: <node chain>`, then `Payload: <name> (<type>): <value>`
when a captured printable value exists, and `Description: <user/node
description>` only when a meaningful description exists. Revealed preview blocks
are read-only command stops: W/S or arrows should be able to highlight them,
scroll them into view, and then continue to the next widget. This keeps ordinary
nodes quiet while making complex workflows inspectable.

Settings includes a visible Cancel control and reserves `K` for an API Keys
submenu. The current API Keys screen is a placeholder only.

The editor persists selected node/branch state on the app shell. Returning from
execution, closing secondary menus, or showing transient notifications should
restore the last highlighted editor row and focus the node list. The node list
normalizes Textual row highlight state after refreshes so only one row renders
as selected.

## Command Navigation

Keyboard-first modals use command mode by default:

```text
W/S or arrows  Move highlight/focus
E or Enter     Activate highlighted control
Esc/Ctrl+Q     Leave edit mode, close dropdown, or cancel/close modal
Ctrl+S         Save where supported
Ctrl+Enter     Save/submit multiline forms where supported
```

Text fields use `CommandInput` or `CommandTextArea`.

- Long/config forms are command-first: focusing a text field does not type until
  the user presses `E` or Enter.
- Popup-style prompts and filters may opt into `auto_edit_on_focus=True`.
- While editing, arrows move within the text widget and `W/S` type normally.
- `Esc`, Enter, and Tab exit small text input editing while preserving typed
  text for the modal-level Save.
- `Ctrl+Q` while editing reverts that field to the value captured at edit start.
- Text areas use Esc or `Ctrl+Enter` to leave editing while preserving text;
  Tab remains text input for indentation/content editing.
- Selection-list widgets, including Vault and merge-branch lists, must not trap
  keyboard movement. W/S and up/down move through list options, then move to the
  previous/next command widget when the highlight is already at the top/bottom.
  Tab/Shift+Tab may also move focus, but they cannot be the only escape path.

Shared behavior belongs in `frontend/widgets/command_navigation.py`,
`command_input.py`, `list_navigation.py`, and `dynamic_sections.py`, not in
per-screen one-off key handlers.

Mouse behavior follows the same command-mode contract:

- In the editor node list, one click highlights/selects a node or branch row.
  Two clicks opens node config or the branch selector.
- In command text fields, one click enters editing mode. Keyboard navigation
  still remains command-first: moving to a field with W/S or arrows only
  highlights it until `E` or Enter is pressed.

## File Structure

```text
frontend/
├── __init__.py
├── app.py
├── styles.tcss
├── screens/
│   ├── __init__.py
│   ├── branch_selector.py
│   ├── confirm.py
│   ├── editor.py
│   ├── error_details.py
│   ├── execution.py
│   ├── help.py
│   ├── memory_viewer.py
│   ├── node_config.py
│   ├── node_selector.py
│   ├── output_viewer.py
│   ├── settings.py
│   ├── user_input.py
│   ├── workflow_library.py
│   └── ...
├── widgets/
│   ├── __init__.py
│   ├── command_input.py
│   ├── command_navigation.py
│   ├── dynamic_sections.py
│   ├── form_generator.py
│   ├── list_navigation.py
│   ├── node_card.py
│   ├── node_list.py
│   └── status_bar.py
├── notifications.py
├── output_records.py
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
- Branch editing now has an editor navigation path: highlight a multi-output
  node's selector row, press `E`/Enter, and choose the visible output port.
  Insert/add flows use the highlighted row as their placement context.
- Adding a node now keeps editor focus on the node list and selects the newly
  added node. When adding into an existing visible path, the new node is inserted
  between the selected source and its previous downstream target.
- Leaving the execution screen stops active running, paused, or waiting runs
  before returning to the editor, so the next `Ctrl+R` starts a fresh run.
- The node configuration modal is command-first. `W/S` or arrows move through
  actionable controls, `E` activates the highlighted control, `Esc`/`Ctrl+Q`
  exits active editing or cancels/closes, and text-heavy forms avoid plain
  `Q` as a close binding.
- Workflow library/File behavior is wired to load, create, duplicate, import,
  export, and delete workflows through existing persistence and `SaveManager`
  services. It is available from the editor with `F`; settings/options use `O`.
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
- Port-edge mutation belongs in editor flows. Generic node config focuses on
  core schema fields, memory-bank input/output declarations, pass-through
  behavior, and topology-derived selectors such as wait/merge controls.
- Workflow library now supports JSON export and import through OS picker first,
  then path prompt fallback, wired to `SaveManager.export_workflow()` and
  `import_workflow()`.
- Editor now exposes `I` as an explicit insert shortcut, using the same
  downstream-preserving insertion behavior as the smart add path.
- Editor validation is available with `V`; validation errors and warnings render
  as structured cards with node id, issue type, description, and jump-to-node
  actions.

## Remaining Work

- Extend the shared file picker helper to schema-generated `FILE_PATH` fields
  when nodes need user-selected filesystem paths.

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
- Textual modal exit should be redundant, but text-heavy forms must avoid plain
  `Q` as a close binding. Prefer `Esc` and `Ctrl+Q`, and make App-level
  `check_action` block close/back while command text widgets are editing.
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

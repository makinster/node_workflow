# Agent Start Guide

Use this as the practical first stop when changing AttackOfTheNodes. It is a
checklist for common work: adding nodes, making config render, keeping editor
display correct, and proving the change works. For deeper architecture, follow
the links in `docs/README.md`.

## Before You Change Code

- Run `git status --short`.
- Do not revert unrelated dirty or untracked files.
- Read `docs/BACKEND_FRONTEND_BOUNDARY.md` before backend changes for editor or
  UI behavior.
- Prefer existing helpers over new per-screen logic.
- Keep backend nodes graph-ignorant and frontend-free.

## Add A New Node

- Create `AttackOfTheNodes/backend/nodes/<category>/<name>_node.py`.
- Add the class to `AttackOfTheNodes/backend/nodes/__init__.py` and
  `ALL_NODE_CLASSES`.
- Required class metadata:
  - `node_type`
  - `display_name`
  - `description`
  - `category`
  - `input_ports`
  - `output_ports`
  - `default_config`
  - `config_schema`
- Optional class metadata:
  - `default_alias`
  - `input_port_metadata`
  - `output_port_metadata`
  - `ui_hints = {"pass_through": True}`
- Implement `async execute(self, context: NodeContext) -> None`.
- Use context APIs such as `context.inputs`, `context.memory_bank`,
  `context.signal_done`, `context.signal_error`, `context.signal_waiting_for_input`,
  `context.wait_for_nodes`, and `context.wait_for_merge`.
- Output transient port data with
  `await context.signal_done({"data": {"default": value}})` or the correct
  output port names.
- Do not import anything from `frontend/` in node files.

## Make Node Config Render Correctly

- Use `config_schema` for ordinary node fields. Do not edit
  `NodeConfigScreen` just to add a normal config field.
- Supported field types:
  - `string`
  - `integer`
  - `float`
  - `number`
  - `boolean`
  - `select`
  - `multiselect`
  - `multiline`
  - `code`
- Supported schema keys:
  - `label`
  - `description`
  - `required`
  - `options`
  - `group`
  - `placeholder`
  - numeric bounds such as `min` and `max`
  - text bounds such as `min_length` and `max_length`
  - multiline/code options such as `height` and `language`
- Generated widgets:
  - text and number fields render as `CommandInput`
  - multiline and code fields render as `CommandTextArea`
  - boolean fields render as checkbox controls
  - select fields render as `Select`
  - multiselect fields render as `SelectionList`
- Generated schema fields land in the Node Config `Parameters` tab. If a schema
  itself has multiple `group` values, those fields render as nested generated
  tabs inside `Parameters`; single-group configs stay flat.
- Standard Node Config tabs are `Source`, `Parameters`, `Payloads`, and
  `Connections`. Keep ordinary node fields schema-driven; custom config screens
  are reserved for topology-derived UI such as Branch, Merge, and Wait targets.
- Config-screen copy currently uses the project vocabulary: graph-passed data is
  a dead-drop payload, named memory is the Vault, and pass-through forwarding is
  labeled `Dead drop payload`.

## Branch Node V1

- `branch_node` is currently exposed as an always-parallel branch spawner.
- It supports fixed ports `path_a` through `path_e`, with `branch_count` clamped
  from `2` to `5`.
- The config UI hides legacy conditional fields. Keep legacy config keys readable
  for old saves, but do not add new conditional UI to `branch_node`; use a future
  dedicated conditional-branch node/pass instead.
- Branch config stores:
  - `<port>_label` for each spawn point name.
  - `branch_payload_sources` such as `dead_drop:input` or `vault:<key>`.
- When changing Branch behavior, update editor active-port traversal so only the
  first `branch_count` ports are shown in branch cycling and branch selector rows.

## Make Inputs And Outputs Display Correctly

- Use `input_ports` and `output_ports` for graph structure.
- Use `input_port_metadata` and `output_port_metadata` for default human names
  and descriptions.
- Use config `transient_outputs` when users override transient output names or
  descriptions in node config.
- Use `membank_inputs` for named memory-bank values a node reads.
- Use `membank_outputs` for named memory-bank values a node writes.
- For pass-through nodes, set `ui_hints.pass_through` so the editor can trace
  visible data provenance back to the node that actually created the data.

## When Frontend Edits Are Needed

- Ordinary nodes should not need frontend edits.
- Add frontend logic for structural UI that derives from workflow topology,
  such as merge branch selection or editor-only placeholders.
- Shared frontend helper locations:
  - `AttackOfTheNodes/frontend/widgets/form_generator.py`
  - `AttackOfTheNodes/frontend/widgets/command_navigation.py`
  - `AttackOfTheNodes/frontend/widgets/list_navigation.py`
  - `AttackOfTheNodes/frontend/widgets/dynamic_sections.py`
  - `AttackOfTheNodes/frontend/node_io_display.py`
  - `AttackOfTheNodes/frontend/notifications.py`

## File I/O UI Pattern

- Workflow import/export should try the OS file picker first and fall back to a
  typed path prompt when the picker is canceled, unavailable, or errors.
- Typed path fallback prompts should expose a `Browse` button/key when picker
  metadata is available, so users can retry the OS file picker without backing
  out to the File menu.
- Keep picker code frontend-only. Backend save/import/export services should
  accept paths and should not know how the user selected them.
- Use `AttackOfTheNodes/frontend/file_io.py` for:
  - `pick_open_file(...)`
  - `pick_save_file(...)`
  - `reveal_path(...)`
- Do not confuse file picking with file-manager reveal:
  - pickers return a selected path for import/export;
  - reveal/open-folder helpers only open Explorer/Finder/xdg-open and cannot
    choose a path for the app.
- Keep the typed path prompt as the reliable fallback for WSL, SSH, headless,
  container, or other no-GUI sessions.
- Future `FILE_PATH` schema fields should reuse the same helper rather than
  adding node-specific picker logic.

## Keyboard And Modal Rules

- Command-mode screens should inherit `CommandScreenMixin`.
- Text fields should use `CommandInput` or `CommandTextArea`.
- In nav mode, `W/S` and arrow keys move focus.
- `E` and Enter activate the focused control.
- `Esc` and `Ctrl+Q` exit edit mode before closing a modal.
- `Ctrl+S` saves where supported.
- List screens should use `frontend/widgets/list_navigation.py`.
- Popup filters and prompts that should accept typing immediately should opt
  into `auto_edit_on_focus=True`.

## Add Or Change A Screen

- Use existing modal patterns before creating a new one.
- Keep button order vertical when possible so `W/S` navigation is natural.
- Provide a visible `Cancel` control.
- Add context-aware help text through `HelpScreen` conventions.
- Avoid ad hoc `app.notify(...)`; use `frontend/notifications.py`.

## Tests To Add

- Node execution tests go in `AttackOfTheNodes/tests/test_debug_nodes.py`.
- Add a metadata or registration test when adding a node.
- Add a config rendering test when adding schema behavior.
- Add an editor Quick View test when changing port or memory display behavior.
- Add a command-navigation test when changing modal focus behavior.
- Run from `AttackOfTheNodes/`:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v`

## Docs To Update

- Update `docs/SESSION_LOG.md` for every completed change.
- Update `docs/MASTER_BUILD_PLAN.md` when roadmap, status, or conventions
  change.
- Update `docs/TUI_DESIGN.md` for frontend behavior changes.
- Update `docs/BACKEND_FRONTEND_BOUNDARY.md` if the backend/frontend boundary
  policy changes.

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

- Read `NODE_STANDARDS.md` first. It defines the standard input source model
  (Upstream / Vault / Configured), output routing model (Transient / Dead-drop /
  Vault write), dynamic form rules, data type scope, and includes reference
  examples for a File instance node and a Basic LLM node.
- Prefer the helper-first flow for ordinary nodes:
  - Write a spec in `aotn_node_helper/specs/<node_type>.yaml`.
  - Use `input_sources` and `output_routing` spec sections to expand the
    standard NODE_STANDARDS input/output model automatically, including the
    dynamic greying rules. See `NODE_HELPER.md` and
    `aotn_node_helper/specs/example_file_instance_node.yaml`.
  - Run `../.venv/bin/python ../aotn_node_helper/create_node.py ../aotn_node_helper/specs/<node_type>.yaml`
    from `AttackOfTheNodes/`, or run the same script from the workspace root.
  - Run `../.venv/bin/python ../aotn_node_helper/check_node.py <node_type>`
    for the focused compile/registration/execution check.
  - Run `../.venv/bin/python ../aotn_node_helper/check_ui.py <node_type>` to
    verify tab placement, focusability, and dynamic-form rule state on the
    mounted config screen.
- The intended human-to-helper workflow is:
  - Describe what the node does and anything unique about it.
  - Provide config tab headers such as `Source`, `Parameters`, and `Payloads`.
  - Under each tab header, list the fields as bullets.
  - Translate those bullets into `config_tabs` in the helper spec.
- Example `config_tabs` shape:

```yaml
config_tabs:
  Source:
    prompt_source:
      type: select
      label: Prompt source
      options: ["Upstream payload", "Vault value"]
      default: Upstream payload
  Parameters:
    temperature:
      type: float
      label: Temperature
      default: 0.7
      min: 0
      max: 2
  Payloads:
    payload_note:
      type: string
      label: Payload note
      default: ""
      required: false
```

- Helper specs create the node file, update registration, and generate a
  node-specific focused test under `AttackOfTheNodes/tests/generated/`.
- If the helper spec requests structural UI, the helper emits a TODO note
  instead of patching frontend screens. Treat that as a deliberate guardrail.
- Create `AttackOfTheNodes/backend/nodes/<category>/<name>_node.py`.
- Add the class to `AttackOfTheNodes/backend/nodes/__init__.py` and
  `ALL_NODE_CLASSES`.
- Required class metadata:
  - `node_type`
  - `display_name`
  - `description`
  - `category`
  - `primary_family` (Phase 17: `Inputs`, `Flow Control`, `Outputs`, or
    `Complex` — required for the selector family tabs)
  - `input_ports`
  - `output_ports`
  - `default_config`
  - `config_schema`
- Optional class metadata:
  - `default_alias`
  - `tags` (Phase 17 subcategory filters such as `File I/O`, `AI`, `Parallel`)
  - `icon_name` and `color_hint` (Phase 17 visual identity)
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
  - dynamic rule keys: `enabled_when` (grey out unless condition holds),
    `visible_when` (hide field, label, and description unless condition holds),
    and `mutually_exclusive_with` (checking one boolean unchecks its partners).
    Conditions are mappings of field name to expected value; rules work across
    tabs and are applied live by `NodeConfigScreen`.
- Generated widgets:
  - text and number fields render as `CommandInput`
  - multiline and code fields render as `CommandTextArea`
  - boolean fields render as checkbox controls
  - select fields render as `Select`
  - multiselect fields render as `SelectionList`
- Generated schema fields land in the Node Config `Parameters` tab by default.
  Add a schema `tab` key or use helper `config_tabs` to place ordinary fields in
  `Source`, `Parameters`, or `Payloads`.
- If a schema itself has multiple `group` values, those fields render as nested
  generated tabs inside their top-level tab; single-group configs stay flat.
- Standard Node Config tabs are `Source`, `Parameters`, `Payloads`, and
  `Connections`. Keep ordinary node fields schema-driven; custom config screens
  are reserved for topology-derived UI such as Branch, Merge, and Wait targets.
- Config-screen copy currently uses the project vocabulary: graph-passed data is
  a dead-drop payload, named memory is the Vault, and pass-through forwarding is
  labeled `Dead drop payload`.
- Standard-model nodes (input ports declaring `sources`) show an auto-revealed
  `Incoming Payload` block at the top of the Source tab — `Node source:` /
  `Payload: <name> (<type>)` / `Payload desc:` / `Value:` lines per connected
  input. It is a plain read-only Static that keyboard navigation skips.
  Legacy nodes keep the opt-in `Reveal upstream payload` / `Reveal Vault
  payload` checkboxes, whose revealed previews are read-only command stops.

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
- Downstream display treats the selected branch seed as that branch port's
  dead-drop payload. Config previews and editor Quick View should trace to the
  original source while keeping the Branch node in the source chain.
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
- Navigation is row-based 2D: in nav mode `W/S`/up-down move line-by-line
  between rows (a multi-widget row counts as one line), and `A/D`/left-right
  move within the current row. On single-widget rows (the common case) A/D is a
  no-op and falls through to caret movement on a focused text field.
- Tabbed command-mode screens switch tabs by **number key** (`1`–`5`, gated to
  nav mode) and label tab headers `N - Label`. A/D no longer switch tabs.
- `E` and Enter activate the focused control; on a `Switch`/`Checkbox` they
  toggle in a single press.
- `Esc` and `Ctrl+Q` exit edit mode before closing a modal.
- `Ctrl+S` saves where supported.
- List screens should use `frontend/widgets/list_navigation.py`.
- Inline `SelectionList` controls such as Vault or merge branch choices must not
  trap keyboard movement. W/S and up/down should move through options, then move
  to the previous/next command widget when already at the top/bottom.
- In tabbed config screens, focusing the first control in a tab should scroll
  high enough to show the tab header again. This keeps long Payloads tabs
  navigable after users scroll through many generated controls.
- Popup filters and prompts that should accept typing immediately should opt
  into `auto_edit_on_focus=True`.

## Add Or Change A Screen

- Use existing modal patterns before creating a new one.
- Keep button order vertical when possible so `W/S` navigation is natural.
- Provide a visible `Cancel` control.
- Add context-aware help text through `HelpScreen` conventions.
- Avoid ad hoc `app.notify(...)`; use `frontend/notifications.py`.

## Tests To Add

- For generated nodes, prefer focused tests under
  `AttackOfTheNodes/tests/generated/test_<node_type>.py` and run:
  - `../.venv/bin/python ../aotn_node_helper/check_node.py <node_type>`
- Node execution tests that cover shared engine behavior still go in
  `AttackOfTheNodes/tests/test_debug_nodes.py`.
- Add a metadata or registration test when adding a node.
- Add a config rendering test when adding schema behavior.
- Add an editor Quick View test when changing port or memory display behavior.
- Add a command-navigation test when changing modal focus behavior.
- For small bug fixes, run the narrow `pytest -k` slice that covers the changed
  behavior before reaching for the full cumulative suite.
- Run from `AttackOfTheNodes/` before shared/runtime commits:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v`

## Docs To Update

- Update `docs/SESSION_LOG.md` for every completed change.
- Update `docs/MASTER_BUILD_PLAN.md` when roadmap, status, or conventions
  change.
- Update `docs/TUI_DESIGN.md` for frontend behavior changes.
- Update `docs/BACKEND_FRONTEND_BOUNDARY.md` if the backend/frontend boundary
  policy changes.

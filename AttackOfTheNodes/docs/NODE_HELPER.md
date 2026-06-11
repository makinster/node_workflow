# aotn_node_helper Guide

`aotn_node_helper` is the helper-first path for adding ordinary
AttackOfTheNodes node types. Its job is to keep node creation boring:
describe the backend node contract once, generate the node source and focused
tests, then let the existing schema-driven config UI render ordinary fields.

The helper lives at the workspace root:

```bash
aotn_node_helper/
├── create_node.py
├── check_node.py
├── generator.py
└── specs/
```

Run helper commands from `AttackOfTheNodes/` with the workspace venv:

```bash
../.venv/bin/python ../aotn_node_helper/create_node.py ../aotn_node_helper/specs/<node_type>.yaml
../.venv/bin/python ../aotn_node_helper/check_node.py <node_type>
```

Or run them from the workspace root by passing the same script paths.

## What It Generates

From one JSON/YAML spec, `create_node.py` generates:

- `AttackOfTheNodes/backend/nodes/<category>/<node_type>.py`
- registration updates in `AttackOfTheNodes/backend/nodes/__init__.py`
- `AttackOfTheNodes/tests/generated/test_<node_type>.py`
- optional UI follow-up notes under `aotn_node_helper/generated_notes/` when
  the spec marks `structural_ui: true`

`check_node.py <node_type>` runs a focused compile plus the generated test for
that node.

## Spec Shape

Use `config_tabs` for the authoring workflow. It mirrors the config UI and
places ordinary fields into the fixed Node Config tabs without frontend edits.

```yaml
node_type: example_formatter_node
class_name: ExampleFormatterNode
category: data
display_name: Example Formatter
default_alias: Format Text
description: Formats an incoming payload for display
input_ports: ["input"]
output_ports: ["default"]
output_port_metadata:
  default:
    name: Formatted Text
    description: Text after formatting
config_tabs:
  Source:
    source_note:
      type: string
      label: Source note
      default: ""
      required: false
  Parameters:
    style:
      type: select
      label: Style
      options: ["Plain", "Title Case", "Uppercase"]
      default: Plain
  Payloads:
    payload_note:
      type: string
      label: Payload note
      default: ""
      required: false
ui_hints:
  pass_through: false
execution_template: transform_stub
```

Each field under `config_tabs` becomes a `config_schema` entry with a `tab`
hint. `NodeConfigScreen` reads that hint and renders the field in `Source`,
`Parameters`, or `Payloads`.

Use `config_fields` only when tab placement does not matter. Untabbed fields
land in `Parameters`.

## Supported Values

Categories:

- `flow`
- `io`
- `data`
- `ai`
- `debug`
- `utility`

Execution templates:

- `pass_through`: forwards `context.inputs["input"]` to the first output port.
- `producer`: emits `config["value"]`.
- `transform_stub`: forwards input with a placeholder transform body.
- `output_sink`: records input in the memory bank `output_log`.
- `async_wait`: sleeps for `config["duration"]`, then forwards input.
- `error_stub`: calls `context.signal_error(...)`.

Config field types:

- `string`
- `integer`
- `float`
- `number`
- `boolean`
- `select`
- `multiselect`
- `multiline`
- `code`

Common schema keys include `label`, `description`, `required`, `options`,
`placeholder`, `group`, `min`, `max`, `min_length`, `max_length`, `height`, and
`language`.

## Helper-First Node Workflow

1. Write a spec in `aotn_node_helper/specs/<node_type>.yaml`.
2. Prefer `config_tabs` with `Source`, `Parameters`, and `Payloads`.
3. Run `create_node.py`.
4. Open the generated node file and replace template execution logic when
   needed.
5. Run `check_node.py <node_type>`.
6. Add broader tests only when the node changes shared runtime behavior,
   editor display, command navigation, or workflow validation.

Ordinary node fields should not require frontend edits. If a new field cannot
render cleanly from schema metadata, improve `frontend/widgets/form_generator.py`
or the shared command widgets before adding node-specific UI.

## Structural UI Guardrail

Set `structural_ui: true` only when the node needs config UI derived from live
workflow topology or editor state, such as branch paths, merge targets, wait
targets, file picker behavior, or dynamic sections that depend on checked
options.

The helper deliberately does not patch frontend screens for these cases. It
emits a UI follow-up note instead. That pause is useful: custom UI is where
keyboard navigation, autoscroll, sizing, and dynamic-update regressions usually
enter.

Before implementing structural UI:

- Read `BACKEND_FRONTEND_BOUNDARY.md`.
- Reuse `CommandScreenMixin`, `CommandInput`, `CommandTextArea`,
  `command_navigation.py`, `list_navigation.py`, and `dynamic_sections.py`.
- Add a keyboard-only test that opens the screen, moves through controls,
  activates controls, changes a dynamic option, reaches Save/Cancel, and checks
  scroll-to-focused-control behavior.
- Keep topology-derived UI in `frontend/`; backend nodes stay graph-ignorant.

## Current Limitations

- Generated execution templates are starter bodies, not final business logic.
- The helper does not validate that generated config fields mount successfully
  in Textual.
- The helper does not yet create UI navigation tests.
- The helper does not scaffold general-purpose screens or modal flows.
- `config_schema` supports only the currently documented generic keys; dynamic
  visibility and conditional sections are still hand-managed by frontend code.

## Direction: UI Standardization Helper

The next useful evolution is to make the helper verify UI contracts, not just
node contracts.

Recommended additions:

- `check_ui.py <node_type>`: mount `NodeConfigScreen` for the generated node and
  assert every schema field appears in the intended top-level tab.
- A generated keyboard smoke test for node config: tab switching, W/S movement,
  E/Enter activation, edit-mode exit, Save/Cancel reachability, and no trapped
  selection lists.
- A generated dynamic-section smoke test for fields that declare visibility
  conditions, once a generic `visible_when` schema key exists.
- A screen scaffold command for new Textual screens that defaults to
  `CommandScreenMixin`, a visible Cancel control, vertical button order, a
  `StatusBar`, and a matching keyboard-navigation test.
- A UI manifest or checklist that lists each screen's command widgets,
  dynamic widgets, scroll container, and expected first/last focus targets.
- A shared "form contract" test suite that every schema field type must pass:
  render, focus, activate, edit/select, serialize, resize safely, and exit.

The goal is not to generate every screen. The goal is to make the default path
hard to get wrong and to catch the recurring regressions before they become
manual UI debugging sessions.

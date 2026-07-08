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
├── check_ui.py
├── generator.py
├── ui_checks.py
└── specs/
```

Run helper commands from `AttackOfTheNodes/` with the workspace venv:

```bash
../.venv/bin/python ../aotn_node_helper/create_node.py ../aotn_node_helper/specs/<node_type>.yaml
../.venv/bin/python ../aotn_node_helper/check_node.py <node_type>
../.venv/bin/python ../aotn_node_helper/check_ui.py <node_type>
```

Or run them from the workspace root by passing the same script paths.

## What It Generates

From one JSON/YAML spec, `create_node.py` generates:

- `AttackOfTheNodes/backend/nodes/<category>/<node_type>.py`
- registration updates in `AttackOfTheNodes/backend/nodes/__init__.py`
- `AttackOfTheNodes/tests/generated/test_<node_type>.py`
- `AttackOfTheNodes/tests/generated/test_<node_type>_ui.py` — a config-UI
  smoke test, emitted when the spec uses `config_tabs`, `input_sources`, or
  `output_routing` (override with `generate_ui_test: false`)
- optional UI follow-up notes under `aotn_node_helper/generated_notes/` when
  the spec marks `structural_ui: true`

`check_node.py <node_type>` runs a focused compile plus the generated test for
that node.

`check_ui.py <node_type>` mounts `NodeConfigScreen` for the node and verifies
the schema-driven UI contract: every schema field renders a widget, each widget
lands in its declared top-level tab, each widget participates in keyboard
focus, and `enabled_when`/`visible_when` rule state matches the mounted
defaults. Structural nodes (`branch_node`, `merge_node`, `branch_end_node`)
are rejected with a clear message — they use custom topology UI. The same
checks run from the generated `test_<node_type>_ui.py`, so CI covers them
without invoking the CLI.

## Spec Shape

Use `config_tabs` for the authoring workflow. It mirrors the config UI and
places ordinary fields into the fixed Node Config tabs without frontend edits.

```yaml
node_type: example_formatter_node
class_name: ExampleFormatterNode
category: data
primary_family: Complex
tags: ["Utility"]
icon_name: combine
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

## Standard Model Sections

Two top-level spec sections expand into the standard node I/O model from
`NODE_STANDARDS.md` so ordinary nodes do not hand-write the pattern.

### input_sources

Declares where each input can come from. Each entry expands into a
`<name>_source` selector in the Source tab (under a `Required Inputs` /
`Optional Inputs` section header from the entry's `required` flag), a
`<name>_vault_key` dropdown that is hidden unless the Vault source is
selected (`visible_when`) and carries `vault_type` = the entry's data type so
the config screen offers type-filtered vault keys, and (when the Configured
source is allowed) a `<name>` parameter field in the Parameters tab that is
visible only for the Configured source.

```yaml
input_sources:
  file_path:
    label: File path
    sources: ["upstream", "vault", "configured"]
    default: configured
    parameter:
      type: string
      label: File path
      placeholder: /path/to/file
```

Rules:

- `sources` must list at least two of `upstream`, `vault`, `configured`.
  Single-source inputs do not need a selector — declare a plain field instead.
- `default` must be one of the listed sources (defaults to the first).
- `parameter` is required when `configured` is allowed and rejected when it is
  not.
- Selector option values are the display strings `Upstream payload`, `Vault`,
  and `Configured`. Backend `execute()` reads them as such, e.g.
  `self.config.get("file_path_source") == "Vault"`.

### output_routing

Declares how the node's result leaves. Expands into the Payloads tab fields
`transient_output` and `dead_drop_passthrough` (mutually exclusive, per
`NODE_STANDARDS.md`) plus optional `vault_write` / `vault_write_key` fields
gated on the vault checkbox — all under a `Result Routing` section header.

```yaml
output_routing:
  default: transient            # or dead_drop
  transient_label: Send bool result to next node
  dead_drop_label: Forward incoming payload unchanged
  vault:
    mode: optional              # optional | default_on | required_unless_transient
    label: Save error message to Vault
    key_label: Error log Vault key
```

Vault modes:

- `optional`: unchecked by default, freely toggled.
- `default_on`: checked by default, freely toggled.
- `required_unless_transient`: checked by default and locked (greyed out)
  until `transient_output` is checked, so the result is never silently
  discarded. This is the Basic LLM node pattern from `NODE_STANDARDS.md`.

Set `dead_drop: false` to omit the passthrough option for nodes that always
produce a fresh output.

## Unified `inputs:` / `outputs:` Blocks

The unified blocks (NODE_STANDARDIZATION_HANDOFF.md §7) let an author declare a
port's full I/O contract in one place. `inputs:` replaces the split
`input_sources` + `input_port_metadata` sections; `outputs:` replaces
`output_port_metadata`. They are additive — the legacy sections still work, and
node-level Payloads routing still comes from the separate `output_routing`
block either way. The generated reference node is
`specs/example_file_instance_node.yaml`.

Each key under `inputs:` / `outputs:` is a **port name**. The port list
(`input_ports` / `output_ports`) is derived from the keys, so do not also
declare `input_ports` / `output_ports` (or the legacy sections) alongside a
block — the generator rejects the mix.

```yaml
inputs:
  file_path:
    type: file                       # canonical data type (backend/data_types.py)
    required: false                  # absent => optional
    label: File path                 # source-selector label + port name
    description: Where the path comes from at execution time
    sources: ["upstream", "vault", "configured"]   # expands the Source selector
    default: configured
    parameter:                       # required when 'configured' is allowed
      type: string
      label: File path
      placeholder: /path/to/file
outputs:
  default:
    name: Open Result
    type: bool                       # 'boolean' is accepted as a deprecated alias
    required: true
    to: ["downstream", "vault"]      # routing destinations for the detail panel
    pass_through: true               # advertises the dead-drop passthrough line
    description: True when the file opened successfully, false on error
```

Per-port keys:

- `type` — canonical data type from `backend/data_types.py` (`string`,
  `number`, `bool`, `var`, `file`, `ai_session`, `any`). Absent ⇒ `any`. An
  unknown type **warns** (it does not block generation); `boolean`
  canonicalizes to `bool`.
- `required` — absent ⇒ optional (`False`).
- `description` / `name` — port label and one-line description.
- `sources` (inputs) — when present, expands the same `<port>_source` selector,
  gated Vault key, and Configured `parameter` field as `input_sources`.
- `to` (outputs) — routing destinations (`downstream`, `vault`) the selector
  detail panel renders; `pass_through: true` advertises the dead-drop line.

These ride on `input_port_metadata` / `output_port_metadata` and are exposed
through `NodeFactory.get_node_types_metadata()`, where absent `data_type` /
`required` are filled with their defaults.

## Dynamic Form Rule Keys

Any config field (hand-written or expanded) may declare these schema keys.
`NodeConfigScreen` applies them live as the user changes controls, including
across tabs (a Source tab selector can grey out a Parameters tab field):

- `enabled_when`: mapping of field name to expected value. The field greys out
  when the condition does not hold. All entries must match (AND); a list value
  matches any listed entry (OR within one field).

  ```yaml
  enabled_when:
    file_path_source: Configured
  ```

- `visible_when`: same condition shape; hides the field, its label, and its
  description when the condition does not hold.
- `mutually_exclusive_with`: list of boolean fields. Checking this field
  unchecks the listed partners. Declarations are symmetric — declaring on one
  side is enough. Only valid on `boolean` fields.
- `required_when`: same condition shape. While it holds, the field renders as
  required (its label / checkbox gains the ` *` marker live), on top of any
  static `required: true`.
- `section_when`: a mapping of `section title → condition`. While a condition
  holds, the field's **section header** is retitled to that title (first match
  wins; falls back to the static `section`). Only meaningful on the field that
  opens a section run — e.g. retitling `Optional Inputs` to `Required Inputs`
  for an input that becomes mandatory in a particular mode.
- `force_value_when`: a mapping of `value → condition`, valid on `select`
  fields. While a condition holds, the select is locked to that value and
  disabled; when none holds it is re-enabled. Use to pin a source to
  `Configured` in a mode where only a typed value makes sense.

  ```yaml
  document_source:
    required_when: { prompt_source: Continue AI session }
    section_when:
      Required Inputs: { prompt_source: Continue AI session }
    force_value_when:
      Configured: { prompt_source: Continue AI session }
  ```

The generator validates rule keys at spec time: referenced fields must exist
and mutual-exclusion participants must be booleans. With the helper's built-in
simple-YAML fallback parser, write conditions as nested mappings (as above)
rather than inline `{key: value}` braces; inline form requires PyYAML.

See `specs/example_file_instance_node.yaml` for a complete spec using
`input_sources`, `output_routing`, and the expanded rule keys.

## Supported Values

Categories:

- `flow`
- `io`
- `data`
- `ai`
- `debug`
- `utility`

Phase 17 identity (required since 2026-06-12; keep in sync with
`backend/node_identity.py`):

- `primary_family` (required): `Inputs`, `Outputs`, `Flow Control`, `Utility`,
  or `Complex`. This is the user-facing selector family; `category` remains
  the legacy backend grouping. `Inputs` and `Outputs` share the selector's
  `I/O` tab behind an Input/Output switch — that mapping is frontend-only.
- `tags` (optional): freeform keyword strings used only for node **search** in
  the selector. The rigid subcategory taxonomy and its filter checkboxes were
  retired 2026-06-19, so there is no fixed vocabulary and no validation — pick
  whatever keywords help discovery (e.g. `File I/O`, `Internet`, `AI`).
- `group` (optional): frontend navigation group name (e.g. `Send / Notify`).
  Nodes sharing a group appear behind one Group Picker entry in the selector.
  See `PHASE_17_NODE_VISUAL_IDENTITY.md` and `NODE_CATALOG.md` for the group
  layout.
- `selector_section` (optional): section header the entry renders under in
  the selector list (e.g. `Transform`). All members of one `group` must
  declare the same section; the generator validates this.
- `icon_name` (optional): icon hint string.
- `color_hint` (optional): defaults from the family color map
  (Inputs green, Outputs amber, Flow Control blue, Utility grey,
  Complex violet).

The generator validates the five families, requires `selector_section`
whenever `group` is set (except on the flat-rendered Outputs side), and emits
`group` / `selector_section` as class metadata on generated nodes.

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
`placeholder`, `group`, `section`, `min`, `max`, `min_length`, `max_length`,
`height`, `language`, `path_hint`, `secret`, and `vault_type`. Dynamic rule
keys are `enabled_when`, `visible_when`, and `mutually_exclusive_with` (see
Dynamic Form Rule Keys above).

`section: "Header"` renders a bold section header above the first field of a
consecutive run declaring the same section (e.g. `Required Inputs`,
`Result Routing`, `AI Session`).

`vault_type: "<canonical type>"` renders a string field as a dropdown over
vault keys compatible with that type (typed entries plus keys declared by
workflow writers; untagged legacy entries satisfy `string`; `any` shows all).
Eligibility: keys whose only writers are downstream of the node on the same
branch — or the node itself — are excluded (they cannot exist when the node
runs); parallel-branch writers stay listed. A select option that would reveal
an empty `vault_type` dropdown (e.g. `Vault`, `Continue AI session`) is pruned
from the source selector by `NodeConfigScreen`.

`path_hint: "file"` marks a string field as a filesystem path; the validator
emits a warning if the configured path does not exist at validation time.

`secret: true` marks a string field as a secrets-store key reference; the
validator emits an error if the field is required and empty, and a warning if
the named key is absent from the secrets store.

## Helper-First Node Workflow

1. Write a spec in `aotn_node_helper/specs/<node_type>.yaml`.
2. Use `input_sources` and `output_routing` for the standard I/O model from
   `NODE_STANDARDS.md`; use `config_tabs` with `Source`, `Parameters`, and
   `Payloads` for node-specific fields.
3. Run `create_node.py`.
4. Open the generated node file and replace template execution logic when
   needed.
5. Run `check_node.py <node_type>` and `check_ui.py <node_type>`.
6. Add broader tests only when the node changes shared runtime behavior,
   editor display, command navigation, or workflow validation.

Ordinary node fields should not require frontend edits. If a new field cannot
render cleanly from schema metadata, improve `frontend/widgets/form_generator.py`
or the shared command widgets before adding node-specific UI.

## Structural UI Guardrail

Set `structural_ui: true` only when the node needs config UI derived from live
workflow topology or editor state, such as branch paths, merge targets, wait
targets, or file picker behavior. Conditional field state no longer requires
structural UI — use `enabled_when`, `visible_when`, and
`mutually_exclusive_with` instead.

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
  Standard-model specs still need their `execute()` written to read
  `<name>_source` and route output per the routing checkboxes.
- Selector option values are display strings, not separate machine values.
  A future label/value pair in the form generator would decouple backend
  reads from UI copy.
- The generated UI smoke test checks mount-time contract state; it does not
  yet simulate keyboard navigation through every control.
- The helper does not scaffold general-purpose screens or modal flows.
- The simple-YAML fallback parser does not support inline `{key: value}`
  mappings; use nested mappings or install PyYAML.

## Direction: UI Standardization Helper

Done so far:

- `check_ui.py <node_type>` mounts `NodeConfigScreen` and asserts tab
  placement, focus participation, and dynamic rule state (2026-06-12).
- Generic dynamic-form schema keys `enabled_when`, `visible_when`, and
  `mutually_exclusive_with` are implemented in `form_generator.py` and applied
  live by `NodeConfigScreen` (2026-06-12).
- Standard-model spec sections `input_sources` and `output_routing` expand the
  `NODE_STANDARDS.md` patterns automatically (2026-06-12).
- A generated config-UI smoke test is emitted for specs that use tabs or the
  standard sections (2026-06-12).

Remaining:

- A generated keyboard smoke test for node config: tab switching, W/S movement,
  E/Enter activation, edit-mode exit, Save/Cancel reachability, and no trapped
  selection lists.
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

# Node Design Standards

**Status:** Design reference — in-progress draft as of 2026-06-11.
This document captures the intended scope, input/output patterns, and UI
behavior rules for AttackOfTheNodes nodes. It is the authoritative reference
before authoring a new node type or changing an existing one's I/O model.

## Node Type Classification

Before defining a new node type, decide how it fits in the taxonomy:

| Situation | Solution |
|---|---|
| Variants have different port shapes | Must be separate node types regardless |
| Variants have same ports, very different config | Group with picker |
| Variants are minor config differences with same ports | One node + mode select field |
| Standalone, unique node | Direct-add, no group |

**Examples:**
- File Write overwrite vs append → same ports, one config field → single node
  with a mode select. No separate type needed.
- Branch variants → different port shapes (2 ports vs N ports vs loop shape) →
  must be separate types.
- Email vs Webhook vs OS notification → same ports, radically different config →
  group with picker.

Apply this rule before changing taxonomy. Groups are a frontend navigation
concept; the backend exposes the metadata but does not use it for execution.
Record every new node idea
in `NODE_CATALOG.md`, even concept-only ones.

---

## Core Principle

Nodes have predetermined input and output configurations with limited, known
flexibility. The flexibility that exists is expressed through a standard source
and routing model — not through open-ended custom config. A node author defines
which inputs and outputs the node has; users configure how data reaches and
leaves those fixed ports.

**Helper support (2026-06-12, aligned with the redesigned UI 2026-07-08):**
the node helper expands this model automatically. Declare `inputs:`/`outputs:`
(or the legacy `input_sources`) plus `output_routing` in a helper spec and the
generator emits the source selectors, hidden-until-Vault typed key dropdowns,
Configured parameter fields, and the routing defaults + port metadata that
drive the composed Payloads tab (Downstream node payload + Vault payloads).
`NodeConfigScreen` applies the dynamic rules live through the generic schema
keys `enabled_when`, `visible_when`, `required_when`, `section_when`,
`force_value_when`, and `mutually_exclusive_with`. See `NODE_HELPER.md` — in
particular "What the Config UI Renders Automatically" — and
`aotn_node_helper/specs/file_output_node.yaml`.

## Standard Input Source Model

Every node input that can accept external data offers up to three source
options. These options are mutually exclusive per input — selecting one
disables the others in the UI.

| Source option | What it means |
|---|---|
| **Upstream (transient)** | Read the dead-drop payload arriving on the connected input port from the previous node in the execution path. The value is stored in MemoryBank keyed by `(source_node_id, port_name)` and is resolved automatically from the execution chain. |
| **Vault** | Read a named variable from the MemoryBank persistent store. User provides the variable key. The key is accessible by any node in the run that declares it, including nodes in other branches. |
| **Configured** | Read a value entered directly in the Parameters tab. No live connection required. |

**Note on MemoryBank:** both Upstream and Vault data live in the same
MemoryBank. The distinction is addressing, not a separate storage system.
Transient data uses ephemeral path-scoped keys (`source_node_id`, `port_name`)
that are resolved automatically along the execution sequence. Vault data uses
stable, user-defined names that any node in the run can look up by key —
including nodes in parallel branches or further downstream that were not
adjacent to the writing node.

Fields that are irrelevant to the selected source are **hidden**
(`visible_when`), not greyed out (revised 2026-07-07 — hiding reads better at
a glance):

- **Upstream** selected: the Vault key dropdown and the Parameters field for
  that input are hidden.
- **Vault** selected: a **type-filtered Vault key dropdown** appears directly
  below the selector (entries compatible with the port's `data_type`, shown as
  `key [type]`); the Parameters field is hidden.
- **Configured** selected: the Vault key dropdown is hidden and the matching
  Parameters field becomes visible and editable.

Grey-out (`enabled_when`) is reserved for a genuinely locked state whose visible
presence helps the user understand a constraint. Explain that constraint in the
UI and document the convenience reason. Prefer a read-only summary if inspection
is the only purpose. A field gated by a toggle, source, or mode uses
`visible_when`; hide its label and description too, while preserving its value.

Some inputs may not offer all three options. For example, a document/context
input on a basic LLM node may only offer Upstream or Vault (no hard-configured
option — the document is always expected to come from a live data source).

## System nodes (AI coordination decision C7, owner 2026-10-20)

Disk space, Git status and File age use the standard **Forward incoming
payload unchanged** checkbox (owner follow-up, 2026-10-22). Checked replaces
the downstream report with the original incoming payload and hides/disables
the report's downstream name/description controls. Unchecked sends the report.
An enabled Vault output always stores the computed report with its own type,
independently of forwarding.

A System node reads the state of this machine with one fixed operation: the
command (if any) is in the node's code, the workflow sets only typed
parameters, arguments are argv with no shell, and the result is one typed
value chosen by a **Report** parameter (routed like any output, optionally to
the Vault). Every folder or file it touches goes through
`backend/system_access.checked_path`, which allows only paths inside the
Options list `system_node_folders` (`;`-separated, default `~`) and raises
`not_allowed` or `folder_missing`. An empty setting allows nothing; only an absent one means `~`. A command must also neutralize anything the target can configure to run (Git's `core.fsmonitor`), check what the command will actually read (Git's discovered repository, not just the given folder), and own its process group so a stop or timeout kills it and its children. A generic `run_command_node` is deferred
until needed, behind a Settings allowlist with approval on.

## Standard Output Routing Model

**Design principle (revised 2026-07-08):** every node has **one designated
downstream output** ("Downstream node payload"), fixed at node-design time.
Every *other* output a node produces is a **keyed Vault payload** of a declared
type. The Payloads tab is built from `output_port_metadata` (each port's `to`
list — `downstream` and/or `vault`), not from routing checkboxes.

**Payloads tab layout** (top to bottom):

1. **Downstream node payload** — the designated output, shown as
   `Name  [type]`, with an **editable payload name** and **editable
   description** (they seed from the port metadata and can be overwritten;
   downstream nodes see the edited name/type in their Incoming Payload block).
2. **`[ ] Forward incoming payload unchanged`** — the single routing checkbox.
   When checked, the node forwards the arriving payload instead of its own
   result, and the downstream name/description fields are hidden.
3. **Vault Payload(s)** — for each output also routed to the Vault: an
   editable Vault key and description. Optional vault outputs carry a
   `[ ] Disable output` checkbox above them (checking it hides the key /
   description). A port is optional-to-vault unless its metadata sets
   `vault_required: true`.
4. Node-specific routing-adjacent sections (e.g. **AI Session**) follow.

An output may be **both** downstream and vault (`to: ["downstream", "vault"]`)
— e.g. an LLM node's `Result  [string]` is the downstream payload *and* is
optionally duplicated to the Vault, so it appears in both sections.

The old per-output `Transient output` / `Save to Vault` checkboxes are retired.
Config keys the composer reads/writes: `dead_drop_passthrough` (the checkbox),
`transient_output` (own-result publication; forwarded payloads still flow), `transient_outputs` (downstream
name/description overrides), and `vault_write` / `vault_write_key` /
`vault_write_description` (the vault output; enabled unless disabled). The single `vault_write*` keys describe the primary result. File Manager adds
explicit keyed `additional_files` rows; nonselected files require Vault keys.
Start and File Reader expose independent downstream publication, including
Vault-only text results.

File Manager emits the viewed file's typed reference as its default downstream
payload. Forward incoming payload unchanged replaces only that downstream
payload. Its optional Vault output always stores the viewed file reference,
independent of forwarding, for later nodes and parallel branches in the run.

File references identify files, not successive versions. File Writer reuses an
upstream/Vault reference (including its resource key) when Overwrite or Append
targets that same file. Create unique emits a different reference when it
creates another file. Additional Vault keys are names for the same reference.
File output forms explain this and label payload-name overrides Display name;
these overrides do not change file identity. File Writer's forwarding checkbox
names the connected input: Content takes precedence when both inputs are wired,
otherwise File Path carries the unchanged incoming payload. Configured/Vault
content and path choices do not change which connected payload is forwarded.

When inserting nodes, the editor prefers a unique exact input type match over
an `any` input (e.g. File Manager reference → File Writer File Path). Ambiguous
or unknown types retain the first-input convention. Config Save can reassign
an inactive input connection to a unique matching, unconnected Upstream input;
active connections and Configured/Vault destination choices are preserved.

Whenever a payload's data **name** appears in the UI (incoming or outgoing),
its data **type** is shown after it as a bracketed teal label —
`Result  [string]`.

### Branch termination

Termination is explicit node behavior, declared by `terminates_branch` metadata,
not a generic Outputs-family checkbox. End explicitly terminates; it is
registered and available through workflow authoring, but hidden from the TUI
selector. See [Current State](CURRENT_STATE.md) for the open selector decision.
Text Output
records formatted text and continues when connected; without a connection it
ends naturally. File Manager, File Reader, File Writer and Window Control
continue along connections.
Merge Beacon participates in the Merge rendezvous; internal supervisor
termination signals remain part of merge/recovery execution.

Old File Manager/Writer completion flags are archived by
`file_io_continuation_v1` migration and no longer affect execution. Use a
terminal node to end such a route. New node specs must not add the retired
optional completion checkbox.

### Branch spawning

A node that signals `branches` from `execute()` must set
`spawns_branches: ClassVar[bool] = True` (today `branch_node` and
`deep_branch_node`; a test enforces it). Factory metadata exposes the flag and
`NodeFactory.spawns_branches(type)` reads it. Only these nodes start a new
branch identity for Merge closure options. Having several output ports (an
`error` path, Error Mux routes, Conditional `true`/`false`) does not make a
node a branch point.

### Emitting Output in Code

Every node signals completion through `context.signal_done(payload)`. The
payload carries output under port names:

```python
context.signal_done({"data": {"default": value}})  # a plain call, not awaited
```

Multi-output and branching nodes use named port keys (`path_a`, `path_b`,
etc.). The `Supervisor` writes these to the transient `MemoryBank` store so
downstream nodes receive them as prepared inputs.

Durable output for user-facing results goes through `context.memory_bank`
membank writes. Named vault keys declared in `membank_outputs` are visible to
all branches and readable via the Vault in node config.

## Data Type Scope

**Transient payloads are JSON.** They can carry any JSON-serializable value:
booleans, numbers, strings, objects, and arrays. This includes LLM responses
and other large text values — payload size is not the limiting factor.

Choose transient or Vault addressing for the workflow's data flow and timing:

- A transient key identifies the source node and port, not a branch. The
  supervisor resolves connected inputs from this shared run store. A later
  write to the same node/port replaces the prior value, and a read before the
  write has no delivered value. Do not assume branch or per-visit isolation.
- A named Vault key is accessible by any node in the run that declares the
  key, regardless of branch or position in the graph.

**Common usage patterns:**

- **Booleans, flags, counters, short strings** — transient is natural. These
  are consumed immediately by the next node (e.g., a conditional branch reading
  a success flag).
- **Document text, LLM responses, accumulated results** — Vault is preferred
  when the data needs to cross branch boundaries or be accessed far downstream.
  Transient is valid when the data only travels to the immediately next node
  and no cross-branch access is needed.
- **Incremental document modification** — transient is appropriate when a
  branch is modifying a document pass-by-pass and does not need to keep the
  original clean copy. The modified document flows forward as transient between
  nodes in that branch.
- **Duplicate to both** — a node can write the same result to both transient
  (for the next node) and Vault (for other branches or later nodes) at the
  same time.

**File I/O:**
Active file sessions are managed by the backend `RunSession`. File paths are
stored as plain strings in node config; actual file handles are opened and
cached by `RunSession` at execution time so multiple nodes in a run can share
the same file access. Files can serve as both inputs (read content into
transient or Vault) and outputs (write Vault or transient content to disk).

## Custom Config Keys

Config a custom editor section manages (not generated form fields) is
declared on the node class: `custom_config_keys = {"routes": "meaning"}`.
The factory publishes it; the authoring builder accepts those keys and
`aotn describe` / `inspect` list them as unchecked (no schema). Error Mux
declares `routes` and `unmatched_route`. A node with an undeclared custom
key cannot be configured from a spec.

## Number Fields (C5)

Schema fields typed `integer`, `float` or `number` follow one policy
(`backend/field_types.check_number`, owner 2026-10-15):

- The value must be a finite number; `integer` fields must be whole.
- Declare limits on the field: `min`, `max`, and `min_exclusive: true` when
  the minimum itself is not allowed (HTTP timeout: `min: 0` exclusive).
  Every node's default must pass its own field (a test checks this).
- Blank means the node's default; the input shows `blank = default`.
- The node editor blocks the save with the problem under the field and
  keeps the typed text; the validator reports a saved bad value as
  `invalid_number`, which blocks the run. Nothing is coerced to 0.
- Hidden fields (`visible_when` not met) are not checked.
- Integer fields parse exactly (no float round trip); a float too large
  to represent reports "Number is too large".
- Nodes receive number fields already normalized (`Node.__init__` uses
  `normalize_numbers`): read `self.config[...]` without re-parsing.
- A number drawn by a custom control is checked too: register its widget
  in `CUSTOM_NUMBER_CONTROLS` (`frontend/screens/node_config.py`).

## Per-Port Contract Metadata

Each port a node declares carries I/O contract metadata in
`input_port_metadata` / `output_port_metadata`, exposed through
`NodeFactory.get_node_types_metadata()`. Per port:

| Field | Meaning | Default when absent |
|---|---|---|
| `name` | Human label for the port | derived from the port id |
| `description` | One line: what travels on the port | `""` |
| `data_type` | Canonical type from `backend/data_types.py` | `any` (explicit permissive) |
| `required` | Whether the port must have an assigned source | `False` (optional) |

The fields are **additive with documented defaults** (handoff §6): older node
files and saved workflows that declare neither still load — absent `data_type`
becomes `any`, absent `required` becomes optional. The factory canonicalizes
declared types (so the deprecated `boolean` resolves to `bool`), and declaring
a type outside the canonical set warns at class-definition time via
`data_types.validate_type`. The frontend renders this contract; the backend
advertises it and never inspects frontend state.

**Edge compatibility (C2).** One rule, `data_types.types_compatible(actual,
wanted)`: `any` (or no type) on either side matches; otherwise the canonical
types must be equal. There is no implicit conversion (File Write rejects a
number on its text input). The editor's connector choice, the Source
dropdowns (whether "Upstream payload" and a Vault key are offered) and the
validator all use it. `backend/port_types.py` traces the producer through
pass-through nodes to every possible producer (`trace_producers`); a Branch
path forwards the Branch's input, or its Vault seed's writer types. The
Upstream option is offered when any producer fits. An active Upstream
edge with a producer type the port does not accept is a preflight
**warning** ("Type mismatch": `Input 'File' expects file but Dice sends
number`). A node that rejects a payload at runtime should say so with
`data_types.input_mismatch_message(port name, source, expected, value)`:
`Input 'File' (Upstream payload) expects a file reference but got a number
(42)`.

## Typed Vault Outputs

Vault writes can carry an explicit `type` field alongside the value. The type
identities come from the canonical data-type vocabulary in
`backend/data_types.py` — the **single source of truth** shared with node port
data types so dropdown type-filtering between ports and vault keys stays
coherent (no parallel free-string vocabularies). Canonical set: `string`,
`number`, `bool`, `var`, `file`, `ai_session`, `any`.

> **Reconciliation (2026-06-19):** this list previously spelled the boolean
> type `boolean`. Per the shared data-type vocabulary the canonical
> spelling is now **`bool`**. `boolean` is accepted only as a deprecated alias
> (`data_types.canonicalize("boolean") == "bool"`) so older specs and saved
> workflows still resolve. `any` is the explicit permissive type — there is no
> silent "untyped" default.

`string`, `number`, and `bool` entries behave as before — pure JSON values
stored and read by name.

`file` and `ai_session` entries carry tagged JSON reference objects; the Vault
also records a separate `type_tag`. A file reference includes `type`, `ref_key`
and `path`. A Python resource, when needed, is registered in `RunSession`.
For example, inside a node with an existing handle and resolved path:

```python
from backend.file_refs import file_reference

ref = file_reference(resolved_path)
context.run_session.register_resource(ref["ref_key"], handle)
context.memory_bank.store_persistent(vault_key, ref, type_tag="file")
```

A downstream node can retrieve the registered file handle with `get_resource`
(it returns `None` if no resource was registered):

```python
ref = context.memory_bank.read_persistent(vault_key)
handle = context.run_session.get_resource(ref["ref_key"])
```

Chat references instead identify histories accessed through RunSession's chat
session API (`get_chat_history`), not generic resources.

The type tag tells the node and the framework which lookup path to use. From
the user's perspective this is invisible — they see `filename (file)` in the
Vault source dropdown.

Input source dropdowns type-filter automatically. An input declared as
accepting `file` shows only `file` vault entries; an LLM continuation input
shows only `ai_session` entries.

## AI Session Config-Driven Output (LLM Nodes)

There is no separate Chat Session node. Chat Completion implements the
"Keep active AI session" option; this is the pattern for future LLM nodes,
not a claim that simulated AI nodes already support it.

On a successful kept-session call, Chat Completion extends a message history
in RunSession using `get_or_create_chat_session` / `append_chat_message`, then
writes `{"type": "ai_session", "ref_key": session_key}` to the Vault with
`type_tag="ai_session"`. The history is a list of messages, not a provider client
registered as a generic resource. Failed calls do not persist the new turn.

A downstream Chat Completion selects Continue AI session and the typed Vault
key. It resolves `ref_key` and reads `get_chat_history(ref_key)`. With Keep active
AI session enabled in Continue mode it extends the same history rather than
asking for a second key. Vault contains the tagged reference; history lives in
RunSession and expires with the run. `get_resource` is not this lookup API.

### AI Input Pattern (session seeding)

The planned **AI Input** node (I/O Input side, see `NODE_CATALOG.md`) is the
standard way to seed a chat session with context before the response is
needed:

- Prompt source: Upstream / Vault / Configured (standard input model). Useful
  when the prompt is customized during workflow execution before being passed
  to the AI.
- Executes the turn under a session key and writes
  `{"type": "ai_session", "ref_key": <session_key>}` to the vault — downstream
  nodes pick the session up by key.
- **Default output routing is dead-drop passthrough** — the AI call is a side
  effect; the incoming payload forwards unchanged.
- Optional "Output AI response" flips transient output to the response text
  (standard transient/dead-drop mutual exclusion applies).

AI nodes declare a curated supported-model list, not an open-ended model
field. Structured-decision AI nodes (AI Conditional Branch, AI Tool Call)
require models with dependable structured output and carry stricter lists.
See the capability-based AI direction in `NODE_CATALOG.md`.

## Validator Rules for Typed Vault References

Two tiers apply to vault entries that reference RunSession handles:

- **Error**: no node in the workflow declares the vault key at all. The key
  can never exist at runtime regardless of timing. This blocks the workflow.
- **Warning**: a node declares the key but lives on a parallel branch where
  execution order cannot be guaranteed. The validator recommends inserting a
  Wait Until node or restructuring branches so the key is written before it is
  read.

The validator must not attempt to infer runtime timing from node count, type,
or branch depth. Static analysis cannot determine which branch is slower.
Warning plus Wait Until suggestion is the correct ceiling.

This error/warning split applies uniformly to string, number, file, and
ai_session vault references.

**Issue codes (2026-10-15).** Every validator error and warning is
`{node_id, code, message}`, plus `port` / `source_node_id` where they apply
(`type_mismatch`, `unwritten_vault_key`). `code` is one of
`backend/validation_codes.ISSUE_CODES` (each with a one-line meaning).
Frontends label and group issues by code (`VALIDATION_LABELS` in
`frontend/screens/error_details.py`), never by message text, so messages
can be reworded freely. A new check adds a code there and a label in the
table; `tests/test_validation_codes.py` fails if either is missing.

## Standard Config Tabs

Use Source, Parameters, Payloads, and Connections as shared section meanings,
in that order when applicable. **Four tabs are not mandatory.** Show only sections
that expose actual node capabilities or useful information; omit empty sections
and unsupported source/routing/Vault controls. Compact nodes may use a flat form.
Topology-driven nodes may use a focused layout while reusing schema fields and
shared navigation. Wait Until uses `1 - Wait` (alias, targets, timeout and fixed
forwarding explanation) and `2 - Connections` (read-only wiring).

Number the tabs that are actually present consecutively. Number keys select the
visible tab; W/S moves controls, A/D stays within a row, and letters/digits type
normally while editing. Keep Save/Cancel outside the tab's scrolling content.
Do not introduce per-node navigation behavior to compensate for layout choices.

Configuration controls must match execution. Wait Until coordinates completion
and forwards its incoming dead-drop unchanged; it never reads or writes the
Vault. Its downstream node selects any Vault input. Timeout 0.0 means wait forever.
See [WAIT_UNTIL_UI_PLAN.md](archive/WAIT_UNTIL_UI_PLAN.md) for implementation details.

### Source Tab

Declares where each input comes from. Layout (revised 2026-07-07):

```
Alias: [_________________]
<node type + description>

Incoming Payload                          ← auto-shown when inputs are wired:
  prompt  [string]  <- Text Input > default   producer chain, description, and
  "last captured value"                       last captured value per port

── Required Inputs ──────────────────
Prompt source:  [ Configured ▼ ]
                                          ← Vault key dropdown appears here
                                            only when Vault is selected
── Optional Inputs ──────────────────
Document / context source:  [ Upstream payload ▼ ]
```

- Input selectors are grouped under **Required Inputs** / **Optional Inputs**
  section headers (schema `section` key, driven by the port's `required`
  flag).
- The Vault key control is a **dropdown filtered by the port's data type**
  (schema `vault_type` key), populated from typed vault entries plus keys
  declared by workflow writers; it is hidden unless Vault is selected.
- **Eligibility (2026-07-07):** dropdowns exclude keys whose only writers sit
  downstream of this node on the same branch — they cannot exist when this
  node runs — and the node's own writes. Parallel-branch writers stay listed
  because static analysis cannot order branch timing (the validator's race
  warning covers that case). Source options that would reveal an empty
  dropdown (`Vault`, `Continue AI session`) are pruned from the selector
  entirely.
- Deleted nodes (including saved tombstones) do not supply selectable Vault
  keys. A shared key stays available when another eligible writer remains.
  File references left in memory without a current workflow writer are hidden;
  deleting a node does not erase Vault data needed for undo. Existing saved
  selections remain visible as unavailable declarations so they can be repaired.
- The old "Reveal upstream payload" / "Reveal Vault payload" checkboxes and
  the standalone Vault selection list are retired for standard-model nodes;
  the incoming payload block is always visible when something is connected.
  Legacy nodes (no `sources` port metadata) keep the old flat layout.

For inputs with only two valid source options (e.g., Upstream or Vault only),
show only those two. Do not show a Configured option if hard-coding is not
valid for that input.

### Parameters Tab

Contains node-specific configuration values that are either always editable
(fixed node settings) or conditional on Source tab selections.

Fields linked to a Source tab selector are **hidden** unless that input's
source is Configured (`visible_when`; revised 2026-07-07 — previously greyed).
Fields that are always editable (such as temperature, model name, or mode
flags) are never affected by source selection.

**Keep it light at a glance (owner, 2026-10-21).** Put a field's hint in its
grey `placeholder` (overwritten by typing; a blank number field means the
default) instead of a description line under it, and label each dropdown
item `Name · what it does` (`{label, value}` or `[label, value]` options).
Checkbox labels explain themselves. Escape `[` in labels (`\[SILENT]`): they
are Rich markup. A select can list names kept in Options with
`options_from_setting: <setting>` (`;`-separated) plus `option_summary`;
Notify me's Send to does.

### Payloads Tab

Built from `output_port_metadata` per the Standard Output Routing Model above:

```
── Downstream node payload ──────────
Result  [string]
  Payload name: [Result_______________]   hidden when forwarding
  Description:  [Model response text___]

[ ] Forward incoming payload unchanged

── Vault Payload ────────────────────
Result  [string]
[ ] Disable output                        (optional vault outputs only)
  Vault key:    [chat_result___________]   hidden when disabled
  Description:  [______________________]

── AI Session ───────────────────────
[ ] Keep active AI session ...
```

The single `Forward incoming payload unchanged` checkbox is the only routing
control; there are no per-output `Send to next node` / `Save to Vault`
checkboxes. The validator derives the vault declarations from `vault_write_key`
and session fields; the legacy "Write to Vault" rows and reveal checkboxes are
not rendered for standard-model nodes.

Per-node defaults vary. Document the default state for each node type in its
spec.

### Connections Tab

Read-only topology view (UX5): one row per incoming and outgoing connection
(the node at the other end, both port names, what flows), then the node's
Vault reads with their writers. Enter on a row opens that node's editor.
Wiring is edited from the editor, not here.

**Vault reads and writes come from one model**, `backend/vault_declarations.py`
(`active_vault_reads` / `active_vault_writes`): declared `membank_inputs` /
`membank_outputs`, the standard model (`<port>_source == "Vault"` +
`<port>_vault_key`, an active `continue_session_key`, `vault_write_key`,
session keys) and node-specific fields (Get Variable / Variable Reader /
Conditional `variable_name`, Set Variable / Variable Setter `variable_name`,
Counter `counter_name`, Branch `vault:` payload seeds). A new node that reads
or writes the Vault through its own config field must be added there, with
the activation rule (hidden slot, inactive mode) that applies. The Vault
pickers and the validator's existence/type/race checks use the same writers
(`typed_vault_writes`); node-specific writers have an unknown type (`any`).
Every read carries a **required/optional** flag (`vault_read_entries`):
`membank_inputs` and standard-model reads are required (no writer is a
preflight error); node-specific reads (`config_vault_read_entries`) declare
their own flag. All of them are optional today because each has a runtime
fallback (`default`, "", 0, the input payload), so a key nobody writes is a
preflight **warning** ("Unwritten Vault key"). A new node-specific read
without a fallback must declare `required=True`.

The Publish (normal output) toggle governs only the `default` port; the
engine's `error` port carries the error payload on failure regardless.

Below it, an **Errors** section (D8, step 3) lists every error code the node
can fail with: the default generic `node_error` first, then the codes the node
declares, each with its description and whether it is retryable. It is
presentation of `NodeFactory` metadata only.

## Errors and the `error` port (step 3, D7)

- Every node can fail through one engine-level port named `error`. A failure
  is either an exception (raise `backend.node_errors.NodeError(code, message,
  details=..., retryable=...)` for a declared code; any other exception gets
  `node_error`) or a signal on the port:
  `context.signal_done({"data": {"error": msg, "code": code, "details": {...}},
  "output_port": "error"})`.
- Declare codes in `error_definitions` (helper specs: `errors:`), each with
  `code`, `description`, `retryable`. Codes are lowercase dotted snake_case,
  unique, not `node_error` and not in the engine's `engine.` namespace (a node
  may list an engine code it raises, e.g. Wait Until's
  `engine.upstream_unreachable`). An undeclared code falls back to
  `node_error` with `details.undeclared_code`.
- The engine logs every failure once, then routes the versioned error payload
  along a connected `error` port (an Error Mux only for codes it lists; any
  other node for every code). Otherwise the run pauses for recovery, or
  follows its recovery policy when headless. The node is failed, never
  completed, and its `default` path is skipped as `not_taken`.
- Match on codes, never on message text.
- **Config-driven ports (port model).** A node whose outputs depend on its
  config overrides the classmethods `resolve_output_ports(config)` (the port
  list) and `describe_output_ports(config)` (per-port `name` / `description`
  / `data_type`, merged over `output_port_metadata`). A node whose output
  *type* depends on a setting declares it there (C3: HTTP Request returns
  `string` or `file` by Response as); read resolved metadata through
  `port_types.resolved_metadata` / `port_metadata`, never the static table. The class `output_ports` stays the
  type's fixed list. Branch (path count) and Error Mux (routes, keyed by
  stable ids, plus `unmatched`) do this. Everything else asks
  `NodeFactory.node_output_ports(node)` /
  `node_output_port_metadata(node)`; when a config save removes a port, the
  editor drops that port's connections
  (`WorkflowMap.prune_removed_output_connections`).
- Never add `error` to a node's `output_ports`: every node can show its
  error path from its Errors section (P3), and until the user picks errors
  to handle there, failures go to the default handler. A node fails by
  calling `context.signal_error(NodeError(code, message, details=...))`
  with a declared code, never by routing a payload to `error` itself
  (owner, 2026-10-18; HTTP Request and JSON Path used to list it).
- A node class may set `catches_upstream_errors = True` (Error Mux does):
  a failure of the node feeding its `input` is routed to it when
  `accepts_error_code(code)` is true, so it can sit inline after the node.
- A node class may set `receives_failed_input = True` (Error Mux does). When
  a failure is routed to it along `error`, the supervisor also passes the
  failed node's input as `inputs["failed_input"]`: the value of its single
  input port, or a dict by port name when it has several. Other nodes never
  see this key.

---

## Reference Example — File Write

`file_output_node` (File Write) accepts content and a file path from its
configured sources. It writes the file and publishes a `file` reference on
`default`, with optional Vault output. Forwarding, when enabled, replaces the
downstream result with the incoming payload. It continues along connections.
Use `aotn describe file_output_node` for its live fields and defaults.

A successful file reference is a tagged object from `backend/file_refs.py`,
not a boolean. File Write reports exceptions through `context.signal_error`;
ordinary exceptions receive the generic `node_error` code. Errors travel on
the engine's `error` route or go to recovery/policy, never a false-result route.

For a custom node that needs a more specific error, declare the code and signal
it (inside its class and execution method respectively):

```python
from backend.node_errors import NodeError

error_definitions = [
    {"code": "missing_path", "description": "No path was supplied.", "retryable": False},
]
# Inside execute(context), after resolving the path:
if not path:
    context.signal_error(NodeError("missing_path", "No path was supplied."))
    return
```

This is an authoring pattern, not a claim that File Write declares `missing_path`.
The factory adds `node_error` to every node. Match codes, not message text.

---

## Reference Example — Basic LLM Node

**Purpose:** send a prompt and a document to an LLM and receive a text
response. Designed for straightforward summarise/transform/extract tasks.

**Source tab:**

```
── Required Inputs ──────────────────
Prompt source:  Where the prompt comes from at execution time
[ Configured ▼ ]
  when Vault:               Prompt Vault key dropdown appears (typed)
  when Continue AI session: Session dropdown appears (ai_session-typed) —
                            the session's history replaces the prompt

── Optional Inputs ──────────────────
Document / context source:  Optional document appended to the prompt
[ Upstream payload ▼ ]
```

**Continue-mode edge case.** When `prompt_source` is `Continue AI session`,
the document input carries the new turn's text, so it becomes required: its
section header retitles `Optional Inputs → Required Inputs` (`section_when`),
it is marked required (`required_when`), and the user still chooses the document
source from the valid non-duplicate options. The kept
session's prior turns are sent as history and the document text is the next
user turn — an empty document is a clear error, not a silent nudge. These are
generic rule keys (see `NODE_HELPER.md`), so any future node can express the
same mode-driven required/section/lock behavior declaratively.

Dropdowns render full-width under a `label: description` header line so their
left edges align; single-line inputs stay inline.

**Parameters tab:**

```
Prompt (E to edit, ESC to finish)      ← visible only when source = Configured
[_________________________________]

Model *:        [ claude-opus-4-8 ▼ ]  ← curated dropdown, always editable
```

The model field is a **curated dropdown**, never free text. Options come from
the node's declared supported-model list, exposed through node metadata so the
frontend renders — never defines — the list. See the capability-based AI direction
in `NODE_CATALOG.md`.

**Payloads tab:**

```
── Downstream node payload ──────────
Result  [string]                        ← the designated downstream output
  Payload name: [Result_______________]  (hidden if forwarding)
  Description:  [Model response text___]
[ ] Forward incoming payload unchanged   (dead-drop; default off)

── Vault Payload ────────────────────
Result  [string]                        ← same Result, optionally duplicated
[x] Disable output                    ← Vault output is off by default
  Vault key:    [______________________]
  Description:  [______________________]

── AI Session ───────────────────────
[ ] Keep active AI session
    Session key: [________]            ← visible only when checked, and only
                                         when NOT continuing a session
```

`Result [string]` goes downstream by default: `transient_output=True`,
`dead_drop_passthrough=False`, `vault_write=False`, `vault_write_key=""`.
To also store the result, enable Vault output and set a key. Forwarding is
optional and independent of that write; it sends the incoming document (or
prompt when no document arrived) downstream instead of the result.

When "Keep active AI session" is checked **in Continue mode**, the resumed
session is the one extended — no new key is asked for (the session-key field
stays hidden), so the ongoing chat grows in place rather than forking a copy.

The AI Session section in the Payloads tab persists this node's session
onward (checkbox + key). *Continuing* a prior session is a Source-tab
concern: the "Continue AI session" prompt-source mode with its
`ai_session`-filtered dropdown (see the Source tab above).

**Data type:** string. Prompt, document, and LLM result are all strings.
Known incompatible Upstream edges can be validation warnings (`type_mismatch`);
a passing preflight does not prove that every runtime value has the expected shape.

**Notes:**
- Transient payloads are JSON so an LLM result can travel as transient when
  it only needs to reach the immediately next node. Check both Transient and
  Vault write to send the result downstream AND save it for other nodes or
  branches simultaneously.
- To forward the original while keeping the analysis, explicitly enable
  forwarding and Vault output and choose a Vault key. Neither is mandatory.

---

## Authoring Checklist

When defining a new node (prefer a helper spec — `NODE_HELPER.md` — so the
config UI comes for free):

- [ ] List every input and decide which source options it supports (Upstream /
      Vault / Configured). Document any inputs that are restricted to a subset.
- [ ] Pick the **one designated downstream output** and declare every port's
      `to` routing (`downstream` and/or `vault`), `pass_through` when the node
      can forward the incoming payload, and `vault_required` for vault writes
      that must not be disabled.
- [ ] Set the default routing state via `output_routing` (`default:
      transient|dead_drop`, `vault.mode: optional | default_on |
      required_unless_transient`).
- [ ] Identify which Parameters fields are conditional on Source tab selections
      and which are always editable.
- [ ] Confirm data types on every port — they drive the typed vault dropdown
      filtering and the `Name  [type]` labels throughout the UI.
- [ ] Use `repeatable_inputs` for bounded ordered input groups instead of
      custom config UI; execute them in numeric slot order.
- [ ] Express mode-driven variations declaratively with the dynamic rule keys
      (`visible_when`, `required_when`, `section_when`, `force_value_when`,
      `mutually_exclusive_with`) rather than custom screens.
- [ ] Note any vault writes that are required vs optional.
- [ ] Document the expected downstream pattern (e.g., "place a conditional
      branch after this node to branch on the bool output").
- [ ] Write `execute()` to read `<port>_source` / `<port>_vault_key` /
      `<port>` and route per `dead_drop_passthrough` and `vault_write` +
      `vault_write_key` (reference: `backend/nodes/chat_completion_node.py`).

### Routing previews (2026-10-08)

Start configures its greeting only in Parameters. Payloads displays a read-only
preview from `ui_hints.output_value_fields` and routing controls; legacy display
name overrides do not replace that value. This leaves room for future Start
parameters without duplicating value editors in the routing tab.

Text Output deliberately accepts `any` and formats it as text. A file reference
is printed as a reference, not dereferenced; use File Reader to obtain file
contents. Payloads shows source, label/template, a captured-value preview when
available, and connection-dependent continuation. No value is invented before
execution. End remains the explicit stop node.

## Portable contract and authoring boundaries

Consolidated from the standardization handoff and agent checklist. The owner
cancelled the proposed `category`/`family` rename on 2026-06-19: keep
`primary_family`, legacy class `category`, frontend `group` and
`selector_section`. Factory metadata provides compatibility aliases; don't
rewrite stored identity because an old example used the rejected vocabulary.
Five families are Inputs, Outputs, Flow Control, Utility and Complex. AI is a
search tag/capability, not a sixth family; rigid subcategory filters are retired.

Expose ports, data types, descriptions, required flags, supported sources,
routing destinations and capabilities through NodeFactory. Missing `data_type`
means `any`; missing `required` means optional. These describe capabilities,
not simultaneous actions or a guarantee that all validation is enforced today.
The selector shows the type's contract, while editor details show the configured
instance: actual producers/targets, port overrides and declared Vault effects.
One required/optional declaration should serve UI and validator, not separate
client guesses; see the Node Contract Plan for remaining conformance work.

Ordinary fields use `config_schema` and shared form rules. Structural sections
may derive Merge/Wait targets from topology, but nodes remain graph-ignorant.
Use backend `port_types` for producer/type tracing and `vault_declarations` for
reads/writes. Fixed forwarding must name its input and exclude the error port.
Multiple output ports alone do not imply `spawns_branches`; Merge ownership
must use the explicit capability. Dynamic ports use shared factory resolution.

The selector's master/detail contract and configured editor detail use shared
type/description helpers. Navigation groups are derived from metadata; a new
group member does not justify per-group screen code. Single-member groups can
be direct-add entries. Keep inspection read-only; path selection belongs in the
frontend and normalization/IO belongs at backend execution/validation boundaries.
Source, Parameters, Payloads and Connections are meanings, not four mandatory
tabs. Only expose operations the node actually implements. The UI reference
owns keyboard behavior and visibility/scrolling rules.

## File and window design decisions

Preserved from File Output D1–D12 (2026-07-11), with current representation
clarified. These are design constraints and reasons, not native verification.

| Decision | Rule and reason |
|---|---|
| D1 | Reuse RunSession for files/windows and cleanup; a second resource manager would duplicate ownership. |
| D2 | Pass tagged `file` reference objects, not handles. The path supports reconstruction in a later run; the live registration does not survive. JSON-safe identity keeps workflows portable. |
| D3 | Use semantic position/size presets rather than pixel coordinates, so monitor changes and future adapters do not require schema changes. Windows Terminal's pseudo-console is not the visible terminal; use real-host resolution or a warned monitor-relative fallback. |
| D4 | Discover at launch using visible-window differences, with a conservative unique-title fallback. Store the result once; do not repeatedly search by title. Ambiguity/discovery failure leaves the file opened but unplaced with a warning, never an arbitrary target. |
| D5 | Keep pywin32 optional and lazily guarded. It was chosen over verbose raw ctypes for maintainability of cold, native-only code. Unsupported placement degrades visibly; native support needs FO7, not Linux mocks. |
| D6 | Target the window for this file identity, never any window of an application. App-wide targeting can grab unrelated files/runs. |
| D7 | No virtual desktop integration in v1; undocumented OS internals add maintenance risk without serving the side-by-side/other-monitor use case. |
| D8 | Prefer the TUI viewer for text/Markdown; OS opening serves formats the terminal does not render. This yields a portable, testable path before native choreography. |
| D9 | Common write/open placement is declarative configuration. A separate small Window Control node handles mid-run focus/minimize/close; avoid five separate imperative node types. |
| D10 | OS opening/placement is an execution side effect behind a backend adapter, not Textual logic. Frontend supplies picker/preset affordances. |
| D11 | Window actions are local-display capabilities. A future remote backend needs a local effector behind a JSON event boundary; keep the adapter free of MasterState coupling so it can move. Do not open windows on a remote server and call them user output. |
| D12 | Windows left open at run end are handed to the user. Their registrations expire; later runs cannot adopt/control them without a separately designed rediscovery policy. |

File Manager displays files and passes references; File Reader copies file
contents into text; File Write writes content. Preserve those separate purposes
and existing internal type identifiers. References retain same-file identity;
forwarding changes downstream routing, not independent Vault writes. Quoted
copied paths remain configuration text, while `file_paths` normalizes at use
time; slash direction alone does not identify the runtime OS.

Migration reasons from the payload/file plan: preserve unknown keys, let explicit
new source choices win, archive retired completion flags rather than changing
meaning silently, and require correction where multiple legacy Text Output
Vault sources cannot be mapped to a single source. Do not repair loaded graphs
by inventing behavior in a rendering refresh. Shared config-migration code is
the authority for exact precedence and saved forms.

[Project Backlog](PROJECT_BACKLOG.md#native-filewindow-verification-fo7) retains
the manual FO7 protocol and deferred platform work. User-facing controls must
explain unsupported capabilities rather than promise silent success.

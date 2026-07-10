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

Apply this rule before touching the taxonomy in
`PHASE_17_NODE_VISUAL_IDENTITY.md`. Groups are a frontend-only navigation
concept — the backend never knows a group exists. Record every new node idea
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
`aotn_node_helper/specs/example_file_instance_node.yaml`.

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

Grey-out (`enabled_when`) is reserved for controls that are *locked*, not
irrelevant — e.g. the vault-write checkbox that cannot be unchecked while the
result is not routed transiently.

Some inputs may not offer all three options. For example, a document/context
input on a basic LLM node may only offer Upstream or Vault (no hard-configured
option — the document is always expected to come from a live data source).

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
   result, and the downstream name/description fields grey out.
3. **Vault Payload(s)** — for each output also routed to the Vault: an
   editable Vault key and description. Optional vault outputs carry a
   `[ ] Disable output` checkbox above them (checking it greys the key /
   description). A port is optional-to-vault unless its metadata sets
   `vault_required: true`.
4. Node-specific routing-adjacent sections (e.g. **AI Session**) follow.

An output may be **both** downstream and vault (`to: ["downstream", "vault"]`)
— e.g. an LLM node's `Result  [string]` is the downstream payload *and* is
optionally duplicated to the Vault, so it appears in both sections.

The old per-output `Transient output` / `Save to Vault` checkboxes are retired.
Config keys the composer reads/writes: `dead_drop_passthrough` (the checkbox),
`transient_output` (derived `= not dead_drop`), `transient_outputs` (downstream
name/description overrides), and `vault_write` / `vault_write_key` /
`vault_write_description` (the vault output; enabled unless disabled). Multiple
vault outputs on one node is a documented future extension — the single
`vault_write*` keys cover the current one-vault-output nodes.

Whenever a payload's data **name** appears in the UI (incoming or outgoing),
its data **type** is shown after it as a bracketed teal label —
`Result  [string]`.

### Branch Termination (output nodes)

Every output node carries a standard config option:

```
[ ] Terminate branch after completion
```

Default off. When enabled, the branch ends after the node completes — no
downstream connection is expected and the supervisor treats the path as
finished. This replaces the legacy standalone End node: branches end through
outputs (with this option), through merges, or through the silent **End
Branch** flow-control node for paths that intentionally discard a route.

Node authors: include this option on every Outputs-family node. It belongs in
the Payloads tab below the routing controls.

### Emitting Output in Code

Every node signals completion through `context.signal_done(payload)`. The
payload carries output under port names:

```python
await context.signal_done({"data": {"default": value}})
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

The practical reason to prefer Vault for large or shared data is **scope and
timing**, not size:

- A transient key is path-scoped. It is written by one node and consumed by
  the immediately downstream node that knows the source ID and port name.
  A parallel branch running concurrently will not have access to another
  branch's transient keys, and timing may not be correct if the write has not
  yet occurred.
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

## Typed Vault Outputs

Vault writes can carry an explicit `type` field alongside the value. The type
identities come from the canonical data-type vocabulary in
`backend/data_types.py` — the **single source of truth** shared with node port
data types so dropdown type-filtering between ports and vault keys stays
coherent (no parallel free-string vocabularies). Canonical set: `string`,
`number`, `bool`, `var`, `file`, `ai_session`, `any`.

> **Reconciliation (2026-06-19):** this list previously spelled the boolean
> type `boolean`. Per `NODE_STANDARDIZATION_HANDOFF.md` §5 the canonical
> spelling is now **`bool`**. `boolean` is accepted only as a deprecated alias
> (`data_types.canonicalize("boolean") == "bool"`) so older specs and saved
> workflows still resolve. `any` is the explicit permissive type — there is no
> silent "untyped" default.

`string`, `number`, and `bool` entries behave as before — pure JSON values
stored and read by name.

`file` and `ai_session` entries store a type tag and a string reference key.
The actual Python handle lives in `RunSession`, registered by the node that
opens or creates it:

```python
context.run_session.register_resource(ref_key, handle)
# write the reference to the vault
context.memory_bank.set(vault_key, {"type": "file", "ref_key": ref_key})
```

A downstream node that reads a `file` or `ai_session` vault entry retrieves
the handle through `get_resource`, which is already implemented on `RunSession`:

```python
handle = context.run_session.get_resource(ref_key)
```

The type tag tells the node and the framework which lookup path to use. From
the user's perspective this is invisible — they see `filename (file)` in the
Vault source dropdown.

Input source dropdowns type-filter automatically. An input declared as
accepting `file` shows only `file` vault entries; an LLM continuation input
shows only `ai_session` entries.

## AI Session Config-Driven Output (LLM Nodes)

There is no separate Chat Session Node. Any LLM node can opt into session
persistence via a config checkbox ("keep active AI session") and a
user-supplied session key.

When the checkbox is set and the node executes:

1. The node opens or retrieves a session handle (provider client + message
   history list) from `RunSession` under the session key.
2. It appends the current turn and runs inference.
3. It registers the updated session handle back in `RunSession`.
4. It writes `{"type": "ai_session", "ref_key": <session_key>}` to the vault
   under the session key.

The first LLM node with a given session key starts the session. All subsequent
nodes that select the same vault key from their source dropdown continue it.
Message history lives in the session object in `RunSession`; `MemoryBank`
holds only the type tag and reference key.

Downstream LLM nodes that want to continue a session:
- Select the vault source for their chat input.
- See `chat_name (ai_session)` in the type-filtered dropdown.
- Retrieve the session via `context.run_session.get_resource(session_key)`,
  append their turn, and re-register the handle.

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
See the AI Model Approach section of `PHASE_17_NODE_VISUAL_IDENTITY.md`.

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

## Standard Config Tabs

Every node config screen uses these tabs in order. Not all tabs need to be
present for every node.

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

### Payloads Tab

Built from `output_port_metadata` per the Standard Output Routing Model above:

```
── Downstream node payload ──────────
Result  [string]
  Payload name: [Result_______________]   greys out when forwarding
  Description:  [Model response text___]

[ ] Forward incoming payload unchanged

── Vault Payload ────────────────────
Result  [string]
[ ] Disable output                        (optional vault outputs only)
  Vault key:    [chat_result___________]   greys out when disabled
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

Read-only topology view showing current input and output connection wiring.
Managed by the editor, not by the user through this tab directly.

---

## Reference Example — File Instance Node

**Purpose:** open a file at a given path and make it available for downstream
nodes. Outputs a success/failure boolean.

**Source tab:**

```
File path source
  ( ) Upstream payload    ← receives path string from previous node
  ( ) Vault               Key: ________
  (x) Configured          ← default; activates path field in Parameters
```

**Parameters tab:**

```
File path:  [________________________]   ← hidden unless source = Configured
```

**Payloads tab:**

```
── Downstream node payload ──────────
Open Result (bool)                     (true = opened, false = error)
  Payload name: [Open Result__________]
  Description:  [True when the file opened successfully]
[ ] Forward incoming payload unchanged

── Vault Payload ────────────────────
Open Result (bool)
[x] Disable output                     (error-log vault write is optional,
  Vault key:    [____________________]  disabled until the user enables it)
  Description:  [____________________]
```

**Notes:**
- The bool output is the natural signal for a conditional branch placed
  immediately after: the `true` path continues normal execution, the `false`
  path handles the error, optionally reading the error message from the Vault
  key configured above.
- The path input is the only input. There is no document or context input.

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
frontend renders — never defines — the list. See the AI Model Approach section
of `PHASE_17_NODE_VISUAL_IDENTITY.md`.

**Payloads tab:**

```
── Downstream node payload ──────────
Result  [string]                        ← the designated downstream output
  Payload name: [Result_______________]  (greys out if forwarding)
  Description:  [Model response text___]
[ ] Forward incoming payload unchanged   (dead-drop; default off)

── Vault Payload ────────────────────
Result  [string]                        ← same Result, optionally duplicated
[ ] Disable output
  Vault key:    [chat_result___________]
  Description:  [______________________]

── AI Session ───────────────────────
[ ] Keep active AI session
    Session key: [________]            ← visible only when checked, and only
                                         when NOT continuing a session
```

`Result  [string]` is the designated downstream payload (dead-drop off by
default, so the Result flows to the next node) and is also duplicated to the
Vault by default (disable via the checkbox).

When "Keep active AI session" is checked **in Continue mode**, the resumed
session is the one extended — no new key is asked for (the session-key field
stays hidden), so the ongoing chat grows in place rather than forking a copy.

The AI Session section in the Payloads tab persists this node's session
onward (checkbox + key). *Continuing* a prior session is a Source-tab
concern: the "Continue AI session" prompt-source mode with its
`ai_session`-filtered dropdown (see the Source tab above).

**Data type:** string. Prompt, document, and LLM result are all strings.
Incompatible data types are a validation error.

**Notes:**
- Transient payloads are JSON so an LLM result can travel as transient when
  it only needs to reach the immediately next node. Check both Transient and
  Vault write to send the result downstream AND save it for other nodes or
  branches simultaneously.
- Dead-drop passthrough is the default because many pipeline stages want to
  forward the original document unchanged while writing the LLM analysis to
  the Vault separately. Useful for incremental document modification workflows
  where the branch modifies a document pass-by-pass and does not need the
  original preserved.
- Vault write cannot be disabled unless Transient output is checked; otherwise
  the LLM result would be silently discarded with no durable record.

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
- [ ] Express mode-driven variations declaratively with the dynamic rule keys
      (`visible_when`, `required_when`, `section_when`, `force_value_when`,
      `mutually_exclusive_with`) rather than custom screens.
- [ ] Note any vault writes that are required vs optional.
- [ ] Document the expected downstream pattern (e.g., "place a conditional
      branch after this node to branch on the bool output").
- [ ] Write `execute()` to read `<port>_source` / `<port>_vault_key` /
      `<port>` and route per `dead_drop_passthrough` and `vault_write` +
      `vault_write_key` (reference: `backend/nodes/chat_completion_node.py`).

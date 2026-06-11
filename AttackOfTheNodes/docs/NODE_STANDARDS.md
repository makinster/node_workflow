# Node Design Standards

**Status:** Design reference — in-progress draft as of 2026-06-11.
This document captures the intended scope, input/output patterns, and UI
behavior rules for AttackOfTheNodes nodes. It is the authoritative reference
before authoring a new node type or changing an existing one's I/O model.

## Core Principle

Nodes have predetermined input and output configurations with limited, known
flexibility. The flexibility that exists is expressed through a standard source
and routing model — not through open-ended custom config. A node author defines
which inputs and outputs the node has; users configure how data reaches and
leaves those fixed ports.

## Standard Input Source Model

Every node input that can accept external data offers up to three source
options. These options are mutually exclusive per input — selecting one
disables the others in the UI.

| Source option | What it means |
|---|---|
| **Upstream (transient)** | Read the dead-drop payload arriving on the connected input port from the previous node in the execution path. |
| **Vault** | Read a named variable from the MemoryBank. User provides the variable key. |
| **Configured** | Read a value entered directly in the Parameters tab. No live connection required. |

When **Upstream** is selected: the Vault key field and the Parameters config
field for that input both grey out.

When **Vault** is selected: the transient connection hint and the Parameters
config field for that input both grey out.

When **Configured** is selected: the transient and Vault fields grey out. The
corresponding Parameters tab field becomes active and editable.

Some inputs may not offer all three options. For example, a document/context
input on a basic LLM node may only offer Upstream or Vault (no hard-configured
option — the document is always expected to come from a live data source).

## Standard Output Routing Model

Every node output that produces data offers the following routing options in
the Payloads tab. Options are not always mutually exclusive — see per-node
rules below.

| Routing option | What it means |
|---|---|
| **Transient output** | Send the node's result to the next connected node as the dead-drop payload on the output port. |
| **Dead-drop passthrough** | Forward the incoming transient payload unchanged. The node's own computed result is not sent downstream; the payload that arrived is passed through as-is. |
| **Vault write** | Save the node's result to the MemoryBank under a user-provided variable key. |

**Transient output vs dead-drop passthrough** are typically mutually exclusive:
a node either outputs its own result or passes through the incoming payload —
not both on the same port. When dead-drop passthrough is active, transient
output is effectively disabled (no new payload is pushed; the existing one
flows forward).

**Vault write** is usually independent. A node can write to the Vault and also
send a transient output, or write to the Vault and use dead-drop passthrough.
Vault writes are optional unless the node type requires it.

## Data Type Scope

**Transient payloads carry lightweight conditional data:**
- Booleans (success/failure flags, branch decisions)
- Counters and integers
- Short variable strings (keys, labels, status codes)
- Simple structured values for conditional logic

**Vault carries heavy or shared data:**
- Large strings, document text, AI responses
- File contents and accumulated data
- Any value that needs to be shared across branches or accessed by multiple
  downstream nodes

**File I/O handles file system interaction:**
- File paths are config values; actual file access happens through the
  `RunSession` at execution time.

Nodes that accept or produce large text content should use Vault inputs and
outputs as the primary data path. Transient connections for those nodes carry
only control-flow signals (booleans, status), not the bulk data.

## Standard Config Tabs

Every node config screen uses these tabs in order. Not all tabs need to be
present for every node.

### Source Tab

Declares where each input comes from. Contains one or more input-source
selector groups:

```
[Input name]
  ( ) Upstream payload      [preview button]
  ( ) Vault  Key: ________
  ( ) Configured            → activates the field in Parameters tab
```

Radio-button style: selecting one option within a group disables the other
two in that group. When Configured is selected, the matching Parameters field
becomes editable; otherwise it is greyed out.

For inputs with only two valid source options (e.g., Upstream or Vault only),
show only those two. Do not show a Configured option if hard-coding is not
valid for that input.

### Parameters Tab

Contains node-specific configuration values that are either always editable
(fixed node settings) or conditionally editable based on Source tab selections.

Fields linked to a Source tab selector are greyed out when that input source
is set to Upstream or Vault, and become active when set to Configured.
Fields that are always editable (such as temperature, model name, or mode
flags) are never greyed out by source selection.

### Payloads Tab

Declares how the node's output is routed. Contains output routing controls:

```
Transient output
  [ ] Send result to next node

Dead-drop passthrough
  [x] Forward incoming payload unchanged (ignores computed result)

Vault write
  [x] Save result to Vault  Key: ________
```

Transient and dead-drop passthrough are mutually exclusive: checking one
unchecks the other. Vault write is independent.

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
File path:  [________________________]   ← greyed out if source ≠ Configured
```

**Payloads tab:**

```
Transient output
  [x] Send bool result to next node  (true = opened successfully, false = error)

Dead-drop passthrough
  [ ] Forward incoming payload unchanged

Vault write — error log (optional)
  [ ] Save error message to Vault  Key: ________
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
Prompt source
  ( ) Upstream payload    ← receives prompt string from previous node
  ( ) Vault               Key: ________
  ( ) Configured          ← activates prompt field in Parameters

Document / context source  (required — one source must be selected)
  ( ) Upstream payload
  ( ) Vault               Key: ________
  [no Configured option — document must come from a live source]
```

**Parameters tab:**

```
Prompt:  [_________________________]   ← editable only when source = Configured
                                         greyed out otherwise

Model:   [_________________________]   ← always editable
```

**Payloads tab:**

```
Transient output
  [ ] Send LLM result to next node     ← unchecking this forces dead-drop below

Dead-drop passthrough
  [x] Forward incoming payload unchanged (default)
      ↑ unchecked automatically when Transient output is checked

Vault write — result
  [x] Save LLM result to Vault  Key: ________   ← default checked
      Cannot be unchecked unless Transient output is checked.
```

**Data type:** string / text only. Both the prompt and document inputs and the
LLM result output are text. Incompatible data types are a validation error.

**Notes:**
- Vault write is the primary durable output path for LLM results. Most
  downstream nodes read LLM output from the Vault, not from a transient
  connection — consistent with the heavy-data-in-Vault rule.
- Dead-drop passthrough is on by default because many pipeline stages want to
  forward the original document unchanged while writing the LLM analysis to
  the Vault separately.
- Vault write cannot be disabled unless the result is being forwarded as a
  transient output; otherwise the result would be silently discarded.

---

## Authoring Checklist

When defining a new node:

- [ ] List every input and decide which source options it supports (Upstream /
      Vault / Configured). Document any inputs that are restricted to a subset.
- [ ] List every output and define the default routing state (transient,
      dead-drop, vault write) and which options the user can change.
- [ ] Identify which Parameters fields are conditional on Source tab selections
      and which are always editable.
- [ ] Confirm data types: transient payloads carry only lightweight values;
      large content uses Vault.
- [ ] Define the mutual-exclusion rules for the Payloads tab.
- [ ] Note any vault writes that are required vs optional and any that cannot
      be disabled under certain conditions.
- [ ] Document the expected downstream pattern (e.g., "place a conditional
      branch after this node to branch on the bool output").

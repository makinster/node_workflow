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

**Helper support (2026-06-12):** the node helper expands this model
automatically. Declare `input_sources` and `output_routing` sections in a
helper spec and the generator emits the source selectors, gated Vault key and
parameter fields, and the mutually exclusive transient/dead-drop pair —
including the dynamic greying rules described below, which `NodeConfigScreen`
now applies live through the generic schema keys `enabled_when`,
`visible_when`, and `mutually_exclusive_with`. See `NODE_HELPER.md` and
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
the Payloads tab.

| Routing option | What it means |
|---|---|
| **Transient output** | Send the node's result to the next connected node as the dead-drop payload on the output port. Written to MemoryBank under the ephemeral `(node_id, port_name)` key. |
| **Dead-drop passthrough** | Forward the incoming transient payload unchanged. The node's own computed result is not pushed to the transient port; the payload that arrived is passed through as-is. |
| **Vault write** | Save the node's result to the MemoryBank persistent store under a user-provided variable key. Independent of transient routing. |

**The one mutual exclusion:** Transient output (send my result) and Dead-drop
passthrough (forward incoming payload unchanged) are mutually exclusive on the
same port — only one thing can occupy the transient path. Checking one
unchecks the other.

**Transient and Vault write are not mutually exclusive.** A node can send its
result as both a transient payload to the next node AND write it to the Vault
simultaneously. This is useful when downstream nodes on the same path need the
result immediately via transient, while other branches or later nodes access it
via the stable Vault key.

**Dead-drop and Vault write can also be combined.** A node can pass the
incoming transient payload unchanged while writing its own computed result
separately to the Vault. For example, a file instance node that passes through
the path string as transient (for the next node to use) while writing its
operation result or error message to a Vault key for error-reporting purposes.

Vault writes are optional unless the node type requires durable output (e.g.,
an LLM node where losing the result on session close is unacceptable).

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
  [ ] Send result to next node    ──┐ mutually exclusive:
                                    │ only one can occupy the transient port
Dead-drop passthrough               │
  [x] Forward incoming payload  ───┘

Vault write  (independent of the above)
  [x] Save result to Vault  Key: ________
```

Transient output and dead-drop passthrough are mutually exclusive: checking
one unchecks the other. Vault write is independent and can be combined with
either transient option.

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
  [ ] Send LLM result to next node     ← can be checked alongside Vault write

Dead-drop passthrough
  [x] Forward incoming payload unchanged (default)
      ↑ unchecked automatically when Transient output is checked

Vault write — result
  [x] Save LLM result to Vault  Key: ________   ← default checked
      Cannot be unchecked unless Transient output is checked.
```

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

When defining a new node:

- [ ] List every input and decide which source options it supports (Upstream /
      Vault / Configured). Document any inputs that are restricted to a subset.
- [ ] List every output and define the default routing state (transient,
      dead-drop, vault write) and which options the user can change.
- [ ] Identify which Parameters fields are conditional on Source tab selections
      and which are always editable.
- [ ] Confirm data types: transient payloads are JSON and can carry any
      serializable value. Use Vault when data must cross branch boundaries,
      be accumulated over time, or be accessed by nodes not in the immediate
      execution chain.
- [ ] Define the mutual-exclusion rules for the Payloads tab.
- [ ] Note any vault writes that are required vs optional and any that cannot
      be disabled under certain conditions.
- [ ] Document the expected downstream pattern (e.g., "place a conditional
      branch after this node to branch on the bool output").

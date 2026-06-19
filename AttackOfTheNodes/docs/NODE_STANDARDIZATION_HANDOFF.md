# Node Standardization Handoff

**Status:** Adopted — §2 decisions signed off 2026-06-19. Implementation-ready;
folds into `NODE_STANDARDS.md`, `PHASE_17_NODE_VISUAL_IDENTITY.md`, and
`NODE_HELPER.md` per §11.
**Audience:** Coding agents (Claude / Codex) implementing across backend, the
node helper, and the frontend selector.
**Relationship to existing docs:** This consolidates a design discussion into an
implementation plan. It does not replace `NODE_STANDARDS.md`,
`PHASE_17_NODE_VISUAL_IDENTITY.md`, or `NODE_HELPER.md` — it specifies the
changes to fold *into* them. Now that it is adopted, update those docs and add a
row to the README Document Directory + an entry in `DOCS_MIGRATION_NOTES.md`.

---

## 1. What this changes, in one paragraph

Every node gains a single authoritative **I/O contract** declared on the node and
exposed through `NodeFactory`: a description, a required/optional split of inputs
and outputs, a data type and human description per port, allowed sources per
input and routing destinations per output, and a default alias. The frontend
renders that one contract everywhere — the selector detail panel, the group/
family detail, and the config-screen field labels — so there is no parallel
hand-maintained copy. The node taxonomy terminology is realigned to
**Category > Family > Type** to remove the family/type/group/subcategory naming
collisions. The node helper spec is unified so authors declare this once and get
the UI for free.

---

## 2. Decisions — all locked

**Original locked set (carry into implementation):**

- Coarse data-type vocabulary, shared with typed vault entries (see §5).
- Every port declares a type; `any` is an explicit, permissive type — there is
  no silent "untyped" default.
- `text_small`/`text_large` are **not** types. Text is `string`; size is at most
  a rendering hint on a configured field, decoupled from the type.
- Required/optional is a symmetric split across both inputs and outputs, driven
  by a per-port `required` flag.
- Unified `inputs:` / `outputs:` helper spec blocks (replacing the split
  `input_sources` / `output_port_metadata` sections).
- The selector uses a master-detail layout: list on the left, live contract
  detail panel on the right.

**Resolved 2026-06-19 (formerly open; owner sign-off received):**

1. **Terminology rename — approved, reusing `category`.** Adopt Category >
   Family > Type (§3). The canonical top-tier metadata key is the **existing**
   `category` key already exposed by `NodeFactory` — **not** a new
   `primary_category`. Make `category` authoritative, **retire** the
   `primary_family` and `legacy_category` aliases, and rename `group → family`.
   `type` is untouched. This avoids introducing a third synonym and aligns with
   the helper spec, which already declares `category:` (§7).
2. **Family navigation — drill-in.** Select a family → the list swaps to its
   members → a back affordance returns. Composes with the existing Phase 17
   group-picker modal and single-member auto-promotion (§9).
3. **Multi-port `to:` display — one line per port.** Each named output port is
   rendered distinctly in the detail panel, per the §8 render spec. Nothing about
   a node's outputs is collapsed or hidden.
4. **Behavior badge — none.** No behavior-trait badge on the node card; the
   one-line description carries behavior. The retired subcategory/`tags` scheme
   is not reintroduced in any form (§3). The separate required-setup indicator
   (§6) is unaffected — it reflects validity, not behavior.

---

## 3. Terminology realignment: Category > Family > Type

The concepts are sound; the names collide. `type` is already the registered
node identity throughout the backend, helper specs (`node_type:`),
`check_node.py <type>`, and the registry — so it must **not** be repurposed for
the top-level buckets. Realign as:

| Tier | Meaning | Current term | Proposed term | Layer |
|---|---|---|---|---|
| Top bucket / selector tab | IO, Flow Control, Utility, Complex | `primary_family` | **Category** — canonical `category` key; retire `primary_family`/`legacy_category` aliases (§2.1) | Backend-exposed identity |
| Grouping of sibling variants | Branch family, User Input family | `group` | **Family** | Frontend-only navigation |
| Concrete registered node | number-comparison-branch | node `type` | **Type** (unchanged) | Backend identity |

Reads naturally: "the *number-comparison-branch* **type**, in the *Branch*
**family**, under the *Flow Control* **category**."

- **Family is optional.** A standalone node attaches directly to its category
  with no family (the existing direct-add rule).
- **`selector_section`** (in-tab headers like "Text & Data / Files / AI") stays a
  frontend-only display device *within* a category tab. It is presentation sugar,
  not part of the Category/Family/Type identity spine.
- **Subcategory / `tags` (behavioral taxonomy) is retired.** Most of what it
  encoded is derivable from family + the contract: "active" = a User Input family
  node; "parallel" = inherent to branch types; "passive" = the default and
  uninformative. Retiring it also resolves the "Utility is both a category and a
  subcategory" clash. A freeform `tags` field *may* survive as loose filter
  keywords — but the rigid active/passive/parallel scheme should not be
  reintroduced. (Per §2.4, no behavior badge is added either.)

**Rename surface (resolved — reuse `category`, §2.1):** make the existing
`category` key canonical for the top tier and **retire** the `primary_family`
and `legacy_category` aliases (node class metadata + `NodeFactory` + helper specs
that declare it); rename `group → family` (frontend-only navigation + the `group`
metadata field). `type` is untouched. Do this as a single mechanical pass with
tests green before/after; it is not an execution-semantics change.

---

## 4. The node I/O contract (authoritative shape)

Declared on the node, exposed via `NodeFactory`, rendered by the frontend. Per
node:

- **Description** — one line: what the node does.
- **Default alias** — overridable per instance.
- **Required Input(s)** / **Optional Input(s)** — each port:
  - name, data type (§5), `from:` allowed sources, description, `required: bool`
- **Output(s)** / **Optional Output(s)** — each port:
  - name, data type, `to:` routing destination(s), description, `required: bool`
  - the **Pass-thru payload** line appears here when dead-drop passthrough is
    offered

**Default upstream-payload description propagation.** Each output port carries a
default human description (e.g. an LLM node's output is "LLM Response"). When a
downstream node's input is set to Upstream, the config screen walks the topology,
finds the connected upstream output, and displays *its* description as the
default label — overridable, never required. The node advertises static metadata
only; the frontend does the topology walk and rendering. No node inspects
frontend state; the backend does not render.

**Capabilities, not simultaneous actions.** The detail panel advertises what a
node *can* do. A node may list both a transient result and a Pass-thru payload
even though transient output and dead-drop passthrough are mutually exclusive
per port at runtime. The panel = "what this node can do"; config = "what this
instance does," where the exclusion is enforced. Render the panel accordingly —
do not imply both happen at once.

---

## 5. Canonical data-type vocabulary

One extensible list, defined in a single backend module, shared by **port data
types and typed vault-entry types** so dropdown filtering during config is
coherent (both sides must reference the same identities; free strings drift and
break filtering). The helper warns on unknown types.

Starting set: `string`, `number`, `bool`, `var`, `file`, `ai_session`, `any`.

- Aligns with the existing typed-vault decision (`string`, `number`, `boolean`,
  `file`, `ai_session`) — reconcile the two lists into one canonical source
  rather than maintaining parallel vocabularies.
- `file` and `ai_session` are reference types: the value is a ref key; the real
  handle lives in `RunSession`.
- The type drives (a) dropdown filtering of compatible upstream ports / vault
  keys during config, and (b) optional soft validation warnings. It is a
  semantic/UX convention, not a hard runtime type — runtime data is JSON + refs.

---

## 6. Required-input validity flag

One declaration, two consumers — author once:

- **Backend validator** reads `required` to mark a node incomplete when a
  required input has no assigned source (same surface as loose-end detection).
- **Frontend** reads the same flag to color config fields and badge the node as
  needing setup.

Boundary stays clean: backend computes validity; frontend renders the indicator.

**Forward compatibility (do this now even if UI consumption is deferred).** Add
the `required` / `data_type` / `description` fields to the contract schema now
with documented defaults so older node files and saved workflows still load:
absent `required` ⇒ optional; absent `data_type` ⇒ `any`. Freezing the format
early avoids a second format churn when the colored indicators land.

---

## 7. Unified helper spec shape

Replace the split `input_sources` + `output_port_metadata` sections with unified
`inputs:` / `outputs:` blocks carrying the full per-port contract. The generator
still emits the Source/Parameters/Payloads selectors and the dynamic greying
(`enabled_when` / `visible_when` / `mutually_exclusive_with`) from this richer
declaration.

Illustrative shape (final keys to be fixed when the helper is edited — confirm
against `NODE_HELPER.md` at implementation time). Note `category:` is the
canonical top-tier key per §2.1:

```yaml
node_type: prompted_llm_node
class_name: PromptedLlmNode
category: Complex            # canonical top-tier key (was: primary_family)
family: AI Processing        # was: group (frontend-only)
display_name: Prompted LLM
default_alias: LLM Response
description: Prompted LLM response / document analysis
inputs:
  text_prompt:
    type: string
    required: true
    sources: ["upstream", "vault", "configured"]
    description: The starter prompt for the LLM chat
    parameter: { type: string, label: Prompt }   # required when 'configured' allowed
  document:
    type: string
    required: false
    sources: ["vault"]
    description: Optional document appended after the prompt
outputs:
  response:
    type: string
    required: true
    to: ["vault"]
    description: LLM chat response
  result:
    type: bool
    required: false
    to: ["downstream"]
    description: Signals success or failure of the LLM API response
  passthrough:
    type: any
    required: false
    to: ["downstream"]
    pass_through: true        # the dead-drop passthrough line
```

The generator/check scripts (`create_node.py`, `check_node.py <type>`,
`check_ui.py <type>`) and the generated tests move together with this schema
change. Structural nodes (`branch_node`, `merge_node`, etc.) keep their custom
topology authoring but should still expose the same contract metadata for the
detail panel.

---

## 8. Detail-panel render spec (selector right panel)

Rendered from the §4 contract. Sections in order, each a list; empty sections
show *none* (italic):

```
<Type display name> — <description>
Required Input(s):
  <Name> (<type>) from: [<sources>]
  Desc: <description>
Optional Input(s):
  <Name> (<type>) from: [<sources>]
  Desc: <description>
Output(s):
  <Name> (<type>) to: [<destinations>]
  Desc: <description>
Optional Output(s):
  <Name> (<type>) to: [<destinations>]
  Desc: <description>
  Pass-thru payload [downstream]
```

- `from:` = allowed input sources; shorthand `all` = upstream + vault +
  configured.
- `to:` = routing destinations: `downstream` (transient), `vault`, and the
  **Pass-thru payload** line for dead-drop passthrough. Multiple named output
  ports are each rendered on their own line (§2.3 resolved — one line per port).
- Render as capabilities, not simultaneous actions (§4).

The same render is reused for **family detail** (when a family is highlighted,
show the family description; per-member, show the member's contract) and to
source **config-screen field labels**.

---

## 9. Selector navigation layout

- **Master-detail.** Horizontal split: list left (`OptionList` / `ListView`),
  contract detail panel right. The list's highlight message
  (`OptionHighlighted` / `Highlighted`) drives a rerender of the right panel.
  This is the intended use of those widgets — standard Textual master-detail.
- **Tabs vs split.** The selector keeps the four **Category** tabs
  (`TabbedContent` / `TabPane`); a master-detail split lives inside each pane.
  Keep the *selector* (pick a node to add) conceptually separate from the
  *config screen* (numbered Source/Parameters/Payloads tabs for a placed node) —
  they share the detail idiom but are different screens.
- **Family navigation (resolved §2.2 — drill-in).** Select a family → the list
  swaps to its members → a back affordance returns to the family list. The detail
  panel shows the family description while a family is highlighted, and the
  member's contract once a member is highlighted. A real Family tier likely
  absorbs most existing pre-dropdown filters, since Family already narrows scope.
- Reconcile with the existing Phase 17 group-picker design: the generic Group
  Picker modal and single-member auto-promotion still apply; "group" there is
  the same concept being renamed to "family."

---

## 10. Boundary summary

| Concept | Layer | Rule |
|---|---|---|
| Category (`category`) | Backend-exposed identity | Frontend reads it for tab placement; no backend component branches execution on it |
| Family | Frontend-only navigation | Backend never knows a family exists |
| Type | Backend identity | The concrete registered node |
| I/O contract (ports, types, sources, routing, descriptions, required) | Backend-exposed metadata | Node advertises; frontend renders; node never inspects frontend; backend never renders |
| Upstream-payload description propagation | Frontend reads backend topology + metadata | Frontend does the walk + render; node advertises only its own output description |
| Required-input validity | Backend computes; frontend renders | One `required` flag, two consumers |

---

## 11. Suggested work split and sequencing

Two agents work concurrently on different branches — sequence to minimize
collisions on shared infra (the helper).

**Track A — backend + helper (do first; shared infra):**

1. Canonical data-type module (§5), reconciled with typed-vault types.
2. Contract schema fields on node classes + `NodeFactory` exposure (§4, §6),
   additive with defaults.
3. Unified `inputs:`/`outputs:` helper spec + generators + check scripts +
   generated tests (§7). Regenerate **one** reference node as the template;
   defer mass regeneration.
4. Terminology rename: make `category` canonical + retire `primary_family` /
   `legacy_category` aliases, `group → family` (§3) — owner sign-off received
   (§2.1); run as one mechanical pass with tests green before/after.

**Track B — frontend (can start against the exposed metadata once Track A step 2
lands):**

5. Detail-panel renderer from the contract (§8).
6. Master-detail selector layout + drill-in family navigation (§9, §2.2).
7. Config-screen labels + dropdown type-filtering + required-field coloring
   sourced from the same metadata.

**Verification (from `AttackOfTheNodes/`):**

- `../.venv/bin/python -m compileall -q .`
- `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v` before shared
  commits; narrow `pytest -k` for small fixes.
- Helper flow per node: spec → `create_node.py` → `check_node.py <type>` →
  `check_ui.py <type>`.
- `git diff --check` for docs.

**Docs to update when this lands:** `NODE_STANDARDS.md` (contract + type vocab +
required flag), `NODE_HELPER.md` (unified spec), `PHASE_17_NODE_VISUAL_IDENTITY.md`
(terminology + detail panel + family nav), `PROJECT_KNOWLEDGE.md` (terminology
rename; taxonomy already reconciled 2026-06-19 — see audit), `TUI_DESIGN.md`
(selector master-detail), `NODE_CATALOG.md` (family relabeling), plus README
Document Directory + `DOCS_MIGRATION_NOTES.md`.

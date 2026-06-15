# Phase 17 - Node Visual Identity And Selector Taxonomy

**Status:** In progress
**Last updated:** 2026-06-15 (editor node rows use Textual ASCII text-box
borders; taxonomy revision remains I/O tab + switch, Utility family, in-list
section headers, AI-as-subcategory)

Phase 17 is not just a cosmetic row-color pass. It is the foundation for the
next node overhaul: clearer node families, reusable subcategory tags, a more
useful node selector, and editor rows that communicate node identity at a
glance without changing runtime behavior.

The current runtime nodes may be redone as this taxonomy settles. Treat existing
node types as implementation inventory, not the final user-facing library.
The complete node inventory — implemented, planned, deferred, and concept —
lives in `NODE_CATALOG.md`.

## User Experience Goal

Users should be able to answer three questions quickly:

- What kind of node is this?
- What capabilities or concerns does it involve?
- Is it quiet utility plumbing, workflow structure, user-facing output, or a
  complex behavior that deserves extra attention?

The selector and editor should use the same language. If a node appears under
the `I/O` tab's Input side with the `File I/O` filter, the editor details
panel should show the same family and subcategories after the node is added.

## Core Simplification Rule

Before placing any node behind a group picker, apply this rule:

| Situation | Solution |
|---|---|
| Variants have different port shapes | Must be separate node types regardless |
| Variants have same ports, very different config | Group with picker |
| Variants are minor config differences with same ports | One node + mode select field |
| Standalone, unique node | Direct-add, no group |

This prevents groups from becoming junk drawers and keeps the number of real
node types honest.

**Example applications:**

- **File Write overwrite vs append** — same ports, one config field → single
  node with a mode select. No separate type needed.
- **Branch variants** — different port shapes (2 ports vs N ports vs loop
  shape) → must be separate node types.
- **Email vs Webhook vs OS notification** — same ports, radically different
  config → group with picker.

Apply this rule before adding any node to `NODE_CATALOG.md` or to the selector.
The rule is also documented in `NODE_STANDARDS.md` as the Node Type
Classification guide.

## Primary Node Families

Each node has one primary family. Families are backend metadata
(`primary_family`); how families map onto selector tabs is a frontend
presentation decision (see Node Selector UX).

| Family | Meaning | Examples |
|---|---|---|
| Inputs | Get data into the workflow from an external source. | User Text Input, File Read, Data Source, AI Input (session seeding) |
| Outputs | Send workflow results to the user, a file, or another system. | Text Output, File Write, Send/Notify, User-Facing Prompt |
| Flow Control | Change workflow structure: branching, merging, waiting, branch termination. | Branch, Merge, Merge Beacon, End Branch, Wait/Timer |
| Utility | Perform custom actions mid-workflow: automation, data transform, debug/log helpers, loop helpers. A working catch-all for action nodes. | UI Automation, Data Transform, Echo, Probe, Counter |
| Complex | Nested workflows, AI processing tools, and triggers — structurally unusual nodes. | AI Processing, Subworkflow, Trigger |

Notes:

- **Five families, four tabs.** `Inputs` and `Outputs` share the frontend
  `I/O` tab behind an Input/Output switch. The backend never knows about the
  switch — it is purely presentation.
- **AI is a subcategory, not a family.** AI-flavored variants live in their
  natural family: AI Conditional Branch in Flow Control's Branch group,
  AI-Guided Read in the File Reader group, AI Input on the I/O Input side.
  Dedicated AI tooling (Chat Completion, Image Generation, Embedding) lives in
  Complex under the AI Processing group, where the `AI` filter surfaces it.
- `Complex` is a pressure-release family, not a junk drawer. Action-style
  nodes belong in `Utility`; data-in/data-out nodes belong in `Inputs`/`Outputs`.

## Start, End, And Branch Termination

Settled 2026-06-12:

- **Start is never user-addable.** The runtime `start_node` is auto-generated.
- **There is no standalone End node.** Branches terminate three ways:
  1. through an output node with the standard **"Terminate branch after
     completion"** config option enabled (see `NODE_STANDARDS.md`);
  2. through a merge (the branch ends by joining);
  3. through the **End Branch** direct-add node — a silent terminator for
     paths that intentionally discard a route (e.g. the "no" path of a
     conditional branch that should do nothing).

## Taxonomy Summary

Full node-by-node detail (with status) is in `NODE_CATALOG.md`. The structure:

| Tab | Sections | Groups and direct-adds |
|---|---|---|
| **I/O — Input** | Text & Data, Files, AI | Text Input ▸, Data Source ▸, File Reader ▸, AI Input |
| **I/O — Output** | (flat — short list) | Text Output ▸, File Write ▸, Send/Notify ▸, User-Facing Prompt ▸ |
| **Flow Control** | Branching, Timing | Branch ▸, Merge ▸, Merge Beacon, End Branch, Wait/Timer ▸ |
| **Utility** | Automation, Transform, Debug, Loop Helpers | UI Automation ▸, Script Runner ▸ (gated), Data Transform ▸, Echo, Probe, Logger, Sleep/Delay, Counter, Accumulator, Repeat Limiter |
| **Complex** | AI, Workflow, Triggers | AI Processing ▸, Subworkflow ▸, Trigger ▸ |

`▸` marks a group (opens the Group Picker). Plain entries are direct-add.

## AI Model Approach

AI nodes generalize around **capability**, not model identity. Each AI node
declares a **curated supported-model list** — not an open-ended model field —
because prompt adherence, tool support, and structured output must be as
dependable as possible:

- Conversational nodes (AI Input, Chat Completion) need coherent multi-turn
  behavior — a moderately strict list.
- Structured-decision nodes (AI Conditional Branch, AI Tool Call, AI Decision)
  require reliable structured output (tool calling or JSON mode). The AI
  selects from defined branch labels/schemas and cannot invent a path. These
  carry the strictest supported lists.

**Future fork point:** if the supported-model list grows large and models
diverge in capability, AI Processing may split into per-model groups (one
group per model family, since each has its own capabilities). Capability
grouping is the contract until that pressure is real. `NODE_CATALOG.md`
carries the same note next to the AI Processing group.

## Full Expanded Taxonomy

This is the target node library. It is not all implemented today. Treat it as
the design contract for the node overhaul. Groups shown below produce a Group
Picker in the selector; nodes marked *direct-add* or structurally unique appear
directly in the list with no picker.

### INPUTS

**Text Input →** *(group with picker)*
- **User Text Input** — prompt user at runtime; blocks until answered
- **Web Scrape** — fetch and extract visible text from a URL
- **PDF to Text** — extract text content from a PDF file
- **OCR** — image or scanned document to text string
- **Clipboard Read** — read current clipboard text
- **Environment Variable** — read a system env var as a string
- **Template Fill** — substitute named vault/transient values into a text template
- **RSS / Feed Item** — fetch and parse an RSS or Atom feed entry

**File Reader →** *(group with picker)*
- **Simple File Read** — read entire file as a text string
- **Bulk File Read** — read all files matching a folder path or glob pattern
- **Find & Extract Passage** — search for a pattern and return the surrounding context window
- **Structured File Read** — parse CSV or JSON into usable object data
- **AI-Guided Read** — provide a file and a question; AI extracts the relevant portion

**Data Source →** *(group with picker — distinct from Text Input: returns structured data, not raw text)*
- **API Read** — GET request to a REST API, returns response body
- **Database Query** — run a read query against SQL or NoSQL, returns result set
- **System State** — read OS metrics: disk, memory, running processes
- **Screen / UI Read** — accessibility tree or live screen capture to structured text

**Trigger →** *(group with picker)*
- **Key Combination** — fire on a keyboard shortcut
- **File Change** — fire when a watched file is modified
- **Folder Watch** — fire when files are added or removed from a folder
- **Scheduled / Cron** — fire at a time or interval
- **Right-Click / Context Menu** — register an OS context menu entry that starts the workflow
- **Webhook / HTTP Listener** — fire when an HTTP request arrives on a local port
- **Process Event** — fire on OS process start or stop

**Trigger architecture note:** Triggers are the most distinct node type in this
list. They do not execute within a workflow — they start one. The runtime
implication is that they need a persistent listener process that runs outside
the normal supervisor execution model. This maps to the "long-lived listening
resources" item already in the backlog. For now, treat them as config-only
nodes (define the trigger in config) and build the listener runtime as a
separate phase. Do not design the workflow execution model around trigger timing.

---

### FLOW CONTROL

**Branch →** *(group with picker — variants have different port shapes, so they must be separate types)*
- **Parallel Branch** — unconditionally split into N concurrent paths (N output ports)
- **Simple Conditional Branch** — bool/flag picks true or false path (2 ports)
- **Multi-Condition Branch** — multiple conditions map to multiple named paths (N named ports)
- **AI Conditional Branch** — AI evaluates a prompt to decide the path (N named paths + default)
- **Loop Branch** — repeat a path N times or until a condition exits (loop body + exit ports)
- **Weighted Branch** — probabilistic path selection (useful for A/B testing within workflows)

**Merge →** *(group with picker)*
- **Standard Merge** — wait for all selected branches, then continue
- **First-Wins Merge** — proceed when any one branch arrives; cancel remaining
- **Conditional Merge** — accept only arriving branches that meet a condition
- **Timed Merge** — merge after a time limit regardless of branch state; incomplete branches abandoned

**Wait / Timer →** *(group with picker)*
- **Wait Until** — pause until a named Vault key is set by another node or branch
- **Fixed Delay** — wait a specified duration then continue
- **Timeout Guard** — continue with an error signal after a limit expires; pair with a downstream conditional branch for error handling
- **Debounce** — wait until a burst of rapid incoming changes settles before continuing

**Loop Utility →** *(group with picker)*
- **Counter** — increment and read a run-scoped integer counter
- **Accumulator** — collect one value per iteration into a growing list
- **Repeat Limiter** — error or force-exit if a loop body exceeds a threshold (prevents runaway loops)

**Merge Beacon** — *direct-add* (single type, config handles flag-setter behavior)

**Start / End** — *direct-add* (unique structural nodes, no grouping makes sense)

---

### OUTPUTS

**Text Output →** *(group with picker)*
- **Standard Text Output** — display text in the execution window (active output, blocks)
- **Log Output** — append to a running log file without interrupting execution (passive)
- **Debug Print** — lightweight transient print, visually quieter, for inspection
- **Formatted Output** — output with sections, dividers, and emphasis (add when rich formatting lands)

**File Write →** *(group with picker)*
- **File Write** — write content to a file (config: overwrite or append mode — one node, mode select)
- **Structured Write** — serialize an object to CSV or JSON format
- **File Delete** — remove a file; output: bool success
- **File Copy / Move** — duplicate or relocate a file; input: source + destination paths

**Send / Notify →** *(group with picker)*
- **OS Desktop Notification** — system tray or toast alert
- **Email Send** — send via SMTP or mail API; input: recipient + subject + body
- **Webhook / HTTP POST** — push data to an external URL; input: URL + payload + headers
- **API Write** — PUT/PATCH/DELETE to a REST endpoint
- **Database Write** — insert or update via SQL/NoSQL connection; input: query/document + data

**User-Facing Prompt →** *(group with picker)*
- **Confirmation Dialog** — yes/no prompt, blocks until answered; output: bool
- **User Choice Picker** — present a labeled list, wait for selection; output: chosen string
- **Progress Message** — show a non-blocking status update; fire and forget

---

### COMPLEX

**AI Processing →** *(group with picker)*
- **Chat Completion** — LLM text generation, optional session persistence via Vault ai_session
- **Image Generation** — generate an image from a text prompt; output: image path
- **Embedding** — convert text to a vector; output: float array
- **Vision / Multimodal** — analyze an image alongside a text prompt
- **AI Tool Call** — LLM with structured function/tool calling; output: structured result object
- **AI Decision** — multi-step reasoning that returns a named, categorized decision with reasoning

**Subworkflow →** *(group with picker — deferred to phases 19/20 per roadmap, taxonomy slot reserved)*
- **Run Subworkflow** — execute a saved workflow as an inline step
- **Parallel Subworkflow** — run multiple saved workflows concurrently, collect all outputs
- **Conditional Subworkflow** — run a workflow only if a condition passes

**Data Transform →** *(group with picker — absorbs current Data and most Debug/Utility nodes)*
- **Concat** — join multiple text strings
- **Text Transform** — regex, find/replace, trim, split operations
- **JSON / Object Transform** — reshape or extract fields from a structured object
- **Set Variable** — write a named Vault variable
- **Get Variable** — read a named Vault variable
- **Math / Comparison** — arithmetic or comparison between numbers; output: value or bool

**Script Runner →** *(group with picker — future; flag security implications)*
- **Python Script** — execute inline or file-based Python; output: return value + stdout
- **Shell Command** — run a shell command, capture stdout and exit code
- **Node.js Script** — execute inline JavaScript

**Script Runner security note:** these nodes are a meaningful attack surface.
They should require an explicit opt-in setting ("allow script execution") before
appearing in the selector at all, and the picker description should show a
visible warning. Do not implement until the security posture is decided.

---

## Subcategories

Nodes can have multiple subcategories. Subcategories are filterable capability
tags, not mutually exclusive families.

| Subcategory | Meaning |
|---|---|
| Triggered | Listens, waits, or wakes a workflow/branch when an external condition happens. |
| File I/O | Interacts with files on the user's computer, including file references kept open for later nodes during a run. |
| Internet | Uses network/web access that is not specifically an AI-service call. |
| AI | Uses AI services. API calls for AI are distinct from the `Internet` tag unless the node is specifically browsing/scraping the web. |
| Passive Output | Produces durable or visible output without taking over the execution window. |
| Active Output | Takes over or interrupts the execution window to show/collect user-facing output. |
| Parallel | Can create or coordinate parallel execution paths. |
| Conditional | Depends on state, inputs, predicates, or branch conditions to decide execution. |
| Runtime Resource | Opens or manages a per-run handle such as a file, stream, listener, or browser/session resource. |
| Utility | Helps inspect, transform, wait, log, debug, or pass data through without being a primary workflow concept. |

More subcategories can be added as the node overhaul reveals real need, but do
not create one-off tags for a single node unless it clearly names a future
filter users would seek.

**Filters are deliberately sparse.** Groups absorb most of the filtering need
(a group collapses many variants behind one entry), and section headers
organize the rest. Only two tabs have filter controls:

| Tab | Filters |
|---|---|
| I/O | `File I/O` · `Internet` · `AI` (apply to whichever switch side is active) |
| Flow Control | none |
| Utility | none |
| Complex | `AI` |

Subcategory tags still exist on all nodes regardless of which tabs surface
filter controls — the string search matches tags everywhere, and the editor
details panel shows them.

## Metadata Direction

The backend should remain UI-agnostic, but node metadata should expose portable
identity that any frontend can consume:

- `primary_family` — one of `Inputs`, `Outputs`, `Flow Control`, `Utility`,
  `Complex`; drives selector tab mapping and strongest row identity
- `tags` — zero or more subcategory strings; drives filter checkboxes and
  search
- `icon_name` — display glyph or icon name
- `color_hint` — optional color from the family color map
- `short_description` — short selector summary
- `description` — detailed description for the right panel/config surfaces
- `group` — frontend-only navigation group name (see below)
- `selector_section` — frontend-only section header the entry renders under
  (see below)

### The `group` Field

**Groups are not real node types.** They are a frontend-only navigation concept
derived from node metadata. The backend never knows a group exists.

Each node class declares one field: `group: str | None`. For example:

```python
class EmailSendNode(Node):
    primary_family = "Outputs"
    tags = ["Internet"]
    group = "Send / Notify"
```

The selector builds group entries dynamically: scan all nodes for the active
tab, collect unique `group` values, and create a group entry for any group
with 2 or more members. Members with `group = None` or belonging to a
single-member group appear as direct-add entries.

This means adding a new node to an existing group requires only declaring the
`group` field. No selector code changes are needed.

**Auto-promotion rule:** if a group ends up with only 1 member (because other
members haven't been implemented yet, or were removed), that member
auto-promotes to a direct-add entry. No picker appears for a group of one.

### The `selector_section` Field

Section headers organize the main selector list within a tab (e.g. Utility's
`Automation` / `Transform` / `Debug` / `Loop Helpers`). Like `group`, sections
are frontend-only navigation metadata:

- Each node class may declare `selector_section: str | None`.
- All members of a group must declare the same section (the group entry
  renders under that header). The node helper validates this at spec time.
- Entries with no section render in an unsectioned block at the top of the
  list, before the first header.
- The frontend owns section ordering per tab (a small ordered constant); the
  metadata only names the section an entry belongs to.
- A section header with no visible entries (after filters/search) is hidden.

`NodeFactory.get_node_types_metadata()` exposes `group` and `selector_section`
alongside existing metadata — two additional keys. No backend component
branches on either field.

## Node Selector UX

The selector is a two-level design: a **Main Selector** and a **Group Picker**
second modal. Together they replace the old flat list and the old
per-subcategory checkbox column.

### Tab Structure

Four tabs: `I/O`, `Flow Control`, `Utility`, `Complex`.

The `I/O` tab maps two backend families onto one tab with a switch:

- A Textual `Switch` sits at the top of the tab body: Input on one side,
  Output on the other.
- The switch state selects which family's entries fill the list
  (`Inputs` or `Outputs`).
- Filter checkboxes and the string filter apply to the active side.
- The switch is a normal keyboard nav stop between the tab row and the list.

### Main Selector Layout

Every list entry occupies its own line(s), vertically stacked, one per
keyboard step. Section headers are non-selectable divider rows that keyboard
navigation automatically jumps over.

```
┌─ Add Node ──────────────────────────────────────────┐
│  I/O    Flow Control    [Utility]    Complex          │
│  ─────────────────────────────────────────────────── │
│  / filter...                                          │
│  ─────────────────────────────────────────────────── │
│  ── Automation ─────────────────────────────────────  │
│  ► UI Automation                                 6 ▸  │
│  ► Script Runner                                 3 ▸  │
│  ── Transform ──────────────────────────────────────  │
│  ► Data Transform                                7 ▸  │
│  ── Debug ──────────────────────────────────────────  │
│    Echo                                               │
│    Probe                                              │
│    Logger                                             │
│    Sleep / Delay                                      │
│  ── Loop Helpers ───────────────────────────────────  │
│    Counter                                            │
│    Accumulator                                        │
│    Repeat Limiter                                     │
│                                                       │
│  W/S move  A/D tabs  E open/add  / filter  ESC close  │
└───────────────────────────────────────────────────────┘
```

I/O tab with the switch and its filter strip:

```
┌─ Add Node ──────────────────────────────────────────┐
│  [I/O]    Flow Control    Utility    Complex          │
│  ─────────────────────────────────────────────────── │
│  ○ Input ──────── Output ●                           │
│  [ ] File I/O   [ ] Internet   [ ] AI                │
│  ─────────────────────────────────────────────────── │
│  / filter...                                          │
│  ─────────────────────────────────────────────────── │
│  ► Text Output                                   4 ▸  │
│  ► File Write                                    4 ▸  │
│  ► Send / Notify                                 5 ▸  │
│  ► User-Facing Prompt                            3 ▸  │
└───────────────────────────────────────────────────────┘
```

Behavior:

- A string match filter sits at the top of every tab (activate with `/`,
  command-mode activation as today) for users who want to type a node name
  instead of moving through the list.
- Group entries show a member count at the right edge. The count reflects only
  members that match currently active filters.
- Groups whose filtered count drops to 0 are hidden. Section headers with no
  visible entries are hidden.
- Direct-add entries can be added with `E` immediately.
- String filtering, subcategory filters (where present), and the I/O switch
  combine: an entry must match all active constraints.
- Subcategory filters use `AND` semantics.

**Entry kinds.** The visible list is a sequence of three entry kinds:

| Kind | Selectable | `E` behavior |
|---|---|---|
| Section header | No — navigation skips it | n/a (clicking does nothing) |
| Group entry | Yes | Opens the Group Picker |
| Node entry (direct-add or dissolved-group member) | Yes | Adds the node, closes the selector |

**Search behavior:** when a filter string is active, all groups flatten and
section headers disappear. Matching node types appear directly in the list —
not behind a group entry. This is the most natural behavior for search (you
are looking for something specific; grouping and sections are for browsing).
Clear the filter and the grouped, sectioned view re-appears.

**Script Runner gating:** while the "allow script execution" setting is off,
Script Runner group members do not appear in the list or in search results.
When enabled, the group entry and picker descriptions carry a visible warning.

### Group Picker (second modal)

```
┌─ Send / Notify ──────────────────────────────────────┐
│  > OS Desktop Notification                            │
│    Email Send                                         │
│    Webhook / HTTP POST                                │
│    API Write                                          │
│    Database Write                                     │
│                                                        │
│  [description of highlighted node appears here]       │
└────────────────────────────────────────────────────────┘
```

- Opens when `E` is pressed on a group entry in the main selector.
- `ESC` pops only the picker modal, returning to the main selector. The user
  does not lose their place if they opened the wrong picker.
- `E` adds the highlighted type and closes both modals simultaneously.
- One node per line; the highlighted node's description is always visible
  below the list.
- No tabs, no checkboxes, no filter input — group sizes are small (3–8
  entries). The main selector's string filter already reaches members when
  active.
- A generic reusable modal, parameterized by group name and member list.
  One picker screen serves all groups.

## Keyboard Flows

### Adding a node from a group

```
1. Open node selector (existing editor binding)
2. A/D to reach the right tab (on I/O, toggle the Input/Output switch if needed)
3. W/S through filter checkboxes if narrowing is needed (I/O and Complex only)
4. W/S to highlight a group entry — count shows at right edge; headers are
   skipped automatically
5. E → Group Picker modal opens
6. W/S to highlight specific type — description visible below
7. E → node added to canvas, both modals close
```

Node lands unconnected; editor cursor auto-selects it.

### Adding a direct-add node (no group)

Same as steps 1–4 above, then `E` directly adds the node. No behavior change
for direct-add nodes.

### Search-first flow (fastest path to a known node)

```
1. Open selector
2. / to focus filter, start typing (e.g. "parallel")
3. Groups and headers dissolve; "Parallel Branch" appears directly in the list
4. W/S to it, E to add
5. Selector closes
```

## Editor Row UX

Editor rows should become easier to scan while staying keyboard-stable.

Preferred direction:

```text
| [ | Security camera setup      | ] |
| [ | Inputs - File I/O          | ] |

| { | Security camera trigger    | } |
| { | Complex - Triggered        | } |
```

This is conceptual, not a fixed ASCII contract. The preferred implementation is
to use Textual `ascii` borders around each node card, with plain alias and
family/subcategory text inside the box. Do not prepend family brackets to the
alias or identity line; the box itself carries the frame.

The important requirements are:

- node rows may use two lines when space allows;
- node cards use a visible text-box border around each individual node;
- the alias and identity lines do not start with family bracket characters;
- the first line emphasizes the user-facing alias;
- the second line shows family plus one or two high-signal subcategories;
- if the second line cannot fit, truncate the visible subcategory text with an
  ellipsis; the full list remains available in the right-side details panel;
- utility/debug/pass-through nodes should be visually quieter;
- validation, breakpoint, selection, execution, and Merge Beacon health colors
  remain more important than decorative family color;
- cursor/highlight behavior and branch selector rows must stay stable.

The right-side details panel should show the node's primary family and all
subcategories. This helps users understand why a node appeared under particular
selector filters.

With the family revision, the editor row family color map needs a fifth entry
for `Utility` (the existing quiet utility styling is the natural fit), and
`Inputs`/`Outputs` keep distinct colors even though they share a selector tab.


## Problems and Solutions Summary

| Problem | Solution |
|---|---|
| Inputs and Outputs as separate tabs felt heavy with fewer entries | One `I/O` tab with an Input/Output switch above the list; backend families stay separate |
| ~20 entries per tab hard to scan as a flat list | Non-selectable section headers inside the list; keyboard nav skips them |
| Checkbox filter column disproportionate to short grouped lists | Filters removed except I/O (`File I/O`/`Internet`/`AI`) and Complex (`AI`); groups + headers do the organizing |
| Search across groups | Flatten all groups and hide headers when filter string is active; restore when cleared |
| Group with only 1 member | Auto-promote: single-member groups show as direct-add entries, no picker |
| ESC behavior in picker | ESC pops only the picker modal, returns to selector. Textual's modal stack handles this naturally |
| Subcategory filter + group count | Group entry count shows only members that match active filters; 0-count groups hidden |
| Where do AI nodes live | AI is a subcategory: AI variants sit in their natural family/group; dedicated AI tools in Complex → AI Processing |
| AI dependability | Curated supported-model list per AI node; strictest for structured-output nodes; possible per-model groups later |
| Branch end semantics | Outputs carry "Terminate branch after completion"; End Branch node covers silent termination; merges end branches naturally |
| Trigger nodes need a listener runtime | Out of scope for selector work — config-only for now, listener deferred to a runtime resource phase |
| Script Runner security | Gate behind an explicit setting; hidden from list and search while gated; warning in picker description |
| Backend impact | Near zero. `NodeFactory` exposes `group` and `selector_section`; no backend component branches on them |

## What Doesn't Need to Exist

- **A "base" node type on the canvas** — the two-level selector handles
  everything before the node is placed. The node that lands is always a
  concrete type.
- **Per-group custom UI logic** — the picker is a generic reusable modal
  parameterized by group name and member list. One screen serves all groups.
- **Filters in the picker** — group sizes are small enough that the picker is
  just a list. The main selector narrows before you enter a group.
- **Separate Overwrite File and Append File nodes** — one File Write node with
  a mode config select. The Core Simplification Rule eliminates these as
  separate types.
- **A user-addable Start or standalone End node** — Start is auto-generated;
  branch termination is handled by output config, merges, and End Branch.
- **A Breakpoint node** — breakpoints are an editor-level concept (already
  implemented). Planned step-execution mode is also editor-level.

## Boundary Rules

- Runtime behavior does not change in Phase 17 unless a metadata field is
  needed to describe existing behavior.
- Selector tabs, the I/O switch, filter state, section headers, row borders,
  row colors, and display density are frontend concerns.
- `group` and `selector_section` are frontend-only navigation concepts. The
  backend exposes them through `NodeFactory` for frontend consumption, but no
  backend component (Supervisor, WorkflowMap, MemoryBank, Validator) should
  branch on them.
- Portable node identity metadata belongs on node classes and through
  `NodeFactory` because future frontends also need it.
- File handles, browser sessions, listeners, and similar resources are runtime
  resource concerns for later phases. Phase 17 can name them with metadata, but
  should not implement resource sessions unless that becomes an explicit phase.

## Forward Design Decisions

These choices are settled (taxonomy revision 2026-06-12):

- Five backend families: `Inputs`, `Outputs`, `Flow Control`, `Utility`,
  `Complex`. Four selector tabs; `Inputs`/`Outputs` share the `I/O` tab via a
  switch.
- AI is a subcategory tag, not a family. AI variants live in their natural
  groups; dedicated AI tools live in Complex → AI Processing.
- Filters: I/O tab gets `File I/O` / `Internet` / `AI`; Complex gets `AI`;
  Flow Control and Utility get none. Subcategory filtering uses `AND`
  semantics where present.
- Section headers are in-list, non-selectable, skipped by keyboard navigation,
  hidden while a string filter is active or when empty.
- The string filter is activate-to-edit (`/`), present at the top of every
  tab, and dissolves groups and headers while active.
- Groups are dynamically derived from node metadata (`group` field). Adding a
  node to a group requires only the field — no selector code changes.
- Sections are derived from node metadata (`selector_section` field); the
  frontend owns per-tab section ordering.
- The group picker is a single generic modal parameterized by group name and
  member list. `ESC` in the picker returns to the main selector. `E` adds and
  closes both.
- Single-member groups auto-promote to direct-add entries.
- Output nodes carry the standard "Terminate branch after completion" config
  option; End Branch is the silent direct-add terminator; Start/End are not
  user-addable.
- AI nodes declare curated supported-model lists; structured-output AI nodes
  carry the strictest lists.
- Existing nodes should receive transitional metadata (including remapping
  current debug/data nodes into the `Utility` family). Do not overfit the new
  taxonomy to the current node list because many current nodes are expected to
  be redone — `NODE_CATALOG.md` tracks the mapping.

## File Resource Direction

Users should see and configure files by their normal file names/paths. File
input and output nodes should let users choose files in node config where
appropriate, then pass those paths into workflow execution.

Actual file access happens during a run. Future runtime-resource work should
provide a run-scoped owner that can open files, keep access available for later
nodes in the same run, and close resources predictably at run completion. This
may be coordinated by `MasterState`, but should likely live in a focused helper
or execution-session module so `MasterState` does not become the file/resource
manager itself.

## Completion Shape

Phase 17 is complete when:

- the active docs agree on the taxonomy and selector/editor direction (this
  document, `NODE_CATALOG.md`, and `NODE_STANDARDS.md`);
- `NodeFactory` exposes the metadata needed by the frontend: `primary_family`
  (five families), `tags`, `icon_name`, `color_hint`, `group`,
  `selector_section`;
- registered nodes are remapped to the five-family scheme (debug/data
  utility nodes move to `Utility`);
- the selector has the four-tab structure with the I/O Input/Output switch
  and the reduced filter set (I/O: File I/O / Internet / AI; Complex: AI);
- the main selector renders section headers that keyboard navigation skips
  and that hide when empty or while searching;
- the selector implements the two-level group picker: group entries with
  member counts, a generic Group Picker modal for groups with 2+ members;
- single-member groups auto-promote to direct-add entries with no picker;
- `ESC` in the group picker returns to the main selector, not all the way out;
- group counts reflect active filters; 0-count groups are hidden;
- when a string filter is active, groups and headers dissolve and node types
  appear directly;
- editor rows show stable visual identity for family/subcategory across the
  five families;
- the details panel exposes family and subcategories;
- focused tests cover metadata exposure, family-to-tab mapping, the I/O
  switch, selector filtering, header skipping, group entry rendering, picker
  navigation, ESC behavior, auto-promotion, row rendering, and
  keyboard/autoscroll behavior;
- the editor view is verified clean in the running app at several terminal
  widths.

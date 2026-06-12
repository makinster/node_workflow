# Phase 17 - Node Visual Identity And Selector Taxonomy

**Status:** In progress
**Last updated:** 2026-06-12

Phase 17 is not just a cosmetic row-color pass. It is the foundation for the
next node overhaul: clearer node families, reusable subcategory tags, a more
useful node selector, and editor rows that communicate node identity at a
glance without changing runtime behavior.

The current runtime nodes may be redone as this taxonomy settles. Treat existing
node types as implementation inventory, not the final user-facing library.

## User Experience Goal

Users should be able to answer three questions quickly:

- What kind of node is this?
- What capabilities or concerns does it involve?
- Is it quiet utility plumbing, workflow structure, user-facing output, or a
  complex behavior that deserves extra attention?

The selector and editor should use the same language. If a node appears under
the `Inputs` tab with `File I/O` and `Triggered` filters, the editor details
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

Apply this rule before adding any node to the taxonomy below or to the selector.
The rule is also documented in `NODE_STANDARDS.md` as the Node Type
Classification guide.

## Primary Node Families

Each node has one primary family. This family drives selector tabs and the
strongest row identity.

| Family | Meaning | Examples |
|---|---|---|
| Inputs | Get input from an external source on a shorter timescale than long-lived triggers. | Text In, File Read, Text File Read, Web Scrape, User Text Input |
| Flow Control | Change workflow structure, branch routing, merge behavior, waiting, or loop shape. | Branch, Conditional Branch, Merge Beacon, Wait Until, Looping Branch |
| Outputs | Send workflow results to the user, a file, another system, or a branch-ending surface. | Text Output, File Output, active execution-window output |
| Complex | Nested workflows and unique nodes that do not fit cleanly in the other families. | Subworkflow, unique triggers, advanced branch beacons |

`Complex` is a pressure-release family, not a junk drawer. Prefer `Inputs`,
`Flow Control`, or `Outputs` when the node's main role is clear.

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

## Metadata Direction

The backend should remain UI-agnostic, but node metadata should expose portable
identity that any frontend can consume:

- `primary_family` — drives selector tabs and strongest row identity
- `tags` — zero or more subcategory strings; drives tab-specific filter checkboxes
- `icon_name` — display glyph or icon name
- `color_hint` — optional color from the family color map
- `short_description` — short selector summary
- `description` — detailed description for the right panel/config surfaces
- `group` — frontend-only navigation group name (see below)

Implementation note: `Node` already has optional `icon_name`, `tags`, and
`color_hint` attributes, but `NodeFactory.get_node_types_metadata()` currently
does not expose `category`, `icon_name`, `tags`, or `color_hint`. Phase 17
should close that metadata gap before building selector filters around it.

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
family, collect unique `group` values, and create a group entry for any group
with 2 or more members. Members with `group = None` or belonging to a
single-member group appear as direct-add entries.

This means adding a new node to an existing group requires only declaring the
`group` field. No selector code changes are needed.

The `group` field sits alongside `primary_family`, `tags`, `icon_name`, and
`color_hint`. `NodeFactory.get_node_types_metadata()` exposes the field
alongside existing metadata — one additional key.

**Auto-promotion rule:** if a group ends up with only 1 member (because other
members haven't been implemented yet, or were removed), that member
auto-promotes to a direct-add entry. No picker appears for a group of one.

## Node Selector UX

The selector is a two-level design: a **Main Selector** and a **Group Picker**
second modal. Together they replace the old flat list.

### Main Selector

```
┌─ Inputs ──── Flow Control ──── Outputs ──── Complex ─┐
│  [ ] File I/O    [ ] Internet    [ ] AI               │
│                                                        │
│  Text Input                              3 ▸           │
│  File Reader                             5 ▸           │
│  > Simple File Read                                    │
│  Data Source                             4 ▸           │
│  Trigger                                 7 ▸           │
└────────────────────────────────────────────────────────┘
```

- Top-level tabs: `Inputs`, `Flow Control`, `Outputs`, `Complex`.
- A string match filter is available (activate with `/`; groups dissolve when
  active — see search behavior below).
- Beneath the string filter, subcategory checkboxes appear for the active tab.
  Only subcategories relevant to nodes in that family are shown.
- Group entries show a member count at the right edge. The count reflects only
  members that match currently active subcategory filters.
- When any subcategory filter is active, the count on each visible group
  updates to reflect only matching members. Groups whose count drops to 0 are
  hidden.
- Direct-add nodes (no group, or single-member group) appear in the list
  directly and can be added with `E` immediately.
- String filtering and subcategory filtering combine: a node must match the
  active family, active subcategory filters, and any string query.
- Subcategory filters use `AND` semantics.

**Search behavior:** when a filter string is active, all groups flatten.
Matching specific node types appear directly in the list — not behind a group
entry. This is the most natural behavior for search (you are looking for
something specific; grouping is for browsing). Clear the filter and groups
re-appear. The initial keyboard highlight is the first subcategory control, not
the string filter.

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
- No tabs, no checkboxes — this is a focused single-purpose list. The node
  description is always visible below the name.
- The picker has no filter input of its own. Group sizes are small enough
  (3–8 entries) that filtering within the picker would be overkill. The main
  selector's string filter already reaches into group members when active.
- A generic reusable modal, parameterized by group name and member list.
  One picker screen serves all groups.

## Keyboard Flows

### Adding a node from a group

```
1. Open node selector (existing editor binding)
2. A/D to reach the right family tab
3. W/S through subcategory checkboxes if narrowing is needed
4. W/S to highlight a group entry — count shows at right edge
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
3. Groups dissolve; "Parallel Branch" appears directly in the list
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
to use fixed left/right bracket columns around a text column. That keeps open
and close brackets aligned across rows, gives the center text maximum room, and
lets Textual manage styling without fragile manual spacing. Textual widgets are
fine if they produce a cleaner result than hand-aligned text.

The important requirements are:

- node rows may use two lines when space allows;
- bracket or frame style can differ by primary family;
- brackets/frames align cleanly across rows, preferably with fixed bracket
  columns on either side of the node text;
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

## Problems and Solutions Summary

| Problem | Solution |
|---|---|
| Search across groups | Flatten all groups when filter string is active; restore groups when filter clears |
| Group with only 1 member | Auto-promote: single-member groups show as direct-add entries, no picker |
| ESC behavior in picker | ESC pops only the picker modal, returns to selector. Textual's modal stack handles this naturally |
| Subcategory filter + group count | Group entry count shows only members that match active subcategory filters |
| Trigger nodes need a listener runtime | Out of scope for selector work — treat as config-only for now, defer listener to runtime resource phase |
| Script Runner security | Gate behind an explicit setting; show warning in picker description; defer implementation until security posture is decided |
| Phase 17 compatibility | `group` field is additive alongside `primary_family` and `tags`. Phase 17 taxonomy work is not wasted — subcategory tags define group filter behavior |
| Backend impact | Zero. `NodeFactory` just exposes a new metadata field. Supervisor, WorkflowMap, MemoryBank, Validator — none of these need to know about groups |

## What Doesn't Need to Exist

- **A "base" node type on the canvas** — the two-level selector handles
  everything before the node is placed. The node that lands is always a
  concrete type.
- **Per-group custom UI logic** — the picker is a generic reusable modal
  parameterized by group name and member list. One screen serves all groups.
- **Subcategory checkboxes in the picker** — group sizes are small enough that
  the picker is just a list. The main selector's filters already do the
  narrowing before you enter a group.
- **Separate Overwrite File and Append File nodes** — one File Write node with
  a mode config select. The Core Simplification Rule eliminates these as
  separate types.

## Boundary Rules

- Runtime behavior does not change in Phase 17 unless a metadata field is
  needed to describe existing behavior.
- Selector tabs, filter state, row brackets, row colors, and display density are
  frontend concerns.
- The `group` field is a frontend-only navigation concept. The backend exposes
  it through `NodeFactory` for frontend consumption, but no backend component
  (Supervisor, WorkflowMap, MemoryBank, Validator) should branch on it.
- Portable node identity metadata belongs on node classes and through
  `NodeFactory` because future frontends also need it.
- File handles, browser sessions, listeners, and similar resources are runtime
  resource concerns for later phases. Phase 17 can name them with metadata, but
  should not implement resource sessions unless that becomes an explicit phase.

## Forward Design Decisions

These choices are settled for the first implementation pass:

- Subcategory filtering uses `AND` semantics.
- The string filter is activate-to-edit, not auto-edit on selector open.
- Subcategory controls are checkboxes.
- Subcategory choices are tab-specific and derived from the active family.
- `Complex` remains partly TBD until the other families are stronger; prefer it
  for structurally unusual nodes such as nested workflows, unique triggers, and
  advanced beacons.
- Outputs use `Passive Output` and `Active Output` tags. A future
  branch-ending output tag can be added if outputs intentionally close branches.
- `AI` and `Internet` stay distinct. A normal AI API call is `AI`; web browsing,
  scraping, or non-AI network access is `Internet`; a web-browsing AI node may
  carry both.
- Existing nodes should receive transitional metadata. Do not overfit the new
  taxonomy to the current node list because many current nodes are expected to
  be redone.
- Groups are dynamically derived from node metadata. Adding a node to a group
  requires only the `group` field — no selector code changes.
- The group picker is a single generic modal parameterized by group name and
  member list. No custom picker per group.
- `ESC` in the group picker returns to the main selector, not all the way out.
- When the string filter is active, groups dissolve and individual node types
  appear directly; groups re-form when the filter is cleared.

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
  document and `NODE_STANDARDS.md`);
- `NodeFactory` exposes the metadata needed by the frontend: `primary_family`,
  `tags`, `icon_name`, `color_hint`, `group`;
- the selector has family tabs and subcategory filters with keyboard-first
  navigation;
- the selector implements the two-level group picker: group entries with member
  counts in the main selector, a generic Group Picker modal for groups with 2+
  members;
- single-member groups auto-promote to direct-add entries with no picker;
- `ESC` in the group picker returns to the main selector, not all the way out;
- group count on a group entry reflects only members matching active subcategory
  filters; groups with a filtered count of 0 are hidden;
- when a string filter is active, groups dissolve and individual node types
  appear directly;
- editor rows show stable visual identity for family/subcategory;
- the details panel exposes family and subcategories;
- focused tests cover metadata exposure, selector filtering, group entry
  rendering, picker navigation, ESC behavior, auto-promotion, row rendering,
  and keyboard/autoscroll behavior.

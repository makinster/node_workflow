# Node Catalog

**Status:** Living inventory — created 2026-06-12.
This is the complete inventory of every node idea in the project: implemented,
planned, deferred, and concept-only. Nothing gets lost here. When the node
overhaul implements, defers, or rejects a node, update its status — do not
delete the row.

Taxonomy structure, selector behavior, and metadata fields live in
`PHASE_17_NODE_VISUAL_IDENTITY.md`. I/O design rules for authoring any of
these nodes live in `NODE_STANDARDS.md`.

## Status Legend

| Status | Meaning |
|---|---|
| **Live** | Implemented and registered today (may be renamed/reworked in the overhaul) |
| **Planned** | In the active build plan |
| **Deferred** | Designed or scoped, intentionally not scheduled |
| **Concept** | Idea only, not fully designed |

Many Live nodes are transitional debug/dev inventory and are expected to be
redone or absorbed during the node overhaul. The `Maps from` column names the
currently registered node type a row absorbs, where one exists.

---

## I/O — Input Side (`primary_family: Inputs`)

### Group: Text Input

| Node | Status | Notes / Maps from |
|---|---|---|
| User Text Input | Live | `user_text_input_node` — prompt user at runtime; blocks until answered |
| Web Scrape | Concept | Fetch and extract visible text from a URL. Tags: Internet |
| PDF to Text | Concept | Extract text content from a PDF file. Tags: File I/O |
| OCR | Concept | Image or scanned document to text string. Tags: File I/O |
| Clipboard Read | Concept | Read current clipboard text |
| Environment Variable | Concept | Read a system env var as a string |
| RSS / Feed Item | Concept | Fetch and parse an RSS or Atom feed entry. Tags: Internet |

### Group: File Reader

| Node | Status | Notes / Maps from |
|---|---|---|
| Simple File Read | Live | `file_reader_node` — read entire file as a text string. Tags: File I/O, Runtime Resource |
| Bulk File Read | Concept | Read all files matching a folder path or glob pattern. Tags: File I/O |
| Find & Extract Passage | Concept | Search for a pattern, return surrounding context window. Tags: File I/O |
| Structured File Read | Concept | Parse CSV or JSON into usable object data. Tags: File I/O |
| AI-Guided Read | Concept | Provide a file and a question; AI extracts the relevant portion. Tags: File I/O, AI |
| File Instance | Live (example) | `example_file_instance_node` — helper-generated reference example; remove or absorb during overhaul |

### Group: Data Source

| Node | Status | Notes / Maps from |
|---|---|---|
| API Read | Concept | GET request to a REST API, returns response body. Tags: Internet |
| Database Query | Concept | Read query against SQL/NoSQL, returns result set |
| System State | Concept | Read OS metrics: disk, memory, running processes |
| Screen / UI Read | Concept | Accessibility tree or screen capture to structured text |

### Direct-add: AI Input

| Node | Status | Notes |
|---|---|---|
| AI Input | Planned | Seeds or extends a chat session before the response is needed. Prompt from upstream/vault/configured; sends to LLM under a session key; writes `(type: ai_session, ref_key)` to vault. Default output is dead-drop passthrough — the AI call is a side effect. Optional "Output AI response" switches transient output to the response text. Useful when the prompt is customized during workflow execution before being passed in. Tags: AI. Depends on typed vault entries + AI session backlog work. |

---

## I/O — Output Side (`primary_family: Outputs`)

All output nodes carry the standard **"Terminate branch after completion"**
config option (see `NODE_STANDARDS.md`). Branches end through outputs, merges,
or an End Branch node — there is no standalone End node.

### Group: Text Output

| Node | Status | Notes / Maps from |
|---|---|---|
| Standard Text Output | Live | `text_output_node` — display text in the execution window. Tags: Active Output |
| Log Output | Concept | Append to a running log file without interrupting execution. Tags: Passive Output, File I/O |
| Debug Print | Concept | Lightweight transient print, visually quieter. Tags: Passive Output, Utility |
| Formatted Output | Concept | Output with sections, dividers, emphasis — when rich formatting lands |

### Group: File Write

| Node | Status | Notes |
|---|---|---|
| File Write | Planned | Write content to a file. Overwrite vs append is a mode select — one node, not two types. Tags: File I/O, Runtime Resource |
| Structured Write | Concept | Serialize an object to CSV or JSON. Tags: File I/O |
| File Delete | Concept | Remove a file; output: bool success. Tags: File I/O |
| File Copy / Move | Concept | Duplicate or relocate a file; input: source + destination. Tags: File I/O |

### Group: Send / Notify

| Node | Status | Notes |
|---|---|---|
| OS Desktop Notification | Concept | System tray or toast alert. Tags: Passive Output |
| Email Send | Concept | Send via SMTP or mail API. Tags: Internet |
| Webhook / HTTP POST | Concept | Push data to an external URL. Tags: Internet |
| API Write | Concept | PUT/PATCH/DELETE to a REST endpoint. Tags: Internet |
| Database Write | Concept | Insert or update via SQL/NoSQL connection |

### Group: User-Facing Prompt

| Node | Status | Notes |
|---|---|---|
| Confirmation Dialog | Concept | Yes/no prompt, blocks until answered; output: bool. Tags: Active Output |
| User Choice Picker | Concept | Present a labeled list, wait for selection; output: chosen string. Tags: Active Output |
| Progress Message | Concept | Non-blocking status update; fire and forget. Tags: Passive Output |

### Direct-add: AI Response Output

| Node | Status | Notes |
|---|---|---|
| AI Response Output | Concept | Surface an AI session's response as user-facing output (counterpart to AI Input). Tags: AI, Active Output. Shape TBD as AI session work lands. |

---

## Flow Control (`primary_family: Flow Control`)

### Section: Branching

#### Group: Branch
Variants have different port shapes, so they must be separate types
(Core Simplification Rule).

| Node | Status | Notes / Maps from |
|---|---|---|
| Parallel Branch | Live | `branch_node` — unconditional split into 2–5 concurrent paths. Tags: Parallel |
| Simple Conditional Branch | Planned | Bool/flag picks true or false path (2 ports). Tags: Conditional. (`conditional_node` is the legacy ancestor.) |
| Multi-Condition Branch | Concept | Multiple conditions map to multiple named paths. Tags: Conditional |
| AI Conditional Branch | Deferred | AI evaluates a prompt to decide the path. Tags: Conditional, AI. **Strict model constraint:** requires reliable structured output (tool calling or JSON mode); the AI selects from defined branch labels and cannot invent a path. Supported-model list will be stricter than conversational AI nodes. |
| Loop Branch | Concept | Repeat a path N times or until a condition exits (loop body + exit ports). Tags: Conditional |
| Weighted Branch | Concept | Probabilistic path selection (A/B testing within workflows) |

#### Group: Merge

| Node | Status | Notes / Maps from |
|---|---|---|
| Standard Merge | Live | `merge_node` — wait for all selected branches, then continue. Tags: Parallel |
| First-Wins Merge | Concept | Proceed when any one branch arrives; cancel remaining |
| Conditional Merge | Concept | Accept only arriving branches that meet a condition. Tags: Conditional |
| Timed Merge | Concept | Merge after a time limit; incomplete branches abandoned |

#### Direct-add

| Node | Status | Notes / Maps from |
|---|---|---|
| Merge Beacon | Live | `branch_end_node` — branch-end flag setter for merge coordination |
| End Branch | Planned | Silently terminates a branch path with no output. For paths that intentionally discard a route (e.g. the "no" path of a conditional that should do nothing). Replaces the legacy `end_node` concept at branch scope. |

### Section: Timing

#### Group: Wait / Timer

| Node | Status | Notes / Maps from |
|---|---|---|
| Wait Until | Live | `wait_until_node` — pause until a named Vault key is set. Tags: Triggered, Conditional |
| Fixed Delay | Live (debug) | Absorbs `sleep_node` — wait a duration then continue |
| Timeout Guard | Concept | Continue with an error signal after a limit expires |
| Debounce | Concept | Wait until a burst of rapid changes settles |

### Removed from taxonomy

| Node | Status | Notes |
|---|---|---|
| Start | Removed | `start_node` exists in the runtime but is auto-generated — never user-addable |
| End | Removed | `end_node` exists in the runtime; replaced by terminate-branch config on outputs, merges, and the End Branch node |

---

## Utility (`primary_family: Utility`)

### Section: Automation

#### Group: UI Automation

| Node | Status | Notes |
|---|---|---|
| Mouse Click | Concept | Click a screen position or element by label |
| Type Text | Concept | Send keyboard input to the focused application |
| Key Press | Concept | Fire a key combination (an action, not a listener — listeners are Triggers) |
| Read Screen | Deferred | Capture visible text or image from a screen region |
| Find Element | Deferred | Locate a UI element by text or accessibility label |
| Window Focus | Deferred | Bring a named application window to the foreground |

#### Group: Script Runner *(security gated)*

| Node | Status | Notes |
|---|---|---|
| Python Script | Deferred | Inline or file-based Python; output: return value + stdout |
| Shell Command | Deferred | Run a shell command; output: stdout + exit code |
| Node.js Script | Deferred | Inline JavaScript |

Script Runner nodes are a meaningful attack surface. They require an explicit
opt-in setting ("allow script execution") before appearing in the selector at
all, are excluded from search results while gated, and the picker description
shows a visible warning. Do not implement until the security posture is
decided.

### Section: Transform

#### Group: Data Transform

| Node | Status | Notes / Maps from |
|---|---|---|
| Set Variable | Live | `set_variable_node` — write a named Vault entry. Duplicate `variable_setter_node` is also registered; consolidate to one type during the overhaul |
| Get Variable | Live | `get_variable_node` — read a named Vault entry. Duplicate `variable_reader_node` is also registered; consolidate to one type during the overhaul |
| Concat | Live | `concat_node` — join multiple text strings |
| Text Transform | Concept | Regex, find/replace, trim, split |
| JSON / Object Transform | Concept | Reshape or extract fields from structured data |
| Math / Comparison | Concept | Arithmetic or comparison; output: value or bool |
| Format Text | Concept | Interpolate vault/transient values into a template string (lives in this group, not direct-add) |

### Section: Debug

Direct-add nodes intended to survive into finished workflows for logging,
inspection, and pacing.

| Node | Status | Notes / Maps from |
|---|---|---|
| Echo | Live | `echo_node` — pass input through unchanged, optionally log it. Tags: Utility |
| Probe | Live | `probe_node` — inspect current payload, write to run output. Tags: Utility |
| Logger | Live | `logger_node` — append to a running log. Tags: Utility, Passive Output |
| Sleep / Delay | Live | `sleep_node` — pause a fixed duration (also Wait/Timer "Fixed Delay" candidate; settle one home during the overhaul). Tags: Utility |
| Memory Snapshot | Live (dev) | `memory_snapshot_node` — dev-only inspection; likely absorbed by Probe |
| No-Op | Live (dev) | `no_op_node` — dev placeholder; likely dropped in overhaul |
| Error | Live (dev) | `error_node` — forces an error for testing error paths; keep as dev tooling |
| Random Branch / Deep Branch | Live (dev) | `random_branch_node`, `deep_branch_node` — test scaffolding; not user-facing in overhaul |

There is no Breakpoint node. Breakpoints are an editor-level concept (already
implemented; they pause all branches). Planned step-execution mode will add
branch-specific or all-branch stepping — still editor-level, not a node.

### Section: Loop Helpers

Direct-add nodes that pair with the Loop Branch node.

| Node | Status | Notes / Maps from |
|---|---|---|
| Counter | Live | `counter_node` — increment and read a run-scoped integer |
| Accumulator | Concept | Collect one value per iteration into a growing list |
| Repeat Limiter | Live (debug) | `repeat_counter_node` — error/force-exit when a loop body exceeds a threshold |

---

## Complex (`primary_family: Complex`)

### Section: AI

#### Group: AI Processing

| Node | Status | Notes / Maps from |
|---|---|---|
| Chat Completion | Live (stub) | `chat_completion_node` — LLM text generation; real execution deferred. Optional session persistence via vault `ai_session` key. Tags: AI |
| Image Generation | Live (stub) | `image_generation_node` — image from text prompt; output: image path. Tags: AI |
| Embedding | Live (stub) | `embedding_node` — text to vector; output: float array. Tags: AI |
| Vision / Multimodal | Concept | Analyze an image alongside a text prompt. Tags: AI |
| AI Tool Call | Concept | LLM with structured function/tool calling; output: structured result. Tags: AI |
| AI Decision | Concept | Multi-step reasoning returning a named, categorized decision. Tags: AI |

**AI model approach:** AI nodes generalize around capability (what the node
does), not model identity. Each AI node declares a curated supported-model
list — not an open-ended endpoint field — because prompt adherence, tool
support, vision, and structured output vary by model and AI nodes must behave
dependably. Nodes with structured-output requirements (AI Conditional Branch,
AI Tool Call, AI Decision) carry stricter supported lists than conversational
nodes. **Future fork point:** if the supported list grows large and models
diverge in capability, AI Processing may split into per-model groups (a group
per model family, since each has its own capabilities). Capability-based
grouping is the contract until that pressure is real.

#### Group: Subworkflow *(reserved — phases 19/20)*

| Node | Status | Notes |
|---|---|---|
| Run Subworkflow | Planned (Phase 19) | Execute a saved workflow as an inline step |
| Parallel Subworkflow | Planned (Phase 20) | Run multiple saved workflows concurrently, collect outputs. Tags: Parallel |
| Conditional Subworkflow | Concept | Run a workflow only if a condition passes. Tags: Conditional |

### Section: Triggers

#### Group: Trigger

Triggers do not execute within a workflow — they start one. They need a
persistent listener process outside the supervisor execution model (the
"long-lived listening resources" backlog item). Treat them as config-only
nodes for now; the listener runtime is a separate phase. Do not design the
workflow execution model around trigger timing.

| Node | Status | Notes |
|---|---|---|
| Key Combination | Deferred | Fire on a keyboard shortcut. Tags: Triggered |
| File Change | Deferred | Fire when a watched file is modified. Tags: Triggered, File I/O |
| Folder Watch | Deferred | Fire when files are added/removed from a folder. Tags: Triggered, File I/O |
| Scheduled / Cron | Deferred | Fire at a time or interval. Tags: Triggered |
| Right-Click / Context Menu | Concept | OS context-menu entry that starts the workflow. Tags: Triggered |
| Webhook / HTTP Listener | Concept | Fire when an HTTP request arrives on a local port. Tags: Triggered, Internet |
| Process Event | Concept | Fire on OS process start or stop. Tags: Triggered |

---

## Editor-Only Types (not in the selector)

| Node | Status | Notes |
|---|---|---|
| Tombstone | Live | `tombstone_node` — save-persistent deleted-node record holding original node data. Backend type by design (2026-06-11 decision); hidden from the selector. See `BACKEND_FRONTEND_BOUNDARY.md`. |

---

## Maintenance Rules

- Add every new node idea here first, even if it is Concept-only.
- When the overhaul renames or absorbs a Live node, update `Maps from` rather
  than deleting history.
- Keep status changes in sync with `MASTER_BUILD_PLAN.md` phases and
  `PROJECT_BACKLOG.md` design entries.
- Taxonomy placement questions (which family, group, or section) are decided
  by the Core Simplification Rule in `PHASE_17_NODE_VISUAL_IDENTITY.md`.

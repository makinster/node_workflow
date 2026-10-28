# Node Catalog

**Status:** Living inventory — created 2026-06-12.
This is the complete inventory of every node idea in the project: implemented,
planned, deferred, and concept-only. Nothing gets lost here. When the node
overhaul implements, defers, or rejects a node, update its status — do not
delete the row.

Node Standards owns taxonomy, metadata and I/O authoring rules;
UI Quick Reference owns selector behavior. Use Current State for delivery status.

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
| Simple File Read | Live | `file_reader_node` — read an entire configured file or typed upstream/Vault file reference as a UTF-8 string, published downstream and/or to typed Vault. Accepts copied quoted paths and converts Windows paths under WSL; reports actionable path/read errors. Tags: File I/O, Runtime Resource |
| Bulk File Read | Concept | Read all files matching a folder path or glob pattern. Tags: File I/O |
| Find & Extract Passage | Concept | Search for a pattern, return surrounding context window. Tags: File I/O |
| Structured File Read | Concept | Parse CSV or JSON into usable object data. Tags: File I/O |
| AI-Guided Read | Concept | Provide a file and a question; AI extracts the relevant portion. Tags: File I/O, AI |

File Reader accepts a file reference from Upstream/Vault or
a configured path, then emits the file contents as a typed `string` downstream
and/or to Vault. The existing `file_reader_node` preserves old graphs; see
[PAYLOAD_FILE_IO_BUILD_PLAN.md](archive/PAYLOAD_FILE_IO_BUILD_PLAN.md), P2a.

### Group: Text files (In → Files)

| Node | Status | Notes |
|------|--------|-------|
| Read lines | Built for review | `read_lines_node` — allowed UTF-8 file excerpt, inclusive/negative line positions, From from upstream/Vault/configured, Around ±5, Last/First list selection. Excerpt [string], standard forwarding and Vault. [Contract](SMALL_WINS.md). |
| Find lines | Built for review | `find_lines_node` — literal per-line search, Match case on, latest 100 matches by default in ascending order; Line numbers [var] and optional Vault Match count [number] containing the true total. Allowed folders and bounded reads. [Contract](SMALL_WINS.md). |

### Group: Data Source

| Node | Status | Notes / Maps from |
|---|---|---|
| HTTP Request | Live | `http_request_node` — make an HTTP GET or POST request and forward the response body. **Response as** `file` saves the raw bytes (binary-safe) to a run-owned file and outputs a `file` ref (deleted when the run succeeds unless **Keep the response file** is on; kept when the run fails). **Body from** `input` POSTs the node's input (text as is, anything else as JSON), e.g. an error payload to a notification service. Failures (including socket timeouts) carry a code (`missing_url`, `timeout`, `network`, `http_status`) and go to the default error handler, unless the node's Errors tab catches them. Group `Web Request`, section `Web`. Tags: Internet |
| Disk space | Live | `disk_space_node` — free space, used percent or total size [number] of the drive holding a folder; runs no command (`shutil.disk_usage`). Codes `folder_missing`, `not_allowed`. Group/section `System`. Tags: System |
| Git status | Live | `git_status_node` — runs only `git rev-parse` (to find the repository, which must itself be allowed) and `git status --porcelain=v2 --branch -z` (argv, no shell, 15 s timeout, own process group killed on stop; repository-configured programs such as `core.fsmonitor` are turned off) and reports Clean [bool], Branch [string], Changed files [var] or Commits ahead [number]. Codes `folder_missing`, `not_allowed`, `not_a_repository`, `git_missing`, `timeout`, `git_failed`. Group/section `System` |
| File age | Live | `file_age_node` — time since a file or folder last changed [number], in minutes, hours or days; runs no command. Codes `folder_missing`, `not_allowed`. Group/section `System` |
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

Output family membership does not imply termination or a completion checkbox.
Text Output, File Write and File Manager continue when connected; a route with
no next connection ends naturally. The registered `end_node` explicitly ends
its branch and can be placed with workflow authoring. The TUI selector hides
End (and Start); see [Current State](CURRENT_STATE.md) for the owner decision.
End Branch below is a proposal, not a substitute already available in the app.

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
| File Write | Live | `file_output_node` — write content to a path and emit a typed `file` reference (FO1). Overwrite / Append / Prepend / Create unique is a mode select — one node, not two types. `Open after write` (FO5) opens the file in its OS-default app at a placement preset (D3) with opt-in `Close when run ends` (default off, D12); discovery failure degrades to opened-but-unplaced, never a node error (D4). Inside a repeat/counter loop, open-after-write opens one window per iteration (one per file with Create unique); a validator warning for that is backlog, not FO5. Absorbed the retired `example_file_instance_node` stub's unified-spec reference role. Tags: File I/O, Runtime Resource |
| Structured Write | Concept | Serialize an object to CSV or JSON. Tags: File I/O |
| File Delete | Concept | Remove a file; output: bool success. Tags: File I/O |
| File Copy / Move | Concept | Duplicate or relocate a file; input: source + destination. Tags: File I/O |

### Group: Hermes

| Node | Status | Notes |
|---|---|---|
| Notify me | Live | `hermes_notify_node` (C1) — renders Message (`{input}`; blank sends the incoming value), escapes it unless Allow Hermes commands, cuts it to Longest message (default 1,000, at most 3,500) and appends it to the Hermes outbox for a Send to name from Options (never a chat id; never holds the Telegram token). Priority Normal / Urgent (first in the digest, ⚠; does not ring, see the [shared folder](integrations/HERMES_SHARED_FOLDER.md#sound)). Skip repeats for N minutes per Repeat key (default run + node + branch). Forwards its input by default; own result Receipt [var]. Codes `outbox_unwritable` (retryable), `unknown_destination`. Tags: Hermes, Telegram |
| Record event | Live | `record_event_node` (C1) — appends one `event` line (name, one-line summary, optional value) to the Hermes events log; sends nothing. A blank Event name uses the node's name. Skip repeats as above; carries on by default if it cannot write. Forwards its input by default; own result Event id [string]. Code `events_unwritable`. Tags: Hermes |
| Propose memory | Concept | Appends a candidate fact to `memory_proposals.jsonl` for review; never edits Hermes memory (proposal 7.1) |

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

### Direct-add: File Manager

| Node | Status | Notes |
|---|---|---|
| File Manager | Live | `file_view_node` — renamed from File Viewer; stable internal type preserves old workflows. Displays a text/Markdown file inside AOTN (FO3). Emits `FILE_VIEW_REQUESTED`; the frontend pushes `FileViewerScreen` (Textual Markdown for `.md`, plain text otherwise; `Render as` override). Headless runs: event is inert, never a node error. Forwards the file reference downstream. Supports multiple configured files, one selected downstream reference, named typed Vault references for all other files, and unchanged incoming forwarding. Tags: File I/O, Active Output |

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
| Parallel Branch | Live | `branch_node` — unconditional split into 2–64 concurrent paths (`path_a` … `path_z`, `path_aa` …; 64 is a safety limit on run width). Tags: Parallel |
| Error Mux | Live | `error_mux_node` — place it right after a node. When that node succeeds, its output continues on **No error**. On **Source**, pick which of that node's errors to catch (listed in plain words, plus **Any other error**); each pick becomes a recovery branch, named on **Parameters**, and on **Payloads** each branch passes along either the error details or the failed node's input. A caught error does not stop the run: the failed node shows *recovered* and the run carries on down the branch; errors not picked stop for recovery as before. Wiring a node's `error` port into the mux's `error` input still works. Old Path A/B/C configs migrate to branches. Tags: Conditional |
| Simple Conditional Branch | Planned | Bool/flag picks true or false path (2 ports). Tags: Conditional. (`conditional_node` is the legacy ancestor.) |
| Multi-Condition Branch | Concept | Multiple conditions map to multiple named paths. Tags: Conditional |
| AI Conditional Branch | Deferred | AI evaluates a prompt to decide the path. Tags: Conditional, AI. **Strict model constraint:** requires reliable structured output (tool calling or JSON mode); the AI selects from defined branch labels and cannot invent a path. Supported-model list will be stricter than conversational AI nodes. |
| Loop Branch | Concept | Repeat a path N times or until a condition exits (loop body + exit ports). Tags: Conditional |
| Weighted Branch | Concept | Probabilistic path selection (A/B testing within workflows) |

#### Group: Merge

| Node | Status | Notes / Maps from |
|---|---|---|
| Standard Merge | Live | `merge_node` — wait for all selected branches, then continue. Input slots use the Branch path names; five by default (`input_slots`), raised by the editor when it closes more branches. Tags: Parallel |
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
| Wait Until | Live | `wait_until_node` — pause until the selected target nodes have completed in the current run (corrected 2026-10-11; it never waited on a Vault key). Fails with a clear error naming the target when that target can no longer complete (structural rule D5, never a timeout); its own `timeout_seconds` still bounds the wait when set. Tags: Triggered, Conditional |
| Fixed Delay | Live (debug) | Absorbs `sleep_node` — wait a duration then continue |
| Timeout Guard | Concept | Continue with an error signal after a limit expires |
| Debounce | Concept | Wait until a burst of rapid changes settles |

### Removed from taxonomy

| Node | Status | Notes |
|---|---|---|
| Start | Removed | `start_node` exists in the runtime but is auto-generated — never user-addable |
| End | Live; hidden in TUI selector | `end_node` explicitly terminates its branch; workflow authoring can place it. `record_line` ("Add a line to the output", on by default; saved Ends without it keep their line) adds `[END] <line>`; off, the End adds nothing, so a silent scheduled check prints nothing |

---

## Utility (`primary_family: Utility`)

### Group: Saved values

Values a workflow keeps for its next run (C2, owner 2026-10-21), in
`<data dir>/stash/saved.json` next to the Stash; see
[Saved values](STASH_PROPOSAL.md#saved-values-c2). "Kept for" / "Look in":
This workflow (by its name; renaming the workflow moves them) or All workflows.
Codes `store_unwritable` and `store_unreadable` are retryable. A blank Saved
as is a validation error (`saved_name_missing`). Remember and Recall send
their own value on by default; "Forward incoming payload unchanged" sends the
incoming payload instead, and their Vault output still gets their own value.

| Node | Status | Notes |
|---|---|---|
| Remember | Live | `remember_node` — saves Value (incoming payload, Vault key or Configured text) under Saved as. How: Replace, or Add (a counter; nothing saved counts as 0). Own result Saved value [any] (the new total with Add), optionally also to the Vault. If it can't be saved: Stop (default) or Carry on (the incoming value goes on). Codes `not_a_number`, `too_big` (over 64 KB or not plain data) |
| Recall | Live | `recall_node` — reads the value saved under Saved as. Type (any, string, number, bool, var, file) is the output's type and is strict (`wrong_type`). If nothing is saved yet: the Starting value read as the Type (blank: "", 0, false or nothing), or Stop (`not_saved`) |
| If changed | Live | `if_changed_node` — compares Value with the one saved last time (Exactly, or ignoring spaces and capitals), saves it, then takes **Changed** or **No change**, each carrying the value; compare and save are one locked step. First run (nothing saved yet): No change · save quietly (default) or Changed · send it on. If it can't be saved: Stop, or Carry on (takes No change). The H3 change detector |

### Section: Windows

| Node | Status | Notes |
|---|---|---|
| Window Control | Live | `window_control_node` — focus / minimize / close the OS window showing a workflow-owned file, targeted by its `file` reference (FO6, D6: file identity, never app type). Missing/vanished window is a soft warning + pass-through. Supersedes the deferred **Window Focus** concept below for workflow-owned file windows; arbitrary named-app targeting stays out of the catalog. Tags: File I/O, Window |

### Section: Automation

#### Group: UI Automation

| Node | Status | Notes |
|---|---|---|
| Mouse Click | Concept | Click a screen position or element by label |
| Type Text | Concept | Send keyboard input to the focused application |
| Key Press | Concept | Fire a key combination (an action, not a listener — listeners are Triggers) |
| Read Screen | Deferred | Capture visible text or image from a screen region |
| Find Element | Deferred | Locate a UI element by text or accessibility label |
| Window Focus | Superseded | Resolved 2026-07-11: `window_control_node` (Section: Windows above) scopes focus to workflow-owned file windows per D6. Arbitrary named-app-window targeting is intentionally out — app-type targeting is a race condition dressed up as a feature |

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

| Node | Status | Notes |
|------|--------|-------|
| Check reply | Built for review | `check_reply_node` — strict JSON object against compact Field/Type/Required rows. Valid → parsed record [var]; mismatch → existing error path, “Reply didn't match.” Standard forwarding, Vault, and optional configured long-text preview/editor. [Contract](SMALL_WINS.md). |
| Node catalogue | Built for review | `node_catalogue_node` — bounded live authoring contracts, Debug opt-in, filters, Compact/Detailed, Text/JSON, optional Continue and Vault. [Contract](integrations/META_NODES.md). |
| Check workflow spec | Built for review | `check_workflow_spec_node` — shared `build --check` validation of JSON text; parsed spec continues or bounded problem list on error. Optional Check report Vault, no library write or execution. [Contract](integrations/META_NODES.md). |
| Context Pack | Built for review | `context_pack_node` — ordered Label/Source facts, shared redaction, bounded trimming, optional per-run info/errors. Context pack [string], standard forwarding and independent Vault copy. [Contract](NODE_STANDARDS.md#context-pack-owner-2026-10-25). |


#### Group: Data Transform

| Node | Status | Notes / Maps from |
|---|---|---|
| Set Variable | Live | `set_variable_node` — write a named Vault entry. Duplicate `variable_setter_node` is also registered; consolidate to one type during the overhaul |
| Get Variable | Live | `get_variable_node` — read a named Vault entry. Duplicate `variable_reader_node` is also registered; consolidate to one type during the overhaul |
| Concat | Live | `concat_node` — join multiple text strings |
| Text Transform | Live | `text_transform_node` — uppercase, lowercase, strip, title, reverse, markdown format (FO2: heading/list/table tidy + optional paragraph re-flow via `backend/text_format.py`). Regex/find-replace/split still concept-stage |
| JSON / Object Transform | Live | `json_path_node` — extract a value from a JSON string by dot-path (e.g. `user.name`). Invalid JSON fails with code `invalid_json` and goes to the default error handler, unless the node's Errors tab catches it. Broader reshape/multi-field extraction still concept-stage |
| Random Number | Live | `random_number_node` — produce a random integer or float within a configured range |
| Math / Comparison | Concept | Arithmetic or comparison; output: value or bool |
| Format Text | Concept | Interpolate vault/transient values into a template string (lives in this group, not direct-add) |

### Section: Debug

Direct-add nodes intended to survive into finished workflows for logging,
inspection, and pacing.

| Node | Status | Notes / Maps from |
|---|---|---|
| Echo | Live | `echo_node` — converts input to text, optionally prefixes `[label] `. Use No-Op for unchanged payload identity. Tags: Utility |
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

Direct add: **Ask local model** (`ask_local_model_node`), built for review.
One text Question plus optional Context; native Ollama, optional JSON,
per-node tuning, Answer and optional Vault Run details.
[Contract](integrations/LOCAL_MODEL.md).

Direct add: **Ask Claude** (`ask_claude_node`), built for review. One text Question,
optional Context, effort, model setting/override, JSON option and optional Vault
Run details. Official SDK, Secrets-only key. [Contract](integrations/ASK_CLAUDE.md).

#### Group: AI Processing

| Node | Status | Notes / Maps from |
|---|---|---|
| Ask Hermes | Built, profile CLI | `hermes_ask_node` — one question, text Answer and optional Vault-only Run details, standard forwarding, private records and visible usage. Dedicated profile CLI, strict disabled-tool preflight and checked CWD; no internal Hermes imports. [Contract](integrations/ASK_HERMES.md). |
| Jev: Pick one | Built, owner review | `pick_one_node` — one exact answer from configured rows, plain text downstream and optional Vault copy. Confidence below the cutoff sends `unsure`; optional Pick details is Vault only. Secrets-store key, bounded shared client, no provider/model selectors. |
| Chat Completion | Live | `chat_completion_node` — real Anthropic call via `backend/llm_provider.py` (curated model dropdown, secrets-store API key). Session persistence via "Keep active AI session" + vault `ai_session` key; continuation input extends prior sessions. Tags: AI |
| Image Generation | Live (stub) | `image_generation_node` — image from text prompt; output: image path. Tags: AI |
| Embedding | Live (stub) | `embedding_node` — text to vector; output: float array. Tags: AI |
| Vision / Multimodal | Concept | Analyze an image alongside a text prompt. Tags: AI |
| AI Tool Call | Concept | LLM with structured function/tool calling; output: structured result. Tags: AI |
| AI Decision | Concept | Multi-step reasoning returning a named, categorized decision. Tags: AI |

**AI node direction (owner, 2026-10-22):** simple, single-purpose nodes
with tailored fields. Jev: Pick one starts a line of Jev nodes; later Yes/No
or Score nodes reuse `backend/integrations/jev.py`. This node has one fixed
service/model contract; no provider or model picker. Existing Chat Completion
keeps its curated choices. Selector sorting is a separate backlog item.

#### Group: Subworkflow *(Step 4 design)*

| Node | Status | Notes |
|---|---|---|
| Subworkflow | Live (4c-1: Node Config, picker and map; watching a call from the Execution screen is 4c-2) | `subworkflow_node` — calls a saved subworkflow by id as a child run and waits. Inputs come from a configured value, the incoming payload or a Vault key; each result goes to the next node, the Vault (default key: the result's name) or both. Failures are coded (`child_not_found`, `child_input_missing`, `child_input_invalid`, `child_failed`, `child_output_conflict`, `depth_limit`, `capacity_limit`) and routable on `error`. See [Subworkflows proposal](SUBWORKFLOWS_PROPOSAL.md). |
| Parallel Subworkflow | Concept | Separate node not required by the approved design: Run Subworkflow calls may overlap on ordinary parallel branches (C15). Retained as a library idea. |
| Conditional Subworkflow | Concept | Run a workflow only if a condition passes. Tags: Conditional |

### Section: Triggers

#### Group: Trigger

> 2026-10-11: start triggers launch a new run per event through a shared
> event-source layer ([DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) step 5, decision D2). A wait-for-event node in the
> middle of a workflow is an open question in that plan.

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
- Keep status changes in sync with `CURRENT_STATE.md`, the owning plan and
  `PROJECT_BACKLOG.md` design entries.
- Taxonomy placement questions (which family, group, or section) are decided
  by the Core Simplification Rule in `NODE_STANDARDS.md`.

## Taxonomy intent retained from Phase 17

The five families should help a user recognize data entry, user-facing output,
flow structure, quiet utility work and structurally complex behavior quickly.
Group by port/config shape as Node Standards describes; avoid base nodes placed
on the canvas, per-group bespoke UI and artificial Overwrite/Append node splits.
AI nodes are grouped by capability, with curated supported models; a future
per-model split needs real capability pressure, not speculation. Output-display
nodes and reusable workflow libraries remain ambitions, not an assertion that
every concept in this catalog is implemented. Use `aotn nodes` / `describe` for
live contracts and Current State for delivery status.

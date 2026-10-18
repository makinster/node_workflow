# Subworkflows and Contracts — Step 4 Design Proposal

**Status:** **approved design** (owner, 2026-10-18), revision 4. Revision 4 records the follow-up decisions C26–C28 and changes to C1, C3, C7, C11, C16, C17 and C24. Revision 3: Revision 2
answered the review of revision 1; revision 3 records the owner's answers
(§7) and two design changes they led to: the Start node overhaul (C1, C2)
and an Execution screen overhaul before the subworkflow UI. The summary and
order live in [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) Step 4;
this file holds the detailed decisions until Step 4 is complete, then it is
archived. Stash S5 is designed in.

## 1. Why this step matters

Step 4 is where AttackOfTheNodes stops being "one long graph" and becomes a
tool for **long, complex workflows built from smaller, trusted pieces**. A
parent can call "Extract documents", "Analyse results" and "Publish report";
each child has its own branches and helpers. The caller only needs to know a
child's inputs, outputs and failures. The CLI, future triggers and the
server fill the same contract.

The structure quickly becomes a tree with repeated calls:

```
Main run ── Branch A calls ──► Extract (child run) ──► Helper (invocation 1)
         └─ Branch B calls ──► Enrich  (child run) ──► Helper (invocation 2)
```

Both branches can wait on their children at the same time, and each helper
invocation needs its own identity, state and lifetime even though both run
the same saved workflow. The design below is built around that picture.

## 2. What exists today (checked against `main` at `714f190`)

- **One run per backend stack.** `MasterState` holds a single `_run`;
  starting a run cancels leftover tasks and clears the memory bank. A child
  run therefore cannot share the parent's stack.
- `RunService.create()` builds a complete headless stack. Its `RunHistory`
  reads **every saved history record from disk** when constructed, so a stack
  per call has a real cost.
- **Run files are deleted inside the engine.** `MasterState._record_run`
  calls `run_session.close_all(delete_run_files=succeeded)` before
  `RunService.wait()` returns. Anything that must survive a child (a
  returned file) has to be handled **before** that point.
- **The TUI runs attended with no input provider object.** It answers
  prompts through events and `MasterState.submit_user_input`. A child has
  nothing to "inherit" there; it needs an explicit bridge.
- `RunContext` already has `parent_run_id` and `inputs` (recorded, unused).
  `aotn run --input KEY=VALUE` fills `inputs`.
- **End terminates one branch**, and a workflow can have several Ends,
  including on mutually exclusive paths. Ordinary execution follows **one
  output port** of a node (its first connection), not every port.
- `RunResult.outputs` is the output log (text lines), not named values.
- The `object_list` field type already renders editable rows, so contract
  rows need no new widget.

## 3. Decisions to adopt

D3 (a subworkflow is its own run, linked by `parent_run_id`) is already
decided. Revision-2 changes are marked **(r2)**.

### Contracts

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C1 | Where the contract lives | **(r4)** Start holds the **inputs**: Start is overhauled so its **rows are its typed outputs** (name, data type, required, value, description); these rows *are* the contract's inputs. The **results** are defined on the Return End (C3), and Start's Result tab is a **read-only mirror** of them, blank until a Return End exists | A separate contract editor; results declared on Start and mapped again on the End | Owner, 2026-10-18: Start is the one place a caller's inputs arrive; results declared once, where they are produced |
| C2 | How a Start row reaches inner nodes | **(r3)** Each row uses the routing model other nodes already have: **downstream payload**, **Vault** (under the row's name, or a chosen key), or both. Start keeps **one continuation**: one routed row passes as itself, several as one object (as C11). Run directly, a row's configured value is its default; called as a subworkflow, the caller fills it. The old greeting becomes a default first row `greeting [string]`, migrated when a workflow loads (no file rewrite) | Start writing every input to the Vault only; one port per row | Reuses a model the editor, validator and dropdowns already understand; keeps today's workflows working |
| C3 | How outputs are produced | **(r4)** Exactly **one End is the Return End** (a checkbox) in a callable workflow (C27). Its mapping rows **are the result schema**: name, type, required/optional, and the source (a Vault key or its incoming payload). Results are opt-in: nothing is returned unless it is mapped. Version 1 requires branches to **merge before** the Return End; the validator rejects a callable workflow with several Return Ends, or a Return End on one side of an unmerged branch | Any End may return; every output node returning automatically | Branches that each return would give intermittent results; automatic results would leak internal outputs and change the contract by accident (a blocking change for callers, C8) |
| C4 | When a result exists | **(r2)** Only after the child run has **finished** (every supervisor ended), the Return End ran, and every required output is present and type-checked. A second visit to the Return End (a loop) fails the child with `child_output_conflict` | Publishing at the moment End runs | The caller must never see a partial or changing result |
| C5 | What a run returns | `RunResult` gains **`values`** (named, typed outputs). The output log is unchanged | Replacing the output log | Today's CLI and TUI output keep working |
| C6 | Missing versus empty | **(r2)** An input is *missing* only when it is absent or `None`. `False`, `0`, `""` and empty lists are values. An explicit value that fails its type check is an error (`child_input_invalid`); it never falls through to a Stash binding or default | Truthiness | A deliberate `0` or empty string must not silently become the default |
| C7 | Types allowed across the boundary | **(r4)** Version 1: `string`, `number`, `bool`, **`var`** (a JSON value, copied by JSON round-trip so neither side can change the other's copy) and `file` refs (see C13). The data types are those in `backend/data_types.py`; there is no `object`/`list` type (r2 was wrong). Run-local references such as `ai_session` are **rejected by the validator** in a contract. A folder is passed as a `string` path until a `folder` type exists (C28) | Passing any value | A run-local handle cannot resolve in another run's session |
| C8 | Contract changes | **(r2)** A child change that breaks an existing mapping or connection (removed or retyped input in use, removed output in use, a new required input not mapped) is a **blocking validation error**; additive changes (a new optional input or output) are warnings. Each run records the child's **revision** (a hash of the saved definition) | Warnings only; full version pinning now | Broken calls must not start; the revision makes "which version ran?" answerable without pinning |
| C9 | Child edited mid-run | **(r2)** Each call loads the child's saved definition **at call time** and records its revision. A long parent can therefore run an edited child on a later call; the run record shows it | Snapshotting every child when the root starts | Simple and visible; snapshotting can come with pinning later |
| C10 | Input fill order (every caller) | 1. explicit value (mapping, `--input`, API, trigger) → 2. inputs file (`--inputs-file`) → 3. **Stash binding on this machine** (S5) → 4. the input's default → 5. still missing and required: **fail before the run starts**, listing every missing name | Failing mid-run | From `STASH_PROPOSAL.md` §4.5 |

### Calls and the parent graph

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C11 | How the parent continues | **(r4)** The Subworkflow node has **one success continuation**, `default`, plus `error`. Results are not ports. Each result is routed in the node's **Payloads tab**, like every node's outputs: **downstream, Vault, or both** (Vault key default `<node alias>.<output>`). `default` carries the results marked downstream: one as itself, several as one `var` object. In the editor, results show as indented lines under the call node (`↳ config [file] → vault: config`); Enter opens that row. Errors use the `error` output and, if wanted, an inline Error Mux. Branching after the call stays explicit | One port per output; a separate auto-added result-handler node locked after the call | Execution follows one port; a locked node pair would special-case insert, delete, undo, tombstones, duplication, authoring specs and the validator for no new behaviour |
| C12 | How the parent refers to the child | By **workflow id** (rename-safe), shown by name | By name | Renames (#68) must not break callers; a deleted child is a blocking validation error |
| C13 | Files across the boundary | **(r2)** Hand-over is part of **child finalization**, in this order: (1) the run finishes, (2) outputs are collected and validated (C4), (3) each returned run-owned file is **released** from the child's session (removed from its delete list) and **adopted** by the caller's session, (4) the child's remaining resources close (R4 deletes its other run files on success), (5) the call completes. A file the parent passes **into** a child stays the parent's; a child deletes only files it created. A grandchild's file is handed up one level at a time. If the caller is cancelled before step 3, nothing is adopted and the stopped child keeps its files (R4: kept when not successful) | Adopting after `wait()` returns; copying files | `_record_run` deletes on success before `wait()` returns, so hand-over must happen inside finalization, with exactly one owner at every moment |
| C14 | Calling mode | Call and wait first. Fire-and-forget later on the same mechanism | Both at once | Fire-and-forget needs Step 5's run records to be useful |

### Many calls at once

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C15 | Simultaneous calls | **(r2)** Allowed: two Parallel Branch paths that each reach a Subworkflow node run their children **at the same time**, each in its own stack. "Call and wait" blocks only the calling branch | Serializing all calls | Existing branching already produces this; serializing would make parallel parents slower than their own design |
| C16 | Load limits | **(r4)** Per root run, in Settings: `max_subworkflow_depth` (default **4**, counted as calls below the root) and `max_live_subworkflow_runs` (placeholder default **16**; the 4b concurrency benchmark sets the real default). A call that would exceed either **fails at once** with `depth_limit` or `capacity_limit`, routable on `error`. It never waits for capacity | A queue that waits for free slots | Waiting parents hold slots their descendants need, so a waiting queue can deadlock; failing fast is predictable and visible |
| C17 | Nesting and recursion | **(r4)** **Nesting is supported** (A calls B, B calls C), limited only by C16's depth. Shared helpers (B and D both call H) are allowed. A workflow that can reach **itself** is rejected by the validator in v1; an advanced "Allow recursion" opt-in is a later idea, not planned | Rejecting all repeated use; allowing self-calls now | Owner, 2026-10-18: nesting is the intent; recursion would be interesting but isn't needed now |
| C18 | Stack cost | **(r2)** A child stack shares the process's read-only parts (node factory, settings, secrets, one run-history writer) and builds only per-run parts (bus, workflow map, memory, master state). A benchmark (`benchmarks/bench_subworkflow_calls.py`) measures many short calls with a large saved history before any further optimisation | A fresh `RunService.create()` per call | `RunHistory` re-reads all history from disk on construction |

### The call tree: prompts, cancellation, observability

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C19 | Prompts and recovery | **(r2)** A **run-aware bridge** forwards a child's input and recovery requests to the root's client (the TUI, or the CLI/API providers), each tagged with its **invocation id** and a readable **call path** ("Main › Extract › Helper #2"). Answers go back by invocation id. Requests queue: one prompt is shown at a time, in arrival order | Children always unattended; matching by workflow name | Two simultaneous calls to the same child must be answerable separately |
| C20 | Cancellation | **(r2)** Root Stop cancels every descendant and **waits for each to acknowledge** it has stopped and cleaned up before the root reports STOPPED. Terminating one branch cancels only that branch's pending calls. A cancelled call ends the node as *stopped*, never as an ordinary recoverable error. A child's handled failure is routed on the node's `error` port and sibling work continues. Pause applies to the **whole tree**; a breakpoint in a child pauses the whole tree like one in the root | Fire-and-forget cancellation | Requesting cancellation is not the same as having stopped; cleanup must finish first |
| C21 | Watching a child | Drill in from the Subworkflow row with **breadcrumbs** (Main › Extract); **Esc changes the view only** and never stops anything. **(r3)** Built on the Execution screen overhaul (stage EX): a keyboard-navigable node map like the Editor's, the memory view scoped to the highlighted node (`M` for the whole log), A/D cycling branches. Enter on a call row opens the child's map | A separate run tab; drill-in on today's Execution screen | Owner's direction for the Execution screen; drill-in should use it, not be bolted on |
| C22 | Run records | **(r2)** Every child run records: `root_run_id`, `parent_run_id`, the call-site node id and alias, the parent branch id and visit/attempt, the child workflow id and **revision**, and its invocation id | `parent_run_id` only | "Which of these twenty Summarise runs failed?" must have an answer |
| C24 | Shared memory (owner, 2026-10-18) | **(r4)** A child may declare **shared entries** in its contract (`shared: job_progress [number], read` or `read-write`). The caller maps each to one of its own Vault keys, as with inputs; run standalone (CLI, trigger), the entry is simply local. Permissions only narrow on the way down. Read-write offers only safe operations (increment, append, set-if-unchanged); there is no rollback. A read-write entry can be **exclusive**: the child holds a lease for the call, others can still read the last value, and a second call or parent write to it **fails at once** (never waits); the validator warns when a parallel branch writes a key a call leases. Live progress uses a separate **progress signal**. The contract format reserves the `shared` row kind in 4a; behaviour ships in 4e (read, plus the progress signal) and 4f (read-write, leases) | Children reading the parent's Vault by key name; locks that wait | A child that knows its parent's key names can't run alone; waiting locks deadlock |
| C25 | Prompting children (owner, 2026-10-18) | **(r3)** The norm is a **prompt-free child**. A child's contract shows **"may ask for input"** when it contains a User Input node or an attended recovery point, so a caller sees it before calling. A headless caller (CLI, trigger) fails fast with an error naming the prompting node instead of waiting. The C19 bridge stays for children that do prompt | Forbidding prompts in children | Owner's design philosophy: avoid prompts in subworkflows, but support them when needed |
| C26 | Returning Vault values (owner, 2026-10-18) | **(r4)** A **Return to caller** toggle on any node's Vault output, in its Payloads tab (shown only in callable workflows). It is a shortcut: switching it on adds a Return End row (`config [file] ← Vault "config"`), switching it off removes it. The validator flags a returned key written by several unmerged branches | A separate "global Vault" mechanism | Declare where the value is made, keep one result list |
| C27 | Callable workflows (owner, 2026-10-18) | **(r4)** **Callable** is a property of a workflow (`"callable": true` in the saved file; absent means a standard workflow, so no migration). The File window shows a `[sub]` badge, **Make callable** on a highlighted workflow (the primary path: build and test a standard workflow, then convert) and **New subworkflow**. On conversion, a single End is offered as the Return End; several Ends get a validator message (merge, or pick one). Subworkflow controls (Return to caller, Result tab, Return End checkbox, "may ask for input") appear only in callable workflows; the validator applies callable-only rules; the Subworkflow node's picker lists only callable workflows. A callable workflow still runs directly with its defaults. Converting back keeps result rows but ignores them | Separate editors for workflows and subworkflows | The owner's editor-mode idea, as a workflow property: one editor, a clean split, one switch to convert |
| C28 | A `folder` type | **(r4)** Add a `folder` data type (typed, pickable, owned and cleaned up like run files), alongside 4b or with the Stash's folder import (S4). Until then a folder crosses as a `string` path | Treating folders as files | "Set up a file environment" children need to return folders |
| C23 | Stash bindings (S5) | Per machine, per workflow: `stash/bindings/<workflow_id>.json` maps input name → Stash entry id; never in the workflow JSON. The CLI also accepts `--input key=@stash:name` | Bindings inside the workflow | Portability |

## 4. How it fits together

```
Parent run                                        Child run (own stack, invocation id)
 ... → [Subworkflow: "Summarise file"] ───────►  Start · contract
         inputs:  file ← Upstream payload            in:  file [file], tone [string]
                  tone ← Configured "plain"          out: summary [string] (required)
         results: summary → Vault "Summarise.summary"  ... branches ... → Merge
       ◄── default (payload = summary) / error   Return End: summary ← Vault "summary"
           codes: child_failed, child_input_missing, child_input_invalid,
                  child_output_conflict, child_not_found, depth_limit, capacity_limit
```

- The **validator** loads each child's contract: it type-checks input
  mappings and result keys, applies C8, rejects recursion (C17) and
  unsupported boundary types (C7), and checks the Return End rule (C3).
  Existing race warnings cover two parallel calls writing the same parent
  Vault key.
- **`aotn run`** reads Start's contract: `--input` values are typed (C6),
  `--inputs-file`, Stash bindings and defaults follow (C10). A missing or
  invalid input exits before the run with a new exit code and a list. The
  printed result includes `values`.

## 5. Delivery

Four stages as before, with the foundations widened. 4b may ship as two PRs
if it grows: lifecycle first, then concurrency and the bridge.

| PR | Contents | Done when |
|---|---|---|
| 4a — Start overhaul and contracts | **(r4)** Two PRs. **4a-1 (backend and CLI):** the Start rows and greeting migration, the `callable` flag, the Return End result schema and callable-only validation, result-on-finish with type checks, missing/invalid semantics, boundary types, compatibility errors, revision recording, typed `--input`/`--inputs-file`. **4a-2 (screens, after keymap phase 2):** Start's Inputs and read-only Result tabs, the row editor, the Return End checkbox and mapping, Return to caller, the `[sub]` badge, Make callable (primary flow, with a test) and New subworkflow. Originally (r3): The Start overhaul (C1, C2: typed rows with routing, greeting migration), then C3–C10 and C5 (and the reserved `shared` row kind from C24): the contract on Start, the Return End and its validation (one, after merges), result-on-finish with type checks, missing/invalid semantics, boundary types, compatibility errors, revision recording; `aotn run` consumes `--input`/`--inputs-file` with fail-fast | A contract workflow runs from the CLI with typed inputs and prints its `values`; conditional and parallel paths produce one validated result |
| 4b — Child runs | C11–C20, C22, **(r4)** plus a **concurrency benchmark** (10/50/100/200 children at once, waiting vs CPU-bound, deep chains; time, memory, live objects, cleanup) that sets C16's default: Subworkflow node backend with one continuation and output mapping, per-call stacks sharing read-only services, finalization with file hand-over, simultaneous calls, depth and capacity limits, recursion check, the prompt bridge with invocation ids, tree cancellation with acknowledgement, tree-wide pause, run records, the stack-cost benchmark | Every acceptance scenario in §6 passes |
| EX — Execution screen overhaul | **(r3)** Its own design and sample screens first: the run shown as a keyboard-navigable node map like the Editor's, the memory view scoped to the highlighted node (`M` for the whole log), A/D cycling branches. May need the memory bank to record which node wrote each entry | You can follow a running workflow on its map, node by node |
| 4c — UI | Workflow picker, input mapping and result rows in node config; the Return End checkbox; "may ask for input" on the contract (C25); drill-in with breadcrumbs on the EX screen (C21); prompts labelled by call path | You can build, run and watch a parent/child workflow in the TUI |
| 4d — Stash bindings (S5) | C23: bind inputs from Start's contract and a Subworkflow node's inputs with `P`; `--input key=@stash:name`; C10 step 3 | Set up once in the TUI, then `aotn run wf` works unattended on this machine |
| 4e — Shared read and progress (C24) | Shared entries with live read; the progress signal in the run view | A child reads a parent value that changes during the call; progress shows live |
| 4f — Shared read-write (C24) | Increment, append and set-if-unchanged on shared entries; validator warning for parallel writers | Concurrent increments from two calls are exact; the warning fires |
| later | **(r4)** On Make callable, run the validator automatically with **suggestions** (for example, fold User Input nodes into Start's inputs); an advanced "Allow recursion" opt-in; fire-and-forget; a **family of Return Merge nodes** (first result wins, all required, collect into a list) to relax C3's single Return End; version pinning | After Step 5 |

## 6. Acceptance scenarios

**Contracts and results**
- A required input that is missing fails before the run starts, listing
  every missing name; `0`, `False` and `""` are accepted as values; a
  wrongly typed explicit value fails with `child_input_invalid`.
- A child with Conditional and Parallel paths that merge before the Return
  End returns one result, typed; a loop that reaches the Return End twice
  fails with `child_output_conflict`.
- An object passed in or returned is a copy: mutating it on one side never
  changes the other.
- Removing an input the parent maps blocks the parent's validation; adding
  an optional input only warns.

**Calls and concurrency**
- Two branches call the same child with different inputs at the same time;
  each gets its own result, memory and invocation id.
- Two different children both call one shared helper; validation accepts it.
- One child fails through a handled error path while its sibling succeeds;
  the sibling's result is used and the parent continues.
- A call beyond the depth or live-run limit fails at once with the right
  code; no call ever waits for capacity.
- Many repeated calls release every completed child stack and bus
  subscription (no growth in live objects or subscriptions).

**Files**
- A returned run-owned file survives the child's cleanup and is deleted
  with the **parent** when the parent succeeds.
- A file returned through a grandchild reaches the root intact.
- A parent-owned file passed into a child is never deleted by the child.
- Root Stop during hand-over leaves exactly one owner (the stopped child
  keeps it), never zero or two.

**Prompts and cancellation**
- A grandchild prompts while another child is already waiting for input;
  both prompts are shown in turn, labelled by call path, and each answer
  reaches the right invocation.
- Root Stop while children are starting, waiting, or handing over files
  ends with every descendant acknowledged as stopped.
- Terminating one branch cancels only that branch's calls.
- Esc from a child's view returns to the parent's view; the run continues.

## 7. Owner answers (2026-10-18)

| # | Question | Answer | Effect |
|---|---|---|---|
| 1 | Child prompts | Agreed, through the bridge. Philosophy: avoid prompts in subworkflows, but support them | C19 stays; C25 makes prompt-free the norm and prompting visible |
| 2 | Watching children | Drill-down, on an overhauled Execution screen: a node map like the Editor's, keyboard-navigable; memory scoped to the highlighted node, `M` for the whole log; A/D cycles branches | New stage EX before 4c; C21 builds on it |
| 3 | Limits | Configurable in Settings. Philosophy: do a lot quickly and merge early, but keep wide workflows possible | C16 defaults (4 deep, 16 live) as settings |
| 4 | Start's greeting | Keep a default greeting; overhaul Start into flexible typed outputs, the central place to route a caller's inputs | C1/C2 rewritten; the greeting becomes a default row |
| 5 | Call-and-wait first | As recommended | C14, C15 |
| 6 | One Return End | As recommended for now; later, a family of merge nodes with different return behaviour | C3 stands; Return Merge family in "later" |
| 7 | Success output | As recommended: one result as itself, several as one object, plus Vault mapping | C11 |
| 8 | Shared memory | As recommended | C24, stages 4e/4f |
| 9 | Results | Results tab starts blank and fills from what is returned | C1, C3: results defined on the Return End, mirrored on Start |
| 10 | A result-handler node after each call | An idea; agreed to use the Payloads tab and indented result lines instead | C11 |
| 11 | Declaring returned Vault values | A toggle in the Payloads tab; editor modes for subworkflows | C26 (Return to caller), C27 (callable workflows) |
| 12 | Concurrency and nesting | Benchmark how many subworkflows can run at once; nesting yes, recursion not intended | C16, C17, 4b benchmark |

## 8. Out of scope for Step 4

- Checkpoint and resume after a process crash. Child relationships help
  diagnosis but do not make runs resumable.
- Concurrent independent root runs in one process, triggers and event
  sources (Step 5), the server and authentication (Step 6).
- Version pinning of child workflows (C8's revision recording comes first).
- Sharing or importing other people's workflows.

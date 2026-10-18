# Subworkflows and Contracts — Step 4 Design Proposal

**Status:** proposal for owner review, revision 2 (2026-10-18). Revision 2
answers the review of revision 1: how a branched child produces one result,
how the parent continues, simultaneous calls, file hand-over timing, the
call tree's prompts and cancellation, and contract compatibility. Nothing
here is built. Once approved, the decisions move into
[DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) Step 4 and this file is
archived. Stash S5 (contract inputs bound to Stash entries) is designed in.

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
| C1 | Where the contract lives | **(r2)** One workflow contract, edited on **Start**: input rows (name, type, required, default, description) **and** output rows (name, type, required, description) | Outputs declared per End | One authoritative schema; End nodes fulfil it rather than each defining their own |
| C2 | How inner nodes read an input | Start writes each input into the **Vault** under its name when the run starts; nodes read it with the existing `Source = Vault` | A new per-port source | No new routing concept; the validator and dropdowns already understand Vault keys and types |
| C3 | How outputs are produced | **(r2)** Exactly **one End is the Return End** (a checkbox). It maps each output to a Vault key or its incoming payload. Version 1 requires branches to **merge before** the Return End; the validator rejects a contract workflow with zero or several Return Ends, or a Return End on one side of an unmerged branch | Any End may return; last write wins | Branches that each return would give intermittent results; a merged single return is predictable and can be relaxed later |
| C4 | When a result exists | **(r2)** Only after the child run has **finished** (every supervisor ended), the Return End ran, and every required output is present and type-checked. A second visit to the Return End (a loop) fails the child with `child_output_conflict` | Publishing at the moment End runs | The caller must never see a partial or changing result |
| C5 | What a run returns | `RunResult` gains **`values`** (named, typed outputs). The output log is unchanged | Replacing the output log | Today's CLI and TUI output keep working |
| C6 | Missing versus empty | **(r2)** An input is *missing* only when it is absent or `None`. `False`, `0`, `""` and empty lists are values. An explicit value that fails its type check is an error (`child_input_invalid`); it never falls through to a Stash binding or default | Truthiness | A deliberate `0` or empty string must not silently become the default |
| C7 | Types allowed across the boundary | **(r2)** Version 1: `string`, `number`, `bool`, JSON `object`/`list` (copied by JSON round-trip, so neither side can mutate the other's value) and `file` refs (see C13). Run-local references such as `ai_session` are **rejected by the validator** in a contract | Passing any value | A run-local handle cannot resolve in another run's session |
| C8 | Contract changes | **(r2)** A child change that breaks an existing mapping or connection (removed or retyped input in use, removed output in use, a new required input not mapped) is a **blocking validation error**; additive changes (a new optional input or output) are warnings. Each run records the child's **revision** (a hash of the saved definition) | Warnings only; full version pinning now | Broken calls must not start; the revision makes "which version ran?" answerable without pinning |
| C9 | Child edited mid-run | **(r2)** Each call loads the child's saved definition **at call time** and records its revision. A long parent can therefore run an edited child on a later call; the run record shows it | Snapshotting every child when the root starts | Simple and visible; snapshotting can come with pinning later |
| C10 | Input fill order (every caller) | 1. explicit value (mapping, `--input`, API, trigger) → 2. inputs file (`--inputs-file`) → 3. **Stash binding on this machine** (S5) → 4. the input's default → 5. still missing and required: **fail before the run starts**, listing every missing name | Failing mid-run | From `STASH_PROPOSAL.md` §4.5 |

### Calls and the parent graph

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C11 | How the parent continues | **(r2)** The Subworkflow node has **one success continuation**, `default`, plus `error`. Results are not ports: an **output mapping** writes each result into a parent Vault key (default key `<node alias>.<output>`), and `default` carries the first declared output as its payload. Branching after the call stays explicit (Parallel Branch, Conditional) | One port per output | Execution follows one port; per-output ports would look like they launch several paths, or stop the parent when none is "selected" |
| C12 | How the parent refers to the child | By **workflow id** (rename-safe), shown by name | By name | Renames (#68) must not break callers; a deleted child is a blocking validation error |
| C13 | Files across the boundary | **(r2)** Hand-over is part of **child finalization**, in this order: (1) the run finishes, (2) outputs are collected and validated (C4), (3) each returned run-owned file is **released** from the child's session (removed from its delete list) and **adopted** by the caller's session, (4) the child's remaining resources close (R4 deletes its other run files on success), (5) the call completes. A file the parent passes **into** a child stays the parent's; a child deletes only files it created. A grandchild's file is handed up one level at a time. If the caller is cancelled before step 3, nothing is adopted and the stopped child keeps its files (R4: kept when not successful) | Adopting after `wait()` returns; copying files | `_record_run` deletes on success before `wait()` returns, so hand-over must happen inside finalization, with exactly one owner at every moment |
| C14 | Calling mode | Call and wait first. Fire-and-forget later on the same mechanism | Both at once | Fire-and-forget needs Step 5's run records to be useful |

### Many calls at once

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C15 | Simultaneous calls | **(r2)** Allowed: two Parallel Branch paths that each reach a Subworkflow node run their children **at the same time**, each in its own stack. "Call and wait" blocks only the calling branch | Serializing all calls | Existing branching already produces this; serializing would make parallel parents slower than their own design |
| C16 | Load limits | **(r2)** Per root run: `max_subworkflow_depth` (default **4**, counted as calls below the root) and `max_live_subworkflow_runs` (default **16**, every child and grandchild that has started and not finished). A call that would exceed either **fails at once** with `depth_limit` or `capacity_limit`, routable on `error`. It never waits for capacity | A queue that waits for free slots | Waiting parents hold slots their descendants need, so a waiting queue can deadlock; failing fast is predictable and visible |
| C17 | Recursion | The validator rejects a workflow that can reach itself through Subworkflow nodes; C16's depth limit is the run-time backstop. Reuse of one helper by different children (a diamond) is allowed | Rejecting all repeated use | Shared helpers are the point of reuse |
| C18 | Stack cost | **(r2)** A child stack shares the process's read-only parts (node factory, settings, secrets, one run-history writer) and builds only per-run parts (bus, workflow map, memory, master state). A benchmark (`benchmarks/bench_subworkflow_calls.py`) measures many short calls with a large saved history before any further optimisation | A fresh `RunService.create()` per call | `RunHistory` re-reads all history from disk on construction |

### The call tree: prompts, cancellation, observability

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C19 | Prompts and recovery | **(r2)** A **run-aware bridge** forwards a child's input and recovery requests to the root's client (the TUI, or the CLI/API providers), each tagged with its **invocation id** and a readable **call path** ("Main › Extract › Helper #2"). Answers go back by invocation id. Requests queue: one prompt is shown at a time, in arrival order | Children always unattended; matching by workflow name | Two simultaneous calls to the same child must be answerable separately |
| C20 | Cancellation | **(r2)** Root Stop cancels every descendant and **waits for each to acknowledge** it has stopped and cleaned up before the root reports STOPPED. Terminating one branch cancels only that branch's pending calls. A cancelled call ends the node as *stopped*, never as an ordinary recoverable error. A child's handled failure is routed on the node's `error` port and sibling work continues. Pause applies to the **whole tree**; a breakpoint in a child pauses the whole tree like one in the root | Fire-and-forget cancellation | Requesting cancellation is not the same as having stopped; cleanup must finish first |
| C21 | Watching a child | Drill in from the Subworkflow row with **breadcrumbs** (Main › Extract); **Esc changes the view only** and never stops anything | A separate run tab | Matches how people think about nested calls |
| C22 | Run records | **(r2)** Every child run records: `root_run_id`, `parent_run_id`, the call-site node id and alias, the parent branch id and visit/attempt, the child workflow id and **revision**, and its invocation id | `parent_run_id` only | "Which of these twenty Summarise runs failed?" must have an answer |
| C24 | Shared memory (owner, 2026-10-18) | **(r2)** A child may declare **shared entries** in its contract (`shared: job_progress [number], read` or `read-write`). The caller maps each to one of its own Vault keys, as with inputs; run standalone (CLI, trigger), the entry is simply local. Permissions only narrow on the way down: a child can pass on what it was granted, never more. Read-write offers only safe operations (increment, append, set-if-unchanged); there is no rollback, so a failed child's writes stay visible. The validator warns when parallel calls map the same read-write key. Live progress uses a separate **progress signal** shown in the run view, not memory writes. The contract format reserves the `shared` row kind in 4a; behaviour ships in 4e (read, plus the progress signal) and 4f (read-write) | Children reading the parent's Vault by key name; implicit access to the root's memory | A child that knows its parent's key names only works under that parent and can't run alone; declaring the entry keeps it reusable, testable and visible in its contract |
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
| 4a — Contracts | C1–C10 and C5 (and the reserved `shared` row kind from C24): the contract on Start, the Return End and its validation (one, after merges), result-on-finish with type checks, missing/invalid semantics, boundary types, compatibility errors, revision recording; `aotn run` consumes `--input`/`--inputs-file` with fail-fast | A contract workflow runs from the CLI with typed inputs and prints its `values`; conditional and parallel paths produce one validated result |
| 4b — Child runs | C11–C20, C22: Subworkflow node backend with one continuation and output mapping, per-call stacks sharing read-only services, finalization with file hand-over, simultaneous calls, depth and capacity limits, recursion check, the prompt bridge with invocation ids, tree cancellation with acknowledgement, tree-wide pause, run records, the stack-cost benchmark | Every acceptance scenario in §6 passes |
| 4c — UI | Workflow picker, input mapping and result rows in node config; contract rows on Start; the Return End checkbox; drill-in with breadcrumbs (C21); prompts labelled by call path | You can build, run and watch a parent/child workflow in the TUI |
| 4d — Stash bindings (S5) | C23: bind inputs from Start's contract and a Subworkflow node's inputs with `P`; `--input key=@stash:name`; C10 step 3 | Set up once in the TUI, then `aotn run wf` works unattended on this machine |
| 4e — Shared read and progress (C24) | Shared entries with live read; the progress signal in the run view | A child reads a parent value that changes during the call; progress shows live |
| 4f — Shared read-write (C24) | Increment, append and set-if-unchanged on shared entries; validator warning for parallel writers | Concurrent increments from two calls are exact; the warning fires |
| later | Fire-and-forget; relaxing C3 to several Return Ends with a defined merge rule; version pinning | After Step 5 |

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

## 7. Questions for the owner

The review of revision 1 recommended an answer for each of the first five;
those are now the proposals.

1. **Child prompts:** through the run-aware bridge with call-path labels and
   a queue (C19). Agree?
2. **Watching children:** drill-in with breadcrumbs; Esc changes the view
   only (C21). Agree?
3. **Limits:** depth 4 (configurable, counted below the root) plus a
   live-run limit of 16 per root run, both failing fast (C16). Agree with
   the defaults?
4. **Start's greeting:** kept for compatibility, separate from contract
   inputs. Agree?
5. **Call-and-wait first,** with simultaneous calls from parallel branches
   supported from the start (C14, C15). Agree?
6. **New:** version 1 allows exactly one Return End, after branches merge
   (C3). Acceptable as a starting limit?
7. **New:** results go into parent Vault keys (`<alias>.<output>` by
   default), with `default` carrying the first output (C11). Is that the
   continuation you want, or should `default` carry all results as one
   object?

8. **New:** shared memory (C24) is in: declared shared entries, read first
   (4e, with a progress signal), read-write later (4f). Agreed in chat
   2026-10-18; listed here so the plan records it.

## 8. Out of scope for Step 4

- Checkpoint and resume after a process crash. Child relationships help
  diagnosis but do not make runs resumable.
- Concurrent independent root runs in one process, triggers and event
  sources (Step 5), the server and authentication (Step 6).
- Version pinning of child workflows (C8's revision recording comes first).
- Sharing or importing other people's workflows.

# Subworkflows and Contracts — Step 4 Design Proposal

**Status:** proposal for owner review (2026-10-18). Nothing here is built.
Once approved, the decisions move into
[DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) Step 4 and this file is
archived. Stash S5 (contract inputs bound to Stash entries) is designed in
here, as agreed.

## 1. Why this step matters

Step 4 is where AttackOfTheNodes stops being "one long graph" and becomes a
tool for **long, complex workflows built from smaller, trusted pieces**:

- a workflow says what it needs and what it returns (its **contract**);
- another workflow calls it like a node (a **subworkflow**);
- the CLI, a future trigger or the server fills the same contract.

Everything after this (triggers in Step 5, the server in Step 6) assumes it.

## 2. What exists today (checked against `main` at `714f190`)

- **One run per backend stack.** `MasterState` holds a single `_run`;
  starting a run cancels leftover tasks and clears the memory bank. A child
  run therefore **cannot share the parent's stack**. It needs its own.
- `RunService.create()` already builds a complete headless stack (EventBus,
  WorkflowMap, MemoryBank, MasterState, settings, secrets).
- `RunContext` already has `parent_run_id` and `inputs`. `inputs` is recorded
  but nothing reads it yet. `aotn run --input KEY=VALUE` fills it.
- Start has no inputs: it emits a configurable greeting. End terminates a
  branch and writes a completion message to the output log.
- `RunResult.outputs` is the output log (a list of text lines), not named
  values.
- Run-owned temporary files (`lifetime: "run"`) are deleted when a run closes
  successfully and kept when it fails.
- The `object_list` field type (File Manager's extra files) already renders
  editable rows from an `item_schema`, so contract rows need no new widget.

## 3. Decisions to adopt

D3 (a subworkflow is its own run, linked by `parent_run_id`) is already
decided. These build on it.

| # | Decision | Proposed | Rejected | Why |
|---|---|---|---|---|
| C1 | Where inputs are declared | On **Start**, as a list of rows: name, type, required, default, description | A separate "Input" node per value | One place to read a workflow's needs; the same list drives the CLI, the subworkflow node and Stash bindings |
| C2 | How inner nodes read an input | Start writes each input into the **Vault** under its name when the run starts; nodes read it with the existing `Source = Vault` | A new per-port "contract input" source | No new routing concept; validator and dropdowns already understand Vault keys and types |
| C3 | Where outputs are declared | On **End**, as rows: name, type, and where the value comes from (a Vault key, or End's incoming payload) | Collecting every Vault key | A child returns only what it promises; the parent sees typed ports |
| C4 | What a run returns | `RunResult` gains **`values`**: the named, typed outputs. The output log stays as it is | Replacing the output log | Keeps today's CLI and TUI output unchanged |
| C5 | How a child runs | A **fresh backend stack per child run** (as `RunService.create()` builds), with `parent_run_id` set | Making `MasterState` hold several runs now | Isolation by construction, no rewrite of the engine's run handling; concurrent runs are Step 6's problem |
| C6 | How the parent refers to the child | By **workflow id** (rename-safe), shown by name | By name | Renames (now possible, #68) must not break callers; a deleted child is a clear validation error |
| C7 | Calling mode | **Call and wait** first. Fire-and-forget later on the same mechanism | Both at once | Call-and-wait covers reuse; fire-and-forget needs Step 5's run records to be useful |
| C8 | Input fill order (every caller) | 1. explicit value (subworkflow mapping, `--input`, API, trigger) → 2. inputs file (`--inputs-file`) → 3. **Stash binding on this machine** (S5) → 4. the input's default → 5. still empty and required: **fail before the run starts**, listing what's missing | Failing mid-run | From `STASH_PROPOSAL.md` §4.5; a run never starts half-supplied |
| C9 | Recursion | Validation rejects a workflow that can reach itself through subworkflow nodes; at run time a `max_subworkflow_depth` setting (default **4**) is a backstop | No limit | A loop of calls would otherwise spawn runs without end |
| C10 | Stop and failure | Stopping the parent stops its children. A child that fails, is stopped, or is missing inputs fails the subworkflow node with a **declared error code**, routable on its `error` port (D7) | Letting the child keep running | Predictable cleanup; failures handled like any other node error |
| C11 | Files a child returns | A file output with `lifetime: "run"` is **handed to the parent run** (re-registered there) before the child closes, so it survives the child's cleanup | Copying the file; keeping all child files | A returned file must outlive the child; everything else follows R4 |
| C12 | Prompts and recovery inside a child | The child **inherits the parent's** input provider and recovery policy. In the TUI, a child's question appears like the parent's, labelled with the child workflow's name | Children always unattended | A child that asks for input must still work interactively; headless parents stay headless |
| C13 | Stash bindings (S5) | Per machine, per workflow: `stash/bindings/<workflow_id>.json` maps input name → Stash entry id. Never stored in the workflow JSON. The CLI also accepts `--input key=@stash:name` | Bindings inside the workflow | Portability: the same workflow file runs on another machine after rebinding |

## 4. How it fits together

```
Parent run                                   Child run (own stack, parent_run_id)
  ... → [Subworkflow: "Summarise file"] ──►  Start (inputs: file [file], tone [string])
            inputs: file ← Upstream payload        writes Vault: file, tone
                    tone ← Configured "plain"     ... nodes read Vault ...
                                                 End (outputs: summary [string] ← Vault "summary")
        ◄── ports: summary [string]          RunResult.values = {"summary": "..."}
            error: child_failed / child_input_missing / child_not_found / depth_limit
```

- The **subworkflow node's ports come from the child's contract**: one output
  port per End output, typed (the port model from P1 already resolves ports
  from config). Each input is a mapping row: Upstream payload, Vault key or
  Configured value, the same sources other nodes use.
- The **validator** loads the child's contract to type-check each mapping and
  each downstream connection. It warns when the child's contract has changed
  since the mapping was made (a removed input, a changed type).
- **`aotn run`** reads Start's contract: `--input` values are checked and
  typed, `--inputs-file` fills the rest, and Stash bindings and defaults
  follow (C8). A missing required input exits before the run with a new
  exit code and a list.
- **Run records:** each child run is recorded with its `parent_run_id`, so
  run history and errors can show the call tree.

## 5. Delivery: four PRs, then S5

Each PR is usable on its own and comes with sample screens before any UI.

| PR | Contents | Done when |
|---|---|---|
| 4a — Contracts | Start inputs and End outputs (object_list rows, C1–C4); Start writes inputs to the Vault; End collects `values`; `aotn run` consumes `--input`/`--inputs-file` with typing and fail-fast (C8 steps 1, 2, 4, 5); validator checks contract rows | A workflow with a contract runs from the CLI with typed inputs and prints its `values` |
| 4b — Child runs | `SubworkflowRunner` (fresh stack, C5), call-and-wait, the subworkflow node backend (C6, C7), recursion check and depth limit (C9), stop cascade and error codes (C10), file hand-over (C11), inherited providers (C12) | A parent calls a child and receives typed outputs; stop, failure, missing input and recursion are all tested |
| 4c — Subworkflow node UI | Workflow picker, input mapping rows and contract-driven ports in node config; in the Execution screen, the subworkflow row shows the child's progress and opens it (drill in, Esc back) | You can build and watch a parent/child workflow in the TUI |
| 4d — Stash bindings (S5) | `stash/bindings/<workflow_id>.json` (C13); bind inputs from Start's contract panel and from a subworkflow node's inputs with `P` (S3's picker); `--input key=@stash:name`; C8 step 3 | Set up once in the TUI, then `aotn run wf` works unattended on this machine |
| later | Fire-and-forget calls; parallel children | After Step 5's run records |

## 6. Tests that prove it

- A contract input arrives in the child's Vault, typed; a missing required
  input fails before the run starts, listing every missing name.
- The parent receives exactly the declared outputs, typed, on matching ports.
- Child memory is isolated: the child never sees the parent's Vault, and the
  parent sees only returned values.
- Stopping the parent stops the child; a failed or stopped child fails the
  node with the right code, routable on `error`.
- A self-calling chain is rejected by validation; a deeper-than-limit chain
  fails at run time with `depth_limit`.
- A returned run-owned file survives the child's cleanup; unreturned child
  files follow R4.
- A child's input prompt reaches the TUI (attended) and the provider
  (headless).
- Renaming the child keeps the call working; deleting it is a validation
  error.

## 7. Questions for the owner

1. **Child prompts in the TUI (C12):** is it right that a child's input
   question appears like the parent's, labelled with the child's name? The
   alternative is running every child unattended.
2. **Watching a child (4c):** a drill-in from the subworkflow row (Enter opens
   the child's run, Esc returns) is proposed. The alternative is a separate
   run tab.
3. **Depth limit:** is 4 nested calls a sensible default?
4. **Start's greeting:** keep it as Start's default output alongside the
   contract (proposed), or retire it once contracts exist?
5. **Scope check:** is call-and-wait-first (C7) the right first slice?

## 8. Out of scope for Step 4

Concurrent independent runs in one process, triggers and event sources
(Step 5), the server and authentication (Step 6), per-node keymaps, sharing or
importing other people's workflows, and version pinning of child workflows
(a changed contract is caught by validation instead).

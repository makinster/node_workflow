# Distributed Direction Build Plan

**Status:** approved direction (owner sign-off 2026-10-10/11). The step 1b
and step 3 open decisions were resolved on 2026-10-12 (D5–D9). On 2026-10-12
the owner authorized execution of steps 1, 1b, the refresh coalescer, 2, 3 and
the ESP32 proof slice, using one PR per step; see
[DISTRIBUTED_EXECUTION_PROMPT.md](DISTRIBUTED_EXECUTION_PROMPT.md). **Step 4
onward needs a new go-ahead.**

**Sources:**

- *AOTN Distributed Direction: Investigation Brief* (2026-10-09), with the
  agent investigation of the same day (see SESSION_LOG).
- *AOTN Proposal v2: Wait Registry and Refresh Coalescer* (2026-10-09), with
  its code review.
- The owner's pushback and sign-off thread, 2026-10-10/11.

This plan supersedes the headless-twin, watcher and API sketches in
`PROJECT_BACKLOG.md`. Those sections are kept and carry superseded banners.

## Goal

AOTN becomes a workflow execution layer, a "meta harness", that can run as an
always-on server. The TUI becomes one client among several (CLI, website,
other PCs, AI, hardware endpoints such as ESP32 boards). Integrations stay thin
adapters. AOTN orchestrates other tools; it does not rebuild them.

## Guiding rules

Do not build anything a later step has to undo:

- **Run state is per run.** Nothing new goes on process-wide singletons.
- **One run service.** The CLI, the TUI and the future server all start and
  control runs through the same in-process API. No client reaches into
  `MasterState` internals.
- **Payloads are JSON.** Large or binary data travels by reference (`file`
  refs held by `RunSession`), never as raw bytes in a payload.
- **Every event carries `run_id`**, and `parent_run_id` where it applies.
- **Each step is independently revertable.** Bug fixes are not tangled with
  new interfaces.

## Decision record

| # | Decision | Chosen | Rejected | Why | Date |
|---|---|---|---|---|---|
| D1 | How non-TUI runs get input and recovery choices | `InputProvider` / `RecoveryPolicy` interfaces supplied by whoever starts the run (TUI, CLI, API, AI) | Compile-and-swap export with headless twin node types | Twins double the node catalog and add an export artifact to keep in sync. Providers let the same node ask whichever client launched the run, and the future server needs them anyway | 2026-10-10 |
| D10 | Whether a handled error fails a run | **An error routed along an error path is handled.** Its record carries `handled: true`; a run whose errors were all handled succeeds (exit 0, run files deleted). Unhandled errors still exit 1 | Exiting 1 for every logged error; not logging routed errors | A workflow that catches its own failures (camera busy → notification) did what it was built to do; cron and scripts must not see it as broken. Logging every error keeps the Errors view and run history complete, and `unhandled_error_count` sits beside `error_count` | 2026-10-12 |
| D2 | How triggers relate to runs | A trigger **launches a new run** through the workflow's contract | An always-running watcher: one run that never ends and loops back to its trigger | A run that never ends needs cycles, a `RunSession` that never closes, unbounded output/error caches and timeout exemptions. One run per event keeps runs finite, crash handling per run, and restart as "re-arm the registry" | 2026-10-10 |
| D3 | What a subworkflow is | Its **own run** (`RunContext`) linked by `parent_run_id` | A scope inside the parent run with key prefixes | Gives isolated memory (already required by the backlog). "Call and wait" and "fire and forget" become one mechanism. Per-run eviction keeps working | 2026-10-10 |
| D4 | When per-run state is extracted | **Step 1b**, right after the bug fixes and ahead of `[error]` routing | Later, at the server step | Concurrency, subworkflows and triggers all depend on it. Touch `master_state.py` once, early | 2026-10-10 |
| R1 | Scope of step 1 | Bug fixes only. The unattended policy is one small parameter that later becomes the first `RecoveryPolicy` | Introduce the provider interfaces in step 1 | Fast and revertable, with less merge pain. The interfaces are better shaped once they have two callers (TUI and CLI) | 2026-10-10 |
| R2 | How the unattended policy is supplied | Passed in when the run starts (`start_workflow(unattended=...)`) | A persisted `ConfigurationManager` setting such as "when no UI attached" | `MasterState` cannot tell whether a UI is subscribed, and a persisted value could end up active inside the TUI | 2026-10-10 |
| R3 | What happens when a trigger fires during an active run | A per-trigger concurrency mode. Build `single` and `queued` first, `restart` once Stop is clean, `parallel` at step 6 | One global queue; or leave it to whatever the code does | A burst of motion events must not queue 30 captures, while each doorbell press matters. Dropping silently is the worst outcome, so drops are counted | 2026-10-11 |
| R4 | Binary and intermediate data | Reuse `file` refs with **run-owned temporary files** and a `lifetime` field; **temp files are kept when a run fails** | Add a new `blob` data type now | No change to type lists, labels, pickers or the helper. Cleanup is handled by the run. A `blob` label can be added later on the same field | 2026-10-11 |
| D5 | What "unreachable" means for a waited-on node | **Structural, based on incoming connections, never on a timeout.** A node is unreachable when the source of every incoming connection is final (completed, failed or skipped) and none of them routed to it, and no live supervisor can still reach those sources (this covers loops). A required input that is never delivered (for example one fed from the Vault or a Configured value) stays a data error, not unreachability | Timeout-based detection; basing the rule on inputs marked `required` | Timeouts belong to individual nodes, and later to triggers. Workflows that wait indefinitely for a trigger must not be killed by this rule. In this engine a node runs when a supervisor reaches it through *any* incoming connection, and `required` is only a data flag | 2026-10-12 |
| D6 | Where benchmark scripts live | A top-level `AttackOfTheNodes/benchmarks/` folder (no existing scripts or tooling folder was found). Backend only, no frontend imports | Inside `tests/` | Keeps the normal pytest run fast. `pytest.ini` sets no `testpaths`, so step 1b checks that pytest does not collect the benchmark scripts | 2026-10-12 |
| D7 | How errors are matched | **Stable codes.** Each node declares its codes in error definitions, which are also what the Errors section shows. Every node gets one default generic code, so no error is ever unmatched. The message stays free text for display and logs. A mux with no matching code falls through to the normal failure behavior: a pause in the app, or the failure policy when headless | Matching on message text | Messages get reworded and include variable details, so a text match breaks silently. The validator can check a mux's codes against what the upstream node declares | 2026-10-12 |
| D8 | Where declared errors are shown in node config | **Keep the Connections tab and add an Errors section** | Repurposing tab 4 | Connections is retained by `NODE_STANDARDS.md` and `WAIT_UNTIL_UI_PLAN.md`, and tests depend on it. Confirms the 2026-10-09 recommendation | 2026-10-12 |
| D9 | How skipped nodes behave | **Skipped is its own status, with a reason** (`recovery_skip`, `upstream_skipped`, `not_taken`, `upstream_failed`). It counts as finished for ending the run and for D5, produces no output, and is never reported as completed. Skips spread downstream until the path rejoins something live; this includes the recovery Skip button. Paths never taken are skipped with reason `not_taken`. A Wait Until (later, a wait-for-event node) whose target becomes unreachable fails with `engine.upstream_unreachable` | Treating a skip as completed; today's Skip behavior, which runs the next node with an empty input; leaving untaken paths unmarked; letting the waiter skip itself silently | A run that took a recovery branch must not look like everything ran. The unreachable error can be routed by a mux or falls through to the normal failure behavior | 2026-10-12 |

## Current-state facts this plan relies on

All verified against the code on 2026-10-09/10. Probe scripts were run against
the real backend.

- The backend runs without Textual installed (`demo_execution.py`).
- `http_request_node` and `json_path_node` write failures to an `error` port
  but route via `default`. The node reports `done`, the run finishes, and a
  node wired to `error` never runs.
- With no UI attached, a run blocks forever at:
  - a recovery prompt (`Supervisor._request_recovery`);
  - a user input request;
  - a saved breakpoint.
- `MasterState.stop()` does not release a supervisor parked in Wait Until.
  The run stays `RUNNING`. `start_workflow` clears `_supervisor_tasks` without
  cancelling them, so a stopped run's Wait Until **wakes inside the next run**
  and writes into its memory.
- Wait Until waits for **node completion**, not a Vault key. It waits forever
  when its target:
  - errored and its branch was terminated; or
  - was skipped (Skip never marks the node completed).
- **Merge does not stall** when a sibling branch fails. Branch termination
  releases the merge group (`_account_for_branch_termination`). This corrects
  the Oct 9 report.
- `node_timeout_seconds` effectively bounds nothing. Wait Until and Merge pass
  an explicit `0.0` (wait forever), and no node execution is wrapped in a
  timeout.
- The validator has **no cycle check**. Loops run today, and completion is
  sticky within a run (`completed_nodes` is never cleared per visit).
- A linear run publishes about 5 events per node:
  - `SUPERVISOR_STATE_UPDATE` ×2;
  - `NODE_EXECUTION_UPDATE` ×2;
  - `NODE_TIMING_UPDATE` ×1.

  The App calls `screen.refresh_from_backend()` synchronously for each one,
  inside the engine's publish call, and the execution screen rebuilds fully
  on every call.
- `http_request_node` decodes response bodies as text, so binary content
  (for example a JPEG) is corrupted.
- `ErrorHandler` already persists every error to `run_errors/<run_id>.json`
  when it is logged, and `main.py` configures a rotating log file.

## Steps

| Step | Contents | Gate |
|---|---|---|
| 1 | Bug fixes: error-port routing, Stop/leak, unattended policy — **done** | Owner has read this plan |
| 1b | `RunContext` + WaitRegistry + delivery tracking (D5) — **done** | Step 1 merged |
| — | Refresh coalescer (frontend only) — **done** | Any time |
| 2 | Run service + CLI — **done** | Step 1b merged |
| 3 | `[error]` routing, error codes, Errors section, skipped status (D7–D9) — **done** | Step 2 merged |
| — | ESP32 proof slice — **done** | Steps 2–3 |
| P0 | Housekeeping: handled errors do not fail a run (D10) — **done** | Owner go-ahead 2026-10-12 |
| P1 | Port model: backend `node_output_ports()` resolves each node's ports from its config — **done** | P0 |
| P2 | Error Mux routes: any number of named routes with stable ids; UI pickers and auto-fill — **done** | P1 |
| P3 | Branch on the same mechanism; editor offers `error` on every node — **done** (Branch + Merge slots, owner choice) | P2 |
| 4 | Contracts + subworkflows (Phases 19/20) | Step 3 (after P3) |
| 5 | Event sources + start triggers | Step 4 |
| 6 | Server, API, auth, parallel runs | Step 5 |

### Step 1 — Bug fixes only

**Status: done (2026-10-12, branch `dist/step-1-bug-fixes`).** See
SESSION_LOG for tests and behavior changes.

One commit per fix, so each can be reverted alone. No new interfaces.

**1a. Error-port routing**

- `http_request_node` and `json_path_node` signal failure with
  `{"data": {"error": msg}, "output_port": "error"}`.
- In `Supervisor._run_loop`, a payload routed to `error` whose `error` port has
  no connection becomes a node error. The normal recovery path runs.
- Catch `TimeoutError` (socket timeouts) in HTTP Request alongside `URLError`.
- **Behaviour change to call out in the commit and SESSION_LOG:** saved
  workflows that previously continued silently after a failure will now stop
  for recovery, unless their `error` port is connected.
- Files: `backend/nodes/io/http_request_node.py`,
  `backend/nodes/data/json_path_node.py`, `backend/supervisor.py`, and both
  node specs under `aotn_node_helper/specs/`. Regenerate per `NODE_HELPER.md`
  and preserve the custom runtime bodies.

**1b-fix. Stop and leak**

- `MasterState.stop()` requests stop, then cancels its supervisor tasks.
- `start_workflow` cancels and awaits any leftover tasks before resetting
  state, instead of only clearing `_supervisor_tasks`.
- Known follow-up, not in step 1: there is no `STOPPED` workflow state, so a
  stopped run is still recorded as `FINISHED`.
- Files: `backend/master_state.py`.

**1c. Unattended policy**

- `start_workflow(unattended=None | "terminate_branch" | "terminate_workflow")`.
- The value reaches `Supervisor` as an optional keyword argument with a
  default, so existing callers are unchanged.
- When set:
  - **Recovery:** the error is still logged through `ErrorHandler` and
    persisted, then the policy action is returned without waiting.
  - **Input request:** fails the node with a clear "input required but run is
    unattended" error, which then follows the policy.
  - **Breakpoints:** skipped.
- The TUI passes nothing, so its behaviour is unchanged. This parameter is the
  seed of `RecoveryPolicy` in step 2.
- Files: `backend/master_state.py`, `backend/supervisor.py`.

**Tests.** New `tests/test_run_lifecycle.py`, built from the Oct 9 probes:

- error port connected (routes) and unconnected (recovery);
- Stop releases a waiting Wait Until;
- no wake-up leaks into the next run;
- an unattended run hitting an error, an input request and a breakpoint each
  finishes within a timeout under both policies.

The generated HTTP Request test still passes (`data["error"]` is kept).

**Done when** the full suite passes, compile and `git diff --check` are clean,
and the behaviour change is logged.

### Step 1b — RunContext and WaitRegistry

**Status: done (2026-10-12, branch `dist/step-1b-run-context`).** See
SESSION_LOG for tests, interpretation notes and behavior changes.

- **RunContext.** Extract per-run state into a `RunContext`:
  - memory bank;
  - completions;
  - merge groups;
  - node timings;
  - `RunSession`;
  - `WaitRegistry`;
  - `run_id` and `parent_run_id`.

  `MasterState` creates one per run and hands each supervisor callables bound
  to **its own run**, so a stale supervisor can never mark completions in
  another run. The Supervisor constructor stays backward compatible.
- **WaitRegistry** (`backend/wait_registry.py`) follows proposal v2, with
  these review changes:
  - It lives inside `RunContext`, not beside `MasterState`.
  - Stopped waiters get a `stopped` result rather than a raised
    `CancelledError`, which would confuse `asyncio.timeout`/`TaskGroup`
    bookkeeping.
  - Any unreachable key fails a wait-for-all at once.
  - Merge is left alone; it already releases correctly when a sibling ends.
  - Completion stays sticky per run. Keys are tuples, `("node", node_id)`, so
    a visit or iteration number can be added later without an API change.
- **Delivery tracking (D5).** One new piece of per-run state in `RunContext`
  serves both D5 now and D9 in step 3. It records:
  - which outgoing connections each finished node actually routed along;
  - each node's final state (completed, failed, skipped).

  When a supervisor finishes a node or terminates, re-evaluate each pending
  wait key against D5. A key is unreachable when:
  - every incoming connection's source is final;
  - none of those sources delivered to the target;
  - no live supervisor can still reach those sources. Check this with the
    existing `WorkflowMap.nodes_reachable_from` (`backend/workflow_map.py`).

  Then call `mark_unreachable`. This rule never uses a timeout.
- **Wait Until on an unreachable target** fails with a clear message naming
  the target, instead of waiting forever. This fixes the Oct 9 hang where the
  target was terminated or skipped. The code `engine.upstream_unreachable` is
  added in step 3. Timeouts remain per node (Wait Until's own
  `timeout_seconds`).
- **Proposal v2 Task 0** (the audit) is largely answered by the facts above.
  Task 1 Case B (refresh rate) must be measured with a mounted
  `ExecutionScreen`.
- **Benchmarks (D6):** commit scripts to `AttackOfTheNodes/benchmarks/`,
  backend only. Confirm that a plain `pytest` run from `AttackOfTheNodes/`
  does not collect them; name files `bench_*.py` and keep them out of
  `tests/`.
- **Tests:**
  - the WaitRegistry unit tests from proposal v2;
  - Wait Until fails, rather than hangs, when its target's branch is
    terminated;
  - a target with no incoming connections is unreachable at once;
  - a target inside a loop is not marked unreachable while a live
    supervisor can still reach it;
  - a long Wait Until on a reachable target is never failed by the rule.

### Any time — Refresh coalescer (frontend only)

**Status: done (2026-10-12, branch `dist/refresh-coalescer`).**

- Coalesce (update state, mark dirty, refresh on a timer):
  `NODE_EXECUTION_UPDATE`, `SUPERVISOR_STATE_UPDATE`, `NODE_TIMING_UPDATE`,
  `MEMORY_UPDATE`, `SUPERVISOR_REGISTER`, `SUPERVISOR_TERMINATING`.
- Act at once and flush: `USER_INPUT_NEEDED`, `RECOVERY_OPTIONS_AVAILABLE`,
  `WORKFLOW_STATE_UPDATE`, `ERROR_LOGGED`, `ERROR_OCCURRED`.
- Use a 75 ms named constant, and expose a flush method for tests.
- Files: `frontend/app.py` plus the execution-screen tests.

### Step 2 — Run service and CLI

**Status: done (2026-10-12, branch `dist/step-2-run-service`).** See
SESSION_LOG for the API, the deviations and the behavior changes.

- **In-process run API:** load, validate, start (with inputs and a policy),
  subscribe to events, submit input or recovery, stop, get result.
  **Validate on start**: `start_workflow` does not validate today.
- **`RecoveryPolicy` and `InputProvider` interfaces (D1).** They are shaped by
  their two real callers, TUI and CLI. Step 1's `unattended` value becomes the
  first `RecoveryPolicy`.
- **Configurable data directory**, done before the CLI. The anchor in
  `persistence.py` and the logs path in `main.py` become an env var or config
  file.
- **CLI `aotn run <workflow>`:**
  - errors printed to stderr from `ERROR_LOGGED`;
  - a meaningful exit code;
  - stdin `InputProvider` when interactive, policy-driven when not.
- Move logging setup out of the TUI-only `main.py` path.

### Step 3 — `[error]` routing

**Status: done (2026-10-12, branch `dist/step-3-error-routing`).** See
SESSION_LOG for interpretation notes, open items and the logged behavior
changes.

- **Payload schema:** versioned JSON with:
  - a namespaced `code` (`engine.*` vs node-declared);
  - `node_id`, `run_id`, stage, message;
  - raw details (stderr, response body, exit code);
  - `retryable`;
  - the `ErrorHandler` record id.
- **Lifetime:** never written to the Vault or to a file. It lives on the
  transient store for the run like any payload. The durable record is
  `run_errors/` plus the log; there is no clear-on-read.
- **One engine-level `error` port name** for every node, so port shapes stay
  uniform.
- **Declared errors (D7):** an `errors:` list in helper specs (code,
  description, retryable), emitted as a class attribute and exposed by
  `NodeFactory`.
  - The factory adds one default generic code (`node_error`) to every node,
    so nothing is ever unmatched.
  - Engine codes such as `engine.upstream_unreachable` share the namespaced
    scheme.
  - The message stays free text.
  - This needs generator parsing/validation, a generated test asserting the
    codes, and a `ui_checks` check that the section renders.
- **Errors section (D8):** keep the Connections tab and add an Errors section
  listing each declared code with its description, including the default
  generic entry. It is presentation of `NodeFactory` metadata only.
- **Error mux (D7).** Matches on codes. Put the linked-path check before
  `_request_recovery`:
  - a matched code routes along `error` to the mux path;
  - no match falls through to the normal failure behavior: a pause in the
    app, or the run's failure policy when headless.

  The validator checks that the mux's codes appear in the upstream node's
  declarations.
- **Skipped status (D9).** Built on step 1b's delivery tracking.
  - `skipped` is published as a `NODE_EXECUTION_UPDATE` status with a `reason`
    field: `recovery_skip`, `upstream_skipped`, `not_taken` or
    `upstream_failed`.
  - It counts as finished for run completion and for D5, produces no output,
    and is never reported as completed. `mark_node_completed` is not called
    for it.
  - Skips spread: when a node's incoming-connection sources are all final and
    none delivered, it is marked skipped and the evaluation continues
    downstream. The spread stops at any node that still has a live or
    delivering source (for example a Merge with a live sibling).
  - Untaken paths (the other port of a Conditional, or the default path after
    an error is routed to `error`) are skipped with reason `not_taken`.
  - Shown distinctly in the execution screen (precedence in
    `frontend/execution_state.py`), in run history and in logs.
  - A Wait Until whose target becomes unreachable now fails with
    `engine.upstream_unreachable` (step 1b's message gains the code).
- **Behavior changes to log on landing:**
  - The recovery **Skip** button no longer runs the next node with an empty
    input. Its downstream path is skipped until it rejoins something live.
  - Untaken paths now show as skipped rather than having no status.
- **Tests:**
  - skip spreading through a linear chain;
  - rejoining at a Merge with a live sibling;
  - a not-taken Conditional port;
  - routing to the error port marks the default path skipped;
  - recovery Skip spreads;
  - Wait Until on a skipped target fails with `engine.upstream_unreachable`;
  - a mux with no matching code falls through to the policy;
  - a skipped node is never counted as completed.

### ESP32 proof slice (between steps 3 and 4)

**Status: done (2026-10-12, branch `dist/esp32-proof-slice`).** See
SESSION_LOG.

The pipeline: cron runs `aotn run capture` → an HTTP node GETs `/capture` and
saves the bytes as a run-owned `file` → the `error` port routes to a
notification (HTTP POST, for example ntfy or Telegram).

It needs:

- **A binary-safe HTTP mode** that writes response bytes to a file ref instead
  of decoding them.
- **Run-owned temp files (R4):**
  - written under `run_files/<run_id>/` in the data directory;
  - registered with `RunSession`;
  - file refs gain `lifetime: "run" | "kept"` (absent means `kept`, so old
    refs are unchanged);
  - `run` files are deleted when the run closes successfully and **kept when
    the run fails**, for debugging;
  - a node can mark a file `kept`.

It can be tested against any HTTP endpoint before hardware arrives.

### Spin-off — port model (P0–P3, before step 4)

Approved 2026-10-12. Today a node's ports are fixed class lists
(`output_ports`), and Branch hides unused `path_*` ports in two copies of
UI-only logic. The backend should own the port shape and the UI should own
field entry.

- **P0 — Housekeeping.** D10 (handled errors); this table's ESP32 row.
- **P1 — Port model refactor, no behavior change.** One backend function
  `node_output_ports(node_data)` (class ports, narrowed or extended by config)
  used by the validator, the editor adapter and both UI helpers, replacing
  the direct `metadata["output_ports"]` reads. Closes the gap where the
  validator accepts a connection on a Branch path that the count hides.
- **P2 — Error Mux routes.** A `routes` list (`id`, `label`, `codes`), any
  number of routes, ports named by stable route id; an optional *unmatched*
  route; old `path_*_codes` configs migrate on load. All entry is UI-only:
  upstream code pickers, auto-fill when `error` is connected, "refill from
  upstream".
- **P3 — Reuse.** Branch uses the same mechanism without the five-path cap;
  the editor offers `error` on every node (the engine already accepts it).

### Step 4 — Contracts and subworkflows (Phases 19/20)

- **Contracts:** typed declared inputs on Start and outputs on End, built on
  port metadata and `backend/data_types.py`.
- **Subworkflows (D3):** a child is its own `RunContext` linked by
  `parent_run_id`. The Phase 19 subworkflow node uses call-and-wait;
  fire-and-forget uses the same mechanism.
- **One contract for every caller:** the subworkflow node, trigger payloads,
  CLI arguments and API calls all use the same contract.

### Step 5 — Event sources and start triggers

- **Event-source layer:** key combination, MQTT, webhook, timer, file change,
  and "workflow finished". Owned by the backend/daemon. OS-dependent sources
  are capability-gated through an adapter, following the `window_manager.py`
  pattern, and report "unsupported" rather than silently never firing.
- **Start triggers (D2):** a stored trigger registry, re-armed on boot. Each
  event launches a new run through the workflow's contract.
- **Persistent store** for state between firings (last-seen, counters),
  separate from `MemoryBank`.
- **Runs recorded when they start**, so a crash shows as "interrupted" rather
  than disappearing.
- **Concurrency modes (R3), set per trigger:**

  | Mode | Behaviour | Build |
  |---|---|---|
  | `single` | Event during an active run is dropped and **counted** | Step 5 |
  | `queued` (max N) | Serial queue with a visible backlog count. The payload is captured when queued. Overflow is dropped and counted | Step 5 |
  | `restart` | Cancel the active run, start fresh | After Stop is clean (step 1 fix proven in use) |
  | `parallel` | Concurrent runs | Step 6 |

  Drop counts are visible to clients. Silent drops are not acceptable.

### Step 6 — Server

- HTTP + WebSocket transport over the step 2 run service.
- Authentication, which is mandatory before any network exposure.
- Encrypted secrets (`secrets/secrets.json` is plain text today).
- `parallel` trigger mode and real concurrent runs. This needs isolation
  beyond `RunContext`:
  - App filtering by `current_run_id`;
  - global EventBus subscribers;
  - file output path collisions.
- Backend telemetry batching, once events cross a WebSocket.

## Open question — wait-for-event node (not decided)

A node in the middle of a workflow that suspends its branch until an external
event arrives, then continues with the event data. Example: some setup nodes,
then wait for a key combination, then carry on. It would be resolved through a
WaitRegistry key such as `("event", source, filter)`, fed by the same
event-source layer as start triggers.

**For**

- Fits the existing "park on one Future" pattern (Wait Until, User Text
  Input).
- Allows setup-then-wait workflows directly.
- Reuses event sources and the WaitRegistry with no API change; it is proposal
  v2's deferred "other wait kinds" item.

**Against / risks**

- A run held open waiting keeps its `RunSession`, memory and caches alive.
- "Wait, act, wait again" needs loop semantics. Loops run today, but
  completion is sticky and there is no per-iteration cleanup.
- When one event matches both a waiting run and a start trigger, something
  must decide which takes it. Suggested: the waiting run.
- Needs an explicit timeout choice and a Stop that releases it, which depends
  on step 1/1b. D5 never uses a timeout, so indefinite waits stay allowed; any
  timeout is the node's own setting. If its event source becomes unavailable,
  the node fails with an engine code (D9).
- Key combinations need an OS capability gate; a headless server may not
  support them at all.

**Alternatives**

- Do the setup once and keep its results in the persistent store; then use a
  start trigger per event.
- Support both, recommending wait nodes for bounded waits and start triggers
  for indefinite repetition.

**Decide by:** step 5 design.

## Doc corrections to carry out as steps land

- `PROJECT_BACKLOG.md`: the claim "cycles are currently rejected" is wrong
  (noted in place).
- `ARCHITECTURE.md` / `SIGNAL_FLOW.md`: describe what `node_timeout_seconds`
  actually covers, `RunContext` and the WaitRegistry (step 1b), the coalescer,
  and the lane rules.
- `NODE_CATALOG.md`: Wait Until description (corrected with this plan).

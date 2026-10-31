# AttackOfTheNodes Architecture

The backend runs a graph of small machines; the Textual UI is its control room.
This reference consolidates the old architecture, project-knowledge, signal-flow
and execution-display documents. [Current State](CURRENT_STATE.md) owns the
checked baseline; [Vision](VISION.md) and [Distributed Build Plan](DISTRIBUTED_BUILD_PLAN.md)
separate intent from delivered behavior.

## Ownership and boundaries

| Component | Owns |
|---|---|
| `WorkflowMap` | Live graph, node/connection CRUD, traversal, dirty state, serialization |
| `NodeFactory` | Registry, config templates, resolved ports and portable metadata |
| `Node` / `NodeContext` | One machine's config and execution; prepared inputs and explicit callbacks |
| `MasterState` | Run control, supervisor tasks, branching, waits, merge coordination and finalization |
| `RunContext` | Run identity, policies, waits, delivery/outcome tracking, groups and timings |
| `MemoryBank` | Named Vault values/type tags and transient port values shared within a run; `writes()` is the run's Vault write log, each write tagged with the node, branch and visit that made it (the supervisor sets `memory_bank.current_writer` each step) |
| `RunSession` | Open resources, chat histories and run-owned temporary files |
| `RunService` | A backend client surface for load, validate, start, wait, input, recovery and stop |
| `OutputManager` / `ErrorHandler` / `RunHistory` | Durable output records, errors and summaries |
| `SaveManager` / `persistence.py` | Save/load orchestration versus raw filesystem I/O |
| `ConfigurationManager` / `SecretsManager` | Known settings versus secret lookup/storage |
| `StashManager` | Reusable machine-local file/text entries, independent of a run |
| `App` / screens | Display cache, navigation, editing affordances, prompts and local path picking |

Nodes are graph-ignorant: `Supervisor` resolves connected inputs before calling
`execute(context)`. Nodes must not inspect neighbors, frontend state or widgets.
Topology-dependent editing stays in frontend adapters using backend graph APIs.
`WorkflowMap` owns graph mutations and dirty state. Tombstones are intentional
backend records, not junk to delete: they preserve the original node/config and
connections for repair and restore. Validation blocks runs containing them.
See [Backend / Frontend Boundary](BACKEND_FRONTEND_BOUNDARY.md) for deletion,
restoration and editor ownership; the older blanket “delete never touches other
nodes” and “merge deletion never rewires” claims are not the complete contract.

`MasterState` and `App` are session singletons in the TUI composition: construct
one of each and register their subscriptions once per session. They are ordinary
classes, not process-global singleton enforcement; tests and `RunService.create()`
can construct independent stacks. One existing stack is not a concurrent-run server.

## Signals, calls and transport limits

`EventBus` is the only inter-component **signal** channel. It invokes callbacks
synchronously in the publisher's thread and logs subscriber exceptions. Commands
and queries also use direct service calls; a supervisor receives callbacks bound
to its own `RunContext` for completion, waits, merge and delivery reports. Do not
replace these ownership APIs with an invented “everything is an event” protocol.

New execution events must carry run identity and JSON-safe facts. This is a
contract for new work, not proof that all existing events are transport-safe:
`SUPERVISOR_REGISTER` still includes the live `supervisor` object consumed by
MasterState, and `MEMORY_UPDATE` is an unscoped change notification. The latter
contains a delta such as `{"change": "set", "key": ...}`, not a memory snapshot;
subscribers query `get_state()` when needed. EventBus does not validate JSON.
A remote protocol must remove those exceptions deliberately.

`NodeContext.emit_event` uses the supervisor's publisher to stamp run, branch
and node identity. `signal_done` and `signal_error` are plain callbacks, not
coroutines. Input and coordination callbacks are awaited. The public dataclass
in `backend/node_base.py` is the exact interface; nodes should not construct it
using an obsolete positional example.

## Storage and resource lifetime

`persistence.DATA_DIR` is the app directory by default, or `AOTN_DATA_DIR`, read
at import time. Set it before backend imports; CLI `--data-dir` does so before
loading the backend. Workflows, settings, secrets, logs, outputs, errors, run
history, run files and Stash storage all derive from that root. Filesystem I/O
belongs in persistence/helpers; workflow interpretation belongs above it.

The Vault's “persistent” name means named values within a run. Values are stored
as supplied; `MemoryBank` keeps optional type tags in a separate dictionary.
Primitive values need not contain a `type` field. Transient keys encode node ID
and port, **not branch ID**: branches share the store, and later writes to the
same node/port can replace earlier values. It is neither a branch-isolated
mailbox nor a per-visit output history. There is no deep-copy or JSON boundary
on every MemoryBank read/write; portable payloads are an authoring contract.

`SaveManager` can optionally include and restore memory snapshots, but starting
a run clears the shared memory instance. That option is not general execution
checkpoint/resume. Workflow saves retain full config; `update_node_config`
replaces it, so callers changing one key must preserve other keys explicitly.
Config migrations run through shared backend helpers, not screen refresh hacks.

Reference values are JSON objects. A file reference contains `type: "file"`,
`ref_key` and `path`, with optional `lifetime`; it does not carry a Python handle.
`RunSession.open_file` caches handles by resolved path/mode; `register_resource`
and `get_resource` provide generic resource lookup. Chat references identify
histories accessed through `get_or_create_chat_session`, `append_chat_message`
and `get_chat_history`, rather than provider-client objects in generic resources.
Typed examples and routing live in [Node Standards](NODE_STANDARDS.md).

`RunSession` closes resources when a run is recorded. Run-owned temporary files
are deleted only on FINISHED with no unhandled errors and no user Stop; failed
or stopped runs retain them for inspection. `keep_file` retains a file explicitly.
A missing lifetime means kept. Files on disk can outlive their run, while live
resource/window registrations do not. Secrets are resolved with `context.get_secret`;
the existing store is plaintext JSON, not an encryption/keychain guarantee.
Stash entries persist separately under the data root; they are not Vault values.

## Start, execute and route

TUI commands call backend services; the headless path is
`main.py` → `aotn_cli.py` → `RunService`, without launching Textual. RunService
validates by default. `MasterState.start_workflow` itself checks that a graph and
Start exist; callers must not assume it performs the full preflight.

1. Serialize starts, cancel and await leftover tasks, then clear runtime memory.
2. Create a new `RunContext`/`RunSession`, set RUNNING and schedule the root.
3. A supervisor checks stop/pause and breakpoints, resolves inputs, then awaits
   `node.execute(context)`. Visits and retry attempts are separate counters.
4. Capture the signal and emit timing from `finally`. Timing is not success.
5. On success, save the completed node ID, publish transient outputs and handle
   routing/branch requests. **Only then mark that saved ID completed** and
   report delivery. Cross-branch waiters must never wake before outputs exist.

Ordinary output routing follows the first matching connection. Extra connections
do not create parallel execution (`ignored_fan_out` diagnoses them). Explicit
branch signals spawn children on their connected paths and end the parent's
path; `spawns_branches` describes that capability. Parallel Branch supports
2–64 paths, while `max_branch_depth` separately limits nesting. A refused depth
is logged; it does not create a child. The child's wired first input reads the
spawning output's transient value, so `initial_data` alone is not enough.

`terminate_branch` ends the path after output publication. A missing next edge
also ends naturally. End explicitly terminates; output family membership is not
termination. Error routing is separate from the ordinary first-edge rule.

## Failure, input, pause and stop

Failures get stable codes from declared `NodeError`, engine errors or generic
`node_error`. The supervisor resolves a connected error route or an inline mux
on the normal output, logs the failure once and routes a versioned failure
record when handled. Display status is `recovered`; delivery outcome still
records failure and the handler target. `error` does not forward the original
input. A mux may explicitly choose its failed-input capability; that is separate.
Unmatched failures go to interactive recovery or the supplied policy.

RETRY adds an attempt within the visit. SKIP marks the failed visit skipped and
ends its branch; it does not run the next node with empty input. Downstream
unreachable nodes receive skip reasons (`recovery_skip`, `upstream_skipped`,
`not_taken`, `upstream_failed`). Handled errors remain durable records but do not
make an otherwise successful run fail. Recovery editor rules are in
[UI Quick Reference](UI_QUICK_REFERENCE.md#recovery-editing).

An attended input request publishes waiting state and a prompt; the frontend
submits through MasterState to the waiting supervisor. A supplied InputProvider
can answer without a modal. Unattended policies use NoInputProvider and fail an
input request; they do not silently invent an answer. User Text Input publishes
its declared Vault answer before successful completion, including an empty answer.
Stopping an unanswered prompt prevents that publication and completion.

Pause is cooperative between nodes. A breakpoint pauses before its node, and
resume skips that same breakpoint once. The setting `node_timeout_seconds`
supplies default node waits, not a timeout around `execute()` or a whole-run
deadline. Wait Until and Merge can pass explicit wait values, including zero.

Stop releases registry waits and cancels supervisor tasks. A task cancelled
before registration is still removed by its done callback. Work already handed
to a thread may continue outside the cancelled coroutine. The next start awaits
leftover supervisor tasks before resetting state; this is not hard cancellation
of external operations. Returning from Execution to Editor calls Stop.
RunService reports STOPPED/exit 130 for its stopped runs, while the engine's
terminal bookkeeping does not add a separate STOPPED enum state.

## Waits and merges

`RunContext` owns `WaitRegistry`, delivery tracking, live supervisors, merge
state and timings. Supervisor callbacks retain their own run context so stale
completion cannot mark a newer run. The TUI still reuses one MemoryBank cleared
at start; child-run isolation/concurrent runs need the planned further work.

Wait Until waits for all selected node IDs. Completion is sticky for the run;
zero timeout waits indefinitely and a positive value limits that wait. The
registry distinguishes completed, stopped and structurally unreachable. The
unreachable check uses final outcomes, delivered edges and live reachability,
not an arbitrary timeout. A missing required value remains a data error.
Targets reachable only through their own parked waiter, or through a Merge that
also waits on that branch, can still deadlock. This is not general deadlock detection.

A Merge collects the values on actual fired edges, not all connected transient
keys. Invocation-local delivery frames preserve simultaneous shared-producer
and Beacon values without isolating the shared Vault/transient stores. Groups
and barriers use `(run, group, pass=1)` / `(run, group, Merge, pass=1)` identities.
Nested forks atomically hand the parent's obligation to their accepted children.
The shallowest arrival continues; ties use first arrival. It publishes the slot
record before the saved Merge ID completes once. Other arrivals are absorbed,
with no node completion/failure/skip; their termination retires the display's
running arrival. End settles a side path; terminal member failure fails the join
once and releases waiters without partial output; user Stop cancels quietly.

`MasterState.start_workflow(merge_plans=...)` accepts run-scoped declarations:
`{merge_id: MergePlan(fork_node_id, {slot: MergeSlot("one" | "many", producers)})}`.
Producer paths are tuples of numeric fork-port indices relative to the group's
root fork, e.g. `(0,)`, `(1, 0)`, `(1, 1)` for A and B's C/D children. They identify
participants as well as shape, so an independent Wait Until on Merge need not
block the join. Empty producer tuples include every actual group member.
A `one` slot keeps its raw value; a `many` slot always lists present values in
structural path order, preserving nested lists. Outer slots use numeric path
order. Missing/control-only values are omitted; null/false/zero/empty survive.
No-group Merge passes the actual arriving value through.

Normal `start_workflow` calls now capture this run's workflow and use
`flow_behaviors.analyze_flow` plus `merge_plans_from_analysis` to derive plans
from that same snapshot used for the revision hash. The adapter only translates
the shared proof; it does not traverse the graph or infer cardinality from
arrivals. This covers the app, RunService and each subworkflow's own map.
Explicit plan dictionaries still override automatic derivation, including an
empty dictionary for unsupported-shape tests. Graph-declared producer lineages
exclude independent side paths from the join, including their terminal failures.

Leaving a Merge closes that group's root and producer paths in the analyser,
matching the continuing supervisor at runtime. A later Branch opens a new group;
sequential split/Merge stages therefore have separate plans. The same structural
walk carries a closed-join marker until a new split, so direct Merge-to-Merge
chains and an inner join feeding an outer join still fail preflight. Two Merges
on separate paths of one split are also refused. No extra graph traversal is used.
The existing draft admission gate is unchanged.

Unproved inputs, already-joined paths, unrelated splits and collecting graphs
beyond analysis bounds are app-validation errors. Direct automatic startup
raises `MergePlanError`, a dedicated `ValueError` subclass, before creating a run.
App Run displays it as `Can't start: ...` and remains usable; subworkflow calls
translate it into the declared, non-retryable `child_flow_invalid` error, which
can be routed through the calling node's error output. Messages say which paths
to reconnect, without exposing the analyser's internal vocabulary.

Sequential groups do not reset supervisor depth. Three sequential stages complete
with `max_branch_depth=5`; at limit 2, the third Branch refuses all its children
with `branch_depth_exceeded`. The shallowest arrival still determines the depth
retained after each join. All coordination state retires per run; old-run
callbacks cannot affect a new run's completion registry.

Five input slots is the default, not a fixed maximum. Frontend configuration
chooses actual slots/Beacon edges through WorkflowMap; refresh is not a license
to silently repair legacy graph connections.

## Finalization and validation

When supervisors and tasks are gone, MasterState captures the shared
`output_log` through OutputManager, sets FINISHED and records the run. Error
paths also capture outputs and record ERROR. The legacy capture rebuilds output
records with `node_id: "output_log"`; it is not a reliable branch/visit provenance
feed. Finalization persists and evicts output/error caches. Historical reads can
load them again. RunHistory caps its in-memory summaries at 500; older files remain.
Resource cleanup and error counts happen in run recording.

Validation scans all nodes/config/connections, not just DFS-reachable nodes;
reachability is an additional pass. It checks node/port existence, tombstones,
source/declaration consistency, numbers, secrets, paths and error routes. Vault
reads/writes use shared declarations; optional unwritten reads and known type
mismatches can be warnings, required reads can be errors, and parallel writers
need ordering diagnostics. The result includes `success`, `errors`, `warnings`;
issues use registered codes and node IDs where applicable. `any` is permissive.
Preflight does not prove runtime types, dynamic side effects or all scheduling.
See `backend/validator.py`, `validation_codes.py`, `port_types.py` and
[Node Standards](NODE_STANDARDS.md) rather than duplicating validation in a client.

## Execution display contract

`NODE_EXECUTION_UPDATE` carries run, branch, node, visit, attempt and status.
Visits start at 1; retry increments attempts, while setup failures can have
attempt 0. Statuses are running, waiting, done, errored, recovered, skipped and
stopped. Timing, branch termination and position changes must never manufacture
node success. Coordination waits are running, not user-input waiting; a global
pause request does not prove an active node has paused.

`frontend/execution_state.py` retains registration order, branch provenance,
ended branches, ordered visits/attempts and timings. Latest-attempt state wins
within a visit; the compatibility node summary prioritizes
`running > waiting > errored > stopped > recovered > skipped > done` across
branches. Earlier visits and attempts remain inspection records.

App checks run IDs, retires cleared runs, and clears state on new runs, workflow
replacement and IDLE. Late events must not resurrect a retired display. This
cache is ephemeral and not a persisted execution history. Long-run retention
and post-stop inspection need separate design decisions.

ExecutionScreen refreshes on modal resume; NodeList updates cards in place when
IDs/order match, preserving selection and scroll. NodeCard refreshes ordinary
status/timing changes explicitly. Skipped/stopped receive text labels rather
than success checks; recovered errors are labelled without a failure cross.
Run-wide durable output and a proposed per-visit preview feed are different
products. The preserved pending design is in [Project Backlog](PROJECT_BACKLOG.md#execution-branch-inspection-proposal).

## Frontend composition and file interactions

App owns the screen stack, subscriptions, display-run guards and coalesced
refresh scheduling. Screens render backend facts; shared command/list/form
helpers own navigation. Notifications use `frontend/notifications.py`.
Path pickers belong in `frontend/file_io.py`, with typed fallback; backend
services accept paths. Local path normalization is backend execution/validation
work, including WSL Windows-path interoperability.

File-view requests are queued FIFO for the displayed run. Input/recovery modals
take priority; reset discards retired-run requests. A display request does not
park execution until the viewer closes. OS window actions are backend local
execution effects today; a future remote deployment needs a local effector,
not windows opened on a server. See the retained file/window decisions in
[Node Standards](NODE_STANDARDS.md#file-and-window-design-decisions).

## Per-visit run facts (2026-10-25)

`NodeContext.run_snapshot` is an optional frozen `RunSnapshot`: actual run
start time, a tuple of at most five frozen `RunErrorSummary` records and the
older-error count. MasterState passes the run start into every Supervisor;
the supervisor captures the ErrorHandler's current-run cache immediately
before invoking a node. Snapshots exclude tracebacks, raw error context and
payloads, never lazy-load files, and do not update after the visit starts.
Branches share the handler, so the last five span this run's branches.
The existing finalization evicts the cache. Nodes have no engine/frontend
reach-in or subscription and decide how to redact/shorten displayed fields.

Supervisor input resolution omits unpublished transient values but preserves
explicit nulls, so a node can distinguish a missing item from JSON null.

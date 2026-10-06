# Execution Display Contract

Implemented 2026-10-06 on `codex/execution-symbol-investigation`.
See `EXECUTION_STATUS_BUILD_PLAN.md` for verification/handoff status and
`EXECUTION_STATUS_INVESTIGATION.md` for the original defects. This document
records current code; A/D branch navigation and output-summary UI are future work.

## Engine facts

`NODE_EXECUTION_UPDATE` is published by Supervisor with JSON-serializable fields:
`run_id`, `branch_id`, `node_id`, `visit_index`, `attempt_index`, `status`.
Statuses are `running`, `waiting`, `done`, `errored`, `skipped`, `stopped`.

- Visits are numbered from 1 per supervisor; attempts start at 1 per visit.
  RETRY increments the attempt, while executing the node again later increments
  the visit. Setup errors before execution can have attempt 0.
- Node entry emits running. Successful signaling after execute returns emits
  done; failures/missing signals emit errored. Timing in finally is independent
  and includes visit/attempt identity as well as the existing elapsed seconds.
- User input emits waiting, then running when answered. A stop that resolves
  the input future emits stopped rather than success. A safe-point stop after
  a node succeeds keeps that node's success and leaves the queued node unvisited.
- SKIP emits skipped for the failed attempt and advances to the next node.
  The next node is not marked completed until it actually executes. This also
  corrects the prior skip path's premature completion-registry update.
- Terminate branch/workflow and cancellation do not turn an error into success.
  Cancellation of an active/waiting attempt emits stopped; existing failed or
  completed outcomes survive cancellation. Unexpected setup failures use the
  supervisor error path so the workflow reports ERROR.
- Supervisor position/state and termination events now carry run_id. State
  events include `node_phase` queued/executing; branch termination reports
  stop_requested. WAITING_FOR_INPUT and AWAITING_RECOVERY retain their existing
  supervisor meanings. Node symbols are derived from lifecycle facts.
- Registration adds parent_branch_id and start_node_id. Its legacy `supervisor`
  object is still present because MasterState consumes it in-process. The new
  lifecycle feed contains no resource objects; converting registration into
  a transport-safe protocol is separate multi-frontend work.

Pause remains cooperative between nodes; breakpoint pause is before executing
its node. WaitUntil/merge barriers remain running, not user-input waiting.
No new pause/barrier glyphs or payload capture were introduced.

## Frontend cache

`frontend/execution_state.py`: `ExecutionDisplayState` owns the current run ID
and `branches` dictionary, preserving branch registration order and ended
branches. Each branch has provenance, supervisor state/position/phase,
ordered visits keyed by visit_index, attempts keyed by attempt_index, per-visit
and per-attempt elapsed seconds, and a latest status map per node.

`App.execution_state.node_statuses(branch_id)` returns a branch's derived node
statuses. With no branch ID it returns the compatibility global summary:
`running > waiting > errored > stopped > skipped > done` across latest visits
in each branch. The latest attempt supersedes earlier attempts in that branch;
records of earlier attempts/visits remain available. A successful retry can
become done, while another branch's unresolved error remains visible.

`App.node_statuses`, `node_timings`, and `supervisors` support the existing
screen. Supervisor termination and node movement no longer assign node success.
New lifecycle, supervisor, timing and modal events are checked against run_id.
Cleared runs are retired so late RUNNING events cannot resurrect display state.
New runs and workflow replacement clear it; finished branches remain inspectable
within the current run. This is ephemeral inspection state, not persisted run
history. Long-run history retention limits remain a future design concern.

## Rendering

ExecutionScreen refreshes on screen resume, so modal-covered updates appear
when the modal closes. NodeList updates existing cards when graph IDs/order
are unchanged, preserving highlight/scroll. NodeCard requires an explicit
refresh after updating its ordinary status/timing attributes.

Glyph meanings stay: circle not visited, play executing, check successful,
cross errored, pause waiting for input. Skipped/stopped use explicit text labels
`[skipped]` and `[stopped]` and receive no checkmark. Warning, breakpoint,
Merge Beacon and editor branch-health indicators are independent.

## Next UI work

Consume branch provenance and visit state for A/D cycling and scrollable branch
lists. Preserve selection/scroll per branch; do not rebuild execution state in
screen widgets. Define upcoming graph rows separately from actual visit history.
Output summaries require separate branch/visit attribution and bounded preview
storage: OutputManager records only output-node results, and transient memory
can be overwritten by subsequent visits. Keep those payload decisions outside
lifecycle events and the correctness fix.

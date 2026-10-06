# Execution Symbols: Investigation and Fix Plan

Investigated 2026-10-06 against fetched main `8ada5b2`, using the canonical
checkout `/home/makin/src/node_workflow`. Branch:
`codex/execution-symbol-investigation`. Investigation only; no application
behavior changed. Owner reports circles failing to become checkmarks for all
completed nodes during execution; this matches the linear-run reproduction.
The owner describes a circle as waiting; current code uses it for not visited
and reserves the pause glyph for waiting for input.

## Finding

The primary defect is missing per-node supervisor updates, rather than an
incorrect glyph mapping. Ordinary node transitions change
`Supervisor.current_node_id` without publishing `SUPERVISOR_STATE_UPDATE`.
The frontend relies on that event to identify running and completed nodes.
Timing and memory events refresh the screen but do not correct those statuses.

Three independent failures were reproduced:

| Probe | Actual result | Expected meaning |
|---|---|---|
| Start -> Sleep -> Sleep -> End | All four execute and report timing; only Start ends as `done`, other nodes default to `idle` | All successfully executed nodes complete |
| Start -> Error, choose TERMINATE_BRANCH | Error is `errored` during recovery, then `done`; workflow finishes | Ending a branch does not make a failed node successful |
| Update a node while a modal covers ExecutionScreen, then dismiss | App cache changes to `running`; underlying card remains `idle` after dismissal | Resumed screen displays latest cached state |

The first and third probes use real runtime/frontend components. The linear
and recovery probes suppress screen refresh or modal creation so status-cache
behavior is isolated. The modal probe uses the actual Textual app's
`run_test()` and a generic ModalScreen, exercising the same stack behavior as
Memory/Output/Error dialogs. These are automated probes, not owner live
verification of this particular bug.

## Current logic to retain as a reference

The path is:
`Supervisor / MasterState -> EventBus -> AttackOfTheNodesApp display caches
-> active screen refresh -> NodeList -> NodeCard`.

- `backend/supervisor.py`: publishes RUNNING at branch start, input wait/resume,
  recovery entry/exit, breakpoint encounter, and termination. There is no
  ordinary per-node RUNNING update inside the loop. Changing the next node
  in `_handle_payload()` does not publish a transition.
- `NODE_TIMING_UPDATE` fires in `_execute_node()` finally, including failed
  attempts. It has run, branch, node IDs and elapsed seconds. Timing is not a
  success signal. `MasterState.mark_node_completed()` maintains a backend set
  for WaitUntil/merge coordination, but this is not a frontend lifecycle feed.
- `frontend/app.py`: owns `node_statuses`, `node_timings`, `supervisors`, and
  `_branch_current_nodes`. Status is indexed only by node ID; concurrent visits
  by different branches overwrite each other. Timings accumulate per node.
- `_on_supervisor_state_update()`: a change of current node marks the prior
  node `done`; WAITING_FOR_INPUT maps to `waiting`, AWAITING_RECOVERY/ERROR to
  `errored`, TERMINATED to `done`, everything else to `running`.
- `_on_supervisor_terminating()`: unconditionally marks its last known node
  `done`, including error/stop cases. The run state and branch state do not
  distinguish all node outcomes.
- Run display caches reset at a new run and on workflow IDLE. FINISHED/ERROR
  normally retain display data; explicit stop/return paths can clear it.
- App subscribes once for its lifetime. EventBus invokes subscribers
  synchronously, in subscription order. MasterState subscribes before App;
  nested workflow events can therefore precede App's handling of an outer
  supervisor event. Preserve this ordering in regression probes.
- `App._on_backend_event()` refreshes only the active mounted screen. A
  covering modal receives refresh attempts, leaving ExecutionScreen stale.
  ExecutionScreen refreshes on mount but has no resume refresh handler.
- `ExecutionScreen.refresh_from_backend()` reads these caches and backend
  memory/output. It rebuilds the whole node list and output log each time.
  `NodeList.refresh_nodes()` clears/appends widgets without awaiting those
  operations. Rebuild churn and selection stability deserve redesign tests;
  this investigation did not establish them as the primary symbol defect.
- `NodeCard.status` is ordinary instance state, not reactive. It renders on
  mount/resize or explicit `refresh_card()`. Existing screen refresh works by
  constructing new cards. A future in-place update must explicitly refresh
  cards or make its rendering state reactive.

### Existing symbol vocabulary

| Display status | Symbol | Intended meaning |
|---|---|---|
| idle | ◌ | Not visited in this run |
| running | ▶ | Executing |
| done | ✓ | Successfully completed |
| errored | ✗ | Error / awaiting recovery |
| waiting | ⏸ | Waiting for user input |

Unknown statuses fall back to idle. Breakpoint `●`, warning `⚠`, editor branch
colors, and Merge Beacon connection indicators are separate from execution
status. Editor rows intentionally hide run-status symbols.

Global PAUSED is not a supervisor state and is not mapped to node waiting.
`MasterState.pause()` requests a pause at the next safe point, after the current
node; breakpoint pause occurs before execution. WaitUntil/merge barrier waits
currently retain RUNNING rather than emitting WAITING_FOR_INPUT. Do not
silently redefine these different waits in a visual redesign.

Other exposed gaps: `_fail()` publishes SUPERVISOR_ERROR without a normal state
update; App does not subscribe to SUPERVISOR_ERROR. Several supervisor events
omit run_id, and App does not filter display updates by run_id. Run-scoping is
needed before relying on the caches for asynchronous or remote frontends.

## Recommended game plan

Implementation stages now live in [EXECUTION_STATUS_BUILD_PLAN.md](EXECUTION_STATUS_BUILD_PLAN.md).
The owner subsequently specified A/D execution-branch cycling, scrollable
per-branch node lists, and output summaries. The fix must retain branch-specific
visit/outcome state; the visual redesign remains a follow-up.

1. **Establish behavioral tests before changing layout.** Check intermediate
   live states and rendered cards for linear and forked paths; untouched nodes
   remain idle. Cover error retry/skip/termination, user input, WaitUntil/merge,
   breakpoint/manual pause, stop, modal dismissal, repeat visits, and reruns.
   Existing backend tests pass while the symbols fail, so backend completion
   tests alone are insufficient.
2. **Repair the lifecycle feed in a focused bugfix.** Publish a supervisor
   update for each node entry and an explicit outcome for each attempt/visit.
   Carry run_id, branch_id, node_id and an outcome independent of branch
   termination. Keep timing separate. Prefer a small portable node lifecycle
   event contract over extending the inference that moving away means success.
   Do not put symbols, widgets, or Textual state in backend events.
3. **Centralize frontend derivation.** Consume lifecycle events in one display
   reducer/cache. Remove unconditional success on movement/termination; retain
   actual failed/skipped/stopped outcomes. Use run_id to reject stale events.
   Track active branch visits so one completing branch cannot mask another
   executing the same node. Rebuild/snapshot state on screen resume.
4. **Verify and merge correctness independently.** Run targeted event/render
   tests, full debug suite and relevant runtime tests; manually confirm the
   owner's workflow. Keep this bugfix separate from the execution layout PR.
5. **Build the upcoming execution UI on the verified state contract.** Preserve
   the existing glyph meanings and keyboard access unless a specific design
   changes them. Update cards in place or coalesce refreshes rather than
   rebuilding the list for every backend event. Preserve selection/scroll and
   output ordering; fast nodes may finish between frames, but final outcomes
   must remain correct. Document any revised aggregation and wait semantics.

Decisions for the execution UI design: how to display skipped/stopped nodes;
whether to distinguish input waits, barrier waits, and pause requested versus
pause reached; and how to summarize overlapping/repeated visits. Suggested
starting rule: live visits stay visible, with terminal outcome retained after
all active visits finish. Define precedence explicitly before implementation;
last event wins is not adequate for shared nodes on parallel branches.

A minimal compatibility patch could publish missing node-entry events and
refresh on resume immediately, but that alone leaves false success on errors
and cancellation. The recommended sequence addresses those correctness gaps
before new visuals depend on them. Node execution, branch/merge coordination,
Vault/dead-drop routing, recovery actions, and safe-point pause behavior remain
backend responsibilities throughout.

## Verification performed

- Linear real-run trace: only RUNNING(Start) and TERMINATED(None) supervisor
  updates; NODE_TIMING_UPDATE for all four nodes; final cache done/idle/idle/idle.
- Real recovery run: errored during recovery -> done after TERMINATE_BRANCH.
- Direct handler probe: ERROR followed by supervisor termination -> done.
- Mounted Textual modal probe: cache running, resumed card idle.
- Existing focused debug suite: 5 passed, 149 deselected (linear traversal,
  breakpoint pause/resume, timing, WaitUntil and merge behavior).
- Documentation check: `git diff --check`.

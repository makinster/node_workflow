# Execution Status Fix Build Plan

Created 2026-10-06. Status: **ES0–ES3 implemented and automatically verified; ES4 automated verification and owner symbol confirmation complete; merge authorized**.
Base: fetched main `8ada5b2`; investigation commit `20d58c7` on
`codex/execution-symbol-investigation`. See
[the investigation](EXECUTION_STATUS_INVESTIGATION.md) for reproduced failures
and the current event/cache/render logic. This plan governs the correctness
fix; the branch-view layout follows in a separate task/PR.

## Objective and scope

Make completed nodes reliably change from circles to checkmarks, preserve
errors through branch termination, and refresh the run screen after modal
closure. Prepare branch-specific display state for the owner's future design:
A/D cycles execution branches, each with a scrollable node list and output
summary UI. These future controls are planned, not currently implemented.

Keep node execution, routing, Vault/dead-drop handling, merge/WaitUntil
coordination, recovery actions, and safe-point pause behavior unchanged.
Timing is not proof of success. Branch termination is not node completion.
Backend events carry portable facts; the frontend owns glyphs and navigation.

## Proposed state contract

Implemented field names and derivation are recorded in
[EXECUTION_STATUS_CONTRACT.md](EXECUTION_STATUS_CONTRACT.md). The bullets below
retain the agreed requirements; use the contract for current implementation.

- Scope every execution display event by `run_id` and `branch_id`; node events
  also identify `node_id`. Reject events from older runs in the display cache.
- Use an explicit node lifecycle event (proposed `NODE_EXECUTION_UPDATE`) for
  entry, success, failure, retry, skip and cancellation. Include a visit index
  and attempt index: repeated visits and retry attempts are different things.
  IDs/counters must be stable within a supervisor and JSON serializable.
- Keep supervisor events for branch registration, state, position, and ending;
  add missing run IDs and current-node context where needed. Node outcome must
  not be inferred from these events. Keep NODE_TIMING_UPDATE as measurement;
  correlate its attempts where needed without changing existing timing totals.
- Record frontend display state by run -> branch -> node visits/attempts.
  Retain branch registration order, parent branch ID, depth, start node ID,
  latest position/state, visit order, timings and terminal outcomes. Keep ended
  branches for inspection through run completion; reset at the next run or
  workflow replacement. Audit stop/IDLE reset paths so late events cannot
  resurrect cleared state. Persistence across app restarts is out of scope.
- Preserve a derived node-ID summary only where the existing global screen
  needs it. Branch-local state is the source for future branch views. Active
  visits take precedence over terminal summaries; terminal errors remain
  visible unless that attempt is superseded by a successful retry. Cover
  overlapping branches explicitly rather than using last-event-wins.
- Existing glyph meanings stay: `◌` not visited, `▶` executing, `✓` successful,
  `✗` errored, `⏸` waiting for input. Skipped/stopped outcomes must not receive
  success checks; use an explicit text outcome until new glyphs are designed.
  Keep breakpoint/warning/branch-health indicators separate.
- Do not call a barrier wait user-input waiting, or claim a pause request has
  already stopped an executing node. New paused/barrier glyphs are deferred.

## ES0 — Regression cases

Status: implemented; covered by `tests/test_execution_status.py`. Likely files: focused execution-status tests plus existing
`tests/test_debug_nodes.py`. Use real EventBus/Supervisor/App wiring and mounted
Textual tests; do not rely solely on simulated handler events.

- Linear Start -> Sleep -> Sleep -> End: observe each slow node running, then
  done; all executed nodes are done at finish, disconnected nodes stay idle.
- Parallel branches and a node visited by two branches: independent statuses
  and timings; finishing one visit cannot hide another active visit.
- Failure with retry, skip, terminate branch/workflow, and unhandled error:
  actual outcomes remain visible; no unconditional checkmark on termination.
- User input and modal closure: cache and rendered symbols agree after resume.
- Breakpoint/manual pause, WaitUntil/merge barriers, stop, repeated visits,
  retry attempts, and a second run: preserve backend semantics, reject stale
  events, and reset display state at the intended boundary.

Exit: failing regression assertions establish the reproduced symbol bugs,
with the existing runtime tests still passing.

## ES1 — Explicit lifecycle reporting

Status: implemented; covered by `tests/test_execution_status.py`. Likely files: `backend/events.py`, `backend/supervisor.py`,
`backend/master_state.py`, runtime/event tests.

- Publish node entry at every execution step and retry; publish explicit
  success/failure/skip/cancellation facts at their actual boundaries.
- Publish branch position updates for each node transition. Distinguish the
  next queued node from an executing node at breakpoint/safe-point pauses.
- Include run/branch/node identity and visit/attempt counters. Handle `_fail()`,
  unexpected exceptions and termination paths without implying node success.
- Audit completion/output routing order; preserve WaitUntil/merge behavior
  and existing timing accumulation. Events must add observability without
  changing which nodes execute or when supervisors advance.

Exit: event traces identify every visit/outcome, including fast nodes, terminal
nodes, failures and repeat visits. Existing runtime checks pass.

## ES2 — Branch-specific frontend status derivation

Status: implemented; covered by `tests/test_execution_status.py`. Likely files: `frontend/app.py`, a small shared frontend
execution-state helper, focused reducer/cache tests.

- Consume lifecycle facts in one reducer; remove success-on-node-movement and
  success-on-supervisor-termination shortcuts.
- Store branch visits/outcomes and preserve ended branches. Derive the current
  screen's global node summary deterministically without conflating branches.
- Filter by active run; validate reset and nested synchronous-event ordering.
  App subscriptions remain session-scoped, not recreated for each screen.
- Retain retry history while showing the current attempt; a recovered success
  can become a checkmark without losing the earlier error detail.

Exit: cache assertions pass for all ES0 cases and provide a stable per-branch
read interface for the future execution view.

## ES3 — Reliable rendering and resume

Status: implemented; covered by `tests/test_execution_status.py`. Likely files: `frontend/screens/execution.py`,
`frontend/widgets/node_list.py`, `frontend/widgets/node_card.py`, mounted tests.

- Refresh from current state on screen resume after any covering modal.
- Render the reducer's actual outcomes, not timing/completion guesses.
- Update stable cards in place, or serialize/coalesce list rebuilds as needed;
  changing plain NodeCard attributes requires explicit rendering refresh.
- Preserve highlighted node and scroll position during status/timing updates.
  Do not add A/D branch switching or redesign the layout in this fix.

Exit: visible symbols match the cache during execution and after modals,
completion/error/stop. Rapid event bursts do not leave stale cards.

## ES4 — Verification and handoff

Status: automated verification complete; owner confirmed live symbols on
2026-10-06. PR #28 reviewed; owner authorized merge. Verify its GitHub status
before the next UI task.
21 focused execution regressions passed, including mounted screens at 60/100/140
columns. Compileall and diff checks passed; full-suite result in SESSION_LOG.md.
Owner confirmation covers the reported symbols; recovery/modal edge cases
remain backed by automated tests, not separate manual reports.

- Compile: `../.venv/bin/python -m compileall -q .` from AttackOfTheNodes.
- Run new focused execution lifecycle/cache/render tests, full debug suite,
  and relevant supervisor/recovery/branch/merge tests identified during ES0.
- Run `git diff --check`. Confirm the owner's failing workflow live, plus a
  slow linear workflow and parallel branches at several terminal widths.
- Update the session log and this plan with actual results, commit hashes,
  and remaining gaps. Publish the focused fix PR when authorized; merge after
  review, then start the visual redesign from updated main.

Exit: symbols and failure outcomes verified; branch state contract documented
for the redesign. No output-summary UI or persistent run browser delivered.

## Future execution screen — agreed direction and design work

Owner direction: per-branch execution view; A/D cycles branches; each branch
has a scrollable node list and output-summary UI. Keep root and completed
branches inspectable. Registration order is a reasonable initial cycling order;
visible names, ordering/wrap behavior and exact layout remain to be designed.
Execution branch IDs identify supervisors, not editor graph branch selectors;
retain parent/depth/start-node provenance so UI labels can be derived safely.

Preserve selected branch, selected visit/node, and scroll independently for
navigation. Backend updates should not jump the user to a different branch.
Use visit history to describe actual execution; showing upcoming graph nodes
requires separate graph-derived rows. Define that distinction in the design,
especially at conditional paths, forks, merges and repeated visits.

Output summaries need a deliberate data-source design. Existing OutputManager
records are output-node results, not every node's produced ports; transient
MemoryBank data is shared and can be overwritten by later visits. Do not
promise per-visit summaries from that data alone. Decide branch/visit
attribution and whether a summary describes the branch, selected node, or both.
Use bounded, safe previews and metadata; do not copy arbitrary payloads or
live resources into lifecycle events. Do not expand runtime retention/storage
in the correctness fix just to support a future visual feature.

Additional design decisions: how to present skip/stop outcomes, shared-node
aggregation, pause-requested versus pause-reached, barrier waits, repeat visits,
output retention/limits, and follow-current-node behavior. These are future UI
choices; the fixed lifecycle facts must support them without rewriting execution.

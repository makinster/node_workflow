# Execution Branch UI Design

Proposed 2026-10-06 from merged PR #28, main `7161ef2`.
Design only; runtime and screen implementation remain unchanged. Defaults below
are concrete recommendations for review, not previously approved owner choices.
Current facts: [EXECUTION_STATUS_CONTRACT.md](EXECUTION_STATUS_CONTRACT.md).

## Branch navigation

Use `app.execution_state.branches` and its stable insertion order. Select the
first registered root initially. Labels are `Root`, `Root 2` for additional
roots, and `Branch N` for child supervisors, with child numbers assigned once
in registration order. Show parent label, depth, start-node alias and a shortened
branch ID in details. Do not infer graph port names from supervisor IDs.

A/left selects the previous runtime branch; D/right selects the next; wrap at
both ends. Include ended branches. With zero branches show “Waiting for branch
registration”; with one branch cycling is a no-op. New registrations append
without changing the selection. A branch completing never selects its parent
or sibling automatically. A header shows `Branch 2 of 5`, state, parent and
visited-node count; it does not need a horizontally scrolling tab strip.

Navigation is owned by ExecutionScreen: `selected_branch_id` and, per branch,
`selected_row_key`, list scroll offset, detail scroll offset, and `follow_live`.
Reset navigation on a new run or workflow replacement, preserve it through
modal resume and resizing. Restore selection before scroll after layout, clamp
scroll after resize, and ignore superseded asynchronous list rebuilds.

## Rows describe actual execution

Use one row per visit in ascending visit_index. Identity is
`(branch_id, visit_index)`, not node_id. Repeated execution of the same node
produces separate rows. Use the visit's latest attempt status and total visit
seconds; details list every attempt and its own status/timing. Attempt 0 is
shown as setup failure where present. A successful retry reads `done · attempt
2`, while the failed first attempt remains in details.

`node_statuses(branch_id)` remains useful for branch-local aggregate badges,
but must not supply every visit row: it describes the latest visit of a node.
Never use global `app.node_statuses` or global timing totals for these rows.

At most one additional `Next: alias [not started]` row appears when branch
position has node_phase queued and no corresponding active visit. Its key is
`(branch_id, "queued", node_id)`; replace it with the actual visit on entry.
Follow mode transfers selection to that visit. Inspect mode keeps its prior
visit selected, or transfers a selected queued row to its replacement.
No speculative walk through conditional/fork/merge paths. Parent visits are
not copied into children; provenance points back to the parent. Disconnected
and never-selected graph nodes do not appear in a branch's visit list.
Missing graph metadata falls back to node ID without dropping history.

W/S and up/down move rows; PageUp/PageDown scroll pages, Home selects the first
row, End selects the newest row and resumes follow mode. Initial selection
follows the current visit. Manual movement or mouse selection disables follow;
F toggles it. Each branch remembers its own follow setting. Inspect mode never
jumps when visits append or timings/status change. Only the selected branch
updates visible cards; keyed reconciliation preserves mounted rows.

**Keyboard conflict:** current execution S stops the workflow. Proposed design
moves stop to X, makes W/S navigation consistent with the editor, and updates
bindings, on_key, help and footer together. P remains pause/resume, M opens
Vault, O opens existing run output, E opens errors, Esc/Ctrl+Q preserve their
existing stop-and-editor behavior. The stop key change must be visibly called
out in the delivered UI. Do not bind S to both actions.

## Outcomes and branch state

Keep the established node glyphs: executing, success, error and waiting for
input. Keep explicit [skipped]/[stopped] labels. A branch's ended state must
not recolor all its visit rows as successful. Branch header and node outcomes
are separate; use state and stop_requested without inventing a success count
from supervisor termination.

Paused branch headers use the supervisor's confirmed state. While global pause
is requested and branches still run, show “Pause requested” in the run header.
Queued breakpoint nodes stay not started. Running merge/WaitUntil visits stay
running; details may say “Coordination node executing”, but must not claim a
confirmed barrier wait because the existing feed has no barrier-enter/exit
facts. New pause/barrier glyphs are unnecessary for this version.

## Layout and output scope

At 100+ columns show a visit list on the left and selected-visit details on the
right. At narrower widths stack the list above a bounded details panel. Keep
run header, branch header and footer outside scrolling regions. The visit list
gets remaining height; details scroll independently with Tab to focus and
standard arrow/page controls. Branch A/D remain screen commands. Keep at least
five visible visit rows at a 60x24 terminal; short terminals prioritize the list
and compact details. Escape from detail focus retains existing screen behavior.

Example wide layout (illustrative text, not a rendered implementation):

```text
Workflow: Example [RUNNING]
< Branch 2 of 3 > Branch 1 | parent Root | depth 1
Visits                          Selected visit #3: Text Output
  1 Start        done  0.01s     Attempt 1: done 0.02s
  2 Transform    done  0.04s     Dead-drop payloads
> 3 Text Output  done  0.02s       default: text (120 chars) “Result...”
  4 Next: Sleep  not started    Branch summary: 3 visits; 1 preview
A/D branch | W/S visit | F follow | P pause | X stop | O run output
```

Details describe the selected visit and attempt, including produced dead-drop
ports. A compact branch summary shows visit/outcome counts and preview counts
for that branch; it does not concatenate every value. Vault remains shared
run state accessible through M and is never labeled branch-owned. O continues
to open run-wide durable output records, explicitly titled “Run output”.

## Preview attribution and bounded retention

Existing OutputManager stores run/node/value records; MasterState finalization
rebuilds them from shared output_log. These are not an attribution source.
Do not guess a branch from node ID, timestamps or the last active supervisor,
and do not inspect shared transient memory to reconstruct older visit values.

Introduce a separate opt-in observational preview feed, independent of
NODE_EXECUTION_UPDATE and durable output persistence. Every preview identifies
run_id, branch_id, node_id, visit_index, attempt_index, port_name and kind
(`dead_drop` initially). Capture from the successful attempt's result.payload
`data` immediately after execute returns, before any awaited handoff or reuse;
do not use _handle_payload alone, because terminate_branch returns before its
data-storage loop. Observe without modifying the result, routing or Vault.
Exclude routing control entries such as _route_via_port. Failed/cancelled
attempts have no success preview. Retry previews are scoped to their attempt.

This feed describes successful reported port data, not every side effect or
output_log write. Durable output-node records remain run-wide. A later explicit
output-record attribution hook may add an `output_record` kind; it needs real
execution identity at write time and must preserve legacy finalization behavior.
Do not put an unattributed durable record into a branch summary.

The backend emits only bounded JSON-safe descriptors: type, known safe size,
short preview text, truncation/omission reason and identity. Never emit payload
objects, resource handles, secret configuration or inputs. No arbitrary repr,
str, iteration, serializer or resource dereference. Restrict formatting to
built-in primitive values and shallow built-in containers. Binary data shows
byte count; resources/custom objects show an opaque type descriptor, no open,
read, network fetch, thumbnail creation or copying. Escape terminal controls
and render as plain text. Text outputs may themselves contain sensitive user
data, so previews are off by default; enabling affects future attempts only.
Disabling clears retained previews immediately and suppresses later capture.

Proposed configurable ceilings: 512 characters of preview text per port,
8 ports per attempt, 4 KiB serialized descriptor budget per attempt, 256 KiB
per run and 200 retained attempt-preview groups, whichever is reached first.
Bound inspection work too: depth 2 and 16 inspected items total per attempt;
do not serialize a whole value before truncation. If a group exceeds budget,
retain omission metadata within the same budget. Evict oldest groups; no duplicate
branch payload cache. Missing summary states distinguish disabled, not captured,
no reported ports, truncated and evicted. Counts are capped/aggregate metadata,
not an unbounded index of omitted records. Reset at the next run/replacement;
retain through natural FINISHED/ERROR while the display run remains available.

Scope limitation: current App clears execution state on backend IDLE, including
explicit workflow stop. This version preserves that reset and stale-run guard;
branch-local stopped attempts remain inspectable while their run is retained.
Post-workflow-stop inspection requires a separate snapshot/retirement decision.
Do not accidentally resurrect the stopped run to satisfy the new layout.

## Delivery stages and acceptance

1. Implement branch/visit list and navigation using existing facts. Use an
   execution-specific list with visit-keyed rows; NodeList.refresh_nodes is
   node-ID keyed and cannot represent repeats. Reuse NodeCard appearance and
   shared navigation helpers without changing editor row behavior. Add details
   for attempts/timing and honest unavailable-preview messages.
2. Add opt-in bounded preview descriptors and an App-owned reducer/cache.
   Keep subscriptions session-scoped and apply current run/retired-run guards.
   Formatter failures are contained and cannot alter node execution/recovery.
3. Wire selected-visit previews and branch counts, then verify live at multiple
   terminal widths. Keep this work in a separate feature PR from PR #28.

Tests should cover wrap/zero/one/many branches, nested provenance, retained ended
branches, independent shared-node visits, repeated visits and retries, queued
row replacement, per-branch scroll/selection/follow, modal resume and resize.
Verify S navigates without stopping and X stops, plus existing recovery keys.
Mounted checks at 60/100/140 columns must assert selection and scroll stability
while events arrive, narrow details access and terminal-control escaping.

Preview tests must cover overwritten shared ports, successful terminate-branch
payloads, stale runs, disabled/enable/disable transitions, resource/custom-object
formatting without invoking methods, oversized/deep values, all retention limits
and explicit evicted/unavailable states. Existing run-output persistence and
414-test baseline must remain intact. Before runtime delivery run focused
execution tests, full tests/, compileall and git diff --check. Design-only
verification is diff and local documentation-link checks; no tests rerun here.

# Delivery tests

Planning and regression fixtures for the [delivery loop](../DELIVERY_LOOP.md).
No fixture is permission to run a live workflow, spend money or send a message.

- [Heartbeat](h1-heartbeat.json): composition-only; final checked spec retained.
- [Notify me](c1-notify-test.json): new-integration at delivery; reconstructed node plan.
- [Investigation test](c3c-investigate-test.json): new-integration at delivery; reconstructed node plan.

In progress: [Ask local model](ask-local-model.json), owner-approved build
through step 5, with original 3/4 coverage, approval timing and two-request
cold/warm smoke. Review/merge/go-live remain pending.

These three requests finished with owner-confirmed Telegram results. The
heartbeat/C1 evidence is in [Current State](../CURRENT_STATE.md); investigation
live proof is from the coordinator's 2026-10-23 shared notes. Repository contracts
explain behaviour; a contract alone is not evidence of live delivery. References
inside JSON resolve relative to this directory (template example references
resolve relative to `templates/`). No live data was read to create these cases.

Coverage is a historical reconstruction of useful workflow operations, not
an exact transcription of private live graphs. Heartbeat: 1/1 existing;
Notify me: 0/1; investigation: 1/2. Against the current catalogue these gaps
are filled; retain the original mapping for comparison and record replay
coverage separately. Unknown historical rounds/timings stay null or absent.

## Record the next case

Use the same top-level fields: integer `schema_version`, stable `case_id`,
`baseline` commit, `record_status`, `request_kind`, `request`, `feasibility`,
`final_artifact`, `coverage`, `measurements`, `evidence`, `acceptance_checks`,
and `notes`. Request and feasibility use the [versioned templates](../DELIVERY_LOOP.md#copyable-templates).
A final artifact is either a relative workflow-spec path or an explicit node
plan. Coverage maps operations to nodes and measurement labels; counts must
sum to the denominator and ratio must equal existing / total.

For each step visit save `step` (0–11), `started_at`/`ended_at` (UTC or null),
`elapsed_days` (number or null), `wait_reason` and any `skipped_reason`.
For reviews retain head, findings and outcome per round. Link approved samples,
setup/rollback, run/device proof and observations; scrub secrets/private facts.
At retro freeze the expected outcome and acceptance checks with a case version.

## Score a future change

Follow [the scoring method](../DELIVERY_LOOP.md#finished-requests-become-tests).
Save a dated `<case-id>.results.<date>.json` with candidate head, catalogue base,
prompt/context versions, each applicable check and pass/fail evidence, coverage,
rounds and time. Mark unexecuted device/paid checks `not_run`; exclude them
from the scored denominator and report them visibly, never count them as passes.
A stub transport proves logic only. Node plans cannot claim a build-check pass
until converted to actual specs. Compare candidates on the same checks/base;
keep approval/permission/redaction failures blocking. Do not overwrite the
frozen case just to improve a score.

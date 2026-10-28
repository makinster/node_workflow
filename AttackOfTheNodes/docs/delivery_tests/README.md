# Delivery tests

Planning and regression fixtures for the [delivery loop](../DELIVERY_LOOP.md).
No fixture is permission to run a live workflow, spend money or send a message.

- [Heartbeat](h1-heartbeat.json): composition-only; final checked spec retained.
- [Notify me](c1-notify-test.json): new-integration at delivery; reconstructed node plan.
- [Investigation test](c3c-investigate-test.json): new-integration at delivery; reconstructed node plan.

[Ask local model](ask-local-model.json): PR #123 reviewed/merged; original 3/4
coverage, approval timing and two-request cold/warm smoke retained. Owner setup
and ordinary use remain pending.

[Source-menu audit and model pickers](source-menu-audit.json): `swiss-army fix`,
five shared mismatches, registry-wide consistency/mutation checks and read-only
picker tests. No new workflow operations, so node coverage is not applicable;
the related local-model workflow now has 4/4 available nodes. Review/merge pending.

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

[Meta nodes](meta-nodes.json): owner-approved build through step 5; two new
meta capabilities, related composition-designer coverage 6/8 on the candidate.
Review, merge and owner use remain pending.

## Record the next case

Use the same top-level fields: integer `schema_version`, stable `case_id`,
`baseline` commit, `record_status`, `request_kind`, `request`, `feasibility`,
`final_artifact`, `coverage`, `measurements`, `evidence`, `acceptance_checks`,
and `notes`. Request and feasibility use the [versioned templates](../DELIVERY_LOOP.md#copyable-templates).
A final artifact is either a relative workflow-spec path or an explicit node
plan. Coverage maps operations to nodes and measurement labels; counts must
sum to the denominator and ratio must equal existing / total.

The [schema](../templates/delivery_test.schema.json) and
[example](../templates/delivery_test.example.json) include optional
`repeated_shapes`: ordered node types, fixed/varied settings, boundary Vault
reads/writes, evidence links and evidence basis. Use design-only evidence
honestly; omit the field where no repeated sub-chain is known.

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

[Draft a workflow](draft-a-workflow.json): owner-approved fixed-palette variant,
step 5 authored and checked. [Spec and usage](specs/README.md),
[approved reply fixtures](fixtures/draft-a-workflow.json). Strict runtime lookup
mapping stays 7/8; the approved narrower scope is 8/8. Decision 11 trial:
one designer run, two calls, 70.64 s CPU, Check failed on annotated port ids.
Failure displayed and stopped; no saved spec or target build/run. Local packet:
`/home/makin/src/agent_channel/draft-workflow-samples/`.

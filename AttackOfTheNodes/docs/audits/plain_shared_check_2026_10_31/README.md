# Plain shared-check refusals — 2026-10-31

Base: main `e7efdae`; branch `codex/plain-shared-check`. No API or model calls.

`meta_workflow.problem_report` matches diagnostics to shared flow findings by code,
node and original message, then uses each finding's message plus repair. Other
validators keep the safe-message whitelist. Existing redaction and output caps apply.
The refusal verdict, flow analysis, palette and draft admission checks are unchanged.

The actual retry path in `docs/delivery_tests/specs/draft-a-workflow-v2.json` is
`check.error → remember_check_error → rejected_draft → remember_first_draft →
retry_question → draft_retry`. The first node stores the entire error payload in
`first_check_error`; Concat formats its Python string representation into
`EXACT CHECK ERROR`. `tools/draft_trials/runner.py:run_case` configures and runs that
same designer graph; it does not independently construct the redraft prompt.

The check node now applies the existing `review_report` projection to error details
before routing, as it already does for successful reports. Merge summaries and
findings remain; raw profiles, arrivals, dependencies and provenance do not reach
the redraft. `meta_workflow.check()` still returns/raises the full analysis, and
`check_draft(..., flow=report['flow_analysis'])` still runs before projection.

## Mock repair evidence

`tests/test_shared_check_redraft.py` uses the real designer graph, shared checker,
draft-stage gate and trial engine with mocked provider replies. A second Merge
for an inner split (F2-03) and a route leaving the required Merge (F2-05) both
produce plain top errors, retry once without raw analysis, then pass with the
corrected draft. These cover `flow_needs_review`, `repeated_join_unsupported` and
`merge_required_path_escape`; a separate impossible-wait case checks its message
and repair. A sanitization test checks credential redaction and the fallback for
non-flow diagnostics. The three regression cases failed before the fix.

Character counts use `len(str(first_check_error))` and the actual third call's
question from `calls.json`, with the same fixed pytest root before and after:

| Mock refusal | Error before | Error after | Retry question before | Retry question after | Reduction |
|---|---:|---:|---:|---:|---:|
| Second inner Merge | 14,423 | 3,336 | 36,989 | 25,902 | 11,087 |
| Escaping route | 9,261 | 1,363 | 33,665 | 25,767 | 7,898 |

The question includes the original brief and rejected draft. Contract context is
unchanged and excluded from these question counts. Paths affect absolute sizes;
the measurements used `--basetemp=/tmp/plain-check-measure` with the new test alone.

## Frozen text and fingerprints

The designer JSON, `admission.configure`, schemas, guidance and trial scoring are
byte-for-byte unchanged. Existing `test_frozen_sets_keep_their_designer_and_see_nothing_new`
checks sets 1, 2 and 3 against their pinned complete configured-designer hashes.
No pin changed. Shared error wording can change their runtime error evidence;
their pinned designer text does not change. Merge and Wait Until review source
fingerprints were refreshed after reviewing their existing records against the
changed shared reporting code; record text and content hashes are unchanged.
The check node's source-menu runtime fingerprint and generic source baseline were
also refreshed. Re-exporting `test_claims_receipt` changed only its two source
hashes; every observation and claim outcome is identical.

## Verification

From `AttackOfTheNodes/`, using the shared interpreter:

- Full `python -m pytest -n auto`: **5,239 passed, 187 skipped**, 62.58 seconds.
- New regression module: **5 passed**; all provider replies mocked.
- Re-exported generic claims receipt: **1 passed**, observations unchanged.
- Existing full configured-designer pins for sets 1, 2 and 3 pass without changes.
- `git diff --check` and local links in changed Markdown pass.

The first full run found three stale fingerprint assertions (5,235 passed,
187 skipped); their evidence was rechecked and refreshed before the final full
run. No validation assertions, scoring rules or refusal criteria were relaxed.

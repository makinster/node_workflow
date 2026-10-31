# Family 2 block 3 — final records and real-engine evidence

Base: merged main `58a22999f38ba03cca443fd4aff980d749ce838d` (#162–#164).
Depth repair is a separate commit, `943c83f`. No palette, trial harness, loop
implementation, Set/Get execution or API calls changed.

## Depth decision

Elect the shallowest entering supervisor, earliest on a tie, as before. Only
after election restore its depth to the Branch opening that group. Updating the
execution view preserves visible supervisor bookkeeping. Six/eight sequential
splits pass at default depth 5; eight also pass at limit 1. A sixth truly nested
split at limit 5 returns `branch_depth_exceeded` and launches none of its batch.
There is no conflict between winner identity and the restored continuation depth.

## Records, evidence and exports

Merge and Wait Until gain final records; Beacon remains a reviewed, visible editor
joining tool, outside the drafter. Set/Get remain pending and not dev-only.
Inventory: 18 reviewed / 25 pending / 16 dev-only, total 59.

[claims.json](claims.json) binds 95 real-engine scenarios to source hashes,
record digests, policy provenance and observed run results. The shared runner
calls the actual source test, observes actual starts/finalization and retains
Merge/Wait/Beacon outputs, completion counts, errors and cleanup. It does not
substitute coordinator callbacks. Scenario definitions live in
`tests/flow_claim_scenarios.py`; local fixed-run scenarios in
`tests/flow_engine_scenarios.py`.

| Claim | Evidence |
|---|---|
| M1–M3 actual values, absence, scalar/list, ordering | reversed file completion, FileView resource integration, falsy/missing values, numeric slots, concurrent/exclusive producers |
| M4–M6 inherited handoff, election, once-only publication | A / B→C,D with Merge on A/C/D, direct/Beacon, both arrival orders, simultaneous arrivals, Wait on Merge |
| M7–M9 failure, cancellation, isolation, standalone | joined failure, independent End/failure, abort/recovery, Stop during wait, stale callbacks, two real RunServices, standalone payload presence |
| B1 real nesting vs sequential groups | six/eight normal automatic-plan stages, nested depth refusal |
| W1–W2 own value and sticky completion | six payloads × four target formats, absent payload, empty targets, shared/repeated Wait, fresh runs, timeout, Stop and failed targets |
| G1/G2 refused graph forms | seven new actual direct-start/child refusal scenarios plus existing shared-analyser tests in `test_flow_behaviors.py` and normal-start integration tests: escaping routes, repeated joins, inner/outer, Merge/control-loop restrictions |
| C1 standard flags | refreshed generic [claims receipt](../claims_baseline_2026_10_29/claims.json); explicitly protocol-level, not coordinator proof |
| E1 editor compatibility | existing real Textual Merge config/Beacon selector tests bound in Beacon's manifest; saving preserves slots, selection and unmatched warnings |

The receipt exporter re-executes all 95 scenarios. It records local source and
runtime rechecks, **not an independent human review or family admission**. The PR
still requires independent review. Reviewed claims were not weakened to obtain
a passing result.

From `AttackOfTheNodes/`, using the project virtualenv:

```bash
AOTN_FLOW_CLAIMS_REPORT="$PWD/docs/audits/family_two_records_2026_10_31/claims.json" python -m pytest tests/test_flow_claims.py -k flow_claims_receipt -q
AOTN_CLAIMS_REPORT="$PWD/docs/audits/claims_baseline_2026_10_29/claims.json" python -m pytest tests/test_node_claims.py -k claims_receipt -q
python -m pytest -n auto -q
```

Flow templates are additive record-v1 fields for seven flow types. The shared
flow owner generates and validates them. Brief carries a short summary;
Compact/Detailed carry the complete declaration. Graph exports reuse existing
analysis with stable spec handles. Schema version 1, policy digest and
LF-normalized analyser/runtime source hashes accompany exports. Invalid policy
values (including boolean pass numbers) fail validation. No second traversal or
global execution cache is introduced.

## Sizes and caps

Exact character/UTF-8 counts and provenance: [sizes.json](sizes.json).

| Text catalogue | Before chars | After chars |
|---|---:|---:|
| All Brief | 13,698 | 15,751 |
| All Compact | 50,385 | 56,693 |
| All Detailed | 118,717 | 125,025 |
| Existing admitted Brief | 7,997 | 8,855 |
| Existing admitted Compact | 25,897 | 27,536 |
| Existing admitted Detailed | 47,419 | 49,058 |

Records: Merge 2,520 bytes, Wait Until 1,983, Beacon 1,308; cap 4,096.
Admitted Compact JSON is 37,601 characters, within the unchanged 50,000-contract
budget; existing v2 context cap is 100,000. Whole-registry Compact text fits the
default 64,000 catalogue cap. Whole-registry Compact JSON (78,501) and Detailed
text/JSON require an explicit larger catalogue cap or narrower selection, as
whole-registry Detailed already did. The configurable ceiling stays 200,000
characters / 256 KiB. Check reports are complete or error at 64,000 characters /
256 KiB; nothing is truncated to fit. No cap was increased.

## Plan/code disagreements and limits

1. **Flow startup gap fixed in the follow-up.** Normal startup now rejects every
   error-level finding from the one shared analysis before creating a run,
   including escaping required routes, omitted children and impossible/missing
   Wait targets. Both conditional inputs refuse with a plain repair message;
   App Run displays `Can't start`, and a child call produces `child_flow_invalid`.
   Seven new real-engine receipt scenarios cover these refusals. General
   `action_run_workflow` validation remains out of scope: the [validator audit](VALIDATOR_STARTUP_AUDIT.md)
   lists the other validator errors that still enter a run, plus compatibility
   results. No second analysis or new general validator call was added.
2. The plan's original retained-winner-depth wording is superseded by the owner's
   requested repair: retain election identity, then restore opening Branch depth.
3. R1 is approved, despite older provisional language. Current graph proofs
   declare scalar for single/exclusive producers and list for concurrent ones.
   Missing is omitted; null/false/zero/empty values remain present.
4. Set/Get sample records and S1/S2 are dropped by the owner's final scope.
   Draft inventory counts assuming four new records are stale: two new records
   yield 18/25/16. Beacon is not a debug node or an execution join by itself.
5. Old hand-built repeated-join allowances disagree with merged preflight:
   two Merges in one group, inner-then-outer joins and any control loop with
   Merge are refused. Fresh sequential groups work. No-split Merge is runtime
   passthrough with an editor warning; draft checks reject it.
6. Only joined producer failures fail that Merge. Independent side-path errors
   do not, though whole-workflow abort policy may cancel all work. A side End
   freely releases its path. The record makes no unconditional completion promise.
7. Atomic coordinator mutation uses non-awaiting event-loop operations, not a
   literal lock. The coordinator seals/elects; only the elected supervisor
   publishes, marks the saved Merge complete and continues.
8. WaitRegistry retains its two-part sticky key; RunContext records pass-1
   completion. Exporting the fixed pass policy does not implement a key migration
   or loops. Wait passes its own input, absent→empty text; it does not fetch targets.
9. Export sketches/old line numbers in the plan are not the merged implementation.
   Bounded generated templates reference port cardinality rather than repeating
   64 slot declarations. Existing flow analysis remains the sole graph owner.

## Changed tests and reasons

- `test_merge_arrival_runtime.py`: inherited-group and later-fork assertions now
  expect restored depth 0; shallow winner lineage assertions remain.
- `test_merge_plan_integration.py`: reference topology expects restored depth;
  sequential test now includes six/eight stages and limit-1 execution; new true
  nesting test proves the limit still refuses an entire batch.
- `test_flow_behaviors.py`: two summary assertions use plain wording, keeping
  original ordering/shape assertions.
- `test_meta_nodes.py`: exact Brief schema expectations include flow summaries
  only on flow records. Invalid-spec no-publication checks remain unchanged.
- `test_dev_test_only_visibility.py`: exact partition counts become 18/25/16.
- `test_node_claims.py`: review status follows actual metadata, not admission;
  source receipt includes the new runtime runner. Protocol-only limitations are
  explicit for join/wait callbacks.
- New `test_family_two_records.py`: membership, bounded complete exports,
  strict declaration validation/hash changes, handles and provenance.
- New `test_flow_claims.py` plus scenario modules: data-driven actual-engine
  evidence, receipt freshness and fixed run/timeout/isolation cases.

Initial block-3 suite: **5,089 passed, 187 skipped**. Follow-up verification is recorded below. No real API calls.

## Startup refusal follow-up

Owner decision 7 is enforced for normal App Run startup using the captured graph
and existing shared analysis. The adapter checks severity rather than a code
allow-list, so future error findings cannot silently become runnable. The same
`MergePlanError` preserves App Run notifications and typed child errors. Existing
explicit-plan runtime fixtures remain available. Merge/Wait records now describe
startup refusal, and manifests, generic claims and the 95-scenario real-engine
receipt are refreshed.

New `test_flow_startup_refusals.py` covers both escaping inputs, omitted children,
impossible/missing waits, no run/outputs/events, App Run toast, typed child error,
and severity-based adapter handling. `test_run_lifecycle.py` and
`test_wait_until_reachability.py` replace downstream-target test scaffolding with
independent slow paths; their leak/Stop/isolation assertions remain. The latter
now expects a disconnected target to refuse startup.

Follow-up full suite: **5,105 passed, 187 skipped in 49.31 seconds**. The focused
startup/lifecycle/reachability suite passed 53 tests. Documentation link checks
and whitespace checks also pass. No API calls.

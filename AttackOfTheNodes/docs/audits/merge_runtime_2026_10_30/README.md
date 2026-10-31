# Collecting Merge runtime — block 1, 2026-10-30

Base `f57f4ed6d646ed9f1bf733c415d98792f171369e`, branch
`codex/merge-arrival-runtime`. Implements the owner's approved family-2 plan
revision 1, decisions 1–6 and same-slot R1. Review level: Important.

## Evidence and integration boundary

`tests/test_merge_arrival_runtime.py` runs **57 real-engine cases**. Controlled
Events govern local node execution; no Merge coordinator callback is faked.
The matrix covers actual two-file reads with reversed arrivals; A slow and
B→C/D with Merge hosted on A/C/D, direct/Beacon wiring, both arrival orders;
concurrent same-slot values, exclusive scalar routes and absent values;
shared producer/Beacon invocations; simultaneous/tied arrivals; independent
End; Stop; terminal and recovered errors; workflow abort; no-arrival failure;
depth refusal; fresh joins/runs and stale callbacks; numeric slots after z;
Wait Until on Merge; duplicate notification and contradictory shape diagnostics.
Vault/source integration also remains covered by the updated payload-plan graph.

## Normal-startup follow-up (rebased onto `5839bfe`, #162/#163)

The initial branch had no production plan supplier; that gap is fixed.
`flow_behaviors.merge_plans_from_analysis` translates the existing shared proof
(root fork, cardinality and producer lineages). Normal MasterState startup
captures its own workflow, derives plans from that snapshot and records the same
revision. This covers app, RunService and child-run callers without patches.
Explicit plans remain supported; no second analyser or cardinality guess exists.
No metadata/admission/trial changes. Runtime fingerprints and evidence are refreshed.

`test_merge_plan_integration.py` adds **22 normal-startup real-engine cases**:
reversed two-file collection; A/C/D hosts × direct/Beacon × separate/shared C/D
slot; both exclusive outcomes; independent End/failure; saved RunService;
subworkflow return record; two-Merge measurement/refusal; and fresh per-run
snapshot/cardinality derivation. Existing 57 explicit-plan tests remain.
`test_flow_behaviors.py` changes repeated-join app acceptance into an error
expectation, and checks unproved collecting shapes at bounds/loops.

**Two-Merge result:** with preflight deliberately bypassed and only the first
join's proof supplied, both outputs were the identical original collected
record. The second Merge failed to wrap/collect a new `path_a` record because
the first winner had detached from its group. This is unsupported. The shared
analysis now emits app errors for `needs_review` and repeated shapes, rather
than warnings. A normal RunService start refuses that saved graph before
creating a run; direct automatic startup cannot produce an unproved plan either.
Standalone Merge still passes through, as documented.

## Review follow-up — 2026-10-31

The existing structural walk now closes the root and producer paths when leaving
Merge. A path-local closed-join marker is cleared only by a fresh split; this
removes the overbroad ancestor-join search without adding another traversal.
Two and three sequential split/Merge stages have separate roots/plans and run
without hand-written plans. Already-joined paths, an inner join feeding an outer
join, and two joins sharing one split still fail before normal startup.

Eight added cases bring `test_merge_plan_integration.py` to **30 cases**. They
include the three refused graphs above, sequential depth measurements, a Textual
pilot pressing Run and checking the visible `Can't start: ...` toast followed by
a successful repaired run, and a child refusal routed as `child_flow_invalid`.
`MergePlanError` is a dedicated `ValueError` subclass; it is handled in app and
child startup without swallowing unrelated ValueErrors. Diagnostic messages
state the connection problem and repair in plain words. The size-limit assertion
in `test_flow_behaviors.py` follows its clearer wording; its limit is unchanged.

**Three-split result:** completes once at every Merge with depth limit 5. At
limit 2 the third Branch refuses all children with `branch_depth_exceeded`.
Closing a group does not reset supervisor depth. The continuing path still
retains the shallowest participant's depth. No loop or draft-admission behavior
was changed. Source/dependency attestations and the claims receipt are refreshed.

## Verification

Full-suite command: `python -m pytest -n auto -q` from the app directory.
Initial block result: **4,853 passed, 187 skipped**. Follow-up full-suite result:
**4,976 passed, 187 skipped in 47.18 s**, zero xfails.
No real API or model calls.
The first full run exposed two stale fingerprints, a half-initialized Supervisor
test, and an accidental failure-abort/user-Stop flag regression. All are fixed;
the existing failure-abort display assertion was preserved.

## Changed existing tests and reasons

- `test_branch_merge_paths.py`: `test_an_eight_way_branch_runs_every_path_and_merges_once`
  now supplies eight explicit scalar slot declarations. `test_a_slot_above_input_slots_is_a_hidden_input_warning`
  and `test_editor_raises_input_slots_to_cover_connected_slots` drop the removed
  selected-value fixture argument; validator expectations are unchanged.
- `test_debug_nodes.py`: `test_merge_node_waits_and_forwards_selected_input` is
  renamed `test_merge_node_waits_and_collects_arrivals`, supplies graph facts and
  expects both path values once. `test_deep_branch_respects_depth_limit` now
  asserts the surfaced refusal error and uses unattended branch termination;
  depth still stops at five, but refusal is no longer silently dropped.
- `test_debug_nodes.py` editor fixtures/expected dictionaries remove only the
  retired value field in `test_merge_config_uses_multi_branch_selector_and_carry_forward_dropdown`,
  `test_merge_options_include_nested_merge_beacons`,
  `test_saving_merge_config_connects_selected_branch_end`,
  `test_saving_merge_config_unchecked_branch_disconnects_branch_end`,
  `test_saving_merge_config_preserves_merge_home_branch_input`, and
  `test_deleting_merge_beacon_prunes_merge_config_selection`.
  Their async helper functions carry these assertions; wiring stays tested.
- `test_error_routing.py`: `test_skip_stops_at_a_merge_with_a_live_sibling` becomes
  `test_failed_member_fails_merge_without_partial_continuation`; it supplies graph
  facts and requires one failed Merge, no successful continuation and downstream
  upstream-failed status, replacing the old partial pick-one result.
- `test_execution_status.py`: `test_barriers_keep_runtime_wait_semantics_and_finish_symbols`
  supplies graph facts for Merge, preserving its final completed UI status.
- `test_merge_branch_identity.py`: `test_no_edit_merge_save_keeps_closure_carry_forward_and_beacon`,
  `test_no_edit_save_keeps_unmatched_values_and_warns`, and
  `test_unchecking_a_kept_closure_drops_it` (async helper) remove the retired value
  field and explicitly assert it is absent; closure/carry/Beacon identity is kept.
- `test_payload_plan_integration.py`: `test_manager_reader_writer_parallel_merge_and_end_branch`
  supplies graph facts and asserts the complete collected record. Both projection
  variants now explicitly show `{input[path_a]}` or `{input[path_b]}` downstream,
  preserving all file, Vault, display and End assertions.
- `test_payload_runtime_contracts.py`: `test_text_output_payload_is_captured_before_continuing_connected_path`
  uses an initialized real engine instead of `object.__new__(Supervisor)` and a
  graph stub. It verifies publication before the connected End begins.
- `test_recovery_flow.py`: `test_merge_keeps_its_branch_after_a_mux_is_inserted_inside_the_branch`
  removes the retired value-field fixture; its wiring assertions are unchanged.
- `test_wait_until_reachability.py`: `test_branch_refused_by_the_depth_limit_does_not_count_as_delivered`
  now expects Branch's typed refusal plus the dependent waiter's unreachable
  error, while still asserting no target delivery. `test_wait_on_a_node_after_a_merge_completes`
  supplies participant/slot declarations, excluding the independent waiter path.
- `test_node_claims.py`: evidence hashes now also bind MasterState, RunContext and
  the new real-engine arrival matrix. No existing claim expectation is weakened.
  Existing source-menu/manifest tests retain their checks against refreshed hashes.

## Plan versus code

The plan's main descriptions of the old runtime were accurate. Details found:
normal Branch configs with `branch_count` always launch all paths; only legacy
configs without that field select by `condition`. This is already reviewed and
is preserved/tested. Unwired chosen ports still skip, as the reviewed record
specifies. No required-join escape analysis was added (block 2 owns it).

Absorption needed a small display-reducer change beyond the named runtime files:
removing completion events alone leaves a stale running visit that outranks the
winner's done status. A termination field now retires that arrival without a
saved-node completion/error/skip event. The minimal editor edits decouple value
selection from the explicitly preserved wiring helpers. No owner decision was
reopened; no runtime shape is inferred from timing.

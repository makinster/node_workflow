# App Run validator audit — PR #165 follow-up

Scope: report only. `frontend/app.py::action_run_workflow` saves, switches to the
execution screen and schedules `_start_workflow`; neither calls
`validate_workflow`. `_start_workflow` catches contract/flow startup refusals.
The flow adapter now rejects **all error-level findings from the existing shared
analysis**, including graphs with no Merge. It does not run the other validator
checks. No general validation was added to App Run.

## Confirmed real startup probes

[validator_startup_probes.json](validator_startup_probes.json) records validator
codes and actual `start_workflow()` outcomes (no explicit plans). No API calls;
invalid settings were on local nodes, often deliberately unconnected, while a
simple Start→End path ran. “Started” means a run was created, not that the invalid
node can execute successfully. This proves lack of full preflight, not successful
handling of bad configuration.

The following validator errors **still reach a run** through that entry point:

- `deleted_node_stub` (tombstone), `multiple_start_nodes`, `unknown_node_type`,
  `missing_node`, `undeclared_port`.
- `invalid_number`, `saved_name_missing`, `missing_file_path`.
- `vault_source_key_missing`, `vault_output_key_missing`, `undeclared_vault_key`.
- `subworkflow_not_found`.

An invalid required Start row instead produced `ContractInputError` before a run;
that independent contract-input guard remains in place.

## Remaining validator-only errors: source inventory

These additional validator errors have **no corresponding startup preflight
check**, from reviewing all `errors.append` sites in `backend/validator.py` and
the startup path. They were not each reproduced as separate runtime probes:

| Area | Codes |
|---|---|
| Connections / sources | `vault_only_connection`, `duplicate_input_source` |
| Configuration | `invalid_file_path`, `invalid_rows`, `secret_not_configured` |
| Error Mux | `mux_wrong_source_port`, `mux_unknown_code` |
| Child calls | `subworkflow_not_callable`, `subworkflow_recursion`, `subworkflow_input_unknown`, `subworkflow_stash_missing`, `subworkflow_input_invalid`, `subworkflow_input_missing`, `subworkflow_result_unknown` |
| Return contract | `multiple_return_ends`, `return_end_unmerged` |
| Contract rows | `contract_row_invalid` — Start inputs can be refused by `resolve_inputs`; End result rows are not inspected by startup |

Child-call and node-specific execution guards may subsequently fail those nodes
inside an already created run. This inventory does not claim every malformed
setting survives every other guard. `no_start_node` is separately blocked by
`find_start_node_id`: startup returns false. The flow findings are separately
blocked by `MergePlanError` before run creation. Callable Start input validation
still runs before state reset.

## Compatibility

[startup_compatibility.json](startup_compatibility.json) records a read-only
normal-mode analysis of all eight graph objects in bundled delivery specs and
fixtures. None is newly refused. The checked-out `workflows/` directory contains
no saved workflows; the owner's external library was not audited or modified.

All existing positive real-engine join tests still pass: direct/Beacon,
exclusive alternatives into one slot, independent side End/failure, sequential
splits, standalone hand-built passthrough, subworkflow and saved RunService runs.
Warning-only forms stay runnable; the adapter test checks warnings explicitly.

Newly refused forms are precisely existing error-level findings that the old
adapter ignored: a required conditional route escaping Merge, a conditional
split omitting a required slot, missing Wait targets, and impossible waits
(self/downstream/mutual/disconnected target). `repeated_join_unsupported` is also
refused if supplied in a report; current normal-mode unsafe repeated joins
already produce `flow_needs_review` and were refused before this patch. No
additional successful hand-built form was found to be refused.

Two old test setups depended on bypassing those existing errors: lifecycle/stale
run tests manually completed a downstream target, and the disconnected-target
test waited for a runtime failure. Lifecycle/stale tests now use a genuinely
independent slow target path; disconnected-target behavior is tested as startup
refusal. Runtime failure/Stop/cleanup assertions remain intact.

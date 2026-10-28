# Step 1 verification — route review, 2026-10-28

Review base `48959db`, branch `codex/draft-workflow-step1`.
No real model/API calls or Secrets access. Judge replies below are canned;
these checks prove harness decisions, not real inference quality.

- Focused tests: 96 passed in 6.83 s.
- Full pytest -n auto: 3,330 passed in 44.60 s.
- Standalone mock batch: ten cases, 21 target fixtures, all pass.
- V2 designer spec unchanged (55 nodes; prior CLI check had no diagnostics).
- Complete palette: 12 types, 9,364 characters; no clipping.
- Mock calls: 31 designer calls plus 44 calibration judge calls.

| Calibration fixture | Good rules | Bad rules | Mock good judge | Mock bad judge |
|---|---|---|---|---|
| broken_braces | pass | fail | pass | fail |
| wrong_transform | pass | fail | pass | fail |
| wrong_order | pass | fail | pass | fail |
| disabled_transient | pass | fail | pass | fail |
| wrong_path | pass | fail | pass | fail |
| overwrite | pass | fail | pass | fail |
| reversed_true_false | pass | fail | pass | fail |
| ordinary_fan_out | pass | fail | pass | fail |
| ignored_clarification | pass | fail | pass | fail |
| unreachable_correct_node | pass | fail | pass | fail |
| double_brace_path | pass | fail | pass | fail |
| whole_file_dict | pass | fail | pass | fail |
| configured_content_override | pass | fail | pass | fail |
| label_in_saved_content | pass | fail | pass | fail |
| contains_empty | pass | fail | pass | fail |
| hardcoded_heading | pass | fail | pass | fail |
| partial_file_display | pass | fail | pass | fail |
| partial_file_copy | pass | fail | pass | fail |
| partial_clarified_content | pass | fail | pass | fail |
| serial_parallel_work | pass | fail | pass | fail |
| conditional_work_before_choice | pass | fail | pass | fail |
| uppercase_before_empty_choice | pass | fail | pass | fail |

The original 19 pairs are retained. The last three add serial work on one
parallel path, both status displays before a Conditional, and uppercase work
before the empty/nonempty decision. Every good draft passes and every bad
draft fails. Deliberately wrong canned-judge tests separately count 22 false
passes and 22 false failures and reject the batch.

Oracle v3 freezes required structural roles, ordering/producer relations and
route work in each case record. The matcher is case-id independent and accepts
renamed handles and swapped parallel ports. Every declared fork port must do
its own real work. Dominance, exclusive reachability and recorded execution
routes exclude hoisted, shared, sibling or End-only work. Actual producer-node
lineage prevents a decorative operation from claiming another value.

All earlier containment/provenance/style regressions remain. No production
backend or designer-spec changes were required. Step 2 remains separately
approved and unexecuted.

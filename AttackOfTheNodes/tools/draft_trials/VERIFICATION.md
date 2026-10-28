# Step 1 verification — PR #135 review fixes, 2026-10-28

Review base `4b42912`, branch `codex/draft-workflow-step1`.
No real model/API calls or owner Secrets access. Judge replies below are canned;
this proves harness decisions, not real inference quality.

- Focused tests: 78 passed in 6.09 s.
- Full pytest -n auto: 3,312 passed in 41.56 s.
- Standalone mock batch: ten cases, 21 target fixtures, all pass.
- Existing v2 designer spec unchanged (55 nodes; prior CLI check had no diagnostics).
- Complete palette: 12 types, 9,364 characters; no clipping.
- Mock calls in final proof: 31 designer calls plus 38 calibration judge calls.

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

The first fifteen pairs are retained; the last four reproduce provenance false
passes. All pair expectations match. A separate deliberately wrong canned-judge
test measures 19 false passes and 19 false failures and fails the batch gate.

Containment probes reproduce the symlinked-library write and marker-sentinel
overwrite with stubbed batch execution, then verify both now stop before writes.
Tests also cover nested internal/external/dangling links, FIFOs, hard links,
invalid preparation records, unchanged sentinels, and rejection before backend
imports/environment changes. Preparation never opens library or Secrets files.

Oracle v2 preserves whole-input expressions through transforms and adapters,
distinguishes data from branch-control dependence, and traces saved paths to
the actual writer. Every case has a provenance regression; Ready intentionally
remains a permitted literal. Unsupported equivalent expressions fail for review.

All trial modules use multiline statements, checked with AST/token regressions.
No app/backend changes were needed. Step 2 remains separately approved and
unexecuted. Prepared-tree validation is not an OS sandbox against concurrent
directory replacement.

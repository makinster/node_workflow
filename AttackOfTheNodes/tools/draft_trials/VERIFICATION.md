# Step 1 verification — 2026-10-28

Base `19640f9`, branch `codex/draft-workflow-step1`.
No real model/API calls or owner Secrets access. All judge outputs below are
canned; this proves harness decisions, not inference quality.

- V2 CLI build --check: ok true, zero diagnostics, 55 nodes.
- Focused tests: 40 passed in 4.93 s.
- Full pytest -n auto: 3,274 passed in 38.41 s.
- Standalone batch: ten cases, 21 target fixtures, all pass.
- Complete palette: 12 types, 9,364 characters; no clipping.
- Mock calls: 31 designer calls and 30 calibration judge calls.

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

All good/bad pair expectations match. A separate deliberately incorrect canned
judge test measures 15 false passes and 15 false failures; the batch gate fails.
The ordinary designer supports every planned step with existing nodes. Deep
nested report checks and deterministic case semantics remain in the external
runner, as approved. Unsupported equivalent layouts fail for review instead
of being silently accepted. Step 2 remains separately approved and unexecuted.

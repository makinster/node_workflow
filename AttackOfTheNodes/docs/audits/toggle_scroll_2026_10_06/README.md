# Toggle visibility and scrolling evidence

Run from the authoritative checkout using its venv:

```bash
.venv/bin/python AttackOfTheNodes/docs/audits/toggle_scroll_2026_10_06/audit.py --label new_baseline --require-clean
```

The runner uses synthetic graphs, populated typed Vault entries, and production
CSS. It never loads or saves owner workflows/settings. Before/after evidence is
stored separately; do not overwrite a historical label for a new baseline.
`--require-clean` returns a failure if scrolling/visibility findings or Cancel
changes remain; omit it when collecting a diagnostic baseline with known gaps.

- `before_summary.json` / `before_evidence.json.gz`: initial rapid diagnostic
  scan at 100 columns; transient geometry candidates must be checked after
  layout settles.
- `before_settled_summary.json` / `before_settled_evidence.json.gz`: settled
  before-fix scan at 100 columns.
- `after_summary.json` / `after_evidence.json.gz`: intermediate three-width scan
  that revealed two additional short-viewport failures.
- `after_final_summary.json` / `after_final_evidence.json.gz`: final
  60/100/140-column scan.

The source review, repairs, convenience decisions, and verification limitations
are in [the audit report](../../NODE_CONFIG_VISIBILITY_SCROLL_AUDIT.md).

## Final coverage

108 production-CSS mounts; 36 editable types; 1,202 states; 4,008 navigation samples.
Cancel unchanged 108/108. No remaining scroll findings, visibility-rule mismatches, or visible disabled selectors/checkboxes in the audited states.

| Type | Widths | States | Navigation samples |
|---|---|---:|---:|
| `branch_end_node` | 60/100/140 | 0 | 12 |
| `branch_node` | 60/100/140 | 30 | 120 |
| `chat_completion_node` | 60/100/140 | 72 | 150 |
| `concat_node` | 60/100/140 | 36 | 108 |
| `conditional_node` | 60/100/140 | 34 | 138 |
| `counter_node` | 60/100/140 | 36 | 113 |
| `deep_branch_node` | 60/100/140 | 30 | 120 |
| `echo_node` | 60/100/140 | 36 | 113 |
| `embedding_node` | 60/100/140 | 38 | 120 |
| `end_node` | 60/100/140 | 36 | 96 |
| `error_node` | 60/100/140 | 37 | 129 |
| `file_output_node` | 60/100/140 | 51 | 120 |
| `file_reader_node` | 60/100/140 | 36 | 113 |
| `file_view_node` | 60/100/140 | 17 | 90 |
| `get_variable_node` | 60/100/140 | 36 | 119 |
| `http_request_node` | 60/100/140 | 32 | 144 |
| `image_generation_node` | 60/100/140 | 40 | 136 |
| `json_path_node` | 60/100/140 | 30 | 138 |
| `logger_node` | 60/100/140 | 48 | 125 |
| `memory_snapshot_node` | 60/100/140 | 36 | 118 |
| `merge_node` | 60/100/140 | 0 | 12 |
| `no_op_node` | 60/100/140 | 36 | 112 |
| `probe_node` | 60/100/140 | 36 | 118 |
| `random_branch_node` | 60/100/140 | 30 | 132 |
| `random_number_node` | 60/100/140 | 37 | 137 |
| `repeat_counter_node` | 60/100/140 | 36 | 113 |
| `set_variable_node` | 60/100/140 | 43 | 114 |
| `sleep_node` | 60/100/140 | 36 | 113 |
| `start_node` | 60/100/140 | 36 | 113 |
| `text_output_node` | 60/100/140 | 42 | 130 |
| `text_transform_node` | 60/100/140 | 41 | 113 |
| `user_text_input_node` | 60/100/140 | 36 | 118 |
| `variable_reader_node` | 60/100/140 | 36 | 119 |
| `variable_setter_node` | 60/100/140 | 42 | 122 |
| `wait_until_node` | 60/100/140 | 0 | 42 |
| `window_control_node` | 60/100/140 | 4 | 78 |

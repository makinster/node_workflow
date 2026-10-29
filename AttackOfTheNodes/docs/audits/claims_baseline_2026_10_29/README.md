# Registered-node claims baseline — 2026-10-29

Captured before this repair from `439e6148e29eaab951e187592d484b508190aa15`
(main including #150). The owner accepted the eight recommendations in
`/home/makin/src/agent_channel/palette-scaling-plan.md`; this PR implements
claims only, without shortlist work, new nodes, metadata backfill or admission.

[`baseline.json`](baseline.json) is the immutable source-reviewed snapshot of
all 59 types: 12 reviewed records and 47 pending. It records every declared
input/output (including `to` / `pass_through` where present), retained default
flags, global authoring acceptance, execute support and LF-normalized sources.
Absent `to` means the legacy implicit downstream route, not a newly invented
Vault capability. Tombstone is registered but deliberately non-authorable.

Before this PR, all four flags were globally accepted as explicit overrides.
V = `vault_write`, T = `transient_output`, D = `dead_drop_passthrough`,
O = `transient_outputs`. The support column is the pre-change execute audit;
it does not promise all retained defaults are supported. Start V/T applies to
legacy greeting mode; explicit rows have their own destinations. No type reads O.

| Registered type | Review | Honours | Declared output routes / optional forwarding |
|---|---|---|---|
| `ask_claude_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `hermes_ask_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `hermes_investigate_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `ask_local_model_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `chat_completion_node` | pending | V,D | default: downstream/vault; optional forwarding |
| `check_reply_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `check_workflow_spec_node` | pending | V,T | default: downstream/vault; report: vault |
| `concat_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `conditional_node` | reviewed | none | true, false: implicit downstream |
| `context_pack_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `counter_node` | pending | none | default: implicit downstream |
| `deep_branch_node` | pending | none | branch: implicit downstream |
| `tombstone_node` | pending | none | none |
| `disk_space_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `echo_node` | pending | none | default: implicit downstream |
| `embedding_node` | pending | none | default: implicit downstream |
| `end_node` | reviewed | none | none |
| `error_mux_node` | pending | none | default, unmatched: implicit downstream |
| `error_node` | pending | none | default: implicit downstream |
| `file_view_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `file_reader_node` | reviewed | V,T | default: downstream/vault |
| `file_output_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `file_age_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `find_lines_node` | pending | V,T,D | default: downstream/vault; optional forwarding; match_count: vault |
| `get_variable_node` | pending | none | default: implicit downstream |
| `git_status_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `http_request_node` | pending | none | default: implicit downstream |
| `if_changed_node` | pending | none | changed, no_change: downstream |
| `image_generation_node` | pending | none | default: implicit downstream |
| `hermes_investigation_result_node` | pending | V,T,D | default: downstream/vault; optional forwarding; state: vault |
| `json_path_node` | reviewed | none | default: implicit downstream |
| `pick_one_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `logger_node` | pending | none | default: implicit downstream |
| `memory_snapshot_node` | pending | none | default: implicit downstream |
| `merge_node` | pending | none | default: implicit downstream |
| `branch_end_node` | reviewed | none | default: implicit downstream |
| `no_op_node` | pending | none | default: implicit downstream |
| `node_catalogue_node` | pending | V,T | default: downstream/vault |
| `hermes_notify_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `branch_node` | reviewed | none | path_a…path_bl (64 ports): implicit downstream |
| `probe_node` | pending | none | default: implicit downstream |
| `random_branch_node` | pending | none | path_a, path_b: implicit downstream |
| `random_number_node` | pending | none | default: implicit downstream |
| `read_lines_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `recall_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `record_event_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `remember_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `repeat_counter_node` | pending | none | default: implicit downstream |
| `set_variable_node` | pending | none | default: implicit downstream |
| `sleep_node` | pending | none | default: implicit downstream |
| `start_node` | reviewed | V,T | default: downstream/vault |
| `subworkflow_node` | pending | none | default: implicit downstream |
| `text_output_node` | reviewed | none | default: downstream |
| `text_transform_node` | reviewed | none | default: implicit downstream |
| `user_text_input_node` | reviewed | none | default: implicit downstream |
| `variable_reader_node` | pending | none | default: implicit downstream |
| `variable_setter_node` | pending | none | default: implicit downstream |
| `wait_until_node` | pending | none | default: implicit downstream |
| `window_control_node` | pending | none | default: downstream |

## Follow-up

The executable claims, source-bound observations and authoring rejection policy
are implemented in the next commit of this claims-only milestone.

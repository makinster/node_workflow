# Complete input inventory

Baseline `f0aa39d`; every registered type, including hidden/debug and trigger-only ports.
Types are coarse filters; runtime caps, required values and detailed shapes still apply.
The contract JSON is the independent reviewed expectation used by tests. See README for findings.

| Node | Port | Accepted sources | Type | UI control / fields |
|---|---|---|---|---|
| ask_local_model_node | input | upstream, vault, configured | string | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| ask_local_model_node | context | upstream, vault, configured | string | context_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| context_pack_node | input | upstream, vault, configured | any | items.source: Ordered item rows; Configured text, Vault key, or the single incoming value; no file open. |
| check_reply_node | input | upstream, vault, configured | string | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| find_lines_node | input | upstream, vault, configured | string | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| read_lines_node | input | upstream, vault, configured | any | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| hermes_investigation_result_node | input | upstream, vault, configured | string | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| hermes_investigate_node | input | upstream, vault, configured | string | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| hermes_investigate_node | evidence | upstream, vault, configured | string | evidence_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| hermes_ask_node | input | upstream, vault, configured | string | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| hermes_ask_node | context | upstream, vault, configured | string | context_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| pick_one_node | input | upstream, vault, configured | string | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| if_changed_node | input | upstream, vault | any | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| recall_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| remember_node | input | upstream, vault, configured | any | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| record_event_node | input | upstream, vault | any | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| hermes_notify_node | input | upstream, vault | any | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| file_age_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| git_status_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| disk_space_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| error_mux_node | input | upstream | any | recover_from: Normal input and optional error record; recovery is structural, not a Vault/text source selector. |
| error_mux_node | error | upstream | any | recover_from: Normal input and optional error record; recovery is structural, not a Vault/text source selector. |
| subworkflow_node | input | upstream, vault, configured, stash | contract | inputs.source: Per-child input types; Configured, Upstream payload, Vault, Stash, or omitted mapping/default. Results routed separately. |
| window_control_node | file | upstream, vault | file | file_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| file_view_node | file | upstream, vault, configured | file | file_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| file_output_node | content | upstream, vault, configured | string | content_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| file_output_node | file_path | upstream, vault, configured | file | file_path_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| http_request_node | input | upstream, configured | any | body_source: POST only: config body vs input (string/bytes/JSON); GET ignores body. |
| random_number_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| json_path_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| text_transform_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| start_node | — | none | — | No input ports |
| end_node | input | upstream, vault | contract | results.source: Ordinary incoming value for log; Return End results select Incoming payload or Vault key by contract type. |
| branch_node | input | upstream, vault | any | branch_payload_sources: Per-path incoming or selected Vault read; Vault keys first selected in Reads. Seed fallback to upstream. |
| branch_end_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| conditional_node | input | upstream, vault | any | left_value_source: input vs variable; any value compared as text; named key is free text. |
| merge_node | path_a | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_b | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_c | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_d | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_e | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_f | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_g | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_h | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_i | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_j | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_k | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_l | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_m | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_n | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_o | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_p | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_q | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_r | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_s | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_t | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_u | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_v | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_w | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_x | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_y | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_z | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_aa | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ab | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ac | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ad | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ae | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_af | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ag | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ah | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ai | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_aj | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ak | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_al | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_am | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_an | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ao | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ap | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_aq | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ar | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_as | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_at | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_au | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_av | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_aw | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ax | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ay | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_az | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_ba | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bb | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bc | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bd | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_be | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bf | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bg | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bh | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bi | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bj | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bk | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| merge_node | path_bl | upstream | any | selected_input_port: All 64 declared path slots; input_slots activates 1–64. Engine coordinates selected payload; no standard source select. |
| wait_until_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| set_variable_node | input | upstream, configured | any | value_source: input vs literal; values unchanged; named output is a dynamic Vault write. |
| get_variable_node | input | vault, configured | any | variable_name: Named Vault read with configured default; incoming edge is a trigger. |
| concat_node | input | upstream, vault, configured | any | template: Template fields read all named Vault values and prepared inputs; {input} means incoming only. No whole-input source selector. |
| variable_setter_node | input | upstream, configured | any | value: Nonempty literal wins; empty literal uses upstream; no source menu by design. |
| variable_reader_node | input | vault, configured | any | variable_name: Named Vault read with configured default; incoming edge is a trigger. |
| text_output_node | input | upstream, vault | any | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| user_text_input_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| file_reader_node | input | upstream, vault, configured | file | input_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | prompt | upstream, vault, configured | string | prompt_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_1 | upstream, vault, configured | string | context_1_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_2 | upstream, vault, configured | string | context_2_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_3 | upstream, vault, configured | string | context_3_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_4 | upstream, vault, configured | string | context_4_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_5 | upstream, vault, configured | string | context_5_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_6 | upstream, vault, configured | string | context_6_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_7 | upstream, vault, configured | string | context_7_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | context_8 | upstream, vault, configured | string | context_8_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| chat_completion_node | document | upstream, vault, configured | string | document_source: Source controls match the runtime resolver; Vault key visible for Vault, configured value visible for Configured. |
| image_generation_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| embedding_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| tombstone_node | — | none | — | No input ports |
| echo_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| logger_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| sleep_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| counter_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| memory_snapshot_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| probe_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| error_node | input | trigger only | any | implicit: Incoming edge triggers work; payload is not selected as task input (may be forwarded). Parameters, saved store or user supplies the result. |
| random_branch_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| deep_branch_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| no_op_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |
| repeat_counter_node | input | upstream | any | implicit: Prepared upstream payload, no alternate source selector; config can tune behavior/template. |

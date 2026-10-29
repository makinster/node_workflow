# Concat Vault and output-routing audit — 2026-10-29

Base `495e9aa`, branch `codex/concat-vault-diagnostics`. Local source review
and mock/local-engine verification only; no provider or owner-workflow calls.

Concat previously called `signal_done` directly: it never performed the
standard Vault write, disabled-output switch, or unchanged-input forwarding.
It now uses `saved_values.finish`: write the formatted string with type
`string` before completion, forward the original input by identity when chosen,
or omit its transient value. A missing bare format name now errors with that
name, rather than silently substituting empty text. Existing brace/field
failures also signal a formatting error without publishing a result.

## Standard result-write inventory

Reviewed all 59 registered types. After Concat's fix, 25 declare a default
output with `to` containing `vault`; each has a direct store or a shared helper
that stores the own result. Start's explicit rows/no-input mode is separate:
its legacy `vault_write` switch is ignored there, so it now warns too.

| Implementation | Types |
|---|---|
| Direct standard writes | Start (legacy greeting), File Reader, File Write, File Viewer, Chat Completion, Ask Claude, Ask local model, Ask Hermes, Pick one |
| Shared result-routing helper | Concat, Context Pack, Check reply, Disk Space, File Age, Find lines, Git Status, Read lines, Remember, Recall, Notify me, Record event, Investigate, Investigation result |
| Meta publish helper | Node catalogue, Check workflow spec |

The other **34 registered types** do not implement the standard result-write
switch. One is the non-authorable tombstone. Build/check now warn for the
other **33** when `vault_write` is enabled, and the shared declaration model
no longer invents their requested key:

```
conditional_node counter_node deep_branch_node echo_node embedding_node
end_node error_mux_node error_node get_variable_node http_request_node
if_changed_node image_generation_node json_path_node logger_node
memory_snapshot_node merge_node branch_end_node no_op_node branch_node
probe_node random_branch_node random_number_node repeat_counter_node
set_variable_node sleep_node subworkflow_node text_output_node
text_transform_node user_text_input_node variable_reader_node
variable_setter_node wait_until_node window_control_node
```

This concerns `vault_write` / `vault_write_key`, not all writes. Set Variable,
Counter, Start rows and Subworkflow results have node-specific write rules.
User Text Input and Text Output support their existing named legacy copies.
Those features are preserved. Acceptance of a retained shared key is not a
promise that every node implements its behavior.

## Structural diagnostics and limits

`vault_write_unsupported` warns and removes the false standard declaration;
a downstream required read may consequently fail for having no writer.
`template_vault_key_unwritten` warns when a Concat format root (excluding
prepared input names) has no declared writer on any ancestor path. It handles
literal braces and nested format-spec roots. This is conservative graph
analysis: declared ancestry does not prove execution, value presence or timing.
A parallel writer still needs ordering; the warning does not ban valid joins.

`disabled_output_connection` warns when a connected default output's actual
routing settings suppress its payload. Passthrough that still forwards is
allowed. Start rows use their own Downstream/Both routing. Legacy types that
ignore the transient switch are not falsely described as dropping data;
Chat Completion is one such known exception. Changing that older runtime is
outside this repair. A downstream node can still be triggered without data:
this diagnostic is about a missing published value, not graph disconnection.

Check workflow spec adds `fail_on_disabled_output` (default false). V2 opts in
on both checks, so the first diagnostic triggers its existing single redraft
with exact warning details; a second bad draft stops before review/save.
Calibration uses the identical option. No fixture changes or regeneration.
All 23 pairs keep their expected rule verdicts; disabled_transient bad also
fails structurally. Live reviewer verdicts have not been measured.

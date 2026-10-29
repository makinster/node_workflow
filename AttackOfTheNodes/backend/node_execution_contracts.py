"""Authoring metadata verified against node execute methods, not trial fixtures.

These describe runtime values beyond the port's broad data type. NodeFactory
exposes them to all authoring clients; they never drive execution or validation.
"""

EXECUTION_CONTRACTS = {
    'start_node': {
        'output_payload': 'default: with rows absent/empty, greeting string verbatim (default "Workflow started"); transient_output=false suppresses it. Nonempty rows replace greeting: one downstream value as-is, several as name:value object, none/no_inputs emits no payload.',
    },
    'end_node': {
        'output_payload': 'None; ends branch. record_line logs [END] completion as normal run framing, not an unrequested effect. return_end publishes workflow results only.',
    },
    'branch_end_node': {
        'output_payload': 'default: input unchanged; absent: empty text.',
    },
    'branch_node': {
        'output_payload': 'Each parallel path gets input, or its branch_payload_sources Vault value (missing key: input).',
    },
    'user_text_input_node': {
        'output_payload': 'default: unchanged user answer string; incoming input triggers prompt only.',
    },
    'text_output_node': {
        'output_payload': 'default/log: empty or whitespace-only label = bare formatted text; a set label adds "[label] " unchanged. Label is display framing. The same downstream payload includes any set label (also when saved). {input[path]}: path; {{input}}: literal.',
    },
    'text_transform_node': {
        'output_payload': 'default: transformed string. strip trims whole-input boundary whitespace. Falsy input becomes empty text.',
    },
    'file_reader_node': {
        'output_payload': 'default: whole UTF-8 file as string; missing/unreadable file errors.',
    },
    'file_output_node': {
        'output_payload': 'default: {type:"file",ref_key:string,path:"actual saved absolute path"}; new ref_key="file:"+path; reused identity/lifetime retained. dead_drop_passthrough forwards input; transient_output=false suppresses normal output.',
        'notes': 'Create unique: name.ext if absent; else name (1).ext, name (2).ext, etc.; keeps existing files. Not atomic.',
    },
    'conditional_node': {
        'output_payload': 'Only the selected port (true if matched, false otherwise) emits the unchanged left value: input, or Vault value when left_value_source=variable; never the comparison boolean.',
        'notes': 'equals compares str(left) == str(right_value): case-sensitive, whitespace preserved; no trimming.',
    },
    'concat_node': {
        'output_payload': 'default: format_map string from Vault + inputs (inputs win). {input[path]} reads the path key.',
    },
    'json_path_node': {
        'output_payload': 'default: extracted typed value, or default_value on miss. Input: JSON text or parsed value; invalid JSON errors.',
    },
}

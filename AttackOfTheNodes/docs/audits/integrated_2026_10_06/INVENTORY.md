# Integrated coverage and actual controls — 2026-10-06

All 37 registered types are accounted for. The 36 editable/user-facing screens were mounted at 60/100/140 columns with production CSS; tombstone is intentionally excluded. The actual selector exposes 34 types, including members behind groups.

For recommended layouts and unresolved findings, use [CONFIG_UI_BUILD_PLAN.md](../../CONFIG_UI_BUILD_PLAN.md) and the per-node policy in the [original audit](../../NODE_CONFIG_UI_AUDIT.md). The three new file/window layouts are in the [File Output review](../../FILE_OUTPUT_INTEGRATION_REVIEW.md).

| Type | Selector | Current tabs | Conditional state captures | Layout recommendation |
|---|---|---|---|---|
| `chat_completion_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 57 | Compact applicable form; omit unsupported generic controls |
| `concat_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `conditional_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 9 | Compact applicable form; omit unsupported generic controls |
| `counter_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `deep_branch_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 5 | Compact applicable form; omit unsupported generic controls |
| `tombstone_node` | intentionally internal | not mounted | n/a | Preserve internal deleted-node contract |
| `echo_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `embedding_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 9 | Compact applicable form; omit unsupported generic controls |
| `end_node` | hidden compatibility | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `error_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 8 | Compact applicable form; omit unsupported generic controls |
| `file_reader_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `file_view_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact file/display configuration, genuine routing only |
| `file_output_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 21 | Applicable source/write/routing sections; explain platform capabilities |
| `get_variable_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `http_request_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `image_generation_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 11 | Compact applicable form; omit unsupported generic controls |
| `json_path_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 5 | Compact applicable form; omit unsupported generic controls |
| `logger_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 9 | Compact applicable form; omit unsupported generic controls |
| `memory_snapshot_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `merge_node` | addable | flat | 0 | Focused topology configuration / Connections |
| `branch_end_node` | addable | flat | 0 | Flat Merge Beacon configuration |
| `no_op_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `branch_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 6 | Focused topology configuration / Connections |
| `probe_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `random_branch_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 5 | Compact applicable form; omit unsupported generic controls |
| `random_number_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 8 | Compact applicable form; omit unsupported generic controls |
| `repeat_counter_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `set_variable_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 9 | Compact applicable form; omit unsupported generic controls |
| `sleep_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `start_node` | hidden compatibility | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `text_output_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 8 | Compact applicable form; omit unsupported generic controls |
| `text_transform_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 12 | Compact applicable form; omit unsupported generic controls |
| `user_text_input_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `variable_reader_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 7 | Compact applicable form; omit unsupported generic controls |
| `variable_setter_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 8 | Compact applicable form; omit unsupported generic controls |
| `wait_until_node` | addable | 1 - Wait, 2 - Connections | 0 | Retain Wait / Connections |
| `window_control_node` | addable | 1 - Source, 2 - Parameters, 3 - Payloads, 4 - Connections | 4 | Compact target/action; fixed reference output; no forwarding toggle |

## Complete default control inventory

Every tab/control/label/options/value/region, alternate state and keyboard trace is retained in `evidence.json.gz`. Below lists actual default composition; hidden controls are marked and all options are included in the packed evidence. Historical control inventories remain unchanged.

### chat_completion_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Chat Completion
- `Static` `node-config-summary` — Node type: Chat Completion / Send a prompt to an LLM and receive a text response
- `Label` `(no id)` — Incoming Payload
- `Static` `incoming-payload-prompt` — Node source: User Text Input node / Payload: audit_text (any)
- `Label` `form-section-prompt_source` — Required Inputs
- `Label` `field-label-prompt_source` — Prompt source:
- `Select` `field-prompt_source` — Configured
- `Label` `field-desc-prompt_source` — Where the prompt comes from at execution time
- Hidden: `Label` `field-label-prompt_vault_key` — Prompt Vault key:
- Hidden: `Select` `field-prompt_vault_key` — Select.NULL
- Hidden: `Label` `field-label-continue_session_key` — Session:
- Hidden: `Select` `field-continue_session_key` — Select.NULL
- Hidden: `Label` `field-desc-continue_session_key` — Declared AI session whose chat this node resumes
- `Label` `form-section-context_input_count` — Additional Context
- `Label` `field-label-context_input_count` — Context inputs:
- `Select` `field-context_input_count` — 0
- `Label` `field-desc-context_input_count` — Additional inputs appended in order before Document
- Hidden: `Label` `field-label-context_1_source` — Context 1 source:
- Hidden: `Select` `field-context_1_source` — Configured
- Hidden: `Label` `field-desc-context_1_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_1_vault_key` — Context 1 Vault key:
- Hidden: `Select` `field-context_1_vault_key` — Select.NULL
- Hidden: `Label` `field-label-context_2_source` — Context 2 source:
- Hidden: `Select` `field-context_2_source` — Configured
- Hidden: `Label` `field-desc-context_2_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_2_vault_key` — Context 2 Vault key:
- Hidden: `Select` `field-context_2_vault_key` — Select.NULL
- Hidden: `Label` `field-label-context_3_source` — Context 3 source:
- Hidden: `Select` `field-context_3_source` — Configured
- Hidden: `Label` `field-desc-context_3_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_3_vault_key` — Context 3 Vault key:
- Hidden: `Select` `field-context_3_vault_key` — Select.NULL
- Hidden: `Label` `field-label-context_4_source` — Context 4 source:
- Hidden: `Select` `field-context_4_source` — Configured
- Hidden: `Label` `field-desc-context_4_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_4_vault_key` — Context 4 Vault key:
- Hidden: `Select` `field-context_4_vault_key` — Select.NULL
- Hidden: `Label` `field-label-context_5_source` — Context 5 source:
- Hidden: `Select` `field-context_5_source` — Configured
- Hidden: `Label` `field-desc-context_5_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_5_vault_key` — Context 5 Vault key:
- Hidden: `Select` `field-context_5_vault_key` — Select.NULL
- Hidden: `Label` `field-label-context_6_source` — Context 6 source:
- Hidden: `Select` `field-context_6_source` — Configured
- Hidden: `Label` `field-desc-context_6_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_6_vault_key` — Context 6 Vault key:
- Hidden: `Select` `field-context_6_vault_key` — Select.NULL
- Hidden: `Label` `field-label-context_7_source` — Context 7 source:
- Hidden: `Select` `field-context_7_source` — Configured
- Hidden: `Label` `field-desc-context_7_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_7_vault_key` — Context 7 Vault key:
- Hidden: `Select` `field-context_7_vault_key` — Select.NULL
- Hidden: `Label` `field-label-context_8_source` — Context 8 source:
- Hidden: `Select` `field-context_8_source` — Configured
- Hidden: `Label` `field-desc-context_8_source` — Additional context appended in configured order
- Hidden: `Label` `field-label-context_8_vault_key` — Context 8 Vault key:
- Hidden: `Select` `field-context_8_vault_key` — Select.NULL
- `Label` `form-section-document_source` — Optional Inputs
- `Label` `field-label-document_source` — Document / context source:
- `Select` `field-document_source` — Configured
- `Label` `field-desc-document_source` — Optional document appended to the prompt
- Hidden: `Label` `field-label-document_vault_key` — Document Vault key:
- Hidden: `Select` `field-document_vault_key` — Select.NULL

**2 - Parameters**

- Hidden: `Label` `field-label-context_1` — Context 1 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_1` — 
- Hidden: `Label` `field-label-context_2` — Context 2 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_2` — 
- Hidden: `Label` `field-label-context_3` — Context 3 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_3` — 
- Hidden: `Label` `field-label-context_4` — Context 4 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_4` — 
- Hidden: `Label` `field-label-context_5` — Context 5 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_5` — 
- Hidden: `Label` `field-label-context_6` — Context 6 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_6` — 
- Hidden: `Label` `field-label-context_7` — Context 7 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_7` — 
- Hidden: `Label` `field-label-context_8` — Context 8 (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-context_8` — 
- `Label` `field-label-prompt` — Prompt (E to edit, ESC to finish):
- `CommandTextArea` `field-prompt` — 
- `Label` `field-label-document` — Document (E to edit, ESC to finish):
- `CommandTextArea` `field-document` — 
- `Label` `field-label-model` — Model *:
- `Select` `field-model` — claude-opus-4-8
- `Label` `field-label-max_tokens` — Max tokens *:
- `CommandInput` `field-max_tokens` — 1024
- `Label` `field-label-temperature` — Temperature *:
- `CommandInput` `field-temperature` — 1.0
- `Label` `field-desc-temperature` — Ignored by models that do not accept sampling parameters
- `Label` `field-label-api_key_secret` — API key (secrets store key) *:
- `Select` `field-api_key_secret` — Select.NULL

**3 - Payloads**

- `Label` `(no id)` — Downstream node payload
- `Static` `downstream-header-default` — LLM Result  [string]
- `Label` `(no id)` — Payload name:
- `CommandInput` `transient-output-name-default` — LLM Result
- `Label` `(no id)` — Description:
- `CommandInput` `transient-output-desc-default` — Model response text (or forwarded payload on dead-drop)
- `Checkbox` `dead-drop-passthrough` — Forward incoming payload unchanged
- `Label` `(no id)` — Vault Payload
- `Static` `vault-header-default` — LLM Result  [string]
- `Checkbox` `vault-output-disabled-default` — Disable output
- `Label` `(no id)` — Vault key:
- `CommandInput` `vault-output-key-default` — 
- `Label` `(no id)` — Description:
- `CommandInput` `vault-output-desc-default` — Model response text (or forwarded payload on dead-drop)
- `Label` `form-section-use_chat_session` — AI Session
- `Checkbox` `field-use_chat_session` — Keep active AI session
- `Label` `field-desc-use_chat_session` — When continuing a session, extends that same session — no new key needed
- Hidden: `Label` `field-label-session_key` — Session key:
- Hidden: `CommandInput` `field-session_key` — 

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_c433a612).default -> prompt /   outputs: /     default -> No-Op (node_303b8104).input

Conditional variants: dead-drop-passthrough, field-api_key_secret, field-context_1_source, field-context_1_vault_key, field-context_2_source, field-context_2_vault_key, field-context_3_source, field-context_3_vault_key, field-context_4_source, field-context_4_vault_key, field-context_5_source, field-context_5_vault_key, field-context_6_source, field-context_6_vault_key, field-context_7_source, field-context_7_vault_key, field-context_8_source, field-context_8_vault_key, field-context_input_count, field-continue_session_key, field-document_source, field-document_vault_key, field-model, field-prompt_source, field-prompt_vault_key, field-use_chat_session, vault-output-disabled-default.

### concat_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Concat
- `Static` `node-config-summary` — Node type: Concat / Formats input and variables into text
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-template` — Template *:
- `CommandTextArea` `field-template` — {input}

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_76c922cb).default -> input /   outputs: /     default -> No-Op (node_16f025a0).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### conditional_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Conditional
- `Static` `node-config-summary` — Node type: Conditional / Routes to one path based on a condition
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-condition_type` — Condition type *:
- `Select` `field-condition_type` — contains
- `Label` `field-label-left_value_source` — Left value source *:
- `Select` `field-left_value_source` — input
- `Label` `field-label-variable_name` — Variable name:
- `CommandInput` `field-variable_name` — 
- `Label` `field-label-right_value` — Right value *:
- `CommandInput` `field-right_value` — 
- `Label` `field-label-true_label` — true branch name:
- `CommandInput` `field-true_label` — 
- `Label` `field-desc-true_label` — Editor display name for true
- `Label` `field-label-false_label` — false branch name:
- `CommandInput` `field-false_label` — 
- `Label` `field-desc-false_label` — Editor display name for false

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — True
- `CommandInput` `transient-output-name-true` — True
- `CommandInput` `transient-output-desc-true` — 
- `Label` `(no id)` — False
- `CommandInput` `transient-output-name-false` — False
- `CommandInput` `transient-output-desc-false` — 

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_59800396).default -> input /   outputs: /     true -> No-Op (node_11bb2fa5).input

Conditional variants: field-condition_type, field-left_value_source, membank-reads, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### counter_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Counter
- `Static` `node-config-summary` — Node type: Counter / Increments a persistent counter each time it is visited
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-counter_name` — Counter Name *:
- `CommandInput` `field-counter_name` — counter

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_4647ba4b).default -> input /   outputs: /     default -> No-Op (node_a5b6ba1d).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### deep_branch_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Deep Branch
- `Static` `node-config-summary` — Node type: Deep Branch / Spawns a child branch to test max-depth enforcement
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-default_label` — default branch name:
- `CommandInput` `field-default_label` — 
- `Label` `field-desc-default_label` — Editor display name for default
- `Label` `field-label-branch_label` — branch branch name:
- `CommandInput` `field-branch_label` — 
- `Label` `field-desc-branch_label` — Editor display name for branch

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Branch
- `CommandInput` `transient-output-name-branch` — Branch
- `CommandInput` `transient-output-desc-branch` — 

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_f0b0eb02).default -> input /   outputs: /     default -> No-Op (node_a8dd00fd).input

Conditional variants: membank-reads, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### echo_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Echo
- `Static` `node-config-summary` — Node type: Echo / Passes input through unchanged
- `Static` `(no id)` — Dead drop payload: forwards the upstream payload unchanged.
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-label` — Label:
- `CommandInput` `field-label` — 

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_7b5d8572).default -> input /   outputs: /     default -> No-Op (node_bbedac13).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### embedding_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Embedding
- `Static` `node-config-summary` — Node type: Embedding / Simulates creating an embedding vector
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-model` — Model *:
- `Select` `field-model` — text-embedding-3-small
- `Label` `field-label-text_field` — Text field *:
- `CommandInput` `field-text_field` — input
- `Label` `field-label-api_key_secret` — API key (secrets store key):
- `Select` `field-api_key_secret` — Select.NULL

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_fb60dbd1).default -> input /   outputs: /     default -> No-Op (node_265efbca).input

Conditional variants: field-api_key_secret, field-model, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### end_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — End
- `Static` `node-config-summary` — Node type: End / Terminates a workflow branch
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-message` — Message *:
- `CommandInput` `field-message` — Branch completed
- `Label` `field-desc-message` — Completion message recorded in the output log

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Static` `(no id)` — No dead drop payloads.
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_b0a35fff).default -> input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### error_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Error Trigger
- `Static` `node-config-summary` — Node type: Error Trigger / Signals a workflow error on demand
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-message` — Error Message *:
- `CommandInput` `field-message` — Deliberate error from ErrorNode
- `Label` `field-label-error_mode` — Error Mode *:
- `Select` `field-error_mode` — fail

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_e3d38b19).default -> input /   outputs: /     default -> No-Op (node_a5e03fe5).input

Conditional variants: field-error_mode, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### file_reader_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — File Reader
- `Static` `node-config-summary` — Node type: File Reader / Reads text from a local file
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-file_path` — File path *:
- `CommandInput` `field-file_path` — 

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_63be120e).default -> input /   outputs: /     default -> No-Op (node_95108cd2).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### file_view_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — View File
- `Static` `node-config-summary` — Node type: File Viewer / Display a text or Markdown file inside AOTN
- `Label` `(no id)` — Incoming Payload
- `Static` `incoming-payload-file` — Node source: User Text Input node / Payload: audit_text (any)
- `Label` `form-section-file_source` — Required Inputs
- `Label` `field-label-file_source` — File source:
- `Select` `field-file_source` — Upstream payload
- `Label` `field-desc-file_source` — File reference from upstream/vault, or a configured path
- Hidden: `Label` `field-label-file_vault_key` — File Vault key:
- Hidden: `Select` `field-file_vault_key` — Select.NULL

**2 - Parameters**

- Hidden: `Label` `field-label-file` — File path *:
- Hidden: `CommandInput` `field-file` — 
- `Label` `field-label-render` — Render as:
- `Select` `field-render` — Auto
- `Label` `field-desc-render` — Auto picks Markdown for .md/.markdown files

**3 - Payloads**

- `Label` `(no id)` — Downstream node payload
- `Static` `downstream-header-default` — File Reference  [file]
- `Label` `(no id)` — Payload name:
- `CommandInput` `transient-output-name-default` — File Reference
- `Label` `(no id)` — Description:
- `CommandInput` `transient-output-desc-default` — The viewed file's reference, forwarded for further steps
- `Checkbox` `dead-drop-passthrough` — Forward incoming payload unchanged
- `Label` `form-section-terminate_branch` — Branch
- `Checkbox` `field-terminate_branch` — Terminate branch after completion
- `Label` `field-desc-terminate_branch` — End this branch after the viewer is requested

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_0b5e51dc).default -> file /   outputs: /     default -> No-Op (node_0f409894).input

Conditional variants: dead-drop-passthrough, field-file_source, field-file_vault_key, field-render, field-terminate_branch.

### file_output_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — File Write
- `Static` `node-config-summary` — Node type: File Write / Write content to a file and emit a typed file reference
- `Label` `(no id)` — Incoming Payload
- `Static` `incoming-payload-content` — Node source: User Text Input node / Payload: audit_text (any)
- `Label` `form-section-content_source` — Required Inputs
- `Label` `field-label-content_source` — Content source:
- `Select` `field-content_source` — Upstream payload
- `Label` `field-desc-content_source` — Data written to the file
- Hidden: `Label` `field-label-content_vault_key` — Content Vault key:
- Hidden: `Select` `field-content_vault_key` — Select.NULL
- `Label` `field-label-file_path_source` — File path source:
- `Select` `field-file_path_source` — Configured
- `Label` `field-desc-file_path_source` — Destination path, or a file reference from upstream/vault
- Hidden: `Label` `field-label-file_path_vault_key` — File path Vault key:
- Hidden: `Select` `field-file_path_vault_key` — Select.NULL

**2 - Parameters**

- Hidden: `Label` `field-label-content` — Content (E to edit, ESC to finish):
- Hidden: `CommandTextArea` `field-content` — 
- `Label` `field-label-file_path` — File path *:
- `CommandInput` `field-file_path` — 
- `Label` `field-label-write_mode` — Write mode:
- `Select` `field-write_mode` — Overwrite
- `Label` `field-desc-write_mode` — Create unique adds a numeric suffix instead of replacing
- `Checkbox` `field-binary_content` — Binary content (Base64)
- `Label` `field-desc-binary_content` — Decode the content as Base64 and write raw bytes
- `Label` `form-section-open_after_write` — OS Window
- `Checkbox` `field-open_after_write` — Open after write
- `Label` `field-desc-open_after_write` — Open the file in its OS-default app (a loop opens the file each iteration)
- Hidden: `Label` `field-label-window_placement` — Open at:
- Hidden: `Select` `field-window_placement` — OS default
- Hidden: `Label` `field-desc-window_placement` — Screen placement preset for the opened window
- Hidden: `Checkbox` `field-close_on_run_end` — Close when run ends
- Hidden: `Label` `field-desc-close_on_run_end` — Off keeps the window open for reading after the run

**3 - Payloads**

- `Label` `(no id)` — Downstream node payload
- `Static` `downstream-header-default` — File Reference  [file]
- `Label` `(no id)` — Payload name:
- `CommandInput` `transient-output-name-default` — File Reference
- `Label` `(no id)` — Description:
- `CommandInput` `transient-output-desc-default` — Typed reference to the written file
- `Checkbox` `dead-drop-passthrough` — Forward incoming payload unchanged
- `Label` `(no id)` — Vault Payload
- `Static` `vault-header-default` — File Reference  [file]
- `Checkbox` `vault-output-disabled-default` — Disable output
- `Label` `(no id)` — Vault key:
- `CommandInput` `vault-output-key-default` — 
- `Label` `(no id)` — Description:
- `CommandInput` `vault-output-desc-default` — Typed reference to the written file
- `Label` `form-section-terminate_branch` — Branch
- `Checkbox` `field-terminate_branch` — Terminate branch after completion
- `Label` `field-desc-terminate_branch` — End this branch after the file is written

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_0ef1e4c7).default -> content /   outputs: /     default -> No-Op (node_36b71fc5).input

Conditional variants: dead-drop-passthrough, field-binary_content, field-close_on_run_end, field-content_source, field-content_vault_key, field-file_path_source, field-file_path_vault_key, field-open_after_write, field-terminate_branch, field-window_placement, field-write_mode, vault-output-disabled-default.

### get_variable_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Get Variable
- `Static` `node-config-summary` — Node type: Get Variable / Reads a value from persistent memory
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-variable_name` — Variable name *:
- `CommandInput` `field-variable_name` — value
- `Label` `field-label-default` — Default:
- `CommandInput` `field-default` — 

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_2864f580).default -> input /   outputs: /     default -> No-Op (node_c755bf9e).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### http_request_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — HTTP Request
- `Static` `node-config-summary` — Node type: HTTP Request / Make an HTTP GET or POST request and forward the response body
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-url` — URL *:
- `CommandInput` `field-url` — 
- `Label` `field-label-method` — Method:
- `Select` `field-method` — GET
- `Label` `field-label-body` — Request body (POST):
- `CommandTextArea` `field-body` — 
- `Label` `field-label-timeout_seconds` — Timeout (seconds):
- `CommandInput` `field-timeout_seconds` — 10.0
- `Label` `field-label-auth_token_secret` — Bearer token (secrets store key):
- `Select` `field-auth_token_secret` — Select.NULL
- `Label` `field-label-default_label` — default branch name:
- `CommandInput` `field-default_label` — 
- `Label` `field-desc-default_label` — Editor display name for default
- `Label` `field-label-error_label` — error branch name:
- `CommandInput` `field-error_label` — 
- `Label` `field-desc-error_label` — Editor display name for error

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Error
- `CommandInput` `transient-output-name-error` — Error
- `CommandInput` `transient-output-desc-error` — 

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_90708ae1).default -> input /   outputs: /     default -> No-Op (node_3da2e04f).input

Conditional variants: field-auth_token_secret, field-method, membank-reads, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### image_generation_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Image Generation
- `Static` `node-config-summary` — Node type: Image Generation / Simulates an image generation request
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-prompt` — Prompt *:
- `CommandTextArea` `field-prompt` — An image of {input}
- `Label` `field-label-size` — Size *:
- `Select` `field-size` — 1024x1024
- `Label` `field-label-style` — Style *:
- `Select` `field-style` — natural
- `Label` `field-label-api_key_secret` — API key (secrets store key):
- `Select` `field-api_key_secret` — Select.NULL

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_e8387433).default -> input /   outputs: /     default -> No-Op (node_2b95b0e7).input

Conditional variants: field-api_key_secret, field-size, field-style, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### json_path_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — JSON Path
- `Static` `node-config-summary` — Node type: JSON Path / Extract a value from a JSON string by dot-path (e.g. "user.name")
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-path` — Dot path *:
- `CommandInput` `field-path` — 
- `Label` `field-label-default_value` — Default on miss:
- `CommandInput` `field-default_value` — 
- `Label` `field-label-default_label` — default branch name:
- `CommandInput` `field-default_label` — 
- `Label` `field-desc-default_label` — Editor display name for default
- `Label` `field-label-error_label` — error branch name:
- `CommandInput` `field-error_label` — 
- `Label` `field-desc-error_label` — Editor display name for error

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Error
- `CommandInput` `transient-output-name-error` — Error
- `CommandInput` `transient-output-desc-error` — 

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_99690ec5).default -> input /   outputs: /     default -> No-Op (node_7c779656).input

Conditional variants: membank-reads, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### logger_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Logger
- `Static` `node-config-summary` — Node type: Logger / Logs the input value and passes it through
- `Static` `(no id)` — Dead drop payload: forwards the upstream payload unchanged.
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-label` — Label:
- `CommandInput` `field-label` — 
- `Checkbox` `field-include_input` — Include Input
- `Checkbox` `field-include_timestamp` — Include Timestamp

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_c62ab733).default -> input /   outputs: /     default -> No-Op (node_73d81cb4).input

Conditional variants: field-include_input, field-include_timestamp, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### memory_snapshot_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Memory Snapshot
- `Static` `node-config-summary` — Node type: Memory Snapshot / Dumps the persistent memory bank to the output log
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-label` — Label:
- `CommandInput` `field-label` — 

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_b423cbf0).default -> input /   outputs: /     default -> No-Op (node_da7c7399).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### merge_node

**flat**

- `Label` `(no id)` — Edit Node: Merge (node_6054a48b)
- `Static` `(no id)` — number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `Label` `(no id)` — Branches To Close
- `Static` `(no id)` — No open branches are available to close.
- `Button` `save-node-config` — Save
- `Button` `cancel-node-config` — Cancel
- `StatusBar` `(no id)` — [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### branch_end_node

**flat**

- `Label` `(no id)` — Edit Node: Merge Beacon (node_2ef3a7ba)
- `Static` `(no id)` — number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `Static` `(no id)` — Merge Beacon has no editable fields. / Status: open until connected to a Merge node.
- `Button` `save-node-config` — Save
- `Button` `cancel-node-config` — Cancel
- `StatusBar` `(no id)` — [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### no_op_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — No-Op
- `Static` `node-config-summary` — Node type: No-Op / Does nothing and passes execution through
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Static` `(no id)` — No parameters.

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_5a5360a6).default -> input /   outputs: /     default -> No-Op (node_9ef6f423).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### branch_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Parallel Branch
- `Static` `node-config-summary` — Node type: Parallel Branch / - Duplicates the incoming payload across branch paths. / - Parallel paths run independently / - Conditional branching hidden for a later node pass
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `(no id)` — Branches
- `CommandInput` `branch-count` — 2
- `Static` `(no id)` — Choose 2 to 5 spawn points.

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Spawn Point:
- `CommandInput` `branch-label-path_a` — Branch 1
- `Label` `(no id)` — Start with:
- `Select` `branch-payload-source-path_a` — dead_drop:input
- `Label` `(no id)` — Spawn Point:
- `CommandInput` `branch-label-path_b` — Branch 2
- `Label` `(no id)` — Start with:
- `Select` `branch-payload-source-path_b` — dead_drop:input
- Hidden: `Label` `(no id)` — Spawn Point:
- Hidden: `CommandInput` `branch-label-path_c` — Branch 3
- Hidden: `Label` `(no id)` — Start with:
- Hidden: `Select` `branch-payload-source-path_c` — dead_drop:input
- Hidden: `Label` `(no id)` — Spawn Point:
- Hidden: `CommandInput` `branch-label-path_d` — Branch 4
- Hidden: `Label` `(no id)` — Start with:
- Hidden: `Select` `branch-payload-source-path_d` — dead_drop:input
- Hidden: `Label` `(no id)` — Spawn Point:
- Hidden: `CommandInput` `branch-label-path_e` — Branch 5
- Hidden: `Label` `(no id)` — Start with:
- Hidden: `Select` `branch-payload-source-path_e` — dead_drop:input

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_9e205f7e).default -> input /   outputs: /     path_a -> No-Op (node_afc3d5af).input

Conditional variants: branch-count, membank-reads, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### probe_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Probe
- `Static` `node-config-summary` — Node type: Probe / Inspects and logs the incoming value with type info
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-label` — Label:
- `CommandInput` `field-label` — 

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_9e0d8622).default -> input /   outputs: /     default -> No-Op (node_4d9d28fa).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### random_branch_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Random Branch
- `Static` `node-config-summary` — Node type: Random Branch / Routes to path_a or path_b at random
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-seed` — Random Seed (empty = random):
- `CommandInput` `field-seed` — 
- `Label` `field-label-path_a_label` — path_a branch name:
- `CommandInput` `field-path_a_label` — 
- `Label` `field-desc-path_a_label` — Editor display name for path_a
- `Label` `field-label-path_b_label` — path_b branch name:
- `CommandInput` `field-path_b_label` — 
- `Label` `field-desc-path_b_label` — Editor display name for path_b

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Path A
- `CommandInput` `transient-output-name-path_a` — Path A
- `CommandInput` `transient-output-desc-path_a` — 
- `Label` `(no id)` — Path B
- `CommandInput` `transient-output-name-path_b` — Path B
- `CommandInput` `transient-output-desc-path_b` — 

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_e903b4d4).default -> input /   outputs: /     path_a -> No-Op (node_2b719ba4).input

Conditional variants: membank-reads, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### random_number_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Random Number
- `Static` `node-config-summary` — Node type: Random Number / Produce a random integer or float within a configured range
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-mode` — Mode:
- `Select` `field-mode` — integer
- `Label` `field-label-min_value` — Minimum value:
- `CommandInput` `field-min_value` — 0
- `Label` `field-label-max_value` — Maximum value:
- `CommandInput` `field-max_value` — 100
- `Label` `field-label-seed` — Random seed (blank = unseeded):
- `CommandInput` `field-seed` — 
- `Label` `field-label-value` — Payload:
- `CommandInput` `field-value` — 

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_66b74202).default -> input /   outputs: /     default -> No-Op (node_00b623b3).input

Conditional variants: field-mode, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### repeat_counter_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Repeat Counter
- `Static` `node-config-summary` — Node type: Repeat Counter / Signals an error when visited more than max_visits times
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-max_visits` — Max Visits *:
- `CommandInput` `field-max_visits` — 3

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_40bb4705).default -> input /   outputs: /     default -> No-Op (node_f5e12326).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### set_variable_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Set Variable
- `Static` `node-config-summary` — Node type: Set Variable / Stores a value in persistent memory
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-variable_name` — Variable name *:
- `CommandInput` `field-variable_name` — value
- `Label` `field-label-value_source` — Value source *:
- `Select` `field-value_source` — input
- `Label` `field-label-value` — Value:
- `CommandInput` `field-value` — 
- `Checkbox` `field-pass_through` — Dead drop payload
- `Label` `field-desc-pass_through` — Forward the upstream payload after writing to memory

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_96f364c6).default -> input /   outputs: /     default -> No-Op (node_43ee7bf7).input

Conditional variants: field-pass_through, field-value_source, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### sleep_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Sleep
- `Static` `node-config-summary` — Node type: Sleep / Pauses execution for a fixed duration
- `Static` `(no id)` — Dead drop payload: Pauses, then forwards the previous node output unchanged.
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-duration` — Duration (seconds) *:
- `CommandInput` `field-duration` — 0.1

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_bcf06035).default -> input /   outputs: /     default -> No-Op (node_50d9598f).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### start_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Start
- `Static` `node-config-summary` — Node type: Start / Entry point for workflow execution
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-greeting` — Greeting *:
- `CommandInput` `field-greeting` — Workflow started
- `Label` `field-desc-greeting` — Message to emit when the workflow begins

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   outputs: /     default -> No-Op (node_1cb3b2c3).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### text_output_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Text Output
- `Static` `node-config-summary` — Node type: Text Output / Formats input through a template and logs it
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-label` — Label *:
- `CommandInput` `field-label` — Output
- `Label` `field-desc-label` — Label shown alongside the output
- `Label` `field-label-template` — Template *:
- `CommandInput` `field-template` — {input}
- `Label` `field-desc-template` — Output text. Use {input} to insert the incoming value.
- `Checkbox` `field-request_user_input` — Request user input
- `Label` `field-desc-request_user_input` — Pause and prompt the user before producing output
- `Label` `field-label-prompt` — Prompt:
- `CommandInput` `field-prompt` — Enter a value:
- `Label` `field-desc-prompt` — Prompt text shown when requesting user input

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_2ba33de4).default -> input /   outputs: /     default -> No-Op (node_eafe0df6).input

Conditional variants: field-request_user_input, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### text_transform_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Text Transform
- `Static` `node-config-summary` — Node type: Text Transform / Apply a text transformation (case, strip, reverse, markdown format) to the input string
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-operation` — Operation:
- `Select` `field-operation` — uppercase
- Hidden: `Label` `field-label-wrap_width` — Wrap width:
- Hidden: `CommandInput` `field-wrap_width` — 0
- Hidden: `Label` `field-desc-wrap_width` — Re-flow paragraphs to this width; 0 keeps existing line breaks

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_f994d280).default -> input /   outputs: /     default -> No-Op (node_dd51ee9b).input

Conditional variants: field-operation, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### user_text_input_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — User Text Input
- `Static` `node-config-summary` — Node type: User Text Input / Prompts the user for text during execution
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-prompt` — Prompt *:
- `CommandInput` `field-prompt` — Enter text:

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_b7f0cbc9).default -> input /   outputs: /     default -> No-Op (node_e86d97a8).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### variable_reader_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Variable Reader
- `Static` `node-config-summary` — Node type: Variable Reader / Reads a named variable from persistent memory
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-variable_name` — Variable Name *:
- `CommandInput` `field-variable_name` — 
- `Label` `field-label-default` — Default Value:
- `CommandInput` `field-default` — 

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_5896b77c).default -> input /   outputs: /     default -> No-Op (node_f88688a8).input

Conditional variants: membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### variable_setter_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Variable Setter
- `Static` `node-config-summary` — Node type: Variable Setter / Stores a named variable in persistent memory
- `Label` `(no id)` — Upstream Payload
- `Checkbox` `show-previous-output` — Reveal upstream payload
- Hidden: `PayloadPreview` `previous-output-preview` — 
- `Checkbox` `membank-reads` — Vault
- `SelectionList` `membank-inputs` — 
- `Checkbox` `show-source-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `source-vault-payload-preview` — 

**2 - Parameters**

- `Label` `field-label-variable_name` — Variable Name *:
- `CommandInput` `field-variable_name` — 
- `Label` `field-label-value` — Value (empty = use input):
- `CommandInput` `field-value` — 
- `Checkbox` `field-pass_through` — Dead drop payload

**3 - Payloads**

- `Label` `(no id)` — Incoming Payloads
- `Checkbox` `show-payload-upstream-payload` — Reveal upstream payload
- Hidden: `PayloadPreview` `payload-upstream-payload-preview` — 
- `Checkbox` `show-payload-vault-payload` — Reveal Vault payload
- Hidden: `PayloadPreview` `payload-vault-payload-preview` — 
- `Label` `(no id)` — Dead Drop Payloads
- `Label` `(no id)` — Default
- `CommandInput` `transient-output-name-default` — Output
- `CommandInput` `transient-output-desc-default` — 
- `Label` `(no id)` — Vault Payloads
- `Checkbox` `membank-writes` — Write to Vault
- `Label` `(no id)` — Payload count
- `CommandInput` `membank-output-count` — 0

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_fb727593).default -> input /   outputs: /     default -> No-Op (node_520e931f).input

Conditional variants: field-pass_through, membank-output-count, membank-reads, membank-writes, show-payload-upstream-payload, show-payload-vault-payload, show-previous-output, show-source-vault-payload.

### wait_until_node

**1 - Wait**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Wait Until
- `Static` `(no id)` — Wait for all selected nodes to complete, then forward the incoming dead-drop payload unchanged. The next node can read the Vault.
- `Label` `(no id)` — Wait for these nodes
- `SelectionList` `wait-targets` — 
- `Static` `wait-target-summary` — No targets selected: this node will continue immediately.
- `Static` `(no id)` — Targets must complete at least once in this run. A target that never executes can wait forever at zero timeout.
- `Label` `field-label-timeout_seconds` — Timeout seconds:
- `CommandInput` `field-timeout_seconds` — 0.0
- `Label` `field-desc-timeout_seconds` — 0 waits forever (default); a positive value limits the wait
- `Static` `wait-config-error` — 
- `Static` `(no id)` — Incoming: User Text Input.default / Forward unchanged / Next: No-Op.input

**2 - Connections**

- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_ceb1c0de).default -> input /   outputs: /     default -> No-Op (node_a6cf5314).input

### window_control_node

**1 - Source**

- `Label` `(no id)` — Alias:
- `CommandInput` `alias-input` — Window Control
- `Static` `node-config-summary` — Node type: Window Control / Focus, minimize, or close the window showing a workflow file
- `Label` `(no id)` — Incoming Payload
- `Static` `incoming-payload-file` — Node source: User Text Input node / Payload: audit_text (any)
- `Label` `form-section-file_source` — Required Inputs
- `Label` `field-label-file_source` — File source:
- `Select` `field-file_source` — Upstream payload
- `Label` `field-desc-file_source` — File reference whose window to control
- Hidden: `Label` `field-label-file_vault_key` — File Vault key:
- Hidden: `Select` `field-file_vault_key` — Select.NULL

**2 - Parameters**

- `Label` `field-label-action` — Action:
- `Select` `field-action` — Focus
- `Label` `field-desc-action` — What to do with the file's window

**3 - Payloads**

- `Label` `(no id)` — Downstream node payload
- `Static` `downstream-header-default` — File Reference  [file]
- `Label` `(no id)` — Payload name:
- `CommandInput` `transient-output-name-default` — File Reference
- `Label` `(no id)` — Description:
- `CommandInput` `transient-output-desc-default` — The targeted file's reference, forwarded unchanged

**4 - Connections**

- `Label` `(no id)` — Connections
- `Static` `(no id)` — Edit connections from the editor.
- `Static` `connection-summary` —   inputs: /     User Text Input (node_1a96b6d5).default -> file /   outputs: /     default -> No-Op (node_ebcda020).input

Conditional variants: field-action, field-file_source, field-file_vault_key.


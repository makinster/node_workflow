# Mounted configuration control inventory

Generated from production-CSS mounts. Read with [the audit](../../NODE_CONFIG_UI_AUDIT.md).
Each default table inventories the 100-column composition, including hidden controls,
static labels, previews and buttons. Three-width regions, keyboard traces, full schemas,
defaults, ports and all alternate-state snapshots are in `evidence.json.gz`.
Alternate rows below show changed control state, not an assertion that execution supports it.
Tab visibility is separate from a field’s own conditional display state. Blank IDs denote
informational widgets. No secret values or owner workflow data were captured.

## Chat Completion — `chat_completion_node`

Source: `backend/nodes/chat_completion_node.py`. Helper spec: `aotn_node_helper/specs/chat_completion_node.yaml`.

Selector family/group: **Complex / AI Processing**.
Ports: `["prompt", "context_1", "context_2", "context_3", "context_4", "context_5", "context_6", "context_7", "context_8", "document"]` → `["default"]`.

Defaults:

```json
{
  "prompt_source": "Configured",
  "prompt_vault_key": "",
  "prompt": "",
  "context_input_count": "0",
  "context_1_source": "Configured",
  "context_1_vault_key": "",
  "context_1": "",
  "context_2_source": "Configured",
  "context_2_vault_key": "",
  "context_2": "",
  "context_3_source": "Configured",
  "context_3_vault_key": "",
  "context_3": "",
  "context_4_source": "Configured",
  "context_4_vault_key": "",
  "context_4": "",
  "context_5_source": "Configured",
  "context_5_vault_key": "",
  "context_5": "",
  "context_6_source": "Configured",
  "context_6_vault_key": "",
  "context_6": "",
  "context_7_source": "Configured",
  "context_7_vault_key": "",
  "context_7": "",
  "context_8_source": "Configured",
  "context_8_vault_key": "",
  "context_8": "",
  "document_source": "Configured",
  "document_vault_key": "",
  "document": "",
  "continue_session_key": "",
  "model": "claude-opus-4-8",
  "max_tokens": 1024,
  "temperature": 1.0,
  "api_key_secret": "",
  "use_chat_session": false,
  "session_key": "",
  "transient_output": true,
  "dead_drop_passthrough": false,
  "vault_write": true,
  "vault_write_key": "",
  "vault_write_description": "",
  "transient_outputs": []
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Chat Completion | True / False |
| node-config-summary | Static | Node type: Chat Completion<br>Send a prompt to an LLM and receive a text response |  | True / False |
| — | Label | Incoming Payload |  | True / False |
| incoming-payload-prompt | Static | Node source: User Text Input node<br>Payload: audit_text (any) |  | True / False |
| form-section-prompt_source | Label | Required Inputs |  | True / False |
| field-label-prompt_source | Label | Prompt source: |  | True / False |
| field-desc-prompt_source | Label | Where the prompt comes from at execution time |  | True / False |
| field-prompt_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"], ["Continue AI session", "Continue AI session"]] | Configured | True / False |
| field-label-prompt_vault_key | Label | Prompt Vault key: |  | False / False |
| field-prompt_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-continue_session_key | Label | Session: |  | False / False |
| field-desc-continue_session_key | Label | Declared AI session whose chat this node resumes |  | False / False |
| field-continue_session_key | Select |  Options: [["", "Select.NULL"], ["audit_session [ai_session]", "audit_session"]] | Select.NULL | False / False |
| form-section-context_input_count | Label | Additional Context |  | True / False |
| field-label-context_input_count | Label | Context inputs: |  | True / False |
| field-desc-context_input_count | Label | Additional inputs appended in order before Document |  | True / False |
| field-context_input_count | Select |  Options: [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]] | 0 | True / False |
| field-label-context_1_source | Label | Context 1 source: |  | False / False |
| field-desc-context_1_source | Label | Additional context appended in configured order |  | False / False |
| field-context_1_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_1_vault_key | Label | Context 1 Vault key: |  | False / False |
| field-context_1_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-context_2_source | Label | Context 2 source: |  | False / False |
| field-desc-context_2_source | Label | Additional context appended in configured order |  | False / False |
| field-context_2_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_2_vault_key | Label | Context 2 Vault key: |  | False / False |
| field-context_2_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-context_3_source | Label | Context 3 source: |  | False / False |
| field-desc-context_3_source | Label | Additional context appended in configured order |  | False / False |
| field-context_3_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_3_vault_key | Label | Context 3 Vault key: |  | False / False |
| field-context_3_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-context_4_source | Label | Context 4 source: |  | False / False |
| field-desc-context_4_source | Label | Additional context appended in configured order |  | False / False |
| field-context_4_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_4_vault_key | Label | Context 4 Vault key: |  | False / False |
| field-context_4_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-context_5_source | Label | Context 5 source: |  | False / False |
| field-desc-context_5_source | Label | Additional context appended in configured order |  | False / False |
| field-context_5_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_5_vault_key | Label | Context 5 Vault key: |  | False / False |
| field-context_5_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-context_6_source | Label | Context 6 source: |  | False / False |
| field-desc-context_6_source | Label | Additional context appended in configured order |  | False / False |
| field-context_6_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_6_vault_key | Label | Context 6 Vault key: |  | False / False |
| field-context_6_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-context_7_source | Label | Context 7 source: |  | False / False |
| field-desc-context_7_source | Label | Additional context appended in configured order |  | False / False |
| field-context_7_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_7_vault_key | Label | Context 7 Vault key: |  | False / False |
| field-context_7_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| field-label-context_8_source | Label | Context 8 source: |  | False / False |
| field-desc-context_8_source | Label | Additional context appended in configured order |  | False / False |
| field-context_8_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | False / False |
| field-label-context_8_vault_key | Label | Context 8 Vault key: |  | False / False |
| field-context_8_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |
| form-section-document_source | Label | Optional Inputs |  | True / False |
| field-label-document_source | Label | Document / context source: |  | True / False |
| field-desc-document_source | Label | Optional document appended to the prompt |  | True / False |
| field-document_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | True / False |
| field-label-document_vault_key | Label | Document Vault key: |  | False / False |
| field-document_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]] | Select.NULL | False / False |

Navigation candidates: `["alias-input", "field-prompt_source", "field-context_input_count", "field-document_source", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-context_1 | Label | Context 1 (E to edit, ESC to finish): |  | False / False |
| field-context_1 | CommandTextArea |  |  | False / False |
| field-label-context_2 | Label | Context 2 (E to edit, ESC to finish): |  | False / False |
| field-context_2 | CommandTextArea |  |  | False / False |
| field-label-context_3 | Label | Context 3 (E to edit, ESC to finish): |  | False / False |
| field-context_3 | CommandTextArea |  |  | False / False |
| field-label-context_4 | Label | Context 4 (E to edit, ESC to finish): |  | False / False |
| field-context_4 | CommandTextArea |  |  | False / False |
| field-label-context_5 | Label | Context 5 (E to edit, ESC to finish): |  | False / False |
| field-context_5 | CommandTextArea |  |  | False / False |
| field-label-context_6 | Label | Context 6 (E to edit, ESC to finish): |  | False / False |
| field-context_6 | CommandTextArea |  |  | False / False |
| field-label-context_7 | Label | Context 7 (E to edit, ESC to finish): |  | False / False |
| field-context_7 | CommandTextArea |  |  | False / False |
| field-label-context_8 | Label | Context 8 (E to edit, ESC to finish): |  | False / False |
| field-context_8 | CommandTextArea |  |  | False / False |
| field-label-prompt | Label | Prompt (E to edit, ESC to finish): |  | True / False |
| field-prompt | CommandTextArea |  |  | True / False |
| field-label-document | Label | Document (E to edit, ESC to finish): |  | True / False |
| field-document | CommandTextArea |  |  | True / False |
| field-label-model | Label | Model *: |  | True / False |
| field-model | Select |  Options: [["claude-opus-4-8", "claude-opus-4-8"], ["claude-sonnet-5", "claude-sonnet-5"], ["claude-sonnet-4-6", "claude-sonnet-4-6"], ["claude-haiku-4-5", "claude-haiku-4-5"]] | claude-opus-4-8 | True / False |
| field-label-max_tokens | Label | Max tokens *: |  | True / False |
| field-max_tokens | CommandInput |  | 1024 | True / False |
| field-label-temperature | Label | Temperature *: |  | True / False |
| field-desc-temperature | Label | Ignored by models that do not accept sampling parameters |  | True / False |
| field-temperature | CommandInput |  | 1.0 | True / False |
| field-label-api_key_secret | Label | API key (secrets store key) *: |  | True / False |
| field-api_key_secret | Select |  Options: [["", "Select.NULL"], ["audit_api", "audit_api"]] | Select.NULL | True / False |

Navigation candidates: `["field-prompt", "field-document", "field-model", "field-max_tokens", "field-temperature", "field-api_key_secret", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Downstream node payload |  | True / False |
| downstream-header-default | Static | LLM Result  [string] |  | True / False |
| — | Label | Payload name: |  | True / False |
| transient-output-name-default | CommandInput |  | LLM Result | True / False |
| — | Label | Description: |  | True / False |
| transient-output-desc-default | CommandInput |  | Model response text (or forwarded payload on dead-drop) | True / False |
| dead-drop-passthrough | Checkbox | Forward incoming payload unchanged | False | True / False |
| — | Label | Vault Payload |  | True / False |
| vault-header-default | Static | LLM Result  [string] |  | True / False |
| vault-output-disabled-default | Checkbox | Disable output | False | True / False |
| — | Label | Vault key: |  | True / False |
| vault-output-key-default | CommandInput |  |  | True / False |
| — | Label | Description: |  | True / False |
| vault-output-desc-default | CommandInput |  | Model response text (or forwarded payload on dead-drop) | True / False |
| form-section-use_chat_session | Label | AI Session |  | True / False |
| field-use_chat_session | Checkbox | Keep active AI session | False | True / False |
| field-desc-use_chat_session | Label | When continuing a session, extends that same session — no new key needed |  | True / False |
| field-label-session_key | Label | Session key: |  | False / False |
| field-session_key | CommandInput |  |  | False / False |

Navigation candidates: `["transient-output-name-default", "transient-output-desc-default", "dead-drop-passthrough", "vault-output-disabled-default", "vault-output-key-default", "vault-output-desc-default", "field-use_chat_session", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_7ac2cb46).default -> prompt<br>  outputs:<br>    default -> No-Op (node_6a312d41).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Chat Completion (node_6a0c2320)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `field-prompt_source` → `Upstream payload` (actual `Upstream payload`): {"field-prompt_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"], ["Continue AI session", "Continue AI session"]], "display": true, "disabled": false}, "field-label-prompt": {"class": "Label", "text": "Prompt (E to edit, ESC to finish):", "display": false, "disabled": false}, "field-prompt": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `field-prompt_source` → `Vault` (actual `Vault`): {"field-prompt_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"], ["Continue AI session", "Continue AI session"]], "display": true, "disabled": false}, "field-label-prompt_vault_key": {"class": "Label", "text": "Prompt Vault key:", "display": true, "disabled": false}, "field-prompt_vault_key": {"class": "Select", "value": "Select.NULL", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": true, "disabled": false}, "field-label-prompt": {"class": "Label", "text": "Prompt (E to edit, ESC to finish):", "display": false, "disabled": false}, "field-prompt": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `field-prompt_source` → `Continue AI session` (actual `Continue AI session`): {"field-prompt_source": {"class": "Select", "value": "Continue AI session", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"], ["Continue AI session", "Continue AI session"]], "display": true, "disabled": false}, "field-label-continue_session_key": {"class": "Label", "text": "Session:", "display": true, "disabled": false}, "field-desc-continue_session_key": {"class": "Label", "text": "Declared AI session whose chat this node resumes", "display": true, "disabled": false}, "field-continue_session_key": {"class": "Select", "value": "Select.NULL", "options": [["", "Select.NULL"], ["audit_session [ai_session]", "audit_session"]], "display": true, "disabled": false}, "form-section-document_source": {"class": "Label", "text": "Required Inputs", "display": true, "disabled": false}, "field-label-document_source": {"class": "Label", "text": "Document / context source *:", "display": true, "disabled": false}, "field-label-prompt": {"class": "Label", "text": "Prompt (E to edit, ESC to finish):", "display": false, "disabled": false}, "field-prompt": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}, "field-use_chat_session": {"class": "Checkbox", "label": "Keep active AI session", "value": false, "display": false, "disabled": false}, "field-desc-use_chat_session": {"class": "Label", "text": "When continuing a session, extends that same session — no new key needed", "display": false, "disabled": false}}
- `field-prompt_vault_key` → `audit_text` (actual `audit_text`): {"field-prompt_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-prompt_vault_key` → `audit_text2` (actual `audit_text2`): {"field-prompt_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-continue_session_key` → `audit_session` (actual `audit_session`): {"field-continue_session_key": {"class": "Select", "value": "audit_session", "options": [["", "Select.NULL"], ["audit_session [ai_session]", "audit_session"]], "display": false, "disabled": false}}
- `field-context_input_count` → `1` (actual `1`): {"field-context_input_count": {"class": "Select", "value": "1", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_input_count` → `2` (actual `2`): {"field-context_input_count": {"class": "Select", "value": "2", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_2_source": {"class": "Label", "text": "Context 2 source:", "display": true, "disabled": false}, "field-desc-context_2_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_2_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_2": {"class": "Label", "text": "Context 2 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_2": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_input_count` → `3` (actual `3`): {"field-context_input_count": {"class": "Select", "value": "3", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_2_source": {"class": "Label", "text": "Context 2 source:", "display": true, "disabled": false}, "field-desc-context_2_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_2_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_3_source": {"class": "Label", "text": "Context 3 source:", "display": true, "disabled": false}, "field-desc-context_3_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_3_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_2": {"class": "Label", "text": "Context 2 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_2": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_3": {"class": "Label", "text": "Context 3 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_3": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_input_count` → `4` (actual `4`): {"field-context_input_count": {"class": "Select", "value": "4", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_2_source": {"class": "Label", "text": "Context 2 source:", "display": true, "disabled": false}, "field-desc-context_2_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_2_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_3_source": {"class": "Label", "text": "Context 3 source:", "display": true, "disabled": false}, "field-desc-context_3_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_3_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_4_source": {"class": "Label", "text": "Context 4 source:", "display": true, "disabled": false}, "field-desc-context_4_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_4_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_2": {"class": "Label", "text": "Context 2 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_2": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_3": {"class": "Label", "text": "Context 3 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_3": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_4": {"class": "Label", "text": "Context 4 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_4": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_input_count` → `5` (actual `5`): {"field-context_input_count": {"class": "Select", "value": "5", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_2_source": {"class": "Label", "text": "Context 2 source:", "display": true, "disabled": false}, "field-desc-context_2_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_2_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_3_source": {"class": "Label", "text": "Context 3 source:", "display": true, "disabled": false}, "field-desc-context_3_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_3_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_4_source": {"class": "Label", "text": "Context 4 source:", "display": true, "disabled": false}, "field-desc-context_4_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_4_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_5_source": {"class": "Label", "text": "Context 5 source:", "display": true, "disabled": false}, "field-desc-context_5_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_5_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_2": {"class": "Label", "text": "Context 2 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_2": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_3": {"class": "Label", "text": "Context 3 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_3": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_4": {"class": "Label", "text": "Context 4 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_4": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_5": {"class": "Label", "text": "Context 5 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_5": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_input_count` → `6` (actual `6`): {"field-context_input_count": {"class": "Select", "value": "6", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_2_source": {"class": "Label", "text": "Context 2 source:", "display": true, "disabled": false}, "field-desc-context_2_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_2_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_3_source": {"class": "Label", "text": "Context 3 source:", "display": true, "disabled": false}, "field-desc-context_3_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_3_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_4_source": {"class": "Label", "text": "Context 4 source:", "display": true, "disabled": false}, "field-desc-context_4_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_4_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_5_source": {"class": "Label", "text": "Context 5 source:", "display": true, "disabled": false}, "field-desc-context_5_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_5_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_6_source": {"class": "Label", "text": "Context 6 source:", "display": true, "disabled": false}, "field-desc-context_6_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_6_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_2": {"class": "Label", "text": "Context 2 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_2": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_3": {"class": "Label", "text": "Context 3 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_3": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_4": {"class": "Label", "text": "Context 4 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_4": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_5": {"class": "Label", "text": "Context 5 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_5": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_6": {"class": "Label", "text": "Context 6 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_6": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_input_count` → `7` (actual `7`): {"field-context_input_count": {"class": "Select", "value": "7", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_2_source": {"class": "Label", "text": "Context 2 source:", "display": true, "disabled": false}, "field-desc-context_2_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_2_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_3_source": {"class": "Label", "text": "Context 3 source:", "display": true, "disabled": false}, "field-desc-context_3_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_3_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_4_source": {"class": "Label", "text": "Context 4 source:", "display": true, "disabled": false}, "field-desc-context_4_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_4_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_5_source": {"class": "Label", "text": "Context 5 source:", "display": true, "disabled": false}, "field-desc-context_5_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_5_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_6_source": {"class": "Label", "text": "Context 6 source:", "display": true, "disabled": false}, "field-desc-context_6_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_6_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_7_source": {"class": "Label", "text": "Context 7 source:", "display": true, "disabled": false}, "field-desc-context_7_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_7_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_2": {"class": "Label", "text": "Context 2 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_2": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_3": {"class": "Label", "text": "Context 3 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_3": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_4": {"class": "Label", "text": "Context 4 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_4": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_5": {"class": "Label", "text": "Context 5 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_5": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_6": {"class": "Label", "text": "Context 6 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_6": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_7": {"class": "Label", "text": "Context 7 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_7": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_input_count` → `8` (actual `8`): {"field-context_input_count": {"class": "Select", "value": "8", "options": [["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"]], "display": true, "disabled": false}, "field-label-context_1_source": {"class": "Label", "text": "Context 1 source:", "display": true, "disabled": false}, "field-desc-context_1_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_1_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_2_source": {"class": "Label", "text": "Context 2 source:", "display": true, "disabled": false}, "field-desc-context_2_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_2_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_3_source": {"class": "Label", "text": "Context 3 source:", "display": true, "disabled": false}, "field-desc-context_3_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_3_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_4_source": {"class": "Label", "text": "Context 4 source:", "display": true, "disabled": false}, "field-desc-context_4_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_4_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_5_source": {"class": "Label", "text": "Context 5 source:", "display": true, "disabled": false}, "field-desc-context_5_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_5_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_6_source": {"class": "Label", "text": "Context 6 source:", "display": true, "disabled": false}, "field-desc-context_6_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_6_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_7_source": {"class": "Label", "text": "Context 7 source:", "display": true, "disabled": false}, "field-desc-context_7_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_7_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_8_source": {"class": "Label", "text": "Context 8 source:", "display": true, "disabled": false}, "field-desc-context_8_source": {"class": "Label", "text": "Additional context appended in configured order", "display": true, "disabled": false}, "field-context_8_source": {"class": "Select", "value": "Configured", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-context_1": {"class": "Label", "text": "Context 1 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_2": {"class": "Label", "text": "Context 2 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_2": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_3": {"class": "Label", "text": "Context 3 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_3": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_4": {"class": "Label", "text": "Context 4 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_4": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_5": {"class": "Label", "text": "Context 5 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_5": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_6": {"class": "Label", "text": "Context 6 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_6": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_7": {"class": "Label", "text": "Context 7 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_7": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "field-label-context_8": {"class": "Label", "text": "Context 8 (E to edit, ESC to finish):", "display": true, "disabled": false}, "field-context_8": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `field-context_1_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_1_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_1_source` → `Vault` (actual `Vault`): {"field-context_1_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_1_vault_key` → `audit_text` (actual `audit_text`): {"field-context_1_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_1_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_1_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_2_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_2_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_2_source` → `Vault` (actual `Vault`): {"field-context_2_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_2_vault_key` → `audit_text` (actual `audit_text`): {"field-context_2_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_2_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_2_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_3_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_3_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_3_source` → `Vault` (actual `Vault`): {"field-context_3_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_3_vault_key` → `audit_text` (actual `audit_text`): {"field-context_3_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_3_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_3_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_4_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_4_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_4_source` → `Vault` (actual `Vault`): {"field-context_4_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_4_vault_key` → `audit_text` (actual `audit_text`): {"field-context_4_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_4_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_4_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_5_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_5_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_5_source` → `Vault` (actual `Vault`): {"field-context_5_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_5_vault_key` → `audit_text` (actual `audit_text`): {"field-context_5_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_5_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_5_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_6_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_6_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_6_source` → `Vault` (actual `Vault`): {"field-context_6_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_6_vault_key` → `audit_text` (actual `audit_text`): {"field-context_6_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_6_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_6_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_7_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_7_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_7_source` → `Vault` (actual `Vault`): {"field-context_7_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_7_vault_key` → `audit_text` (actual `audit_text`): {"field-context_7_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_7_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_7_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_8_source` → `Upstream payload` (actual `Upstream payload`): {"field-context_8_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_8_source` → `Vault` (actual `Vault`): {"field-context_8_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": false, "disabled": false}}
- `field-context_8_vault_key` → `audit_text` (actual `audit_text`): {"field-context_8_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-context_8_vault_key` → `audit_text2` (actual `audit_text2`): {"field-context_8_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-document_source` → `Upstream payload` (actual `Upstream payload`): {"field-document_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-document": {"class": "Label", "text": "Document (E to edit, ESC to finish):", "display": false, "disabled": false}, "field-document": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `field-document_source` → `Vault` (actual `Vault`): {"field-document_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-document_vault_key": {"class": "Label", "text": "Document Vault key:", "display": true, "disabled": false}, "field-document_vault_key": {"class": "Select", "value": "Select.NULL", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": true, "disabled": false}, "field-label-document": {"class": "Label", "text": "Document (E to edit, ESC to finish):", "display": false, "disabled": false}, "field-document": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `field-document_vault_key` → `audit_text` (actual `audit_text`): {"field-document_vault_key": {"class": "Select", "value": "audit_text", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-document_vault_key` → `audit_text2` (actual `audit_text2`): {"field-document_vault_key": {"class": "Select", "value": "audit_text2", "options": [["", "Select.NULL"], ["audit_text [string]", "audit_text"], ["audit_text2 [string]", "audit_text2"]], "display": false, "disabled": false}}
- `field-model` → `claude-sonnet-5` (actual `claude-sonnet-5`): {"field-model": {"class": "Select", "value": "claude-sonnet-5", "options": [["claude-opus-4-8", "claude-opus-4-8"], ["claude-sonnet-5", "claude-sonnet-5"], ["claude-sonnet-4-6", "claude-sonnet-4-6"], ["claude-haiku-4-5", "claude-haiku-4-5"]], "display": true, "disabled": false}}
- `field-model` → `claude-sonnet-4-6` (actual `claude-sonnet-4-6`): {"field-model": {"class": "Select", "value": "claude-sonnet-4-6", "options": [["claude-opus-4-8", "claude-opus-4-8"], ["claude-sonnet-5", "claude-sonnet-5"], ["claude-sonnet-4-6", "claude-sonnet-4-6"], ["claude-haiku-4-5", "claude-haiku-4-5"]], "display": true, "disabled": false}}
- `field-model` → `claude-haiku-4-5` (actual `claude-haiku-4-5`): {"field-model": {"class": "Select", "value": "claude-haiku-4-5", "options": [["claude-opus-4-8", "claude-opus-4-8"], ["claude-sonnet-5", "claude-sonnet-5"], ["claude-sonnet-4-6", "claude-sonnet-4-6"], ["claude-haiku-4-5", "claude-haiku-4-5"]], "display": true, "disabled": false}}
- `field-api_key_secret` → `audit_api` (actual `audit_api`): {"field-api_key_secret": {"class": "Select", "value": "audit_api", "options": [["", "Select.NULL"], ["audit_api", "audit_api"]], "display": true, "disabled": false}}
- `dead-drop-passthrough` → `True` (actual `True`): {"transient-output-name-default": {"class": "CommandInput", "value": "LLM Result", "display": true, "disabled": true}, "transient-output-desc-default": {"class": "CommandInput", "value": "Model response text (or forwarded payload on dead-drop)", "display": true, "disabled": true}, "dead-drop-passthrough": {"class": "Checkbox", "label": "Forward incoming payload unchanged", "value": true, "display": true, "disabled": false}}
- `vault-output-disabled-default` → `True` (actual `True`): {"vault-output-disabled-default": {"class": "Checkbox", "label": "Disable output", "value": true, "display": true, "disabled": false}, "vault-output-key-default": {"class": "CommandInput", "value": "", "display": true, "disabled": true}, "vault-output-desc-default": {"class": "CommandInput", "value": "Model response text (or forwarded payload on dead-drop)", "display": true, "disabled": true}}
- `field-use_chat_session` → `True` (actual `True`): {"field-use_chat_session": {"class": "Checkbox", "label": "Keep active AI session", "value": true, "display": true, "disabled": false}, "field-label-session_key": {"class": "Label", "text": "Session key:", "display": true, "disabled": false}, "field-session_key": {"class": "CommandInput", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **57**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Concat — `concat_node`

Source: `backend/nodes/concat_node.py`. Helper spec: none.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "template": "{input}"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Concat | True / False |
| node-config-summary | Static | Node type: Concat<br>Formats input and variables into text |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-template | Label | Template *: |  | True / False |
| field-template | CommandTextArea |  | {input} | True / False |

Navigation candidates: `["field-template", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_88f442a6).default -> input<br>  outputs:<br>    default -> No-Op (node_f1c3f1c6).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Concat (node_2ff0ea27)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Conditional — `conditional_node`

Source: `backend/nodes/conditional_node.py`. Helper spec: none.

Selector family/group: **Flow Control / Branch**.
Ports: `["input"]` → `["true", "false"]`.

Defaults:

```json
{
  "condition_type": "contains",
  "left_value_source": "input",
  "variable_name": "",
  "right_value": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Conditional | True / False |
| node-config-summary | Static | Node type: Conditional<br>Routes to one path based on a condition |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-condition_type | Label | Condition type *: |  | True / False |
| field-condition_type | Select |  Options: [["equals", "equals"], ["not_equals", "not_equals"], ["contains", "contains"], ["regex", "regex"]] | contains | True / False |
| field-label-left_value_source | Label | Left value source *: |  | True / False |
| field-left_value_source | Select |  Options: [["input", "input"], ["variable", "variable"]] | input | True / False |
| field-label-variable_name | Label | Variable name: |  | True / False |
| field-variable_name | CommandInput |  |  | True / False |
| field-label-right_value | Label | Right value *: |  | True / False |
| field-right_value | CommandInput |  |  | True / False |
| field-label-true_label | Label | true branch name: |  | True / False |
| field-desc-true_label | Label | Editor display name for true |  | True / False |
| field-true_label | CommandInput |  |  | True / False |
| field-label-false_label | Label | false branch name: |  | True / False |
| field-desc-false_label | Label | Editor display name for false |  | True / False |
| field-false_label | CommandInput |  |  | True / False |

Navigation candidates: `["field-condition_type", "field-left_value_source", "field-variable_name", "field-right_value", "field-true_label", "field-false_label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | True |  | True / False |
| transient-output-name-true | CommandInput |  | True | True / False |
| transient-output-desc-true | CommandInput |  |  | True / False |
| — | Label | False |  | True / False |
| transient-output-name-false | CommandInput |  | False | True / False |
| transient-output-desc-false | CommandInput |  |  | True / False |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-true", "transient-output-desc-true", "transient-output-name-false", "transient-output-desc-false", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_0ca8b471).default -> input<br>  outputs:<br>    true -> No-Op (node_5502b12a).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Conditional (node_f63882fb)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-condition_type` → `equals` (actual `equals`): {"field-condition_type": {"class": "Select", "value": "equals", "options": [["equals", "equals"], ["not_equals", "not_equals"], ["contains", "contains"], ["regex", "regex"]], "display": true, "disabled": false}}
- `field-condition_type` → `not_equals` (actual `not_equals`): {"field-condition_type": {"class": "Select", "value": "not_equals", "options": [["equals", "equals"], ["not_equals", "not_equals"], ["contains", "contains"], ["regex", "regex"]], "display": true, "disabled": false}}
- `field-condition_type` → `regex` (actual `regex`): {"field-condition_type": {"class": "Select", "value": "regex", "options": [["equals", "equals"], ["not_equals", "not_equals"], ["contains", "contains"], ["regex", "regex"]], "display": true, "disabled": false}}
- `field-left_value_source` → `variable` (actual `variable`): {"field-left_value_source": {"class": "Select", "value": "variable", "options": [["input", "input"], ["variable", "variable"]], "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **4**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Counter — `counter_node`

Source: `backend/nodes/debug/counter_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "counter_name": "counter"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Counter | True / False |
| node-config-summary | Static | Node type: Counter<br>Increments a persistent counter each time it is visited |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-counter_name | Label | Counter Name *: |  | True / False |
| field-counter_name | CommandInput |  | counter | True / False |

Navigation candidates: `["field-counter_name", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_7e37a3b9).default -> input<br>  outputs:<br>    default -> No-Op (node_b30f541c).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Counter (node_36960c6e)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Deep Branch — `deep_branch_node`

Source: `backend/nodes/debug/deep_branch_node.py`. Helper spec: none.

Selector family/group: **Flow Control / Branch**.
Ports: `["input"]` → `["default", "branch"]`.

Defaults:

```json
{}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Deep Branch | True / False |
| node-config-summary | Static | Node type: Deep Branch<br>Spawns a child branch to test max-depth enforcement |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-default_label | Label | default branch name: |  | True / False |
| field-desc-default_label | Label | Editor display name for default |  | True / False |
| field-default_label | CommandInput |  |  | True / False |
| field-label-branch_label | Label | branch branch name: |  | True / False |
| field-desc-branch_label | Label | Editor display name for branch |  | True / False |
| field-branch_label | CommandInput |  |  | True / False |

Navigation candidates: `["field-default_label", "field-branch_label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Branch |  | True / False |
| transient-output-name-branch | CommandInput |  | Branch | True / False |
| transient-output-desc-branch | CommandInput |  |  | True / False |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "transient-output-name-branch", "transient-output-desc-branch", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_83fdfa96).default -> input<br>  outputs:<br>    default -> No-Op (node_6ac7c0f1).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Deep Branch (node_0a46988f)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Deleted Node — `tombstone_node`

Source: `backend/nodes/debug/tombstone_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `[]` → `[]`.

Defaults:

```json
{
  "original_type": "",
  "original_display_name": "",
  "original_input_ports": [],
  "original_output_ports": []
}
```

Intentionally no ordinary config mount: restore/replace record, excluded from selector.

## Echo — `echo_node`

Source: `backend/nodes/debug/echo_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "label": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Echo | True / False |
| node-config-summary | Static | Node type: Echo<br>Passes input through unchanged |  | True / False |
| — | Static | Dead drop payload: forwards the upstream payload unchanged. |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-label | Label | Label: |  | True / False |
| field-label | CommandInput |  |  | True / False |

Navigation candidates: `["field-label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_a177bd15).default -> input<br>  outputs:<br>    default -> No-Op (node_6ed6acbc).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Echo (node_5f2434c3)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Embedding — `embedding_node`

Source: `backend/nodes/embedding_node.py`. Helper spec: none.

Selector family/group: **Complex / AI Processing**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "model": "text-embedding-3-small",
  "text_field": "input",
  "api_key_secret": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Embedding | True / False |
| node-config-summary | Static | Node type: Embedding<br>Simulates creating an embedding vector |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-model | Label | Model *: |  | True / False |
| field-model | Select |  Options: [["text-embedding-3-small", "text-embedding-3-small"], ["text-embedding-3-large", "text-embedding-3-large"]] | text-embedding-3-small | True / False |
| field-label-text_field | Label | Text field *: |  | True / False |
| field-text_field | CommandInput |  | input | True / False |
| field-label-api_key_secret | Label | API key (secrets store key): |  | True / False |
| field-api_key_secret | Select |  Options: [["", "Select.NULL"], ["audit_api", "audit_api"]] | Select.NULL | True / False |

Navigation candidates: `["field-model", "field-text_field", "field-api_key_secret", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_9b1680ca).default -> input<br>  outputs:<br>    default -> No-Op (node_61879860).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Embedding (node_c7bb4475)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-model` → `text-embedding-3-large` (actual `text-embedding-3-large`): {"field-model": {"class": "Select", "value": "text-embedding-3-large", "options": [["text-embedding-3-small", "text-embedding-3-small"], ["text-embedding-3-large", "text-embedding-3-large"]], "display": true, "disabled": false}}
- `field-api_key_secret` → `audit_api` (actual `audit_api`): {"field-api_key_secret": {"class": "Select", "value": "audit_api", "options": [["", "Select.NULL"], ["audit_api", "audit_api"]], "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **2**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## End — `end_node`

Source: `backend/nodes/end_node.py`. Helper spec: none.

Selector family/group: **Flow Control / direct**.
Ports: `["input"]` → `[]`.

Defaults:

```json
{
  "message": "Branch completed"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | End | True / False |
| node-config-summary | Static | Node type: End<br>Terminates a workflow branch |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-message | Label | Message *: |  | True / False |
| field-desc-message | Label | Completion message recorded in the output log |  | True / False |
| field-message | CommandInput |  | Branch completed | True / False |

Navigation candidates: `["field-message", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Static | No dead drop payloads. |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_165db45c).default -> input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: End (node_aa3d1de7)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Error Trigger — `error_node`

Source: `backend/nodes/debug/error_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "message": "Deliberate error from ErrorNode",
  "error_mode": "fail"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Error Trigger | True / False |
| node-config-summary | Static | Node type: Error Trigger<br>Signals a workflow error on demand |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-message | Label | Error Message *: |  | True / False |
| field-message | CommandInput |  | Deliberate error from ErrorNode | True / False |
| field-label-error_mode | Label | Error Mode *: |  | True / False |
| field-error_mode | Select |  Options: [["fail", "fail"], ["warn", "warn"]] | fail | True / False |

Navigation candidates: `["field-message", "field-error_mode", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_f6e8c30f).default -> input<br>  outputs:<br>    default -> No-Op (node_492e937c).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Error Trigger (node_2c4eb764)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-error_mode` → `warn` (actual `warn`): {"field-error_mode": {"class": "Select", "value": "warn", "options": [["fail", "fail"], ["warn", "warn"]], "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **1**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## File Instance — `example_file_instance_node`

Source: `backend/nodes/io/example_file_instance_node.py`. Helper spec: `aotn_node_helper/specs/example_file_instance_node.yaml`.

Selector family/group: **Inputs / direct**.
Ports: `["file_path"]` → `["default"]`.

Defaults:

```json
{
  "file_path_source": "Configured",
  "file_path_vault_key": "",
  "file_path": "",
  "transient_output": true,
  "dead_drop_passthrough": false,
  "transient_outputs": [],
  "vault_write": false,
  "vault_write_key": "",
  "vault_write_description": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | File Instance | True / False |
| node-config-summary | Static | Node type: File Instance<br>Opens a file at a configured or supplied path and reports success |  | True / False |
| — | Label | Incoming Payload |  | True / False |
| incoming-payload-file_path | Static | Node source: User Text Input node<br>Payload: audit_text (any) |  | True / False |
| form-section-file_path_source | Label | Optional Inputs |  | True / False |
| field-label-file_path_source | Label | File path source: |  | True / False |
| field-desc-file_path_source | Label | Where the file path comes from at execution time |  | True / False |
| field-file_path_source | Select |  Options: [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]] | Configured | True / False |
| field-label-file_path_vault_key | Label | File path Vault key: |  | False / False |
| field-file_path_vault_key | Select |  Options: [["", "Select.NULL"], ["audit_file [file]", "audit_file"]] | Select.NULL | False / False |

Navigation candidates: `["alias-input", "field-file_path_source", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-file_path | Label | File path: |  | True / False |
| field-file_path | CommandInput |  |  | True / False |

Navigation candidates: `["field-file_path", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Downstream node payload |  | True / False |
| downstream-header-default | Static | Open Result  [bool] |  | True / False |
| — | Label | Payload name: |  | True / False |
| transient-output-name-default | CommandInput |  | Open Result | True / False |
| — | Label | Description: |  | True / False |
| transient-output-desc-default | CommandInput |  | True when the file opened successfully, false on error | True / False |
| dead-drop-passthrough | Checkbox | Forward incoming payload unchanged | False | True / False |
| — | Label | Vault Payload |  | True / False |
| vault-header-default | Static | Open Result  [bool] |  | True / False |
| vault-output-disabled-default | Checkbox | Disable output | True | True / False |
| — | Label | Vault key: |  | True / False |
| vault-output-key-default | CommandInput |  |  | True / True |
| — | Label | Description: |  | True / False |
| vault-output-desc-default | CommandInput |  | True when the file opened successfully, false on error | True / True |

Navigation candidates: `["transient-output-name-default", "transient-output-desc-default", "dead-drop-passthrough", "vault-output-disabled-default", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_2aa346f9).default -> file_path<br>  outputs:<br>    default -> No-Op (node_41662da5).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: File Instance (node_e5186a0f)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `field-file_path_source` → `Upstream payload` (actual `Upstream payload`): {"field-file_path_source": {"class": "Select", "value": "Upstream payload", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-file_path": {"class": "Label", "text": "File path:", "display": false, "disabled": false}, "field-file_path": {"class": "CommandInput", "value": "", "display": false, "disabled": false}}
- `field-file_path_source` → `Vault` (actual `Vault`): {"field-file_path_source": {"class": "Select", "value": "Vault", "options": [["Upstream payload", "Upstream payload"], ["Vault", "Vault"], ["Configured", "Configured"]], "display": true, "disabled": false}, "field-label-file_path_vault_key": {"class": "Label", "text": "File path Vault key:", "display": true, "disabled": false}, "field-file_path_vault_key": {"class": "Select", "value": "Select.NULL", "options": [["", "Select.NULL"], ["audit_file [file]", "audit_file"]], "display": true, "disabled": false}, "field-label-file_path": {"class": "Label", "text": "File path:", "display": false, "disabled": false}, "field-file_path": {"class": "CommandInput", "value": "", "display": false, "disabled": false}}
- `field-file_path_vault_key` → `audit_file` (actual `audit_file`): {"field-file_path_vault_key": {"class": "Select", "value": "audit_file", "options": [["", "Select.NULL"], ["audit_file [file]", "audit_file"]], "display": false, "disabled": false}}
- `dead-drop-passthrough` → `True` (actual `True`): {"transient-output-name-default": {"class": "CommandInput", "value": "Open Result", "display": true, "disabled": true}, "transient-output-desc-default": {"class": "CommandInput", "value": "True when the file opened successfully, false on error", "display": true, "disabled": true}, "dead-drop-passthrough": {"class": "Checkbox", "label": "Forward incoming payload unchanged", "value": true, "display": true, "disabled": false}}
- `vault-output-disabled-default` → `False` (actual `False`): {"vault-output-disabled-default": {"class": "Checkbox", "label": "Disable output", "value": false, "display": true, "disabled": false}, "vault-output-key-default": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "vault-output-desc-default": {"class": "CommandInput", "value": "True when the file opened successfully, false on error", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **5**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## File Reader — `file_reader_node`

Source: `backend/nodes/file_reader_node.py`. Helper spec: none.

Selector family/group: **Inputs / File Reader**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "file_path": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | File Reader | True / False |
| node-config-summary | Static | Node type: File Reader<br>Reads text from a local file |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-file_path | Label | File path *: |  | True / False |
| field-file_path | CommandInput |  |  | True / False |

Navigation candidates: `["field-file_path", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_34b6ea3d).default -> input<br>  outputs:<br>    default -> No-Op (node_badc42dd).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: File Reader (node_ab0d9240)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Get Variable — `get_variable_node`

Source: `backend/nodes/get_variable_node.py`. Helper spec: none.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "variable_name": "value",
  "default": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Get Variable | True / False |
| node-config-summary | Static | Node type: Get Variable<br>Reads a value from persistent memory |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-variable_name | Label | Variable name *: |  | True / False |
| field-variable_name | CommandInput |  | value | True / False |
| field-label-default | Label | Default: |  | True / False |
| field-default | CommandInput |  |  | True / False |

Navigation candidates: `["field-variable_name", "field-default", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_2681ad72).default -> input<br>  outputs:<br>    default -> No-Op (node_15bf44d9).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Get Variable (node_4b226eca)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## HTTP Request — `http_request_node`

Source: `backend/nodes/io/http_request_node.py`. Helper spec: `aotn_node_helper/specs/http_request_node.yaml`.

Selector family/group: **Inputs / Web Request**.
Ports: `["input"]` → `["default", "error"]`.

Defaults:

```json
{
  "url": "",
  "method": "GET",
  "body": "",
  "timeout_seconds": 10.0,
  "auth_token_secret": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | HTTP Request | True / False |
| node-config-summary | Static | Node type: HTTP Request<br>Make an HTTP GET or POST request and forward the response body |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-url | Label | URL *: |  | True / False |
| field-url | CommandInput |  |  | True / False |
| field-label-method | Label | Method: |  | True / False |
| field-method | Select |  Options: [["GET", "GET"], ["POST", "POST"]] | GET | True / False |
| field-label-body | Label | Request body (POST): |  | True / False |
| field-body | CommandTextArea |  |  | True / False |
| field-label-timeout_seconds | Label | Timeout (seconds): |  | True / False |
| field-timeout_seconds | CommandInput |  | 10.0 | True / False |
| field-label-auth_token_secret | Label | Bearer token (secrets store key): |  | True / False |
| field-auth_token_secret | Select |  Options: [["", "Select.NULL"], ["audit_api", "audit_api"]] | Select.NULL | True / False |
| field-label-default_label | Label | default branch name: |  | True / False |
| field-desc-default_label | Label | Editor display name for default |  | True / False |
| field-default_label | CommandInput |  |  | True / False |
| field-label-error_label | Label | error branch name: |  | True / False |
| field-desc-error_label | Label | Editor display name for error |  | True / False |
| field-error_label | CommandInput |  |  | True / False |

Navigation candidates: `["field-url", "field-method", "field-body", "field-timeout_seconds", "field-auth_token_secret", "field-default_label", "field-error_label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Error |  | True / False |
| transient-output-name-error | CommandInput |  | Error | True / False |
| transient-output-desc-error | CommandInput |  |  | True / False |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "transient-output-name-error", "transient-output-desc-error", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_cad727cc).default -> input<br>  outputs:<br>    default -> No-Op (node_6ef332fd).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: HTTP Request (node_0dac15b3)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-method` → `POST` (actual `POST`): {"field-method": {"class": "Select", "value": "POST", "options": [["GET", "GET"], ["POST", "POST"]], "display": true, "disabled": false}}
- `field-auth_token_secret` → `audit_api` (actual `audit_api`): {"field-auth_token_secret": {"class": "Select", "value": "audit_api", "options": [["", "Select.NULL"], ["audit_api", "audit_api"]], "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **2**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Image Generation — `image_generation_node`

Source: `backend/nodes/image_generation_node.py`. Helper spec: none.

Selector family/group: **Complex / AI Processing**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "prompt": "An image of {input}",
  "size": "1024x1024",
  "style": "natural",
  "api_key_secret": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Image Generation | True / False |
| node-config-summary | Static | Node type: Image Generation<br>Simulates an image generation request |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-prompt | Label | Prompt *: |  | True / False |
| field-prompt | CommandTextArea |  | An image of {input} | True / False |
| field-label-size | Label | Size *: |  | True / False |
| field-size | Select |  Options: [["512x512", "512x512"], ["1024x1024", "1024x1024"], ["1024x1792", "1024x1792"]] | 1024x1024 | True / False |
| field-label-style | Label | Style *: |  | True / False |
| field-style | Select |  Options: [["natural", "natural"], ["vivid", "vivid"]] | natural | True / False |
| field-label-api_key_secret | Label | API key (secrets store key): |  | True / False |
| field-api_key_secret | Select |  Options: [["", "Select.NULL"], ["audit_api", "audit_api"]] | Select.NULL | True / False |

Navigation candidates: `["field-prompt", "field-size", "field-style", "field-api_key_secret", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_13cf81ce).default -> input<br>  outputs:<br>    default -> No-Op (node_429fc9a2).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Image Generation (node_4de702bf)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-size` → `512x512` (actual `512x512`): {"field-size": {"class": "Select", "value": "512x512", "options": [["512x512", "512x512"], ["1024x1024", "1024x1024"], ["1024x1792", "1024x1792"]], "display": true, "disabled": false}}
- `field-size` → `1024x1792` (actual `1024x1792`): {"field-size": {"class": "Select", "value": "1024x1792", "options": [["512x512", "512x512"], ["1024x1024", "1024x1024"], ["1024x1792", "1024x1792"]], "display": true, "disabled": false}}
- `field-style` → `vivid` (actual `vivid`): {"field-style": {"class": "Select", "value": "vivid", "options": [["natural", "natural"], ["vivid", "vivid"]], "display": true, "disabled": false}}
- `field-api_key_secret` → `audit_api` (actual `audit_api`): {"field-api_key_secret": {"class": "Select", "value": "audit_api", "options": [["", "Select.NULL"], ["audit_api", "audit_api"]], "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **4**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## JSON Path — `json_path_node`

Source: `backend/nodes/data/json_path_node.py`. Helper spec: `aotn_node_helper/specs/json_path_node.yaml`.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default", "error"]`.

Defaults:

```json
{
  "path": "",
  "default_value": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | JSON Path | True / False |
| node-config-summary | Static | Node type: JSON Path<br>Extract a value from a JSON string by dot-path (e.g. "user.name") |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-path | Label | Dot path *: |  | True / False |
| field-path | CommandInput |  |  | True / False |
| field-label-default_value | Label | Default on miss: |  | True / False |
| field-default_value | CommandInput |  |  | True / False |
| field-label-default_label | Label | default branch name: |  | True / False |
| field-desc-default_label | Label | Editor display name for default |  | True / False |
| field-default_label | CommandInput |  |  | True / False |
| field-label-error_label | Label | error branch name: |  | True / False |
| field-desc-error_label | Label | Editor display name for error |  | True / False |
| field-error_label | CommandInput |  |  | True / False |

Navigation candidates: `["field-path", "field-default_value", "field-default_label", "field-error_label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Error |  | True / False |
| transient-output-name-error | CommandInput |  | Error | True / False |
| transient-output-desc-error | CommandInput |  |  | True / False |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "transient-output-name-error", "transient-output-desc-error", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_2bdf941f).default -> input<br>  outputs:<br>    default -> No-Op (node_2da32916).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: JSON Path (node_53f2dafc)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Logger — `logger_node`

Source: `backend/nodes/debug/logger_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "label": "",
  "include_input": true,
  "include_timestamp": false
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Logger | True / False |
| node-config-summary | Static | Node type: Logger<br>Logs the input value and passes it through |  | True / False |
| — | Static | Dead drop payload: forwards the upstream payload unchanged. |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-label | Label | Label: |  | True / False |
| field-label | CommandInput |  |  | True / False |
| field-include_input | Checkbox | Include Input | True | True / False |
| field-include_timestamp | Checkbox | Include Timestamp | False | True / False |

Navigation candidates: `["field-label", "field-include_input", "field-include_timestamp", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_6bd27c51).default -> input<br>  outputs:<br>    default -> No-Op (node_4ade02d9).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Logger (node_64ac536d)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-include_input` → `False` (actual `False`): {"field-include_input": {"class": "Checkbox", "label": "Include Input", "value": false, "display": true, "disabled": false}}
- `field-include_timestamp` → `True` (actual `True`): {"field-include_timestamp": {"class": "Checkbox", "label": "Include Timestamp", "value": true, "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **2**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Memory Snapshot — `memory_snapshot_node`

Source: `backend/nodes/debug/memory_snapshot_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "label": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Memory Snapshot | True / False |
| node-config-summary | Static | Node type: Memory Snapshot<br>Dumps the persistent memory bank to the output log |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-label | Label | Label: |  | True / False |
| field-label | CommandInput |  |  | True / False |

Navigation candidates: `["field-label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_4b7c4547).default -> input<br>  outputs:<br>    default -> No-Op (node_28b66edc).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Memory Snapshot (node_209e5afc)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Merge — `merge_node`

Source: `backend/nodes/merge_node.py`. Helper spec: none.

Selector family/group: **Flow Control / Merge**.
Ports: `["path_a", "path_b", "path_c", "path_d", "path_e"]` → `["default"]`.

Defaults:

```json
{
  "branches_to_close": [],
  "carry_forward_branch_id": "",
  "selected_branch_id": "",
  "selected_input_port": "path_a"
}
```

### Flat form

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Edit Node: Merge (node_628c80a5) |  | True / False |
| — | Static | number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert |  | True / False |
| — | Label | Branches To Close |  | True / False |
| — | Static | No open branches are available to close. |  | True / False |
| save-node-config | Button | Save |  | True / False |
| cancel-node-config | Button | Cancel |  | True / False |
| — | StatusBar | [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Alternate controls inspected

No selectable mode/checkbox variations in this composition.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Merge Beacon — `branch_end_node`

Source: `backend/nodes/branch_end_node.py`. Helper spec: none.

Selector family/group: **Flow Control / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{}
```

### Flat form

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Edit Node: Merge Beacon (node_5d42b3a6) |  | True / False |
| — | Static | number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert |  | True / False |
| — | Static | Merge Beacon has no editable fields.<br>Status: open until connected to a Merge node. |  | True / False |
| save-node-config | Button | Save |  | True / False |
| cancel-node-config | Button | Cancel |  | True / False |
| — | StatusBar | [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Alternate controls inspected

No selectable mode/checkbox variations in this composition.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## No-Op — `no_op_node`

Source: `backend/nodes/debug/no_op_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | No-Op | True / False |
| node-config-summary | Static | Node type: No-Op<br>Does nothing and passes execution through |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Static | No parameters. |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_7f8fb6f0).default -> input<br>  outputs:<br>    default -> No-Op (node_38582c4b).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: No-Op (node_6b0e1992)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Parallel Branch — `branch_node`

Source: `backend/nodes/branch_node.py`. Helper spec: none.

Selector family/group: **Flow Control / Branch**.
Ports: `["input"]` → `["path_a", "path_b", "path_c", "path_d", "path_e"]`.

Defaults:

```json
{
  "branch_count": 2,
  "branch_payload_sources": {},
  "condition": "always_branch",
  "match_value": "yes",
  "match_mode": "equals",
  "case_sensitive": false,
  "on_match": "path_a",
  "on_no_match": "path_b",
  "path_a_label": "Branch 1",
  "path_b_label": "Branch 2",
  "path_c_label": "Branch 3",
  "path_d_label": "Branch 4",
  "path_e_label": "Branch 5"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Parallel Branch | True / False |
| node-config-summary | Static | Node type: Parallel Branch<br>- Duplicates the incoming payload across branch paths.<br>- Parallel paths run independently<br>- Conditional branching hidden for a later node pass |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Branches |  | True / False |
| branch-count | CommandInput |  | 2 | True / False |
| — | Static | Choose 2 to 5 spawn points. |  | True / False |

Navigation candidates: `["branch-count", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Spawn Point: |  | True / False |
| branch-label-path_a | CommandInput |  | Branch 1 | True / False |
| — | Label | Start with: |  | True / False |
| branch-payload-source-path_a | Select |  Options: [["Upstream payload", "dead_drop:input"]] | dead_drop:input | True / False |
| — | Label | Spawn Point: |  | True / False |
| branch-label-path_b | CommandInput |  | Branch 2 | True / False |
| — | Label | Start with: |  | True / False |
| branch-payload-source-path_b | Select |  Options: [["Upstream payload", "dead_drop:input"]] | dead_drop:input | True / False |
| — | Label | Spawn Point: |  | True / False |
| branch-label-path_c | CommandInput |  | Branch 3 | True / False |
| — | Label | Start with: |  | True / False |
| branch-payload-source-path_c | Select |  Options: [["Upstream payload", "dead_drop:input"]] | dead_drop:input | True / False |
| — | Label | Spawn Point: |  | True / False |
| branch-label-path_d | CommandInput |  | Branch 4 | True / False |
| — | Label | Start with: |  | True / False |
| branch-payload-source-path_d | Select |  Options: [["Upstream payload", "dead_drop:input"]] | dead_drop:input | True / False |
| — | Label | Spawn Point: |  | True / False |
| branch-label-path_e | CommandInput |  | Branch 5 | True / False |
| — | Label | Start with: |  | True / False |
| branch-payload-source-path_e | Select |  Options: [["Upstream payload", "dead_drop:input"]] | dead_drop:input | True / False |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "branch-label-path_a", "branch-payload-source-path_a", "branch-label-path_b", "branch-payload-source-path_b", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_e346407d).default -> input<br>  outputs:<br>    path_a -> No-Op (node_9be5fb27).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Parallel Branch (node_f3ad531f)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `branch-count` → `5` (actual `5`): {"branch-count": {"class": "CommandInput", "value": "5", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **1**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Probe — `probe_node`

Source: `backend/nodes/debug/probe_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "label": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Probe | True / False |
| node-config-summary | Static | Node type: Probe<br>Inspects and logs the incoming value with type info |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-label | Label | Label: |  | True / False |
| field-label | CommandInput |  |  | True / False |

Navigation candidates: `["field-label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_b2d970d1).default -> input<br>  outputs:<br>    default -> No-Op (node_7a08c3e6).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Probe (node_33e155aa)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Random Branch — `random_branch_node`

Source: `backend/nodes/debug/random_branch_node.py`. Helper spec: none.

Selector family/group: **Flow Control / Branch**.
Ports: `["input"]` → `["path_a", "path_b"]`.

Defaults:

```json
{
  "seed": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Random Branch | True / False |
| node-config-summary | Static | Node type: Random Branch<br>Routes to path_a or path_b at random |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-seed | Label | Random Seed (empty = random): |  | True / False |
| field-seed | CommandInput |  |  | True / False |
| field-label-path_a_label | Label | path_a branch name: |  | True / False |
| field-desc-path_a_label | Label | Editor display name for path_a |  | True / False |
| field-path_a_label | CommandInput |  |  | True / False |
| field-label-path_b_label | Label | path_b branch name: |  | True / False |
| field-desc-path_b_label | Label | Editor display name for path_b |  | True / False |
| field-path_b_label | CommandInput |  |  | True / False |

Navigation candidates: `["field-seed", "field-path_a_label", "field-path_b_label", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Path A |  | True / False |
| transient-output-name-path_a | CommandInput |  | Path A | True / False |
| transient-output-desc-path_a | CommandInput |  |  | True / False |
| — | Label | Path B |  | True / False |
| transient-output-name-path_b | CommandInput |  | Path B | True / False |
| transient-output-desc-path_b | CommandInput |  |  | True / False |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-path_a", "transient-output-desc-path_a", "transient-output-name-path_b", "transient-output-desc-path_b", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_4e52b000).default -> input<br>  outputs:<br>    path_a -> No-Op (node_4abcdbc9).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Random Branch (node_b17295e9)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Random Number — `random_number_node`

Source: `backend/nodes/data/random_number_node.py`. Helper spec: `aotn_node_helper/specs/random_number_node.yaml`.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "mode": "integer",
  "min_value": 0,
  "max_value": 100,
  "seed": "",
  "value": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Random Number | True / False |
| node-config-summary | Static | Node type: Random Number<br>Produce a random integer or float within a configured range |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-mode | Label | Mode: |  | True / False |
| field-mode | Select |  Options: [["integer", "integer"], ["float", "float"]] | integer | True / False |
| field-label-min_value | Label | Minimum value: |  | True / False |
| field-min_value | CommandInput |  | 0 | True / False |
| field-label-max_value | Label | Maximum value: |  | True / False |
| field-max_value | CommandInput |  | 100 | True / False |
| field-label-seed | Label | Random seed (blank = unseeded): |  | True / False |
| field-seed | CommandInput |  |  | True / False |
| field-label-value | Label | Payload: |  | True / False |
| field-value | CommandInput |  |  | True / False |

Navigation candidates: `["field-mode", "field-min_value", "field-max_value", "field-seed", "field-value", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_8c159897).default -> input<br>  outputs:<br>    default -> No-Op (node_e85718f9).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Random Number (node_c6fcb403)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-mode` → `float` (actual `float`): {"field-mode": {"class": "Select", "value": "float", "options": [["integer", "integer"], ["float", "float"]], "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **1**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Repeat Counter — `repeat_counter_node`

Source: `backend/nodes/debug/repeat_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "max_visits": 3
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Repeat Counter | True / False |
| node-config-summary | Static | Node type: Repeat Counter<br>Signals an error when visited more than max_visits times |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-max_visits | Label | Max Visits *: |  | True / False |
| field-max_visits | CommandInput |  | 3 | True / False |

Navigation candidates: `["field-max_visits", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_230ac935).default -> input<br>  outputs:<br>    default -> No-Op (node_3bb13278).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Repeat Counter (node_2ed4003d)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Set Variable — `set_variable_node`

Source: `backend/nodes/set_variable_node.py`. Helper spec: none.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "variable_name": "value",
  "value_source": "input",
  "value": "",
  "pass_through": true
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Set Variable | True / False |
| node-config-summary | Static | Node type: Set Variable<br>Stores a value in persistent memory |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-variable_name | Label | Variable name *: |  | True / False |
| field-variable_name | CommandInput |  | value | True / False |
| field-label-value_source | Label | Value source *: |  | True / False |
| field-value_source | Select |  Options: [["input", "input"], ["literal", "literal"]] | input | True / False |
| field-label-value | Label | Value: |  | True / False |
| field-value | CommandInput |  |  | True / False |
| field-pass_through | Checkbox | Dead drop payload | True | True / False |
| field-desc-pass_through | Label | Forward the upstream payload after writing to memory |  | True / False |

Navigation candidates: `["field-variable_name", "field-value_source", "field-value", "field-pass_through", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / True |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_235363b9).default -> input<br>  outputs:<br>    default -> No-Op (node_c3ca820e).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Set Variable (node_be32986d)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-value_source` → `literal` (actual `literal`): {"field-value_source": {"class": "Select", "value": "literal", "options": [["input", "input"], ["literal", "literal"]], "display": true, "disabled": false}}
- `field-pass_through` → `False` (actual `False`): {"field-pass_through": {"class": "Checkbox", "label": "Dead drop payload", "value": false, "display": true, "disabled": false}, "membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": false, "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": true}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": true}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": true}}

Additional changed mode/routing save-reopen checks: **2**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Sleep — `sleep_node`

Source: `backend/nodes/debug/sleep_node.py`. Helper spec: none.

Selector family/group: **Utility / direct**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "duration": 0.1
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Sleep | True / False |
| node-config-summary | Static | Node type: Sleep<br>Pauses execution for a fixed duration |  | True / False |
| — | Static | Dead drop payload: Pauses, then forwards the previous node output unchanged. |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-duration | Label | Duration (seconds) *: |  | True / False |
| field-duration | CommandInput |  | 0.1 | True / False |

Navigation candidates: `["field-duration", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_9159c1ae).default -> input<br>  outputs:<br>    default -> No-Op (node_1923c03f).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Sleep (node_510c45a4)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Start — `start_node`

Source: `backend/nodes/start_node.py`. Helper spec: none.

Selector family/group: **Flow Control / direct**.
Ports: `[]` → `["default"]`.

Defaults:

```json
{
  "greeting": "Workflow started"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Start | True / False |
| node-config-summary | Static | Node type: Start<br>Entry point for workflow execution |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-greeting | Label | Greeting *: |  | True / False |
| field-desc-greeting | Label | Message to emit when the workflow begins |  | True / False |
| field-greeting | CommandInput |  | Workflow started | True / False |

Navigation candidates: `["field-greeting", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   outputs:<br>    default -> No-Op (node_a8f57922).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Start (node_f66648df)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "No upstream connection.", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "No upstream connection.", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Text Output — `text_output_node`

Source: `backend/nodes/text_output_node.py`. Helper spec: none.

Selector family/group: **Outputs / Text Output**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "label": "Output",
  "template": "{input}",
  "request_user_input": false,
  "prompt": "Enter a value:"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Text Output | True / False |
| node-config-summary | Static | Node type: Text Output<br>Formats input through a template and logs it |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-label | Label | Label *: |  | True / False |
| field-desc-label | Label | Label shown alongside the output |  | True / False |
| field-label | CommandInput |  | Output | True / False |
| field-label-template | Label | Template *: |  | True / False |
| field-desc-template | Label | Output text. Use {input} to insert the incoming value. |  | True / False |
| field-template | CommandInput |  | {input} | True / False |
| field-request_user_input | Checkbox | Request user input | False | True / False |
| field-desc-request_user_input | Label | Pause and prompt the user before producing output |  | True / False |
| field-label-prompt | Label | Prompt: |  | True / False |
| field-desc-prompt | Label | Prompt text shown when requesting user input |  | True / False |
| field-prompt | CommandInput |  | Enter a value: | True / False |

Navigation candidates: `["field-label", "field-template", "field-request_user_input", "field-prompt", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_040c27fb).default -> input<br>  outputs:<br>    default -> No-Op (node_221a2457).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Text Output (node_60e20848)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-request_user_input` → `True` (actual `True`): {"field-request_user_input": {"class": "Checkbox", "label": "Request user input", "value": true, "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **1**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Text Transform — `text_transform_node`

Source: `backend/nodes/data/text_transform_node.py`. Helper spec: `aotn_node_helper/specs/text_transform_node.yaml`.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "operation": "uppercase"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Text Transform | True / False |
| node-config-summary | Static | Node type: Text Transform<br>Apply a text transformation (uppercase, lowercase, strip, title, reverse) to the input string |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-operation | Label | Operation: |  | True / False |
| field-operation | Select |  Options: [["uppercase", "uppercase"], ["lowercase", "lowercase"], ["strip", "strip"], ["title", "title"], ["reverse", "reverse"]] | uppercase | True / False |

Navigation candidates: `["field-operation", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_6e0217c2).default -> input<br>  outputs:<br>    default -> No-Op (node_67ec5050).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Text Transform (node_eb8bcb31)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-operation` → `lowercase` (actual `lowercase`): {"field-operation": {"class": "Select", "value": "lowercase", "options": [["uppercase", "uppercase"], ["lowercase", "lowercase"], ["strip", "strip"], ["title", "title"], ["reverse", "reverse"]], "display": true, "disabled": false}}
- `field-operation` → `strip` (actual `strip`): {"field-operation": {"class": "Select", "value": "strip", "options": [["uppercase", "uppercase"], ["lowercase", "lowercase"], ["strip", "strip"], ["title", "title"], ["reverse", "reverse"]], "display": true, "disabled": false}}
- `field-operation` → `title` (actual `title`): {"field-operation": {"class": "Select", "value": "title", "options": [["uppercase", "uppercase"], ["lowercase", "lowercase"], ["strip", "strip"], ["title", "title"], ["reverse", "reverse"]], "display": true, "disabled": false}}
- `field-operation` → `reverse` (actual `reverse`): {"field-operation": {"class": "Select", "value": "reverse", "options": [["uppercase", "uppercase"], ["lowercase", "lowercase"], ["strip", "strip"], ["title", "title"], ["reverse", "reverse"]], "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": false, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": false, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Additional changed mode/routing save-reopen checks: **4**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## User Text Input — `user_text_input_node`

Source: `backend/nodes/user_text_input_node.py`. Helper spec: none.

Selector family/group: **Inputs / Text Input**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "prompt": "Enter text:"
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | User Text Input | True / False |
| node-config-summary | Static | Node type: User Text Input<br>Prompts the user for text during execution |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-prompt | Label | Prompt *: |  | True / False |
| field-prompt | CommandInput |  | Enter text: | True / False |

Navigation candidates: `["field-prompt", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_1ec3b960).default -> input<br>  outputs:<br>    default -> No-Op (node_a7841940).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: User Text Input (node_a6ce1f91)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Variable Reader — `variable_reader_node`

Source: `backend/nodes/debug/variable_reader_node.py`. Helper spec: none.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "variable_name": "",
  "default": ""
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Variable Reader | True / False |
| node-config-summary | Static | Node type: Variable Reader<br>Reads a named variable from persistent memory |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-variable_name | Label | Variable Name *: |  | True / False |
| field-variable_name | CommandInput |  |  | True / False |
| field-label-default | Label | Default Value: |  | True / False |
| field-default | CommandInput |  |  | True / False |

Navigation candidates: `["field-variable_name", "field-default", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / False |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["show-payload-upstream-payload", "show-payload-vault-payload", "transient-output-name-default", "transient-output-desc-default", "membank-writes", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_96fab358).default -> input<br>  outputs:<br>    default -> No-Op (node_64831838).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Variable Reader (node_b2f86cc9)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "1", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": false}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": false}, "membank-output-desc-0": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-0": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}, "membank-output-desc-1": {"class": "CommandInput", "value": "", "display": true, "disabled": false}, "membank-output-id-1": {"class": "CommandTextArea", "value": "", "display": true, "disabled": false}}

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Variable Setter — `variable_setter_node`

Source: `backend/nodes/debug/variable_setter_node.py`. Helper spec: none.

Selector family/group: **Utility / Data Transform**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "variable_name": "",
  "value": "",
  "pass_through": true
}
```

### 1 - Source

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Variable Setter | True / False |
| node-config-summary | Static | Node type: Variable Setter<br>Stores a named variable in persistent memory |  | True / False |
| — | Label | Upstream Payload |  | True / False |
| show-previous-output | Checkbox | Reveal upstream payload | False | True / False |
| previous-output-preview | PayloadPreview |  |  | False / False |
| membank-reads | Checkbox | Vault | False | True / False |
| membank-inputs | SelectionList |  Options: [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}] | [] | True / True |
| show-source-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| source-vault-payload-preview | PayloadPreview |  |  | False / False |

Navigation candidates: `["alias-input", "show-previous-output", "membank-reads", "show-source-vault-payload", "save-node-config", "cancel-node-config"]`.

### 2 - Parameters

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| field-label-variable_name | Label | Variable Name *: |  | True / False |
| field-variable_name | CommandInput |  |  | True / False |
| field-label-value | Label | Value (empty = use input): |  | True / False |
| field-value | CommandInput |  |  | True / False |
| field-pass_through | Checkbox | Dead drop payload | True | True / False |

Navigation candidates: `["field-variable_name", "field-value", "field-pass_through", "save-node-config", "cancel-node-config"]`.

### 3 - Payloads

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Incoming Payloads |  | True / False |
| show-payload-upstream-payload | Checkbox | Reveal upstream payload | False | True / False |
| payload-upstream-payload-preview | PayloadPreview |  |  | False / False |
| show-payload-vault-payload | Checkbox | Reveal Vault payload | False | True / False |
| payload-vault-payload-preview | PayloadPreview |  |  | False / False |
| — | Label | Dead Drop Payloads |  | True / False |
| — | Label | Default |  | True / False |
| transient-output-name-default | CommandInput |  | Output | True / False |
| transient-output-desc-default | CommandInput |  |  | True / False |
| — | Label | Vault Payloads |  | True / False |
| membank-writes | Checkbox | Write to Vault | False | True / True |
| — | Label | Payload count |  | True / False |
| membank-output-count | CommandInput |  | 0 | True / True |

Navigation candidates: `["field-variable_name", "field-value", "field-pass_through", "save-node-config", "cancel-node-config"]`.

### 4 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Connections |  | True / False |
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_157ce978).default -> input<br>  outputs:<br>    default -> No-Op (node_8cdf2b57).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Variable Setter (node_b3c488fc)
- `Static`: number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  number keys tabs \| w/s move \| a/d within row \| e interact \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

- `show-previous-output` → `True` (actual `True`): {"show-previous-output": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "previous-output-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `membank-reads` → `True` (actual `True`): {"membank-reads": {"class": "Checkbox", "label": "Vault", "value": true, "display": true, "disabled": false}, "membank-inputs": {"class": "SelectionList", "options": [{"prompt": "Vault: audit_text - No description", "value": "audit_text"}], "selected": [], "display": true, "disabled": false}}
- `show-source-vault-payload` → `True` (actual `True`): {"show-source-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "source-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `field-pass_through` → `False` (actual `False`): {"field-pass_through": {"class": "Checkbox", "label": "Dead drop payload", "value": false, "display": true, "disabled": false}, "membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": false, "display": true, "disabled": false}}
- `show-payload-upstream-payload` → `True` (actual `True`): {"show-payload-upstream-payload": {"class": "Checkbox", "label": "Reveal upstream payload", "value": true, "display": true, "disabled": false}, "payload-upstream-payload-preview": {"class": "PayloadPreview", "text": "Source: User Text Input\nPayload: audit_text", "display": true, "disabled": false}}
- `show-payload-vault-payload` → `True` (actual `True`): {"show-payload-vault-payload": {"class": "Checkbox", "label": "Reveal Vault payload", "value": true, "display": true, "disabled": false}, "payload-vault-payload-preview": {"class": "PayloadPreview", "text": "No Vault payload selected.", "display": true, "disabled": false}}
- `membank-writes` → `True` (actual `True`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": true}}
- `membank-output-count` → `2` (actual `2`): {"membank-writes": {"class": "Checkbox", "label": "Write to Vault", "value": true, "display": true, "disabled": true}, "membank-output-count": {"class": "CommandInput", "value": "2", "display": true, "disabled": true}}

Additional changed mode/routing save-reopen checks: **1**, all selected values retained.

Cancel unchanged: **True**. Unknown key survives Save: **False**. Second Save stable: **True**.

## Wait Until — `wait_until_node`

Source: `backend/nodes/wait_until_node.py`. Helper spec: none.

Selector family/group: **Flow Control / Wait / Timer**.
Ports: `["input"]` → `["default"]`.

Defaults:

```json
{
  "target_node_ids": "",
  "timeout_seconds": 0.0
}
```

### 1 - Wait

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Label | Alias: |  | True / False |
| alias-input | CommandInput |  | Wait Until | True / False |
| — | Static | Wait for all selected nodes to complete, then forward the incoming dead-drop payload unchanged. The next node can read the Vault. |  | True / False |
| — | Label | Wait for these nodes |  | True / False |
| wait-targets | SelectionList |  Options: [{"prompt": "User Text Input (node_3cde78e1)", "value": "node_3cde78e1"}] | [] | True / False |
| wait-target-summary | Static | No targets selected: this node will continue immediately. |  | True / False |
| — | Static | Targets must complete at least once in this run. A target that never executes can wait forever at zero timeout. |  | True / False |
| field-label-timeout_seconds | Label | Timeout seconds: |  | True / False |
| field-desc-timeout_seconds | Label | 0 waits forever (default); a positive value limits the wait |  | True / False |
| field-timeout_seconds | CommandInput |  | 0.0 | True / False |
| wait-config-error | Static |  |  | True / False |
| — | Static | Incoming: User Text Input.default<br>Forward unchanged<br>Next: No-Op.input |  | True / False |

Navigation candidates: `["alias-input", "wait-targets", "field-timeout_seconds", "save-node-config", "cancel-node-config"]`.

### 2 - Connections

| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |
|---|---|---|---|---|
| — | Static | Edit connections from the editor. |  | True / False |
| connection-summary | Static |   inputs:<br>    User Text Input (node_3cde78e1).default -> input<br>  outputs:<br>    default -> No-Op (node_9b324409).input |  | True / False |

Navigation candidates: `["save-node-config", "cancel-node-config"]`.

### Shared dialog chrome

- `Label`: Edit Node: Wait Until (node_5ad7e2ed)
- `Static`: 1/2 tabs \| w/s move \| e toggle/edit \| ctrl+s save \| esc cancel \| ctrl+q revert
- `save-node-config`: Save
- `cancel-node-config`: Cancel
- `StatusBar`: [NAV]  1/2 tabs \| w/s move \| e toggle/edit \| ctrl+s save \| esc cancel \| ctrl+q revert

### Alternate controls inspected

No selectable mode/checkbox variations in this composition.

Cancel unchanged: **True**. Unknown key survives Save: **True**. Second Save stable: **True**.


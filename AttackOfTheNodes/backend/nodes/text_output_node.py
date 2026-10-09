"""Text Output Node: reads input, formats it, and appends to output log."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory
from ..output_entry import OutputLogEntry
from ..vault_declarations import legacy_output_keys


class TextOutputNode(Node):
    """Formats input through a template and records the result."""

    terminates_branch: ClassVar[bool] = False

    node_type: ClassVar[str] = "text_output_node"
    display_name: ClassVar[str] = "Text Output"
    description: ClassVar[str] = "Formats input through a template and logs it"
    category: ClassVar[str] = NodeCategory.IO

    ui_hints: ClassVar[Dict[str, Any]] = {"formatted_output_preview": True}

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]

    input_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "input": {"name": "Input", "description": "Any payload formatted as text; use File Reader for file contents", "data_type": "any",
                  "required": True, "sources": ["upstream", "vault"]}
    }
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {"name": "Formatted output", "data_type": "string", "to": ["downstream"]}
    }

    default_config: ClassVar[Dict[str, Any]] = {
        "input_source": "Upstream payload",
        "input_vault_key": "",
        "label": "Output",
        "template": "{input}",
        "request_user_input": False,
        "prompt": "Enter a value:",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "input_source": {"type": "select", "label": "Input source", "options": ["Upstream payload", "Vault"], "tab": "Source", "section": "Required Inputs"},
        "input_vault_key": {"type": "string", "label": "Input Vault key", "vault_type": "any", "tab": "Source", "section": "Required Inputs", "visible_when": {"input_source": "Vault"}},
        "label": {
            "type": "string",
            "description": "Label shown alongside the output",
            "required": True,
        },
        "template": {
            "type": "string",
            "description": "Output text. Use {input} to insert the incoming value.",
            "required": True,
        },
        "request_user_input": {
            "type": "boolean",
            "description": "Pause and prompt the user before producing output",
            "required": False,
        },
        "prompt": {
            "type": "string",
            "description": "Prompt text shown when requesting user input",
            "required": False,
            "visible_when": {"request_user_input": True},
        },
    }

    async def execute(self, context: NodeContext) -> None:
        label = self.config.get("label", "Output")
        template = self.config.get("template", "{input}")
        request_input = self.config.get("request_user_input", False)
        prompt = self.config.get("prompt", "Enter a value:")

        if self.config.get("input_source", "Upstream payload") == "Vault":
            key = str(self.config.get("input_vault_key") or "").strip()
            missing = object()
            input_value = context.memory_bank.read_persistent(key, default=missing) if key else missing
            if input_value is missing:
                context.signal_error(ValueError(f"Text Output Vault input is unavailable: {key or '(no key selected)'}"))
                return
        else:
            input_value = context.inputs.get("input", "")
        if request_input:
            input_value = await context.signal_waiting_for_input(prompt)

        try:
            formatted = template.format(input=input_value)
        except (KeyError, IndexError, ValueError) as exc:
            context.signal_error(
                ValueError(f"Template formatting failed in {context.node_id}: {exc}")
            )
            return

        full_output = f"[{label}] {formatted}"
        log = list(context.memory_bank.read_persistent("output_log", default=[]))
        log.append(
            OutputLogEntry(
                full_output,
                branch_id=context.branch_id,
                node_id=context.node_id,
            )
        )
        context.memory_bank.store_persistent("output_log", log)

        for legacy_key in legacy_output_keys(self.config):
            context.memory_bank.store_persistent(legacy_key, full_output, type_tag="string")

        context.signal_done({"data": {"default": full_output}})

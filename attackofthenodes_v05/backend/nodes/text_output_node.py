"""Text Output Node: reads input, formats it, and appends to output log."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory
from ..output_entry import OutputLogEntry


class TextOutputNode(Node):
    """Formats input through a template and records the result."""

    node_type: ClassVar[str] = "text_output_node"
    display_name: ClassVar[str] = "Text Output"
    description: ClassVar[str] = "Formats input through a template and logs it"
    category: ClassVar[str] = NodeCategory.IO

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]

    default_config: ClassVar[Dict[str, Any]] = {
        "label": "Output",
        "template": "{input}",
        "request_user_input": False,
        "prompt": "Enter a value:",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "label": {
            "type": "string",
            "description": "Label shown alongside the output",
            "required": True,
        },
        "template": {
            "type": "string",
            "description": "str.format template with {input} placeholder",
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
        },
    }

    async def execute(self, context: NodeContext) -> None:
        label = self.config.get("label", "Output")
        template = self.config.get("template", "{input}")
        request_input = self.config.get("request_user_input", False)
        prompt = self.config.get("prompt", "Enter a value:")

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

        context.signal_done({"data": {"default": full_output}, "next_node_id": None})

"""Text Output Node: placeholder for Phase 2 execution logic."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext


class TextOutputNode(Node):
    """Processes an input value and appends formatted text to the output log."""

    node_type: ClassVar[str] = "text_output_node"
    display_name: ClassVar[str] = "Text Output"
    description: ClassVar[str] = "Processes input and produces text output"

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]

    default_config: ClassVar[Dict[str, Any]] = {
        "label": "Output",
        "template": "{input}",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "label": {
            "type": "string",
            "description": "Label shown alongside the output",
            "required": True,
        },
        "template": {
            "type": "string",
            "description": "Format string with {input} placeholder",
            "required": True,
        },
    }

    async def execute(self, context: NodeContext) -> None:
        context.signal_error(NotImplementedError("TextOutputNode arrives in Phase 2"))

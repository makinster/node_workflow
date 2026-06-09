"""Error trigger node — signals a workflow error on demand."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class ErrorNode(Node):
    """Raises a configurable error, useful for testing recovery flows."""

    node_type: ClassVar[str] = "error_node"
    display_name: ClassVar[str] = "Error Trigger"
    description: ClassVar[str] = "Signals a workflow error on demand"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "message": "Deliberate error from ErrorNode",
        "error_mode": "fail",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "message": {"type": "string", "label": "Error Message", "required": True},
        "error_mode": {
            "type": "string",
            "label": "Error Mode",
            "options": ["fail", "warn"],
            "required": True,
        },
    }

    async def execute(self, context: NodeContext) -> None:
        message = self.config.get("message", "Deliberate error from ErrorNode")
        mode = self.config.get("error_mode", "fail")
        if mode == "warn":
            context.signal_done({"data": {"default": f"[warn] {message}"}})
        else:
            context.signal_error(RuntimeError(message))

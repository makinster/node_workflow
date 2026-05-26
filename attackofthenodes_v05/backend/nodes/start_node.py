"""Start Node: entry point for workflow execution."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext


class StartNode(Node):
    """Entry point node. Emits a configurable greeting."""

    node_type: ClassVar[str] = "start_node"
    display_name: ClassVar[str] = "Start"
    description: ClassVar[str] = "Entry point for workflow execution"

    input_ports: ClassVar[List[str]] = []
    output_ports: ClassVar[List[str]] = ["default"]

    default_config: ClassVar[Dict[str, Any]] = {"greeting": "Workflow started"}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "greeting": {
            "type": "string",
            "description": "Message to emit when the workflow begins",
            "required": True,
        }
    }

    async def execute(self, context: NodeContext) -> None:
        greeting = self.config.get("greeting", "Workflow started")
        context.signal_done({"data": {"message": greeting}, "next_node_id": None})

"""End Node: placeholder for Phase 2 execution logic."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext


class EndNode(Node):
    """Terminates a workflow branch by signaling done with no continuation."""

    node_type: ClassVar[str] = "end_node"
    display_name: ClassVar[str] = "End"
    description: ClassVar[str] = "Terminates a workflow branch"

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = []

    default_config: ClassVar[Dict[str, Any]] = {"message": "Branch completed"}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "message": {
            "type": "string",
            "description": "Completion message recorded in the output log",
            "required": True,
        }
    }

    async def execute(self, context: NodeContext) -> None:
        context.signal_error(NotImplementedError("EndNode arrives in Phase 2"))

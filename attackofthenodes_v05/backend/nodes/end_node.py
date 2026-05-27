"""End Node: terminates a branch and records a completion message."""

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
        message = self.config.get("message", "Branch completed")
        input_value = context.inputs.get("input", "")

        if input_value:
            full = f"[END] {message} (received: {input_value})"
        else:
            full = f"[END] {message}"

        log = list(context.memory_bank.read_persistent("output_log", default=[]))
        log.append(full)
        context.memory_bank.store_persistent("output_log", log)

        context.signal_done({"data": {}, "next_node_id": None})

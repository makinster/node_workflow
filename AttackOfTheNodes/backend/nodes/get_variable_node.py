"""Node that reads a persistent MemoryBank variable."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class GetVariableNode(Node):
    """Reads a named persistent memory value."""

    node_type: ClassVar[str] = "get_variable_node"
    display_name: ClassVar[str] = "Get Variable"
    description: ClassVar[str] = "Reads a value from persistent memory"
    category: ClassVar[str] = NodeCategory.DATA
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "variable_name": "value",
        "default": "",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "variable_name": {"type": "string", "required": True},
        "default": {"type": "string", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        value = context.memory_bank.read_persistent(
            str(self.config.get("variable_name", "value")),
            self.config.get("default", ""),
        )
        context.signal_done({"data": {"default": value}, "next_node_id": None})

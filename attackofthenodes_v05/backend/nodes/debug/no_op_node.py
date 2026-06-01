"""No-op node — does nothing and immediately signals done."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class NoOpNode(Node):
    """Passes execution through without modifying any state."""

    node_type: ClassVar[str] = "no_op_node"
    display_name: ClassVar[str] = "No-Op"
    description: ClassVar[str] = "Does nothing and passes execution through"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    async def execute(self, context: NodeContext) -> None:
        context.signal_done({"data": {"default": context.inputs.get("input", "")}})

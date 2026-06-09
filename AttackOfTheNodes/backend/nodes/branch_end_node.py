"""Merge Beacon node: marks a branch as closed before a merge."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class BranchEndNode(Node):
    """Utility marker that passes input through and exposes a branch to Merge."""

    node_type: ClassVar[str] = "branch_end_node"
    display_name: ClassVar[str] = "Merge Beacon"
    description: ClassVar[str] = "Marks a branch as complete before merge"
    category: ClassVar[str] = NodeCategory.UTILITY
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    async def execute(self, context: NodeContext) -> None:
        context.signal_done({"data": {"default": context.inputs.get("input", "")}})

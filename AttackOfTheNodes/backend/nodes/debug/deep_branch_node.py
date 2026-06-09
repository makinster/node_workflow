"""Deep branch node — spawns a child branch to test max-depth enforcement."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class DeepBranchNode(Node):
    """Spawns a branch on the 'branch' port and continues on 'default'."""

    node_type: ClassVar[str] = "deep_branch_node"
    display_name: ClassVar[str] = "Deep Branch"
    description: ClassVar[str] = "Spawns a child branch to test max-depth enforcement"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default", "branch"]
    default_config: ClassVar[Dict[str, Any]] = {}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    async def execute(self, context: NodeContext) -> None:
        value = context.inputs.get("input", "")
        context.signal_done({
            "branches": [
                {"output_port": "branch", "initial_data": {"input": value}},
            ],
            "data": {"default": value},
        })

"""Deep branch node — spawns a child branch to test max-depth enforcement."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class DeepBranchNode(Node):
    """Spawns one child branch on 'branch'; its own path then ends.

    A node that spawns branches ends its supervisor, so there is no
    continuation port. Loop 'branch' back into this node (or chain several)
    to nest branches until ``max_branch_depth`` refuses the next one.
    """

    node_type: ClassVar[str] = "deep_branch_node"
    display_name: ClassVar[str] = "Deep Branch"
    description: ClassVar[str] = (
        "Spawns one child branch and ends its own path; loop it to test the branch depth limit"
    )
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["branch"]
    spawns_branches: ClassVar[bool] = True
    default_config: ClassVar[Dict[str, Any]] = {}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    async def execute(self, context: NodeContext) -> None:
        value = context.inputs.get("input", "")
        context.signal_done({
            "branches": [
                {"output_port": "branch", "initial_data": {"input": value}},
            ],
            # The child's first node reads the 'branch' port's stored output.
            "data": {"branch": value},
        })

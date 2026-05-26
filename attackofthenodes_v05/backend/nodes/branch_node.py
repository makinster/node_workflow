"""Branch Node: placeholder for Phase 2 execution logic."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext


class BranchNode(Node):
    """Creates parallel execution paths by emitting a branches payload."""

    node_type: ClassVar[str] = "branch_node"
    display_name: ClassVar[str] = "Branch"
    description: ClassVar[str] = "Creates parallel execution paths"

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["path_a", "path_b"]

    default_config: ClassVar[Dict[str, Any]] = {"condition": "always_branch"}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "condition": {
            "type": "string",
            "description": "How to decide which paths to spawn",
            "required": True,
        }
    }

    async def execute(self, context: NodeContext) -> None:
        context.signal_error(NotImplementedError("BranchNode arrives in Phase 2"))

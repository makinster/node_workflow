"""Merge Beacon node: marks a branch as closed before a merge."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class BranchEndNode(Node):
    """Utility marker that passes input through and exposes a branch to Merge."""

    node_type: ClassVar[str] = "branch_end_node"
    display_name: ClassVar[str] = "Merge Beacon"
    description: ClassVar[str] = "Marks a branch as complete before merge"
    # C4: fixed forwarding. The output is the input, so its type follows the
    # input (port_types traces through this node) and the editor shows a
    # read-only summary instead of an option.
    ui_hints: ClassVar[Dict[str, Any]] = {
        "pass_through": "Forwards the branch's payload unchanged to the Merge.",
        "forwarded_input_port": "input",
    }
    category: ClassVar[str] = NodeCategory.UTILITY
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    async def execute(self, context: NodeContext) -> None:
        context.signal_done({"data": {"default": context.inputs.get("input", "")}})

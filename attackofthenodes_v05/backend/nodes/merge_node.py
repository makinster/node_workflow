"""Merge node: waits for sibling branches and emits one selected input."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class MergeNode(Node):
    """Recombines branch paths by forwarding one selected incoming value."""

    node_type: ClassVar[str] = "merge_node"
    display_name: ClassVar[str] = "Merge"
    description: ClassVar[str] = "Waits for branch peers and forwards one input"
    category: ClassVar[str] = NodeCategory.FLOW
    input_ports: ClassVar[List[str]] = ["path_a", "path_b", "path_c", "path_d", "path_e"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "branches_to_close": [],
        "carry_forward_branch_id": "",
        "selected_branch_id": "",
        "selected_input_port": "path_a",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    async def execute(self, context: NodeContext) -> None:
        selected_port = str(self.config.get("selected_input_port") or "").strip()
        if not selected_port:
            selected_port = next(iter(context.inputs.keys()), "path_a")
        try:
            result = await context.wait_for_merge(
                context.node_id,
                context.branch_id,
                selected_port,
                dict(context.inputs),
                0.0,
            )
        except Exception as exc:
            context.signal_error(exc)
            return

        if not result.get("continue"):
            context.signal_done({"terminate_branch": True})
            return

        context.signal_done({"data": {"default": result.get("value", "")}})

"""Merge node: waits for sibling branches and emits one selected input."""

from typing import Any, ClassVar, Dict, List, Optional

from ..branch_paths import ALL_PATH_PORTS, DEFAULT_MERGE_SLOTS, merge_slot_count, path_ports
from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class MergeNode(Node):
    """Recombines branch paths by forwarding one selected incoming value."""

    node_type: ClassVar[str] = "merge_node"
    display_name: ClassVar[str] = "Merge"
    description: ClassVar[str] = "Waits for branch peers and forwards one input"
    category: ClassVar[str] = NodeCategory.FLOW
    # The type's full list; one node has its first ``input_slots`` slots.
    input_ports: ClassVar[List[str]] = list(ALL_PATH_PORTS)
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "branches_to_close": [],
        "carry_forward_branch_id": "",
        "selected_branch_id": "",
        "selected_input_port": "path_a",
        "input_slots": DEFAULT_MERGE_SLOTS,
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    @classmethod
    def resolve_input_ports(cls, config: Optional[Dict[str, Any]]) -> List[str]:
        """Slots ``path_a`` ... up to ``input_slots`` (five unless raised)."""
        return path_ports(merge_slot_count(config))

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

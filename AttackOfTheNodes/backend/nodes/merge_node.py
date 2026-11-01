"""Merge node: collects actual path arrivals and continues once."""

from typing import Any, ClassVar, Dict, List, Optional

from ..branch_paths import ALL_PATH_PORTS, DEFAULT_MERGE_SLOTS, merge_slot_count, path_ports
from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class MergeNode(Node):
    """Collects the delivered slot values after participating paths settle."""

    node_type: ClassVar[str] = "merge_node"
    display_name: ClassVar[str] = "Merge collector"
    description: ClassVar[str] = 'Wait for joining paths, collect their results by input slot, and continue once.'
    category: ClassVar[str] = NodeCategory.FLOW
    # The type's full list; one node has its first ``input_slots`` slots.
    input_ports: ClassVar[List[str]] = list(ALL_PATH_PORTS)
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "branches_to_close": [],
        "carry_forward_branch_id": "",
        "selected_branch_id": "",
        "input_slots": DEFAULT_MERGE_SLOTS,
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}
    error_definitions = [
        {'code': code, 'description': description, 'retryable': False}
        for code, description in (
            ('merge_member_failed', 'A joining path failed before the Merge completed.'),
            ('merge_shape_unknown', 'The graph has not declared a Merge slot shape.'),
            ('merge_shape_invalid', 'Concurrent deliveries contradict a scalar slot declaration.'),
            ('merge_delivery_missing', 'The actual incoming path delivery is unavailable.'),
        )]

    @classmethod
    def resolve_input_ports(cls, config: Optional[Dict[str, Any]]) -> List[str]:
        """Slots ``path_a`` ... up to ``input_slots`` (five unless raised)."""
        return path_ports(merge_slot_count(config))

    async def execute(self, context: NodeContext) -> None:
        try:
            result = await context.wait_for_merge(
                context.node_id,
                context.branch_id,
                next(iter(context.inputs), ''),
                dict(context.inputs),
                0.0,
            )
        except Exception as exc:
            context.signal_error(exc)
            return

        if not result.get("continue"):
            context.signal_done({'arrival_outcome': result.get('arrival_outcome', 'absorbed')})
            return
        data = {}
        if result.get('present', 'value' in result):
            data['default'] = result['value']
            context.memory_bank.store_transient(context.node_id, 'default', result['value'])
        context.signal_done({'data': data})

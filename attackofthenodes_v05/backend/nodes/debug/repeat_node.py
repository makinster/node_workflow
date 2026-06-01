"""Repeat counter node — detects loops by erroring after max visits."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class RepeatCounterNode(Node):
    """Counts per-node visits in persistent memory and errors on the Nth visit."""

    node_type: ClassVar[str] = "repeat_counter_node"
    display_name: ClassVar[str] = "Repeat Counter"
    description: ClassVar[str] = "Signals an error when visited more than max_visits times"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {"max_visits": 3}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "max_visits": {"type": "integer", "label": "Max Visits", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        key = f"_repeat_counter_{context.node_id}"
        count = int(context.memory_bank.read_persistent(key, default=0)) + 1
        context.memory_bank.store_persistent(key, count)
        max_visits = int(self.config.get("max_visits", 3))
        if count >= max_visits:
            context.signal_error(
                RuntimeError(
                    f"RepeatCounterNode '{context.node_id}' has been visited {count} times "
                    f"(max {max_visits}) — possible infinite loop detected"
                )
            )
            return
        context.signal_done({"data": {"default": context.inputs.get("input", ""), "visits": count}})

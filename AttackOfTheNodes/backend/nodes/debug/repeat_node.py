"""Repeat counter node — detects loops by erroring after max visits."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class RepeatCounterNode(Node):
    """Counts per-node visits in persistent memory and errors on the Nth visit."""

    node_type: ClassVar[str] = "repeat_counter_node"
    display_name: ClassVar[str] = "Repeat Counter"
    description: ClassVar[str] = "Signals an error when visited more than max_visits times"
    # C4: fixed forwarding. The output is the input, so its type follows the
    # input (port_types traces through this node) and the editor shows a
    # read-only summary instead of an option.
    ui_hints: ClassVar[Dict[str, Any]] = {
        "pass_through": "Counts visits, then forwards the incoming payload unchanged.",
        "forwarded_input_port": "input", "forwarded_output_ports": ["default"],
    }
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default", "visits"]
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {"name": "Payload", "description": "The incoming payload, forwarded unchanged",
                    "data_type": "any", "required": False, "to": ["downstream"]},
        "visits": {"name": "Visits", "description": "Visits to this node before the error threshold",
                   "data_type": "number", "required": False, "to": ["downstream"]},
    }
    default_config: ClassVar[Dict[str, Any]] = {"max_visits": 3}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "max_visits": {"type": "integer", "label": "Max Visits", "required": True, "min": 1},
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

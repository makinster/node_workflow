"""Counter node — increments a named persistent counter on each visit."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class CounterNode(Node):
    """Increments a named counter in persistent memory and passes input through."""

    node_type: ClassVar[str] = "counter_node"
    display_name: ClassVar[str] = "Counter"
    description: ClassVar[str] = "Increments a persistent counter each time it is visited"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default", "count"]
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {"name": "Payload", "description": "The incoming payload, forwarded unchanged",
                    "data_type": "any", "required": False, "to": ["downstream"]},
        "count": {"name": "Count", "description": "The incremented persistent counter",
                   "data_type": "number", "required": False, "to": ["downstream"]},
    }
    ui_hints = {"pass_through": True, "forwarded_input_port": "input", "forwarded_output_ports": ["default"]}
    default_config: ClassVar[Dict[str, Any]] = {"counter_name": "counter"}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "counter_name": {"type": "string", "label": "Counter Name", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        key = self.config.get("counter_name", "counter") or "counter"
        count = int(context.memory_bank.read_persistent(key, default=0)) + 1
        context.memory_bank.store_persistent(key, count)
        context.signal_done({"data": {"default": context.inputs.get("input", ""), "count": count}})

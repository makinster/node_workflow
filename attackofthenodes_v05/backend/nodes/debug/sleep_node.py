"""Sleep node — pauses execution for a configurable duration."""

import asyncio
from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class SleepNode(Node):
    """Sleeps for a set number of seconds then passes input through."""

    node_type: ClassVar[str] = "sleep_node"
    display_name: ClassVar[str] = "Sleep"
    description: ClassVar[str] = "Pauses execution for a fixed duration"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {"duration": 0.1}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "duration": {
            "type": "float",
            "label": "Duration (seconds)",
            "required": True,
            "min": 0.0,
            "max": 60.0,
        },
    }

    async def execute(self, context: NodeContext) -> None:
        duration = float(self.config.get("duration", 0.1))
        await asyncio.sleep(max(0.0, duration))
        context.signal_done({"data": {"default": context.inputs.get("input", "")}})

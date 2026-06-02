"""Conditional routing node that chooses one path."""

import re
from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class ConditionalNode(Node):
    """Chooses either the true or false output based on a string condition."""

    node_type: ClassVar[str] = "conditional_node"
    display_name: ClassVar[str] = "Conditional"
    description: ClassVar[str] = "Routes to one path based on a condition"
    category: ClassVar[str] = NodeCategory.FLOW
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["true", "false"]
    default_config: ClassVar[Dict[str, Any]] = {
        "condition_type": "contains",
        "left_value_source": "input",
        "variable_name": "",
        "right_value": "",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "condition_type": {"type": "string", "options": ["equals", "not_equals", "contains", "regex"], "required": True},
        "left_value_source": {"type": "string", "options": ["input", "variable"], "required": True},
        "variable_name": {"type": "string", "required": False},
        "right_value": {"type": "string", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        if self.config.get("left_value_source") == "variable":
            left = context.memory_bank.read_persistent(str(self.config.get("variable_name", "")), "")
        else:
            left = context.inputs.get("input", "")
        left_text = str(left)
        right = str(self.config.get("right_value", ""))
        kind = self.config.get("condition_type", "contains")
        if kind == "equals":
            matched = left_text == right
        elif kind == "not_equals":
            matched = left_text != right
        elif kind == "regex":
            matched = re.search(right, left_text) is not None
        else:
            matched = right in left_text
        port = "true" if matched else "false"
        context.signal_done({
            "data": {port: left},
            "output_port": port,
            "next_node_id": None,
        })

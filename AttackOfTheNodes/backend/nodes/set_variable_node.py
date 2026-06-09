"""Node that writes a persistent MemoryBank variable."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class SetVariableNode(Node):
    """Writes a literal or input value to persistent memory."""

    node_type: ClassVar[str] = "set_variable_node"
    display_name: ClassVar[str] = "Set Variable"
    description: ClassVar[str] = "Stores a value in persistent memory"
    category: ClassVar[str] = NodeCategory.DATA
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "variable_name": "value",
        "value_source": "input",
        "value": "",
        "pass_through": True,
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "variable_name": {"type": "string", "required": True},
        "value_source": {"type": "string", "options": ["input", "literal"], "required": True},
        "value": {"type": "string", "required": False},
        "pass_through": {
            "type": "boolean",
            "label": "Dead drop payload",
            "description": "Forward the upstream payload after writing to memory",
            "required": False,
        },
    }

    async def execute(self, context: NodeContext) -> None:
        input_value = context.inputs.get("input", "")
        if self.config.get("value_source", "input") == "literal":
            value = self.config.get("value", "")
        else:
            value = input_value
        name = str(self.config.get("variable_name", "value"))
        context.memory_bank.store_persistent(name, value)
        output_value = input_value if self.config.get("pass_through", True) else value
        context.signal_done({"data": {"default": output_value}, "next_node_id": None})

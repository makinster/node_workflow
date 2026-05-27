"""Node that writes a persistent MemoryBank variable."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext


class SetVariableNode(Node):
    """Writes a literal or input value to persistent memory."""

    node_type: ClassVar[str] = "set_variable_node"
    display_name: ClassVar[str] = "Set Variable"
    description: ClassVar[str] = "Stores a value in persistent memory"
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "variable_name": "value",
        "value_source": "input",
        "value": "",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "variable_name": {"type": "string", "required": True},
        "value_source": {"type": "string", "options": ["input", "literal"], "required": True},
        "value": {"type": "string", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        if self.config.get("value_source", "input") == "literal":
            value = self.config.get("value", "")
        else:
            value = context.inputs.get("input", "")
        name = str(self.config.get("variable_name", "value"))
        context.memory_bank.store_persistent(name, value)
        context.signal_done({"data": {"default": value}, "next_node_id": None})

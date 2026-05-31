"""Debug variable setter — stores a named variable in persistent memory."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class VariableSetterNode(Node):
    """Writes a literal value (or the input) to a named persistent variable."""

    node_type: ClassVar[str] = "variable_setter_node"
    display_name: ClassVar[str] = "Variable Setter"
    description: ClassVar[str] = "Stores a named variable in persistent memory"
    category: ClassVar[str] = NodeCategory.DATA
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "variable_name": "",
        "value": "",
        "pass_through": True,
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "variable_name": {"type": "string", "label": "Variable Name", "required": True},
        "value": {
            "type": "string",
            "label": "Value (empty = use input)",
            "required": False,
        },
        "pass_through": {
            "type": "boolean",
            "label": "Pass input through",
            "required": False,
        },
    }

    async def execute(self, context: NodeContext) -> None:
        name = str(self.config.get("variable_name", "")).strip()
        input_value = context.inputs.get("input", "")
        literal = self.config.get("value", "")
        stored = literal if literal != "" else input_value
        if name:
            context.memory_bank.store_persistent(name, stored)
        output_value = input_value if self.config.get("pass_through", True) else stored
        context.signal_done({"data": {"default": output_value}})

"""Debug variable reader — reads a named variable from persistent memory."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class VariableReaderNode(Node):
    """Reads a named persistent variable and emits its value."""

    node_type: ClassVar[str] = "variable_reader_node"
    display_name: ClassVar[str] = "Variable Reader"
    description: ClassVar[str] = "Reads a named variable from persistent memory"
    category: ClassVar[str] = NodeCategory.DATA
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {"variable_name": "", "default": ""}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "variable_name": {"type": "string", "label": "Variable Name", "required": True},
        "default": {"type": "string", "label": "Default Value", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        name = str(self.config.get("variable_name", "")).strip()
        fallback = self.config.get("default", "")
        value = context.memory_bank.read_persistent(name, default=fallback) if name else fallback
        context.signal_done({"data": {"default": value}})

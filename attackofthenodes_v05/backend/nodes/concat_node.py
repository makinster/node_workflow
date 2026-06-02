"""Node that formats inputs and persistent variables into one string."""

from collections import defaultdict
from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class ConcatNode(Node):
    """Combines input and memory values through a format template."""

    node_type: ClassVar[str] = "concat_node"
    display_name: ClassVar[str] = "Concat"
    description: ClassVar[str] = "Formats input and variables into text"
    category: ClassVar[str] = NodeCategory.DATA
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "template": "{input}",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "template": {"type": "multiline", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        values = defaultdict(str)
        values.update(context.memory_bank.get_state().get("persistent", {}))
        values.update(context.inputs)
        values["input"] = context.inputs.get("input", "")
        try:
            result = str(self.config.get("template", "{input}")).format_map(values)
        except ValueError as exc:
            context.signal_error(ValueError(f"Concat template failed: {exc}"))
            return
        context.signal_done({"data": {"default": result}, "next_node_id": None})

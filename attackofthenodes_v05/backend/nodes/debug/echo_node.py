"""Echo node — passes its input through unchanged."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class EchoNode(Node):
    """Re-emits the incoming value on the default port."""

    node_type: ClassVar[str] = "echo_node"
    display_name: ClassVar[str] = "Echo"
    description: ClassVar[str] = "Passes input through unchanged"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {"label": ""}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "label": {"type": "string", "label": "Label", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        value = context.inputs.get("input", "")
        label = self.config.get("label", "")
        output = f"[{label}] {value}" if label else str(value)
        context.signal_done({"data": {"default": output}})

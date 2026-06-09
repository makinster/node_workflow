"""Dedicated user text input node."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class UserTextInputNode(Node):
    """Pauses execution and emits text supplied by the user."""

    node_type: ClassVar[str] = "user_text_input_node"
    display_name: ClassVar[str] = "User Text Input"
    description: ClassVar[str] = "Prompts the user for text during execution"
    category: ClassVar[str] = NodeCategory.IO
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "prompt": "Enter text:",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "prompt": {"type": "string", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        value = await context.signal_waiting_for_input(str(self.config.get("prompt", "Enter text:")))
        context.signal_done({"data": {"default": value}, "next_node_id": None})

"""Placeholder chat-completion node for pre-v1 API workflow design."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class ChatCompletionNode(Node):
    """Simulates an LLM chat completion without making network calls."""

    node_type: ClassVar[str] = "chat_completion_node"
    display_name: ClassVar[str] = "Chat Completion"
    description: ClassVar[str] = "Simulates an LLM chat response"
    category: ClassVar[str] = NodeCategory.AI
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "model": "gpt-4",
        "system_prompt": "You are helpful.",
        "user_prompt": "{input}",
        "temperature": 0.7,
        "max_tokens": 256,
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "model": {"type": "string", "options": ["gpt-4", "gpt-3.5-turbo", "claude-3"], "required": True},
        "system_prompt": {"type": "multiline", "required": False},
        "user_prompt": {"type": "multiline", "required": True},
        "temperature": {"type": "float", "required": True},
        "max_tokens": {"type": "integer", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        input_value = context.inputs.get("input", "")
        prompt = str(self.config.get("user_prompt", "{input}")).format(input=input_value)
        model = self.config.get("model", "gpt-4")
        response = f"[chat_completion_node executed with model={model}, prompt='{prompt}']"
        context.signal_done({"data": {"default": response}, "next_node_id": None})

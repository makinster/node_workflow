"""Placeholder embedding node for pre-v1 API workflow design."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext


class EmbeddingNode(Node):
    """Simulates text embedding generation."""

    node_type: ClassVar[str] = "embedding_node"
    display_name: ClassVar[str] = "Embedding"
    description: ClassVar[str] = "Simulates creating an embedding vector"
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "model": "text-embedding-3-small",
        "text_field": "input",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "model": {"type": "string", "options": ["text-embedding-3-small", "text-embedding-3-large"], "required": True},
        "text_field": {"type": "string", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        value = str(context.inputs.get(self.config.get("text_field", "input"), context.inputs.get("input", "")))
        seed = sum(ord(char) for char in value) % 1000
        vector = f"[embedding_node executed with model={self.config.get('model')}, vector=[{seed}, {seed + 1}, {seed + 2}]]"
        context.signal_done({"data": {"default": vector}, "next_node_id": None})

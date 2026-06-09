"""Placeholder image-generation node for pre-v1 API workflow design."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class ImageGenerationNode(Node):
    """Simulates image generation without making network calls."""

    node_type: ClassVar[str] = "image_generation_node"
    display_name: ClassVar[str] = "Image Generation"
    description: ClassVar[str] = "Simulates an image generation request"
    category: ClassVar[str] = NodeCategory.AI
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "prompt": "An image of {input}",
        "size": "1024x1024",
        "style": "natural",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "prompt": {"type": "multiline", "required": True},
        "size": {"type": "string", "options": ["512x512", "1024x1024", "1024x1792"], "required": True},
        "style": {"type": "string", "options": ["natural", "vivid"], "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        input_value = context.inputs.get("input", "")
        prompt = str(self.config.get("prompt", "An image of {input}")).format(input=input_value)
        size = self.config.get("size", "1024x1024")
        style = self.config.get("style", "natural")
        result = f"[image_generation_node executed: would generate {size} {style} image with prompt '{prompt}']"
        context.signal_done({"data": {"default": result}, "next_node_id": None})

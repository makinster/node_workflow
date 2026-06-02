"""Local file reader node."""

from pathlib import Path
from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class FileReaderNode(Node):
    """Reads a local text file and emits its contents."""

    node_type: ClassVar[str] = "file_reader_node"
    display_name: ClassVar[str] = "File Reader"
    description: ClassVar[str] = "Reads text from a local file"
    category: ClassVar[str] = NodeCategory.IO
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "file_path": "",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "file_path": {"type": "string", "required": True},
    }

    async def execute(self, context: NodeContext) -> None:
        path = Path(str(self.config.get("file_path", ""))).expanduser()
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError as exc:
            context.signal_error(exc)
            return
        context.signal_done({"data": {"default": contents}, "next_node_id": None})

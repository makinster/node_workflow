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
        "file_path": {"type": "string", "required": True, "path_hint": "file"},
    }

    async def execute(self, context: NodeContext) -> None:
        path = str(self.config.get("file_path", ""))
        try:
            if context.run_session is not None:
                handle = context.run_session.open_file(path, mode="r")
                handle.seek(0)
                contents = handle.read()
            else:
                contents = Path(path).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            context.signal_error(exc)
            return
        context.signal_done({"data": {"default": contents}, "next_node_id": None})

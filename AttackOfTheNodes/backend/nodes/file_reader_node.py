"""Local file reader node."""

import asyncio
from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory
from ..file_paths import normalize_local_path


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
        "file_path": {
            "type": "string", "required": True, "path_hint": "file",
            "normalize_local_path": True,
            "description": "Text file path. Copied quotes are removed; Windows paths are converted under WSL.",
        },
    }

    async def execute(self, context: NodeContext) -> None:
        try:
            path = await asyncio.to_thread(
                normalize_local_path, str(self.config.get("file_path") or "")
            )
            if context.run_session is not None:
                handle = context.run_session.open_file(str(path), mode="r")
                handle.seek(0)
                contents = handle.read()
            else:
                contents = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            context.signal_error(FileNotFoundError(f"File Reader: file not found: {path}. Check the path and make sure the file is available locally."))
            return
        except IsADirectoryError:
            context.signal_error(IsADirectoryError(f"File Reader: {path} is a folder. Select a text file instead."))
            return
        except PermissionError:
            context.signal_error(PermissionError(f"File Reader: permission denied for {path}. Check file access permissions."))
            return
        except UnicodeError:
            context.signal_error(ValueError(f"File Reader: {path} is not readable as UTF-8 text. Save it as UTF-8 text before reading."))
            return
        except ValueError as exc:
            context.signal_error(ValueError(f"File Reader: {exc}"))
            return
        except OSError as exc:
            context.signal_error(exc)
            return
        context.signal_done({"data": {"default": contents}, "next_node_id": None})

"""Read a configured path or typed file reference into a text payload."""
import asyncio
from typing import Any, ClassVar, Dict, List
from ..node_base import Node, NodeContext
from ..node_category import NodeCategory
from ..file_paths import normalize_local_path
from ..file_refs import is_file_reference, reference_path


class FileReaderNode(Node):
    node_type = "file_reader_node"
    display_name = "File Reader"
    description = "Copies UTF-8 file contents into a text payload"
    category = NodeCategory.IO
    primary_family = "Inputs"
    tags = ["File I/O"]
    icon_name = "file-input"
    input_ports = ["input"]
    output_ports = ["default"]
    input_port_metadata = {"input": {"name": "File", "data_type": "file", "required": True,
        "sources": ["upstream", "vault", "configured"], "configured_field": "file_path"}}
    output_port_metadata = {"default": {"name": "File contents", "data_type": "string",
        "required": True, "to": ["downstream", "vault"]}}
    default_config = {"input_source": "Configured", "input_vault_key": "", "file_path": "",
        "transient_output": True, "transient_outputs": [], "vault_write": False,
        "vault_write_key": "", "vault_write_description": ""}
    config_schema = {
        "input_source": {"type": "select", "label": "File source", "options": ["Upstream payload", "Vault", "Configured"], "tab": "Source"},
        "input_vault_key": {"type": "string", "label": "File Vault key", "vault_type": "file", "tab": "Source", "visible_when": {"input_source": "Vault"}},
        "file_path": {"type": "string", "label": "File path", "required": True, "path_hint": "file", "normalize_local_path": True, "tab": "Parameters", "visible_when": {"input_source": "Configured"}},
    }

    async def execute(self, context: NodeContext) -> None:
        path = ""
        try:
            source = self.config.get("input_source", "Configured")
            if source == "Configured":
                raw = self.config.get("file_path", "")
            elif source == "Vault":
                raw = context.memory_bank.read_persistent(str(self.config.get("input_vault_key") or "").strip())
            else:
                raw = context.inputs.get("input")
            if source != "Configured" and not is_file_reference(raw):
                raise ValueError("File source must contain a typed file reference.")
            path = await asyncio.to_thread(normalize_local_path, reference_path(raw))
            def read():
                if context.run_session is not None:
                    handle = context.run_session.open_file(str(path), mode="r")
                    handle.seek(0)
                    return handle.read()
                return path.read_text(encoding="utf-8")
            contents = await asyncio.to_thread(read)
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
        except (ValueError, OSError) as exc:
            context.signal_error(ValueError(f"File Reader: {exc}"))
            return
        if self.config.get("vault_write"):
            key = str(self.config.get("vault_write_key") or "").strip()
            if not key:
                context.signal_error(ValueError("File Reader: enter a Vault output key."))
                return
            context.memory_bank.store_persistent(key, contents, type_tag="string")
        context.signal_done({"data": {"default": contents} if self.config.get("transient_output", True) else {}})

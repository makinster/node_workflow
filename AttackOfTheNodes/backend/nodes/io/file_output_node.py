"""File Write node — write content to a path and emit a typed file reference.

FO1 of docs/FILE_OUTPUT_BUILD_PLAN.md. The written handle registers in
RunSession under the reference key, so downstream nodes (viewer, window
control) resolve the same file by identity (D2/D6) and the handle closes at
run end. The emitted reference is JSON-serializable: the handle itself never
travels through MemoryBank.
"""

import base64
import binascii
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ...file_refs import file_reference, reference_path
from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


# One write mode select, not separate node types (NODE_STANDARDS
# classification: same ports, minor config difference).
MODE_OVERWRITE = "Overwrite"
MODE_APPEND = "Append"
MODE_CREATE_UNIQUE = "Create unique"

_MAX_UNIQUE_ATTEMPTS = 10_000


class FileOutputNode(Node):
    """Write content to a file and emit a typed file reference."""

    node_type: ClassVar[str] = 'file_output_node'
    display_name: ClassVar[str] = 'File Write'
    default_alias: ClassVar[str] = 'File Write'
    description: ClassVar[str] = 'Write content to a file and emit a typed file reference'
    category: ClassVar[str] = NodeCategory.IO
    primary_family: ClassVar[str] = 'Outputs'
    tags: ClassVar[List[str]] = ['File I/O', 'Runtime Resource']
    icon_name: ClassVar[str] = 'file-output'
    color_hint: ClassVar[str] = 'amber'
    group: ClassVar[Optional[str]] = 'File Write'
    selector_section: ClassVar[Optional[str]] = None
    input_ports: ClassVar[List[str]] = ['content', 'file_path']
    output_ports: ClassVar[List[str]] = ['default']
    input_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'content': {'name': 'Content', 'description': 'Data written to the file', 'data_type': 'any', 'required': True, 'sources': ['upstream', 'vault', 'configured']}, 'file_path': {'name': 'File Path', 'description': 'Destination path, or a file reference from upstream/vault', 'data_type': 'file', 'required': True, 'sources': ['upstream', 'vault', 'configured']}}
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'default': {'name': 'File Reference', 'description': 'Typed reference to the written file', 'data_type': 'file', 'required': True, 'to': ['downstream', 'vault'], 'pass_through': True}}
    default_config: ClassVar[Dict[str, Any]] = {'content_source': 'Upstream payload', 'content_vault_key': '', 'content': '', 'file_path_source': 'Configured', 'file_path_vault_key': '', 'file_path': '', 'write_mode': 'Overwrite', 'binary_content': False, 'terminate_branch': False, 'transient_output': True, 'dead_drop_passthrough': False, 'transient_outputs': [], 'vault_write': False, 'vault_write_key': '', 'vault_write_description': ''}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {'content_source': {'type': 'select', 'label': 'Content source', 'options': ['Upstream payload', 'Vault', 'Configured'], 'tab': 'Source', 'section': 'Required Inputs', 'description': 'Data written to the file'}, 'content_vault_key': {'type': 'string', 'label': 'Content Vault key', 'required': False, 'tab': 'Source', 'section': 'Required Inputs', 'vault_type': 'any', 'visible_when': {'content_source': 'Vault'}}, 'content': {'type': 'multiline', 'label': 'Content (E to edit, ESC to finish)', 'tab': 'Parameters', 'visible_when': {'content_source': 'Configured'}}, 'file_path_source': {'type': 'select', 'label': 'File path source', 'options': ['Upstream payload', 'Vault', 'Configured'], 'tab': 'Source', 'section': 'Required Inputs', 'description': 'Destination path, or a file reference from upstream/vault'}, 'file_path_vault_key': {'type': 'string', 'label': 'File path Vault key', 'required': False, 'tab': 'Source', 'section': 'Required Inputs', 'vault_type': 'file', 'visible_when': {'file_path_source': 'Vault'}}, 'file_path': {'type': 'string', 'label': 'File path', 'placeholder': '/path/to/output.md', 'path_hint': 'file', 'required': True, 'tab': 'Parameters', 'visible_when': {'file_path_source': 'Configured'}}, 'write_mode': {'type': 'select', 'label': 'Write mode', 'options': ['Overwrite', 'Append', 'Create unique'], 'description': 'Create unique adds a numeric suffix instead of replacing', 'tab': 'Parameters'}, 'binary_content': {'type': 'boolean', 'label': 'Binary content (Base64)', 'description': 'Decode the content as Base64 and write raw bytes', 'tab': 'Parameters'}, 'terminate_branch': {'type': 'boolean', 'label': 'Terminate branch after completion', 'section': 'Branch', 'description': 'End this branch after the file is written', 'tab': 'Payloads'}}
    ui_hints: ClassVar[Dict[str, Any]] = {}

    async def execute(self, context: NodeContext) -> None:
        content = self._resolve_content(context)
        if content is None:
            context.signal_error(
                RuntimeError("Content is missing — configure a content source")
            )
            return

        raw_path = self._resolve_path(context)
        if not raw_path:
            context.signal_error(
                RuntimeError("File path is empty — configure a file path source")
            )
            return

        binary = bool(self.config.get("binary_content"))
        if binary:
            if isinstance(content, (bytes, bytearray)):
                data: Any = bytes(content)
            else:
                try:
                    data = base64.b64decode(str(content), validate=True)
                except (binascii.Error, ValueError) as exc:
                    context.signal_error(
                        RuntimeError(f"Binary content is not valid Base64: {exc}")
                    )
                    return
        else:
            data = content if isinstance(content, str) else str(content)

        try:
            target = Path(raw_path).expanduser()
            target.parent.mkdir(parents=True, exist_ok=True)
            if self.config.get("write_mode") == MODE_CREATE_UNIQUE:
                target = self._unique_path(target)
            resolved = str(target.resolve())
            handle = self._write(context, resolved, data, binary)
        except OSError as exc:
            context.signal_error(exc)
            return

        ref = file_reference(resolved)
        if context.run_session is not None and handle is not None:
            # The open_file handle is already lifecycle-tracked; registering it
            # under the ref key lets downstream nodes resolve it by identity.
            if context.run_session.get_resource(ref["ref_key"]) is None:
                context.run_session.register_resource(ref["ref_key"], handle)

        if self.config.get("vault_write") and str(self.config.get("vault_write_key") or "").strip():
            context.memory_bank.store_persistent(
                str(self.config["vault_write_key"]).strip(), ref, type_tag="file"
            )

        if self.config.get("dead_drop_passthrough"):
            payload: Any = context.inputs.get("content")
        else:
            payload = ref
        done: Dict[str, Any] = {"data": {"default": payload}}
        if self.config.get("terminate_branch"):
            done["terminate_branch"] = True
        context.signal_done(done)

    def _resolve_content(self, context: NodeContext) -> Optional[Any]:
        source = self.config.get("content_source", "Upstream payload")
        if source == "Vault":
            key = str(self.config.get("content_vault_key") or "").strip()
            return context.memory_bank.read_persistent(key) if key else None
        if source == "Configured":
            return self.config.get("content")
        return context.inputs.get("content")

    def _resolve_path(self, context: NodeContext) -> str:
        source = self.config.get("file_path_source", "Configured")
        if source == "Vault":
            key = str(self.config.get("file_path_vault_key") or "").strip()
            value: Any = context.memory_bank.read_persistent(key) if key else None
        elif source == "Upstream payload":
            value = context.inputs.get("file_path")
        else:
            value = self.config.get("file_path")
        return reference_path(value)

    def _file_mode(self, binary: bool) -> str:
        append = self.config.get("write_mode") == MODE_APPEND
        mode = "a" if append else "w"
        return mode + "b" if binary else mode

    def _write(self, context: NodeContext, resolved: str, data: Any, binary: bool) -> Optional[Any]:
        """Write data; return the RunSession handle when one is in play."""
        mode = self._file_mode(binary)
        if context.run_session is not None:
            handle = context.run_session.open_file(resolved, mode=mode)
            if "w" in mode:
                # A cached "w" handle from an earlier execute sits at its last
                # write position; overwrite means the file holds exactly this
                # content afterwards.
                handle.seek(0)
                handle.truncate()
            handle.write(data)
            handle.flush()
            return handle
        path = Path(resolved)
        if binary:
            if mode == "ab":
                with open(path, "ab") as fh:
                    fh.write(data)
            else:
                path.write_bytes(data)
        elif mode == "a":
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(data)
        else:
            path.write_text(data, encoding="utf-8")
        return None

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        for index in range(1, _MAX_UNIQUE_ATTEMPTS):
            candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
            if not candidate.exists():
                return candidate
        raise OSError(f"No unique variant available for {path}")

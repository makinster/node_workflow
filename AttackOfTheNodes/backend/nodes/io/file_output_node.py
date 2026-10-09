"""File Write node — write content to a path and emit a typed file reference.

FO1/FO5 of docs/FILE_OUTPUT_BUILD_PLAN.md. The written handle registers in
RunSession under the reference key, so downstream nodes (viewer, window
control) resolve the same file by identity (D2/D6) and the handle closes at
run end. The emitted reference is JSON-serializable: the handle itself never
travels through MemoryBank.

With `Open after write` on, the file also opens in its OS-default app at the
configured placement preset (D3) via the platform window manager. Discovery
failure leaves the node successful — opened but unplaced, never an error
(D4). The discovered WindowRef registers under `window:<ref_key>`; its
close-at-run-end hook is opt-in (`Close when run ends`, default off — D12:
windows that outlive the run are unmanaged orphans).
"""

import asyncio
import base64
import binascii
import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ...file_refs import file_reference, is_file_reference, reference_path
from ...file_paths import normalize_local_path
from ...node_base import Node, NodeContext
from ...node_category import NodeCategory
from ...window_manager import PLACE_OS_DEFAULT, PLACEMENT_PRESETS
from .window_support import run_window_manager


logger = logging.getLogger(__name__)


# One write mode select, not separate node types (NODE_STANDARDS
# classification: same ports, minor config difference).
MODE_OVERWRITE = "Overwrite"
MODE_APPEND = "Append"
MODE_PREPEND = "Prepend"
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
    input_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'content': {'name': 'Content', 'description': 'Text or Base64 text written to the file', 'data_type': 'string', 'required': True, 'sources': ['upstream', 'vault', 'configured']}, 'file_path': {'name': 'File Path', 'description': 'Destination path, or a file reference from upstream/vault', 'data_type': 'file', 'required': True, 'sources': ['upstream', 'vault', 'configured']}}
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'default': {'name': 'File Reference', 'description': 'Typed reference to the written file', 'data_type': 'file', 'required': True, 'to': ['downstream', 'vault'], 'pass_through': True}}
    default_config: ClassVar[Dict[str, Any]] = {'content_source': 'Upstream payload', 'content_vault_key': '', 'content': '', 'file_path_source': 'Configured', 'file_path_vault_key': '', 'file_path': '', 'write_mode': 'Overwrite', 'binary_content': False, 'open_after_write': False, 'window_placement': 'OS default', 'close_on_run_end': False, 'transient_output': True, 'dead_drop_passthrough': False, 'transient_outputs': [], 'vault_write': False, 'vault_write_key': '', 'vault_write_description': '', 'interpret_newlines': False}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {'content_source': {'type': 'select', 'label': 'Content source', 'options': ['Upstream payload', 'Vault', 'Configured'], 'tab': 'Source', 'section': 'Required Inputs', 'description': 'Data written to the file'}, 'content_vault_key': {'type': 'string', 'label': 'Content Vault key', 'required': False, 'tab': 'Source', 'section': 'Required Inputs', 'vault_type': 'string', 'visible_when': {'content_source': 'Vault'}}, 'content': {'type': 'multiline', 'label': 'Content (E to edit, ESC to finish)', 'tab': 'Parameters', 'visible_when': {'content_source': 'Configured'}}, 'file_path_source': {'type': 'select', 'label': 'File path source', 'options': ['Upstream payload', 'Vault', 'Configured'], 'tab': 'Source', 'section': 'Required Inputs', 'description': 'Destination path, or a file reference from upstream/vault'}, 'file_path_vault_key': {'type': 'string', 'label': 'File path Vault key', 'required': False, 'tab': 'Source', 'section': 'Required Inputs', 'vault_type': 'file', 'visible_when': {'file_path_source': 'Vault'}}, 'file_path': {'type': 'string', 'label': 'File path', 'normalize_local_path': True, 'placeholder': '/path/to/output.md', 'path_hint': 'file', 'path_mode': 'write', 'required': True, 'tab': 'Parameters', 'visible_when': {'file_path_source': 'Configured'}}, 'write_mode': {'type': 'select', 'label': 'Write mode', 'options': ['Overwrite', 'Append', 'Prepend', 'Create unique'], 'description': 'Append adds at bottom; Prepend adds at top. Text is joined exactly, without automatic separators.', 'tab': 'Parameters'}, 'binary_content': {'type': 'boolean', 'label': 'Binary content (Base64)', 'description': 'Decode the content as Base64 and write raw bytes', 'tab': 'Parameters'}, 'open_after_write': {'type': 'boolean', 'label': 'Open after write', 'description': 'Open the file in its OS-default app (a loop opens the file each iteration)', 'tab': 'Parameters', 'section': 'OS Window'}, 'window_placement': {'type': 'select', 'label': 'Open at', 'options': list(PLACEMENT_PRESETS), 'description': 'Screen placement preset for the opened window', 'tab': 'Parameters', 'section': 'OS Window', 'visible_when': {'open_after_write': True}}, 'close_on_run_end': {'type': 'boolean', 'label': 'Close when run ends', 'description': 'Off keeps the window open for reading after the run', 'tab': 'Parameters', 'section': 'OS Window', 'visible_when': {'open_after_write': True}}, 'interpret_newlines': {'type': 'boolean', 'label': 'Interpret newline escapes (\\n and /n)', 'description': 'Text only: convert these two sequences to newlines; other characters remain literal.', 'tab': 'Parameters', 'visible_when': {'binary_content': False}}}
    ui_hints: ClassVar[Dict[str, Any]] = {'forwarded_input_port': 'content', 'forwarded_input_fallbacks': ['file_path']}

    async def execute(self, context: NodeContext) -> None:
        content = self._resolve_content(context)
        if content is None:
            context.signal_error(
                RuntimeError("Content is missing — configure a content source")
            )
            return

        path_value = self._resolve_path_value(context)
        if self.config.get("file_path_source", "Configured") != "Configured" and not is_file_reference(path_value):
            context.signal_error(ValueError("File Path source must contain a typed file reference."))
            return
        raw_path = reference_path(path_value)
        if not raw_path:
            source = self.config.get("file_path_source", "Configured")
            if source == "Configured":
                detail = "Enter a file path in Parameters."
            elif source == "Vault":
                detail = "Select a File path Vault key containing a typed file reference."
            else:
                detail = "Connect a typed file reference to the File Path input."
            context.signal_error(
                RuntimeError(f"File path is empty ({source}). {detail}")
            )
            return

        binary = bool(self.config.get("binary_content"))
        mode = self.config.get("write_mode", MODE_OVERWRITE)
        if mode not in {MODE_OVERWRITE, MODE_APPEND, MODE_PREPEND, MODE_CREATE_UNIQUE}:
            context.signal_error(ValueError(f"Unsupported write mode: {mode}"))
            return
        if binary and mode == MODE_PREPEND:
            context.signal_error(ValueError("Prepend supports text content only."))
            return
        if binary:
            if isinstance(content, (bytes, bytearray)):
                data: Any = bytes(content)
            else:
                try:
                    if not isinstance(content, str):
                        raise ValueError("expected Base64 text or bytes")
                    data = base64.b64decode(content, validate=True)
                except (binascii.Error, ValueError) as exc:
                    context.signal_error(
                        RuntimeError(f"Binary content is not valid Base64: {exc}")
                    )
                    return
        else:
            if not isinstance(content, str):
                context.signal_error(ValueError("Content must be a text payload (string). Use File Reader to copy file contents."))
                return
            data = content
            if self.config.get("interpret_newlines"):
                data = data.replace("\\n", "\n").replace("/n", "\n")

        try:
            target = await asyncio.to_thread(normalize_local_path, raw_path)
            source_resolved = str(target.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            if self.config.get("write_mode") == MODE_CREATE_UNIQUE:
                target = self._unique_path(target)
            resolved = str(target.resolve())
            if mode == MODE_PREPEND and target.exists():
                # Decode fully before opening a truncating write handle.
                with target.open("r", encoding="utf-8", newline="") as existing:
                    data += existing.read()
            handle = await asyncio.to_thread(self._write, context, resolved, data, binary)
        except (OSError, ValueError) as exc:
            context.signal_error(exc)
            return

        # Keep the source's identity (including its RunSession key) when the
        # operation writes the same file. Create unique may target another file.
        reuse_source = (is_file_reference(path_value) and resolved == source_resolved
                        and isinstance(path_value.get("ref_key"), str)
                        and bool(path_value["ref_key"].strip()))
        ref = (path_value if reuse_source
               else file_reference(resolved))
        if context.run_session is not None and handle is not None:
            # The open_file handle is already lifecycle-tracked; registering it
            # under the ref key lets downstream nodes resolve it by identity.
            if context.run_session.get_resource(ref["ref_key"]) is None:
                context.run_session.register_resource(ref["ref_key"], handle)

        if self.config.get("vault_write") and str(self.config.get("vault_write_key") or "").strip():
            context.memory_bank.store_persistent(
                str(self.config["vault_write_key"]).strip(), ref, type_tag="file"
            )

        if self.config.get("open_after_write"):
            await self._open_window(context, ref)

        if self.config.get("dead_drop_passthrough"):
            payload: Any = context.inputs["content"] if "content" in context.inputs else context.inputs.get("file_path")
        else:
            payload = ref
        done: Dict[str, Any] = {"data": {"default": payload} if (self.config.get("transient_output", True) or self.config.get("dead_drop_passthrough")) else {}}
        context.signal_done(done)

    async def _open_window(self, context: NodeContext, ref: Dict[str, str]) -> None:
        """Open the written file at the configured placement (FO5).

        Discovery failure is a degraded success: the file is open but
        unplaced, no WindowRef registers, and the node stays green (D4).
        """
        manager = run_window_manager(context)
        placement = str(self.config.get("window_placement") or PLACE_OS_DEFAULT)
        try:
            window_ref = await asyncio.to_thread(manager.open_path, ref["path"], placement)
        except OSError as exc:
            logger.warning("Could not open %s: %s", ref["path"], exc)
            return
        if window_ref is None:
            logger.warning(
                "Opened %s but could not identify its window; placement and "
                "window control are unavailable for it",
                ref["path"],
            )
            return
        if context.run_session is None or context.run_session.is_closed:
            return
        if self.config.get("close_on_run_end"):
            context.run_session.register_resource(
                f"window:{ref['ref_key']}",
                window_ref,
                close=lambda handle: manager.close(handle),
            )
        else:
            # D12: without the close hook the window outlives the run as an
            # unmanaged orphan — registered only for same-run control (FO6).
            context.run_session.register_resource(
                f"window:{ref['ref_key']}", window_ref
            )

    def _resolve_content(self, context: NodeContext) -> Optional[Any]:
        source = self.config.get("content_source", "Upstream payload")
        if source == "Vault":
            key = str(self.config.get("content_vault_key") or "").strip()
            return context.memory_bank.read_persistent(key) if key else None
        if source == "Configured":
            return self.config.get("content")
        return context.inputs.get("content")

    def _resolve_path_value(self, context: NodeContext) -> Any:
        source = self.config.get("file_path_source", "Configured")
        if source == "Vault":
            key = str(self.config.get("file_path_vault_key") or "").strip()
            value: Any = context.memory_bank.read_persistent(key) if key else None
        elif source == "Upstream payload":
            value = context.inputs.get("file_path")
        else:
            value = self.config.get("file_path")
        return value

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

"""File Manager node — show a text/md file inside AOTN (FO3).

The node never imports frontend code: it emits FILE_VIEW_REQUESTED with a
JSON payload and any listening frontend pushes the viewer screen. Headless
runs simply have no subscriber, so the event is inert — that is not a node
error (docs/FILE_OUTPUT_BUILD_PLAN.md, D8/FO3).
"""

import asyncio
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ...events import FILE_VIEW_REQUESTED
from ...file_refs import file_reference, is_file_reference, reference_path
from ...file_paths import normalize_local_path
from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


RENDER_MARKDOWN = "markdown"
RENDER_PLAIN = "plain"
_MARKDOWN_SUFFIXES = {".md", ".markdown"}


class FileViewNode(Node):
    """Display a text or Markdown file inside AOTN."""

    node_type: ClassVar[str] = 'file_view_node'
    display_name: ClassVar[str] = 'File Manager'
    default_alias: ClassVar[str] = 'File Manager'
    description: ClassVar[str] = 'Display a text or Markdown file inside AOTN'
    category: ClassVar[str] = NodeCategory.IO
    primary_family: ClassVar[str] = 'Outputs'
    tags: ClassVar[List[str]] = ['File I/O', 'Active Output']
    icon_name: ClassVar[str] = 'file-search'
    color_hint: ClassVar[str] = 'amber'
    group: ClassVar[Optional[str]] = None
    selector_section: ClassVar[Optional[str]] = None
    input_ports: ClassVar[List[str]] = ['file']
    output_ports: ClassVar[List[str]] = ['default']
    input_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'file': {'name': 'File', 'description': 'File reference from upstream/vault, or a configured path', 'data_type': 'file', 'required': True, 'sources': ['upstream', 'vault', 'configured']}}
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'default': {'name': 'File Reference', 'description': "The viewed file's reference, forwarded for further steps", 'data_type': 'file', 'required': True, 'to': ['downstream', 'vault'], 'pass_through': True}}
    default_config: ClassVar[Dict[str, Any]] = {'file_source': 'Upstream payload', 'file_vault_key': '', 'file': '', 'render': 'Auto', 'transient_output': True, 'dead_drop_passthrough': False, 'transient_outputs': [], 'vault_write': False, 'vault_write_key': '', 'vault_write_description': '', 'additional_files': [], 'downstream_file_id': 'primary'}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {'file_source': {'type': 'select', 'label': 'File source', 'options': ['Upstream payload', 'Vault', 'Configured'], 'tab': 'Source', 'section': 'Required Inputs', 'description': 'File reference from upstream/vault, or a configured path'}, 'file_vault_key': {'type': 'string', 'label': 'File Vault key', 'required': False, 'tab': 'Source', 'section': 'Required Inputs', 'vault_type': 'file', 'visible_when': {'file_source': 'Vault'}}, 'file': {'type': 'string', 'label': 'File path', 'normalize_local_path': True, 'placeholder': '/path/to/notes.md', 'path_hint': 'file', 'required': True, 'tab': 'Parameters', 'visible_when': {'file_source': 'Configured'}}, 'render': {'type': 'select', 'label': 'Render as', 'options': ['Auto', 'Markdown', 'Plain text'], 'description': 'Auto picks Markdown for .md/.markdown files', 'tab': 'Parameters'}}
    ui_hints: ClassVar[Dict[str, Any]] = {'forwarded_input_port': 'file'}

    config_schema["additional_files"] = {
        "type": "object_list", "label": "Additional files", "tab": "Parameters",
        "item_schema": {"id": {"type": "string", "label": "Stable id"},
            "path": {"type": "string", "label": "File path", "path_hint": "file", "normalize_local_path": True},
            "vault_key": {"type": "string", "label": "Vault key"},
            "description": {"type": "string", "label": "Description"}},
    }
    config_schema["downstream_file_id"] = {
        "type": "select", "label": "Downstream file", "tab": "Payloads",
        "options": ["primary"], "options_from": "additional_files",
        "options_include": [("Primary file", "primary")],
    }

    async def execute(self, context: NodeContext) -> None:
        try:
            rows = self.config.get("additional_files", [])
            if not isinstance(rows, list):
                raise ValueError("Additional files must be an ordered list.")
            selected = self.config.get("downstream_file_id", "primary")
            primary_key = str(self.config.get("vault_write_key") or "").strip() if self.config.get("vault_write") else ""
            if self.config.get("vault_write") and not primary_key:
                raise ValueError("Enter a Vault key for the primary file output.")
            entries = [("primary", self._resolve_file(context), primary_key)]
            ids = {"primary"}
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError("Each additional file must be a row object.")
                row_id = str(row.get("id") or "").strip()
                if not row_id or row_id in ids:
                    raise ValueError("Each additional file needs a unique nonblank id.")
                ids.add(row_id)
                entries.append((row_id, row.get("path"), str(row.get("vault_key") or "").strip()))
            if selected not in ids:
                raise ValueError("Select an existing file for the downstream payload.")
            keys = set()
            prepared = []
            for row_id, raw, key in entries:
                if row_id != selected and not key:
                    raise ValueError(f"File {row_id}: a Vault key is required for a nonselected file.")
                if key in keys:
                    raise ValueError(f"Duplicate file Vault key: {key}")
                if key:
                    keys.add(key)
                if row_id == "primary" and self.config.get("file_source", "Upstream payload") != "Configured" and not is_file_reference(raw):
                    raise ValueError("File source must contain a typed file reference.")
                path = await asyncio.to_thread(normalize_local_path, reference_path(raw))
                if not await asyncio.to_thread(path.is_file):
                    raise FileNotFoundError(f"File to view was not found: {path}")
                resolved = str(path.resolve())
                ref = raw if is_file_reference(raw) and str(raw.get("ref_key") or "").strip() else file_reference(resolved)
                prepared.append((row_id, ref, key, resolved))
        except (ValueError, OSError) as exc:
            context.signal_error(exc)
            return

        # Validate the complete batch before publishing any Vault value or event.
        for row_id, ref, key, resolved in prepared:
            if key:
                context.memory_bank.store_persistent(key, ref, type_tag="file")
        for row_id, ref, key, resolved in prepared:
            context.emit_event(FILE_VIEW_REQUESTED, {
                "path": resolved, "ref_key": ref["ref_key"],
                "render": self._render_hint(resolved),
            })
        payload = next(ref for row_id, ref, _, _ in prepared if row_id == selected)
        if self.config.get("dead_drop_passthrough"):
            payload = context.inputs.get("file")
        context.signal_done({"data": {"default": payload} if (self.config.get("transient_output", True) or self.config.get("dead_drop_passthrough")) else {}})

    def _resolve_file(self, context: NodeContext) -> Any:
        source = self.config.get("file_source", "Upstream payload")
        if source == "Vault":
            key = str(self.config.get("file_vault_key") or "").strip()
            return context.memory_bank.read_persistent(key) if key else None
        if source == "Configured":
            return self.config.get("file")
        return context.inputs.get("file")

    def _render_hint(self, resolved: str) -> str:
        choice = str(self.config.get("render") or "Auto")
        if choice == "Markdown":
            return RENDER_MARKDOWN
        if choice == "Plain text":
            return RENDER_PLAIN
        suffix = Path(resolved).suffix.lower()
        return RENDER_MARKDOWN if suffix in _MARKDOWN_SUFFIXES else RENDER_PLAIN

"""File Viewer node — show a text/md file inside AOTN (FO3).

The node never imports frontend code: it emits FILE_VIEW_REQUESTED with a
JSON payload and any listening frontend pushes the viewer screen. Headless
runs simply have no subscriber, so the event is inert — that is not a node
error (docs/FILE_OUTPUT_BUILD_PLAN.md, D8/FO3).
"""

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ...events import FILE_VIEW_REQUESTED
from ...file_refs import file_reference, is_file_reference, reference_path
from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


RENDER_MARKDOWN = "markdown"
RENDER_PLAIN = "plain"
_MARKDOWN_SUFFIXES = {".md", ".markdown"}


class FileViewNode(Node):
    """Display a text or Markdown file inside AOTN."""

    node_type: ClassVar[str] = 'file_view_node'
    display_name: ClassVar[str] = 'File Viewer'
    default_alias: ClassVar[str] = 'View File'
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
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'default': {'name': 'File Reference', 'description': "The viewed file's reference, forwarded for further steps", 'data_type': 'file', 'required': True, 'to': ['downstream'], 'pass_through': True}}
    default_config: ClassVar[Dict[str, Any]] = {'file_source': 'Upstream payload', 'file_vault_key': '', 'file': '', 'render': 'Auto', 'terminate_branch': False, 'transient_output': True, 'dead_drop_passthrough': False, 'transient_outputs': []}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {'file_source': {'type': 'select', 'label': 'File source', 'options': ['Upstream payload', 'Vault', 'Configured'], 'tab': 'Source', 'section': 'Required Inputs', 'description': 'File reference from upstream/vault, or a configured path'}, 'file_vault_key': {'type': 'string', 'label': 'File Vault key', 'required': False, 'tab': 'Source', 'section': 'Required Inputs', 'vault_type': 'file', 'visible_when': {'file_source': 'Vault'}}, 'file': {'type': 'string', 'label': 'File path', 'placeholder': '/path/to/notes.md', 'path_hint': 'file', 'required': True, 'tab': 'Parameters', 'visible_when': {'file_source': 'Configured'}}, 'render': {'type': 'select', 'label': 'Render as', 'options': ['Auto', 'Markdown', 'Plain text'], 'description': 'Auto picks Markdown for .md/.markdown files', 'tab': 'Parameters'}, 'terminate_branch': {'type': 'boolean', 'label': 'Terminate branch after completion', 'section': 'Branch', 'description': 'End this branch after the viewer is requested', 'tab': 'Payloads'}}
    ui_hints: ClassVar[Dict[str, Any]] = {}

    async def execute(self, context: NodeContext) -> None:
        raw = self._resolve_file(context)
        path_text = reference_path(raw)
        if not path_text:
            context.signal_error(
                RuntimeError("File is missing — configure a file source")
            )
            return
        path = Path(path_text).expanduser()
        if not path.is_file():
            context.signal_error(
                FileNotFoundError(f"File to view was not found: {path}")
            )
            return
        resolved = str(path.resolve())
        ref = raw if is_file_reference(raw) else file_reference(resolved)

        context.emit_event(
            FILE_VIEW_REQUESTED,
            {
                "path": resolved,
                "ref_key": ref["ref_key"],
                "render": self._render_hint(resolved),
            },
        )

        if self.config.get("dead_drop_passthrough"):
            payload: Any = context.inputs.get("file")
        else:
            payload = ref
        done: Dict[str, Any] = {"data": {"default": payload}}
        if self.config.get("terminate_branch"):
            done["terminate_branch"] = True
        context.signal_done(done)

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

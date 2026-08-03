"""Window Control node — mid-run focus/minimize/close by file identity (FO6).

Targets the OS window that a `file_output_node` opened for the referenced
file (D6: file identity, never app type), resolved from RunSession under
`window:<ref_key>`. Window state is inherently racy against the user, so a
window that was never opened, never discovered (D4), or is already gone is a
**soft error**: a logged warning plus pass-through, never a node error.
"""

import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ...file_refs import is_file_reference, reference_path
from ...node_base import Node, NodeContext
from ...node_category import NodeCategory
from .window_support import run_window_manager


logger = logging.getLogger(__name__)

ACTION_FOCUS = "Focus"
ACTION_MINIMIZE = "Minimize"
ACTION_CLOSE = "Close"


class WindowControlNode(Node):
    """Focus, minimize, or close the window showing a workflow file."""

    node_type: ClassVar[str] = 'window_control_node'
    display_name: ClassVar[str] = 'Window Control'
    default_alias: ClassVar[str] = 'Window Control'
    description: ClassVar[str] = 'Focus, minimize, or close the window showing a workflow file'
    category: ClassVar[str] = NodeCategory.IO
    primary_family: ClassVar[str] = 'Utility'
    tags: ClassVar[List[str]] = ['File I/O', 'Window', 'Utility']
    icon_name: ClassVar[str] = 'app-window'
    color_hint: ClassVar[str] = 'grey'
    group: ClassVar[Optional[str]] = None
    selector_section: ClassVar[Optional[str]] = 'Windows'
    input_ports: ClassVar[List[str]] = ['file']
    output_ports: ClassVar[List[str]] = ['default']
    input_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'file': {'name': 'File', 'description': 'File reference whose window to control', 'data_type': 'file', 'required': True, 'sources': ['upstream', 'vault']}}
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {'default': {'name': 'File Reference', 'description': "The targeted file's reference, forwarded unchanged", 'data_type': 'file', 'required': True, 'to': ['downstream'], 'pass_through': True}}
    default_config: ClassVar[Dict[str, Any]] = {'file_source': 'Upstream payload', 'file_vault_key': '', 'action': 'Focus', 'transient_output': True, 'dead_drop_passthrough': False, 'transient_outputs': []}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {'file_source': {'type': 'select', 'label': 'File source', 'options': ['Upstream payload', 'Vault'], 'tab': 'Source', 'section': 'Required Inputs', 'description': 'File reference whose window to control'}, 'file_vault_key': {'type': 'string', 'label': 'File Vault key', 'required': False, 'tab': 'Source', 'section': 'Required Inputs', 'vault_type': 'file', 'visible_when': {'file_source': 'Vault'}}, 'action': {'type': 'select', 'label': 'Action', 'options': ['Focus', 'Minimize', 'Close'], 'description': "What to do with the file's window", 'tab': 'Parameters'}}
    ui_hints: ClassVar[Dict[str, Any]] = {}

    async def execute(self, context: NodeContext) -> None:
        raw = self._resolve_file(context)
        ref_key = self._reference_key(raw)
        if not ref_key:
            context.signal_error(
                RuntimeError("File is missing — configure a file source")
            )
            return

        window = (
            context.run_session.get_resource(f"window:{ref_key}")
            if context.run_session is not None
            else None
        )
        if window is None:
            # Soft error by design: the window was never opened/discovered,
            # or the run has no session. The workflow keeps moving.
            logger.warning(
                "No open window is registered for %s; skipping %s",
                ref_key,
                self.config.get("action"),
            )
        else:
            action = str(self.config.get("action") or ACTION_FOCUS)
            manager = run_window_manager(context)
            if action == ACTION_CLOSE:
                ok = manager.close(window)
            elif action == ACTION_MINIMIZE:
                ok = manager.minimize(window)
            else:
                ok = manager.focus(window)
            if not ok:
                logger.warning(
                    "%s failed for the window showing %s (already gone?)",
                    action,
                    window.path,
                )

        context.signal_done({"data": {"default": raw}})

    def _resolve_file(self, context: NodeContext) -> Any:
        source = self.config.get("file_source", "Upstream payload")
        if source == "Vault":
            key = str(self.config.get("file_vault_key") or "").strip()
            return context.memory_bank.read_persistent(key) if key else None
        return context.inputs.get("file")

    def _reference_key(self, raw: Any) -> str:
        """The window registration key for a file reference or raw path.

        Raw paths resolve the same way file_output_node resolved them at
        write time, so both spellings target one window identity (D6).
        """
        if is_file_reference(raw):
            return str(raw.get("ref_key") or "").strip()
        path = reference_path(raw)
        if not path:
            return ""
        return f"file:{Path(path).expanduser().resolve()}"

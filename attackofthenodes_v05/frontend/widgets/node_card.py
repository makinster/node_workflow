"""Single-row node renderer for the TUI node list."""

from __future__ import annotations

from typing import Any, Dict

from textual.widgets import Static


STATUS_ICONS = {
    "idle": "◌",
    "running": "▶",
    "done": "✓",
    "errored": "✗",
    "waiting": "⏸",
}


class NodeCard(Static):
    """Render a workflow node as one terminal-friendly row."""

    def __init__(
        self,
        node_id: str,
        node_data: Dict[str, Any],
        status: str = "idle",
    ) -> None:
        super().__init__()
        self.node_id = node_id
        self.node_data = node_data
        self.status = status

    def on_mount(self) -> None:
        self.add_class("node-card")
        self.refresh_card()

    def refresh_card(self) -> None:
        alias = self.node_data.get("alias") or self.node_data.get("type", "node")
        node_type = self.node_data.get("type", "unknown")
        icon = STATUS_ICONS.get(self.status, STATUS_ICONS["idle"])
        breakpoint_marker = " ●" if self.node_data.get("breakpoint") else ""
        self.update(f"{icon}{breakpoint_marker} [{node_type}] {alias}")


class BranchSelectCard(Static):
    """Render the editor branch selector row."""

    def __init__(
        self, branch_node_id: str, active_port: str, active_label: str | None = None
    ) -> None:
        super().__init__()
        self.branch_node_id = branch_node_id
        self.active_port = active_port
        self.active_label = active_label or active_port

    def on_mount(self) -> None:
        self.add_class("branch-select-card")
        self.update(f"  Branch Select: {self.active_label}")

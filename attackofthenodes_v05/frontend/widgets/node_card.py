"""Single-row node renderer for the TUI node list."""

from __future__ import annotations

from typing import Any, Dict

from textual import events
from textual.message import Message
from textual.widgets import Static


STATUS_ICONS = {
    "idle": "◌",
    "running": "▶",
    "done": "✓",
    "errored": "✗",
    "waiting": "⏸",
}

DEPTH_WIDTH = 3
DEPTH_SPACING = "   "
DEPTH_GUTTER = " " * (DEPTH_WIDTH + len(DEPTH_SPACING))


class NodeCard(Static):
    """Render a workflow node as one terminal-friendly row."""

    class Clicked(Message):
        """Posted when a node row is clicked."""

        def __init__(self, node_id: str, chain: int) -> None:
            super().__init__()
            self.node_id = node_id
            self.chain = chain

    def __init__(
        self,
        node_id: str,
        node_data: Dict[str, Any],
        status: str = "idle",
        timing_seconds: float | None = None,
        show_status: bool = True,
        show_id: bool = True,
    ) -> None:
        super().__init__()
        self.node_id = node_id
        self.node_data = node_data
        self.status = status
        self.timing_seconds = timing_seconds
        self.show_status = show_status
        self.show_id = show_id
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("node-card")
        self.refresh_card()

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Clicked(self.node_id, event.chain))
        event.stop()

    def refresh_card(self) -> None:
        alias = self.node_data.get("alias") or self.node_data.get("type", "node")
        node_type = self.node_data.get("type", "unknown")
        if node_type == "branch_end_node":
            self.remove_class("branch-end-open", "branch-end-connected")
            if self.node_data.get("_branch_end_connected_to_merge"):
                self.add_class("branch-end-connected")
            else:
                self.add_class("branch-end-open")
        icon = STATUS_ICONS.get(self.status, STATUS_ICONS["idle"]) if self.show_status else ""
        breakpoint_marker = "● " if self.node_data.get("breakpoint") else ""
        timing = f" ({self._format_timing(self.timing_seconds)})" if self.timing_seconds else ""
        depth = self.node_data.get("_editor_depth")
        id_text = f" ({self.node_id})" if self.show_id else ""
        prefix = f"{icon} " if icon else ""
        main_text = f"{prefix}{breakpoint_marker}{alias}{id_text}{timing}"
        if isinstance(depth, int):
            self.display_text = f"{depth:>{DEPTH_WIDTH}}{DEPTH_SPACING}{main_text}"
        else:
            self.display_text = f"{DEPTH_GUTTER}{main_text}"
        self.update(self.display_text)

    def _format_timing(self, seconds: float | None) -> str:
        if seconds is None:
            return ""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        return f"{seconds:.2f}s"


class BranchSelectCard(Static):
    """Render the editor branch selector row."""

    class Clicked(Message):
        """Posted when a branch selector row is clicked."""

        def __init__(self, branch_node_id: str, active_port: str, chain: int) -> None:
            super().__init__()
            self.branch_node_id = branch_node_id
            self.active_port = active_port
            self.chain = chain

    def __init__(
        self,
        branch_node_id: str,
        active_port: str,
        active_label: str | None = None,
        depth: int | None = None,
    ) -> None:
        super().__init__()
        self.branch_node_id = branch_node_id
        self.active_port = active_port
        self.active_label = active_label or active_port
        self.depth = depth
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("branch-select-card")
        self.display_text = f"{'☛':>{DEPTH_WIDTH}}{DEPTH_SPACING}{self.active_label}"
        self.update(self.display_text)

    def on_click(self, event: events.Click) -> None:
        self.post_message(
            self.Clicked(self.branch_node_id, self.active_port, event.chain)
        )
        event.stop()

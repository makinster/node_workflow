"""Node renderers for the TUI node list."""

from __future__ import annotations

from typing import Any, Dict

from textual import events
from textual.message import Message
from textual.widgets import Static

from frontend.node_io_display import node_display_name


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
IDENTITY_TEXT_WIDTH = 48
UTILITY_TAG = "Utility"


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
        show_identity: bool = False,
    ) -> None:
        super().__init__()
        self.node_id = node_id
        self.node_data = node_data
        self.status = status
        self.timing_seconds = timing_seconds
        self.show_status = show_status
        self.show_id = show_id
        self.show_identity = show_identity
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("node-card")
        self.refresh_card()

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Clicked(self.node_id, event.chain))
        event.stop()

    def refresh_card(self) -> None:
        self._sync_identity_classes()
        alias = node_display_name(self.node_id, self.node_data)
        node_type = self.node_data.get("type", "unknown")
        deleted_overlay = self.node_data.get("_deleted_overlay") or {}
        if node_type == "branch_end_node" and not deleted_overlay:
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
        gutter = (
            f"{depth:>{DEPTH_WIDTH}}{DEPTH_SPACING}"
            if isinstance(depth, int)
            else DEPTH_GUTTER
        )
        if self.show_identity:
            if isinstance(deleted_overlay, dict) and deleted_overlay:
                self.display_text = self._deleted_overlay_display_text(
                    gutter,
                    deleted_overlay,
                )
            else:
                self.display_text = self._identity_display_text(gutter, main_text)
        else:
            self.display_text = f"{gutter}{main_text}"
        self.update(self.display_text)

    def _sync_identity_classes(self) -> None:
        self.set_class(self.show_identity, "node-card-identity")
        family = self._identity_family()
        family_class = f"node-family-{self._class_slug(family)}" if family else ""
        for class_name in [
            "node-family-inputs",
            "node-family-flow-control",
            "node-family-outputs",
            "node-family-complex",
        ]:
            self.set_class(class_name == family_class, class_name)
        self.set_class(UTILITY_TAG in self._identity_tags(), "node-utility")
        self.set_class(bool(self.node_data.get("_deleted_overlay")), "node-deleted")

    def _deleted_overlay_display_text(
        self,
        gutter: str,
        overlay: Dict[str, Any],
    ) -> str:
        alias = str(overlay.get("original_alias") or "").strip()
        node_type = str(
            overlay.get("original_display_name")
            or overlay.get("original_type")
            or ""
        ).strip()
        if alias or node_type:
            label = "Deleted node: "
            if alias and node_type:
                label = f"{label}{alias} ({node_type})"
            else:
                label = f"{label}{alias or node_type}"
        else:
            label = "Deleted node"
        controls = (
            "x delete | z undo | e new node"
            if overlay.get("can_restore")
            else "x delete | e new node"
        )
        line_one = f"{gutter}{self._fit_text(label)}"
        line_two = f"{DEPTH_GUTTER}{self._fit_text(controls)}"
        return f"{line_one}\n{line_two}"

    def _identity_display_text(self, gutter: str, main_text: str) -> str:
        family = self._identity_family()
        tags = self._identity_tags()
        identity_text = family or str(self.node_data.get("type") or "Unknown")
        row_tags = self._row_identity_tags(tags)
        if row_tags:
            identity_text = f"{identity_text} - {', '.join(row_tags)}"
        line_one = f"{gutter}{self._fit_text(main_text)}"
        line_two = f"{DEPTH_GUTTER}{self._fit_text(identity_text)}"
        return f"{line_one}\n{line_two}"

    def _identity_family(self) -> str:
        identity = self.node_data.get("_identity") or {}
        if isinstance(identity, dict):
            return str(
                identity.get("primary_family")
                or identity.get("category")
                or ""
            )
        return ""

    def _identity_tags(self) -> list[str]:
        identity = self.node_data.get("_identity") or {}
        if not isinstance(identity, dict):
            return []
        return [str(tag) for tag in identity.get("tags") or [] if str(tag)]

    def _row_identity_tags(self, tags: list[str]) -> list[str]:
        high_signal = [tag for tag in tags if tag != UTILITY_TAG]
        if high_signal:
            return high_signal[:2]
        return tags[:1]

    def _fit_text(self, text: str) -> str:
        if len(text) <= IDENTITY_TEXT_WIDTH:
            return f"{text:<{IDENTITY_TEXT_WIDTH}}"
        if IDENTITY_TEXT_WIDTH <= 1:
            return text[:IDENTITY_TEXT_WIDTH]
        return f"{text[: IDENTITY_TEXT_WIDTH - 1]}…"

    def _class_slug(self, value: str) -> str:
        return value.lower().replace(" ", "-").replace("/", "")

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


class MergeBeaconSelectCard(Static):
    """Render the editor merge-beacon selector row."""

    class Clicked(Message):
        """Posted when a merge-beacon selector row is clicked."""

        def __init__(self, beacon_node_id: str, chain: int) -> None:
            super().__init__()
            self.beacon_node_id = beacon_node_id
            self.chain = chain

    def __init__(
        self,
        beacon_node_id: str,
        active_label: str | None = None,
        depth: int | None = None,
    ) -> None:
        super().__init__()
        self.beacon_node_id = beacon_node_id
        self.active_label = active_label or "Choose merge"
        self.depth = depth
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("merge-beacon-select-card")
        self.display_text = f"{'☛':>{DEPTH_WIDTH}}{DEPTH_SPACING}{self.active_label}"
        self.update(self.display_text)

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Clicked(self.beacon_node_id, event.chain))
        event.stop()

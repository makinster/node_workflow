"""Node renderers for the TUI node list."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from rich.style import Style
from rich.text import Text
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
FRAME_RIGHT_INSET = 2  # spaces between the closing frame and the panel edge
UTILITY_TAG = "Utility"
FAMILY_FRAMES = {
    "Inputs": ("[", "]"),
    "Outputs": ("<", ">"),
    "Flow Control": ("{", "}"),
    "Utility": ("|", "|"),
    "Complex": ("(", ")"),
}
# Framed-segment row colors: background matches the family hue previously
# used for the font; the font flips to a dark high-contrast color on top.
IDENTITY_ROW_TEXT_COLOR = "#0d1117"
FAMILY_ROW_BACKGROUNDS = {
    "Inputs": "#7ee787",
    "Outputs": "#f2cc60",
    "Flow Control": "#8ab4f8",
    "Utility": "#9aa7b3",
    "Complex": "#c586c0",
}
UTILITY_ROW_BACKGROUND = "#9aa7b3"


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
        # The card has no size yet at mount; re-fit once layout has run so
        # framed rows match the real panel width even if no Resize fires.
        self.call_after_refresh(self.refresh_card)

    def on_resize(self) -> None:
        # Identity rows pad text to the rendered width; re-fit when it changes
        # so bracket columns stay on-screen instead of soft-wrapping.
        self.refresh_card()

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Clicked(self.node_id, event.chain))
        event.stop()

    def refresh_card(self) -> None:
        self._sync_identity_classes()
        alias = node_display_name(self.node_id, self.node_data)
        if (
            self.show_identity
            and not str(self.node_data.get("alias") or "").strip()
            and self.node_data.get("type")
            not in ("branch_end_node", "tombstone_node")
        ):
            alias = "No alias"
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
        self.update(self._card_content())

    def _card_content(self) -> Any:
        """Return the display text, with framed-segment colors when they apply.

        Merge Beacon health rows and deleted-node rows keep their CSS colors;
        family backgrounds only decorate ordinary identity rows.

        Named carefully: `Widget._render_content` is a Textual paint internal,
        and shadowing it makes the widget render blank.
        """
        if not self.is_mounted:
            # Rich content needs the app console; plain text is fine off-app.
            return self.display_text
        if not self.show_identity:
            return self.display_text
        if self.node_data.get("_deleted_overlay"):
            return self.display_text
        if self.node_data.get("type") == "branch_end_node":
            return self.display_text
        colors = self._identity_row_colors()
        if colors is None:
            return self.display_text
        background, foreground = colors
        segment_style = Style(color=foreground, bgcolor=background)
        content = Text(no_wrap=True)
        lines = self.display_text.splitlines()
        for index, line in enumerate(lines):
            styled_line = Text(line, no_wrap=True)
            styled_line.stylize(segment_style, len(DEPTH_GUTTER), len(line))
            content.append(styled_line)
            if index < len(lines) - 1:
                content.append("\n")
        return content

    def _identity_row_colors(self) -> Optional[Tuple[str, str]]:
        if UTILITY_TAG in self._identity_tags():
            return (UTILITY_ROW_BACKGROUND, IDENTITY_ROW_TEXT_COLOR)
        background = FAMILY_ROW_BACKGROUNDS.get(self._identity_family())
        if background is None:
            return None
        return (background, IDENTITY_ROW_TEXT_COLOR)

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
        width = self._identity_text_width()
        line_one = f"{gutter}< {self._fit_text(label, width)} >"
        line_two = f"{DEPTH_GUTTER}< {self._fit_text(controls, width)} >"
        return f"{line_one}\n{line_two}"

    def _identity_display_text(self, gutter: str, main_text: str) -> str:
        family = self._identity_family()
        tags = self._identity_tags()
        left, right = FAMILY_FRAMES.get(family, ("[", "]"))
        identity_text = family or str(self.node_data.get("type") or "Unknown")
        row_tags = self._row_identity_tags(tags)
        if row_tags:
            identity_text = f"{identity_text} - {', '.join(row_tags)}"
        width = self._identity_text_width()
        line_one = f"{gutter}{left} {self._fit_text(main_text, width)} {right}"
        line_two = f"{DEPTH_GUTTER}{left} {self._fit_text(identity_text, width)} {right}"
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

    def _identity_text_width(self) -> int:
        """Width for the framed text column, from the rendered card width.

        Lines are `gutter + frame + space + text + space + frame`; padding to
        more than the actual width makes Textual soft-wrap the line and pushes
        the closing frame onto its own visual row. Unmounted cards (no size
        yet) fall back to the fixed test/default width.
        """
        rendered_width = self.content_size.width
        if rendered_width <= 0:
            return IDENTITY_TEXT_WIDTH
        overhead = len(DEPTH_GUTTER) + 4 + FRAME_RIGHT_INSET
        return max(8, rendered_width - overhead)

    def _fit_text(self, text: str, width: int = IDENTITY_TEXT_WIDTH) -> str:
        if len(text) <= width:
            return f"{text:<{width}}"
        if width <= 1:
            return text[:width]
        return f"{text[: width - 1]}…"

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
        # Two extra spaces line the label up with framed node text above.
        self.display_text = (
            f"{'☛':>{DEPTH_WIDTH}}{DEPTH_SPACING}  {self.active_label}"
        )
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
        # Two extra spaces line the label up with framed node text above.
        self.display_text = (
            f"{'☛':>{DEPTH_WIDTH}}{DEPTH_SPACING}  {self.active_label}"
        )
        self.update(self.display_text)

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Clicked(self.beacon_node_id, event.chain))
        event.stop()

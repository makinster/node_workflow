"""Node renderers for the TUI node list."""

from __future__ import annotations

from typing import Any, Dict, Optional

from rich.style import Style
from rich.text import Text
from textual import events
from textual.message import Message
from textual.widgets import Static

from frontend.node_io_display import node_display_name
from frontend.node_types import (
    BRANCH_END_NODE_TYPE,
    MERGE_NODE_TYPE,
    TOMBSTONE_NODE_TYPE,
)


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
BOX_RIGHT_INSET = 1  # keep the drawn box away from the panel edge
UTILITY_TAG = "Utility"
BOX_HORIZONTAL = "-"
BOX_VERTICAL = "|"
BOX_CORNER = "+"
DOWN_ARROW = "↓"
SELECTED_BACKGROUND = "#1a3a5c"
BRANCH_PATH_PORTS = ("path_a", "path_b", "path_c", "path_d", "path_e")
BRANCH_PATH_PALETTE = (
    "#2dd4bf",  # teal
    "#60a5fa",  # blue
    "#a78bfa",  # violet
    "#f472b6",  # pink
    "#fb7185",  # rose
    "#fbbf24",  # amber
    "#a3e635",  # lime
    "#34d399",  # emerald
    "#22d3ee",  # cyan
    "#c084fc",  # purple
)
BRANCH_PATH_COLORS = {
    port: BRANCH_PATH_PALETTE[index]
    for index, port in enumerate(BRANCH_PATH_PORTS)
}
BRANCH_SELECT_CONNECTOR = "├──"
MERGE_SELECT_CONNECTOR = "└──"
LINE_CHAR = "─"
BRANCH_LABEL_PREFIX = " [ "
BRANCH_LABEL_SUFFIX = " ]"
MERGE_INCOMING_MARKER = "┤"


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
        has_warning: bool = False,
    ) -> None:
        super().__init__()
        self.node_id = node_id
        self.node_data = node_data
        self.status = status
        self.timing_seconds = timing_seconds
        self.show_status = show_status
        self.show_id = show_id
        self.show_identity = show_identity
        self.has_warning = has_warning
        branch_color_key = node_data.get("_editor_branch_color_key")
        branch_port = node_data.get("_editor_branch_port")
        self.gutter_color = branch_path_color(
            str(branch_color_key or branch_port)
        ) if (branch_color_key or branch_port) else None
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("node-card")
        self.refresh_card()
        # The card has no size yet at mount; re-fit once layout has run so
        # framed rows match the real panel width even if no Resize fires.
        self.call_after_refresh(self.refresh_card)

    def on_resize(self) -> None:
        # Identity rows pad text to the rendered width; re-fit when it changes
        # so content stays inside the ASCII border instead of soft-wrapping.
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
            not in (BRANCH_END_NODE_TYPE, TOMBSTONE_NODE_TYPE)
        ):
            alias = "No alias"
        node_type = self.node_data.get("type", "unknown")
        deleted_overlay = self.node_data.get("_deleted_overlay") or {}
        if node_type == BRANCH_END_NODE_TYPE and not deleted_overlay:
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
        warning_badge = "⚠ " if self.has_warning else ""
        main_text = f"{prefix}{warning_badge}{breakpoint_marker}{alias}{id_text}{timing}"
        gutter = depth_number_gutter(depth) if isinstance(depth, int) else DEPTH_GUTTER
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
        if not self.is_mounted:
            return self.display_text
        return selected_box_text(
            self.display_text,
            self.has_class("selected"),
            gutter_symbol_color=self.gutter_color,
        )

    def _sync_identity_classes(self) -> None:
        self.set_class(self.show_identity, "node-card-identity")
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
            label = "Deleted: "
            if alias and node_type:
                label = f"{label}{alias} ({node_type})"
            else:
                label = f"{label}{alias or node_type}"
        else:
            label = "Deleted"
        controls = (
            "x delete | z undo | e new node"
            if overlay.get("can_restore")
            else "x delete | e new node"
        )
        return self._boxed_display_text(gutter, label, controls)

    def _identity_display_text(self, gutter: str, main_text: str) -> str:
        family = self._identity_family()
        tags = self._identity_tags()
        identity_text = family or str(self.node_data.get("type") or "Unknown")
        row_tags = self._row_identity_tags(tags)
        if row_tags:
            identity_text = f"{identity_text} - {', '.join(row_tags)}"
        return self._boxed_display_text(gutter, main_text, identity_text)

    def _boxed_display_text(
        self,
        top_gutter: str,
        line_one_text: str,
        line_two_text: str,
    ) -> str:
        inner_width = self._identity_text_width()
        continuation_gutter = branch_continuation_gutter()
        first_continuation_gutter = (
            num_gutter_marker(MERGE_INCOMING_MARKER)
            if self.node_data.get("type") == MERGE_NODE_TYPE
            else continuation_gutter
        )
        top = f"{top_gutter}{BOX_CORNER}{BOX_HORIZONTAL * inner_width}{BOX_CORNER}"
        line_one = self._boxed_content_line(
            line_one_text,
            inner_width,
            first_continuation_gutter,
        )
        line_two = self._boxed_content_line(line_two_text, inner_width, continuation_gutter)
        bottom = (
            f"{continuation_gutter}{BOX_CORNER}"
            f"{BOX_HORIZONTAL * inner_width}{BOX_CORNER}"
        )
        lines = [top, line_one, line_two, bottom]
        return "\n".join(lines)

    def _boxed_content_line(self, text: str, inner_width: int, gutter: str) -> str:
        if inner_width <= 2:
            return (
                f"{gutter}{BOX_VERTICAL}"
                f"{self._fit_text(text, inner_width)}{BOX_VERTICAL}"
            )
        return (
            f"{gutter}{BOX_VERTICAL} "
            f"{self._fit_text(text, inner_width - 2)} {BOX_VERTICAL}"
        )

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
        """Width for identity text inside the drawn ASCII box.

        Lines are `gutter + border + text + border`. Padding to more than the
        actual content width makes Textual soft-wrap inside the panel.
        Unmounted cards (no size yet) fall back to the fixed test/default
        width.
        """
        rendered_width = self.content_size.width
        if rendered_width <= 0:
            return IDENTITY_TEXT_WIDTH
        overhead = len(DEPTH_GUTTER) + 2 + BOX_RIGHT_INSET
        return max(8, rendered_width - overhead)

    def _fit_text(self, text: str, width: int = IDENTITY_TEXT_WIDTH) -> str:
        if len(text) <= width:
            return f"{text:<{width}}"
        if width <= 1:
            return text[:width]
        return f"{text[: width - 1]}…"

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
        active_color_key: str | None = None,
    ) -> None:
        super().__init__()
        self.branch_node_id = branch_node_id
        self.active_port = active_port
        self.active_label = active_label or active_port
        self.depth = depth
        self.active_color_key = active_color_key or active_port
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("branch-select-card")
        self.refresh_card()
        self.call_after_refresh(self.refresh_card)

    def on_resize(self) -> None:
        self.refresh_card()

    def refresh_card(self) -> None:
        self.display_text = branch_selector_text(
            self.active_label,
            self.active_port,
            self.content_size.width,
            BRANCH_SELECT_CONNECTOR,
        )
        self.update(
            selected_box_text(
                self.display_text,
                self.has_class("selected"),
                foreground=branch_path_color(self.active_color_key),
                foreground_start=0,
            )
        )

    def on_click(self, event: events.Click) -> None:
        self.post_message(
            self.Clicked(self.branch_node_id, self.active_port, event.chain)
        )
        event.stop()


class GapArrowCard(Static):
    """Render a non-selectable insertion gap marker between node rows."""

    def __init__(
        self,
        gutter_marker: str | None = None,
        branch_port: str | None = None,
        branch_color_key: str | None = None,
        output_marker: str | None = None,
    ) -> None:
        super().__init__()
        self.gutter_marker = gutter_marker
        self.gutter_color = branch_path_color(
            branch_color_key or branch_port
        ) if (branch_color_key or branch_port) else None
        self.output_marker = output_marker
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("gap-arrow-card")
        self.refresh_card()
        self.call_after_refresh(self.refresh_card)

    def on_resize(self) -> None:
        self.refresh_card()

    def refresh_card(self) -> None:
        self.display_text = gap_arrow_text(
            self.content_size.width,
            self.gutter_marker,
            self.output_marker,
        )
        self.update(
            selected_box_text(
                self.display_text,
                False,
                gutter_symbol_color=self.gutter_color,
            )
        )


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
        active_port: str | None = None,
        active_color_key: str | None = None,
    ) -> None:
        super().__init__()
        self.beacon_node_id = beacon_node_id
        self.active_label = active_label or "Choose merge"
        self.depth = depth
        self.active_port = active_port or "path_a"
        self.active_color_key = active_color_key or self.active_port
        self.display_text = ""

    def on_mount(self) -> None:
        self.add_class("merge-beacon-select-card")
        self.refresh_card()
        self.call_after_refresh(self.refresh_card)

    def on_resize(self) -> None:
        self.refresh_card()

    def refresh_card(self) -> None:
        active_port = self.active_port
        self.display_text = branch_selector_text(
            self.active_label,
            active_port,
            self.content_size.width,
            MERGE_SELECT_CONNECTOR,
        )
        self.update(
            selected_box_text(
                self.display_text,
                self.has_class("selected"),
                foreground=branch_path_color(self.active_color_key),
                foreground_start=0,
            )
        )

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Clicked(self.beacon_node_id, event.chain))
        event.stop()


def center_gap_marker(box_width: int, marker: str | None = None) -> str:
    """Return a centered down marker for the gap below a node box."""
    return center_text(marker or DOWN_ARROW, box_width)


def center_text(text: str, width: int) -> str:
    """Center text within width using left bias only when unavoidable."""
    width = max(1, width)
    if len(text) >= width:
        return text[:width]
    left = (width - len(text)) // 2
    right = width - len(text) - left
    return f"{' ' * left}{text}{' ' * right}"


def branch_selector_text(
    label: str,
    active_port: str,
    rendered_width: int,
    connector: str,
) -> str:
    """Return a colored branch/merge selector line with a connector gutter."""
    box_width = branch_box_width(rendered_width)
    content = branch_line_label(label, box_width)
    return f"{connector_gutter(connector)}{content}"


def branch_line_label(label: str, box_width: int) -> str:
    """Fill the node column with a line that runs into the branch label."""
    label_text = str(label or "").strip() or "Branch"
    marker = f"{BRANCH_LABEL_PREFIX}{label_text}{BRANCH_LABEL_SUFFIX}"
    if len(marker) >= box_width:
        return marker[:box_width]
    label_start = max(0, (box_width - len(label_text)) // 2)
    line_before = max(0, label_start - len(BRANCH_LABEL_PREFIX))
    line_after = box_width - line_before - len(marker)
    return f"{LINE_CHAR * line_before}{marker}{' ' * line_after}"


def branch_box_width(rendered_width: int) -> int:
    """Width of the node-column branch line, excluding the depth gutter."""
    box_width = (
        IDENTITY_TEXT_WIDTH + 2
        if rendered_width <= 0
        else max(10, rendered_width - len(DEPTH_GUTTER) - BOX_RIGHT_INSET)
    )
    return box_width


def gap_arrow_text(
    rendered_width: int,
    gutter_marker: str | None = None,
    output_marker: str | None = None,
) -> str:
    """Center a non-focusable down arrow under the node box."""
    box_width = branch_box_width(rendered_width)
    gutter = (
        num_gutter_marker(gutter_marker)
        if gutter_marker
        else branch_continuation_gutter()
    )
    return f"{gutter}{center_gap_marker(box_width, output_marker)}"


def depth_number_gutter(depth: int) -> str:
    """Gutter for numbered rows."""
    return f"{depth:<{DEPTH_WIDTH}}{DEPTH_SPACING}"


def branch_continuation_gutter() -> str:
    """Gutter used below a node's numbered top row."""
    return num_gutter_marker(BOX_VERTICAL)


def num_gutter_marker(marker: str) -> str:
    """Place a non-number marker in the visual connector column."""
    return f"{marker:<{len(DEPTH_GUTTER)}}"


def connector_gutter(connector: str) -> str:
    """Gutter used by branch/merge selector connector rows."""
    stem = str(connector or LINE_CHAR)[:1]
    tail = str(connector or "")[1:]
    tail_width = max(0, len(DEPTH_GUTTER) - len(stem))
    extended_tail = (tail + (LINE_CHAR * tail_width))[:tail_width]
    return f"{stem}{extended_tail}"


def branch_path_color(port: str) -> str:
    """Return the configured display color for a branch output port."""
    key = str(port)
    if key in BRANCH_PATH_COLORS:
        return BRANCH_PATH_COLORS[key]
    index = branch_path_palette_index(key)
    return BRANCH_PATH_PALETTE[index]


def branch_path_color_key(branch_index: int, port: str) -> str:
    """Return a display-only color key for a branch node output path."""
    port_index = branch_path_port_index(port)
    return f"branch:{branch_index}:{port_index}"


def branch_path_palette_index(key: str) -> int:
    """Resolve a branch color key to a cycling palette index."""
    pieces = str(key).split(":")
    if len(pieces) == 3 and pieces[0] == "branch":
        try:
            branch_index = int(pieces[1])
            port_index = int(pieces[2])
        except ValueError:
            return 0
        return (
            branch_index * len(BRANCH_PATH_PORTS) + port_index
        ) % len(BRANCH_PATH_PALETTE)
    return 0


def branch_path_port_index(port: str) -> int:
    """Return a stable branch-port position for palette assignment."""
    key = str(port)
    if key in BRANCH_PATH_PORTS:
        return BRANCH_PATH_PORTS.index(key)
    return 0


def selected_box_text(
    display_text: str,
    selected: bool,
    foreground: str | None = None,
    foreground_start: int | None = None,
    gutter_symbol_color: str | None = None,
    bold_foreground_chars: set[str] | None = None,
) -> str | Text:
    """Highlight only the node/jump box area, leaving the depth gutter plain."""
    if not selected and not foreground and not gutter_symbol_color:
        return display_text
    content = Text(no_wrap=True)
    foreground_style = Style(color=foreground) if foreground else None
    gutter_style = (
        Style(color=gutter_symbol_color, bold=True)
        if gutter_symbol_color
        else None
    )
    selected_style = Style(bgcolor=SELECTED_BACKGROUND) if selected else None
    color_start = len(DEPTH_GUTTER) if foreground_start is None else foreground_start
    lines = display_text.splitlines()
    for index, line in enumerate(lines):
        styled_line = Text(line, no_wrap=True)
        if foreground_style:
            styled_line.stylize(foreground_style, color_start, len(line))
            if bold_foreground_chars:
                bold_style = Style(color=foreground, bold=True)
                for offset, char in enumerate(line):
                    if offset >= color_start and char in bold_foreground_chars:
                        styled_line.stylize(bold_style, offset, offset + 1)
        if gutter_style:
            for offset, char in enumerate(line[:DEPTH_WIDTH]):
                if char.strip():
                    styled_line.stylize(gutter_style, offset, offset + 1)
        if selected_style:
            styled_line.stylize(selected_style, len(DEPTH_GUTTER), len(line))
        content.append(styled_line)
        if index < len(lines) - 1:
            content.append("\n")
    return content

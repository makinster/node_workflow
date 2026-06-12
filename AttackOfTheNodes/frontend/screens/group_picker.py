"""Group picker modal: second-level node selection for a node group.

A single generic modal serves every group. It is parameterized by group name
and member metadata, shows one member per line with the highlighted member's
description below, and returns the chosen node type. `ESC` pops only this
modal so the user lands back in the main selector.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static


class GroupPickerScreen(ModalScreen):
    """Pick one node type from a group's members."""

    BINDINGS = [
        ("escape", "cancel", "Back"),
        Binding("ctrl+q", "cancel", "Back", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        ("enter", "choose", "Add"),
        Binding("e", "choose", "Add", priority=True),
    ]

    def __init__(self, group_name: str, members: List[Dict[str, Any]]) -> None:
        super().__init__()
        self.group_name = group_name
        self.members = list(members)

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label(self.group_name, classes="modal-title")
            yield ListView(id="group-member-list")
            yield Static(
                "W/S navigate  E add  ESC back to selector",
                classes="modal-help",
            )

    def on_mount(self) -> None:
        list_view = self.query_one("#group-member-list", ListView)
        for member in self.members:
            display = member["display_name"]
            description = str(member.get("description") or "").strip() or "No description"
            if len(description) > 76:
                description = f"{description[:75]}…"
            list_view.append(
                ListItem(
                    Static(f"\\[ {display} ]\n- {description}", classes="group-member-row")
                )
            )
        if self.members:
            list_view.index = 0
        self.app.set_focus(list_view)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "group-member-list":
            self._choose(event.list_view.index)

    def action_cursor_up(self) -> None:
        self._move(-1)

    def action_cursor_down(self) -> None:
        self._move(1)

    def action_choose(self) -> None:
        list_view = self.query_one("#group-member-list", ListView)
        self._choose(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _move(self, delta: int) -> None:
        if not self.members:
            return
        list_view = self.query_one("#group-member-list", ListView)
        current = list_view.index if list_view.index is not None else 0
        list_view.index = max(0, min(len(self.members) - 1, current + delta))

    def _choose(self, index: Optional[int]) -> None:
        if index is None or index < 0 or index >= len(self.members):
            return
        self.dismiss(self.members[index]["type"])

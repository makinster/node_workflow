"""Merge Beacon selector modal for jumping to merge nodes."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static

from frontend.widgets.list_navigation import focus_list, move_list_highlight


class MergeBeaconSelectorScreen(ModalScreen):
    """Select a merge node to jump to from a Merge Beacon row."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        ("enter", "choose", "Choose"),
        Binding("e", "choose", "Choose", priority=True),
    ]

    def __init__(
        self,
        beacon_node_id: str,
        options: list[dict[str, str]],
        active_merge_id: str | None = None,
    ) -> None:
        super().__init__()
        self.beacon_node_id = beacon_node_id
        self.options = list(options)
        self.active_merge_id = active_merge_id or ""

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Merge Beacon", classes="modal-title")
            yield ListView(id="merge-beacon-list")
            yield Static("↑↓ navigate  ENTER select  ESC close", classes="modal-help")
            yield Button("Cancel", id="cancel-merge-beacon", variant="default")

    def on_mount(self) -> None:
        list_view = self.query_one("#merge-beacon-list", ListView)
        for option in self.options:
            marker = "*" if option["merge_node_id"] == self.active_merge_id else " "
            list_view.append(ListItem(Static(f"{marker} {option['label']}")))
        active_index = self._active_index()
        if active_index is not None:
            list_view.index = active_index
        focus_list(self.app, list_view, len(self.options))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_selected(event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-merge-beacon":
            self.action_cancel()

    def action_choose(self) -> None:
        list_view = self.query_one("#merge-beacon-list", ListView)
        self._dismiss_selected(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._move_selection(1)

    def _active_index(self) -> int | None:
        for index, option in enumerate(self.options):
            if option["merge_node_id"] == self.active_merge_id:
                return index
        return None

    def _dismiss_selected(self, index: int | None) -> None:
        if index is None or index < 0 or index >= len(self.options):
            return
        self.dismiss(
            {
                "beacon_node_id": self.beacon_node_id,
                "merge_node_id": self.options[index]["merge_node_id"],
            }
        )

    def _move_selection(self, delta: int) -> None:
        list_view = self.query_one("#merge-beacon-list", ListView)
        move_list_highlight(self.app, list_view, len(self.options), delta)

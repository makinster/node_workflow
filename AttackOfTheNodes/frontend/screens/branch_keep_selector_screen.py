"""Branch keep selector modal — choose which branch to retain on tombstone deletion."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static

from frontend.widgets.list_navigation import focus_list, move_list_highlight


class BranchKeepSelectorScreen(ModalScreen):
    """Pick which branch to keep when permanently deleting a branch-node tombstone.

    All other branches and their downstream nodes will be pruned.
    Dismisses with ``{"kept_port": <port_name>}`` or ``None`` on cancel.
    """

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
        branch_node_id: str,
        branch_label: str,
        ports: list[str],
        port_labels: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.branch_node_id = branch_node_id
        self.branch_label = branch_label
        self.ports = ports
        self.port_labels = port_labels or {}

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label(
                f"Keep which branch of: {self.branch_label}?",
                classes="modal-title",
            )
            yield Static(
                "Other branches and their nodes will be permanently deleted.",
                classes="modal-help",
            )
            yield ListView(id="branch-keep-list")
            yield Static("↑↓ navigate  ENTER keep  ESC cancel", classes="modal-help")
            yield Button("Cancel", id="cancel-branch-keep", variant="default")

    def on_mount(self) -> None:
        list_view = self.query_one("#branch-keep-list", ListView)
        for port in self.ports:
            label = self.port_labels.get(port, port)
            list_view.append(ListItem(Static(label)))
        focus_list(self.app, list_view, len(self.ports))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_selected(event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-branch-keep":
            self.action_cancel()

    def action_choose(self) -> None:
        list_view = self.query_one("#branch-keep-list", ListView)
        self._dismiss_selected(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._move_selection(1)

    def _dismiss_selected(self, index: int | None) -> None:
        if index is None or index < 0 or index >= len(self.ports):
            return
        self.dismiss({"kept_port": self.ports[index]})

    def _move_selection(self, delta: int) -> None:
        list_view = self.query_one("#branch-keep-list", ListView)
        move_list_highlight(self.app, list_view, len(self.ports), delta)

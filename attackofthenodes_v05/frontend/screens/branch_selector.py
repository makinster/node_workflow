"""Branch selector modal for choosing the visible editor branch."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static


class BranchSelectorScreen(ModalScreen):
    """Select which output branch is visible below a branch node."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("q", "cancel", "Cancel"),
        ("w", "cursor_up", "Up"),
        ("s", "cursor_down", "Down"),
        ("enter", "choose", "Choose"),
        ("e", "choose", "Choose"),
        ("d", "choose", "Choose"),
    ]

    def __init__(
        self,
        branch_node_id: str,
        branch_node_label: str,
        output_ports: list[str],
        active_port: str,
        port_labels: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.branch_node_id = branch_node_id
        self.branch_node_label = branch_node_label
        self.output_ports = output_ports
        self.active_port = active_port
        self.port_labels = port_labels or {}

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label(f"Branch Select: {self.branch_node_label}", classes="modal-title")
            yield ListView(id="branch-port-list")
            yield Static("↑↓ navigate  ENTER select  ESC close", classes="modal-help")
            yield Button("Cancel", id="cancel-branch-select", variant="default")

    def on_mount(self) -> None:
        list_view = self.query_one("#branch-port-list", ListView)
        for port in self.output_ports:
            marker = "*" if port == self.active_port else " "
            label = self.port_labels.get(port, port)
            list_view.append(ListItem(Static(f"{marker} {label}")))
        if self.active_port in self.output_ports:
            list_view.index = self.output_ports.index(self.active_port)
        list_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_selected(event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-branch-select":
            self.action_cancel()

    def action_choose(self) -> None:
        list_view = self.query_one("#branch-port-list", ListView)
        self._dismiss_selected(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._move_selection(1)

    def _dismiss_selected(self, index: int | None) -> None:
        if index is None or index < 0 or index >= len(self.output_ports):
            return
        self.dismiss(
            {
                "branch_node_id": self.branch_node_id,
                "branch_port": self.output_ports[index],
            }
        )

    def _move_selection(self, delta: int) -> None:
        if not self.output_ports:
            return
        list_view = self.query_one("#branch-port-list", ListView)
        current = list_view.index if list_view.index is not None else 0
        list_view.index = max(0, min(len(self.output_ports) - 1, current + delta))
        list_view.focus()

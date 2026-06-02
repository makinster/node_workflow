"""Memory viewer modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label

from frontend.widgets.command_navigation import activate_command_widget, focus_command_widget


class MemoryViewerScreen(ModalScreen):
    """Inspect persistent variables and transient port data."""

    BINDINGS = [
        ("escape", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("e", "activate_focused", "Activate", priority=True),
        Binding("enter", "activate_focused", "Activate", priority=True),
    ]

    def __init__(self, memory_bank) -> None:
        super().__init__()
        self.memory_bank = memory_bank

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Memory", classes="modal-title")
            yield DataTable(id="memory-table")
            yield Button("Close", id="close-memory", variant="default")

    def on_mount(self) -> None:
        table = self.query_one("#memory-table", DataTable)
        table.add_columns("Store", "Key", "Value")
        state = self.memory_bank.get_state()
        self._add_rows(table, "persistent", state.get("persistent", {}))
        self._add_rows(table, "transient", state.get("transient", {}))
        focus_command_widget(self, table)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-memory":
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)

    def action_activate_focused(self) -> None:
        activate_command_widget(self.app.focused)

    def action_cursor_up(self) -> None:
        focused = self.app.focused
        table = self.query_one("#memory-table", DataTable)
        if focused is table:
            table.action_cursor_up()
            return
        focus_command_widget(self, table)

    def action_cursor_down(self) -> None:
        focused = self.app.focused
        table = self.query_one("#memory-table", DataTable)
        if focused is table:
            table.action_cursor_down()
            return
        focus_command_widget(self, self.query_one("#close-memory", Button))

    def _add_rows(self, table: DataTable, store: str, values: dict) -> None:
        if not values:
            table.add_row(store, "-", "-")
            return
        for key, value in values.items():
            table.add_row(store, str(key), str(value))

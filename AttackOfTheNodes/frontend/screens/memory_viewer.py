"""Memory viewer modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label

from frontend.node_io_display import node_display_name
from frontend.widgets.command_navigation import activate_command_widget, focus_command_widget


TRANSIENT_SEPARATOR = "__"


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

    def __init__(self, memory_bank, workflow_map=None) -> None:
        super().__init__()
        self.memory_bank = memory_bank
        # Optional frontend display context: lets transient keys like
        # ``node_b4369251__default`` render as ``<alias> · <port>`` instead of
        # surfacing raw generated node ids in the table.
        self.workflow_map = workflow_map

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="fill-modal"):
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
            display_key = (
                self._friendly_transient_key(str(key))
                if store == "transient"
                else str(key)
            )
            table.add_row(store, display_key, str(value))

    def _friendly_transient_key(self, key: str) -> str:
        """Render ``node_id__port`` as ``<alias> · <port>`` when context allows.

        Falls back to the raw key when no workflow context is available or the
        producing node can no longer be resolved.
        """
        if self.workflow_map is None:
            return key
        node_id, separator, port = key.partition(TRANSIENT_SEPARATOR)
        if not separator:
            return key
        node_data = self.workflow_map.get_node_data(node_id)
        if not node_data:
            return key
        alias = node_display_name(node_id, node_data)
        return f"{alias} · {port}"

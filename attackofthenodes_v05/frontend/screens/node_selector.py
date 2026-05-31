"""Node selector modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static


class NodeSelectorScreen(ModalScreen):
    """Add-node modal, backed entirely by NodeFactory metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("/", "focus_filter", "Filter"),
        Binding("tab", "focus_node_list", "List", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        ("enter", "choose", "Add"),
        ("e", "choose", "Add"),
        ("d", "choose", "Add"),
    ]

    def __init__(self, factory) -> None:
        super().__init__()
        self.factory = factory
        self._all_nodes: list[Dict[str, Any]] = []
        self._visible_nodes: list[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Add Node", classes="modal-title")
            yield Input(placeholder="Filter nodes", id="node-filter")
            yield ListView(id="node-type-list")
            yield Static("↑↓ navigate  ENTER add  / filter  ESC close", classes="modal-help")
            yield Button("Cancel", id="cancel-node-select", variant="default")

    def on_mount(self) -> None:
        self._all_nodes = self.factory.get_node_types_metadata()
        self._apply_filter("")
        self.query_one("#node-filter", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "node-filter":
            self._apply_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "node-filter":
            self._dismiss_selected(0)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_selected(event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-node-select":
            self.dismiss(None)

    def action_focus_filter(self) -> None:
        self.query_one("#node-filter", Input).focus()

    def action_focus_node_list(self) -> None:
        self._focus_node_list()

    def action_choose(self) -> None:
        list_view = self.query_one("#node-type-list", ListView)
        self._dismiss_selected(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._move_selection(1)

    def _apply_filter(self, query: str) -> None:
        query = query.strip().lower()
        if query:
            self._visible_nodes = [
                node
                for node in self._all_nodes
                if query in node["type"].lower()
                or query in node["display_name"].lower()
                or query in node.get("description", "").lower()
            ]
        else:
            self._visible_nodes = list(self._all_nodes)

        list_view = self.query_one("#node-type-list", ListView)
        list_view.clear()
        for node in self._visible_nodes:
            display = node["display_name"]
            description = node.get("description", "")
            list_view.append(ListItem(Static(f"{display:<18} {description}")))
        if not self._visible_nodes:
            list_view.append(ListItem(Static("No matching nodes")))
        else:
            list_view.index = 0

    def _focus_node_list(self) -> None:
        list_view = self.query_one("#node-type-list", ListView)
        if self._visible_nodes and list_view.index is None:
            list_view.index = 0
        elif self._visible_nodes:
            list_view.index = max(0, min(list_view.index or 0, len(self._visible_nodes) - 1))
        list_view.focus()

    def _dismiss_selected(self, index: Optional[int]) -> None:
        if index is None or index < 0 or index >= len(self._visible_nodes):
            return
        self.dismiss(self._visible_nodes[index]["type"])

    def _move_selection(self, delta: int) -> None:
        if not self._visible_nodes:
            return
        list_view = self.query_one("#node-type-list", ListView)
        current = list_view.index if list_view.index is not None else 0
        list_view.index = max(0, min(len(self._visible_nodes) - 1, current + delta))
        list_view.focus()

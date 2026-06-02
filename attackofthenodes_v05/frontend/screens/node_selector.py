"""Node selector modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static

from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_navigation import focus_command_widget
from frontend.widgets.list_navigation import (
    ensure_list_highlight,
    focus_list,
    move_list_highlight,
)


class NodeSelectorScreen(ModalScreen):
    """Add-node modal, backed entirely by NodeFactory metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
        ("/", "focus_filter", "Filter"),
        Binding("tab", "focus_node_list", "List", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        ("enter", "choose", "Add"),
        Binding("e", "choose", "Add", priority=True),
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
            yield CommandInput(
                placeholder="Filter nodes",
                id="node-filter",
                auto_edit_on_focus=True,
            )
            yield ListView(id="node-type-list")
            yield Static("W/S navigate  E activate/add  / filter  ESC close", classes="modal-help")
            yield Button("Cancel", id="cancel-node-select", variant="default")

    def on_mount(self) -> None:
        self._all_nodes = self.factory.get_node_types_metadata()
        self._apply_filter("")
        self._focus_node_list()
        self.call_after_refresh(self._focus_node_list)
        self.set_timer(0.01, self._focus_node_list)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        focused = self.focused
        if isinstance(focused, CommandInput) and focused.editing:
            if action in {"cursor_up", "cursor_down", "choose", "focus_filter", "focus_node_list", "cancel"}:
                return False
        return True

    def on_input_changed(self, event: CommandInput.Changed) -> None:
        if event.input.id == "node-filter":
            self._apply_filter(event.value)

    def on_input_submitted(self, event: CommandInput.Submitted) -> None:
        if event.input.id == "node-filter":
            event.input.end_edit()
            self._focus_node_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_selected(event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-node-select":
            self.dismiss(None)

    def action_focus_filter(self) -> None:
        focus_command_widget(self, self.query_one("#node-filter", CommandInput))

    def action_focus_node_list(self) -> None:
        self._focus_node_list()

    def action_choose(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput):
            focused.begin_edit()
            return
        list_view = self.query_one("#node-type-list", ListView)
        self._dismiss_selected(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput):
            return
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput):
            self._focus_node_list()
            return
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
        focus_list(self.app, list_view, len(self._visible_nodes))

    def _dismiss_selected(self, index: Optional[int]) -> None:
        if index is None or index < 0 or index >= len(self._visible_nodes):
            return
        self.dismiss(self._visible_nodes[index]["type"])

    def _move_selection(self, delta: int) -> None:
        if not self._visible_nodes:
            return
        list_view = self.query_one("#node-type-list", ListView)
        ensure_list_highlight(list_view, len(self._visible_nodes))
        current = list_view.index if list_view.index is not None else 0
        if delta < 0 and current == 0:
            self.action_focus_filter()
            return
        move_list_highlight(self.app, list_view, len(self._visible_nodes), delta)

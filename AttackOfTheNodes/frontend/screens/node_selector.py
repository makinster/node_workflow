"""Node selector modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label, ListItem, ListView, Static

from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_navigation import focus_command_widget
from frontend.widgets.list_navigation import (
    ensure_list_highlight,
    focus_list,
    move_list_highlight,
)


FAMILIES = ["Inputs", "Flow Control", "Outputs", "Complex"]
EDITOR_ONLY_NODE_TYPES = {"tombstone_node"}
SUBCATEGORY_ORDER = [
    "Triggered",
    "File I/O",
    "Internet",
    "AI",
    "Passive Output",
    "Active Output",
    "Parallel",
    "Conditional",
    "Runtime Resource",
    "Utility",
]


class NodeSelectorScreen(ModalScreen):
    """Add-node modal, backed entirely by NodeFactory metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
        ("/", "focus_filter", "Filter"),
        Binding("tab", "focus_node_list", "List", priority=True),
        Binding("a", "previous_family", "Previous family", priority=True),
        Binding("d", "next_family", "Next family", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        ("enter", "choose", "Add"),
        Binding("e", "choose", "Add", priority=True),
    ]

    def __init__(self, factory) -> None:
        super().__init__()
        self.factory = factory
        self._all_nodes: list[Dict[str, Any]] = []
        self._visible_nodes: list[Dict[str, Any]] = []
        self._active_family = FAMILIES[0]
        self._selected_subcategories: set[str] = set()
        self._tag_checkbox_ids = {
            tag: f"node-subcategory-{self._slug(tag)}"
            for tag in SUBCATEGORY_ORDER
        }
        self._checkbox_id_tags = {
            checkbox_id: tag
            for tag, checkbox_id in self._tag_checkbox_ids.items()
        }

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Add Node", classes="modal-title")
            with Horizontal(id="node-family-tabs"):
                for family in FAMILIES:
                    yield Button(
                        family,
                        id=f"node-family-{self._slug(family)}",
                        variant="primary" if family == self._active_family else "default",
                    )
            yield CommandInput(
                placeholder="Filter nodes",
                id="node-filter",
                auto_edit_on_focus=False,
            )
            with Vertical(id="node-subcategory-filters"):
                for tag in SUBCATEGORY_ORDER:
                    yield Checkbox(tag, value=False, id=self._tag_checkbox_ids[tag])
            yield ListView(id="node-type-list")
            yield Static(
                "W/S navigate  A/D families  E activate/add  / filter  ESC close",
                classes="modal-help",
            )
            yield Button("Cancel", id="cancel-node-select", variant="default")

    def on_mount(self) -> None:
        self._all_nodes = [
            node
            for node in self.factory.get_node_types_metadata()
            if not self._is_editor_only_node_type(node)
        ]
        self._sync_family_buttons()
        self._sync_subcategory_filter_visibility()
        self._apply_filter("")
        self._focus_first_subcategory_or_list()
        self.call_after_refresh(self._focus_first_subcategory_or_list)
        self.set_timer(0.01, self._focus_first_subcategory_or_list)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        focused = self.focused
        if isinstance(focused, CommandInput) and focused.editing:
            if action in {
                "cursor_up",
                "cursor_down",
                "choose",
                "focus_filter",
                "focus_node_list",
                "previous_family",
                "next_family",
                "cancel",
            }:
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
        button_id = event.button.id or ""
        if button_id == "cancel-node-select":
            self.dismiss(None)
        elif button_id.startswith("node-family-"):
            family = self._family_for_button_id(button_id)
            if family:
                self._set_active_family(family)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id in self._checkbox_id_tags:
            self._sync_selected_subcategories()
            self._apply_filter(self.query_one("#node-filter", CommandInput).value)

    def action_focus_filter(self) -> None:
        focus_command_widget(self, self.query_one("#node-filter", CommandInput))

    def action_focus_node_list(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            focused.end_edit()
        self._focus_node_list()

    def action_choose(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput):
            focused.begin_edit()
            return
        if isinstance(focused, Checkbox):
            focused.value = not focused.value
            self._sync_selected_subcategories()
            self._apply_filter(self.query_one("#node-filter", CommandInput).value)
            return
        if isinstance(focused, Button):
            focused.press()
            return
        list_view = self.query_one("#node-type-list", ListView)
        self._dismiss_selected(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_previous_family(self) -> None:
        self._cycle_family(-1)

    def action_next_family(self) -> None:
        self._cycle_family(1)

    def action_cursor_up(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            return
        self._move_focus_or_selection(-1)

    def action_cursor_down(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            return
        self._move_focus_or_selection(1)

    def _apply_filter(self, query: str) -> None:
        query = query.strip().lower()
        family_nodes = [
            node
            for node in self._all_nodes
            if self._node_family(node) == self._active_family
        ]
        if query:
            self._visible_nodes = [
                node
                for node in family_nodes
                if self._matches_query(node, query)
            ]
        else:
            self._visible_nodes = list(family_nodes)
        if self._selected_subcategories:
            selected = set(self._selected_subcategories)
            self._visible_nodes = [
                node
                for node in self._visible_nodes
                if selected.issubset(set(node.get("tags") or []))
            ]

        list_view = self.query_one("#node-type-list", ListView)
        list_view.clear()
        for node in self._visible_nodes:
            list_view.append(
                ListItem(
                    Static(self._node_row_text(node), classes="node-select-row")
                )
            )
        if not self._visible_nodes:
            list_view.append(ListItem(Static("No matching nodes")))
        else:
            list_view.index = 0

    def _node_row_text(self, node: Dict[str, Any]) -> str:
        """Two-line selector row: name + subcategories, then description.

        The family is omitted because it is redundant with the active tab;
        only the subcategory tags add information here.
        """
        display = node["display_name"]
        tags = node.get("tags") or []
        tag_text = "".join(f"({tag})" for tag in tags)
        line_one = f"{display} - {tag_text}" if tags else display
        description = str(node.get("description") or "").strip() or "No description"
        if len(description) > 76:
            description = f"{description[:75]}…"
        line_two = f"    {description}"
        return f"{line_one}\n{line_two}"

    def _focus_node_list(self) -> None:
        list_view = self.query_one("#node-type-list", ListView)
        focus_list(self.app, list_view, len(self._visible_nodes))

    def _dismiss_selected(self, index: Optional[int]) -> None:
        if index is None or index < 0 or index >= len(self._visible_nodes):
            return
        self.dismiss(self._visible_nodes[index]["type"])

    def _move_focus_or_selection(self, delta: int) -> None:
        focused = self.app.focused
        list_view = self.query_one("#node-type-list", ListView)
        if focused is list_view:
            self._move_selection_or_leave_list(delta)
            return
        widgets = self._nav_widgets()
        if not widgets:
            return
        try:
            current = widgets.index(focused)
        except ValueError:
            current = 0 if delta > 0 else len(widgets) - 1
        next_index = max(0, min(len(widgets) - 1, current + delta))
        self._focus_widget(widgets[next_index])

    def _move_selection_or_leave_list(self, delta: int) -> None:
        list_view = self.query_one("#node-type-list", ListView)
        if not self._visible_nodes:
            self._focus_adjacent_to_list(delta)
            return
        ensure_list_highlight(list_view, len(self._visible_nodes))
        current = list_view.index if list_view.index is not None else 0
        if delta < 0 and current == 0:
            self._focus_adjacent_to_list(delta)
            return
        if delta > 0 and current >= len(self._visible_nodes) - 1:
            self._focus_adjacent_to_list(delta)
            return
        move_list_highlight(self.app, list_view, len(self._visible_nodes), delta)

    def _focus_adjacent_to_list(self, delta: int) -> None:
        widgets = self._nav_widgets()
        list_view = self.query_one("#node-type-list", ListView)
        try:
            list_index = widgets.index(list_view)
        except ValueError:
            return
        next_index = max(0, min(len(widgets) - 1, list_index + delta))
        self._focus_widget(widgets[next_index])

    def _focus_first_subcategory_or_list(self) -> None:
        checkboxes = self._visible_subcategory_checkboxes()
        if checkboxes:
            focus_command_widget(self, checkboxes[0])
            return
        self._focus_node_list()

    def _focus_widget(self, widget: Any) -> None:
        if isinstance(widget, ListView):
            self._focus_node_list()
        else:
            focus_command_widget(self, widget)

    def _nav_widgets(self) -> list[Any]:
        widgets: list[Any] = [
            self.query_one(f"#node-family-{self._slug(self._active_family)}", Button),
            self.query_one("#node-filter", CommandInput),
        ]
        widgets.extend(self._visible_subcategory_checkboxes())
        widgets.append(self.query_one("#node-type-list", ListView))
        widgets.append(self.query_one("#cancel-node-select", Button))
        return widgets

    def _visible_subcategory_checkboxes(self) -> list[Checkbox]:
        return [
            checkbox
            for checkbox in self.query("#node-subcategory-filters Checkbox")
            if isinstance(checkbox, Checkbox) and checkbox.display
        ]

    def _cycle_family(self, delta: int) -> None:
        index = FAMILIES.index(self._active_family)
        self._set_active_family(FAMILIES[(index + delta) % len(FAMILIES)])

    def _set_active_family(self, family: str) -> None:
        if family not in FAMILIES:
            return
        self._active_family = family
        self._selected_subcategories = set()
        for checkbox in self.query("#node-subcategory-filters Checkbox"):
            if isinstance(checkbox, Checkbox):
                checkbox.value = False
        self._sync_family_buttons()
        self._sync_subcategory_filter_visibility()
        self._apply_filter(self.query_one("#node-filter", CommandInput).value)
        self._focus_first_subcategory_or_list()

    def _sync_family_buttons(self) -> None:
        for family in FAMILIES:
            button = self.query_one(f"#node-family-{self._slug(family)}", Button)
            button.variant = "primary" if family == self._active_family else "default"

    def _sync_subcategory_filter_visibility(self) -> None:
        available = set(self._subcategory_options_for_family(self._active_family))
        for checkbox in self.query("#node-subcategory-filters Checkbox"):
            if not isinstance(checkbox, Checkbox):
                continue
            tag = self._checkbox_id_tags.get(checkbox.id or "")
            visible = tag in available
            checkbox.display = visible
            checkbox.disabled = not visible

    def _subcategory_options_for_family(self, family: str) -> list[str]:
        tags = {
            tag
            for node in self._all_nodes
            if self._node_family(node) == family
            for tag in (node.get("tags") or [])
        }
        ordered = [tag for tag in SUBCATEGORY_ORDER if tag in tags]
        ordered.extend(sorted(tags - set(ordered)))
        return ordered

    def _sync_selected_subcategories(self) -> None:
        selected: set[str] = set()
        for checkbox in self._visible_subcategory_checkboxes():
            tag = self._checkbox_id_tags.get(checkbox.id or "")
            if tag and checkbox.value:
                selected.add(tag)
        self._selected_subcategories = selected

    def _family_for_button_id(self, button_id: str) -> str:
        for family in FAMILIES:
            if button_id == f"node-family-{self._slug(family)}":
                return family
        return ""

    def _node_family(self, node: Dict[str, Any]) -> str:
        return str(node.get("primary_family") or node.get("category") or "")

    def _is_editor_only_node_type(self, node: Dict[str, Any]) -> bool:
        return str(node.get("type") or "") in EDITOR_ONLY_NODE_TYPES

    def _matches_query(self, node: Dict[str, Any], query: str) -> bool:
        haystacks = [
            node.get("type", ""),
            node.get("display_name", ""),
            node.get("description", ""),
            *[str(tag) for tag in node.get("tags") or []],
        ]
        return any(query in str(value).lower() for value in haystacks)

    def _slug(self, value: str) -> str:
        return (
            value.lower()
            .replace("/", "")
            .replace("&", "and")
            .replace(" ", "-")
            .replace("_", "-")
        )

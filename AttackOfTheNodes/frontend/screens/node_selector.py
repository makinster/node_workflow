"""Node selector modal.

Four tabs map five backend families onto the selector (2026-06-12 taxonomy
revision): the `I/O` tab shows the `Inputs` or `Outputs` family behind an
Input/Output switch; `Flow Control`, `Utility`, and `Complex` map directly.
Lists are organized by group entries (which open the Group Picker) and
non-selectable section headers that keyboard navigation skips. See
docs/PHASE_17_NODE_VISUAL_IDENTITY.md.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Label,
    ListItem,
    ListView,
    Static,
    Switch,
)

from frontend.screens.group_picker import GroupPickerScreen
from frontend.node_types import END_NODE_TYPE, START_NODE_TYPE, TOMBSTONE_NODE_TYPE
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_navigation import focus_command_widget


TABS = ["I/O", "Flow Control", "Utility", "Complex"]
IO_TAB = "I/O"

# Hidden from the selector: tombstone is the editor-only deleted-node record;
# start is auto-generated; end is replaced by terminate-branch output config
# and the End Branch node.
HIDDEN_NODE_TYPES = {TOMBSTONE_NODE_TYPE, START_NODE_TYPE, END_NODE_TYPE}

# Filter checkboxes are deliberately sparse: groups and section headers do
# most of the organizing. Only these tabs surface filters.
TAB_FILTER_TAGS: Dict[str, List[str]] = {
    "I/O": ["Internet", "AI"],
    "Flow Control": [],
    "Utility": [],
    "Complex": ["AI"],
}
ALL_FILTER_TAGS = ["Internet", "AI"]

# Short descriptions shown on group entries in the selector and picker.
# Fallback: first member's description.
GROUP_DESCRIPTIONS: Dict[str, str] = {
    "Branch": "Splits execution flow into configurable parallel branches",
    "Merge": "Waits for all parallel branches to complete and collects outputs",
    "Data Transform": "Transforms data between formats and structures",
    "AI Processing": "Sends prompts to an AI model and returns the response",
}

# Frontend-owned section ordering per family. Entries without a
# selector_section render before the first header.
SECTION_ORDER: Dict[str, List[str]] = {
    "Inputs": ["Text & Data", "Files", "AI"],
    "Outputs": [],
    "Flow Control": ["Branching", "Timing"],
    "Utility": ["Automation", "Transform", "Debug", "Loop Helpers"],
    "Complex": ["AI", "Workflow", "Triggers"],
}

HEADER_RULE_WIDTH = 44


class NodeSelectorScreen(ModalScreen):
    """Add-node modal, backed entirely by NodeFactory metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
        ("/", "focus_filter", "Filter"),
        Binding("tab", "focus_node_list", "List", priority=True),
        Binding("a", "previous_tab", "Previous tab", priority=True),
        Binding("d", "next_tab", "Next tab", priority=True),
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
        self._entries: list[Dict[str, Any]] = []
        self._visible_nodes: list[Dict[str, Any]] = []
        self._active_tab = TABS[0]
        self._io_output_side = False
        self._selected_subcategories: set[str] = set()
        self._tag_checkbox_ids = {
            tag: f"node-subcategory-{self._slug(tag)}"
            for tag in ALL_FILTER_TAGS
        }
        self._checkbox_id_tags = {
            checkbox_id: tag
            for tag, checkbox_id in self._tag_checkbox_ids.items()
        }

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Add Node", classes="modal-title")
            with Horizontal(id="node-family-tabs"):
                for tab in TABS:
                    yield Button(
                        tab,
                        id=f"node-family-{self._slug(tab)}",
                        variant="primary" if tab == self._active_tab else "default",
                    )
            yield CommandInput(
                placeholder="Filter nodes",
                id="node-filter",
                auto_edit_on_focus=False,
            )
            with Horizontal(id="io-direction-row"):
                yield Label("Input", id="io-direction-label-input")
                yield Switch(value=False, id="io-direction-switch")
                yield Label("Output", id="io-direction-label-output")
            with Vertical(id="node-subcategory-filters"):
                for tag in ALL_FILTER_TAGS:
                    yield Checkbox(tag, value=False, id=self._tag_checkbox_ids[tag])
            yield ListView(id="node-type-list")
            yield Static(
                "W/S navigate  A/D tabs  E activate/add  / filter  ESC close",
                classes="modal-help",
            )
            yield Button("Cancel", id="cancel-node-select", variant="default")

    def on_mount(self) -> None:
        self._all_nodes = [
            node
            for node in self.factory.get_node_types_metadata()
            if str(node.get("type") or "") not in HIDDEN_NODE_TYPES
        ]
        self._sync_tab_buttons()
        self._sync_io_switch_visibility()
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
                "previous_tab",
                "next_tab",
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
        self._activate_entry(event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "cancel-node-select":
            self.dismiss(None)
        elif button_id.startswith("node-family-"):
            tab = self._tab_for_button_id(button_id)
            if tab:
                self._set_active_tab(tab)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id in self._checkbox_id_tags:
            self._sync_selected_subcategories()
            self._apply_filter(self.query_one("#node-filter", CommandInput).value)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "io-direction-switch":
            self._io_output_side = bool(event.value)
            self._sync_subcategory_filter_visibility()
            # Filters checked on the other side must not constrain this side.
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
        if isinstance(focused, Switch):
            focused.value = not focused.value
            return
        if isinstance(focused, Button):
            focused.press()
            return
        list_view = self.query_one("#node-type-list", ListView)
        self._activate_entry(list_view.index)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_previous_tab(self) -> None:
        self._cycle_tab(-1)

    def action_next_tab(self) -> None:
        self._cycle_tab(1)

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

    # ------------------------------------------------------------------
    # Entry building
    # ------------------------------------------------------------------

    def _active_family(self) -> str:
        if self._active_tab == IO_TAB:
            return "Outputs" if self._io_output_side else "Inputs"
        return self._active_tab

    def _apply_filter(self, query: str) -> None:
        query = query.strip().lower()
        family = self._active_family()
        family_nodes = [
            node
            for node in self._all_nodes
            if self._node_family(node) == family
        ]
        if self._selected_subcategories:
            selected = set(self._selected_subcategories)
            family_nodes = [
                node
                for node in family_nodes
                if selected.issubset(set(node.get("tags") or []))
            ]
        if query:
            # Search dissolves groups and hides headers: matching node types
            # appear directly in the list.
            matching = [
                node
                for node in family_nodes
                if self._matches_query(node, query)
            ]
            matching.sort(key=lambda node: node["display_name"])
            self._entries = [
                {"kind": "node", "node": node} for node in matching
            ]
        else:
            self._entries = self._grouped_entries(family, family_nodes)
        self._visible_nodes = [
            entry["node"] for entry in self._entries if entry["kind"] == "node"
        ]

        list_view = self.query_one("#node-type-list", ListView)
        list_view.clear()
        for entry in self._entries:
            if entry["kind"] == "header":
                list_view.append(
                    ListItem(
                        Static(
                            self._header_row_text(entry["name"]),
                            classes="node-select-header",
                        ),
                        classes="node-header-item",
                    )
                )
            elif entry["kind"] == "group":
                list_view.append(
                    ListItem(
                        Static(
                            self._group_row_text(entry),
                            classes="node-select-group",
                        )
                    )
                )
            else:
                list_view.append(
                    ListItem(
                        Static(
                            self._node_row_text(entry["node"]),
                            classes="node-select-row",
                        )
                    )
                )
        if not self._entries:
            list_view.append(ListItem(Static("No matching nodes")))
        else:
            selectable = self._selectable_indices()
            list_view.index = selectable[0] if selectable else 0

    def _grouped_entries(
        self, family: str, nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build the browsing view: section headers, groups, direct-adds."""
        groups: Dict[str, List[Dict[str, Any]]] = {}
        direct: List[Dict[str, Any]] = []
        for node in nodes:
            group = str(node.get("group") or "")
            if group:
                groups.setdefault(group, []).append(node)
            else:
                direct.append(node)

        # (section, sort key, entry) triples; single-member groups
        # auto-promote to direct-add node entries.
        items: List[tuple] = []
        for group_name, members in groups.items():
            members.sort(key=lambda node: node["display_name"])
            if len(members) >= 2:
                section = str(members[0].get("selector_section") or "")
                items.append(
                    (
                        section,
                        group_name,
                        {
                            "kind": "group",
                            "name": group_name,
                            "members": members,
                            "section": section,
                        },
                    )
                )
            else:
                node = members[0]
                items.append(
                    (
                        str(node.get("selector_section") or ""),
                        node["display_name"],
                        {"kind": "node", "node": node},
                    )
                )
        for node in direct:
            items.append(
                (
                    str(node.get("selector_section") or ""),
                    node["display_name"],
                    {"kind": "node", "node": node},
                )
            )

        order = SECTION_ORDER.get(family, [])

        def section_rank(section: str) -> tuple:
            if not section:
                return (0, 0, "")
            if section in order:
                return (1, order.index(section), "")
            return (2, 0, section)

        items.sort(key=lambda item: (section_rank(item[0]), item[1]))

        entries: List[Dict[str, Any]] = []
        current_section: Optional[str] = None
        for section, _, entry in items:
            if section != current_section:
                if section:
                    entries.append({"kind": "header", "name": section})
                current_section = section
            entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    # Row rendering
    # ------------------------------------------------------------------

    def _header_row_text(self, name: str) -> str:
        return f"── {name} ".ljust(HEADER_RULE_WIDTH, "─")

    def _group_row_text(self, entry: Dict[str, Any]) -> str:
        name = entry["name"]
        count = len(entry["members"])
        desc = GROUP_DESCRIPTIONS.get(name, "")
        if not desc:
            first = entry["members"][0]
            desc = str(first.get("description") or "").strip() or "No description"
        if len(desc) > 76:
            desc = f"{desc[:75]}…"
        return f"{{ {name} }} ({count})\n- {desc}"

    def _node_row_text(self, node: Dict[str, Any]) -> str:
        display = node["display_name"]
        description = str(node.get("description") or "").strip() or "No description"
        if len(description) > 76:
            description = f"{description[:75]}…"
        return f"\\[ {display} ]\n- {description}"

    # ------------------------------------------------------------------
    # Selection and activation
    # ------------------------------------------------------------------

    def _selectable_indices(self) -> List[int]:
        return [
            index
            for index, entry in enumerate(self._entries)
            if entry["kind"] != "header"
        ]

    def _activate_entry(self, index: Optional[int]) -> None:
        if index is None or index < 0 or index >= len(self._entries):
            return
        entry = self._entries[index]
        if entry["kind"] == "header":
            return
        if entry["kind"] == "group":
            members = entry["members"]

            def _on_pick(result: Optional[str]) -> None:
                if result:
                    self.dismiss(result)

            self.app.push_screen(
                GroupPickerScreen(entry["name"], members), _on_pick
            )
            return
        self.dismiss(entry["node"]["type"])

    # ------------------------------------------------------------------
    # Focus and navigation
    # ------------------------------------------------------------------

    def _focus_node_list(self) -> None:
        list_view = self.query_one("#node-type-list", ListView)
        self.app.set_focus(list_view)
        self._ensure_selectable_highlight(list_view)
        list_view.scroll_visible(animate=False)

    def _ensure_selectable_highlight(self, list_view: ListView) -> None:
        selectable = self._selectable_indices()
        if not selectable:
            return
        index = list_view.index
        if index is None or index not in selectable:
            index = selectable[0]
        # Re-assert the highlight even when the index is unchanged so the
        # cursor is always visible after re-entering the list.
        list_view.index = None
        list_view.index = index

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
        selectable = self._selectable_indices()
        if not selectable:
            self._focus_adjacent_to_list(delta)
            return
        current = list_view.index
        if current is None:
            list_view.index = selectable[0] if delta > 0 else selectable[-1]
            return
        if delta > 0:
            later = [index for index in selectable if index > current]
            if not later:
                self._focus_adjacent_to_list(delta)
                return
            list_view.index = later[0]
        else:
            earlier = [index for index in selectable if index < current]
            if not earlier:
                self._focus_adjacent_to_list(delta)
                return
            list_view.index = earlier[-1]

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
        focus_command_widget(self, self.query_one("#node-filter", CommandInput))

    def _focus_widget(self, widget: Any) -> None:
        if isinstance(widget, ListView):
            self._focus_node_list()
        else:
            focus_command_widget(self, widget)

    def _nav_widgets(self) -> list[Any]:
        widgets: list[Any] = [
            self.query_one(f"#node-family-{self._slug(self._active_tab)}", Button),
        ]
        widgets.append(self.query_one("#node-filter", CommandInput))
        if self._active_tab == IO_TAB:
            widgets.append(self.query_one("#io-direction-switch", Switch))
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

    # ------------------------------------------------------------------
    # Tab and filter state
    # ------------------------------------------------------------------

    def _cycle_tab(self, delta: int) -> None:
        index = TABS.index(self._active_tab)
        self._set_active_tab(TABS[(index + delta) % len(TABS)])

    def _set_active_tab(self, tab: str) -> None:
        if tab not in TABS:
            return
        self._active_tab = tab
        self._selected_subcategories = set()
        for checkbox in self.query("#node-subcategory-filters Checkbox"):
            if isinstance(checkbox, Checkbox):
                checkbox.value = False
        self._sync_tab_buttons()
        self._sync_io_switch_visibility()
        self._sync_subcategory_filter_visibility()
        self._apply_filter(self.query_one("#node-filter", CommandInput).value)
        self._focus_first_subcategory_or_list()

    def _sync_tab_buttons(self) -> None:
        for tab in TABS:
            button = self.query_one(f"#node-family-{self._slug(tab)}", Button)
            button.variant = "primary" if tab == self._active_tab else "default"

    def _sync_io_switch_visibility(self) -> None:
        row = self.query_one("#io-direction-row")
        visible = self._active_tab == IO_TAB
        row.display = visible
        switch = self.query_one("#io-direction-switch", Switch)
        switch.disabled = not visible

    def _sync_subcategory_filter_visibility(self) -> None:
        configured = set(TAB_FILTER_TAGS.get(self._active_tab, []))
        available = {
            tag
            for node in self._all_nodes
            if self._node_family(node) == self._active_family()
            for tag in (node.get("tags") or [])
        }
        for checkbox in self.query("#node-subcategory-filters Checkbox"):
            if not isinstance(checkbox, Checkbox):
                continue
            tag = self._checkbox_id_tags.get(checkbox.id or "")
            visible = tag in configured and tag in available
            checkbox.display = visible
            checkbox.disabled = not visible

    def _sync_selected_subcategories(self) -> None:
        selected: set[str] = set()
        for checkbox in self._visible_subcategory_checkboxes():
            tag = self._checkbox_id_tags.get(checkbox.id or "")
            if tag and checkbox.value:
                selected.add(tag)
        self._selected_subcategories = selected

    def _tab_for_button_id(self, button_id: str) -> str:
        for tab in TABS:
            if button_id == f"node-family-{self._slug(tab)}":
                return tab
        return ""

    def _node_family(self, node: Dict[str, Any]) -> str:
        return str(node.get("primary_family") or node.get("category") or "")

    def _matches_query(self, node: Dict[str, Any], query: str) -> bool:
        haystacks = [
            node.get("type", ""),
            node.get("display_name", ""),
            node.get("description", ""),
            str(node.get("group") or ""),
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

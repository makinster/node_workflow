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
    Label,
    ListItem,
    ListView,
    Static,
)

from frontend.screens.group_picker import GroupPickerScreen
from frontend.node_types import END_NODE_TYPE, START_NODE_TYPE, TOMBSTONE_NODE_TYPE
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_navigation import (
    focus_command_widget,
    group_widgets_into_rows,
    row_move_target,
    within_row_target,
)


TABS = ["I/O", "Flow Control", "Utility", "Complex"]
IO_TAB = "I/O"

# Hidden from the selector: tombstone is the editor-only deleted-node record;
# start is auto-generated; end is replaced by terminate-branch output config
# and the End Branch node.
HIDDEN_NODE_TYPES = {TOMBSTONE_NODE_TYPE, START_NODE_TYPE, END_NODE_TYPE}

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
        # Tabs switch by number key (1-4); A/D move within the current row.
        Binding("1", "jump_tab(1)", "Tab 1", priority=True),
        Binding("2", "jump_tab(2)", "Tab 2", priority=True),
        Binding("3", "jump_tab(3)", "Tab 3", priority=True),
        Binding("4", "jump_tab(4)", "Tab 4", priority=True),
        Binding("a", "cursor_left", "Left", priority=True),
        Binding("d", "cursor_right", "Right", priority=True),
        Binding("left", "cursor_left", "Left", priority=True),
        Binding("right", "cursor_right", "Right", priority=True),
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

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="node-selector-modal"):
            yield Label("Add Node", classes="modal-title")
            with Horizontal(id="node-family-tabs"):
                for index, tab in enumerate(TABS):
                    yield Button(
                        f"{index + 1} - {tab}",
                        id=f"node-family-{self._slug(tab)}",
                        variant="primary" if tab == self._active_tab else "default",
                    )
            yield CommandInput(
                placeholder="Filter nodes",
                id="node-filter",
                auto_edit_on_focus=False,
            )
            with Horizontal(id="io-direction-row"):
                yield Button(
                    "Input",
                    id="io-side-input",
                    classes="segmented-toggle",
                    variant="primary",
                )
                yield Button(
                    "Output",
                    id="io-side-output",
                    classes="segmented-toggle",
                    variant="default",
                )
            yield ListView(id="node-type-list")
            yield Static("", id="node-detail", classes="node-detail")
            yield Static(
                "W/S move  A/D within row  1-4 tabs  E add  / filter  ESC close",
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
        self._sync_io_toggle()
        self._apply_filter("")
        self._focus_filter_input()
        self.call_after_refresh(self._focus_filter_input)
        self.set_timer(0.01, self._focus_filter_input)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        focused = self.focused
        if isinstance(focused, CommandInput) and focused.editing:
            # While typing in the filter, nav keys and digits act as text.
            if action in {
                "cursor_up",
                "cursor_down",
                "cursor_left",
                "cursor_right",
                "jump_tab",
                "choose",
                "focus_filter",
                "focus_node_list",
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

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "node-type-list":
            self._update_detail(event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "cancel-node-select":
            self.dismiss(None)
        elif button_id == "io-side-input":
            self._set_io_side(False)
        elif button_id == "io-side-output":
            self._set_io_side(True)
        elif button_id.startswith("node-family-"):
            tab = self._tab_for_button_id(button_id)
            if tab:
                self._set_active_tab(tab)

    def _set_io_side(self, output_side: bool) -> None:
        """Switch the I/O segmented toggle between the Input and Output sides."""
        if self._active_tab != IO_TAB:
            return
        self._io_output_side = bool(output_side)
        self._sync_io_toggle()
        self._apply_filter(self.query_one("#node-filter", CommandInput).value)
        self._focus_active_io_button()

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
        if isinstance(focused, Button):
            # On the segmented I/O toggle this presses the focused side button
            # (Input/Output), which sets that side via on_button_pressed.
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

    def action_jump_tab(self, tab_number: int) -> None:
        """Jump directly to the Nth family tab (1-based). No-op past the end."""
        index = tab_number - 1
        if 0 <= index < len(TABS):
            self._set_active_tab(TABS[index])

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

    def action_cursor_left(self) -> None:
        self._move_within_row(-1)

    def action_cursor_right(self) -> None:
        self._move_within_row(1)

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
            self._update_detail(None)
        else:
            selectable = self._selectable_indices()
            list_view.index = selectable[0] if selectable else 0
            self._update_detail(list_view.index)

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
        """One-line scan row for a group: ``{ Name } (count)``."""
        return f"{{ {entry['name']} }} ({len(entry['members'])})"

    def _node_row_text(self, node: Dict[str, Any]) -> str:
        """One-line scan row for a node: ``[ Display Name ]``."""
        return f"\\[ {node['display_name']} ]"

    def _group_description(self, entry: Dict[str, Any]) -> str:
        desc = GROUP_DESCRIPTIONS.get(entry["name"], "")
        if not desc:
            first = entry["members"][0]
            desc = str(first.get("description") or "").strip()
        return desc or "No description"

    def _entry_detail_text(self, entry: Dict[str, Any]) -> str:
        """Description for the highlighted row, shown in the fixed detail line."""
        if entry["kind"] == "group":
            return self._group_description(entry)
        if entry["kind"] == "node":
            return (
                str(entry["node"].get("description") or "").strip()
                or "No description"
            )
        return ""

    def _update_detail(self, index: Optional[int]) -> None:
        detail_query = self.query("#node-detail")
        if not detail_query:
            return
        detail = detail_query.first()
        if index is None or index < 0 or index >= len(self._entries):
            detail.update("")
            return
        text = self._entry_detail_text(self._entries[index])
        if len(text) > 84:
            text = f"{text[:83]}…"
        detail.update(text)

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
        """W/S move between rows; the node list owns its own internal cursor."""
        focused = self.app.focused
        list_view = self.query_one("#node-type-list", ListView)
        if focused is list_view:
            self._move_selection_or_leave_list(delta)
            return
        rows = group_widgets_into_rows(self._nav_widgets())
        if not rows:
            return
        target, _at_boundary = row_move_target(rows, focused, delta)
        if target is not None:
            self._focus_widget(target)

    def _move_within_row(self, delta: int) -> None:
        """A/D move between widgets sharing the focused widget's row."""
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            return
        list_view = self.query_one("#node-type-list", ListView)
        if focused is list_view:
            return
        rows = group_widgets_into_rows(self._nav_widgets())
        target = within_row_target(rows, focused, delta)
        if target is not None:
            self._focus_widget(target)

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
        list_view = self.query_one("#node-type-list", ListView)
        rows = group_widgets_into_rows(self._nav_widgets())
        target, _at_boundary = row_move_target(rows, list_view, delta)
        if target is not None and target is not list_view:
            self._focus_widget(target)

    def _focus_filter_input(self) -> None:
        focus_command_widget(self, self.query_one("#node-filter", CommandInput))

    def _focus_widget(self, widget: Any) -> None:
        if isinstance(widget, ListView):
            self._focus_node_list()
        else:
            focus_command_widget(self, widget)

    def _nav_widgets(self) -> list[Any]:
        # All four family-tab buttons share the tab row (A/D moves between
        # them); both I/O side buttons share the toggle row.
        widgets: list[Any] = [
            self.query_one(f"#node-family-{self._slug(tab)}", Button)
            for tab in TABS
        ]
        widgets.append(self.query_one("#node-filter", CommandInput))
        if self._active_tab == IO_TAB:
            widgets.append(self.query_one("#io-side-input", Button))
            widgets.append(self.query_one("#io-side-output", Button))
        widgets.append(self.query_one("#node-type-list", ListView))
        widgets.append(self.query_one("#cancel-node-select", Button))
        return widgets

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
        self._sync_tab_buttons()
        self._sync_io_toggle()
        self._apply_filter(self.query_one("#node-filter", CommandInput).value)
        self._focus_filter_input()

    def _sync_tab_buttons(self) -> None:
        for tab in TABS:
            button = self.query_one(f"#node-family-{self._slug(tab)}", Button)
            button.variant = "primary" if tab == self._active_tab else "default"

    def _sync_io_toggle(self) -> None:
        row = self.query_one("#io-direction-row")
        visible = self._active_tab == IO_TAB
        row.display = visible
        input_button = self.query_one("#io-side-input", Button)
        output_button = self.query_one("#io-side-output", Button)
        for button in (input_button, output_button):
            button.disabled = not visible
        active = output_button if self._io_output_side else input_button
        inactive = input_button if self._io_output_side else output_button
        active.variant = "primary"
        active.add_class("active")
        inactive.variant = "default"
        inactive.remove_class("active")

    def _active_io_button(self) -> Button:
        button_id = "io-side-output" if self._io_output_side else "io-side-input"
        return self.query_one(f"#{button_id}", Button)

    def _focus_active_io_button(self) -> None:
        focus_command_widget(self, self._active_io_button())

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

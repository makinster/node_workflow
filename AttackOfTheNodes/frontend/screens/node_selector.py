"""Node selector modal.

Five tabs map 1:1 onto the five backend families (2026-06-22 taxonomy
revision): `In` → Inputs, `Flow Control`, `Utility`, `Out` → Outputs, and
`Complex`. The earlier combined `I/O` tab with an Input/Output toggle was
retired so the Outputs family can grow its own identity (live UI display
nodes during workflow execution). Tab display labels (`In`/`Out`) are
abbreviated; `TAB_FAMILY` maps each to its backend `primary_family` value.
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
from textual.containers import VerticalScroll

from frontend.screens.group_picker import GroupPickerScreen
from frontend.node_types import END_NODE_TYPE, START_NODE_TYPE, TOMBSTONE_NODE_TYPE
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_navigation import (
    focus_command_widget,
    group_widgets_into_rows,
    row_move_target,
    within_row_target,
)


# Tab display order with number-key hotkeys 1-5. Reads like data flow:
# In → process (Flow Control, Utility) → Out → Complex.
TABS = ["In", "Flow Control", "Utility", "Out", "Complex"]

# Tab display label → backend `primary_family` value. The abbreviated `In`/`Out`
# labels map to the full `Inputs`/`Outputs` families; the rest are 1:1.
TAB_FAMILY = {
    "In": "Inputs",
    "Flow Control": "Flow Control",
    "Utility": "Utility",
    "Out": "Outputs",
    "Complex": "Complex",
}

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
        # Tabs switch by number key (1-5); A/D move within the current row.
        Binding("1", "jump_tab(1)", "Tab 1", priority=True),
        Binding("2", "jump_tab(2)", "Tab 2", priority=True),
        Binding("3", "jump_tab(3)", "Tab 3", priority=True),
        Binding("4", "jump_tab(4)", "Tab 4", priority=True),
        Binding("5", "jump_tab(5)", "Tab 5", priority=True),
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
        self._drilled_in = False
        self._quick_list_members: List[str] = []
        self._quick_list_nodes: List[Dict[str, Any]] = []

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
            with Horizontal(id="node-selector-body"):
                yield ListView(id="node-type-list")
                with VerticalScroll(id="node-detail-panel"):
                    yield ListView(id="node-quick-list", classes="node-quick-list")
                    yield Static("", id="node-detail", classes="node-detail")
            yield Static(
                "W/S move  A/D within row  1-5 tabs  E add  / filter  ESC close",
                id="selector-help",
                classes="modal-help",
            )
            yield Button("Cancel", id="cancel-node-select", variant="default")

    def on_mount(self) -> None:
        self._all_nodes = [
            node
            for node in self.factory.get_node_types_metadata()
            if str(node.get("type") or "") not in HIDDEN_NODE_TYPES
        ]
        self.query_one("#node-quick-list", ListView).display = False
        self._sync_tab_buttons()
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
        if event.list_view.id == "node-quick-list":
            if self._drilled_in:
                index = event.list_view.index
                if index is not None and 0 <= index < len(self._quick_list_members):
                    self.dismiss(self._quick_list_members[index])
            return
        self._activate_entry(event.list_view.index)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "node-type-list":
            self._update_detail(event.list_view.index)
        elif event.list_view.id == "node-quick-list" and self._drilled_in:
            self._update_quick_detail(event.list_view.index or 0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "cancel-node-select":
            self.dismiss(None)
        elif button_id.startswith("node-family-"):
            tab = self._tab_for_button_id(button_id)
            if tab:
                self._set_active_tab(tab)

    def action_focus_filter(self) -> None:
        focus_command_widget(self, self.query_one("#node-filter", CommandInput))

    def action_focus_node_list(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            focused.end_edit()
        self._focus_node_list()

    def action_choose(self) -> None:
        focused = self.app.focused
        quick_list = self.query_one("#node-quick-list", ListView)
        if self._drilled_in and focused is quick_list:
            index = quick_list.index
            if index is not None and 0 <= index < len(self._quick_list_members):
                self.dismiss(self._quick_list_members[index])
            return
        if isinstance(focused, CommandInput):
            focused.begin_edit()
            return
        if isinstance(focused, Button):
            # On a family tab button this switches to that tab; on Cancel it
            # dismisses — both routed through on_button_pressed.
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
        if self._drilled_in:
            quick_list = self.query_one("#node-quick-list", ListView)
            if focused is quick_list:
                self._move_quick_list(quick_list, -1)
                return
        self._move_focus_or_selection(-1)

    def action_cursor_down(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            return
        if self._drilled_in:
            quick_list = self.query_one("#node-quick-list", ListView)
            if focused is quick_list:
                self._move_quick_list(quick_list, 1)
                return
        self._move_focus_or_selection(1)

    def action_cursor_left(self) -> None:
        if self._drilled_in:
            self._exit_quick_list()
            return
        self._move_within_row(-1)

    def action_cursor_right(self) -> None:
        if self._drilled_in:
            return
        list_view = self.query_one("#node-type-list", ListView)
        focused = self.app.focused
        if focused is list_view:
            index = list_view.index
            if index is not None and 0 <= index < len(self._entries):
                entry = self._entries[index]
                if entry["kind"] == "group":
                    self._enter_quick_list(entry)
                    return
        self._move_within_row(1)

    # ------------------------------------------------------------------
    # Entry building
    # ------------------------------------------------------------------

    def _active_family(self) -> str:
        return TAB_FAMILY.get(self._active_tab, self._active_tab)

    def _apply_filter(self, query: str) -> None:
        self._reset_drill_in()
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
        entry = self._entries[index]
        if entry["kind"] == "node":
            text = self._render_node_contract(entry["node"])
        elif entry["kind"] == "group":
            text = self._render_group_detail(entry)
        else:
            text = ""
        detail.update(text)

    # ------------------------------------------------------------------
    # Contract rendering
    # ------------------------------------------------------------------

    _TYPE_COLOR = "#4EC9B0"

    def _render_node_contract(self, node: Dict[str, Any]) -> str:
        """Render the full I/O contract for a node with Rich markup."""
        display_name = str(node.get("display_name") or node.get("type") or "Node")
        description = str(node.get("description") or "").strip()

        lines: List[str] = [f"[bold]{display_name}[/bold]"]
        if description:
            lines.append(description)

        input_meta: Dict[str, Any] = node.get("input_port_metadata") or {}
        output_meta: Dict[str, Any] = node.get("output_port_metadata") or {}

        required_inputs = [(p, m) for p, m in input_meta.items() if m.get("required")]
        optional_inputs = [(p, m) for p, m in input_meta.items() if not m.get("required")]
        required_outputs = [(p, m) for p, m in output_meta.items() if m.get("required")]
        optional_outputs = [(p, m) for p, m in output_meta.items() if not m.get("required")]

        def add_section(title: str, ports: List, direction: str) -> None:
            if not ports:
                return
            lines.append("")
            lines.append(f"[dim]{title}:[/dim]")
            for i, (port, meta) in enumerate(ports):
                if i > 0:
                    lines.append("")
                lines.extend(self._fmt_port(port, meta, direction))

        add_section("Required Inputs", required_inputs, "input")
        add_section("Optional Inputs", optional_inputs, "input")
        add_section("Required Outputs", required_outputs, "output")
        add_section("Optional Outputs", optional_outputs, "output")

        if not input_meta and not output_meta:
            lines.append("")
            lines.append("[dim]No I/O contract declared.[/dim]")

        return "\n".join(lines)

    def _fmt_port(self, port: str, meta: Dict[str, Any], direction: str) -> List[str]:
        """Return Rich-markup lines for one port (3-line format)."""
        name = str(meta.get("name") or port).replace("_", " ")
        data_type = str(meta.get("data_type") or "any")
        desc = str(meta.get("description") or "").strip()
        required = bool(meta.get("required"))
        pass_through = bool(meta.get("pass_through"))
        required_mark = "*" if required else ""

        port_lines: List[str] = []
        port_lines.append(
            f"  {name}{required_mark}  \\[[{self._TYPE_COLOR}]{data_type}[/]]"
        )
        if desc:
            port_lines.append(f"  [dim]{desc}[/dim]")
        if direction == "input":
            sources = meta.get("sources") or meta.get("from") or []
            if sources:
                src_text = "  ".join(str(s) for s in sources)
                port_lines.append(f"  [dim]└─< {src_text}[/dim]")
        else:
            if pass_through:
                port_lines.append("  [dim]↔ pass-thru[/dim]")
            else:
                dests = meta.get("to") or []
                if dests:
                    dest_text = "  ".join(str(d) for d in dests)
                    port_lines.append(f"  [dim]└─> {dest_text}[/dim]")
        return port_lines

    def _render_group_detail(self, entry: Dict[str, Any]) -> str:
        """Render a summary card for a group row."""
        name = str(entry.get("name") or "Group")
        desc = self._group_description(entry)
        members: List[Dict[str, Any]] = entry.get("members") or []

        lines: List[str] = [f"[bold]{{ {name} }}[/bold]"]
        if desc:
            lines.append(desc)
        if members:
            lines.append("")
            lines.append(f"[dim]{len(members)} node types:[/dim]")
            for member in members:
                display = str(member.get("display_name") or member.get("type") or "")
                lines.append(f"  \\[ {display} ]")
        lines.append("")
        lines.append("[dim]E = open picker  D/→ = quick list[/dim]")
        return "\n".join(lines)

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

    def _enter_quick_list(self, entry: Dict[str, Any]) -> None:
        """Drill into a group: show top-6 members in the right panel quick list."""
        members = sorted(entry.get("members") or [], key=lambda m: m["display_name"])[:6]
        quick_list = self.query_one("#node-quick-list", ListView)
        quick_list.clear()
        for member in members:
            quick_list.append(ListItem(Static(
                self._node_row_text(member),
                classes="node-select-row",
            )))
        self._drilled_in = True
        self._quick_list_members = [m["type"] for m in members]
        self._quick_list_nodes = list(members)
        quick_list.display = True
        quick_list.index = 0
        self.app.set_focus(quick_list)
        self._update_quick_detail(0)
        self._sync_help_text()

    def _exit_quick_list(self) -> None:
        """Return focus to the left list and restore its group detail."""
        self._reset_drill_in()
        self._focus_node_list()
        list_view = self.query_one("#node-type-list", ListView)
        self._update_detail(list_view.index)

    def _reset_drill_in(self) -> None:
        """Clear drill-in state; does not change focus or update detail."""
        if not self._drilled_in:
            return
        self._drilled_in = False
        self._quick_list_members = []
        self._quick_list_nodes = []
        quick_list = self.query_one("#node-quick-list", ListView)
        quick_list.display = False
        self._sync_help_text()

    def _move_quick_list(self, quick_list: ListView, delta: int) -> None:
        """Clamp-move within the quick list; does not exit at boundaries."""
        count = len(self._quick_list_members)
        if not count:
            return
        current = quick_list.index if quick_list.index is not None else 0
        new_index = max(0, min(count - 1, current + delta))
        if new_index != current:
            quick_list.index = new_index

    def _update_quick_detail(self, index: int) -> None:
        """Show the I/O contract for the quick-list item at index."""
        detail = self.query_one("#node-detail", Static)
        if 0 <= index < len(self._quick_list_nodes):
            detail.update(self._render_node_contract(self._quick_list_nodes[index]))
        else:
            detail.update("")

    def _sync_help_text(self) -> None:
        help_widget = self.query_one("#selector-help", Static)
        if self._drilled_in:
            help_widget.update("W/S quick list  A/← back  E add  ESC close")
        else:
            help_widget.update(
                "W/S move  A/D within row  1-5 tabs  E add  / filter  ESC close"
            )

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
        # All five family-tab buttons share the tab row (A/D moves between them).
        widgets: list[Any] = [
            self.query_one(f"#node-family-{self._slug(tab)}", Button)
            for tab in TABS
        ]
        widgets.append(self.query_one("#node-filter", CommandInput))
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
        self._reset_drill_in()
        self._active_tab = tab
        self._sync_tab_buttons()
        self._apply_filter(self.query_one("#node-filter", CommandInput).value)
        self._focus_filter_input()

    def _sync_tab_buttons(self) -> None:
        for tab in TABS:
            button = self.query_one(f"#node-family-{self._slug(tab)}", Button)
            button.variant = "primary" if tab == self._active_tab else "default"

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

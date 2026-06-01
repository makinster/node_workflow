"""Editor screen for the first Textual milestone."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Label, Static

from backend.validator import validate_workflow
from frontend.screens.branch_selector import BranchSelectorScreen
from frontend.screens.error_details import ErrorDetailsScreen
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.node_selector import NodeSelectorScreen
from frontend.widgets.node_list import NodeList
from frontend.widgets.status_bar import StatusBar


class EditorScreen(Screen):
    """Workflow editor view: node list on the left, details on the right."""

    BINDINGS = [
        ("tab", "focus_next", "Next panel"),
        ("shift+tab", "focus_previous", "Previous panel"),
        ("w", "cursor_up", "Up"),
        ("s", "cursor_down", "Down"),
        ("enter", "edit_selected", "Edit"),
        Binding("e", "edit_selected", "Edit", priority=True),
        Binding("a", "add_node", "Add node", priority=True),
        Binding("i", "insert_node", "Insert node", priority=True),
        Binding("v", "validate_workflow", "Validate", priority=True),
        Binding("b", "toggle_breakpoint", "Breakpoint", priority=True),
        Binding("ctrl+b", "clear_breakpoints", "Clear breakpoints", priority=True),
        Binding("backspace", "delete_selected", "Delete", priority=True),
        Binding("x", "delete_selected", "Delete", priority=True),
        Binding("l", "workflow_library", "Library", priority=True),
        Binding("o", "workflow_library", "Library", priority=True),
        Binding("?", "help", "Help", priority=True),
    ]

    def __init__(self, factory, workflow_map, save_manager=None) -> None:
        super().__init__()
        self.factory = factory
        self.workflow_map = workflow_map
        self.save_manager = save_manager
        self.selected_node_id: Optional[str] = None
        self.selected_row: Optional[Dict[str, Any]] = None
        self.active_branch_ports: Dict[str, str] = {}
        self._pending_node_add_mode = "add"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="editor-root"):
            yield Label("", id="workflow-title")
            with Horizontal(id="editor-columns"):
                with Vertical(id="nodes-panel", classes="panel"):
                    yield Label("Nodes", classes="panel-title")
                    yield NodeList()
                with Vertical(id="details-panel", classes="panel"):
                    yield Label("Details", classes="panel-title")
                    yield Static("", id="node-details")
            yield StatusBar(
                "W/S move  ENTER/E edit  A add  I insert  B breakpoint  V validate  X/⌫ delete  L library  Ctrl+S save  Ctrl+R run  ? help"
            )

    def on_mount(self) -> None:
        self.refresh_from_backend()
        node_list = self.query_one(NodeList)
        if node_list._rows:
            node_list.index = 0
            self._select_row(node_list.row_for_index(0))
        node_list.focus()
        self._refresh_details()

    def refresh_from_backend(self) -> None:
        """Reload screen widgets from backend state."""
        title = self.workflow_map.workflow_name or "No workflow"
        dirty = " *" if self.workflow_map.is_dirty else ""
        state = "IDLE"
        self.query_one("#workflow-title", Label).update(
            f"Workflow: {title}{dirty} [{state}]"
        )
        rows = self._build_visible_rows()
        if self.selected_node_id and not any(
            row["kind"] == "node" and row.get("node_id") == self.selected_node_id
            for row in rows
        ):
            node = self.workflow_map.get_node_data(self.selected_node_id)
            if node is not None:
                rows.append(
                    {
                        "kind": "node",
                        "node_id": self.selected_node_id,
                        "node": node,
                        "loose": True,
                    }
                )
        node_list = self.query_one(NodeList)
        node_list.refresh_rows(rows)
        if self.selected_row and not self._row_still_visible(self.selected_row, rows):
            self.selected_row = rows[0] if rows else None
            self.selected_node_id = (
                self.selected_row.get("node_id")
                if self.selected_row and self.selected_row["kind"] == "node"
                else None
            )
        elif self.selected_row is not None:
            self.selected_row = self._matching_visible_row(self.selected_row, rows)
            self.selected_node_id = (
                self.selected_row.get("node_id")
                if self.selected_row and self.selected_row["kind"] == "node"
                else None
            )
        elif self.selected_row is None and rows:
            self._select_row(rows[0])
        index = self._index_for_selected_row(node_list)
        if index is not None:
            node_list.index = index
        node_list.focus()
        self._refresh_details()

    def on_list_view_selected(self, event) -> None:
        node_list = self.query_one(NodeList)
        self._select_row(node_list.row_for_index(event.list_view.index))
        self._refresh_details()
        self.action_edit_selected()

    def on_list_view_highlighted(self, event) -> None:
        node_list = self.query_one(NodeList)
        self._select_row(node_list.row_for_index(event.list_view.index))
        self._refresh_details()

    def action_add_node(self) -> None:
        self._pending_node_add_mode = "add"
        self.app.push_screen(NodeSelectorScreen(self.factory), self._add_node_from_modal)

    def action_insert_node(self) -> None:
        self._pending_node_add_mode = "insert"
        self.app.push_screen(NodeSelectorScreen(self.factory), self._add_node_from_modal)

    def action_validate_workflow(self) -> None:
        result = validate_workflow(self.workflow_map, self.factory)
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        if not errors and not warnings:
            self.app.notify("Workflow is valid")
            return
        self.app.push_screen(
            ErrorDetailsScreen({"validation": result}),
            self._handle_validation_details_result,
        )

    def action_workflow_library(self) -> None:
        self.app.action_workflow_library()

    def action_help(self) -> None:
        self.app.action_help()

    def action_toggle_breakpoint(self) -> None:
        if self.selected_node_id is None:
            self.app.notify("No node selected")
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            self.app.notify("No node selected")
            return
        enabled = not bool(node.get("breakpoint"))
        self.workflow_map.set_breakpoint(self.selected_node_id, enabled)
        self.refresh_from_backend()
        self.app.notify("Breakpoint set" if enabled else "Breakpoint cleared")

    def action_clear_breakpoints(self) -> None:
        cleared = self.workflow_map.clear_all_breakpoints()
        self.refresh_from_backend()
        self.app.notify(
            f"Cleared {cleared} breakpoint{'s' if cleared != 1 else ''}"
        )

    def action_edit_selected(self) -> None:
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            self._open_branch_selector(self.selected_row)
            return
        if self.selected_node_id is None:
            self.app.notify("No node selected")
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            self.app.notify("No node selected")
            return
        # Tombstone nodes open the NodeSelector to pick a replacement
        if node.get("type") == "tombstone_node":
            self.app.push_screen(
                NodeSelectorScreen(self.factory),
                self._replace_tombstone_from_modal,
            )
            return
        self.app.push_screen(
            NodeConfigScreen(self.factory, self.workflow_map, self.selected_node_id, node),
            self._save_node_config_from_modal,
        )

    def action_delete_selected(self) -> None:
        if self.selected_node_id is None:
            self.app.notify("No node selected")
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            self.app.notify("No node selected")
            return
        if node.get("type") == "start_node":
            self.app.notify("Cannot delete the Start node", severity="error")
            return

        self._do_delete(True)

    def _do_delete(self, confirmed: bool) -> None:
        if not confirmed or self.selected_node_id is None:
            return
        self.workflow_map.replace_with_tombstone(self.selected_node_id)
        self.refresh_from_backend()
        self.app.notify("Node deleted — open the stub to choose a replacement")

    def _replace_tombstone_from_modal(self, node_type: str | None) -> None:
        if not node_type or self.selected_node_id is None:
            return
        self.workflow_map.replace_node_type(self.selected_node_id, node_type)
        self.refresh_from_backend()
        self.app.notify(f"Node replaced with {node_type}")

    def action_cursor_up(self) -> None:
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._move_selection(1)

    def _add_node_from_modal(self, node_type: str | None) -> None:
        insert_mode = self._pending_node_add_mode == "insert"
        self._pending_node_add_mode = "add"
        if not node_type:
            return
        source = (
            self._source_for_insert_node()
            if insert_mode
            else self._source_for_new_node()
        )
        node_id = self.workflow_map.add_node(node_type)
        if node_id is None:
            self.app.notify(f"Unknown node type: {node_type}", severity="error")
            return
        if source is not None:
            self._connect_new_node(source["node_id"], source["port"], node_id)
        self.selected_node_id = node_id
        self.selected_row = {"kind": "node", "node_id": node_id}
        self.refresh_from_backend()
        self.app.notify("Node inserted" if insert_mode else "Node added")

    def _save_node_config_from_modal(self, result: Dict[str, Any] | None) -> None:
        if not result or self.selected_node_id is None:
            return
        alias = str(result.get("alias", "")).strip()
        config = result.get("config", {})
        self.workflow_map.update_node_alias(self.selected_node_id, alias)
        self.workflow_map.update_node_config(self.selected_node_id, config)
        self.refresh_from_backend()
        self.app.notify("Node updated")

    def _handle_validation_details_result(self, result: Dict[str, Any] | None) -> None:
        if not result or result.get("action") != "jump":
            return
        node_id = result.get("node_id")
        if not node_id or self.workflow_map.get_node_data(node_id) is None:
            return
        self.selected_node_id = node_id
        self.selected_row = {"kind": "node", "node_id": node_id}
        self.refresh_from_backend()
        self.app.notify(f"Jumped to {node_id}")

    def _open_branch_selector(self, row: Dict[str, Any]) -> None:
        branch_node_id = row["branch_node_id"]
        branch_node = self.workflow_map.get_node_data(branch_node_id)
        if branch_node is None:
            return
        label = branch_node.get("alias") or branch_node_id
        self.app.push_screen(
            BranchSelectorScreen(
                branch_node_id=branch_node_id,
                branch_node_label=label,
                output_ports=list(row["output_ports"]),
                active_port=row["active_port"],
                port_labels=row.get("port_labels", {}),
            ),
            self._select_branch_from_modal,
        )

    def _select_branch_from_modal(self, result: Dict[str, str] | None) -> None:
        if not result:
            return
        branch_node_id = result["branch_node_id"]
        branch_port = result["branch_port"]
        self.active_branch_ports[branch_node_id] = branch_port
        self.selected_node_id = None
        self.selected_row = {
            "kind": "branch_select",
            "branch_node_id": branch_node_id,
            "active_port": branch_port,
        }
        self.refresh_from_backend()
        branch_node = self.workflow_map.get_node_data(branch_node_id) or {}
        branch_label = self._branch_port_labels(branch_node).get(branch_port, branch_port)
        self.app.notify(f"Viewing branch: {branch_label}")

    def _connect_new_node(self, source_node_id: str, source_port: str, target_node_id: str) -> None:
        source = self.workflow_map.get_node_data(source_node_id)
        target = self.workflow_map.get_node_data(target_node_id)
        if source is None or target is None:
            return
        source_meta = self._metadata_for_type(source.get("type", ""))
        target_meta = self._metadata_for_type(target.get("type", ""))
        if source_meta is None or target_meta is None:
            return
        input_ports = target_meta.get("input_ports") or []
        if not input_ports:
            return
        existing_connection = self._connection_for_port(source, source_port)
        existing_target = (
            existing_connection.get("target_node_id") if existing_connection else None
        )
        if existing_connection and existing_target:
            self.workflow_map.disconnect(
                source_node_id,
                source_port,
                existing_target,
                existing_connection.get("target_port", "input"),
            )
        self.workflow_map.connect(
            source_node_id,
            source_port,
            target_node_id,
            input_ports[0],
        )
        if existing_target:
            target_output_ports = target_meta.get("output_ports") or []
            existing = self.workflow_map.get_node_data(existing_target)
            existing_meta = (
                self._metadata_for_type(existing.get("type", "")) if existing else None
            )
            existing_input_ports = existing_meta.get("input_ports") if existing_meta else []
            if target_output_ports and existing_input_ports:
                self.workflow_map.connect(
                    target_node_id,
                    target_output_ports[0],
                    existing_target,
                    existing_input_ports[0],
                )

    def _refresh_details(self) -> None:
        detail = self.query_one("#node-details", Static)
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            detail.update(self._format_branch_selector_details(self.selected_row))
            return
        if self.selected_node_id is None:
            detail.update("No node selected")
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            detail.update("No node selected")
            return
        detail.update(self._format_node_details(self.selected_node_id, node))

    def _format_node_details(self, node_id: str, node: Dict[str, Any]) -> str:
        metadata = self._metadata_for_type(node.get("type", ""))
        lines = [
            f"Selected: {node.get('alias') or node_id}",
            f"Type: {node.get('type', 'unknown')}",
            f"Breakpoint: {'on' if node.get('breakpoint') else 'off'}",
        ]
        if metadata:
            lines.append(f"Description: {metadata.get('description', '')}")
            lines.append("")
            lines.append("Ports:")
            lines.append(f"  inputs: {self._format_input_ports(node_id, metadata)}")
            lines.append(f"  outputs: {self._format_output_ports(node, metadata)}")
        lines.append("")
        lines.append("Configuration:")
        config = node.get("config") or {}
        if config:
            for key, value in config.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("  -")
        lines.append("")
        lines.append("Connections:")
        outputs = node.get("connections", {}).get("outputs", [])
        if outputs:
            for conn in outputs:
                target = conn.get("target_node_id", "?")
                target_node = self.workflow_map.get_node_data(target) or {}
                source_port = conn.get("source_port", "default")
                lines.append(
                    f"  {source_port} -> {self._node_label(target, target_node)}"
                )
        else:
            lines.append("  outputs: -")
        return "\n".join(lines)

    def _metadata_for_type(self, node_type: str) -> Optional[Dict[str, Any]]:
        for item in self.factory.get_node_types_metadata():
            if item["type"] == node_type:
                return item
        return None

    def _node_label(self, node_id: str, node: Dict[str, Any]) -> str:
        name = node.get("alias") or node.get("type") or node_id
        return f"{name} ({node_id})"

    def _format_input_ports(self, node_id: str, metadata: Dict[str, Any]) -> str:
        ports = metadata.get("input_ports") or []
        if not ports:
            return "-"
        pieces = []
        node = self.workflow_map.get_node_data(node_id) or {}
        inputs = node.get("connections", {}).get("inputs", [])
        for port in ports:
            source_text = "-"
            for conn in inputs:
                if conn.get("target_port") == port:
                    source_id = conn.get("source_node_id", "?")
                    source_node = self.workflow_map.get_node_data(source_id) or {}
                    source_text = self._node_label(source_id, source_node)
                    break
            pieces.append(f"{port} <- {source_text}")
        return "; ".join(pieces)

    def _format_output_ports(self, node: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        ports = metadata.get("output_ports") or []
        if not ports:
            return "-"
        pieces = []
        outputs = node.get("connections", {}).get("outputs", [])
        port_labels = self._branch_port_labels(node)
        for port in ports:
            target_text = "-"
            for conn in outputs:
                if conn.get("source_port", "default") == port:
                    target_id = conn.get("target_node_id", "?")
                    target_node = self.workflow_map.get_node_data(target_id) or {}
                    target_text = self._node_label(target_id, target_node)
                    break
            label = port_labels.get(port, port)
            pieces.append(f"{label} -> {target_text}")
        return "; ".join(pieces)

    def _branch_port_labels(self, node: Dict[str, Any]) -> Dict[str, str]:
        config = node.get("config") or {}
        return {
            "path_a": str(config.get("path_a_label") or "Path A"),
            "path_b": str(config.get("path_b_label") or "Path B"),
        }

    def _select_row(self, row: Optional[Dict[str, Any]]) -> None:
        self.selected_row = row
        self.selected_node_id = (
            row.get("node_id") if row and row["kind"] == "node" else None
        )

    def _move_selection(self, delta: int) -> None:
        node_list = self.query_one(NodeList)
        if not node_list._rows:
            return
        current = node_list.index if node_list.index is not None else 0
        next_index = max(0, min(len(node_list._rows) - 1, current + delta))
        node_list.index = next_index
        self._select_row(node_list.row_for_index(next_index))
        self._refresh_details()
        node_list.focus()

    def _build_visible_rows(self) -> list[Dict[str, Any]]:
        nodes = self.workflow_map.get_all_node_data()
        start_node_id = self.workflow_map.find_start_node_id() or next(iter(nodes), None)
        rows: list[Dict[str, Any]] = []
        visited: set[str] = set()
        current_node_id = start_node_id

        while current_node_id and current_node_id not in visited:
            node = nodes.get(current_node_id)
            if node is None:
                break
            visited.add(current_node_id)
            rows.append({"kind": "node", "node_id": current_node_id, "node": node})

            metadata = self._metadata_for_type(node.get("type", ""))
            output_ports = list(metadata.get("output_ports") or []) if metadata else []
            if len(output_ports) > 1:
                active_port = self.active_branch_ports.get(current_node_id, output_ports[0])
                if active_port not in output_ports:
                    active_port = output_ports[0]
                self.active_branch_ports[current_node_id] = active_port
                port_labels = self._branch_port_labels(node)
                rows.append(
                    {
                        "kind": "branch_select",
                        "branch_node_id": current_node_id,
                        "active_port": active_port,
                        "active_label": port_labels.get(active_port, active_port),
                        "output_ports": output_ports,
                        "port_labels": port_labels,
                    }
                )
                current_node_id = self._target_for_port(node, active_port)
                continue

            next_port = "default"
            if output_ports:
                next_port = output_ports[0]
            current_node_id = self._target_for_port(node, next_port)
        return rows

    def _target_for_port(self, node: Dict[str, Any], source_port: str) -> Optional[str]:
        connection = self._connection_for_port(node, source_port)
        return connection.get("target_node_id") if connection else None

    def _connection_for_port(
        self, node: Dict[str, Any], source_port: str
    ) -> Optional[Dict[str, Any]]:
        for conn in node.get("connections", {}).get("outputs", []):
            if conn.get("source_port", "default") == source_port:
                return conn
        return None

    def _row_still_visible(
        self, selected_row: Dict[str, Any], rows: list[Dict[str, Any]]
    ) -> bool:
        for row in rows:
            if selected_row["kind"] != row["kind"]:
                continue
            if row["kind"] == "node" and row.get("node_id") == selected_row.get("node_id"):
                return True
            if (
                row["kind"] == "branch_select"
                and row.get("branch_node_id") == selected_row.get("branch_node_id")
            ):
                return True
        return False

    def _matching_visible_row(
        self, selected_row: Dict[str, Any], rows: list[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for row in rows:
            if selected_row["kind"] != row["kind"]:
                continue
            if row["kind"] == "node" and row.get("node_id") == selected_row.get("node_id"):
                return row
            if (
                row["kind"] == "branch_select"
                and row.get("branch_node_id") == selected_row.get("branch_node_id")
            ):
                return row
        return None

    def _index_for_selected_row(self, node_list: NodeList) -> Optional[int]:
        if self.selected_row is None:
            return None
        for index, row in enumerate(node_list._rows):
            if row["kind"] != self.selected_row["kind"]:
                continue
            if row["kind"] == "node" and row.get("node_id") == self.selected_row.get("node_id"):
                return index
            if (
                row["kind"] == "branch_select"
                and row.get("branch_node_id") == self.selected_row.get("branch_node_id")
            ):
                return index
        return None

    def _source_for_new_node(self) -> Optional[Dict[str, str]]:
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            branch_node_id = self.selected_row["branch_node_id"]
            active_port = self.active_branch_ports.get(
                branch_node_id, self.selected_row["active_port"]
            )
            tail_id = self._tail_for_branch(branch_node_id, active_port)
            if tail_id != branch_node_id:
                tail = self.workflow_map.get_node_data(tail_id)
                tail_meta = self._metadata_for_type(tail.get("type", "")) if tail else None
                tail_ports = tail_meta.get("output_ports") if tail_meta else None
                return {"node_id": tail_id, "port": (tail_ports or ["default"])[0]}
            return {"node_id": branch_node_id, "port": active_port}
        if self.selected_node_id:
            node = self.workflow_map.get_node_data(self.selected_node_id)
            metadata = self._metadata_for_type(node.get("type", "")) if node else None
            ports = metadata.get("output_ports") if metadata else None
            return {"node_id": self.selected_node_id, "port": (ports or ["default"])[0]}
        return None

    def _source_for_insert_node(self) -> Optional[Dict[str, str]]:
        """Return the highlighted row source for insert-after behavior."""
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            branch_node_id = self.selected_row["branch_node_id"]
            active_port = self.active_branch_ports.get(
                branch_node_id, self.selected_row["active_port"]
            )
            return {"node_id": branch_node_id, "port": active_port}
        if self.selected_node_id:
            node = self.workflow_map.get_node_data(self.selected_node_id)
            metadata = self._metadata_for_type(node.get("type", "")) if node else None
            ports = metadata.get("output_ports") if metadata else None
            return {"node_id": self.selected_node_id, "port": (ports or ["default"])[0]}
        return None

    def _tail_for_branch(self, branch_node_id: str, branch_port: str) -> str:
        nodes = self.workflow_map.get_all_node_data()
        current_node_id = self._target_for_port(nodes.get(branch_node_id, {}), branch_port)
        if current_node_id is None:
            return branch_node_id
        visited = {branch_node_id}
        tail_id = current_node_id
        while current_node_id and current_node_id not in visited:
            visited.add(current_node_id)
            tail_id = current_node_id
            node = nodes.get(current_node_id)
            if node is None:
                break
            metadata = self._metadata_for_type(node.get("type", ""))
            ports = metadata.get("output_ports") if metadata else []
            if len(ports or []) != 1:
                break
            current_node_id = self._target_for_port(node, ports[0])
        return tail_id

    def _format_branch_selector_details(self, row: Dict[str, Any]) -> str:
        branch_node = self.workflow_map.get_node_data(row["branch_node_id"]) or {}
        target_id = self._target_for_port(branch_node, row["active_port"])
        branch_label = row.get("active_label") or row["active_port"]
        lines = [
            "Branch Select",
            f"Branch node: {branch_node.get('alias') or row['branch_node_id']}",
            f"Selected branch: {branch_label}",
            f"Target: {target_id or '-'}",
            "",
            "Press ENTER to choose another branch.",
            "Press A to add a node to this branch.",
            "Press I to insert a node into this branch.",
        ]
        return "\n".join(lines)

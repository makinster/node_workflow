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
from frontend.screens.merge_beacon_selector import MergeBeaconSelectorScreen
from frontend.screens.node_config import (
    NodeConfigScreen,
    merge_input_options,
    upstream_branch_info,
)
from frontend.screens.node_selector import NodeSelectorScreen
from frontend import notifications
from frontend.editor_workflow_adapter import EditorWorkflowAdapter
from frontend.node_io_display import (
    memory_registry,
    node_display_name,
    node_label,
    normalize_membank_inputs,
    normalize_membank_outputs,
    output_display_description,
    output_display_name,
    trace_transient_producer,
)
from frontend.widgets.node_card import (
    BranchSelectCard,
    MergeBeaconSelectCard,
    NodeCard,
    branch_path_color_key,
)
from frontend.widgets.node_list import NodeList
from frontend.widgets.status_bar import StatusBar


class EditorScreen(Screen):
    """Workflow editor view: node list on the left, details on the right."""

    BINDINGS = [
        ("tab", "focus_next", "Next panel"),
        ("shift+tab", "focus_previous", "Previous panel"),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        Binding("left", "cycle_branch_prev", "Previous branch", priority=True),
        Binding("right", "cycle_branch_next", "Next branch", priority=True),
        ("enter", "edit_selected", "Edit"),
        Binding("e", "edit_selected", "Edit", priority=True),
        Binding("a", "cycle_branch_prev", "Previous branch", priority=True),
        Binding("d", "cycle_branch_next", "Next branch", priority=True),
        Binding("ctrl+a", "cycle_incomplete_branch_prev", "Previous incomplete branch", priority=True),
        Binding("ctrl+d", "cycle_incomplete_branch_next", "Next incomplete branch", priority=True),
        Binding("ctrl+left", "cycle_incomplete_branch_prev", "Previous incomplete branch", priority=True),
        Binding("ctrl+right", "cycle_incomplete_branch_next", "Next incomplete branch", priority=True),
        Binding("i", "insert_node", "Insert node", priority=True),
        Binding("v", "validate_workflow", "Validate", priority=True),
        Binding("b", "toggle_breakpoint", "Breakpoint", priority=True),
        Binding("ctrl+b", "clear_breakpoints", "Clear breakpoints", priority=True),
        Binding("z", "undo_delete", "Undo delete", priority=True),
        Binding("backspace", "delete_selected", "Delete", priority=True),
        Binding("x", "delete_selected", "Delete", priority=True),
        Binding("f", "workflow_library", "File", priority=True),
        Binding("o", "options", "Options", priority=True),
        Binding("h", "help", "Help", priority=True),
        Binding("?", "help", "Help", priority=True),
        Binding("ctrl+s", "save_workflow", "Save", priority=True),
    ]

    def __init__(self, factory, workflow_map, save_manager=None, secrets_manager=None) -> None:
        super().__init__()
        self.factory = factory
        self.workflow_map = workflow_map
        self.save_manager = save_manager
        self.secrets_manager = secrets_manager
        self.selected_node_id: Optional[str] = None
        self.selected_row: Optional[Dict[str, Any]] = None
        self.active_branch_ports: Dict[str, str] = {}
        self.last_branch_selection: Dict[str, str] = {}
        self._branch_cycle_anchor: Optional[str] = None
        self._refreshing_from_backend = False
        self._pending_node_add_mode = "add"
        self.workflow_adapter = EditorWorkflowAdapter(workflow_map, factory)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="editor-root"):
            yield Label("", id="workflow-title")
            with Horizontal(id="editor-columns"):
                with Vertical(id="nodes-panel", classes="panel"):
                    yield Label("Nodes", classes="panel-title")
                    yield NodeList()
                with Vertical(id="details-panel", classes="panel"):
                    yield Label("Selected Node:", classes="panel-title")
                    yield Static("", id="node-details")
            yield StatusBar("f file | o options | h help | ctrl+q quit")

    def on_mount(self) -> None:
        self.workflow_adapter.bind_state_owner(self.app)
        self._restore_editor_state_from_app()
        self.refresh_from_backend()
        node_list = self.query_one(NodeList)
        if node_list._rows and self.selected_row is None:
            node_list.index = 0
            self._select_row(node_list.row_for_index(0))
        self._restore_node_list_focus()
        self._refresh_details()

    def on_show(self) -> None:
        self.workflow_adapter.bind_state_owner(self.app)
        self._restore_editor_state_from_app()
        if self.is_mounted:
            self.refresh_from_backend()

    def refresh_from_backend(self) -> None:
        """Reload screen widgets from backend state."""
        if self._refreshing_from_backend:
            return
        self._refreshing_from_backend = True
        try:
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
                            "node": self._node_for_display(self.selected_node_id, node),
                            "loose": True,
                        }
                    )
            node_list = self.query_one(NodeList)
            node_list.refresh_rows(rows, timings=self._average_node_timings())
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
            self._restore_node_list_focus()
            self._refresh_details()
            self._persist_editor_state()
        finally:
            self._refreshing_from_backend = False

    def on_list_view_selected(self, event) -> None:
        node_list = self.query_one(NodeList)
        self._select_row(node_list.row_for_index(event.list_view.index))
        self._refresh_details()
        self.action_edit_selected()

    def on_list_view_highlighted(self, event) -> None:
        node_list = self.query_one(NodeList)
        self._select_row(node_list.row_for_index(event.list_view.index))
        self._refresh_details()

    def on_node_card_clicked(self, event: NodeCard.Clicked) -> None:
        """Single click selects a node; double click opens its config."""
        self._branch_cycle_anchor = None
        node_list = self.query_one(NodeList)
        index = node_list.index_for_node_id(event.node_id)
        if index is None:
            return
        node_list.index = index
        self.app.set_focus(node_list)
        self._select_row(node_list.row_for_index(index))
        self._refresh_details()
        if event.chain >= 2:
            self.action_edit_selected()

    def on_branch_select_card_clicked(self, event: BranchSelectCard.Clicked) -> None:
        """Single click selects a branch row; double click opens branch selection."""
        self._branch_cycle_anchor = f"{event.branch_node_id}:{event.active_port}"
        node_list = self.query_one(NodeList)
        index = node_list.index_for_branch_select(
            event.branch_node_id,
            event.active_port,
        )
        if index is None:
            return
        node_list.index = index
        self.app.set_focus(node_list)
        self._select_row(node_list.row_for_index(index))
        self._refresh_details()
        if event.chain >= 2:
            self.action_edit_selected()

    def on_merge_beacon_select_card_clicked(
        self, event: MergeBeaconSelectCard.Clicked
    ) -> None:
        """Single click selects a Merge Beacon row; double click opens selector."""
        node_list = self.query_one(NodeList)
        index = node_list.index_for_merge_beacon_select(event.beacon_node_id)
        if index is None:
            return
        node_list.index = index
        self.app.set_focus(node_list)
        self._select_row(node_list.row_for_index(index))
        self._refresh_details()
        if event.chain >= 2:
            self.action_edit_selected()

    def action_add_node(self) -> None:
        self._pending_node_add_mode = "add"
        self.app.push_screen(NodeSelectorScreen(self.factory), self._add_node_from_modal)

    def action_insert_node(self) -> None:
        if self._selected_insert_target_is_merge_beacon():
            notifications.notify_info(self.app, "Merge Beacon is the end of this branch")
            return
        self._pending_node_add_mode = "insert"
        self.app.push_screen(NodeSelectorScreen(self.factory), self._add_node_from_modal)

    def _selected_insert_target_is_merge_beacon(self) -> bool:
        if self.selected_row and self.selected_row["kind"] == "merge_beacon_select":
            return True
        if not self.selected_node_id:
            return False
        node = self.workflow_map.get_node_data(self.selected_node_id) or {}
        return node.get("type") == "branch_end_node"

    def action_cycle_branch_prev(self) -> None:
        self._restore_node_list_focus()
        self._cycle_branch_view(incomplete_only=False, direction=-1)

    def action_cycle_branch_next(self) -> None:
        self._restore_node_list_focus()
        self._cycle_branch_view(incomplete_only=False, direction=1)

    def action_cycle_incomplete_branch_prev(self) -> None:
        self._restore_node_list_focus()
        self._cycle_branch_view(incomplete_only=True, direction=-1)

    def action_cycle_incomplete_branch_next(self) -> None:
        self._restore_node_list_focus()
        self._cycle_branch_view(incomplete_only=True, direction=1)

    def action_validate_workflow(self) -> None:
        self.workflow_adapter.materialize_deleted_nodes()
        self.refresh_from_backend()
        result = validate_workflow(
            self.workflow_map,
            self.factory,
            secrets_manager=self.secrets_manager,
        )
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        if not errors and not warnings:
            notifications.workflow_valid(self.app)
            return
        self.app.push_screen(
            ErrorDetailsScreen({"validation": result}),
            self._handle_validation_details_result,
        )

    def action_workflow_library(self) -> None:
        self.app.action_workflow_library()

    def action_options(self) -> None:
        self.app.action_settings()

    def action_help(self) -> None:
        self.app.action_help()

    def action_save_workflow(self) -> None:
        self.workflow_adapter.materialize_deleted_nodes()
        self.app.action_save_workflow()

    def action_toggle_breakpoint(self) -> None:
        if self.selected_node_id is None:
            notifications.no_node_selected(self.app)
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            notifications.no_node_selected(self.app)
            return
        enabled = not bool(node.get("breakpoint"))
        self.workflow_map.set_breakpoint(self.selected_node_id, enabled)
        self.refresh_from_backend()
        notifications.breakpoint_toggled(self.app, enabled)

    def action_clear_breakpoints(self) -> None:
        cleared = self.workflow_map.clear_all_breakpoints()
        self.refresh_from_backend()
        notifications.breakpoints_cleared(self.app, cleared)

    def action_edit_selected(self) -> None:
        self._restore_node_list_focus()
        if self.selected_row and self.selected_row["kind"] == "merge_beacon_select":
            self._open_merge_beacon_selector(self.selected_row)
            return
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            self._open_branch_selector(self.selected_row)
            return
        if self.selected_node_id is None:
            notifications.no_node_selected(self.app)
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            notifications.no_node_selected(self.app)
            return
        # Tombstone nodes open the NodeSelector to pick a replacement
        if self.workflow_adapter.is_placeholder(self.selected_node_id):
            self.app.push_screen(
                NodeSelectorScreen(self.factory),
                self._replace_tombstone_from_modal,
            )
            return
        self.app.push_screen(
            NodeConfigScreen(
                self.factory,
                self.workflow_map,
                self.selected_node_id,
                node,
                memory_bank=getattr(self.app, "memory_bank", None),
            ),
            self._save_node_config_from_modal,
        )

    def action_undo_delete(self) -> None:
        self._restore_node_list_focus()
        if self.selected_node_id is None:
            notifications.no_node_selected(self.app)
            return
        if not self.workflow_adapter.is_placeholder(self.selected_node_id):
            return
        if not self.workflow_adapter.undo_placeholder(self.selected_node_id):
            notifications.notify_info(self.app, "Deleted node cannot be restored")
            return
        self.refresh_from_backend()
        notifications.notify_info(self.app, "Deleted node restored")

    def action_delete_selected(self) -> None:
        if self.selected_node_id is None:
            notifications.no_node_selected(self.app)
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            notifications.no_node_selected(self.app)
            return
        if node.get("type") == "start_node":
            notifications.cannot_delete_start_node(self.app)
            return
        if self._is_protected_structural_node(node):
            notifications.cannot_delete_structural_node(self.app)
            return

        self._do_delete(True)

    def _do_delete(self, confirmed: bool) -> None:
        if not confirmed or self.selected_node_id is None:
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node and self.workflow_adapter.is_placeholder(self.selected_node_id):
            if node.get("type") == "branch_end_node":
                self._prune_merge_config_for_beacon(self.selected_node_id)
            removed = self.workflow_adapter.remove_placeholder(self.selected_node_id)
            if removed:
                self.selected_node_id = None
                self.selected_row = None
                self.refresh_from_backend()
                notifications.tombstone_removed(self.app)
            return
        self.workflow_adapter.replace_with_placeholder(self.selected_node_id)
        self.refresh_from_backend()
        notifications.node_deleted(self.app)

    def _replace_tombstone_from_modal(self, node_type: str | None) -> None:
        if not node_type or self.selected_node_id is None:
            return
        result = self.workflow_adapter.replace_placeholder(
            self.selected_node_id,
            node_type,
        )
        if not result.get("replaced"):
            return
        if result.get("original_type") == "branch_end_node" and node_type != "branch_end_node":
            self._prune_merge_config_for_beacon(self.selected_node_id)
        if not result.get("restored_original"):
            self._clear_timing_for_node(self.selected_node_id)
        self.refresh_from_backend()
        notifications.node_replaced(self.app, node_type)

    def _prune_merge_config_for_beacon(self, beacon_node_id: str) -> None:
        stale_keys = self._branch_keys_for_beacon(beacon_node_id)
        self._disconnect_beacon_merge_outputs(beacon_node_id)
        if not stale_keys:
            return
        for merge_id, merge_node in self.workflow_map.get_all_node_data().items():
            if merge_node.get("type") != "merge_node":
                continue
            config = dict(merge_node.get("config") or {})
            branches = [
                str(value)
                for value in config.get("branches_to_close", [])
                if str(value) and str(value) not in stale_keys
            ]
            changed = branches != [
                str(value)
                for value in config.get("branches_to_close", [])
                if str(value)
            ]
            for key in ("carry_forward_branch_id", "selected_branch_id"):
                if str(config.get(key) or "") in stale_keys:
                    config[key] = ""
                    changed = True
            if str(config.get("selected_input_port") or "") and changed:
                config["selected_input_port"] = ""
            if changed:
                config["branches_to_close"] = branches
                self.workflow_map.update_node_config(merge_id, config)

    def _disconnect_beacon_merge_outputs(self, beacon_node_id: str) -> None:
        beacon_node = self.workflow_map.get_node_data(beacon_node_id) or {}
        for conn in list(beacon_node.get("connections", {}).get("outputs", [])):
            target_id = str(conn.get("target_node_id") or "")
            target_node = self.workflow_map.get_node_data(target_id) or {}
            if target_node.get("type") != "merge_node":
                continue
            self.workflow_map.disconnect(
                beacon_node_id,
                str(conn.get("source_port", "default") or "default"),
                target_id,
                str(conn.get("target_port") or "path_a"),
            )

    def _branch_keys_for_beacon(self, beacon_node_id: str) -> set[str]:
        keys: set[str] = set()
        for candidate in self._branch_view_candidates():
            if self._branch_path_contains(
                candidate["branch_node_id"],
                candidate["port"],
                beacon_node_id,
            ):
                keys.add(self._branch_candidate_key(candidate))
        return keys

    def _is_protected_structural_node(self, node: Dict[str, Any]) -> bool:
        if node.get("type") not in {"branch_node", "merge_node"}:
            return False
        return bool(node.get("connections", {}).get("outputs"))

    def _clear_timing_for_node(self, node_id: str) -> None:
        timings = getattr(self.app, "node_timings", None)
        if isinstance(timings, dict):
            timings.pop(node_id, None)

    def action_cursor_up(self) -> None:
        self._branch_cycle_anchor = None
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._branch_cycle_anchor = None
        self._move_selection(1)

    def _add_node_from_modal(self, node_type: str | None) -> None:
        insert_mode = self._pending_node_add_mode == "insert"
        self._pending_node_add_mode = "add"
        if not node_type:
            return
        if insert_mode:
            source = self._source_for_insert_node()
        else:
            source = self._source_for_new_node()
        node_id = self.workflow_map.add_node(node_type)
        if node_id is None:
            notifications.unknown_node_type(self.app, node_type)
            return
        if source is not None:
            self._connect_new_node(source["node_id"], source["port"], node_id)
        self.selected_node_id = node_id
        self.selected_row = {"kind": "node", "node_id": node_id}
        self.refresh_from_backend()
        notifications.node_added(self.app, inserted=insert_mode)

    def _save_node_config_from_modal(self, result: Dict[str, Any] | None) -> None:
        if not result or self.selected_node_id is None:
            return
        alias = str(result.get("alias", "")).strip()
        config = result.get("config", {})
        self.workflow_map.update_node_alias(self.selected_node_id, alias)
        self.workflow_map.update_node_config(self.selected_node_id, config)
        node = self.workflow_map.get_node_data(self.selected_node_id) or {}
        if node.get("type") == "merge_node":
            self._sync_merge_branch_end_connections(
                self.selected_node_id,
                config,
                reconcile_unselected=True,
            )
        self.refresh_from_backend()
        notifications.node_updated(self.app)

    def _handle_validation_details_result(self, result: Dict[str, Any] | None) -> None:
        if not result or result.get("action") != "jump":
            return
        node_id = result.get("node_id")
        if not node_id or self.workflow_map.get_node_data(node_id) is None:
            return
        self.selected_node_id = node_id
        self.selected_row = {"kind": "node", "node_id": node_id}
        self.refresh_from_backend()
        notifications.jumped_to_node(self.app, node_id)

    def _sync_merge_branch_end_connections(
        self,
        merge_node_id: str,
        config: Dict[str, Any],
        reconcile_unselected: bool = False,
    ) -> None:
        selected = {
            str(value)
            for value in config.get("branches_to_close", [])
            if str(value)
        }
        for option in merge_input_options(self.workflow_map, merge_node_id):
            option_value = f"{option['branch_id']}:{option['branch_port']}"
            source_id = option.get("branch_end_id", "")
            source_node = self.workflow_map.get_node_data(source_id) if source_id else None
            if not source_node or source_node.get("type") != "branch_end_node":
                continue
            source_port = option.get("source_port") or "default"
            target_port = option.get("port") or "path_a"
            if option_value not in selected:
                if reconcile_unselected and self._merge_input_connection_exists(
                    source_id,
                    source_port,
                    merge_node_id,
                    target_port,
                ):
                    self.workflow_map.disconnect(
                        source_id,
                        source_port,
                        merge_node_id,
                        target_port,
                    )
                continue
            self._replace_merge_input_connection(
                source_id,
                source_port,
                merge_node_id,
                target_port,
            )

    def _sync_all_merge_branch_end_connections(self) -> None:
        for node_id, node in self.workflow_map.get_all_node_data().items():
            if node.get("type") != "merge_node":
                continue
            self._repair_merge_input_ports(node_id)
            self._sync_merge_branch_end_connections(
                node_id,
                node.get("config") or {},
            )

    def _repair_merge_input_ports(self, merge_node_id: str) -> None:
        merge_node = self.workflow_map.get_node_data(merge_node_id) or {}
        metadata = self._metadata_for_type(merge_node.get("type", ""))
        declared_inputs = list(metadata.get("input_ports") or []) if metadata else []
        if not declared_inputs:
            return
        for conn in list(merge_node.get("connections", {}).get("inputs", [])):
            current_port = str(conn.get("target_port") or "")
            if current_port in declared_inputs:
                continue
            source_id = str(conn.get("source_node_id") or "")
            source_port = str(conn.get("source_port", "default") or "default")
            repaired_port = self._target_input_port_for_connection(
                source_id,
                source_port,
                merge_node_id,
                declared_inputs,
            )
            self.workflow_map.disconnect(
                source_id,
                source_port,
                merge_node_id,
                current_port,
            )
            self._replace_merge_input_connection(
                source_id,
                source_port,
                merge_node_id,
                repaired_port,
            )

    def _replace_merge_input_connection(
        self,
        source_node_id: str,
        source_port: str,
        merge_node_id: str,
        target_port: str,
    ) -> None:
        source = self.workflow_map.get_node_data(source_node_id) or {}
        existing_output = self._connection_for_port(source, source_port)
        if (
            existing_output
            and existing_output.get("target_node_id") == merge_node_id
            and existing_output.get("target_port") == target_port
            and self._merge_input_connection_exists(
                source_node_id,
                source_port,
                merge_node_id,
                target_port,
            )
        ):
            return
        if existing_output:
            self.workflow_map.disconnect(
                source_node_id,
                source_port,
                existing_output.get("target_node_id", ""),
                existing_output.get("target_port", "input"),
            )

        merge_node = self.workflow_map.get_node_data(merge_node_id) or {}
        for conn in list(merge_node.get("connections", {}).get("inputs", [])):
            if conn.get("target_port") != target_port:
                continue
            self.workflow_map.disconnect(
                conn.get("source_node_id", ""),
                conn.get("source_port", "default"),
                merge_node_id,
                target_port,
            )

        self.workflow_map.connect(source_node_id, source_port, merge_node_id, target_port)

    def _merge_input_connection_exists(
        self,
        source_node_id: str,
        source_port: str,
        merge_node_id: str,
        target_port: str,
    ) -> bool:
        merge_node = self.workflow_map.get_node_data(merge_node_id) or {}
        for conn in merge_node.get("connections", {}).get("inputs", []):
            if (
                conn.get("source_node_id") == source_node_id
                and conn.get("source_port", "default") == source_port
                and conn.get("target_port") == target_port
            ):
                return True
        return False

    def _target_input_port_for_connection(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        input_ports: list[str],
    ) -> str:
        target_node = self.workflow_map.get_node_data(target_node_id) or {}
        if target_node.get("type") == "merge_node":
            branch_port = self._upstream_branch_port(source_node_id, source_port)
            if branch_port in input_ports:
                return branch_port
        return input_ports[0]

    def _upstream_branch_port(self, source_node_id: str, source_port: str) -> str:
        node = self.workflow_map.get_node_data(source_node_id) or {}
        metadata = self._metadata_for_type(node.get("type", ""))
        output_ports = self._output_ports_for_node(node, metadata)
        if len(output_ports) > 1 and source_port in output_ports:
            return source_port

        visited: set[str] = set()
        stack = [source_node_id]
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            current = self.workflow_map.get_node_data(node_id) or {}
            for input_conn in current.get("connections", {}).get("inputs", []):
                upstream_id = str(input_conn.get("source_node_id") or "")
                upstream_node = self.workflow_map.get_node_data(upstream_id) or {}
                upstream_meta = self._metadata_for_type(upstream_node.get("type", ""))
                upstream_outputs = self._output_ports_for_node(upstream_node, upstream_meta)
                upstream_port = str(input_conn.get("source_port", "default") or "default")
                if len(upstream_outputs) > 1:
                    return upstream_port
                if upstream_id:
                    stack.append(upstream_id)
        return source_port

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
        notifications.viewing_branch(self.app, branch_label)

    def _open_merge_beacon_selector(self, row: Dict[str, Any]) -> None:
        beacon_node_id = row["beacon_node_id"]
        options = self._merge_beacon_options(beacon_node_id)
        if not options:
            notifications.notify_info(self.app, "No other merge nodes available")
            return
        self.app.push_screen(
            MergeBeaconSelectorScreen(
                beacon_node_id=beacon_node_id,
                options=options,
                active_merge_id=self._merge_beacon_connected_merge_id(beacon_node_id),
            ),
            self._select_merge_from_beacon_modal,
        )

    def _select_merge_from_beacon_modal(self, result: Dict[str, str] | None) -> None:
        if not result:
            return
        merge_node_id = result.get("merge_node_id")
        if not merge_node_id or self.workflow_map.get_node_data(merge_node_id) is None:
            notifications.notify_info(self.app, "Merge node is not available")
            return
        branch_choices = self._branch_choices_to_node(merge_node_id)
        if not branch_choices:
            notifications.notify_info(self.app, "Merge node is not on another branch")
            return
        for ancestor_id, ancestor_port in branch_choices:
            self.active_branch_ports[ancestor_id] = ancestor_port
        visible_rows = self._build_visible_rows()
        if not any(
            row["kind"] == "node" and row.get("node_id") == merge_node_id
            for row in visible_rows
        ):
            notifications.notify_info(self.app, "Merge branch is not visible")
            return
        self.selected_node_id = merge_node_id
        self.selected_row = {"kind": "node", "node_id": merge_node_id}
        self.refresh_from_backend()
        notifications.jumped_to_node(self.app, merge_node_id)

    def _cycle_branch_view(self, incomplete_only: bool, direction: int) -> None:
        candidates = self._branch_view_candidates()
        if incomplete_only:
            candidates = [
                candidate
                for candidate in candidates
                if not candidate["closed"]
            ]
        if not candidates:
            notifications.notify_info(
                self.app,
                "No incomplete branches" if incomplete_only else "No branches",
            )
            return
        current_index = self._current_branch_candidate_index(candidates)
        next_index = (current_index + direction) % len(candidates)
        candidate = candidates[next_index]
        self._show_branch_candidate(candidate)
        notifications.viewing_branch(self.app, candidate["label"])

    def _branch_view_candidates(self) -> list[Dict[str, Any]]:
        candidates: list[Dict[str, Any]] = []
        nodes = self.workflow_map.get_all_node_data()
        for node_id, node in nodes.items():
            metadata = self._metadata_for_type(node.get("type", ""))
            output_ports = self._output_ports_for_node(node, metadata)
            if len(output_ports) <= 1:
                continue
            port_labels = self._branch_port_labels(node)
            for port in output_ports:
                tail_id, closed = self._branch_tail_and_closed_state(node_id, port)
                candidates.append(
                    {
                        "branch_node_id": node_id,
                        "port": port,
                        "label": port_labels.get(port, port),
                        "head_id": self._branch_head_for_branch(node_id, port),
                        "tail_id": tail_id,
                        "closed": closed,
                    }
                )
        return candidates

    def _branch_tail_and_closed_state(
        self, branch_node_id: str, branch_port: str
    ) -> tuple[str, bool]:
        nodes = self.workflow_map.get_all_node_data()
        current_node_id = self._target_for_port(nodes.get(branch_node_id, {}), branch_port)
        if current_node_id is None:
            return branch_node_id, False
        visited = {branch_node_id}
        tail_id = current_node_id
        closed = False
        while current_node_id and current_node_id not in visited:
            visited.add(current_node_id)
            tail_id = current_node_id
            node = nodes.get(current_node_id)
            if node is None:
                break
            node_type = node.get("type")
            if self._is_branch_terminal_node(node_type):
                closed = (
                    node_type != "branch_end_node"
                    or self._branch_end_connected_to_merge(node)
                )
                break
            metadata = self._metadata_for_type(node.get("type", ""))
            ports = self._output_ports_for_node(node, metadata)
            if len(ports or []) != 1:
                break
            current_node_id = self._target_for_port(node, ports[0])
        return tail_id, closed

    def _is_branch_terminal_node(self, node_type: str | None) -> bool:
        return node_type in {
            "branch_end_node",
            "end_node",
            "text_output_node",
            "merge_node",
        }

    def _current_branch_candidate_index(self, candidates: list[Dict[str, Any]]) -> int:
        if self._branch_cycle_anchor:
            for index, candidate in enumerate(candidates):
                if self._branch_candidate_key(candidate) == self._branch_cycle_anchor:
                    return index
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            for index, candidate in enumerate(candidates):
                if (
                    candidate["branch_node_id"] == self.selected_row.get("branch_node_id")
                    and candidate["port"] == self.selected_row.get("active_port")
                ):
                    return index
        if self.selected_node_id:
            for index, candidate in enumerate(candidates):
                if self._branch_path_contains(
                    candidate["branch_node_id"],
                    candidate["port"],
                    self.selected_node_id,
                ):
                    return index
        for index, candidate in enumerate(candidates):
            if self.active_branch_ports.get(candidate["branch_node_id"]) == candidate["port"]:
                return index
        return -1

    def _branch_path_contains(
        self,
        branch_node_id: str,
        branch_port: str,
        target_node_id: str,
    ) -> bool:
        nodes = self.workflow_map.get_all_node_data()
        current_node_id = self._target_for_port(nodes.get(branch_node_id, {}), branch_port)
        visited = {branch_node_id}
        while current_node_id and current_node_id not in visited:
            if current_node_id == target_node_id:
                return True
            visited.add(current_node_id)
            node = nodes.get(current_node_id)
            if node is None:
                return False
            if node.get("type") == "branch_end_node":
                return False
            metadata = self._metadata_for_type(node.get("type", ""))
            ports = self._output_ports_for_node(node, metadata)
            if len(ports or []) != 1:
                return False
            current_node_id = self._target_for_port(node, ports[0])
        return False

    def _branch_head_for_branch(
        self,
        branch_node_id: str,
        branch_port: str,
    ) -> str:
        nodes = self.workflow_map.get_all_node_data()
        return self._target_for_port(nodes.get(branch_node_id, {}), branch_port) or branch_node_id

    def _show_branch_candidate(self, candidate: Dict[str, Any]) -> None:
        branch_node_id = candidate["branch_node_id"]
        branch_port = candidate["port"]
        self._branch_cycle_anchor = self._branch_candidate_key(candidate)
        for ancestor_id, ancestor_port in self._branch_choices_to_node(branch_node_id):
            self.active_branch_ports[ancestor_id] = ancestor_port
        self.active_branch_ports[branch_node_id] = branch_port

        branch_key = self._branch_candidate_key(candidate)
        remembered_id = self.last_branch_selection.get(branch_key)
        visible_rows = self._build_visible_rows()
        selected_row = self._row_for_branch_switch(
            visible_rows,
            branch_node_id,
            branch_port,
            remembered_id,
            candidate.get("head_id"),
        )
        self.selected_row = selected_row
        self.selected_node_id = (
            selected_row.get("node_id")
            if selected_row and selected_row["kind"] == "node"
            else None
        )
        self._persist_editor_state()
        self.refresh_from_backend()

    def _row_for_branch_switch(
        self,
        rows: list[Dict[str, Any]],
        branch_node_id: str,
        branch_port: str,
        remembered_id: Optional[str],
        head_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if remembered_id:
            for row in rows:
                if row["kind"] == "node" and row.get("node_id") == remembered_id:
                    return row
        if head_id:
            for row in rows:
                if row["kind"] == "node" and row.get("node_id") == head_id:
                    return row
        for row in rows:
            if (
                row["kind"] == "branch_select"
                and row.get("branch_node_id") == branch_node_id
                and row.get("active_port") == branch_port
            ):
                return row
        for row in rows:
            if row["kind"] == "node" and row.get("node_id") == branch_node_id:
                return row
        return rows[0] if rows else None

    def _branch_choices_to_node(self, target_node_id: str) -> list[tuple[str, str]]:
        start_node_id = self.workflow_map.find_start_node_id()
        if not start_node_id or start_node_id == target_node_id:
            return []
        visited: set[str] = set()
        result = self._find_branch_choices_to_node(
            start_node_id,
            target_node_id,
            [],
            visited,
        )
        return result or []

    def _find_branch_choices_to_node(
        self,
        current_node_id: str,
        target_node_id: str,
        choices: list[tuple[str, str]],
        visited: set[str],
    ) -> Optional[list[tuple[str, str]]]:
        if current_node_id == target_node_id:
            return list(choices)
        if current_node_id in visited:
            return None
        visited.add(current_node_id)
        node = self.workflow_map.get_node_data(current_node_id)
        if node is None:
            return None
        if node.get("type") == "branch_end_node":
            return None
        metadata = self._metadata_for_type(node.get("type", ""))
        output_ports = self._output_ports_for_node(node, metadata)
        for port in output_ports:
            target = self._target_for_port(node, port)
            if not target:
                continue
            next_choices = list(choices)
            if len(output_ports) > 1:
                next_choices.append((current_node_id, port))
            result = self._find_branch_choices_to_node(
                target,
                target_node_id,
                next_choices,
                set(visited),
            )
            if result is not None:
                return result
        return None

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
        target_port = self._target_input_port_for_connection(
            source_node_id,
            source_port,
            target_node_id,
            list(input_ports),
        )
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
            target_port,
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
            text = self._format_branch_selector_details(self.selected_row)
            setattr(detail, "display_text", text)
            detail.update(text)
            return
        if self.selected_row and self.selected_row["kind"] == "merge_beacon_select":
            text = self._format_merge_beacon_selector_details(self.selected_row)
            setattr(detail, "display_text", text)
            detail.update(text)
            return
        if self.selected_node_id is None:
            text = "No node selected"
            setattr(detail, "display_text", text)
            detail.update(text)
            return
        node = self.workflow_map.get_node_data(self.selected_node_id)
        if node is None:
            text = "No node selected"
            setattr(detail, "display_text", text)
            detail.update(text)
            return
        text = self._format_node_details(self.selected_node_id, node)
        setattr(detail, "display_text", text)
        detail.update(text)

    def _format_node_details(self, node_id: str, node: Dict[str, Any]) -> str:
        metadata = self._metadata_for_type(node.get("type", ""))
        kind = metadata.get("display_name") if metadata else node.get("type", "unknown")
        lines = [
            f"Name: {self._node_label(node_id, node)}",
            f"Kind: {kind}",
            f"Family: {self._metadata_family(metadata)}",
            f"Subcategories: {self._metadata_subcategories(metadata)}",
            f"Step: {self._selected_depth_text()}",
            f"Breakpoint: {'on' if node.get('breakpoint') else 'off'}",
        ]
        if node.get("type") == "branch_end_node":
            lines.extend(self._branch_end_merge_detail_lines(node_id, node))
        if metadata:
            description = str(metadata.get("description", "")).strip()
            if description:
                lines.append(f"About: {description}")
        average_timing = self._average_node_timings().get(node_id)
        if average_timing is not None:
            lines.append(f"Avg time: {self._format_timing(average_timing)}")
        lines.extend(self._format_io_summary(node_id, node, metadata))
        return "\n".join(lines)

    def _format_io_summary(
        self,
        node_id: str,
        node: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
    ) -> list[str]:
        return [
            "",
            "Inputs:",
            *self._format_transient_input_lines(node),
            "  Memory",
            *self._format_memory_lines(node, "inputs"),
            "",
            "Outputs:",
            "  Transient",
            *self._format_transient_output_lines(node, metadata),
            "  Memory",
            *self._format_memory_lines(node, "outputs"),
        ]

    def _format_transient_input_lines(self, node: Dict[str, Any]) -> list[str]:
        inputs = node.get("connections", {}).get("inputs", [])
        if not inputs:
            return ["  Transient Source: none"]
        lines: list[str] = []
        for conn in inputs:
            source_id = str(conn.get("source_node_id") or "")
            source_port = str(conn.get("source_port") or "default")
            producer = trace_transient_producer(
                self.workflow_map,
                self.factory,
                source_id,
                source_port,
            )
            producer_node = producer.get("node") or {}
            producer_id = producer.get("node_id") or source_id or "?"
            lines.append(
                f"  Transient Source: {node_display_name(producer_id, producer_node)}"
            )
            lines.append(
                f"    {producer['name']}: {producer.get('description') or ''}"
            )
        return lines

    def _format_transient_output_lines(
        self,
        node: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
    ) -> list[str]:
        ports = self._output_ports_for_node(node, metadata)
        if not ports:
            return ["    none"]
        lines: list[str] = []
        for port in ports:
            description = output_display_description(self.factory, node, str(port))
            lines.append(
                f"    {output_display_name(self.factory, node, str(port))}: {description}"
            )
        return lines

    def _format_memory_lines(self, node: Dict[str, Any], direction: str) -> list[str]:
        def line(name: str, description: str = "") -> str:
            return f"    {name}: {description}" if description else f"    {name}:"

        if direction == "inputs":
            selected = normalize_membank_inputs(node.get("config") or {})
            if not selected:
                return ["    none"]
            registry = memory_registry(self.workflow_map)
            return [
                line(output_id, (registry.get(output_id) or {}).get("description", ""))
                for output_id in selected
            ]
        outputs = normalize_membank_outputs(node.get("config") or {})
        if not outputs:
            return ["    none"]
        return [
            line(output["id"], output.get("description", ""))
            for output in outputs
        ]

    def _branch_end_merge_detail_lines(
        self, node_id: str, node: Dict[str, Any]
    ) -> list[str]:
        for conn in node.get("connections", {}).get("outputs", []):
            target_id = str(conn.get("target_node_id") or "")
            target_node = self.workflow_map.get_node_data(target_id) or {}
            if target_node.get("type") != "merge_node":
                continue
            target_port = str(conn.get("target_port") or "default")
            branch_label, branch_id = upstream_branch_info(
                self.workflow_map,
                node_id,
                target_id,
                target_port,
            )
            return [
                f"Merges To Branch: {branch_label} ({branch_id})",
                f"Merge Node: {self._node_label(target_id, target_node)}",
            ]
        return ["Merges To Branch: -", "Merge Node: -"]

    def _selected_depth_text(self) -> str:
        if self.selected_row and self.selected_row.get("depth") is not None:
            return str(self.selected_row["depth"])
        if self.selected_node_id:
            for row in self.query_one(NodeList)._rows:
                if row["kind"] == "node" and row.get("node_id") == self.selected_node_id:
                    depth = row.get("depth")
                    return str(depth) if depth is not None else "-"
        return "-"

    def _average_node_timings(self) -> Dict[str, float]:
        try:
            master_state = getattr(self.app, "master_state", None)
        except Exception:
            return {}
        run_history = getattr(master_state, "run_history", None)
        if run_history is None:
            return {}
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for run in run_history.list_runs():
            timings = run.get("node_timings") or {}
            if not isinstance(timings, dict):
                continue
            for node_id, seconds in timings.items():
                try:
                    value = float(seconds)
                except (TypeError, ValueError):
                    continue
                totals[node_id] = totals.get(node_id, 0.0) + value
                counts[node_id] = counts.get(node_id, 0) + 1
        return {
            node_id: totals[node_id] / counts[node_id]
            for node_id in totals
            if counts.get(node_id)
        }

    def _format_timing(self, seconds: float) -> str:
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        return f"{seconds:.2f}s"

    def _metadata_for_type(self, node_type: str) -> Optional[Dict[str, Any]]:
        for item in self.factory.get_node_types_metadata():
            if item["type"] == node_type:
                return item
        return None

    def _metadata_family(self, metadata: Optional[Dict[str, Any]]) -> str:
        if not metadata:
            return "Unknown"
        return str(metadata.get("primary_family") or metadata.get("category") or "Unknown")

    def _metadata_subcategories(self, metadata: Optional[Dict[str, Any]]) -> str:
        if not metadata:
            return "none"
        tags = [str(tag) for tag in metadata.get("tags") or [] if str(tag)]
        return ", ".join(tags) if tags else "none"

    def _output_ports_for_node(
        self,
        node: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> list[str]:
        metadata = metadata or self._metadata_for_type(node.get("type", ""))
        ports = [str(port) for port in (metadata.get("output_ports") if metadata else []) or []]
        if node.get("type") == "branch_node":
            config = node.get("config") or {}
            try:
                count = int(config.get("branch_count", 2))
            except (TypeError, ValueError):
                count = 2
            return ports[: max(2, min(5, count))]
        return ports

    def _node_label(self, node_id: str, node: Dict[str, Any]) -> str:
        return node_label(node_id, node)

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
        ports = self._output_ports_for_node(node, metadata)
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
        metadata = self._metadata_for_type(node.get("type", ""))
        labels: Dict[str, str] = {}
        for port in self._output_ports_for_node(node, metadata):
            labels[port] = output_display_name(self.factory, node, str(port))
        return labels

    def _select_row(self, row: Optional[Dict[str, Any]]) -> None:
        self.selected_row = row
        self.selected_node_id = (
            row.get("node_id") if row and row["kind"] == "node" else None
        )
        if self.selected_node_id:
            self._remember_branch_selection(self.selected_node_id)
        self._persist_editor_state()

    def _restore_node_list_focus(self) -> None:
        node_list = self.query_one(NodeList)
        index = self._index_for_selected_row(node_list)
        if index is None and node_list._rows:
            index = (
                node_list.index
                if node_list.index is not None and 0 <= node_list.index < len(node_list._rows)
                else 0
            )
            self._select_row(node_list.row_for_index(index))
        if index is not None:
            node_list.index = index
            node_list.scroll_visible(animate=False)
        node_list.normalize_highlight()
        self.app.set_focus(node_list)

    def _persist_editor_state(self) -> None:
        try:
            app = self.app
        except Exception:
            return
        selected_row = dict(self.selected_row) if self.selected_row else None
        setattr(
            app,
            "_editor_selection_state",
            {
                "selected_node_id": self.selected_node_id,
                "selected_row": selected_row,
                "active_branch_ports": dict(self.active_branch_ports),
                "last_branch_selection": dict(self.last_branch_selection),
            },
        )

    def _restore_editor_state_from_app(self) -> None:
        try:
            state = getattr(self.app, "_editor_selection_state", None)
        except Exception:
            return
        if not isinstance(state, dict):
            return
        active_branch_ports = state.get("active_branch_ports")
        if isinstance(active_branch_ports, dict):
            self.active_branch_ports.update(
                {str(key): str(value) for key, value in active_branch_ports.items()}
            )
        last_branch_selection = state.get("last_branch_selection")
        if isinstance(last_branch_selection, dict):
            self.last_branch_selection.update(
                {str(key): str(value) for key, value in last_branch_selection.items()}
            )
        selected_row = state.get("selected_row")
        if isinstance(selected_row, dict):
            self.selected_row = dict(selected_row)
        selected_node_id = state.get("selected_node_id")
        self.selected_node_id = str(selected_node_id) if selected_node_id else None

    def _move_selection(self, delta: int) -> None:
        self._restore_node_list_focus()
        node_list = self.query_one(NodeList)
        if not node_list._rows:
            return
        current = node_list.index if node_list.index is not None else 0
        next_index = node_list.next_selectable_index(current, delta)
        if next_index is None:
            return
        node_list.index = next_index
        node_list.scroll_visible(animate=False)
        self._select_row(node_list.row_for_index(next_index))
        self._refresh_details()
        node_list.normalize_highlight()
        self.app.set_focus(node_list)

    def _build_visible_rows(self) -> list[Dict[str, Any]]:
        nodes = self.workflow_map.get_all_node_data()
        if self._hidden_empty_start_node_id(nodes):
            return []
        start_node_id = self.workflow_map.find_start_node_id() or next(iter(nodes), None)
        rows: list[Dict[str, Any]] = []
        visited: set[str] = set()
        current_node_id = start_node_id
        depth = 0
        current_branch_port: str | None = "path_a"
        current_branch_color_key: str | None = branch_path_color_key(0, "path_a")
        branch_index = 0

        while current_node_id and current_node_id not in visited:
            node = nodes.get(current_node_id)
            if node is None:
                break
            visited.add(current_node_id)
            node = self._node_for_display(current_node_id, node)
            node = dict(node)
            node["_editor_depth"] = depth
            metadata = self._metadata_for_type(node.get("type", ""))
            node["_editor_gap_marker"] = self._gap_marker_for_node(node, metadata)
            if current_branch_port:
                node["_editor_branch_port"] = current_branch_port
            if current_branch_color_key:
                node["_editor_branch_color_key"] = current_branch_color_key
            rows.append(
                {
                    "kind": "node",
                    "node_id": current_node_id,
                    "node": node,
                    "depth": depth,
                }
            )

            if self.workflow_adapter.is_placeholder(current_node_id):
                break

            if node.get("type") == "branch_end_node":
                rows.append(
                    self._merge_beacon_select_row(
                        current_node_id,
                        depth,
                        current_branch_color_key,
                    )
                )
                break

            output_ports = self._output_ports_for_node(node, metadata)
            if len(output_ports) > 1:
                active_port = self.active_branch_ports.get(current_node_id, output_ports[0])
                if active_port not in output_ports:
                    active_port = output_ports[0]
                self.active_branch_ports[current_node_id] = active_port
                port_labels = self._branch_port_labels(node)
                active_color_key = branch_path_color_key(branch_index, active_port)
                node["_editor_active_color_key"] = active_color_key
                merge_node_id = self._find_merge_for_branch(current_node_id, active_port)
                rows.append(
                    {
                        "kind": "branch_select",
                        "branch_node_id": current_node_id,
                        "active_port": active_port,
                        "active_color_key": active_color_key,
                        "active_label": port_labels.get(active_port, active_port),
                        "output_ports": output_ports,
                        "port_labels": port_labels,
                        "depth": depth,
                        "merge_node_id": merge_node_id,
                    }
                )
                current_node_id = self._target_for_port(node, active_port)
                current_branch_port = active_port
                current_branch_color_key = active_color_key
                branch_index += 1
                depth += 1
                continue

            next_port = "default"
            if output_ports:
                next_port = output_ports[0]
            current_node_id = self._target_for_port(node, next_port)
            depth += 1
        return rows

    def _gap_marker_for_node(
        self,
        node: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        config = node.get("config") or {}
        markers = ""
        if self._output_ports_for_node(node, metadata):
            markers += "▼ "
        vault_output_count = len(normalize_membank_outputs(config))
        if vault_output_count > 0:
            markers += f"➥ ({vault_output_count})"
        return markers or "▼ "

    def _hidden_empty_start_node_id(
        self, nodes: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Optional[str]:
        nodes = nodes if nodes is not None else self.workflow_map.get_all_node_data()
        if len(nodes) != 1:
            return None
        node_id, node = next(iter(nodes.items()))
        if node.get("type") != "start_node":
            return None
        outputs = node.get("connections", {}).get("outputs", [])
        return None if outputs else node_id

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

    def _branch_end_connected_to_merge(self, node: Dict[str, Any]) -> bool:
        for conn in node.get("connections", {}).get("outputs", []):
            target_id = conn.get("target_node_id")
            target_node = self.workflow_map.get_node_data(target_id) if target_id else None
            if target_node and target_node.get("type") == "merge_node":
                return True
        return False

    def _find_merge_for_branch(self, branch_node_id: str, port: str) -> str:
        """Return the merge node ID that the given branch port ultimately connects to."""
        tail_id = self._tail_for_branch(branch_node_id, port)
        tail_node = self.workflow_map.get_node_data(tail_id) or {}
        if tail_node.get("type") == "branch_end_node":
            return self._merge_beacon_connected_merge_id(tail_id)
        return ""

    def _merge_beacon_connected_merge_id(self, beacon_node_id: str) -> str:
        beacon = self.workflow_map.get_node_data(beacon_node_id) or {}
        for conn in beacon.get("connections", {}).get("outputs", []):
            target_id = str(conn.get("target_node_id") or "")
            target_node = self.workflow_map.get_node_data(target_id) or {}
            if target_node.get("type") == "merge_node":
                return target_id
        return ""

    def _merge_beacon_select_row(
        self,
        beacon_node_id: str,
        depth: int,
        active_color_key: str | None = None,
    ) -> Dict[str, Any]:
        connected_merge_id = self._merge_beacon_connected_merge_id(beacon_node_id)
        label = "Choose merge"
        if connected_merge_id:
            merge_node = self.workflow_map.get_node_data(connected_merge_id) or {}
            label = node_display_name(connected_merge_id, merge_node)
        return {
            "kind": "merge_beacon_select",
            "beacon_node_id": beacon_node_id,
            "active_merge_id": connected_merge_id,
            "active_label": label,
            "active_port": self._upstream_branch_port_for_node(beacon_node_id),
            "active_color_key": active_color_key,
            "merge_node_id": connected_merge_id,
            "depth": depth,
        }

    def _upstream_branch_port_for_node(self, node_id: str) -> str:
        """Return the nearest upstream branch output port for display styling."""
        visited: set[str] = set()
        stack = [node_id]
        while stack:
            current_id = stack.pop()
            if current_id in visited:
                continue
            visited.add(current_id)
            node = self.workflow_map.get_node_data(current_id) or {}
            for input_conn in node.get("connections", {}).get("inputs", []):
                upstream_id = str(input_conn.get("source_node_id") or "")
                if not upstream_id:
                    continue
                upstream_node = self.workflow_map.get_node_data(upstream_id) or {}
                metadata = self._metadata_for_type(upstream_node.get("type", ""))
                upstream_outputs = self._output_ports_for_node(upstream_node, metadata)
                source_port = str(input_conn.get("source_port") or "default")
                if len(upstream_outputs) > 1:
                    return source_port
                stack.append(upstream_id)
        return "path_a"

    def _merge_beacon_options(self, beacon_node_id: str) -> list[Dict[str, str]]:
        options: list[Dict[str, str]] = []
        nodes = self.workflow_map.get_all_node_data()
        for merge_node_id, merge_node in nodes.items():
            if merge_node.get("type") != "merge_node":
                continue
            if not self._branch_choices_to_node(merge_node_id):
                continue
            if self._merge_on_current_beacon_branch(beacon_node_id, merge_node_id):
                continue
            options.append(
                {
                    "merge_node_id": merge_node_id,
                    "label": self._node_label(merge_node_id, merge_node),
                }
            )
        return options

    def _merge_on_current_beacon_branch(
        self,
        beacon_node_id: str,
        merge_node_id: str,
    ) -> bool:
        for candidate in self._branch_view_candidates():
            if not self._branch_path_contains(
                candidate["branch_node_id"],
                candidate["port"],
                beacon_node_id,
            ):
                continue
            if self._branch_path_contains_before_stop(
                candidate["branch_node_id"],
                candidate["port"],
                merge_node_id,
                beacon_node_id,
            ):
                return True
        return False

    def _branch_path_contains_before_stop(
        self,
        branch_node_id: str,
        branch_port: str,
        target_node_id: str,
        stop_node_id: str,
    ) -> bool:
        nodes = self.workflow_map.get_all_node_data()
        current_node_id = self._target_for_port(nodes.get(branch_node_id, {}), branch_port)
        visited = {branch_node_id}
        while current_node_id and current_node_id not in visited:
            if current_node_id == stop_node_id:
                return False
            if current_node_id == target_node_id:
                return True
            visited.add(current_node_id)
            node = nodes.get(current_node_id)
            if node is None:
                return False
            metadata = self._metadata_for_type(node.get("type", ""))
            ports = self._output_ports_for_node(node, metadata)
            if len(ports or []) != 1:
                return False
            current_node_id = self._target_for_port(node, ports[0])
        return False

    def _node_for_display(self, node_id: str, node: Dict[str, Any]) -> Dict[str, Any]:
        display_node = dict(node)
        if self.workflow_adapter.is_placeholder(node_id):
            metadata = self.workflow_adapter.placeholder_metadata(node_id)
            display_node["_deleted_overlay"] = {
                **metadata,
                "can_restore": self.workflow_adapter.placeholder_has_restore_data(node_id),
            }
            display_node["_identity"] = {
                "primary_family": "Outputs",
                "category": "Outputs",
                "tags": ["Passive Output", "Utility"],
            }
            return display_node
        metadata = self._metadata_for_type(display_node.get("type", ""))
        if metadata:
            display_node["_identity"] = {
                "primary_family": metadata.get("primary_family") or metadata.get("category"),
                "category": metadata.get("category"),
                "tags": list(metadata.get("tags") or []),
                "icon_name": metadata.get("icon_name"),
                "color_hint": metadata.get("color_hint"),
            }
        if node.get("type") == "branch_end_node":
            display_node["_branch_end_connected_to_merge"] = (
                self._branch_end_connected_to_merge(node)
            )
            display_node["_editor_merge_node_id"] = (
                self._merge_beacon_connected_merge_id(node_id)
            )
        return display_node

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
            if (
                row["kind"] == "merge_beacon_select"
                and row.get("beacon_node_id") == selected_row.get("beacon_node_id")
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
            if (
                row["kind"] == "merge_beacon_select"
                and row.get("beacon_node_id") == selected_row.get("beacon_node_id")
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
            if (
                row["kind"] == "merge_beacon_select"
                and row.get("beacon_node_id") == self.selected_row.get("beacon_node_id")
            ):
                return index
        return None

    def _source_for_new_node(self) -> Optional[Dict[str, str]]:
        hidden_start_id = self._hidden_empty_start_node_id()
        if hidden_start_id:
            return {"node_id": hidden_start_id, "port": "default"}
        if self.selected_row and self.selected_row["kind"] == "merge_beacon_select":
            return None
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            branch_node_id = self.selected_row["branch_node_id"]
            active_port = self.active_branch_ports.get(
                branch_node_id, self.selected_row["active_port"]
            )
            tail_id = self._tail_for_branch(branch_node_id, active_port)
            if tail_id != branch_node_id:
                tail = self.workflow_map.get_node_data(tail_id)
                tail_meta = self._metadata_for_type(tail.get("type", "")) if tail else None
                tail_ports = self._output_ports_for_node(tail, tail_meta) if tail else []
                return {"node_id": tail_id, "port": (tail_ports or ["default"])[0]}
            return {"node_id": branch_node_id, "port": active_port}
        if self.selected_node_id:
            node = self.workflow_map.get_node_data(self.selected_node_id)
            if node and node.get("type") == "branch_end_node":
                return None
            metadata = self._metadata_for_type(node.get("type", "")) if node else None
            ports = self._output_ports_for_node(node, metadata) if node else []
            return {"node_id": self.selected_node_id, "port": (ports or ["default"])[0]}
        return None

    def _source_for_insert_node(self) -> Optional[Dict[str, str]]:
        """Return the highlighted row source for insert-after behavior."""
        hidden_start_id = self._hidden_empty_start_node_id()
        if hidden_start_id:
            return {"node_id": hidden_start_id, "port": "default"}
        if self.selected_row and self.selected_row["kind"] == "merge_beacon_select":
            return {"node_id": self.selected_row["beacon_node_id"], "port": "default"}
        if self.selected_row and self.selected_row["kind"] == "branch_select":
            branch_node_id = self.selected_row["branch_node_id"]
            active_port = self.active_branch_ports.get(
                branch_node_id, self.selected_row["active_port"]
            )
            return {"node_id": branch_node_id, "port": active_port}
        if self.selected_node_id:
            node = self.workflow_map.get_node_data(self.selected_node_id)
            metadata = self._metadata_for_type(node.get("type", "")) if node else None
            ports = self._output_ports_for_node(node, metadata) if node else []
            return {"node_id": self.selected_node_id, "port": (ports or ["default"])[0]}
        return None

    def _branch_candidate_key(self, candidate: Dict[str, Any]) -> str:
        return f"{candidate['branch_node_id']}:{candidate['port']}"

    def _remember_branch_selection(self, node_id: str) -> None:
        for candidate in self._branch_view_candidates():
            if self._branch_path_contains(
                candidate["branch_node_id"],
                candidate["port"],
                node_id,
            ):
                self.last_branch_selection[self._branch_candidate_key(candidate)] = node_id

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
            if node.get("type") == "branch_end_node":
                break
            metadata = self._metadata_for_type(node.get("type", ""))
            ports = self._output_ports_for_node(node, metadata)
            if len(ports or []) != 1:
                break
            current_node_id = self._target_for_port(node, ports[0])
        return tail_id

    def _format_branch_selector_details(self, row: Dict[str, Any]) -> str:
        branch_node = self.workflow_map.get_node_data(row["branch_node_id"]) or {}
        target_id = self._target_for_port(branch_node, row["active_port"])
        branch_label = row.get("active_label") or row["active_port"]
        lines = [
            f"Branch: {branch_label}",
            f"From: {branch_node.get('alias') or row['branch_node_id']}",
            f"Step: {row.get('depth', '-')}",
            f"Next: {target_id or '-'}",
            "",
            "E: choose branch",
            "I: insert here",
        ]
        return "\n".join(lines)

    def _format_merge_beacon_selector_details(self, row: Dict[str, Any]) -> str:
        beacon_node = self.workflow_map.get_node_data(row["beacon_node_id"]) or {}
        merge_id = row.get("active_merge_id") or ""
        lines = [
            f"Merge Beacon: {node_display_name(row['beacon_node_id'], beacon_node)}",
            f"Connected Merge: {row.get('active_label') or '-'}",
            f"Step: {row.get('depth', '-')}",
            "",
            "E: choose merge to jump to",
        ]
        if merge_id:
            lines.append(f"Current target: {merge_id}")
        return "\n".join(lines)

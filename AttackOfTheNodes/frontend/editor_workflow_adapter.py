"""Frontend-owned workflow editing helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


DELETED_NODE_SYSTEM_ROLE = "deleted_node_branch_end"
DELETED_NODE_ALIAS = "Deleted node"
DELETED_NODE_STATE_ATTR = "_editor_deleted_nodes"


class EditorWorkflowAdapter:
    """Apply editor-only workflow transformations for the Textual UI."""

    def __init__(self, workflow_map, factory, state_owner: Optional[Any] = None) -> None:
        self.workflow_map = workflow_map
        self.factory = factory
        self._state_owner = state_owner
        self._local_deleted_nodes: Dict[str, Dict[str, Any]] = {}

    def bind_state_owner(self, state_owner: Any) -> None:
        """Use app-owned state so soft deletes survive screen recreation."""
        self._state_owner = state_owner
        if not hasattr(state_owner, DELETED_NODE_STATE_ATTR):
            setattr(state_owner, DELETED_NODE_STATE_ATTR, {})

    def is_placeholder(self, node_id: str) -> bool:
        node = self.workflow_map.get_node_data(node_id) or {}
        return node_id in self._deleted_nodes or self.is_materialized_placeholder(node)

    def is_materialized_placeholder(self, node: Dict[str, Any]) -> bool:
        config = node.get("config") or {}
        return (
            node.get("type") == "branch_end_node"
            and config.get("_system_role") == DELETED_NODE_SYSTEM_ROLE
        )

    def placeholder_metadata(self, node_id: str) -> Dict[str, Any]:
        node = self.workflow_map.get_node_data(node_id) or {}
        if node_id in self._deleted_nodes:
            return dict(self._deleted_nodes[node_id])
        config = node.get("config") or {}
        metadata = config.get("deleted_node") or {}
        return dict(metadata) if isinstance(metadata, dict) else {}

    def placeholder_has_restore_data(self, node_id: str) -> bool:
        metadata = self.placeholder_metadata(node_id)
        return bool(metadata.get("original_type"))

    def replace_with_placeholder(self, node_id: str) -> bool:
        node = self.workflow_map.get_node_data(node_id)
        if node is None:
            return False
        self._deleted_nodes[node_id] = self._metadata_for_node(node)
        self._mark_dirty()
        return True

    def undo_placeholder(self, node_id: str) -> bool:
        if not self.is_placeholder(node_id):
            return False
        node = self.workflow_map.get_node_data(node_id)
        if node is None:
            return False
        metadata = self.placeholder_metadata(node_id)
        original_type = str(metadata.get("original_type") or "")
        if not original_type:
            return False
        if self.is_materialized_placeholder(node):
            if not self.factory.is_valid_node_type(original_type):
                return False
            node["type"] = original_type
            node["config"] = deepcopy(metadata.get("original_config") or {})
            node["alias"] = str(metadata.get("original_alias") or "")
            node["connections"] = {
                "inputs": deepcopy(metadata.get("original_input_connections") or []),
                "outputs": deepcopy(metadata.get("original_output_connections") or []),
            }
            self._restore_downstream_inputs(node_id, node["connections"]["outputs"])
            node.pop("_timing_invalidated", None)
        self._deleted_nodes.pop(node_id, None)
        self._mark_dirty()
        return True

    def materialize_deleted_nodes(self) -> int:
        """Replace soft-deleted editor rows with saved branch-end placeholders."""
        materialized = 0
        for node_id, metadata in list(self._deleted_nodes.items()):
            node = self.workflow_map.get_node_data(node_id)
            if node is None or self.is_materialized_placeholder(node):
                continue
            node["type"] = "branch_end_node"
            node["alias"] = DELETED_NODE_ALIAS
            node["config"] = {
                "_system_role": DELETED_NODE_SYSTEM_ROLE,
                "deleted_node": deepcopy(metadata),
            }
            self._drop_outgoing_connections(node_id, node)
            node.pop("_timing_invalidated", None)
            materialized += 1
        if materialized:
            self._mark_dirty()
        return materialized

    def _metadata_for_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        original_type = node.get("type", "")
        return {
            "original_type": original_type,
            "original_display_name": self._display_name_for_type(original_type),
            "original_alias": node.get("alias", ""),
            "original_config": deepcopy(node.get("config") or {}),
            "original_input_connections": deepcopy(
                node.get("connections", {}).get("inputs", [])
            ),
            "original_output_connections": deepcopy(
                node.get("connections", {}).get("outputs", [])
            ),
            "original_input_ports": list(
                {
                    conn.get("target_port", "")
                    for conn in node.get("connections", {}).get("inputs", [])
                }
            ),
            "original_output_ports": list(
                {
                    conn.get("source_port", "")
                    for conn in node.get("connections", {}).get("outputs", [])
                }
            ),
        }

    def _drop_outgoing_connections(self, node_id: str, node: Dict[str, Any]) -> None:
        outputs = list(node.get("connections", {}).get("outputs", []))
        node.setdefault("connections", {})["outputs"] = []
        for conn in outputs:
            target_id = str(conn.get("target_node_id") or "")
            target_node = self.workflow_map.get_node_data(target_id)
            if target_node is None:
                continue
            target_inputs = target_node.setdefault("connections", {}).setdefault(
                "inputs",
                [],
            )
            target_node["connections"]["inputs"] = [
                input_conn
                for input_conn in target_inputs
                if not (
                    input_conn.get("source_node_id") == node_id
                    and input_conn.get("source_port", "default")
                    == conn.get("source_port", "default")
                    and input_conn.get("target_port", "input")
                    == conn.get("target_port", "input")
                )
            ]

    def _restore_downstream_inputs(
        self,
        node_id: str,
        outputs: list[Dict[str, Any]],
    ) -> None:
        for conn in outputs:
            target_id = str(conn.get("target_node_id") or "")
            target_node = self.workflow_map.get_node_data(target_id)
            if target_node is None:
                continue
            target_inputs = target_node.setdefault("connections", {}).setdefault(
                "inputs",
                [],
            )
            restored_input = {
                "target_port": conn.get("target_port", "input"),
                "source_node_id": node_id,
                "source_port": conn.get("source_port", "default"),
            }
            if restored_input not in target_inputs:
                target_inputs.append(restored_input)

    def remove_placeholder(self, node_id: str) -> bool:
        if not self.is_placeholder(node_id):
            return False
        self._deleted_nodes.pop(node_id, None)
        return self.workflow_map.delete_node(node_id)

    def replace_placeholder(self, node_id: str, new_type: str) -> Dict[str, Any]:
        node = self.workflow_map.get_node_data(node_id)
        if node is None or not self.is_placeholder(node_id):
            return {"replaced": False, "restored_original": False}
        metadata = self.placeholder_metadata(node_id)
        original_type = metadata.get("original_type")
        restored_original = new_type == original_type
        was_materialized = self.is_materialized_placeholder(node)
        node["type"] = new_type
        node["config"] = (
            deepcopy(metadata.get("original_config") or {})
            if restored_original
            else (self.factory.create_config_template(new_type) or {})
        )
        node["alias"] = (
            metadata.get("original_alias", "")
            if restored_original
            else ""
        )
        if restored_original and was_materialized:
            node["connections"] = {
                "inputs": deepcopy(metadata.get("original_input_connections") or []),
                "outputs": deepcopy(metadata.get("original_output_connections") or []),
            }
            self._restore_downstream_inputs(node_id, node["connections"]["outputs"])
        node.pop("_timing_invalidated", None)
        self._deleted_nodes.pop(node_id, None)
        self._mark_dirty()
        return {
            "replaced": True,
            "restored_original": restored_original,
            "original_type": original_type,
        }

    def _display_name_for_type(self, node_type: str) -> str:
        for metadata in self.factory.get_node_types_metadata():
            if metadata.get("type") == node_type:
                return metadata.get("display_name", node_type)
        return node_type

    def _mark_dirty(self) -> None:
        mark_dirty = getattr(self.workflow_map, "_mark_dirty", None)
        if callable(mark_dirty):
            mark_dirty()

    @property
    def _deleted_nodes(self) -> Dict[str, Dict[str, Any]]:
        if self._state_owner is None:
            return self._local_deleted_nodes
        state = getattr(self._state_owner, DELETED_NODE_STATE_ATTR, None)
        if not isinstance(state, dict):
            state = {}
            setattr(self._state_owner, DELETED_NODE_STATE_ATTR, state)
        return state

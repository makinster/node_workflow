"""Frontend-owned workflow editing helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


DELETED_NODE_SYSTEM_ROLE = "deleted_node_branch_end"
DELETED_NODE_ALIAS = "Deleted node"
DELETED_NODE_STATE_ATTR = "_editor_deleted_nodes"
TOMBSTONE_NODE_TYPE = "tombstone_node"


def tombstone_config_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Build the save-persistent tombstone config from delete-time metadata.

    Shape follows the tombstone contract in BACKEND_FRONTEND_BOUNDARY.md:
    full original node data so restore survives save/reload, plus the port
    lists the validator reads for orphaned-connection context.
    """
    return {
        "original_type": str(metadata.get("original_type") or ""),
        "original_display_name": str(metadata.get("original_display_name") or ""),
        "original_alias": str(metadata.get("original_alias") or ""),
        "original_config": deepcopy(metadata.get("original_config") or {}),
        "original_inputs": deepcopy(
            metadata.get("original_input_connections") or []
        ),
        "original_outputs": deepcopy(
            metadata.get("original_output_connections") or []
        ),
        "original_input_ports": list(metadata.get("original_input_ports") or []),
        "original_output_ports": list(metadata.get("original_output_ports") or []),
    }


def metadata_from_tombstone_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild delete-time metadata from a tombstone config (inverse of above)."""
    return {
        "original_type": str(config.get("original_type") or ""),
        "original_display_name": str(config.get("original_display_name") or ""),
        "original_alias": str(config.get("original_alias") or ""),
        "original_config": deepcopy(config.get("original_config") or {}),
        "original_input_connections": deepcopy(config.get("original_inputs") or []),
        "original_output_connections": deepcopy(config.get("original_outputs") or []),
        "original_input_ports": list(config.get("original_input_ports") or []),
        "original_output_ports": list(config.get("original_output_ports") or []),
    }


def migrate_legacy_deleted_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a legacy branch_end_node+_system_role record to tombstone_node in-place.

    Old saves write a deleted node as branch_end_node with:
        config._system_role == DELETED_NODE_SYSTEM_ROLE
        config.deleted_node == {original_type, original_display_name, ...}

    New tombstone_node stores the full original data at the config top level,
    so legacy saves keep undo-after-reload when the metadata carried it.
    Non-matching nodes are returned unchanged.
    """
    config = node.get("config") or {}
    if not (
        node.get("type") == "branch_end_node"
        and config.get("_system_role") == DELETED_NODE_SYSTEM_ROLE
    ):
        return node
    metadata = config.get("deleted_node") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    node["type"] = TOMBSTONE_NODE_TYPE
    node["alias"] = DELETED_NODE_ALIAS
    node["config"] = tombstone_config_from_metadata(metadata)
    return node


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
        if node.get("type") == TOMBSTONE_NODE_TYPE:
            return True
        # Legacy marker, recognized until migrate_workflow_on_load runs.
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
        if node.get("type") == TOMBSTONE_NODE_TYPE:
            return metadata_from_tombstone_config(config)
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
        """Replace soft-deleted editor rows with save-persistent tombstone records."""
        materialized = 0
        for node_id, metadata in list(self._deleted_nodes.items()):
            node = self.workflow_map.get_node_data(node_id)
            if node is None or self.is_materialized_placeholder(node):
                continue
            node["type"] = TOMBSTONE_NODE_TYPE
            node["alias"] = DELETED_NODE_ALIAS
            node["config"] = tombstone_config_from_metadata(metadata)
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

    def migrate_workflow_on_load(self, all_nodes: Dict[str, Dict[str, Any]]) -> int:
        """Migrate legacy deleted-node records to tombstone_node format in-place.

        Returns the count of nodes migrated. Call this after loading a workflow
        and before the editor renders the node list. The actual call-site wiring
        in app.py is deferred (UI concern); this method is testable standalone.
        """
        count = 0
        for node in all_nodes.values():
            config = node.get("config") or {}
            if (
                node.get("type") == "branch_end_node"
                and config.get("_system_role") == DELETED_NODE_SYSTEM_ROLE
            ):
                migrate_legacy_deleted_node(node)
                count += 1
        return count

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

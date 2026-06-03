"""Frontend-owned workflow editing helpers.

This adapter keeps Textual editor behavior out of backend service methods while
the legacy backend tombstone node remains available for compatibility.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


class EditorWorkflowAdapter:
    """Apply editor-only workflow transformations for the Textual UI."""

    def __init__(self, workflow_map, factory) -> None:
        self.workflow_map = workflow_map
        self.factory = factory

    def is_placeholder(self, node_id: str) -> bool:
        node = self.workflow_map.get_node_data(node_id) or {}
        return node.get("type") == "tombstone_node"

    def replace_with_placeholder(self, node_id: str) -> bool:
        node = self.workflow_map.get_node_data(node_id)
        if node is None:
            return False
        original_type = node.get("type", "")
        node["type"] = "tombstone_node"
        node["config"] = {
            "original_type": original_type,
            "original_display_name": self._display_name_for_type(original_type),
            "original_alias": node.get("alias", ""),
            "original_config": deepcopy(node.get("config") or {}),
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
        self._mark_dirty()
        return True

    def remove_placeholder(self, node_id: str) -> bool:
        if not self.is_placeholder(node_id):
            return False
        return self.workflow_map.delete_node(node_id)

    def replace_placeholder(self, node_id: str, new_type: str) -> Dict[str, Any]:
        node = self.workflow_map.get_node_data(node_id)
        if node is None or node.get("type") != "tombstone_node":
            return {"replaced": False, "restored_original": False}
        placeholder_config = node.get("config") or {}
        original_type = placeholder_config.get("original_type")
        restored_original = new_type == original_type
        node["type"] = new_type
        node["config"] = (
            deepcopy(placeholder_config.get("original_config") or {})
            if restored_original
            else (self.factory.create_config_template(new_type) or {})
        )
        node["alias"] = (
            placeholder_config.get("original_alias", "")
            if restored_original
            else ""
        )
        node.pop("_timing_invalidated", None)
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

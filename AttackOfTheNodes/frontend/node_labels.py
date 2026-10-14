"""Friendly node labels: the name a node is shown by.

A node shows its alias, or its type's name when it has none. The owner tried
a numbered suffix for repeated names (UX6, Q8) and rolled it back on
2026-10-14: the alias and type are enough almost everywhere, and the node ID
is shown on its own line where it is needed (node editor, details panel,
error messages). Kept as the one place call sites ask for a node's name.
"""

from __future__ import annotations

from typing import Dict

from frontend.node_io_display import node_display_name


def friendly_labels(workflow_map) -> Dict[str, str]:
    """Node id -> display name for every node in the workflow."""
    return {
        node_id: node_display_name(node_id, node)
        for node_id, node in workflow_map.get_all_node_data().items()
    }


def friendly_label(workflow_map, node_id: str) -> str:
    """One node's display name."""
    return node_display_name(node_id, workflow_map.get_node_data(node_id) or {})

"""Friendly node labels (UX6, U5): display-only names for nodes.

A node shows its usual name (alias, or a type-based fallback). When two or
more nodes in the workflow share that name, every one of them gets a
counter suffix in workflow order, starting at 1000: ``Fetch ·1000``,
``Fetch ·1001`` (owner, Q8, 2026-10-13: "something simple for now"). Stored
IDs never change; the raw ID stays in the node details and editor titles.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict

from frontend.node_io_display import node_display_name

SUFFIX_START = 1000


def friendly_labels(workflow_map) -> Dict[str, str]:
    """Node id -> friendly label for every node in the workflow."""
    nodes = workflow_map.get_all_node_data()
    base = {node_id: node_display_name(node_id, node) for node_id, node in nodes.items()}
    repeats = Counter(base.values())
    next_number: Dict[str, int] = {}
    labels: Dict[str, str] = {}
    for node_id, name in base.items():
        if repeats[name] > 1:
            number = next_number.get(name, SUFFIX_START)
            next_number[name] = number + 1
            labels[node_id] = f"{name} ·{number}"
        else:
            labels[node_id] = name
    return labels


def friendly_label(workflow_map, node_id: str) -> str:
    """One node's friendly label (computes the workflow's labels; when
    labelling many nodes, call ``friendly_labels`` once instead)."""
    label = friendly_labels(workflow_map).get(node_id)
    if label is not None:
        return label
    return node_display_name(node_id, workflow_map.get_node_data(node_id) or {})

"""Branch health derivation.

Derives the structural health of each parallel branch path from workflow
structure alone — no stored UI state. A "branch" is one outgoing edge from a
`branch_node` (one spawned parallel path). Each branch is classified into one
of three states:

- ``VALID``: the path reaches an end/output node, a ``merge_node`` (merged),
  or a Merge Beacon (``branch_end_node``) that is connected to a ``merge_node``.
- ``ENDED_UNMERGED``: the path reaches a Merge Beacon that is not connected to
  a ``merge_node`` — the branch is marked complete but never merges.
- ``FLOATING``: the path dead-ends with no valid output/end node and no Merge
  Beacon.

This module is backend-only and Textual-agnostic. The editor / FA-7 visual
pass consumes the returned data to colour branch rows without re-deriving the
structure. Build the output-node-type set from factory metadata with
``output_types_from_factory`` so the policy tracks the node taxonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


VALID = "valid"
ENDED_UNMERGED = "ended_unmerged"
FLOATING = "floating"

BRANCH_NODE_TYPE = "branch_node"
MERGE_NODE_TYPE = "merge_node"
MERGE_BEACON_TYPE = "branch_end_node"
END_NODE_TYPE = "end_node"

# Node types that count as a valid output/end terminus when no factory is
# supplied. ``merge_node`` and connected Merge Beacons are handled separately.
DEFAULT_OUTPUT_NODE_TYPES: Set[str] = {"end_node", "text_output_node"}


@dataclass(frozen=True)
class BranchHealth:
    """Structural health of one parallel branch path."""

    branch_node_id: str
    port: str
    state: str
    terminus_node_id: Optional[str]
    reason: str


def output_types_from_factory(factory: Any) -> Set[str]:
    """Collect node types that are valid output/end termini from metadata.

    A type qualifies when it is the explicit ``end_node`` or its primary
    family/category is ``Outputs``. Always returns a set safe to pass as
    ``output_node_types``.
    """
    types: Set[str] = {END_NODE_TYPE}
    try:
        metadata = factory.get_node_types_metadata()
    except AttributeError:
        return set(DEFAULT_OUTPUT_NODE_TYPES)
    for meta in metadata:
        node_type = meta.get("type")
        if not node_type:
            continue
        family = (meta.get("primary_family") or meta.get("category") or "").strip()
        if family.lower() == "outputs":
            types.add(node_type)
    # text_output_node predates the Outputs family tag in some builds.
    types |= DEFAULT_OUTPUT_NODE_TYPES
    return types


def derive_branch_health(
    all_nodes: Dict[str, Dict[str, Any]],
    output_node_types: Optional[Set[str]] = None,
) -> List[BranchHealth]:
    """Classify every branch path in the workflow.

    Returns one ``BranchHealth`` per outgoing edge of every ``branch_node``,
    in a deterministic order (branch node id, then port). Pass
    ``output_node_types`` from ``output_types_from_factory`` to track the live
    node taxonomy; it defaults to ``DEFAULT_OUTPUT_NODE_TYPES``.
    """
    outputs = (
        set(output_node_types)
        if output_node_types is not None
        else set(DEFAULT_OUTPUT_NODE_TYPES)
    )
    results: List[BranchHealth] = []
    for branch_node_id in sorted(all_nodes):
        node = all_nodes[branch_node_id]
        if node.get("type") != BRANCH_NODE_TYPE:
            continue
        edges = _outgoing_edges(node)
        for port, target_id in sorted(edges, key=lambda item: item[0]):
            results.append(
                _classify_branch(branch_node_id, port, target_id, all_nodes, outputs)
            )
    return results


def branch_health_by_port(
    all_nodes: Dict[str, Dict[str, Any]],
    output_node_types: Optional[Set[str]] = None,
) -> Dict[Tuple[str, str], BranchHealth]:
    """Return branch health keyed by ``(branch_node_id, port)``.

    Convenience for editor adapters that already key branch rows by branch
    node and port and want O(1) colour lookups.
    """
    return {
        (health.branch_node_id, health.port): health
        for health in derive_branch_health(all_nodes, output_node_types)
    }


def _classify_branch(
    branch_node_id: str,
    port: str,
    target_id: Optional[str],
    all_nodes: Dict[str, Dict[str, Any]],
    outputs: Set[str],
) -> BranchHealth:
    """Walk one branch path and classify its terminus."""
    if not target_id or target_id not in all_nodes:
        return BranchHealth(
            branch_node_id, port, FLOATING, None, "branch_port_unconnected"
        )

    visited: Set[str] = {branch_node_id}
    current_id: Optional[str] = target_id
    while current_id and current_id not in visited and current_id in all_nodes:
        visited.add(current_id)
        node = all_nodes[current_id]
        node_type = node.get("type")

        if node_type == MERGE_NODE_TYPE:
            return BranchHealth(branch_node_id, port, VALID, current_id, "merged")
        if node_type == MERGE_BEACON_TYPE:
            if _connects_to_merge(node, all_nodes):
                return BranchHealth(
                    branch_node_id, port, VALID, current_id, "beacon_merged"
                )
            return BranchHealth(
                branch_node_id, port, ENDED_UNMERGED, current_id, "beacon_unmerged"
            )
        if node_type in outputs:
            return BranchHealth(branch_node_id, port, VALID, current_id, "output_end")
        if node_type == BRANCH_NODE_TYPE:
            # A nested split leads onward to structured sub-branches, which are
            # classified as their own entries; this path is not floating.
            return BranchHealth(
                branch_node_id, port, VALID, current_id, "nested_branch"
            )

        next_id = _single_output_target(node)
        if next_id is None:
            # Dead end on a non-output node, or a fork we cannot follow.
            return BranchHealth(
                branch_node_id, port, FLOATING, current_id, "dead_end"
            )
        current_id = next_id

    return BranchHealth(branch_node_id, port, FLOATING, current_id, "no_terminus")


def _outgoing_edges(node: Dict[str, Any]) -> List[Tuple[str, Optional[str]]]:
    """Return (source_port, target_node_id) for each outgoing connection."""
    edges: List[Tuple[str, Optional[str]]] = []
    for conn in node.get("connections", {}).get("outputs", []):
        edges.append(
            (conn.get("source_port", "default"), conn.get("target_node_id"))
        )
    return edges


def _single_output_target(node: Dict[str, Any]) -> Optional[str]:
    """Return the sole forward target, or None when absent or ambiguous."""
    targets = [
        conn.get("target_node_id")
        for conn in node.get("connections", {}).get("outputs", [])
        if conn.get("target_node_id")
    ]
    if len(targets) == 1:
        return targets[0]
    return None


def _connects_to_merge(
    node: Dict[str, Any], all_nodes: Dict[str, Dict[str, Any]]
) -> bool:
    """True when any outgoing edge targets a ``merge_node``."""
    for conn in node.get("connections", {}).get("outputs", []):
        target_id = conn.get("target_node_id")
        target = all_nodes.get(target_id) if target_id else None
        if target and target.get("type") == MERGE_NODE_TYPE:
            return True
    return False

"""Give a built workflow the editor's own join shape.

Specs wire every path straight to Merge. The editor joins paths with a Merge
Beacon, so a save swaps each wire outside Merge's home slot for a preconfigured
Beacon. The values, slots and run behaviour stay the same.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .branch_paths import ALL_PATH_PORTS

MERGE_TYPE = "merge_node"
BEACON_TYPE = "branch_end_node"

BranchKey = Tuple[str, str]


def _branch_contexts(workflow_map, factory) -> Dict[str, List[BranchKey]]:
    """Which branch paths reach each node, stopping at Beacons as the editor does."""
    contexts: Dict[str, List[BranchKey]] = {}
    start_id = workflow_map.find_start_node_id()
    if not start_id:
        return contexts
    seen = set()
    stack: List[Tuple[str, BranchKey | None]] = [(start_id, None)]
    while stack:
        node_id, context = stack.pop()
        node = workflow_map.get_node_data(node_id) or {}
        if not node or (node_id, context) in seen:
            continue
        seen.add((node_id, context))
        if context and context not in contexts.setdefault(node_id, []):
            contexts[node_id].append(context)
        if node.get("type") == BEACON_TYPE:
            continue
        outputs = node.get("connections", {}).get("outputs", [])
        if factory.spawns_branches(str(node.get("type") or "")):
            # Port order, not wiring order, so this picks the editor's branch key.
            children = []
            for port in factory.node_output_ports(node):
                conn = next((c for c in outputs if c.get("source_port") == port), None)
                if conn:
                    children.append((str(conn.get("target_node_id") or ""), (node_id, port)))
        else:
            children = [(str(conn.get("target_node_id") or ""), context) for conn in outputs]
        stack.extend(reversed(children))
    return contexts


def _arrival_contexts(workflow_map, factory, contexts, conn: Dict[str, Any]) -> List[BranchKey]:
    source_id = str(conn.get("source_node_id") or "")
    source = workflow_map.get_node_data(source_id) or {}
    if factory.spawns_branches(str(source.get("type") or "")):
        return [(source_id, str(conn.get("source_port") or "default"))]
    return contexts.get(source_id, [])


def _home_port(config: Dict[str, Any], direct_ports: set) -> str:
    carry = str(config.get("carry_forward_branch_id") or "")
    if carry.startswith("home:") and carry.removeprefix("home:") in direct_ports:
        return carry.removeprefix("home:")
    return next((port for port in ALL_PATH_PORTS if port in direct_ports), "")


def insert_merge_beacons(workflow_map, factory) -> List[Dict[str, str]]:
    """Swap direct joins for Beacons; return what was added.

    A wire with no branch path of its own to close (an either-or route, say)
    stays direct: the editor would have nothing to offer for its Beacon.
    """
    added: List[Dict[str, str]] = []
    for merge_id, merge in list(workflow_map.get_all_node_data().items()):
        if merge.get("type") != MERGE_TYPE:
            continue
        contexts = _branch_contexts(workflow_map, factory)
        direct = [
            conn for conn in merge.get("connections", {}).get("inputs", [])
            if (workflow_map.get_node_data(str(conn.get("source_node_id") or "")) or {}).get("type") != BEACON_TYPE
        ]
        config = dict(merge.get("config") or {})
        home = _home_port(config, {str(conn.get("target_port") or "") for conn in direct})
        home_keys = {
            key for conn in direct if conn.get("target_port") == home
            for key in _arrival_contexts(workflow_map, factory, contexts, conn)
        }
        closures = list(config.get("branches_to_close") or [])
        for conn in direct:
            if conn.get("target_port") == home:
                continue
            key = next(
                (key for key in reversed(_arrival_contexts(workflow_map, factory, contexts, conn))
                 if key not in home_keys),
                None,
            )
            if key is None:
                continue
            source_id = str(conn["source_node_id"])
            source_port = str(conn.get("source_port") or "default")
            target_port = str(conn["target_port"])
            beacon_id = workflow_map.add_node(BEACON_TYPE)
            workflow_map.disconnect(source_id, source_port, merge_id, target_port)
            workflow_map.connect(source_id, source_port, beacon_id, "input")
            workflow_map.connect(beacon_id, "default", merge_id, target_port)
            closure = f"{key[0]}:{key[1]}"
            if closure not in closures:
                closures.append(closure)
            added.append({"beacon": beacon_id, "source": source_id, "merge": merge_id, "slot": target_port})
        if closures != list(config.get("branches_to_close") or []):
            config["branches_to_close"] = sorted(closures)
            config["carry_forward_branch_id"] = f"home:{home}"
            workflow_map.update_node_config(merge_id, config)
    return added

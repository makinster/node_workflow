"""What a connection carries and whether the receiving port accepts it.

One compatibility rule (:func:`backend.data_types.types_compatible`) shared by
the editor's connector choice, the node editor's Source dropdowns and the
validator's edge check, so a port the UI offers is a port preflight accepts.

The producer type follows pass-through nodes (Sleep, Counter, a node with
``pass_through`` set, a dead-drop pass-through port) back to the node that
made the payload. Branch paths and anything else without a declared type are
``any``: never flagged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from .data_types import DEFAULT_TYPE, coerce_type


def metadata_for_type(factory, node_type: str) -> Optional[Dict[str, Any]]:
    """Return factory metadata for a node type (shared; do not modify)."""
    cached = getattr(factory, "metadata_for_type", None)
    if callable(cached):
        return cached(node_type)
    for item in factory.get_node_types_metadata():
        if item["type"] == node_type:
            return item
    return None


def is_pass_through_node(factory, node: Dict[str, Any], port: str | None = None) -> bool:
    """Whether ``node`` forwards its input payload unchanged on ``port``."""
    metadata = metadata_for_type(factory, node.get("type", ""))
    if metadata and (metadata.get("ui_hints") or {}).get("pass_through"):
        return True
    config = node.get("config") or {}
    if config.get("pass_through") is True:
        return True
    output = ((metadata or {}).get("output_port_metadata") or {}).get(port or "default") or {}
    return config.get("dead_drop_passthrough") is True and bool(output.get("pass_through"))


def port_metadata(factory, node: Dict[str, Any], port: str, direction: str) -> Dict[str, Any]:
    """Declared metadata for one ``input`` or ``output`` port of ``node``."""
    if direction == "output" and hasattr(factory, "node_output_port_metadata"):
        # Config-driven ports (Error Mux routes) get their metadata here.
        value = factory.node_output_port_metadata(node).get(port)
        if isinstance(value, dict):
            return value
    metadata = metadata_for_type(factory, node.get("type", ""))
    if not metadata:
        return {}
    key = "output_port_metadata" if direction == "output" else "input_port_metadata"
    value = (metadata.get(key) or {}).get(port) or {}
    return value if isinstance(value, dict) else {}


def input_port_type(factory, node: Dict[str, Any], port: str) -> str:
    """Declared data type of an input port (``any`` when undeclared)."""
    return coerce_type(port_metadata(factory, node, port, "input").get("data_type"))


def trace_producers(
    nodes: Mapping[str, Dict[str, Any]],
    factory,
    node_id: str,
    port: str,
) -> List[Tuple[str, str]]:
    """Every ``(producer node id, data type)`` that can leave ``node_id``'s
    ``port``, in connection order without repeats.

    A pass-through node forwards whichever incoming payload triggered it, so
    each connection into its forwarded port is followed, not just the first
    (a Sleep fed by File Write and Random Number can forward either). A
    pass-through node with no connected input is its own producer, typed
    ``any``; a cycle of pass-through nodes ends without a producer.
    """
    producers: List[Tuple[str, str]] = []
    visited: set[tuple[str, str]] = set()
    stack = [(node_id, port or "default")]
    while stack:
        current_id, current_port = stack.pop()
        if (current_id, current_port) in visited:
            continue
        visited.add((current_id, current_port))
        node = nodes.get(current_id) or {}
        if not node:
            found = (current_id, DEFAULT_TYPE)
        elif not is_pass_through_node(factory, node, current_port):
            output = port_metadata(factory, node, current_port, "output")
            found = (current_id, coerce_type(output.get("data_type")))
        else:
            upstream = [conn for conn in _forwarded_inputs(factory, node)
                        if conn.get("source_node_id")]
            if upstream:
                # Reversed so the stack visits connections in their saved order.
                stack.extend(
                    (str(conn["source_node_id"]), str(conn.get("source_port") or "default"))
                    for conn in reversed(upstream)
                )
                continue
            found = (current_id, DEFAULT_TYPE)
        if found not in producers:
            producers.append(found)
    return producers


def _forwarded_inputs(factory, node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The connections a pass-through node may forward: all of its hinted
    input port (else the first fallback port that has any), or every input
    when it has no hint."""
    hints = (metadata_for_type(factory, node.get("type", "")) or {}).get("ui_hints") or {}
    inputs = list(node.get("connections", {}).get("inputs", []))
    forward_port = hints.get("forwarded_input_port")
    if not forward_port:
        return inputs
    for wanted in [forward_port, *(hints.get("forwarded_input_fallbacks") or [])]:
        matches = [conn for conn in inputs if str(conn.get("target_port") or "") == str(wanted)]
        if matches:
            return matches
    return []

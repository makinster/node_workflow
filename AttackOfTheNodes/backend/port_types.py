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

from typing import Any, Dict, Mapping, Optional

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


def producer_type(
    nodes: Mapping[str, Dict[str, Any]],
    factory,
    node_id: str,
    port: str,
) -> str:
    """Data type that leaves ``node_id``'s ``port``, traced through pass-through nodes."""
    return trace_producer(nodes, factory, node_id, port)[1]


def trace_producer(
    nodes: Mapping[str, Dict[str, Any]],
    factory,
    node_id: str,
    port: str,
) -> tuple[str, str]:
    """``(producer node id, data type)`` for the payload leaving ``node_id``'s
    ``port``. A pass-through node with no connected input is its own
    producer, typed ``any``."""
    visited: set[tuple[str, str]] = set()
    current_id, current_port = node_id, port or "default"
    while (current_id, current_port) not in visited:
        visited.add((current_id, current_port))
        node = nodes.get(current_id) or {}
        if not node:
            return current_id, DEFAULT_TYPE
        if not is_pass_through_node(factory, node, current_port):
            output = port_metadata(factory, node, current_port, "output")
            return current_id, coerce_type(output.get("data_type"))
        upstream = _forwarded_input(factory, node)
        if not upstream or not upstream.get("source_node_id"):
            return current_id, DEFAULT_TYPE
        current_id = str(upstream.get("source_node_id"))
        current_port = str(upstream.get("source_port") or "default")
    return current_id, DEFAULT_TYPE


def _forwarded_input(factory, node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The connection a pass-through node forwards (its hinted input first)."""
    hints = (metadata_for_type(factory, node.get("type", "")) or {}).get("ui_hints") or {}
    inputs = node.get("connections", {}).get("inputs", [])
    forward_port = hints.get("forwarded_input_port")
    if not forward_port:
        return inputs[0] if inputs else None
    for wanted in [forward_port, *(hints.get("forwarded_input_fallbacks") or [])]:
        for conn in inputs:
            if str(conn.get("target_port") or "") == str(wanted):
                return conn
    return None

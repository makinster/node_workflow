"""Which output paths the editor shows for a node (port model P3). Frontend-only.

Every node can fail along the engine-level ``error`` port (D7). A node
shows its error path once the user asks for it in the node's Errors section
(``show_error_path``) or once that path is wired; until then its errors go
to the default handler, so no node gets an error path by default.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.node_errors import ERROR_PORT

SHOW_ERROR_PATH = "show_error_path"


def lists_error_port(factory, node: Dict[str, Any]) -> bool:
    """True when the node type itself lists ``error`` among its outputs."""
    return ERROR_PORT in factory.node_output_ports(node)


def has_error_connection(node: Dict[str, Any]) -> bool:
    return any(
        str(conn.get("source_port") or "") == ERROR_PORT
        for conn in (node.get("connections") or {}).get("outputs", [])
    )


def shows_error_path(factory, node: Dict[str, Any]) -> bool:
    return (
        lists_error_port(factory, node)
        or bool((node.get("config") or {}).get(SHOW_ERROR_PATH))
        or has_error_connection(node)
    )


def editor_output_ports(factory, node: Dict[str, Any]) -> List[str]:
    """The node's ports from the backend, plus ``error`` when it is shown."""
    metadata = factory.node_output_port_metadata(node)
    ports = [port for port in factory.node_output_ports(node)
             if "to" not in metadata.get(port, {}) or "downstream" in metadata[port]["to"]]
    if ERROR_PORT not in ports and shows_error_path(factory, node):
        ports.append(ERROR_PORT)
    return ports

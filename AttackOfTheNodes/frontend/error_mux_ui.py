"""Error Mux route entry helpers (port model P2). Frontend-only.

The backend owns what a route *is* (``backend.node_errors.mux_routes``); this
module only proposes values for the config UI: which codes the upstream node
can raise, and a starting set of routes built from them.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Mapping, Optional

from backend.node_errors import (
    ENGINE_ERROR_DEFINITIONS,
    ERROR_PORT,
    error_codes,
    mux_routes,
)

ERROR_MUX_NODE_TYPE = "error_mux_node"
ROUTE_ID_PREFIX = "route_"


def new_route_id(prefix: str = ROUTE_ID_PREFIX) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def upstream_error_definitions(factory, workflow_map, node_id: str) -> List[Dict[str, Any]]:
    """Error definitions of every node wired into ``node_id``'s ``error`` input.

    Codes come from each source type's declared errors (the default
    ``node_error`` first) in connection order, without duplicates.
    """
    node = workflow_map.get_node_data(node_id) or {}
    definitions: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for conn in (node.get("connections") or {}).get("inputs", []):
        if conn.get("target_port") != ERROR_PORT or conn.get("source_port") != ERROR_PORT:
            continue
        source = workflow_map.get_node_data(str(conn.get("source_node_id") or "")) or {}
        for meta in factory.get_node_types_metadata():
            if meta.get("type") != source.get("type"):
                continue
            for definition in meta.get("errors") or []:
                code = str(definition.get("code") or "")
                if code and code not in seen:
                    seen.add(code)
                    definitions.append(dict(definition))
    return definitions


def code_options(
    definitions: List[Mapping[str, Any]], routes: Any = None
) -> List[tuple[str, str]]:
    """``(label, code)`` choices: upstream codes, engine codes, then any code a
    route already lists (so a saved code is never dropped from the picker)."""
    options: List[tuple[str, str]] = []
    seen: set[str] = set()

    def add(code: str, description: str = "") -> None:
        if code and code not in seen:
            seen.add(code)
            options.append((f"{code} - {description}" if description else code, code))

    for definition in definitions:
        add(str(definition.get("code") or ""), str(definition.get("description") or ""))
    for code, definition in ENGINE_ERROR_DEFINITIONS.items():
        add(code, str(definition.get("description") or ""))
    for entry in routes if isinstance(routes, list) else []:
        if isinstance(entry, Mapping):
            for code in error_codes(entry.get("codes")):
                add(code, "not raised upstream")
    return options


def routes_from_definitions(
    definitions: List[Mapping[str, Any]],
    existing: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """One route per upstream code, labelled by the code.

    A route that already handles exactly that one code keeps its id and
    label, so its connection survives a refill. Other existing routes are
    dropped; the caller decides whether to refill at all.
    """
    by_code: Dict[str, Dict[str, Any]] = {}
    for route in mux_routes({"routes": existing if isinstance(existing, list) else []}):
        if len(route["codes"]) == 1:
            by_code.setdefault(route["codes"][0], route)
    routes: List[Dict[str, Any]] = []
    for definition in definitions:
        code = str(definition.get("code") or "")
        if not code:
            continue
        kept = by_code.get(code)
        routes.append({
            "id": kept["id"] if kept else new_route_id(),
            "label": kept["label"] if kept else code.replace("_", " ").replace(".", " ").capitalize(),
            "codes": [code],
        })
    return routes


def autofill_mux_routes(factory, workflow_map, node_id: str) -> bool:
    """Give an Error Mux with no routes one route per upstream code.

    Returns True when the node's config changed. A mux that already has
    routes is never touched.
    """
    node = workflow_map.get_node_data(node_id) or {}
    if node.get("type") != ERROR_MUX_NODE_TYPE:
        return False
    config = dict(node.get("config") or {})
    if mux_routes(config):
        return False
    routes = routes_from_definitions(upstream_error_definitions(factory, workflow_map, node_id))
    if not routes:
        return False
    config["routes"] = routes
    return workflow_map.update_node_config(node_id, config)

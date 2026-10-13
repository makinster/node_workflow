"""Error Mux config helpers (frontend-only).

The Error Mux sits inline after a node. Its Source tab lists the errors that
node can raise, in plain words; each one the user picks becomes a recovery
branch, which the Parameters tab names and the Payloads tab configures. The
backend owns what a route is (``backend.node_errors``); this module only turns
error definitions into readable choices and selections into routes.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Mapping, Optional, Sequence

from backend.node_errors import (
    DEFAULT_ERROR_CODE,
    ERROR_PORT,
    MUX_FORWARD_ERROR,
    MUX_FORWARD_FAILED_INPUT,
    MUX_INPUT_PORT,
    UNMATCHED_ROUTE,
    mux_has_unmatched_route,
    mux_routes,
    mux_unmatched_label,
)

ERROR_MUX_NODE_TYPE = "error_mux_node"
ROUTE_ID_PREFIX = "route_"
# Selection value for the catch-all branch ("Any other error").
ANY_OTHER_ERROR = "__any_other__"

FORWARD_CHOICES = [
    ("The error message and details", MUX_FORWARD_ERROR),
    ("The failed node's input (retry or fall back with the same data)",
     MUX_FORWARD_FAILED_INPUT),
]

_WORDS = {
    "http": "HTTP", "url": "URL", "json": "JSON", "api": "API", "id": "ID",
    "ai": "AI", "llm": "LLM", "io": "I/O", "dns": "DNS", "tls": "TLS",
}
_NAMES = {
    DEFAULT_ERROR_CODE: "Unexpected failure",
    "engine.upstream_unreachable": "A node it waits for can no longer finish",
    "engine.unattended_input": "Needs input but nobody can answer",
}


def new_route_id() -> str:
    return f"{ROUTE_ID_PREFIX}{uuid.uuid4().hex[:8]}"


def friendly_error_name(code: str) -> str:
    """``http_status`` -> ``HTTP status``; engine and default codes get names."""
    code = str(code or "")
    if code in _NAMES:
        return _NAMES[code]
    words = code.split(".")[-1].split("_")
    text = " ".join(_WORDS.get(word, word) for word in words if word)
    return text[:1].upper() + text[1:] if text else code


def friendly_error_choice(definition: Mapping[str, Any]) -> str:
    """One readable line for a picker: name, what it means, whether retrying helps."""
    name = friendly_error_name(str(definition.get("code") or ""))
    description = str(definition.get("description") or "").strip().rstrip(".")
    retry = " Retrying may help." if definition.get("retryable") else ""
    return f"{name}: {description}.{retry}" if description else f"{name}{retry}"


def guarded_node_ids(workflow_map, mux_id: str) -> List[str]:
    """Nodes whose failures this mux catches: the node feeding its ``input``,
    or a node whose ``error`` port is wired to its ``error`` input."""
    node = workflow_map.get_node_data(mux_id) or {}
    ids: List[str] = []
    for conn in (node.get("connections") or {}).get("inputs", []):
        port = conn.get("target_port")
        inline = port == MUX_INPUT_PORT
        wired = port == ERROR_PORT and conn.get("source_port") == ERROR_PORT
        source = str(conn.get("source_node_id") or "")
        if (inline or wired) and source and source not in ids:
            ids.append(source)
    return ids


def upstream_error_definitions(factory, workflow_map, mux_id: str) -> List[Dict[str, Any]]:
    """Declared errors of the guarded node(s), default generic code first."""
    by_type = {meta.get("type"): meta for meta in factory.get_node_types_metadata()}
    definitions: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for node_id in guarded_node_ids(workflow_map, mux_id):
        source = workflow_map.get_node_data(node_id) or {}
        for definition in (by_type.get(source.get("type")) or {}).get("errors") or []:
            code = str(definition.get("code") or "")
            if code and code not in seen:
                seen.add(code)
                definitions.append(dict(definition))
    return definitions


def recovery_choices(
    definitions: Sequence[Mapping[str, Any]], config: Optional[Mapping[str, Any]] = None
) -> List[tuple[str, str]]:
    """``(readable text, value)`` for the Source picker: the guarded node's
    errors, any picked code it no longer raises, then "Any other error"."""
    choices: List[tuple[str, str]] = []
    seen: set[str] = set()
    for definition in definitions:
        code = str(definition.get("code") or "")
        if code and code not in seen:
            seen.add(code)
            choices.append((friendly_error_choice(definition), code))
    for route in mux_routes(config):
        for code in route["codes"]:
            if code not in seen:
                seen.add(code)
                choices.append((f"{friendly_error_name(code)}: not raised by the connected node", code))
    choices.append(("Any other error: everything not picked above", ANY_OTHER_ERROR))
    return choices


def selected_values(config: Optional[Mapping[str, Any]]) -> List[str]:
    values = [code for route in mux_routes(config) for code in route["codes"]]
    if mux_has_unmatched_route(config):
        values.append(ANY_OTHER_ERROR)
    return values


def routes_for_selection(
    selected: Sequence[str],
    existing: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Routes for the picked codes (order kept). A code already on a route
    stays on that route, keeping its id (so its connection survives), name
    and pass-along choice; each newly picked code gets its own branch."""
    owner: Dict[str, Dict[str, Any]] = {}
    for route in mux_routes(existing):
        for code in route["codes"]:
            owner.setdefault(code, route)
    routes: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for code in selected:
        if code == ANY_OTHER_ERROR:
            continue
        kept = owner.get(code)
        if kept is not None:
            if kept["id"] not in by_id:
                by_id[kept["id"]] = {**kept, "codes": []}
                routes.append(by_id[kept["id"]])
            by_id[kept["id"]]["codes"].append(code)
            continue
        route = {"id": new_route_id(), "label": friendly_error_name(code),
                 "codes": [code], "forward": MUX_FORWARD_ERROR}
        owner[code] = route
        by_id[route["id"]] = route
        routes.append(route)
    return routes


def unmatched_route(config: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """The catch-all branch shaped like a route, for the config rows."""
    forward = (config or {}).get("unmatched_forward")
    return {
        "id": UNMATCHED_ROUTE,
        "label": mux_unmatched_label(config),
        "codes": [],
        "forward": forward if forward in (MUX_FORWARD_ERROR, MUX_FORWARD_FAILED_INPUT)
        else MUX_FORWARD_ERROR,
    }

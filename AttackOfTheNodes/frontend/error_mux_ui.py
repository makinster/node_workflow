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

from frontend.node_types import MERGE_NODE_TYPE

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
    """One picker line, the same as the node's Errors list: ``[code] description``."""
    code = str(definition.get("code") or "")
    description = str(definition.get("description") or "").strip()
    return f"[{code}] {description}".rstrip()


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


def inline_mux_for(workflow_map, node_id: str) -> Optional[str]:
    """The Error Mux this node feeds inline, if any (U7 reuse rule).

    Reused only when one of the node's outputs connects directly to a mux's
    ``input``, which is exactly when the engine routes the node's failures
    to that mux.
    """
    node = workflow_map.get_node_data(node_id) or {}
    for conn in (node.get("connections") or {}).get("outputs", []):
        if conn.get("target_port") != MUX_INPUT_PORT:
            continue
        target = str(conn.get("target_node_id") or "")
        target_node = workflow_map.get_node_data(target) or {}
        if target_node.get("type") == ERROR_MUX_NODE_TYPE:
            return target
    return None


def branch_nodes_for_port(workflow_map, mux_id: str, port: str) -> List[str]:
    """Nodes reached only through the mux's ``port`` (owner, Q6).

    Follows the port's connections downstream and stops at a Merge and at
    any node that Start also reaches another way; those are never part of
    the branch. Order is breadth-first from the port.
    """
    mux = workflow_map.get_node_data(mux_id) or {}
    heads = [
        str(conn.get("target_node_id") or "")
        for conn in (mux.get("connections") or {}).get("outputs", [])
        if conn.get("source_port") == port
    ]
    return nodes_only_reached_from(workflow_map, heads, mux_id, {port})


def nodes_only_reached_from(
    workflow_map,
    heads: Sequence[str],
    skip_node: str,
    skip_ports: Optional[set] = None,
    extra_roots: Sequence[str] = (),
) -> List[str]:
    """Nodes reached from ``heads`` that Start (or ``extra_roots``) does not
    also reach without ``skip_node``'s ``skip_ports`` (all its outputs when
    None). Stops at a Merge. Order is breadth-first from the heads."""
    nodes = workflow_map.get_all_node_data()
    elsewhere: set[str] = set()
    start = workflow_map.find_start_node_id()
    stack = ([start] if start else []) + [root for root in extra_roots if root]
    while stack:
        node_id = stack.pop()
        if node_id in elsewhere or node_id not in nodes:
            continue
        elsewhere.add(node_id)
        for conn in (nodes[node_id].get("connections") or {}).get("outputs", []):
            if node_id == skip_node and (
                    skip_ports is None or conn.get("source_port") in skip_ports):
                continue
            stack.append(str(conn.get("target_node_id") or ""))
    branch: List[str] = []
    seen: set[str] = set()
    queue = list(heads)
    while queue:
        node_id = queue.pop(0)
        if node_id in seen or node_id in elsewhere or node_id not in nodes:
            continue
        seen.add(node_id)
        if nodes[node_id].get("type") == MERGE_NODE_TYPE:
            continue
        branch.append(node_id)
        for conn in (nodes[node_id].get("connections") or {}).get("outputs", []):
            queue.append(str(conn.get("target_node_id") or ""))
    return branch


def caught_error_count(workflow_map, mux_id: Optional[str]) -> int:
    """How many error choices (codes, plus "Any other error") a mux catches."""
    if not mux_id:
        return 0
    return len(selected_values((workflow_map.get_node_data(mux_id) or {}).get("config")))


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
    errors, then any picked code it no longer raises.

    "Any other error" is not offered (owner, 2026-10-13): every code a node
    can fail with is listed (undeclared codes become ``node_error``, and the
    nodes that raise engine codes declare them), so it only ever repeated
    the unpicked choices. A mux that already uses it still shows it, ticked,
    so it can be unpicked; it keeps working until then.
    """
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
                choices.append((f"[{code}] Not raised by the connected node", code))
    if mux_has_unmatched_route(config):
        choices.append(("[any other error] Older setting: everything not picked above. "
                        "Unpick to remove.", ANY_OTHER_ERROR))
    return choices


def selected_values(config: Optional[Mapping[str, Any]]) -> List[str]:
    values = [code for route in mux_routes(config) for code in route["codes"]]
    if mux_has_unmatched_route(config):
        values.append(ANY_OTHER_ERROR)
    return values


class MuxRouteDraft:
    """The branches of an Error Mux while its config is open.

    ``routes_by_id`` keeps every branch seen in this edit (id, label,
    forward and its codes in their original order); ``owner_by_code`` says
    which branch each code belongs to (the first listing wins, as in the
    engine). Unpicking a code removes it from the rows but keeps the
    ownership, so re-picking puts it back on the same branch with its id
    (its connection survives), latest name and pass-along choice. A branch
    whose codes are all unpicked leaves the rows but keeps its record, and
    grouped branches stay grouped. Each newly picked code gets a branch.
    """

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self.routes_by_id: Dict[str, Dict[str, Any]] = {}
        self.owner_by_code: Dict[str, str] = {}
        for route in mux_routes(config):
            self.routes_by_id[route["id"]] = {
                "id": route["id"], "label": route["label"],
                "forward": route["forward"], "codes": list(route["codes"]),
            }
            for code in route["codes"]:
                self.owner_by_code.setdefault(code, route["id"])

    def rows(self, selected: Sequence[str]) -> List[Dict[str, Any]]:
        """Fresh route rows for the picked codes, in pick-list order."""
        picked = [code for code in selected if code != ANY_OTHER_ERROR]
        rows: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for code in picked:
            route_id = self.owner_by_code.get(code)
            if route_id is None:
                route_id = new_route_id()
                self.routes_by_id[route_id] = {
                    "id": route_id, "label": friendly_error_name(code),
                    "forward": MUX_FORWARD_ERROR, "codes": [code],
                }
                self.owner_by_code[code] = route_id
            if route_id in seen:
                continue
            seen.add(route_id)
            record = self.routes_by_id[route_id]
            rows.append({
                "id": route_id, "label": record["label"], "forward": record["forward"],
                "codes": [c for c in record["codes"]
                          if c in picked and self.owner_by_code.get(c) == route_id],
            })
        return rows

    def record(self, rows: Sequence[Mapping[str, Any]]) -> None:
        """Keep the latest name and pass-along choice typed for each row."""
        for row in rows:
            record = self.routes_by_id.get(str(row.get("id")))
            if record is not None:
                record["label"] = row["label"]
                record["forward"] = row["forward"]


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

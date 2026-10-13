"""
Error codes, declared errors and the error payload (distributed step 3, D7).

Errors are matched on stable codes, never on message text. Each node declares
the codes it can raise in ``error_definitions``; ``NodeFactory`` adds one
default generic code (``node_error``) to every node so no error is ever
unmatched. Engine codes use the ``engine.`` namespace. Messages stay free
text for display and logs.

Every failure is routed through one engine-level ``error`` port. The error
payload sent along it is versioned JSON. It lives on the run's transient
store like any payload and is never written to the Vault or a file; the
durable record is ``run_errors/`` plus the log.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional


ERROR_PORT = "error"
ERROR_PAYLOAD_VERSION = 1

DEFAULT_ERROR_CODE = "node_error"
# Input key under which a node with ``receives_failed_input`` gets the failed
# node's input when a failure is routed to it along ``error``.
FAILED_INPUT = "failed_input"
ENGINE_UPSTREAM_UNREACHABLE = "engine.upstream_unreachable"
ENGINE_UNATTENDED_INPUT = "engine.unattended_input"

DEFAULT_ERROR_DEFINITION: Dict[str, Any] = {
    "code": DEFAULT_ERROR_CODE,
    "description": "Any failure the node does not declare more precisely.",
    "retryable": False,
}
ENGINE_ERROR_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    ENGINE_UPSTREAM_UNREACHABLE: {
        "code": ENGINE_UPSTREAM_UNREACHABLE,
        "description": "A node this one waits for can no longer complete in this run.",
        "retryable": False,
    },
    ENGINE_UNATTENDED_INPUT: {
        "code": ENGINE_UNATTENDED_INPUT,
        "description": "The node asked for input but nobody can answer in this run.",
        "retryable": False,
    },
}

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


class NodeError(Exception):
    """A node failure with a declared code.

    Nodes raise it (or pass it to ``context.signal_error``) to give a failure
    a stable code; any other exception gets the default ``node_error`` code.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Optional[Mapping[str, Any]] = None,
        retryable: Optional[bool] = None,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.details = dict(details or {})
        self.retryable = retryable


def is_engine_code(code: str) -> bool:
    return str(code).startswith("engine.")


def validate_code(code: Any, where: str = "error code") -> str:
    text = str(code or "").strip()
    if not _CODE_PATTERN.fullmatch(text):
        raise ValueError(
            f"{where} {code!r} must be lowercase snake_case segments joined by dots"
        )
    return text


def normalize_error_definitions(
    raw: Any, where: str = "errors", allow_engine_codes: bool = False
) -> List[Dict[str, Any]]:
    """Validate a declared ``errors`` list: code, description, retryable."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{where} must be a list")
    seen: set[str] = set()
    definitions: List[Dict[str, Any]] = []
    for index, entry in enumerate(raw):
        label = f"{where}[{index}]"
        if not isinstance(entry, Mapping):
            raise ValueError(f"{label} must be an object with code and description")
        unknown = set(entry) - {"code", "description", "retryable"}
        if unknown:
            raise ValueError(f"{label} has unknown keys: {sorted(unknown)}")
        code = validate_code(entry.get("code"), f"{label}.code")
        if is_engine_code(code) and not (allow_engine_codes and code in ENGINE_ERROR_DEFINITIONS):
            raise ValueError(f"{label}.code {code!r} is reserved for the engine")
        if code == DEFAULT_ERROR_CODE:
            raise ValueError(f"{label}.code {code!r} is added to every node automatically")
        if code in seen:
            raise ValueError(f"{label}.code {code!r} is declared twice")
        seen.add(code)
        description = str(entry.get("description") or "").strip()
        if not description:
            raise ValueError(f"{label}.description is required")
        retryable = entry.get("retryable", False)
        if not isinstance(retryable, bool):
            raise ValueError(f"{label}.retryable must be true or false")
        definitions.append({"code": code, "description": description, "retryable": retryable})
    return definitions


def definitions_with_default(declared: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Declared definitions plus the default generic code (first), copied."""
    result = [dict(DEFAULT_ERROR_DEFINITION)]
    result.extend(dict(item) for item in declared if item.get("code") != DEFAULT_ERROR_CODE)
    return result


def declared_codes(definitions: Iterable[Mapping[str, Any]]) -> List[str]:
    return [str(item.get("code")) for item in definitions]


# ---------------------------------------------------------------------------
# Error Mux routes (port model P2)
# ---------------------------------------------------------------------------

# Port of the optional catch-all route for codes no other route lists.
UNMATCHED_ROUTE = "unmatched"
# The Error Mux sits inline after a node: its `input` receives that node's
# normal output, which leaves on `default` (the "No error" branch). A failure
# of that node with a selected code leaves on the code's route instead.
MUX_INPUT_PORT = "input"
MUX_DEFAULT_PORT = "default"
# What a route passes along: the error payload, or the failed node's input.
MUX_FORWARD_ERROR = "error"
MUX_FORWARD_FAILED_INPUT = "failed_input"
MUX_FORWARD_OPTIONS = (MUX_FORWARD_ERROR, MUX_FORWARD_FAILED_INPUT)
# Pre-P2 Error Mux configs stored codes per fixed path; they migrate to
# routes with these ids so existing connections keep working.
LEGACY_MUX_PATHS = ("path_a", "path_b", "path_c")
_RESERVED_ROUTE_IDS = {ERROR_PORT, UNMATCHED_ROUTE, "default"}


def error_codes(raw: Any) -> List[str]:
    """Codes from a list or a comma/newline-separated string, de-duplicated."""
    items = raw if isinstance(raw, (list, tuple)) else str(raw or "").replace("\n", ",").split(",")
    codes: List[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in codes:
            codes.append(text)
    return codes


def _forward(value: Any, fallback: str = MUX_FORWARD_ERROR) -> str:
    return str(value) if value in MUX_FORWARD_OPTIONS else fallback


def mux_routes(config: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """An Error Mux's usable routes: ``[{"id", "label", "codes", "forward"}]``.

    Each route's ``id`` is its output port. Entries without an id, with a
    reserved id (``error``, ``unmatched``, ``default``) or repeating an
    earlier id are ignored; ``mux_route_problems`` reports them. ``forward``
    falls back to the pre-P4 node-wide ``forward`` setting, then ``error``.
    """
    node_forward = _forward((config or {}).get("forward"))
    raw = (config or {}).get("routes")
    routes: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, Mapping):
            continue
        route_id = str(entry.get("id") or "").strip()
        if not route_id or route_id in seen or route_id in _RESERVED_ROUTE_IDS:
            continue
        seen.add(route_id)
        label = str(entry.get("label") or "").strip() or f"Route {len(routes) + 1}"
        routes.append({
            "id": route_id, "label": label, "codes": error_codes(entry.get("codes")),
            "forward": _forward(entry.get("forward"), node_forward),
        })
    return routes


def mux_unmatched_label(config: Optional[Mapping[str, Any]]) -> str:
    return str((config or {}).get("unmatched_label") or "").strip() or "Any other error"


def mux_forward_for(config: Optional[Mapping[str, Any]], port: str) -> str:
    """What ``port`` passes along: ``error`` or ``failed_input``."""
    node_forward = _forward((config or {}).get("forward"))
    if port == UNMATCHED_ROUTE:
        return _forward((config or {}).get("unmatched_forward"), node_forward)
    for route in mux_routes(config):
        if route["id"] == port:
            return route["forward"]
    return node_forward


def mux_has_unmatched_route(config: Optional[Mapping[str, Any]]) -> bool:
    return bool((config or {}).get("unmatched_route"))


def mux_output_ports(config: Optional[Mapping[str, Any]]) -> List[str]:
    """``default`` (No error), route ids in order, then ``unmatched`` when on."""
    ports = [MUX_DEFAULT_PORT] + [route["id"] for route in mux_routes(config)]
    if mux_has_unmatched_route(config):
        ports.append(UNMATCHED_ROUTE)
    return ports


def mux_route_for_code(config: Optional[Mapping[str, Any]], code: Optional[str]) -> Optional[str]:
    """The route (port) a failure with ``code`` takes; the first listing wins."""
    if not code:
        return None
    for route in mux_routes(config):
        if code in route["codes"]:
            return route["id"]
    if mux_has_unmatched_route(config):
        return UNMATCHED_ROUTE
    return None


def mux_route_problems(config: Optional[Mapping[str, Any]]) -> List[str]:
    """Configuration mistakes ``mux_routes`` silently skips, for the validator."""
    raw = (config or {}).get("routes")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return ["routes must be a list"]
    problems: List[str] = []
    seen: set[str] = set()
    owner: Dict[str, str] = {}
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            problems.append(f"route {index + 1} is not an object")
            continue
        route_id = str(entry.get("id") or "").strip()
        if not route_id:
            problems.append(f"route {index + 1} has no id")
        elif route_id in _RESERVED_ROUTE_IDS:
            problems.append(f"route id '{route_id}' is reserved")
        elif route_id in seen:
            problems.append(f"route id '{route_id}' is used twice")
        seen.add(route_id)
        for code in error_codes(entry.get("codes")):
            if code in owner:
                problems.append(
                    f"code '{code}' is listed on two routes; the first ({owner[code]}) wins"
                )
            else:
                owner[code] = str(entry.get("label") or route_id)
    return problems


def legacy_mux_routes(config: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Routes for a pre-P2 config that stored ``path_a_codes`` ... ``path_c_codes``."""
    return [
        {"id": port, "label": f"Path {port[-1].upper()}",
         "codes": error_codes(config.get(f"{port}_codes"))}
        for port in LEGACY_MUX_PATHS
    ]


def build_error_payload(
    *,
    code: str,
    message: str,
    node_id: Optional[str],
    run_id: Optional[str],
    stage: str,
    details: Optional[Mapping[str, Any]] = None,
    retryable: bool = False,
    error_id: Optional[str] = None,
) -> Dict[str, Any]:
    """The versioned JSON payload routed along an ``error`` port."""
    return {
        "version": ERROR_PAYLOAD_VERSION,
        "code": code,
        "message": message,
        "node_id": node_id,
        "run_id": run_id,
        "stage": stage,
        "details": json_safe(dict(details or {})),
        "retryable": bool(retryable),
        "error_id": error_id,
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return str(value)

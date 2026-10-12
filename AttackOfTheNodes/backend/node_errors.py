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

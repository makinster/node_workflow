"""Workflow contracts (Step 4a-1): Start's typed rows in, the Return End out.

The design is ``docs/SUBWORKFLOWS_PROPOSAL.md`` (C1–C10, C26–C27). This module
is pure: no graph walking, no engine state, no Textual.

- **Start rows** are a workflow's inputs. Each row has a name, a data type, a
  value (its default when the workflow runs directly), ``required``, and where
  it goes: downstream, the Vault, or both. A Start with no rows behaves as
  before: its legacy greeting is one string row sent downstream.
- **Return End rows** are a callable workflow's results: name, type,
  ``required`` and where the value comes from (a Vault key or the End's
  incoming payload).
- **Missing** means absent or ``None``. ``False``, ``0``, ``""`` and empty
  collections are values. An explicit value that fails its type is an error;
  it never falls back to a default.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from .file_paths import normalize_local_path
from .file_refs import file_reference, is_file_reference, reference_path

#: Types a contract row may use (C7). ``var`` is any JSON value, copied.
ROW_TYPES = ("string", "number", "bool", "var", "file")
DESTINATIONS = ("Downstream", "Vault", "Both")
RESULT_SOURCES = ("Vault key", "Incoming payload")

DEFAULT_GREETING = "Workflow started"


class ContractError(ValueError):
    """A contract value or row is not acceptable; the message says why."""


class ContractInputError(ContractError):
    """A run cannot start: inputs are missing, invalid or unknown."""

    def __init__(self, missing: List[str], invalid: Dict[str, str], unknown: List[str]) -> None:
        self.missing = list(missing)
        self.invalid = dict(invalid)
        self.unknown = list(unknown)
        parts = []
        if missing:
            parts.append("missing required input(s): " + ", ".join(missing))
        for name, reason in invalid.items():
            parts.append(f"input '{name}': {reason}")
        if unknown:
            parts.append("unknown input(s): " + ", ".join(unknown))
        super().__init__("; ".join(parts))


# -- rows -----------------------------------------------------------------------

def start_rows(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Start's rows, normalized. With no rows, the legacy greeting is one row,
    unless ``no_inputs`` says every input was removed (Step 4a-2)."""
    rows = config.get("rows")
    if isinstance(rows, list) and rows:
        return [_start_row(row) for row in rows if isinstance(row, dict)]
    if config.get("no_inputs"):
        return []
    to = []
    if config.get("transient_output", True):
        to.append("Downstream")
    key = str(config.get("vault_write_key") or "").strip() if config.get("vault_write") else ""
    if key:
        to.append("Vault")
    destination = "Both" if len(to) == 2 else (to[0] if to else "Downstream")
    return [{
        "id": "greeting", "name": "greeting", "type": "string", "required": False,
        "value": str(config.get("greeting", DEFAULT_GREETING)),
        "to": destination, "vault_key": key, "description": "Message emitted when the workflow begins",
        "_legacy": True, "_downstream": bool(config.get("transient_output", True)),
    }]


def _start_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row.get("id") or row.get("name") or ""),
        "name": str(row.get("name") or "").strip(),
        "type": str(row.get("type") or "string"),
        "required": bool(row.get("required", False)),
        "value": row.get("value"),
        "to": str(row.get("to") or "Downstream"),
        "vault_key": str(row.get("vault_key") or "").strip(),
        "description": str(row.get("description") or ""),
    }


def sends_downstream(row: Dict[str, Any]) -> bool:
    if row.get("_legacy"):
        return bool(row.get("_downstream"))
    return row.get("to") in ("Downstream", "Both")


def sends_to_vault(row: Dict[str, Any]) -> bool:
    return row.get("to") in ("Vault", "Both")


def vault_key_for(row: Dict[str, Any]) -> str:
    return row.get("vault_key") or row["name"]


def return_rows(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A Return End's result rows, normalized; [] when it isn't a Return End."""
    if not config.get("return_end"):
        return []
    rows = config.get("results")
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        out.append({
            "id": str(row.get("id") or row.get("name") or ""),
            "name": str(row.get("name") or "").strip(),
            "type": str(row.get("type") or "string"),
            "required": bool(row.get("required", True)),
            "source": str(row.get("source") or "Vault key"),
            "vault_key": str(row.get("vault_key") or "").strip(),
            "description": str(row.get("description") or ""),
        })
    return out


def row_problems(rows: List[Dict[str, Any]], what: str) -> List[str]:
    """Readable problems with a row list: blank or repeated names, bad types."""
    problems, seen = [], set()
    for row in rows:
        name = row["name"]
        if not name:
            problems.append(f"{what} row has no name")
            continue
        if name.casefold() in seen:
            problems.append(f"{what} '{name}' is declared twice")
        seen.add(name.casefold())
        if row["type"] not in ROW_TYPES:
            problems.append(f"{what} '{name}' has type '{row['type']}'; "
                            f"contracts take {', '.join(ROW_TYPES)}")
    return problems


# -- values ---------------------------------------------------------------------

def is_missing(value: Any) -> bool:
    return value is None


def parse_text(row_type: str, text: Any) -> Any:
    """Typed value from *text*: an ``aotn run --input`` value or a row's
    default as the editor stores it. Only text is parsed; anything else is
    checked as an already-typed value."""
    if not isinstance(text, str):
        return check(row_type, text)
    if row_type == "string":
        return text
    if row_type == "number":
        stripped = text.strip()
        try:
            number = float(stripped)
        except ValueError:
            raise ContractError(f"expects a number, got {stripped!r}") from None
        integral = number.is_integer() and "." not in stripped and "e" not in stripped.lower()
        return int(number) if integral else number
    if row_type == "bool":
        word = text.strip().lower()
        if word in ("true", "yes", "1", "on"):
            return True
        if word in ("false", "no", "0", "off"):
            return False
        raise ContractError(f"expects true or false, got {text!r}")
    if row_type == "var":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text  # plain text is a valid JSON string value
    return check(row_type, text)


def check(row_type: str, value: Any) -> Any:
    """``value`` if it already is ``row_type`` (copied), else ContractError.

    Used for typed values: an inputs file, a caller's mapping, a Vault
    entry. Never re-parses: the string "false" stays a string.
    """
    if row_type == "string":
        if not isinstance(value, str):
            raise ContractError(f"expects text, got {type(value).__name__}")
        return value
    if row_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ContractError(f"expects a number, got {type(value).__name__}")
        return value
    if row_type == "bool":
        if not isinstance(value, bool):
            raise ContractError(f"expects true or false, got {type(value).__name__}")
        return value
    if row_type == "var":
        try:
            # A copy, so neither side of a call can change the other's value.
            return json.loads(json.dumps(value))
        except (TypeError, ValueError):
            raise ContractError("expects a JSON value") from None
    if row_type == "file":
        if is_file_reference(value):
            return deepcopy(value)
        if not isinstance(value, str) or not value.strip():
            raise ContractError("expects a file path")
        try:
            path = normalize_local_path(value).expanduser().resolve()
        except ValueError as exc:
            raise ContractError(str(exc)) from None
        if not path.is_file():
            raise ContractError(f"{path}: not found on this machine")
        return file_reference(str(path))
    raise ContractError(f"unsupported type '{row_type}'")


def resolve_inputs(
    rows: List[Dict[str, Any]],
    supplied: Dict[str, Any],
    *,
    strict: bool,
) -> Dict[str, Any]:
    """Fill each row (C10): a supplied value, else the row's value (its
    default), else missing. Raises ContractInputError listing every problem.

    Supplied values are already typed (an inputs file, a caller, text the
    CLI parsed by row) and are only checked; a row's stored default is text
    from the editor and is parsed.

    A row's *stored* value of ``""`` means "no default", for every type:
    the editor can't tell an intentional empty value from an unset one, and
    a required row must not quietly start with ``""``. A *supplied* ``""``
    is always a value. ``strict`` (callable workflows) also rejects supplied
    names no row declares.
    """
    values: Dict[str, Any] = {}
    missing: List[str] = []
    invalid: Dict[str, str] = {}
    names = {row["name"] for row in rows}
    for row in rows:
        name = row["name"]
        supplied_value = name in supplied and not is_missing(supplied[name])
        if supplied_value:
            raw = supplied[name]
        else:
            raw = row.get("value")
            if raw == "":
                raw = None
        if is_missing(raw):
            if row["required"]:
                missing.append(name)
            continue
        try:
            values[name] = check(row["type"], raw) if supplied_value else parse_text(row["type"], raw)
        except ContractError as exc:
            invalid[name] = str(exc)
    unknown = sorted(name for name in supplied if name not in names) if strict else []
    if missing or invalid or unknown:
        raise ContractInputError(missing, invalid, unknown)
    return values


def downstream_payload(rows: List[Dict[str, Any]], values: Dict[str, Any]) -> Tuple[bool, Any]:
    """(has_payload, payload): one routed row as itself, several as an object."""
    routed = [row for row in rows if sends_downstream(row) and row["name"] in values]
    if not routed:
        return False, None
    if len(routed) == 1:
        return True, values[routed[0]["name"]]
    return True, {row["name"]: values[row["name"]] for row in routed}


def downstream_type(rows: List[Dict[str, Any]]) -> Optional[str]:
    routed = [row for row in rows if sends_downstream(row)]
    if not routed:
        return None
    return routed[0]["type"] if len(routed) == 1 else "var"


def collect_results(
    rows: List[Dict[str, Any]],
    read_vault,
    payload: Any,
) -> Tuple[Dict[str, Any], List[str], Dict[str, str]]:
    """The Return End's values: (values, missing required, invalid)."""
    values: Dict[str, Any] = {}
    missing: List[str] = []
    invalid: Dict[str, str] = {}
    for row in rows:
        raw = payload if row["source"] == "Incoming payload" else read_vault(row["vault_key"] or row["name"])
        if is_missing(raw):
            if row["required"]:
                missing.append(row["name"])
            continue
        try:
            values[row["name"]] = check(row["type"], raw)
        except ContractError as exc:
            invalid[row["name"]] = str(exc)
    return values, missing, invalid


# -- the workflow as a whole ---------------------------------------------------------

def workflow_revision(data: Dict[str, Any]) -> str:
    """A short, stable hash of what a run executes (C8): nodes and callable."""
    canonical = json.dumps(
        {"nodes": data.get("nodes") or {}, "callable": bool(data.get("callable"))},
        sort_keys=True, default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def display_value(value: Any) -> str:
    """How a result value prints on the CLI."""
    if is_file_reference(value):
        return reference_path(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)

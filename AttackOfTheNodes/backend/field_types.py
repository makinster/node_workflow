"""Field type enum and config schema validation for AttackOfTheNodes."""

import math
from enum import Enum
from typing import Any, Dict, Iterator, List, Tuple

from .data_types import canonicalize


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    MULTILINE = "multiline"
    CODE = "code"
    OBJECT_LIST = "object_list"


_VALID_TYPES = {ft.value for ft in FieldType}


def validate_config_schema(schema: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return a list of error strings for any schema violations."""
    errors: List[str] = []
    for field_name, field_info in schema.items():
        if not isinstance(field_info, dict):
            errors.append(
                f"Field '{field_name}': schema must be a dict, got {type(field_info).__name__}"
            )
            continue
        field_type = field_info.get("type", "string")
        if field_type not in _VALID_TYPES:
            errors.append(f"Field '{field_name}': unknown type '{field_type}'")
        if field_type == "object_list":
            items = field_info.get("item_schema")
            if not isinstance(items, dict) or not items:
                errors.append(f"Field '{field_name}': object_list requires item_schema")
            else:
                errors.extend(f"Field '{field_name}': {error}" for error in validate_config_schema(items))
        if field_type in {"select", "multiselect"} and not field_info.get("options"):
            errors.append(
                f"Field '{field_name}': type '{field_type}' requires 'options'"
            )
    return errors


#: Schema field types holding a number.
NUMERIC_FIELD_TYPES = frozenset({FieldType.INTEGER.value, FieldType.FLOAT.value, FieldType.NUMBER.value})


def number_fields(schema: Dict[str, Dict[str, Any]]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """``(field name, field schema)`` for every number field in ``schema``."""
    for name, info in schema.items():
        if isinstance(info, dict) and str(info.get("type") or "") in NUMERIC_FIELD_TYPES:
            yield name, info


def accepted_types(field_info: Dict[str, Any]) -> set:
    """The value types a config field accepts from the Stash (and, later,
    from contract bindings): one rule for every caller.

    A field's declared ``data_type`` wins. Otherwise ``path_hint: file``
    means a file, and a text field takes a string. Everything else (numbers,
    checkboxes, selects, lists) takes nothing. Whether a text field should
    also take a file as a raw path is open (STASH_PROPOSAL.md, question 1).
    """
    declared = field_info.get("data_type")
    if declared:
        return {canonicalize(str(declared))}
    if field_info.get("path_hint") == "file":
        return {"file"}
    if field_info.get("type") in ("string", "multiline"):
        return {"string"}
    return set()


def stash_insert_target(schema: Dict[str, Dict[str, Any]], field_name: str) -> Dict[str, Any] | None:
    """What a Stash insert from ``field_name`` fills (Stash S3), or None.

    A field that accepts entries (``accepted_types``) is filled itself. A
    port's Source select whose path field is hidden until it reads
    ``Configured`` fills that field and switches the source (STASH_PROPOSAL.md
    §9 note 1). Everything else takes nothing.
    """
    info = schema.get(field_name) or {}
    accepts = accepted_types(info)
    if accepts:
        return {"field": field_name, "label": str(info.get("label") or field_name),
                "accepts": accepts, "set_source": None, "source_label": None}
    if info.get("type") == "select" and "Configured" in (info.get("options") or []):
        for name, other in schema.items():
            other_accepts = accepted_types(other)
            if other.get("visible_when") == {field_name: "Configured"} and other_accepts:
                return {"field": name, "label": str(other.get("label") or name),
                        "accepts": other_accepts, "set_source": (field_name, "Configured"),
                        "source_label": str(info.get("label") or field_name)}
    return None


def field_visible(config: Dict[str, Any], defaults: Dict[str, Any], field_info: Dict[str, Any]) -> bool:
    """Whether a schema field's ``visible_when`` condition currently holds.

    Every entry must match (AND); a list value matches any listed entry (OR
    within one field). Unset config keys fall back to the node type's
    default_config, the value the config screen renders. Fields with no
    visible_when are always visible. Hidden fields are not checked.
    """
    condition = field_info.get("visible_when")
    if not isinstance(condition, dict):
        return True
    for key, expected in condition.items():
        actual = config.get(key, defaults.get(key))
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def check_number(field_info: Dict[str, Any], raw: Any, default: Any = None) -> Tuple[Any, str]:
    """C5 number policy (owner, 2026-10-15): ``(value, problem)``.

    ``problem`` is "" when ``raw`` is a finite number inside the field's
    declared range (``min`` / ``max``; ``min_exclusive: true`` makes ``min``
    exclusive); the value is then an ``int`` for integer fields, else a
    ``float``. Blank means the field's default, which is checked the same
    way. Nothing is ever coerced to 0: callers keep the typed text and block
    the save (editor) or the run (validator).
    """
    integer = str(field_info.get("type") or "") == FieldType.INTEGER.value
    text = raw.strip() if isinstance(raw, str) else raw
    if text is None or text == "":
        if default is None or (isinstance(default, str) and not default.strip()):
            return None, "Enter a number"
        return check_number(field_info, default)
    if isinstance(text, bool):
        return None, "Enter a whole number" if integer else "Enter a number"
    if integer:
        value, problem = _whole_number(text)
        if problem:
            return None, problem
    else:
        try:
            value = float(text)
        except (TypeError, ValueError):
            return None, "Enter a number"
        except OverflowError:
            return None, "Number is too large"
        if not math.isfinite(value):
            return None, "Enter a finite number"
    minimum, maximum = field_info.get("min"), field_info.get("max")
    if minimum is not None:
        if field_info.get("min_exclusive") and value <= minimum:
            return None, f"Must be more than {minimum:g}"
        if value < minimum:
            return None, f"Must be at least {minimum:g}"
    if maximum is not None and value > maximum:
        return None, f"Must be at most {maximum:g}"
    return value, ""


def _whole_number(text: Any) -> Tuple[Any, str]:
    """An exact ``int`` for an integer field (never via float when the text
    is already whole: 9007199254740993 stays exact)."""
    if isinstance(text, int):
        return text, ""
    if isinstance(text, str):
        try:
            return int(text), ""
        except ValueError:
            pass
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None, "Enter a whole number"
    except OverflowError:
        return None, "Number is too large"
    if not math.isfinite(number):
        return None, "Enter a finite number"
    if not number.is_integer():
        return None, "Enter a whole number"
    return int(number), ""


def normalize_numbers(
    schema: Dict[str, Dict[str, Any]], defaults: Dict[str, Any], config: Dict[str, Any],
) -> Dict[str, Any]:
    """``config`` with every number field that passes ``check_number`` stored
    as its checked value, so execution reads exactly what preflight accepted
    (blank becomes the default, "3.0" becomes 3). Missing keys stay missing;
    values that fail are left as they are (preflight blocks the run)."""
    result = dict(config)
    for name, info in number_fields(schema):
        if name not in result:
            continue
        value, problem = check_number(info, result[name], defaults.get(name))
        if not problem:
            result[name] = value
    return result


def object_list_problems(schema: Dict[str, Dict[str, Any]], config: Dict[str, Any]) -> list[str]:
    """Validate opted-in row counts, exact unique values and required cells."""
    problems = []
    for name, info in schema.items():
        if info.get("type") != "object_list" or not any(
                key in info for key in ("unique_by", "min_items", "max_items")):
            continue
        label = str(info.get("label") or name)
        rows = config.get(name, [])
        if not isinstance(rows, list):
            problems.append(f"{label} must be a list of rows")
            continue
        if not info.get("min_items", 0) <= len(rows) <= info.get("max_items", 10000):
            problems.append(f"{label}: use {info.get('min_items', 0)} to {info.get('max_items', 10000)} rows")
        seen = set()
        unique = info.get("unique_by")
        for index, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                problems.append(f"{label}: row {index} must be a record")
                continue
            for field, cell in (info.get("item_schema") or {}).items():
                value = row.get(field, "")
                if not isinstance(value, str) or (cell.get("required") and not value.strip()):
                    problems.append(f"{label}: row {index} needs {cell.get('label') or field}")
            if unique and isinstance(row.get(unique), str):
                value = row[unique]
                if value in seen:
                    problems.append(f"{label}: duplicate answer in row {index} (matching is exact)")
                seen.add(value)
    return problems

"""Field type enum and config schema validation for AttackOfTheNodes."""

from enum import Enum
from typing import Any, Dict, List


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

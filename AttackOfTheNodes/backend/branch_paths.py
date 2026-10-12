"""Branch path and Merge slot names (port model P3).

Branch outputs and Merge inputs share one naming scheme: ``path_a`` ...
``path_z``, then ``path_aa``, ``path_ab`` ... A Branch has ``branch_count``
paths; a Merge has ``input_slots`` slots (five by default, the old fixed
number, so saved workflows are unchanged). ``MAX_BRANCH_COUNT`` bounds how
wide one run can fan out; it is a safety limit, not a design cap.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

MIN_BRANCH_COUNT = 2
MAX_BRANCH_COUNT = 64
DEFAULT_MERGE_SLOTS = 5


def path_port(index: int) -> str:
    """0 -> ``path_a``, 25 -> ``path_z``, 26 -> ``path_aa`` (spreadsheet style)."""
    if index < 0:
        raise ValueError("path index must be >= 0")
    letters = ""
    number = index
    while True:
        letters = chr(ord("a") + number % 26) + letters
        number = number // 26 - 1
        if number < 0:
            return f"path_{letters}"


def path_ports(count: int) -> List[str]:
    return [path_port(index) for index in range(max(0, int(count)))]


ALL_PATH_PORTS: List[str] = path_ports(MAX_BRANCH_COUNT)
_PATH_INDEX: Dict[str, int] = {port: index for index, port in enumerate(ALL_PATH_PORTS)}


def path_index(port: Any) -> Optional[int]:
    """Position of a path or slot name, or None when it is not one."""
    return _PATH_INDEX.get(str(port))


def _clamped(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def branch_count_from_config(config: Optional[Mapping[str, Any]]) -> int:
    """The number of Branch paths ``config`` asks for, clamped to 2-64."""
    return _clamped(
        (config or {}).get("branch_count", MIN_BRANCH_COUNT),
        MIN_BRANCH_COUNT, MIN_BRANCH_COUNT, MAX_BRANCH_COUNT,
    )


def merge_slot_count(config: Optional[Mapping[str, Any]]) -> int:
    """The number of Merge input slots, at least the old five."""
    return _clamped(
        (config or {}).get("input_slots", DEFAULT_MERGE_SLOTS),
        DEFAULT_MERGE_SLOTS, DEFAULT_MERGE_SLOTS, MAX_BRANCH_COUNT,
    )


def slots_covering(ports: Any) -> int:
    """The smallest slot count that includes every path name in ``ports``."""
    indexes = [path_index(port) for port in ports or []]
    return max([index + 1 for index in indexes if index is not None] or [0])

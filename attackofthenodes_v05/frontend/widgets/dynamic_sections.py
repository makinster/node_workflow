"""Helpers for config sections that reveal a counted set of rows."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


RowValue = dict[str, Any]


def clamp_dynamic_row_count(raw_count: Any, max_rows: int) -> int:
    """Clamp a user-entered dynamic row count to a supported range."""
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        count = 0
    return max(0, min(count, max_rows))


def preserved_dynamic_rows(
    row_count: int,
    max_rows: int,
    read_existing_row: Callable[[int], RowValue | None],
    initial_rows: list[Mapping[str, Any]] | None = None,
    blank_row: Mapping[str, Any] | None = None,
) -> list[RowValue]:
    """Return row values for a remount while preserving visible user edits.

    The count is the source of truth. Existing mounted rows win, initial config
    fills rows that have not mounted yet, and blank rows fill new capacity.
    """
    count = clamp_dynamic_row_count(row_count, max_rows)
    initial_rows = initial_rows or []
    blank_row = blank_row or {}
    values: list[RowValue] = []
    for index in range(count):
        current = read_existing_row(index)
        if current is not None:
            values.append(dict(current))
        elif index < len(initial_rows):
            values.append(dict(initial_rows[index]))
        else:
            values.append(dict(blank_row))
    return values

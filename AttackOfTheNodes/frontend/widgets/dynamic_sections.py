"""Helpers for config sections that reveal a counted set of rows."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any


RowValue = dict[str, Any]
SelectionOption = tuple[str, Any]
SelectionRow = tuple[str, Any, bool]


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


def dynamic_selection_rows(
    options: Sequence[SelectionOption],
    selected_values: Iterable[Any] | None = None,
    *,
    select_all_when_empty: bool = False,
) -> list[SelectionRow]:
    """Return Textual SelectionList rows with stale selections filtered out."""
    valid_values = {str(value) for _, value in options}
    selected = {
        str(value)
        for value in (selected_values or [])
        if str(value) in valid_values
    }
    if select_all_when_empty and options and not selected:
        selected = set(valid_values)
    return [
        (label, value, str(value) in selected)
        for label, value in options
    ]


def selected_values_from_widget(selection_list: Any) -> set[str]:
    """Return selected values from a Textual SelectionList as strings."""
    return {str(value) for value in getattr(selection_list, "selected", [])}

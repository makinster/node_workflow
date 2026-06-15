"""Shared list-selection helpers for keyboard-first modals."""

from __future__ import annotations

from textual.widgets import ListView


def clamp_list_index(index: int | None, item_count: int) -> int | None:
    """Clamp a possibly-empty ListView index to available selectable rows."""
    if item_count <= 0:
        return None
    return max(0, min(item_count - 1, index if index is not None else 0))


def ensure_list_highlight(list_view: ListView, item_count: int) -> int | None:
    """Ensure a selectable list has a visible highlighted row."""
    list_view.index = clamp_list_index(list_view.index, item_count)
    return list_view.index


def focus_list(app, list_view: ListView, item_count: int) -> int | None:
    """Focus a ListView and ensure its highlight is valid and visible."""
    index = ensure_list_highlight(list_view, item_count)
    app.set_focus(list_view)
    # Re-assert the highlight. ListView.watch_index only fires on a changed
    # value, so re-entering the list with an unchanged index would otherwise
    # leave the highlighted row visually unset.
    if index is not None:
        list_view.index = None
        list_view.index = index
    list_view.scroll_visible(animate=False)
    return index


def move_list_highlight(
    app,
    list_view: ListView,
    item_count: int,
    delta: int,
) -> int | None:
    """Move a ListView highlight by one command-navigation step."""
    if item_count <= 0:
        list_view.index = None
        return None
    current = list_view.index if list_view.index is not None else 0
    list_view.index = max(0, min(item_count - 1, current + delta))
    app.set_focus(list_view)
    list_view.scroll_visible(animate=False)
    return list_view.index

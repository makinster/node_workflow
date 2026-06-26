"""Shared command-mode navigation helpers for Textual forms."""

from __future__ import annotations

from typing import Any, Iterable

from textual import events
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, Checkbox, ListView, Select, SelectionList, Switch
from textual.widgets._select import SelectOverlay

from frontend.widgets.command_input import CommandInput, CommandTextArea


DEFAULT_COMMAND_FOCUS_TYPES = (
    CommandInput,
    CommandTextArea,
    Checkbox,
    SelectionList,
    ListView,
    Select,
    Button,
)


def _install_select_overlay_command_bindings() -> None:
    existing_keys = {
        binding.key if isinstance(binding, Binding) else binding[0]
        for binding in SelectOverlay.BINDINGS
    }
    additions = [
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("e", "select", "Select", priority=True),
        Binding("enter", "select", "Select", priority=True),
        Binding("ctrl+q", "dismiss", "Dismiss menu", priority=True),
    ]
    SelectOverlay.BINDINGS = [
        *SelectOverlay.BINDINGS,
        *[binding for binding in additions if binding.key not in existing_keys],
    ]
    if getattr(SelectOverlay, "_command_navigation_key_patch", False):
        return
    original_on_key = SelectOverlay._on_key

    async def _on_key(self: SelectOverlay, event: events.Key) -> None:
        if event.key in {"w", "up"}:
            self.action_cursor_up()
            event.stop()
            event.prevent_default()
            return
        if event.key in {"s", "down"}:
            self.action_cursor_down()
            event.stop()
            event.prevent_default()
            return
        if event.key in {"e", "enter"}:
            self.action_select()
            event.stop()
            event.prevent_default()
            return
        if event.key == "ctrl+q":
            self.action_dismiss()
            event.stop()
            event.prevent_default()
            return
        await original_on_key(self, event)

    SelectOverlay._on_key = _on_key
    SelectOverlay._command_navigation_key_patch = True


_install_select_overlay_command_bindings()


def is_editing_text(widget: Any) -> bool:
    """Return True when a command text widget is actively accepting text."""
    return isinstance(widget, (CommandInput, CommandTextArea)) and bool(
        getattr(widget, "editing", False)
    )


def blocks_command_action(widget: Any, action: str) -> bool:
    """Return True when a text editor should own the key action."""
    return is_editing_text(widget) and action in {
        "cursor_up",
        "cursor_down",
        "activate_focused",
        "choose",
        "focus_filter",
        "focus_node_list",
        "cancel",
        "browse",
    }


def command_focus_widgets(
    root: Any,
    focusable_types: Iterable[type] = DEFAULT_COMMAND_FOCUS_TYPES,
) -> list[Any]:
    """Return enabled command-mode widgets under a Textual root."""
    focusable = tuple(focusable_types)
    return [
        widget
        for widget in root.query("*")
        if isinstance(widget, focusable) and not getattr(widget, "disabled", False)
    ]


def group_widgets_into_rows(widgets: list[Any]) -> list[list[Any]]:
    """Group focusable widgets into rows for 2D keyboard navigation.

    Row rule (in priority order): widgets sharing the nearest ``Horizontal``
    container ancestor form one row; otherwise widgets sharing a realized visual
    line (equal ``region.y``) form a row; otherwise each widget is its own row.
    Rows are returned in first-seen (DOM/nav) order, which matches top-to-bottom
    visual order; within a row, widgets are ordered left-to-right by ``region.x``
    (falling back to nav order before layout). Single-column screens therefore
    become one widget per row, so W/S behaves like the old flat list and A/D is
    a no-op. The Horizontal-ancestor rule keeps stacked rows (segmented toggles,
    tab bars, button rows) navigable even before geometry is realized.
    """
    rows: list[list[tuple[int, Any]]] = []
    key_to_row: dict[Any, list[tuple[int, Any]]] = {}
    for order, widget in enumerate(widgets):
        key = _row_key(widget, order)
        existing = key_to_row.get(key)
        if existing is not None:
            existing.append((order, widget))
        else:
            row = [(order, widget)]
            key_to_row[key] = row
            rows.append(row)

    result: list[list[Any]] = []
    for row in rows:
        row.sort(key=lambda item: (_widget_x(item[1]), item[0]))
        result.append([widget for _order, widget in row])
    return result


def _row_key(widget: Any, order: int) -> Any:
    """Return the grouping key for a widget's row (see group_widgets_into_rows)."""
    node = getattr(widget, "parent", None)
    while node is not None:
        if isinstance(node, Horizontal):
            return ("horizontal", id(node))
        node = getattr(node, "parent", None)
    region = getattr(widget, "region", None)
    if region is not None and getattr(region, "height", 0):
        return ("line", region.y)
    return ("unique", order)


def _row_position(rows: list[list[Any]], widget: Any) -> tuple[int | None, int | None]:
    for row_index, row in enumerate(rows):
        if widget in row:
            return row_index, row.index(widget)
    return None, None


def row_move_target(
    rows: list[list[Any]], current: Any, direction: int
) -> tuple[Any | None, bool]:
    """Vertical move between rows, preserving horizontal (column) position.

    Returns ``(target_widget, at_boundary)``. When leaving a row the cursor
    lands on the column-nearest widget (by ``region.x``) in the destination
    row, clamping to that row's only widget when it is narrower. At the top or
    bottom boundary the current widget is returned with ``at_boundary=True``.
    """
    if not rows:
        return None, False
    row_index, _col = _row_position(rows, current)
    if row_index is None:
        first = rows[0][0]
        return first, False
    next_index = row_index + direction
    if next_index < 0 or next_index >= len(rows):
        return current, True
    destination = rows[next_index]
    current_x = _widget_x(current)
    target = min(destination, key=lambda w: abs(_widget_x(w) - current_x))
    return target, False


def within_row_target(
    rows: list[list[Any]], current: Any, direction: int
) -> Any | None:
    """Horizontal move within the current row. Returns None at a row edge."""
    row_index, col = _row_position(rows, current)
    if row_index is None or col is None:
        return None
    next_col = col + direction
    row = rows[row_index]
    if next_col < 0 or next_col >= len(row):
        return None
    return row[next_col]


def _widget_x(widget: Any) -> int:
    region = getattr(widget, "region", None)
    return region.x if region is not None else 0


def move_command_focus(
    screen: Any,
    direction: int,
    widgets: list[Any] | None = None,
    scroll_container: Any | None = None,
) -> Any | None:
    """Move focus through command-mode widgets and keep the target visible."""
    widgets = widgets if widgets is not None else command_focus_widgets(screen)
    if not widgets:
        return None
    current = screen.app.focused
    try:
        current_index = widgets.index(current)
    except ValueError:
        current_index = 0 if direction > 0 else len(widgets) - 1
    next_index = max(0, min(len(widgets) - 1, current_index + direction))
    target = widgets[next_index]
    focus_command_widget(screen, target, scroll_container)
    return target


def focus_command_widget(
    screen: Any,
    widget: Any,
    scroll_container: Any | None = None,
) -> Any:
    """Focus a command widget and optionally begin editing text prompts."""
    target = widget
    active_text = getattr(screen, "_active_command_text_widget", None)
    if active_text is not target and isinstance(active_text, (CommandInput, CommandTextArea)):
        active_text.end_edit()
    if isinstance(target, (CommandInput, CommandTextArea)):
        if getattr(target, "auto_edit_on_focus", False):
            target.begin_edit()
        else:
            target.end_edit()
            # Fresh navigation focus: drop any stale nav-cursor position so the
            # next begin_edit() places the caret at the end of the value.
            target._nav_cursor_positioned = False
            screen.app.set_focus(target)
    else:
        screen.app.set_focus(target)
    if scroll_container is not None:
        scroll_container.scroll_to_widget(target, animate=False)
    else:
        target.scroll_visible(animate=False)
    return target


def open_select_at_top(select: Select) -> None:
    """Open a Select overlay and highlight the first enabled option."""
    select.action_show_overlay()
    select_overlay(select).action_first()


def move_select_overlay(select: Select, direction: int) -> None:
    """Move an expanded Select overlay by one row."""
    overlay = select_overlay(select)
    if direction < 0:
        overlay.action_cursor_up()
    else:
        overlay.action_cursor_down()


def select_overlay(select: Select) -> SelectOverlay:
    """Return the private Textual overlay used by Select."""
    return select.query_one(SelectOverlay)


def activate_command_widget(widget: Any) -> bool:
    """Activate a focused command-mode widget."""
    if isinstance(widget, (CommandInput, CommandTextArea)):
        widget.begin_edit()
        return True
    if isinstance(widget, (Checkbox, Switch)):
        # Single-press toggle: E/Enter flips the value directly.
        widget.value = not widget.value
        return True
    if isinstance(widget, SelectionList):
        if widget.highlighted is not None:
            option = widget.get_option_at_index(widget.highlighted)
            widget.toggle(option.value)
        return True
    if isinstance(widget, Select):
        if widget.expanded:
            commit_highlighted_select(widget)
        else:
            open_select_at_top(widget)
        return True
    if isinstance(widget, Button):
        widget.press()
        return True
    return False


def commit_highlighted_select(select: Select) -> None:
    """Commit the highlighted Select option and close its overlay."""
    highlighted = select_overlay(select).highlighted
    if highlighted is None:
        return
    value = select._options[highlighted][1]
    if value != select.value:
        select.value = value
    select.focus()
    select.expanded = False

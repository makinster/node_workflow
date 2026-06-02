"""Shared command-mode navigation helpers for Textual forms."""

from __future__ import annotations

from typing import Any, Iterable

from textual.widgets import Button, Checkbox, Select, SelectionList
from textual.widgets._select import SelectOverlay

from frontend.widgets.command_input import CommandInput, CommandTextArea


DEFAULT_COMMAND_FOCUS_TYPES = (
    CommandInput,
    CommandTextArea,
    Checkbox,
    SelectionList,
    Select,
    Button,
)


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
    if isinstance(target, (CommandInput, CommandTextArea)):
        target.end_edit()
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
    if isinstance(widget, Checkbox):
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

"""Shared command-mode navigation helpers for Textual forms."""

from __future__ import annotations

from typing import Any, Iterable

from textual import events
from textual.binding import Binding
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

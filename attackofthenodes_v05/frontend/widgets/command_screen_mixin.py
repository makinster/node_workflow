"""Shared cursor-model mixin for command-mode Textual screens.

Screens that inherit CommandScreenMixin get:
- Standard W/S/up/down/E/enter bindings (priority=True).
- check_action() that blocks nav actions while a text widget is editing.
- action_cursor_up/down() that move through _nav_widgets() with bell on boundary.
- action_activate_focused() that activates the focused widget.
- _sync_cursor_mode() to update app.cursor_state and the screen's StatusBar.

Override _nav_widgets() to control the focusable widget order.
Override _scroll_container() to enable scroll-to-visible on movement.
Call _focus_first() in on_mount() to initialize focus on the first widget.
"""

from __future__ import annotations

from typing import Any, Optional

from textual.binding import Binding
from textual.css.query import NoMatches

from frontend.widgets.command_navigation import (
    activate_command_widget,
    blocks_command_action,
    command_focus_widgets,
    focus_command_widget,
    is_editing_text,
    move_command_focus,
)
from frontend.widgets.status_bar import StatusBar


_NAV_BINDINGS = [
    Binding("w", "cursor_up", "Up", priority=True),
    Binding("s", "cursor_down", "Down", priority=True),
    Binding("up", "cursor_up", "Up", priority=True),
    Binding("down", "cursor_down", "Down", priority=True),
    Binding("e", "activate_focused", "Activate", priority=True),
    Binding("enter", "activate_focused", "Activate", priority=True),
]


class CommandScreenMixin:
    """Mixin providing standard command-mode navigation for Textual screens."""

    BINDINGS = _NAV_BINDINGS

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # Inject nav bindings BEFORE super() so DOMNode._merge_bindings sees them.
        try:
            from textual.dom import DOMNode
            if issubclass(cls, DOMNode):
                own = list(cls.__dict__.get("BINDINGS", []))
                own_keys: set[str] = set()
                for b in own:
                    key = b.key if hasattr(b, "key") else (b[0] if isinstance(b, tuple) else None)
                    if key:
                        own_keys.add(key)
                injected = False
                for binding in _NAV_BINDINGS:
                    if binding.key not in own_keys:
                        own.append(binding)
                        injected = True
                if injected or "BINDINGS" not in cls.__dict__:
                    cls.BINDINGS = own
        except ImportError:
            pass
        super().__init_subclass__(**kwargs)

    def _nav_widgets(self) -> list[Any]:
        """Return the ordered list of focusable command-mode widgets."""
        return command_focus_widgets(self)

    def _scroll_container(self) -> Optional[Any]:
        """Return the scroll container to use for scroll-to-visible, or None."""
        return None

    def _focus_first(self) -> None:
        """Focus the first nav widget. Call from on_mount()."""
        widgets = self._nav_widgets()
        if widgets:
            focus_command_widget(self, widgets[0], self._scroll_container())

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if blocks_command_action(self.app.focused, action):
            return False
        return True

    def action_cursor_up(self) -> None:
        self._move_cursor(-1)

    def action_cursor_down(self) -> None:
        self._move_cursor(1)

    def _move_cursor(self, direction: int) -> None:
        """Move focus by direction (+1 down, -1 up) within _nav_widgets()."""
        if getattr(self, "_cursor_moving", False):
            return
        self._cursor_moving = True
        try:
            widgets = self._nav_widgets()
            if not widgets:
                self.app.bell()
                return
            current = self.app.focused
            try:
                current_index = widgets.index(current)
                at_boundary = (
                    (direction < 0 and current_index == 0)
                    or (direction > 0 and current_index == len(widgets) - 1)
                )
            except ValueError:
                at_boundary = False
            move_command_focus(
                self,
                direction,
                widgets=widgets,
                scroll_container=self._scroll_container(),
            )
            if at_boundary:
                self.app.bell()
            self._sync_cursor_mode()
        finally:
            self._cursor_moving = False

    def action_activate_focused(self) -> None:
        activate_command_widget(self.app.focused)
        self._sync_cursor_mode()

    def _sync_cursor_mode(self) -> None:
        """Update app.cursor_state and the screen's StatusBar mode indicator."""
        editing = is_editing_text(self.app.focused)
        mode = "edit" if editing else "nav"
        cursor_state = getattr(self.app, "cursor_state", None)
        if cursor_state is not None:
            cursor_state.mode = mode
        try:
            self.query_one(StatusBar).set_mode(mode)
        except NoMatches:
            pass

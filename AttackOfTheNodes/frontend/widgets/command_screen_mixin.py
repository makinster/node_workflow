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

from textual import events
from textual.binding import Binding
from textual.css.query import NoMatches

from frontend.widgets.command_navigation import (
    activate_command_widget,
    blocks_command_action,
    command_focus_widgets,
    focus_command_widget,
    group_widgets_into_rows,
    is_editing_text,
    row_move_target,
    within_row_target,
)
from frontend.widgets.status_bar import StatusBar


_NAV_BINDINGS = [
    Binding("w", "cursor_up", "Up", priority=True),
    Binding("s", "cursor_down", "Down", priority=True),
    Binding("up", "cursor_up", "Up", priority=True),
    Binding("down", "cursor_down", "Down", priority=True),
    # A/D and left/right move within the current row (2D navigation); a no-op
    # on single-widget rows, which is the common single-column case.
    Binding("a", "cursor_left", "Left", priority=True),
    Binding("d", "cursor_right", "Right", priority=True),
    Binding("left", "cursor_left", "Left", priority=True),
    Binding("right", "cursor_right", "Right", priority=True),
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
        active_text = getattr(self, "_active_command_text_widget", None)
        if blocks_command_action(active_text, action):
            return False
        if blocks_command_action(self.app.focused, action):
            return False
        if action in {"cursor_left", "cursor_right"}:
            # While editing, A/D type/move the caret in the field.
            if is_editing_text(active_text) or is_editing_text(self.app.focused):
                return False
            # Within-row movement only applies when the focused widget shares a
            # row with another widget. On a single-widget row (the common case,
            # e.g. a lone CommandInput) fall through so the key reaches the
            # widget for caret positioning.
            if not self._focused_in_multi_widget_row():
                return False
        return True

    def _focused_in_multi_widget_row(self) -> bool:
        rows = group_widgets_into_rows(self._nav_widgets())
        focused = self.app.focused
        for row in rows:
            if focused in row:
                return len(row) > 1
        return False

    def action_cursor_up(self) -> None:
        self._move_cursor(-1)

    def action_cursor_down(self) -> None:
        self._move_cursor(1)

    def action_cursor_left(self) -> None:
        self._move_within_row(-1)

    def action_cursor_right(self) -> None:
        self._move_within_row(1)

    def _move_cursor(self, direction: int) -> None:
        """Move focus between rows (+1 down, -1 up), preserving column."""
        if getattr(self, "_cursor_moving", False):
            return
        self._cursor_moving = True
        try:
            rows = group_widgets_into_rows(self._nav_widgets())
            if not rows:
                self.app.bell()
                return
            target, at_boundary = row_move_target(rows, self.app.focused, direction)
            if target is not None:
                focus_command_widget(self, target, self._scroll_container())
            if at_boundary:
                self.app.bell()
            self._sync_cursor_mode()
        finally:
            self._cursor_moving = False

    def _move_within_row(self, direction: int) -> None:
        """Move focus within the current row (+1 right, -1 left)."""
        if getattr(self, "_cursor_moving", False):
            return
        self._cursor_moving = True
        try:
            rows = group_widgets_into_rows(self._nav_widgets())
            if not rows:
                return
            target = within_row_target(rows, self.app.focused, direction)
            if target is not None:
                focus_command_widget(self, target, self._scroll_container())
                self._sync_cursor_mode()
            # Row edge / single-widget row: no-op (no bell, expected on the
            # common single-column case).
        finally:
            self._cursor_moving = False

    def action_activate_focused(self) -> None:
        activate_command_widget(self.app.focused)
        self._sync_cursor_mode()

    def on_key(self, event: events.Key) -> None:
        """Rescue keys that should have gone to an editing text field.

        In the real terminal driver, the priority-binding / key-forward path
        can deliver keys to the wrong widget (focus drift) even though
        `_active_command_text_widget` is set and in editing mode. Those keys
        bubble up here unconsumed. Re-focus the editing widget and re-dispatch
        the key to it so typing always lands.

        The normal path (focus already on the editing widget) stops bubbling
        inside `CommandInput._on_key`, so this handler is never reached in that
        case — no double-processing.
        """
        active = getattr(self, "_active_command_text_widget", None)
        if not is_editing_text(active):
            return
        # Only rescue when focus has actually drifted to another widget. When
        # focus is already on the editing widget, normal event flow handles
        # everything — intercepting here would stop events before App._on_key
        # fires non-priority bindings (e.g. backspace → delete_left).
        if self.app.focused is active:
            return
        # Rescue only non-navigation input. Navigation keys (w/s/a/d/e and
        # arrows/enter) are intentionally blocked by check_action while editing;
        # they must NOT force focus back to the editing field when focus has been
        # legitimately moved to another widget (e.g., a Button).
        _NAV_BINDING_KEYS = {b.key for b in _NAV_BINDINGS}
        _TEXT_EDIT_KEYS = {"backspace", "delete", "ctrl+h", "ctrl+w", "ctrl+u", "ctrl+k"}
        if not (event.is_printable or event.key in _TEXT_EDIT_KEYS):
            return
        if event.key in _NAV_BINDING_KEYS:
            return
        self.app.set_focus(active)
        # Re-post the key directly to the editing widget, bypassing App.on_event
        # and the priority-binding check that originally routed it elsewhere.
        active.post_message(event.__class__(event.key, event.character))
        event.stop()
        event.prevent_default()

    def _sync_cursor_mode(self) -> None:
        """Update app.cursor_state and the screen's StatusBar mode indicator."""
        active_text = getattr(self, "_active_command_text_widget", None)
        editing = is_editing_text(active_text) or is_editing_text(self.app.focused)
        mode = "edit" if editing else "nav"
        cursor_state = getattr(self.app, "cursor_state", None)
        if cursor_state is not None:
            cursor_state.mode = mode
        try:
            self.query_one(StatusBar).set_mode(mode)
        except NoMatches:
            pass

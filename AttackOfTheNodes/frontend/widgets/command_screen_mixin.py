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

from textual.css.query import NoMatches

from frontend.widgets.command_navigation import (
    activate_command_widget,
    command_focus_widgets,
    focus_command_widget,
    group_widgets_into_rows,
    is_editing_text,
    row_move_target,
    within_row_target,
)
from frontend.widgets.status_bar import StatusBar
from frontend.keymap import NAVIGATION, Profile, bindings_for
from frontend.keymap_runtime import KeymapScreenMixin


class CommandScreenMixin(KeymapScreenMixin):
    """Mixin providing standard command-mode navigation for Textual screens."""

    KEYMAP = Profile("command_navigation", NAVIGATION)
    BINDINGS = bindings_for(KEYMAP)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # Small legacy/test hosts can inherit the shared profile. Production
        # migrated screens declare their complete profile in the class body.
        if "KEYMAP" not in cls.__dict__:
            own = list(cls.__dict__.get("BINDINGS", []))
            keys = {b.key if hasattr(b, "key") else b[0] for b in own}
            cls.BINDINGS = own + [b for b in bindings_for(cls.KEYMAP) if b.key not in keys]
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
        if action in {"cursor_left", "cursor_right"} and not self._focused_in_multi_widget_row():
            # A single field retains its native caret positioning in NAV.
            return False
        return super().check_action(action, parameters)

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
                peek_target = None
                if not at_boundary:
                    peek_target, _ = row_move_target(rows, target, direction)
                focus_command_widget(
                    self,
                    target,
                    self._scroll_container(),
                    peek_widget=peek_target,
                )
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

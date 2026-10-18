"""Input widget with keyboard-command selection before text editing."""

from __future__ import annotations

import os
import time

from textual import events
from textual.widgets import Input, TextArea

from frontend.keymap import TEXT_INPUT, TEXT_AREA, bindings_for
from frontend.keymap_runtime import KeymapScreenMixin, screen_owns_key, navigation_keys

_DEBUG_LOG = os.environ.get("CI_EDIT_DEBUG")


def _dbg(*args) -> None:
    if not _DEBUG_LOG:
        return
    line = f"[{time.monotonic():.3f}] {' '.join(str(a) for a in args)}\n"
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write(line)
    except Exception:
        pass


EDITING_NAV_KEYS = {
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
}


def _move_input_cursor_to_end(widget: Input) -> None:
    try:
        widget.cursor_position = len(widget.value)
    except Exception:
        pass


def _move_text_area_cursor_to_end(widget: TextArea) -> None:
    try:
        lines = widget.text.splitlines()
        if not lines:
            widget.move_cursor((0, 0))
            return
        widget.move_cursor((len(lines) - 1, len(lines[-1])))
    except Exception:
        pass


def _move_command_input_cursor(widget: Input, key: str) -> bool:
    if key == "left":
        widget.cursor_position = max(0, widget.cursor_position - 1)
    elif key == "right":
        widget.cursor_position = min(len(widget.value), widget.cursor_position + 1)
    elif key == "home":
        widget.cursor_position = 0
    elif key == "end":
        widget.cursor_position = len(widget.value)
    else:
        return False
    return True


def _move_command_text_area_cursor(widget: TextArea, key: str) -> bool:
    actions = {
        "left": widget.action_cursor_left,
        "right": widget.action_cursor_right,
        "up": widget.action_cursor_up,
        "down": widget.action_cursor_down,
        "home": widget.action_cursor_line_start,
        "end": widget.action_cursor_line_end,
        "pageup": widget.action_cursor_page_up,
        "pagedown": widget.action_cursor_page_down,
    }
    action = actions.get(key)
    if action is None:
        return False
    action()
    return True


def _sync_screen_cursor_mode(widget) -> None:
    try:
        sync = getattr(widget.screen, "_sync_cursor_mode", None)
    except Exception:
        return
    if sync is not None:
        sync()
    widget.screen.refresh_bindings()


class CommandTextMixin(KeymapScreenMixin):
    """Native widget actions for edit transitions; no raw shortcut dispatcher."""

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if not self.auto_edit_on_focus and any(
            command.auto_edit_only and command.action_signature == (action, parameters)
            for command in self.KEYMAP.commands
        ):
            return False
        # Screen navigation is authoritative, including after a key override.
        # Only standalone controls use the widget's fallback navigation map.
        screen_profile = getattr(self.screen, "KEYMAP", None)
        if screen_profile is not None:
            for command in self.KEYMAP.commands:
                if command.action_signature != (action, parameters) or not command.navigation:
                    continue
                for other in screen_profile.commands:
                    if other.navigation != command.navigation or not set(other.keys) & set(command.keys):
                        continue
                    if command.row_fallback and self.screen.check_action(*other.action_signature) is False:
                        continue
                    return False
        return super().check_action(action, parameters)

    def action_begin_edit(self) -> None:
        self.begin_edit()

    def action_enter_edit(self) -> None:
        self.begin_edit()

    def action_caret_left(self) -> None:
        self._position_nav_caret("left")

    def action_caret_right(self) -> None:
        self._position_nav_caret("right")

    def _position_nav_caret(self, direction: str) -> None:
        move = _move_command_input_cursor if isinstance(self, Input) else _move_command_text_area_cursor
        move(self, direction)
        self._nav_cursor_positioned = True

    def action_finish_edit(self) -> None:
        self.end_edit()

    def action_revert_edit(self) -> None:
        self.end_edit(revert=True)

    def action_finish_enter(self) -> None:
        self.end_edit()

    def action_screen_up(self) -> None:
        self._run_screen_action("cursor_up")

    def action_screen_down(self) -> None:
        self._run_screen_action("cursor_down")

    def action_previous_field(self) -> None:
        self._run_screen_action("cursor_up")

    def action_next_field(self) -> None:
        self._run_screen_action("cursor_down")

    def action_auto_up(self) -> None:
        self.end_edit()
        self._run_screen_action("cursor_up")

    def action_auto_down(self) -> None:
        self.end_edit()
        self._run_screen_action("cursor_down")


class CommandInput(CommandTextMixin, Input):
    """Input that requires explicit activation before printable keys edit text."""

    KEYMAP = TEXT_INPUT
    BINDINGS = bindings_for(KEYMAP)

    def __init__(
        self,
        *args,
        auto_edit_on_focus: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.editing = False
        self.auto_edit_on_focus = auto_edit_on_focus
        self._edit_start_value = self.value
        # Command inputs append on edit; focusing must not select-all (which
        # would make the first keystroke replace the whole value).
        self.select_on_focus = False
        # Single-line command inputs render compact (1 row); the stylesheet
        # gives them a reserved left-accent column instead of a tall border.
        self.add_class("command-input", "single-line")

    def begin_edit(self, place_cursor_at_end: bool = True) -> None:
        active_text = getattr(self.screen, "_active_command_text_widget", None)
        if active_text is not self and hasattr(active_text, "end_edit"):
            active_text.end_edit()
        if not self.editing:
            self._edit_start_value = self.value
        self.editing = True
        self.add_class("editing")
        setattr(self.screen, "_active_command_text_widget", self)
        self.app.set_focus(self)
        _dbg("begin_edit", self.id, "focused_after_set_focus:", getattr(self.app, "focused", None) is self)
        if place_cursor_at_end and not getattr(self, "_nav_cursor_positioned", False):
            _move_input_cursor_to_end(self)
        self._nav_cursor_positioned = False
        _sync_screen_cursor_mode(self)

    def end_edit(self, revert: bool = False) -> None:
        if revert:
            self.value = self._edit_start_value
        else:
            self._edit_start_value = self.value
        self.editing = False
        self.remove_class("editing")
        if getattr(self.screen, "_active_command_text_widget", None) is self:
            setattr(self.screen, "_active_command_text_widget", None)
        _sync_screen_cursor_mode(self)

    def on_blur(self) -> None:
        pass

    def on_click(self, event: events.Click) -> None:
        self.begin_edit(place_cursor_at_end=False)

    def check_action(self, action: str, parameters: tuple) -> bool:
        if not self.editing and action in {
            "delete_left",
            "delete_right",
            "delete_left_word",
            "delete_right_word",
            "delete_left_all",
            "delete_right_all",
        }:
            return False
        return super().check_action(action, parameters)

    def check_consume_key(self, key: str, character: str | None) -> bool:
        if not self.editing:
            return False
        if key == "ctrl+q":
            return True  # editor owns revert, including hosts with App's Quit
        if screen_owns_key(self, key, priority_only=True):
            return False
        if character is not None and len(character) == 1 and character.isprintable():
            return True
        return key in {
            "escape",
            "ctrl+q",
            "tab",
            "shift+tab",
            "enter",
            "backspace",
            "delete",
            "ctrl+w",
            "ctrl+u",
            "ctrl+k",
            "ctrl+backspace",
            *EDITING_NAV_KEYS,
        }

    async def _on_key(self, event: events.Key) -> None:
        if self.editing:
            if event.key in EDITING_NAV_KEYS and _move_command_input_cursor(self, event.key):
                event.stop()
                event.prevent_default()
                return
            await super()._on_key(event)
            if event.key in EDITING_NAV_KEYS or event.is_printable:
                event.stop()
            return

        # Detect focus drift: another CommandInput/TextArea is actively editing
        # but focus landed here instead.  Handling keys as if THIS widget owned
        # the session would steal editing from the intended field, so we redirect.
        try:
            _drift_active = getattr(self.screen, "_active_command_text_widget", None)
        except Exception:
            _drift_active = None
        if (
            _drift_active is not None
            and _drift_active is not self
            and isinstance(_drift_active, (CommandInput, CommandTextArea))
            and _drift_active.editing
        ):
            if event.key in navigation_keys(self.screen if hasattr(self.screen, "KEYMAP") else self, role="activate"):
                # Re-focus the correct editing widget instead of taking over.
                self.app.set_focus(_drift_active)
                event.stop()
                event.prevent_default()
                return
            # For printable/delete keys: let them bubble to the screen rescue
            # handler rather than swallowing them here.  Nav keys bubble too but
            # the rescue handler explicitly ignores them (they are no-ops while
            # editing is active).
            return

        if screen_owns_key(self, event.key):
            return  # bubble to Textual's native screen binding

        if event.key in EDITING_NAV_KEYS:
            event.stop()
            event.prevent_default()
            return

        if event.is_printable:
            event.stop()
            event.prevent_default()

    def _run_screen_action(self, action_name: str) -> None:
        screen = self.screen
        action = getattr(screen, f"action_{action_name}", None)
        if action is not None:
            action()


class CommandTextArea(CommandTextMixin, TextArea):
    """Text area with the same command-before-edit behavior as CommandInput."""

    KEYMAP = TEXT_AREA
    BINDINGS = bindings_for(KEYMAP)

    def __init__(
        self,
        *args,
        auto_edit_on_focus: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.editing = False
        self.auto_edit_on_focus = auto_edit_on_focus
        self._edit_start_text = self.text
        self.add_class("command-input")

    def begin_edit(self, place_cursor_at_end: bool = True) -> None:
        active_text = getattr(self.screen, "_active_command_text_widget", None)
        if active_text is not self and hasattr(active_text, "end_edit"):
            active_text.end_edit()
        if not self.editing:
            self._edit_start_text = self.text
        self.editing = True
        self.read_only = False
        self.add_class("editing")
        setattr(self.screen, "_active_command_text_widget", self)
        self.app.set_focus(self)
        if place_cursor_at_end and not getattr(self, "_nav_cursor_positioned", False):
            _move_text_area_cursor_to_end(self)
        self._nav_cursor_positioned = False
        _sync_screen_cursor_mode(self)

    def end_edit(self, revert: bool = False) -> None:
        if revert:
            self.text = self._edit_start_text
        else:
            self._edit_start_text = self.text
        self.editing = False
        self.read_only = True
        self.remove_class("editing")
        if getattr(self.screen, "_active_command_text_widget", None) is self:
            setattr(self.screen, "_active_command_text_widget", None)
        _sync_screen_cursor_mode(self)

    def on_mount(self) -> None:
        self.read_only = True

    def on_blur(self) -> None:
        pass

    def on_click(self, event: events.Click) -> None:
        self.begin_edit(place_cursor_at_end=False)

    def check_consume_key(self, key: str, character: str | None) -> bool:
        if self.editing and key == "ctrl+q":
            return True
        if screen_owns_key(self, key, priority_only=True):
            return False
        return self.editing and key in {
            "escape",
            "ctrl+q",
            "ctrl+enter",
            "tab",
            "shift+tab",
            "enter",
            *EDITING_NAV_KEYS,
        }

    async def _on_key(self, event: events.Key) -> None:
        if self.editing:
            if event.key in EDITING_NAV_KEYS and _move_command_text_area_cursor(self, event.key):
                event.stop()
                event.prevent_default()
                return
            await super()._on_key(event)
            if event.key in EDITING_NAV_KEYS or event.is_printable or event.key == "enter":
                event.stop()
            return

        # Focus-drift guard: redirect to the correct editing widget.
        try:
            _drift_active = getattr(self.screen, "_active_command_text_widget", None)
        except Exception:
            _drift_active = None
        if (
            _drift_active is not None
            and _drift_active is not self
            and isinstance(_drift_active, (CommandInput, CommandTextArea))
            and _drift_active.editing
        ):
            if event.key in navigation_keys(self.screen if hasattr(self.screen, "KEYMAP") else self, role="activate"):
                self.app.set_focus(_drift_active)
                event.stop()
                event.prevent_default()
                return
            return  # Let printable/delete keys bubble to screen rescue handler

        if screen_owns_key(self, event.key):
            return  # bubble to Textual's native screen binding

        if event.key in EDITING_NAV_KEYS:
            event.stop()
            event.prevent_default()
            return

        if event.is_printable:
            event.stop()
            event.prevent_default()

    def _run_screen_action(self, action_name: str) -> None:
        screen = self.screen
        action = getattr(screen, f"action_{action_name}", None)
        if action is not None:
            action()

"""Input widget with keyboard-command selection before text editing."""

from __future__ import annotations

from textual import events
from textual.widgets import Input, TextArea


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
    if key in {"a", "left"}:
        widget.cursor_position = max(0, widget.cursor_position - 1)
    elif key in {"d", "right"}:
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
        "a": widget.action_cursor_left,
        "d": widget.action_cursor_right,
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


def _run_screen_tab_action(widget, key: str) -> bool:
    action_name = None
    if key in {"a", "left"}:
        action_name = "previous_config_tab"
    elif key in {"d", "right"}:
        action_name = "next_config_tab"
    if action_name is None:
        return False
    try:
        action = getattr(widget.screen, f"action_{action_name}", None)
    except Exception:
        return False
    if action is None:
        return False
    action()
    return True


class CommandInput(Input):
    """Input that requires explicit activation before printable keys edit text."""

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
        self.add_class("command-input")
        self.styles.height = 3
        self.styles.width = "100%"

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

    def check_consume_key(self, key: str, character: str | None) -> bool:
        return self.editing and key in {
            "escape",
            "ctrl+q",
            "tab",
            "shift+tab",
            "enter",
            *EDITING_NAV_KEYS,
        }

    async def _on_key(self, event: events.Key) -> None:
        if self.editing:
            if event.key == "escape":
                self.end_edit()
                event.stop()
                event.prevent_default()
                return
            if event.key == "ctrl+q":
                self.end_edit(revert=True)
                event.stop()
                event.prevent_default()
                return
            if event.key in ("tab", "shift+tab"):
                self.end_edit()
                self._run_screen_action(
                    "cursor_up" if event.key == "shift+tab" else "cursor_down"
                )
                event.stop()
                event.prevent_default()
                return
            if event.key == "enter":
                self.end_edit()
                await super()._on_key(event)
                event.stop()
                return
            if event.key in EDITING_NAV_KEYS and _move_command_input_cursor(self, event.key):
                event.stop()
                event.prevent_default()
                return
            await super()._on_key(event)
            if event.key in EDITING_NAV_KEYS or event.is_printable:
                event.stop()
            return

        if event.key in ("e", "enter"):
            self.begin_edit()
            event.stop()
            event.prevent_default()
            return

        if event.key in ("w", "up"):
            self._run_screen_action("cursor_up")
            event.stop()
            event.prevent_default()
            return

        if event.key in ("s", "down"):
            self._run_screen_action("cursor_down")
            event.stop()
            event.prevent_default()
            return

        if _run_screen_tab_action(self, event.key):
            event.stop()
            event.prevent_default()
            return

        if event.key in EDITING_NAV_KEYS:
            event.stop()
            event.prevent_default()
            return

        if _move_command_input_cursor(self, event.key):
            self._nav_cursor_positioned = True
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


class CommandTextArea(TextArea):
    """Text area with the same command-before-edit behavior as CommandInput."""

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
            if event.key == "escape":
                self.end_edit()
                event.stop()
                event.prevent_default()
                return
            if event.key == "ctrl+q":
                self.end_edit(revert=True)
                event.stop()
                event.prevent_default()
                return
            if event.key == "ctrl+enter":
                self.end_edit()
                event.stop()
                event.prevent_default()
                return
            if event.key in EDITING_NAV_KEYS and _move_command_text_area_cursor(self, event.key):
                event.stop()
                event.prevent_default()
                return
            await super()._on_key(event)
            if event.key in EDITING_NAV_KEYS or event.is_printable or event.key == "enter":
                event.stop()
            return

        if event.key in ("e", "enter"):
            self.begin_edit()
            event.stop()
            event.prevent_default()
            return

        if event.key in ("w", "up"):
            self._run_screen_action("cursor_up")
            event.stop()
            event.prevent_default()
            return

        if event.key in ("s", "down"):
            self._run_screen_action("cursor_down")
            event.stop()
            event.prevent_default()
            return

        if _run_screen_tab_action(self, event.key):
            event.stop()
            event.prevent_default()
            return

        if event.key in EDITING_NAV_KEYS:
            event.stop()
            event.prevent_default()
            return

        if _move_command_text_area_cursor(self, event.key):
            self._nav_cursor_positioned = True
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

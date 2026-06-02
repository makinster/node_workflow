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

    def begin_edit(self) -> None:
        active_text = getattr(self.screen, "_active_command_text_widget", None)
        if active_text is not self and hasattr(active_text, "end_edit"):
            active_text.end_edit()
        if not self.editing:
            self._edit_start_value = self.value
        self.editing = True
        self.add_class("editing")
        setattr(self.screen, "_active_command_text_widget", self)
        self.app.set_focus(self)

    def end_edit(self, revert: bool = False) -> None:
        if revert:
            self.value = self._edit_start_value
        else:
            self._edit_start_value = self.value
        self.editing = False
        self.remove_class("editing")
        if getattr(self.screen, "_active_command_text_widget", None) is self:
            setattr(self.screen, "_active_command_text_widget", None)

    def on_blur(self) -> None:
        pass

    def on_click(self, event: events.Click) -> None:
        self.begin_edit()
        event.stop()

    async def _on_key(self, event: events.Key) -> None:
        if self.editing:
            if event.key in ("escape", "ctrl+q"):
                self.end_edit(revert=True)
                event.stop()
                event.prevent_default()
                return
            if event.key == "enter":
                self.end_edit()
                await super()._on_key(event)
                event.stop()
                return
            if event.key in {"up", "down", "pageup", "pagedown"}:
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

    def begin_edit(self) -> None:
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

    def on_mount(self) -> None:
        self.read_only = True

    def on_blur(self) -> None:
        pass

    def on_click(self, event: events.Click) -> None:
        self.begin_edit()
        event.stop()

    async def _on_key(self, event: events.Key) -> None:
        if self.editing:
            if event.key in ("escape", "ctrl+q"):
                self.end_edit(revert=True)
                event.stop()
                event.prevent_default()
                return
            if event.key == "ctrl+enter":
                self.end_edit()
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

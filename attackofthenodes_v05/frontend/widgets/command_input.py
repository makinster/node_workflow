"""Input widget with keyboard-command selection before text editing."""

from __future__ import annotations

from textual import events
from textual.widgets import Input, TextArea


class CommandInput(Input):
    """Input that requires explicit activation before printable keys edit text."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.editing = False
        self.add_class("command-input")
        self.styles.height = 3
        self.styles.width = "100%"

    def begin_edit(self) -> None:
        self.editing = True
        self.add_class("editing")
        self.app.set_focus(self)

    def end_edit(self) -> None:
        self.editing = False
        self.remove_class("editing")

    def on_blur(self) -> None:
        self.end_edit()

    def on_click(self, _event: events.Click) -> None:
        self.begin_edit()

    async def _on_key(self, event: events.Key) -> None:
        if self.editing:
            if event.key == "escape":
                self.end_edit()
                event.stop()
                event.prevent_default()
                return
            await super()._on_key(event)
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.editing = False
        self.add_class("command-input")

    def begin_edit(self) -> None:
        self.editing = True
        self.read_only = False
        self.add_class("editing")
        self.app.set_focus(self)

    def end_edit(self) -> None:
        self.editing = False
        self.read_only = True
        self.remove_class("editing")

    def on_mount(self) -> None:
        self.read_only = True

    def on_blur(self) -> None:
        self.end_edit()

    def on_click(self, _event: events.Click) -> None:
        self.begin_edit()

    async def _on_key(self, event: events.Key) -> None:
        if self.editing:
            if event.key == "escape":
                self.end_edit()
                event.stop()
                event.prevent_default()
                return
            await super()._on_key(event)
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

        if event.is_printable:
            event.stop()
            event.prevent_default()

    def _run_screen_action(self, action_name: str) -> None:
        screen = self.screen
        action = getattr(screen, f"action_{action_name}", None)
        if action is not None:
            action()

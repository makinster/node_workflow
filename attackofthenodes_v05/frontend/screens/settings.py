"""Settings modal."""

from __future__ import annotations

from typing import Any, Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Static

from backend.configuration_manager import DEFAULT_SETTINGS
from frontend.widgets.command_input import CommandInput


class SettingsScreen(ModalScreen):
    """Configuration form generated from configuration metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        Binding("e", "activate_focused", "Activate", priority=True),
        Binding("enter", "activate_focused", "Activate", priority=True),
    ]

    def __init__(self, configuration_manager) -> None:
        super().__init__()
        self.configuration_manager = configuration_manager

    def compose(self) -> ComposeResult:
        values = self.configuration_manager.get_all()
        with Vertical(id="modal-card"):
            yield Label("Settings", classes="modal-title")
            yield Static("W/S move  E edit/toggle  Ctrl+S save  Esc close", classes="modal-help")
            for key, default in DEFAULT_SETTINGS.items():
                yield Label(key, classes="form-label")
                value = values.get(key, default)
                if isinstance(default, bool):
                    yield Checkbox(value=bool(value), id=f"setting-{key}")
                else:
                    yield CommandInput(value=str(value), id=f"setting-{key}")
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save-settings", variant="primary")
                yield Button("Cancel", id="cancel-settings", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings":
            self.action_save()
        elif event.button.id == "cancel-settings":
            self.action_cancel()

    def on_mount(self) -> None:
        widgets = self._keyboard_focus_widgets()
        if widgets:
            self.app.set_focus(widgets[0])

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            if action in {"cursor_up", "cursor_down", "activate_focused"}:
                return False
        return True

    def action_save(self) -> None:
        values: Dict[str, Any] = {}
        for key, default in DEFAULT_SETTINGS.items():
            widget = self.query_one(f"#setting-{key}")
            if isinstance(default, bool):
                values[key] = bool(widget.value)
            elif isinstance(default, int):
                try:
                    values[key] = int(widget.value)
                except ValueError:
                    values[key] = default
            else:
                values[key] = str(widget.value)
        self.dismiss({"action": "save", "settings": values})

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        self._move_keyboard_focus(-1)

    def action_cursor_down(self) -> None:
        self._move_keyboard_focus(1)

    def action_activate_focused(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput):
            focused.begin_edit()
        elif isinstance(focused, Checkbox):
            focused.value = not focused.value
        elif isinstance(focused, Button):
            focused.press()

    def _move_keyboard_focus(self, direction: int) -> None:
        widgets = self._keyboard_focus_widgets()
        if not widgets:
            return
        current = self.app.focused
        try:
            current_index = widgets.index(current)
        except ValueError:
            current_index = 0 if direction > 0 else len(widgets) - 1
        next_index = max(0, min(len(widgets) - 1, current_index + direction))
        focused = widgets[next_index]
        if isinstance(focused, CommandInput):
            focused.end_edit()
        self.app.set_focus(focused)
        focused.scroll_visible()

    def _keyboard_focus_widgets(self) -> list[Any]:
        focusable_types = (CommandInput, Checkbox, Button)
        return [
            widget
            for widget in self.query("*")
            if isinstance(widget, focusable_types) and not getattr(widget, "disabled", False)
        ]

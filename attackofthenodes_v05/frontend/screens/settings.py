"""Settings modal."""

from __future__ import annotations

from typing import Any, Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label, Static

from backend.configuration_manager import DEFAULT_SETTINGS
from frontend.widgets.command_navigation import command_focus_widgets
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_screen_mixin import CommandScreenMixin


class SettingsScreen(CommandScreenMixin, ModalScreen):
    """Configuration form generated from configuration metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
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
        self._focus_first()

    def _nav_widgets(self) -> list[Any]:
        return command_focus_widgets(self, (CommandInput, Checkbox, Button))

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

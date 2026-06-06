"""Settings modal."""

from __future__ import annotations

from typing import Any, Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label, Static

from backend.configuration_manager import DEFAULT_SETTINGS
from frontend.widgets.command_navigation import command_focus_widgets
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.status_bar import StatusBar


class SettingsScreen(CommandScreenMixin, ModalScreen):
    """Configuration form generated from configuration metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        Binding("k", "api_keys", "API Keys", priority=True),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, configuration_manager) -> None:
        super().__init__()
        self.configuration_manager = configuration_manager

    def compose(self) -> ComposeResult:
        values = self.configuration_manager.get_all()
        with Vertical(id="modal-card"):
            yield Label("Settings", classes="modal-title")
            yield Static("W/S move | E edit/toggle | K API keys | Ctrl+S save", classes="modal-help")
            for key, default in DEFAULT_SETTINGS.items():
                yield Label(key, classes="form-label")
                value = values.get(key, default)
                if isinstance(default, bool):
                    yield Checkbox(value=bool(value), id=f"setting-{key}")
                else:
                    yield CommandInput(value=str(value), id=f"setting-{key}")
            with Vertical(classes="button-row"):
                yield Button("API Keys", id="api-keys-settings", variant="default")
                yield Button("Save", id="save-settings", variant="primary")
                yield Button("Cancel", id="cancel-settings", variant="default")
            yield StatusBar("W/S move | E edit/toggle | K API keys | Ctrl+S save")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings":
            self.action_save()
        elif event.button.id == "cancel-settings":
            self.action_cancel()
        elif event.button.id == "api-keys-settings":
            self.action_api_keys()

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

    def action_api_keys(self) -> None:
        self.app.push_screen(ApiKeysPlaceholderScreen())


class ApiKeysPlaceholderScreen(CommandScreenMixin, ModalScreen):
    """Placeholder for future API key management."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("API Keys", classes="modal-title")
            yield Static("API key settings will live here.", classes="form-description")
            yield Button("Cancel", id="cancel-api-keys", variant="default")

    def on_mount(self) -> None:
        self._focus_first()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-api-keys":
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)

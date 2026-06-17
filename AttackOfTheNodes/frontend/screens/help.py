"""Help modal."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from frontend.widgets.command_screen_mixin import CommandScreenMixin


HELP_TEXT = {
    "editor": [
        "Editor",
        "  W/S or ↑/↓            Move through nodes",
        "  A/D or ←/→            Switch branches",
        "  Ctrl+A/D or Ctrl+←/→  Switch incomplete branches",
        "  E or Enter            Select / edit",
        "  I                     Insert after selection",
        "  X or Backspace        Delete selection",
        "  Z                     Undo delete",
        "  B                     Toggle breakpoint",
        "  Ctrl+B                Clear breakpoints",
        "  V                     Validate workflow",
        "  H or ?                Help",
        "",
        "  Ctrl+S                Save workflow",
        "  Ctrl+R                Run workflow",
        "  Ctrl+N                New workflow",
        "  Ctrl+O                File",
        "  Ctrl+E                Options",
        "  Ctrl+Q                Quit",
    ],
    "execution": [
        "Execution",
        "  P    Pause / resume",
        "  S    Stop",
        "  M    Memory",
        "  O    Output",
        "  E    Errors",
        "  Esc  Stop and return to editor",
    ],
    "node_config": [
        "Config",
        "  W/S or ↑/↓  Move through fields",
        "  A/D or ←/→  Switch tabs",
        "  E or Enter  Edit / choose",
        "  Ctrl+S      Save",
        "  Ctrl+Enter  Save multiline text",
        "  Esc         Leave field or cancel",
        "  Ctrl+Q      Revert field edit",
    ],
    "node_selector": [
        "Selector",
        "  W/S or ↑/↓  Move through nodes",
        "  A/D         Switch tabs",
        "  E or Enter  Add / open group",
        "  /           Filter",
        "  Esc         Cancel",
    ],
    "workflow_library": [
        "File",
        "  W/S or ↑/↓  Move through workflows",
        "  E or Enter  Choose highlighted item",
        "  Esc         Cancel",
    ],
    "settings": [
        "Options",
        "  W/S or ↑/↓  Move through settings",
        "  E or Enter  Edit / toggle",
        "  Ctrl+S      Save",
        "  Esc         Cancel",
    ],
    "general": [
        "General",
        "  Ctrl+S  Save workflow",
        "  Ctrl+R  Run workflow",
        "  Ctrl+N  New workflow",
        "  Ctrl+O  File",
        "  Ctrl+E  Options",
        "  H or ?  Help",
        "  Ctrl+C  Copy selected text",
        "  Ctrl+Q  Quit from editor",
    ],
}


class HelpScreen(CommandScreenMixin, ModalScreen):
    """Keyboard reference and short TUI usage guide."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
    ]

    def __init__(self, context: str = "general") -> None:
        super().__init__()
        self.context = context if context in HELP_TEXT else "general"

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Help", classes="modal-title")
            yield Static(
                "\n".join(HELP_TEXT[self.context]),
                id="help-text",
            )
            yield Button("Cancel", id="close-help", variant="default")

    def on_mount(self) -> None:
        self._focus_first()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-help":
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)

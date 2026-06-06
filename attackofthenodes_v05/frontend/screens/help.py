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
        "  W/S or ^/v           Move through nodes",
        "  A/D or </>           Switch branches",
        "  Ctrl+A/D or Ctrl+</> Switch incomplete branches",
        "  E                    Select / edit",
        "  I                    Insert after selection",
        "  V                    Check workflow",
        "  B                    Toggle breakpoint",
        "  F                    File",
        "  O                    Options",
    ],
    "execution": [
        "Execution",
        "  P       pause / resume",
        "  S       stop",
        "  M       memory",
        "  O       output",
        "  E       errors",
        "  Esc     stop and return to editor",
    ],
    "node_config": [
        "Node Config",
        "  W/S or ^/v  move through fields",
        "  E           edit / choose",
        "  Esc         leave field or cancel",
        "  Ctrl+S      save",
        "  Ctrl+Enter  save multiline text",
    ],
    "workflow_library": [
        "File",
        "  W/S or ^/v  move through workflows",
        "  E / Enter   choose highlighted item",
        "  Esc         cancel",
    ],
    "settings": [
        "Options",
        "  W/S or ^/v  move through settings",
        "  E           edit / toggle",
        "  Ctrl+S      save",
        "  Esc         cancel",
    ],
    "general": [
        "General",
        "  Ctrl+S  save workflow",
        "  Ctrl+R  run workflow",
        "  Ctrl+N  new workflow",
        "  Ctrl+O  file",
        "  Ctrl+E  options",
        "  H / ?   help",
        "  Ctrl+C  copy selected text",
        "  Ctrl+Q  quit from editor",
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

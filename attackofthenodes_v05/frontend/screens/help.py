"""Help modal."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HelpScreen(ModalScreen):
    """Keyboard reference and short TUI usage guide."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Help", classes="modal-title")
            yield Static(
                "\n".join(
                    [
                        "Global",
                        "  Ctrl+S  Save workflow",
                        "  Ctrl+R  Run workflow",
                        "  Ctrl+N  New workflow",
                        "  Ctrl+O  Workflow library",
                        "  Ctrl+E  Settings",
                        "  ?       Help",
                        "  Q / Ctrl+Q  Back / close modal (works while typing)",
                        "  Ctrl+C      Quit to terminal",
                        "",
                        "Editor",
                        "  ↑↓ or W/S            Vertical movement",
                        "  ←→ or A/D            Branches in progress",
                        "  Ctrl+←→ or Ctrl+A/D  Complete branches",
                        "  Enter or E           Select/edit highlighted row",
                        "  I                    Insert after highlighted node",
                        "  B                    Toggle breakpoint",
                        "  Ctrl+B               Clear all breakpoints",
                        "  V                    Validate workflow",
                        "",
                        "Branch Editing",
                        "  Select the Branch Select row under a branch node.",
                        "  Enter opens the branch chooser.",
                        "  A/D cycles branches that do not yet have a Branch End.",
                        "  Ctrl+A/D cycles branches that already have a Branch End.",
                        "  I inserts after the highlighted node.",
                        "",
                        "Node Config",
                        "  Ctrl+S or Ctrl+Enter  Save",
                        "  Esc                  Cancel",
                        "  Tab / Shift+Tab      Move focus",
                        "",
                        "Execution",
                        "  P       Pause/resume",
                        "  S       Stop",
                        "  M/O/E   Memory, output, errors",
                        "  Esc/Q   Stop active run and return to editor",
                    ]
                ),
                id="help-text",
            )
            yield Button("Close", id="close-help", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-help":
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)

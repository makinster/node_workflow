"""Simple Yes/No confirmation modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmScreen(ModalScreen):
    """Modal that asks the user to confirm or cancel a destructive action."""

    BINDINGS = [
        ("y", "confirm_yes", "Yes"),
        ("n", "confirm_no", "No"),
        ("escape", "confirm_no", "No"),
        Binding("ctrl+q", "confirm_no", "Cancel", priority=True),
    ]

    def __init__(self, message: str, yes_label: str = "Yes", no_label: str = "No") -> None:
        super().__init__()
        self._message = message
        self._yes_label = yes_label
        self._no_label = no_label

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="confirm-modal"):
            yield Label(self._message, classes="modal-title")
            yield Label("Y confirm  N / Esc cancel", classes="modal-help")
            with Horizontal(classes="button-row"):
                yield Button(self._yes_label, id="confirm-yes", variant="warning")
                yield Button(self._no_label, id="confirm-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def action_confirm_yes(self) -> None:
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        self.dismiss(False)

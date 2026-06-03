"""User input modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.command_input import CommandInput
from frontend.widgets.status_bar import StatusBar


class UserInputScreen(CommandScreenMixin, ModalScreen):
    """Prompt shown when a user-input node suspends a supervisor."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "submit", "Submit"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, branch_id: str, node_id: str, prompt: str) -> None:
        super().__init__()
        self.branch_id = branch_id
        self.node_id = node_id
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("User Input Needed", classes="modal-title")
            yield Static(f"Node: {self.node_id}\nBranch: {self.branch_id}")
            yield Static("Type response  Ctrl+Enter submit  Esc leaves edit/cancels", classes="modal-help")
            yield Label(self.prompt, classes="form-label")
            yield CommandInput(id="user-input-value", auto_edit_on_focus=True)
            with Horizontal(classes="button-row"):
                yield Button("Submit", id="submit-user-input", variant="primary")
                yield Button("Cancel", id="cancel-user-input", variant="default")
            yield StatusBar("Type response  Ctrl+Enter submit  Esc leaves edit/cancels")

    def on_mount(self) -> None:
        self._focus_first()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self.action_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-user-input":
            self.action_submit()
        elif event.button.id == "cancel-user-input":
            self.action_cancel()

    def action_submit(self) -> None:
        value = self.query_one("#user-input-value", Input).value
        self.dismiss({"branch_id": self.branch_id, "value": value})

    def action_cancel(self) -> None:
        stop = getattr(self.app, "stop_active_workflow", None)
        if stop is not None:
            stop()
        self.dismiss(None)

"""User input modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from rich.text import Text

from frontend.colors import MUTED
from textual.widgets import Button, Input, Label, Static

from frontend.keymap import USER_INPUT, bindings_for

from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.command_input import CommandInput
from frontend.widgets.status_bar import StatusBar


class UserInputScreen(CommandScreenMixin, ModalScreen):
    """Prompt shown when a user-input node suspends a supervisor."""

    KEYMAP = USER_INPUT
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, branch_id: str, node_id: str, prompt: str, asker: str = "",
                 path: list | tuple = ()) -> None:
        super().__init__()
        self.branch_id = branch_id
        self.node_id = node_id
        self.prompt = prompt
        # Step 4c-2 (owner samples, 2026-10-20): who asks, and from where.
        self.asker = asker
        self.path = list(path)

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label(f"{self.asker} asks" if self.asker else "User Input Needed",
                        classes="modal-title", markup=False)
            where = Text("From ", style=MUTED)
            for index, name in enumerate(self.path or [self.node_id]):
                where.append(" › " if index else "", style=MUTED)
                where.append(str(name), style="bold" if index == len(self.path or [1]) - 1 else MUTED)
            yield Static(where, id="user-input-from")
            yield Label(self.prompt, classes="form-label")
            yield CommandInput(id="user-input-value")
            with Horizontal(classes="button-row"):
                yield Button("Send", id="submit-user-input", variant="primary")
                yield Button("Cancel", id="cancel-user-input", variant="default")
            yield StatusBar("type an answer | ctrl+enter send | esc cancel")

    def on_mount(self) -> None:
        self._focus_first()
        # Start in text entry, but avoid auto-edit's W/S focus navigation:
        # those letters belong to the user's answer while editing.
        self.query_one("#user-input-value", CommandInput).begin_edit()

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

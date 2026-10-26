"""Simple Yes/No confirmation modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from frontend.keymap import CONFIRM, bindings_for, hint_for
from frontend.widgets.command_navigation import command_focus_widgets
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.contract_rows import CompactRowButton


class ConfirmScreen(CommandScreenMixin, ModalScreen):
    """Modal that asks the user to confirm or cancel a destructive action."""

    KEYMAP = CONFIRM
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, message: str, yes_label: str = "Yes", no_label: str = "No", *,
                 initial_no: bool = False, role_highlight: bool = False) -> None:
        super().__init__()
        self._message = message
        self._yes_label = yes_label
        self._no_label = no_label
        self._initial_no = initial_no
        self._role_highlight = role_highlight

    def compose(self) -> ComposeResult:
        button = CompactRowButton if self._role_highlight else Button
        options = {"selected_foreground_role": "NAME"} if self._role_highlight else {}
        with Vertical(id="modal-card", classes="confirm-modal"):
            yield Label(self._message, classes="modal-title")
            yield Label(hint_for(self.KEYMAP), classes="modal-help")
            with Horizontal(classes="button-row"):
                yield button(self._yes_label, id="confirm-yes", variant="warning", **options)
                yield button(self._no_label, id="confirm-no", variant="default", **options)

    def on_mount(self) -> None:
        if self._initial_no:
            self.query_one("#confirm-no", Button).focus()
        else:
            self._focus_first()

    def _nav_widgets(self):
        return command_focus_widgets(self, (Button,))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def action_confirm_yes(self) -> None:
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        self.dismiss(False)

"""Save / Discard / Stay prompt for leaving a node editor with edits (U9)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from frontend.keymap import UNSAVED_CHANGES, bindings_for

from frontend.widgets.command_navigation import command_focus_widgets
from frontend.widgets.command_screen_mixin import CommandScreenMixin

SAVE = "save"
DISCARD = "discard"


class UnsavedChangesScreen(CommandScreenMixin, ModalScreen):
    """Dismisses with ``"save"``, ``"discard"`` or ``None`` (stay)."""

    KEYMAP = UNSAVED_CHANGES
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, node_name: str) -> None:
        super().__init__()
        self.node_name = node_name

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="confirm-modal"):
            yield Label(f"Unsaved changes to {self.node_name}", classes="modal-title")
            yield Label("Esc stay", classes="modal-help")
            with Horizontal(classes="button-row"):
                yield Button("Save", id="unsaved-save", variant="primary", compact=True)
                yield Button("Discard", id="unsaved-discard", variant="error", compact=True)
                yield Button("Stay", id="unsaved-stay", variant="default", compact=True)

    def on_mount(self) -> None:
        self._focus_first()

    def _nav_widgets(self):
        return command_focus_widgets(self, (Button,))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "unsaved-save":
            self.dismiss(SAVE)
        elif event.button.id == "unsaved-discard":
            self.dismiss(DISCARD)
        else:
            self.action_stay()

    def action_stay(self) -> None:
        self.dismiss(None)

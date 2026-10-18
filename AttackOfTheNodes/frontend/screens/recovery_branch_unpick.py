"""Unpick confirmation for an Error Mux recovery branch that has nodes (U1)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

LEAVE_UNLINKED = "leave"
DELETE_BRANCH = "delete"


from frontend.keymap import RECOVERY_BRANCH_UNPICK, bindings_for
from frontend.keymap_runtime import KeymapScreenMixin

class RecoveryBranchUnpickScreen(KeymapScreenMixin, ModalScreen):
    """Ask what happens to a recovery branch whose last error was unpicked.

    Dismisses with ``"leave"`` (keep the nodes, drop the connection),
    ``"delete"`` (delete the listed nodes on save) or ``None`` (cancel:
    the error is picked again).
    """

    KEYMAP = RECOVERY_BRANCH_UNPICK
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, branch_label: str, node_labels: list[str]) -> None:
        super().__init__()
        self.branch_label = branch_label
        self.node_labels = node_labels

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label(f"Recovery branch “{self.branch_label}” has nodes", classes="modal-title")
            yield Static(
                "No error picked leads here any more. Keep these nodes without a "
                "connection, or delete them when you save?",
                classes="modal-help",
            )
            yield Static(
                "\n".join(f"  • {label}" for label in self.node_labels) or "  (none)",
                id="unpick-branch-nodes",
                classes="modal-help",
                markup=False,
            )
            with Horizontal(classes="button-row"):
                yield Button("Leave unlinked", id="unpick-leave", variant="primary", compact=True)
                yield Button("Delete branch", id="unpick-delete", variant="error", compact=True)
                yield Button("Cancel", id="unpick-cancel", variant="default", compact=True)

    def on_mount(self) -> None:
        self.query_one("#unpick-leave", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "unpick-leave":
            self.dismiss(LEAVE_UNLINKED)
        elif event.button.id == "unpick-delete":
            self.dismiss(DELETE_BRANCH)
        else:
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)

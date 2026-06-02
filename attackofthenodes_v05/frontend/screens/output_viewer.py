"""Output viewer modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static
from rich.text import Text

from frontend.output_records import branch_names, format_output_record, normalize_outputs


class OutputViewerScreen(ModalScreen):
    """Scrollable run output log."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
    ]

    def __init__(self, outputs) -> None:
        super().__init__()
        self.records = normalize_outputs(outputs or [])
        self.active_branch = "all"

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Output", classes="modal-title")
            yield Select(
                [(name, name) for name in branch_names(self.records)],
                value="all",
                id="output-branch-filter",
            )
            yield Static("", id="output-log")
            yield Button("Close", id="close-output", variant="default")

    def on_mount(self) -> None:
        self._refresh_output_text()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "output-branch-filter":
            self.active_branch = str(event.value)
            self._refresh_output_text()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-output":
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)

    def _refresh_output_text(self) -> None:
        records = self.records
        if self.active_branch != "all":
            records = [
                record
                for record in records
                if record.get("branch_id") == self.active_branch
            ]
        content = "\n".join(format_output_record(record) for record in records)
        self.query_one("#output-log", Static).update(Text(content or "-"))

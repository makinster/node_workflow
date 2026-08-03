"""In-TUI file viewer modal (FO3, docs/FILE_OUTPUT_BUILD_PLAN.md).

Pushed by the app when a FILE_VIEW_REQUESTED event arrives. Renders Markdown
natively via Textual's Markdown widget; everything else shows as plain text.
The file is read here, at display time — the event carries only the path and
render hint, never file contents.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Markdown, Static
from rich.text import Text


class FileViewerScreen(ModalScreen):
    """Scrollable viewer for a text or Markdown file."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
    ]

    def __init__(self, path: str, render: str = "plain") -> None:
        super().__init__()
        self.path = str(path)
        self.render_hint = "markdown" if render == "markdown" else "plain"

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="fill-modal"):
            yield Label(Path(self.path).name or "File", classes="modal-title")
            yield Static(self.path, id="file-viewer-path")
            with VerticalScroll(id="file-viewer-scroll"):
                if self.render_hint == "markdown":
                    yield Markdown(self._read_contents(), id="file-viewer-markdown")
                else:
                    yield Static(
                        Text(self._read_contents()), id="file-viewer-plain"
                    )
            yield Button("Close", id="close-file-viewer", variant="default")

    def on_mount(self) -> None:
        self.query_one("#file-viewer-scroll", VerticalScroll).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-file-viewer":
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)

    def _read_contents(self) -> str:
        try:
            return Path(self.path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Could not read file:\n{exc}"

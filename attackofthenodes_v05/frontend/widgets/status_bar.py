"""Context-sensitive bottom status bar."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    """A compact footer showing the useful bindings for the active context."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        padding: 0 1;
    }
    """

    def set_bindings_text(self, text: str) -> None:
        """Replace the displayed binding hint."""
        self.update(text)

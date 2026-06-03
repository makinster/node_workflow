"""Context-sensitive bottom status bar."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    """A compact footer showing mode indicator and useful bindings for the active context."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self, binding_text: str = "") -> None:
        self._binding_text = binding_text
        self._mode = "nav"
        super().__init__(self._formatted())

    def set_mode(self, mode: str) -> None:
        """Update the [NAV]/[EDIT] indicator."""
        self._mode = mode
        self.update(self._formatted())

    def set_bindings_text(self, text: str) -> None:
        """Replace the displayed binding hint."""
        self._binding_text = text
        self.update(self._formatted())

    def _formatted(self) -> str:
        indicator = "[NAV]" if self._mode == "nav" else "[EDIT]"
        if self._binding_text:
            return f"{indicator}  {self._binding_text}"
        return indicator

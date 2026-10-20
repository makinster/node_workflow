"""The editor's Validation panel (owner, 2026-10-19; samples 2026-10-20).

V opens and closes it at the top of the editor's right pane. A Run
validation button sits at its top; below it the last run's issues, errors
first, one line each: mark, node name, message. The editor moves the cursor
(W/S) and activates it (E/Enter): the button runs validation, an issue row
goes to its node.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Button, Label, ListItem, ListView, Static

from frontend import colors


class ValidationPanel(Vertical):
    """Run validation button plus the last run's issues."""

    DEFAULT_CSS = """
    ValidationPanel {
        height: auto;
        border: round $primary;
        padding: 0 1;
        margin-bottom: 1;
    }
    ValidationPanel #validation-summary { height: auto; }
    ValidationPanel #validation-list {
        height: auto;
        max-height: 10;
        background: transparent;
    }
    ValidationPanel #validation-list > ListItem {
        height: 1;
        background: transparent;
    }
    ValidationPanel #validation-list Label { width: 1fr; text-wrap: nowrap; text-overflow: ellipsis; }
    ValidationPanel #validation-run:focus,
    ValidationPanel #validation-list > ListItem.-highlight {
        background: HIGHLIGHT;
        color: $text;
        text-style: bold;
    }
    """.replace("HIGHLIGHT", colors.HIGHLIGHT)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        #: One run's issues, each ``{"level", "node_id", "name", "message"}``;
        #: ``None`` until the first run.
        self.issues: Optional[List[Dict[str, str]]] = None
        self._labels: List[Label] = []

    def compose(self):
        yield Label("Validation", classes="panel-title")
        yield Button("Run validation", id="validation-run", compact=True)
        yield Static("", id="validation-summary")
        yield ListView(id="validation-list")

    def on_mount(self) -> None:
        self.show_issues(self.issues)

    # -- content ------------------------------------------------------------

    def show_issues(self, issues: Optional[List[Dict[str, str]]]) -> None:
        self.issues = issues
        if not self.is_mounted:
            return
        summary = self.query_one("#validation-summary", Static)
        list_view = self.query_one("#validation-list", ListView)
        list_view.clear()
        self._labels = []
        list_view.display = bool(issues)
        if issues is None:
            summary.update(Text("Not run yet", style=colors.MUTED))
            return
        if not issues:
            summary.update(Text.assemble(("✓ ", colors.SUCCESS), ("Last run: no issues", colors.MUTED)))
            return
        errors = sum(1 for issue in issues if issue["level"] == "error")
        warnings = len(issues) - errors
        parts = [f"{n} {word}{'s' if n != 1 else ''}"
                 for n, word in ((errors, "error"), (warnings, "warning")) if n]
        summary.update(Text("Last run: " + " · ".join(parts), style=colors.MUTED))
        width = max(len(issue["name"]) for issue in issues)
        for issue in issues:
            self._labels.append(Label(self._row(issue, width, highlighted=False)))
            list_view.append(ListItem(self._labels[-1]))
        list_view.index = None

    @staticmethod
    def _row(issue: Dict[str, str], width: int, highlighted: bool) -> Text:
        error = issue["level"] == "error"
        mark_style = "bold" if highlighted else f"bold {colors.ERROR if error else colors.WARNING}"
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(("✗ " if error else "! "), style=mark_style)
        text.append(f"{issue['name']:<{width}}  ", style="bold")
        text.append(issue["message"])
        return text

    def _restyle_rows(self) -> None:
        """Plain text on the highlighted row, coloured marks on the others."""
        if not self.issues:
            return
        index = self.list_view.index
        width = max(len(issue["name"]) for issue in self.issues)
        for row, (label, issue) in enumerate(zip(self._labels, self.issues)):
            label.update(self._row(issue, width, highlighted=row == index))

    # -- cursor (driven by the editor's W/S/E) --------------------------------

    @property
    def list_view(self) -> ListView:
        return self.query_one("#validation-list", ListView)

    @property
    def selected_issue(self) -> Optional[Dict[str, str]]:
        index = self.list_view.index
        if self.issues and index is not None and self.list_view.has_focus:
            return self.issues[index]
        return None

    def focus_button(self) -> None:
        self.list_view.index = None
        self._restyle_rows()
        self.query_one("#validation-run", Button).focus()

    def move(self, step: int) -> None:
        list_view = self.list_view
        on_list = list_view.has_focus and list_view.index is not None
        count = len(self.issues or [])
        if not on_list:
            if step > 0 and count:
                list_view.index = 0
                list_view.focus()
                self._restyle_rows()
            return
        index = list_view.index + step
        if index < 0:
            self.focus_button()
            return
        list_view.index = min(index, count - 1)
        self._restyle_rows()

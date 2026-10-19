"""Vault log: every Vault write in the run, and one write in full (EX).

Owner-approved samples, 2026-10-19: columns Time, Key, Type (coloured like
elsewhere), Value (shortened) and Source (``S3B2 Save note``: map step,
branch number, node name). The highlighted row opens with E; in the entry,
A/D step to the same key's earlier or later writes. ``/`` filters by key,
value or source. Writes come from ``MemoryBank.writes()``.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static

from frontend.io_contract import TYPE_COLOR
from frontend.widgets.status_bar import StatusBar

SourceLabel = Callable[[Dict[str, Any]], str]
VALUE_WIDTH = 30


def clock(seconds: Any) -> str:
    total = int(float(seconds or 0))
    return f"{total // 60}:{total % 60:02d}"


def value_text(value: Any) -> str:
    """A value as one line: text quoted, everything else as JSON."""
    if isinstance(value, str):
        return f'"{value}"'
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


def shorten(text: str, width: int = VALUE_WIDTH) -> str:
    """One line, at most ``width`` characters; a quoted value keeps its closing quote."""
    text = " ".join(text.split())
    if len(text) <= width:
        return text
    if text.endswith('"'):
        return text[: width - 2] + '…"'
    return text[: width - 1] + "…"


def kind_of(value: Any) -> str:
    """The data type a value would have on a port."""
    if isinstance(value, dict) and value.get("type") == "file":
        return "file"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "var"


def type_cell(type_tag: Any, value: Any = None) -> Text:
    """``[type]`` in the type colour; untyped writes show the value's type."""
    return Text(f"[{type_tag or kind_of(value)}]", style=TYPE_COLOR)


class VaultLogScreen(ModalScreen):
    """The whole run's Vault writes, newest last."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        Binding("e", "open_entry", "Open", priority=True),
        Binding("enter", "open_entry", "Open", priority=True),
        Binding("slash", "filter", "Filter", priority=True),
    ]

    def __init__(self, writes: List[Dict[str, Any]], source_label: SourceLabel) -> None:
        super().__init__()
        self.all_writes = list(writes)
        self.writes = list(writes)
        self.source_label = source_label

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="fill-modal"):
            yield Label("Vault  (the whole run)", classes="modal-title")
            yield Input(placeholder="filter by key, value or source", id="vault-filter")
            yield DataTable(id="vault-table", cursor_type="row", zebra_stripes=False)
            yield Static("Newest last. S = step, B = branch.", classes="form-description")
            with Horizontal(classes="button-row"):
                yield Button("Open", id="open-vault-entry", variant="primary", compact=True)
                yield Button("Close", id="close-vault-log", compact=True)
            yield StatusBar("w/s move | e open | / filter | esc close")

    def on_mount(self) -> None:
        self.query_one("#vault-filter", Input).display = False
        table = self.query_one("#vault-table", DataTable)
        table.add_columns("Time", "Key", "Type", "Value", "Source")
        self._fill()
        table.focus()

    def _fill(self) -> None:
        table = self.query_one("#vault-table", DataTable)
        table.clear()
        if not self.writes:
            table.add_row("-", "Nothing written yet", "", "", "")
            return
        for write in self.writes:
            table.add_row(clock(write.get("seconds")), str(write.get("key")),
                          type_cell(write.get("type"), write.get("value")),
                          shorten(value_text(write.get("value"))), self.source_label(write))
        table.move_cursor(row=len(self.writes) - 1)

    def on_input_changed(self, event: Input.Changed) -> None:
        wanted = event.value.strip().casefold()
        self.writes = [w for w in self.all_writes
                       if not wanted or wanted in " ".join([str(w.get("key")), value_text(w.get("value")),
                                                            self.source_label(w)]).casefold()]
        self._fill()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self.query_one("#vault-table", DataTable).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-vault-entry":
            self.action_open_entry()
        elif event.button.id == "close-vault-log":
            self.action_close()

    def on_data_table_row_selected(self, _event: DataTable.RowSelected) -> None:
        self.action_open_entry()

    def action_filter(self) -> None:
        box = self.query_one("#vault-filter", Input)
        box.display = True
        box.focus()

    def action_close(self) -> None:
        box = self.query_one("#vault-filter", Input)
        if self.focused is box:
            box.value = ""
            box.display = False
            self.query_one("#vault-table", DataTable).focus()
            return
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        if isinstance(self.focused, Input):
            return
        self.query_one("#vault-table", DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        if isinstance(self.focused, Input):
            return
        self.query_one("#vault-table", DataTable).action_cursor_down()

    def action_open_entry(self) -> None:
        if isinstance(self.focused, Input) or not self.writes:
            return
        row = self.query_one("#vault-table", DataTable).cursor_row
        if 0 <= row < len(self.writes):
            write = self.writes[row]
            same_key = [w for w in self.all_writes if w.get("key") == write.get("key")]
            self.app.push_screen(VaultEntryScreen(same_key, same_key.index(write), self.source_label))


class VaultEntryScreen(ModalScreen):
    """One Vault write in full; A/D step through the same key's writes."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
        Binding("e", "close", "Close", priority=True),
        Binding("enter", "close", "Close", priority=True),
        Binding("a", "step(-1)", "Earlier", priority=True),
        Binding("d", "step(1)", "Later", priority=True),
        Binding("left", "step(-1)", "Earlier", priority=True),
        Binding("right", "step(1)", "Later", priority=True),
        Binding("w", "scroll(-1)", "Up", priority=True),
        Binding("s", "scroll(1)", "Down", priority=True),
    ]

    def __init__(self, writes: List[Dict[str, Any]], index: int, source_label: SourceLabel) -> None:
        super().__init__()
        self.writes = writes
        self.index = index
        self.source_label = source_label

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="fill-modal"):
            yield Label("Vault entry", classes="modal-title")
            with VerticalScroll(id="vault-entry-scroll"):
                yield Static(id="vault-entry")
            with Horizontal(classes="button-row"):
                yield Button("Close", id="close-vault-entry", variant="primary", compact=True)
            yield StatusBar("a/d earlier/later | w/s scroll | esc close")

    def on_mount(self) -> None:
        self._show()

    def _show(self) -> None:
        write = self.writes[self.index]
        text = Text()
        for label, value in (("Key", str(write.get("key"))), ("Type", None),
                             ("Written", f"{clock(write.get('seconds'))} by {self.source_label(write)}")):
            text.append(f"{label + ':':<9}", style="bold")
            if value is None:
                text.append_text(type_cell(write.get("type"), write.get("value")))
                text.append("\n")
            else:
                text.append(value + "\n")
        text.append("\nValue\n", style="bold")
        value = write.get("value")
        text.append(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False, default=str))
        text.append("\n")
        if len(self.writes) > 1:
            text.append(f"\nWrite {self.index + 1} of {len(self.writes)} for this key. a/d earlier or later.",
                        style="grey50")
        self.query_one("#vault-entry", Static).update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-vault-entry":
            self.action_close()

    def action_step(self, delta: int) -> None:
        new = self.index + int(delta)
        if 0 <= new < len(self.writes):
            self.index = new
            self._show()

    def action_scroll(self, delta: int) -> None:
        scroll = self.query_one("#vault-entry-scroll", VerticalScroll)
        scroll.scroll_relative(y=int(delta) * 3, animate=False)

    def action_close(self) -> None:
        self.dismiss(None)

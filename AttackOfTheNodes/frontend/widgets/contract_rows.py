"""Start inputs and Return End results as one-line rows (Step 4a-2).

Each row is a compact button: W/S reach it and E opens the row editor. The
buttons under the list add, remove and reorder the highlighted row. Owner,
2026-10-18: short plain wording ("next node", "from incoming value").
Values follow ``backend.contracts``: a default is stored as the text typed
(blank means none) and parsed by the row's type when a run starts.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from rich.text import Text
from rich.segment import Segment
from rich.style import Style
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widgets import Button, Checkbox, Label, Select, Static

from backend.contracts import ROW_TYPES, ContractError, parse_text
from frontend import colors
from frontend.keymap import CONTRACT_ROW_EDITOR, bindings_for
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.status_bar import StatusBar

INPUT, RESULT = "input", "result"
SEND_TO = (("Next node", "Downstream"), ("Vault", "Vault"), ("Both", "Both"))
FROM = (("Vault", "Vault key"), ("Incoming value", "Incoming payload"))


def default_text(value: Any) -> str:
    """A stored default as editable text: a file reference as its path, JSON
    for objects, lists, numbers and true/false. The editor keeps the stored
    value itself when this text comes back unchanged."""
    from backend.file_refs import is_file_reference, reference_path

    if value is None:
        return ""
    if is_file_reference(value):
        return str(reference_path(value) or "")
    return value if isinstance(value, str) else json.dumps(value)


def _shown_value(value: Any, row_type: str) -> str:
    """Text defaults in quotes; numbers, true/false and files as typed."""
    if value is None or value == "":
        return ""
    if row_type == "string":
        return f'"{value}"'
    return default_text(value)


def row_line(kind: str, row: Dict[str, Any]) -> str:
    """The one-line summary for a row, as the approved samples show it."""
    name = str(row.get("name") or "(no name)")
    kind_label = f"[{row.get('type') or 'string'}]"
    if kind == RESULT:
        need = "required" if row.get("required", True) else "optional"
        if row.get("source") == "Incoming payload":
            where = "from incoming value"
        else:
            where = f'from Vault "{row.get("vault_key") or name}"'
        return f"{name:<10} {kind_label:<8} {need}  {where}"
    to = row.get("to") or "Downstream"
    key = row.get("vault_key") or name
    route = {"Downstream": "next node", "Vault": f'Vault "{key}"',
             "Both": "next node, Vault"}.get(to, "next node")
    value = _shown_value(row.get("value"), str(row.get("type") or "string"))
    if not value:
        value = "required, no default" if row.get("required") else "no default"
    elif row.get("required"):
        value += ", required"
    return f"{name:<10} {kind_label:<8} → {route:<17} {value}"


class CompactRowButton(Button):
    """One solid role colour across selected text, cells and row padding."""

    def __init__(self, *args, selected_foreground_role=None, **kwargs):
        self.selected_foreground_role = selected_foreground_role
        super().__init__(*args, **kwargs)

    def render_lines(self, crop):
        lines = super().render_lines(crop)
        if not (self.has_focus or self.has_class("nav-highlight") or self.has_class("-active")):
            return lines
        # Paint after cell styles and padding are composed, so a coloured type
        # or embedded background cannot punch through the selection. Read the
        # live role on every draw so palette changes and overrides apply.
        foreground = (getattr(colors, self.selected_foreground_role)
                      if self.selected_foreground_role else self.visual_style.rich_style.color)
        style = Style(color=foreground,
                      bgcolor=colors.HIGHLIGHT, bold=True)
        return [Strip([Segment(cell.text, style, cell.control) for cell in line],
                      line.cell_length) for line in lines]


class ContractRowsField(Vertical):
    """An ordered list of contract rows with an editor for each."""

    class Changed(Message):
        """Rows were added, edited, removed or moved."""

    DEFAULT_CSS = """
    ContractRowsField { height: auto; }
    ContractRowsField .contract-row { width: 100%; height: 1; min-width: 10;
        border: none; text-align: left; content-align: left middle; }
    ContractRowsField .contract-row-buttons { height: auto; }
    """

    DEFAULT_CSS += """
    ContractRowsField Button.contract-row:focus,
    ContractRowsField Button.contract-row.nav-highlight,
    ContractRowsField Button.contract-row.-active {
        background: transparent;
        color: $foreground;
        text-style: bold;
        background-tint: transparent;
        tint: transparent;
    }
    """

    def __init__(self, kind: str, rows: List[Dict[str, Any]], **kwargs) -> None:
        super().__init__(**kwargs)
        self.kind = kind
        self.rows: List[Dict[str, Any]] = [dict(row) for row in rows]
        self._opened = [dict(row) for row in self.rows]
        self.selected = 0

    def compose(self) -> ComposeResult:
        yield Vertical(*self._row_buttons(), id=f"{self.id}-rows", classes="contract-row-list")
        add = "Add result" if self.kind == RESULT else "Add input"
        buttons = [Button(add, id=f"{self.id}-add", compact=True),
                   Button("Edit", id=f"{self.id}-edit", compact=True),
                   Button("Remove", id=f"{self.id}-remove", compact=True)]
        if self.kind == INPUT:
            buttons += [Button("Move up", id=f"{self.id}-up", compact=True),
                        Button("Move down", id=f"{self.id}-down", compact=True)]
        yield Horizontal(*buttons, classes="button-row contract-row-buttons")

    def _row_buttons(self) -> List[Static]:
        if not self.rows:
            empty = "No results yet." if self.kind == RESULT else "No inputs yet."
            return [Static(empty, classes="form-description")]
        return [CompactRowButton(Text(row_line(self.kind, row)), id=f"{self.id}-row-{index}",
                       classes="contract-row", compact=True)
                for index, row in enumerate(self.rows)]

    @property
    def value(self) -> List[Dict[str, Any]]:
        """The rows to save (private ``_`` keys dropped)."""
        return [{key: value for key, value in row.items() if not key.startswith("_")}
                for row in self.rows]

    @property
    def untouched_legacy(self) -> bool:
        """Still the old greeting, unedited: the Start keeps its old config."""
        return self.rows == self._opened and any(row.get("_legacy") for row in self.rows)

    async def _redraw(self, focus_index: Optional[int] = None) -> None:
        holder = self.query_one(f"#{self.id}-rows", Vertical)
        await holder.remove_children()
        await holder.mount_all(self._row_buttons())
        self.post_message(self.Changed())
        if focus_index is not None and self.rows:
            self.selected = max(0, min(focus_index, len(self.rows) - 1))
            self.app.set_focus(self.query_one(f"#{self.id}-row-{self.selected}", Button))

    def on_descendant_focus(self, event) -> None:
        widget_id = str(getattr(event.widget, "id", "") or "")
        prefix = f"{self.id}-row-"
        if widget_id.startswith(prefix):
            self.selected = int(widget_id[len(prefix):])

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id or "")
        if not button_id.startswith(f"{self.id}-"):
            return
        event.stop()
        action = button_id[len(self.id) + 1:]
        if action.startswith("row-"):
            self.selected = int(action[4:])
            self._open_editor(self.selected)
        elif action == "add":
            self._open_editor(None)
        elif action == "edit" and self.rows:
            self._open_editor(self.selected)
        elif action == "remove" and self.rows:
            del self.rows[self.selected]
            await self._redraw(self.selected)
        elif action in ("up", "down") and self.rows:
            index = self.selected
            other = index - 1 if action == "up" else index + 1
            if 0 <= other < len(self.rows):
                self.rows[index], self.rows[other] = self.rows[other], self.rows[index]
                await self._redraw(other)

    def _open_editor(self, index: Optional[int]) -> None:
        row = dict(self.rows[index]) if index is not None else {}
        others = [r.get("name", "") for i, r in enumerate(self.rows) if i != index]

        async def done(result: Optional[Dict[str, Any]]) -> None:
            if result is None:
                return
            if index is None:
                self.rows.append(result)
                await self._redraw(len(self.rows) - 1)
            else:
                self.rows[index] = result
                await self._redraw(index)

        self.app.push_screen(ContractRowEditor(self.kind, row, others), done)


class ContractRowEditor(CommandScreenMixin, ModalScreen):
    """Edit one input (or result) row: Confirm returns the row, Cancel None."""

    KEYMAP = CONTRACT_ROW_EDITOR
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, kind: str, row: Dict[str, Any], other_names: List[str]) -> None:
        super().__init__()
        self.kind = kind
        self.row = dict(row)
        self.other_names = {str(name).strip().casefold() for name in other_names}

    def compose(self) -> ComposeResult:
        row = self.row

        def field(label: str, widget, row_id: str) -> Horizontal:
            return Horizontal(Label(label, classes="form-label-inline"), widget,
                              classes="form-inline-row", id=row_id)

        title = "Edit result" if self.kind == RESULT else "Edit input"
        with Vertical(id="modal-card", classes="contract-row-modal"):
            yield Label(title if row else title.replace("Edit", "New"), classes="modal-title")
            yield field("Name:", CommandInput(value=str(row.get("name") or ""), id="row-name"), "row-name-row")
            row_type = row.get("type") if row.get("type") in ROW_TYPES else "string"
            yield field("Type:", Select([(t, t) for t in ROW_TYPES], value=row_type,
                                        allow_blank=False, id="row-type"), "row-type-row")
            if self.kind == INPUT:
                yield field("Default:", CommandInput(value=default_text(row.get("value")),
                                                     placeholder="optional (P: Stash)", id="row-value"),
                            "row-value-row")
                yield Checkbox("Required", value=bool(row.get("required", False)), id="row-required")
                yield field("Send to:", Select(list(SEND_TO), value=row.get("to") or "Downstream",
                                               allow_blank=False, id="row-to"), "row-to-row")
            else:
                yield Checkbox("Required", value=bool(row.get("required", True)), id="row-required")
                yield field("From:", Select(list(FROM), value=row.get("source") or "Vault key",
                                            allow_blank=False, id="row-to"), "row-to-row")
            yield field("Vault key:", CommandInput(value=str(row.get("vault_key") or ""),
                                                   placeholder="same as name", id="row-vault-key"),
                        "row-vault-key-row")
            yield field("Description:", CommandInput(value=str(row.get("description") or ""),
                                                     id="row-description"), "row-description-row")
            yield Static("", id="row-error", classes="field-error", markup=False)
            with Horizontal(classes="button-row"):
                yield Button("Confirm", id="confirm-row", variant="primary")
                yield Button("Cancel", id="cancel-row", variant="default")
            hint = "w/s move | e edit | ctrl+s confirm | esc cancel"
            if self.kind == INPUT:
                hint = "w/s move | e edit | p stash | ctrl+s confirm | esc cancel"
            yield StatusBar(hint)

    def on_mount(self) -> None:
        self.query_one("#row-error", Static).display = False
        self._sync_vault_key()
        self._focus_first()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "row-to":
            self._sync_vault_key()

    def _sync_vault_key(self) -> None:
        to = self.query_one("#row-to", Select).value
        self.query_one("#row-vault-key-row").display = to in ("Vault", "Both", "Vault key")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-row":
            self.action_submit()
        elif event.button.id == "cancel-row":
            self.action_cancel()

    def _text(self, widget_id: str) -> str:
        return str(self.query_one(f"#{widget_id}", CommandInput).value)

    def action_submit(self) -> None:
        for widget in self.query(CommandInput):
            if widget.editing:
                widget.end_edit()
        name = self._text("row-name").strip()
        row_type = str(self.query_one("#row-type", Select).value)
        problem = ""
        if not name:
            problem = "Give it a name"
        elif name.casefold() in self.other_names:
            problem = f'"{name}" is already used'
        result: Dict[str, Any] = {
            "id": self.row.get("id") or f"{'out' if self.kind == RESULT else 'in'}_{uuid.uuid4().hex[:8]}",
            "name": name,
            "type": row_type,
            "required": bool(self.query_one("#row-required", Checkbox).value),
            "vault_key": self._text("row-vault-key").strip(),
            "description": self._text("row-description"),
        }
        if self.kind == INPUT:
            value: Any = self._text("row-value")
            original = self.row.get("value")
            if value == default_text(original) and row_type == self.row.get("type"):
                value = original  # unchanged: keep the typed value as stored
            elif not problem and value.strip() and row_type != "file":
                try:
                    parse_text(row_type, value)
                except ContractError as error:
                    problem = f"Default {error}"
            result.update(value=value, to=str(self.query_one("#row-to", Select).value))
        else:
            result["source"] = str(self.query_one("#row-to", Select).value)
        if problem:
            error = self.query_one("#row-error", Static)
            error.update(problem)
            error.display = True
            return
        self.dismiss(result)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_stash_insert(self) -> None:
        """P: fill Default from the Stash (a file input takes files, others text)."""
        from frontend.widgets.stash_focus import stash_field
        if self.kind != INPUT:
            from frontend import notifications
            notifications.notify_info(self.app, "Stash text can't go into this field")
            return
        if stash_field(self, '#row-value') is None:
            return
        row_type = str(self.query_one("#row-type", Select).value)
        accepts = ["file"] if row_type == "file" else ["string"]
        self.app.action_stash("entries", insert_into={"label": "Default", "accepts": accepts},
                              callback=self._insert_stash_entry)

    def _insert_stash_entry(self, entry: Optional[Dict[str, Any]]) -> None:
        if not entry:
            return
        from frontend.widgets.stash_focus import stash_field
        if stash_field(self, '#row-value') is None:
            return
        from backend.file_refs import reference_path

        value = reference_path(entry["value"]) if entry["type"] == "file" else str(entry["value"])
        self.query_one("#row-value", CommandInput).value = value


def next_node_summary(rows: List[Dict[str, Any]]) -> str:
    """"Next node gets: a, b" for the rows Start sends downstream."""
    from backend.contracts import sends_downstream

    names = [str(row.get("name") or "") for row in rows if sends_downstream(row)]
    return "Next node gets: " + (", ".join(names) if names else "nothing")

"""The Subworkflow node's Inputs and Payloads tabs (Step 4c, owner samples
2026-10-19, revision 2).

Inputs lists the chosen subworkflow's inputs as a table (Input, Type,
Required?, Value comes from); E on a row opens ``SubworkflowInputEditor``.
Payloads lists what it sends back (Payload, Type, Goes to); E opens
``SubworkflowPayloadEditor``. ``SubworkflowPicker`` chooses the subworkflow:
a search field, a scrolling list, a count and a preview.

Config shape (``backend/nodes/flow/subworkflow_node.py``): ``workflow_id``;
``inputs`` rows ``{id, name, source, value, vault_key}`` where ``source`` is
Configured, Upstream payload or Vault (no row: the input's own default);
``results`` rows ``{id, name, to, vault_key}`` (blank key: the payload name).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from backend.contracts import ContractError, parse_text
from frontend import subworkflow_info as info
from frontend.io_contract import TYPE_COLOR
from frontend.keymap import CONTRACT_ROW_EDITOR, bindings_for
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.contract_rows import default_text, CompactRowButton
from frontend.widgets.status_bar import StatusBar

from frontend import colors  # noqa: E402
from frontend.colors import HIGHLIGHT, WARNING as YELLOW  # noqa: E402
NAME_WIDTH, TYPE_WIDTH, NEED_WIDTH = 10, 10, 11
FROM_CHOICES = (("Typed value", "Configured"), ("The incoming payload", "Upstream payload"),
                ("Vault key", "Vault"), ("Stash entry", "Stash"), ("Its default", "default"))
GOES_TO = (("Next node", "Downstream"), ("Vault", "Vault"), ("Both", "Both"))
#: The map's selection blue, one solid colour over the whole highlighted row.
ROW_HIGHLIGHT = HIGHLIGHT
ROW_CSS = """
    {name} {{ height: auto; }}
    {name} .sub-row {{ width: 100%; height: 1; min-width: 10; border: none;
        text-align: left; content-align: left middle; }}
    {name} .sub-row:focus {{ background: HIGHLIGHT; color: $text; text-style: bold; }}
""".replace("HIGHLIGHT", ROW_HIGHLIGHT)


def _cell(text: str, width: int) -> str:
    return text if len(text) >= width else text + " " * (width - len(text))


def _type_text(kind: str) -> Text:
    return Text(_cell(f"[{kind}]", TYPE_WIDTH), style=TYPE_COLOR)


def ask_warning(name: str, asks: List[str]) -> Text:
    """⚠ Greeter may stop and ask you something (at its node Ask name)."""
    text = Text()
    if asks:
        where = ", ".join(asks)
        node = "node" if len(asks) == 1 else "nodes"
        text.append(f"⚠ {name} may stop and ask you something (at its {node} {where}).", style=YELLOW)
    return text


class RowButton(Button):
    """A table row: coloured types normally, one plain colour when highlighted."""

    def __init__(self, line: Text, **kwargs) -> None:
        super().__init__(line, **kwargs)
        self.coloured = Content.from_rich_text(line)

    # The label reactive compares text only, so the swap is set directly.
    def on_focus(self) -> None:
        self.set_reactive(Button.label, Content(self.coloured.plain))
        self.refresh()

    def on_blur(self) -> None:
        self.set_reactive(Button.label, self.coloured)
        self.refresh()


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class _RowsBase(Vertical):
    """A header line and one compact button per row (W/S reach them, E opens)."""

    HEADER = ""

    class Changed(Message):
        """A row changed."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.child: Optional[Dict[str, Any]] = None

    def _lines(self) -> List[Text]:
        return []

    def _empty_text(self) -> str:
        return ""

    def compose(self) -> ComposeResult:
        yield Vertical(*self._widgets(), id=f"{self.id}-rows")

    def _widgets(self) -> List[Any]:
        lines = self._lines()
        if not lines:
            return [Static(self._empty_text(), classes="form-description", markup=False)]
        header = Static(Text("  " + self.HEADER, style="bold underline"), classes="sub-header")
        return [header] + [RowButton(line, id=f"{self.id}-row-{index}", classes="sub-row", compact=True)
                           for index, line in enumerate(lines)]

    async def redraw(self, focus_index: Optional[int] = None) -> None:
        holder = self.query_one(f"#{self.id}-rows", Vertical)
        await holder.remove_children()
        await holder.mount_all(self._widgets())
        self.post_message(self.Changed())
        if focus_index is not None:
            for button in self.query(f"#{self.id}-row-{focus_index}"):
                self.app.set_focus(button)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        prefix = f"{self.id}-row-"
        button_id = str(event.button.id or "")
        if button_id.startswith(prefix):
            event.stop()
            self.open_row(int(button_id[len(prefix):]))

    def open_row(self, index: int) -> None:
        raise NotImplementedError


class SubworkflowInputsField(_RowsBase):
    """The chosen subworkflow's inputs and where each value comes from."""

    class Changed(Message):
        """An input row changed."""

    DEFAULT_CSS = ROW_CSS.format(name="SubworkflowInputsField")
    HEADER = (_cell("Input", NAME_WIDTH) + _cell("Type", TYPE_WIDTH) + _cell("Required?", NEED_WIDTH)
              + "Value comes from")

    def __init__(self, child: Optional[Dict[str, Any]], mapping: List[Dict[str, Any]], **kwargs) -> None:
        super().__init__(**kwargs)
        self.child = child
        self.mapping: Dict[str, Dict[str, Any]] = info.input_mapping({"inputs": mapping})

    @property
    def rows(self) -> List[Dict[str, Any]]:
        return list((self.child or {}).get("inputs") or [])

    def _empty_text(self) -> str:
        if self.child is None:
            return "Choose a subworkflow first."
        return f"{self.child['name']} needs no inputs."

    def _lines(self) -> List[Text]:
        lines = []
        for row in self.rows:
            line = Text(_cell(row["name"], NAME_WIDTH), style=colors.PAYLOAD)
            line.append_text(_type_text(row["type"]))
            line.append(_cell("yes" if row["required"] else "no", NEED_WIDTH))
            line.append_text(info.parts_text(info.source_parts(row, self.mapping.get(row["name"]))))
            lines.append(line)
        return lines

    @property
    def value(self) -> List[Dict[str, Any]]:
        """Rows to save: one per input that doesn't use its own default."""
        names = [row["name"] for row in self.rows] if self.child is not None else list(self.mapping)
        return [self.mapping[name] for name in names if name in self.mapping]

    def open_row(self, index: int) -> None:
        row = self.rows[index]

        async def done(result: Optional[Dict[str, Any]]) -> None:
            if result is None:
                return
            if result.get("source") == "default":
                self.mapping.pop(row["name"], None)
            else:
                self.mapping[row["name"]] = result
            await self.redraw(index)

        self.app.push_screen(SubworkflowInputEditor(row, self.mapping.get(row["name"])), done)

    async def set_child(self, child: Optional[Dict[str, Any]]) -> None:
        """A new subworkflow: keep only the mappings it still has inputs for."""
        self.child = child
        names = {row["name"] for row in self.rows}
        self.mapping = {name: row for name, row in self.mapping.items() if name in names}
        await self.redraw()


class SubworkflowPayloadsField(_RowsBase):
    """What the subworkflow sends back, and where each payload goes."""

    class Changed(Message):
        """A payload row changed."""

    DEFAULT_CSS = ROW_CSS.format(name="SubworkflowPayloadsField")
    HEADER = _cell("Payload", NAME_WIDTH) + _cell("Type", TYPE_WIDTH) + "Goes to"

    def __init__(self, child: Optional[Dict[str, Any]], routes: List[Dict[str, Any]], **kwargs) -> None:
        super().__init__(**kwargs)
        self.child = child
        self.routes: Dict[str, Dict[str, Any]] = info.result_routes({"results": routes})

    @property
    def rows(self) -> List[Dict[str, Any]]:
        return list((self.child or {}).get("results") or [])

    def _empty_text(self) -> str:
        if self.child is None:
            return "Choose a subworkflow first."
        return f"{self.child['name']} sends nothing back."

    def _lines(self) -> List[Text]:
        lines = []
        for row in self.rows:
            line = Text(_cell(row["name"], NAME_WIDTH), style=colors.PAYLOAD)
            line.append_text(_type_text(row["type"]))
            line.append_text(info.parts_text(info.route_parts(row["name"], self.routes.get(row["name"]))))
            lines.append(line)
        return lines

    @property
    def value(self) -> List[Dict[str, Any]]:
        """Rows to save: one per payload with a route set."""
        names = [row["name"] for row in self.rows] if self.child is not None else list(self.routes)
        return [self.routes[name] for name in names if name in self.routes]

    def next_node_text(self) -> str:
        return info.next_node_text(self.rows, self.routes)

    def open_row(self, index: int) -> None:
        row = self.rows[index]

        async def done(result: Optional[Dict[str, Any]]) -> None:
            if result is not None:
                self.routes[row["name"]] = result
                await self.redraw(index)

        self.app.push_screen(SubworkflowPayloadEditor(row, self.routes.get(row["name"])), done)

    async def set_child(self, child: Optional[Dict[str, Any]]) -> None:
        self.child = child
        names = {row["name"] for row in self.rows}
        self.routes = {name: row for name, row in self.routes.items() if name in names}
        await self.redraw()


def _field(label: str, widget, row_id: str) -> Horizontal:
    return Horizontal(Label(label, classes="form-label-inline"), widget, classes="form-inline-row", id=row_id)


class _EditorBase(CommandScreenMixin, ModalScreen):
    KEYMAP = CONTRACT_ROW_EDITOR
    BINDINGS = bindings_for(KEYMAP)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-row":
            self.action_submit()
        elif event.button.id == "cancel-row":
            self.action_cancel()

    def _text(self, widget_id: str) -> str:
        return str(self.query_one(f"#{widget_id}", CommandInput).value)

    def _end_edits(self) -> None:
        for widget in self.query(CommandInput):
            if widget.editing:
                widget.end_edit()

    def _problem(self, text: str) -> None:
        error = self.query_one("#row-error", Static)
        error.update(text)
        error.display = True

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_stash_insert(self) -> None:
        """P has nothing to insert here."""
        from frontend import notifications
        notifications.notify_info(self.app, "Stash text can't go into this field")


class SubworkflowInputEditor(_EditorBase):
    """Where one input's value comes from: Confirm returns the row, Cancel None."""

    def __init__(self, row: Dict[str, Any], mapping: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.row = row
        self.mapping = dict(mapping or {})

    def _has_default(self) -> bool:
        return self.row.get("value") not in (None, "")

    def compose(self) -> ComposeResult:
        row, mapping = self.row, self.mapping
        need = "required" if row["required"] else "optional"
        choices = [choice for choice in FROM_CHOICES
                   if choice[1] != "default" or self._has_default() or not row["required"]]
        current = mapping.get("source") or "default"
        if current not in {value for _, value in choices}:
            current = choices[0][1]
        with Vertical(id="modal-card", classes="contract-row-modal"):
            title = Text(f"Input {row['name']}  ")
            title.append(f"[{row['type']}]", style=TYPE_COLOR)
            title.append(f"  ({need})")
            yield Label(title, classes="modal-title")
            yield _field("Value comes from:", Select(list(choices), value=current, allow_blank=False,
                                                     id="row-source"), "row-source-row")
            typed = default_text(mapping.get("value")) if current == "Configured" else ""
            yield _field("Value:", CommandInput(value=typed, id="row-value"), "row-value-row")
            yield _field("Vault key:", CommandInput(value=str(mapping.get("vault_key") or ""), id="row-vault-key"),
                         "row-vault-key-row")
            self.stash_entry = str(mapping.get("stash_entry") or "")
            yield _field("Stash entry:", CompactRowButton(self._stash_text(), id="row-stash", compact=True), "row-stash-row")
            yield Static(Text("P picks another entry.", style=colors.MUTED), id="row-stash-hint")
            if self._has_default():
                default = f'"{row["value"]}"' if row["type"] == "string" else default_text(row["value"])
                yield Static(f"Its default is {default}.", classes="form-description", markup=False)
            elif not row["required"]:
                yield Static("It has no default: left empty.", classes="form-description", markup=False)
            yield Static("", id="row-error", classes="field-error", markup=False)
            with Horizontal(classes="button-row"):
                yield Button("Confirm", id="confirm-row", variant="primary")
                yield Button("Cancel", id="cancel-row", variant="default")
            yield StatusBar("w/s move | e edit | p stash | ctrl+s confirm | esc cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "row-stash":
            event.stop()
            self.action_stash_insert()
        else:
            super().on_button_pressed(event)

    def _stash_text(self) -> Text:
        if not self.stash_entry:
            return Text("none yet: press P", style=colors.MUTED)
        return info.parts_text(info.stash_parts(self.stash_entry))

    def action_stash_insert(self) -> None:
        """P: pick the Stash entry this input comes from (by name)."""
        from frontend.widgets.stash_focus import stash_field
        if stash_field(self, '#row-stash') is None:
            return
        accepts = ["file"] if self.row["type"] == "file" else ["string"]
        self.app.action_stash("entries", insert_into={"label": "Stash entry", "accepts": accepts},
                              callback=self._pick_stash_entry)

    def _pick_stash_entry(self, entry: Optional[Dict[str, Any]]) -> None:
        if not entry:
            return
        from frontend.widgets.stash_focus import stash_field
        if stash_field(self, '#row-stash') is None:
            return
        self.stash_entry = str(entry["name"])
        self.query_one("#row-stash", Button).label = self._stash_text()
        self._sync()

    def on_mount(self) -> None:
        self.query_one("#row-error", Static).display = False
        self._sync()
        self._focus_first()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "row-source":
            self._sync()

    def _sync(self) -> None:
        source = self.query_one("#row-source", Select).value
        self.query_one("#row-value-row").display = source == "Configured"
        self.query_one("#row-vault-key-row").display = source == "Vault"
        self.query_one("#row-stash-row").display = source == "Stash"
        self.query_one("#row-stash-hint").display = source == "Stash"

    def action_submit(self) -> None:
        self._end_edits()
        source = str(self.query_one("#row-source", Select).value)
        if source == "default":
            self.dismiss({"source": "default"})
            return
        result: Dict[str, Any] = {"id": self.mapping.get("id") or _new_id("map_"), "name": self.row["name"],
                                  "source": source, "value": "", "vault_key": ""}
        if source == "Configured":
            value: Any = self._text("row-value")
            original = self.mapping.get("value")
            if self.mapping.get("source") == "Configured" and value == default_text(original):
                value = original  # unchanged: keep the value as stored
            elif value.strip() and self.row["type"] != "file":
                try:
                    parse_text(self.row["type"], value)
                except ContractError as error:
                    self._problem(f"Value {error}")
                    return
            result["value"] = value
        elif source == "Vault":
            key = self._text("row-vault-key").strip()
            if not key:
                self._problem("Give the Vault key")
                return
            result["vault_key"] = key
        elif source == "Stash":
            if not self.stash_entry:
                self._problem("Pick a Stash entry (P)")
                return
            result["stash_entry"] = self.stash_entry
        self.dismiss(result)


class SubworkflowPayloadEditor(_EditorBase):
    """Where one payload goes: Confirm returns the route, Cancel None."""

    def __init__(self, row: Dict[str, Any], route: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.row = row
        self.route = dict(route or {})

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="contract-row-modal"):
            title = Text(f"Payload {self.row['name']}  ")
            title.append(f"[{self.row['type']}]", style=TYPE_COLOR)
            yield Label(title, classes="modal-title")
            yield _field("Goes to:", Select(list(GOES_TO), value=self.route.get("to") or "Downstream",
                                            allow_blank=False, id="row-to"), "row-to-row")
            yield _field("Vault key:", CommandInput(value=str(self.route.get("vault_key") or ""),
                                                    placeholder=self.row["name"], id="row-vault-key"),
                         "row-vault-key-row")
            yield Static("", id="row-error", classes="field-error", markup=False)
            with Horizontal(classes="button-row"):
                yield Button("Confirm", id="confirm-row", variant="primary")
                yield Button("Cancel", id="cancel-row", variant="default")
            yield StatusBar("w/s move | e edit | ctrl+s confirm | esc cancel")

    def on_mount(self) -> None:
        self.query_one("#row-error", Static).display = False
        self._sync()
        self._focus_first()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "row-to":
            self._sync()

    def _sync(self) -> None:
        self.query_one("#row-vault-key-row").display = self.query_one("#row-to", Select).value in ("Vault", "Both")

    def action_submit(self) -> None:
        self._end_edits()
        to = str(self.query_one("#row-to", Select).value)
        key = self._text("row-vault-key").strip() if to in ("Vault", "Both") else ""
        self.dismiss({"id": self.route.get("id") or _new_id("res_"), "name": self.row["name"],
                      "to": to, "vault_key": key})


class SubworkflowPicker(_EditorBase):
    """Choose a subworkflow: search, a scrolling list, a count and a preview.
    Dismisses with the chosen workflow id, or None."""

    DEFAULT_CSS = """
    SubworkflowPicker #pick-list { height: 1fr; min-height: 3; border: round $foreground 20%; }
    SubworkflowPicker .pick-row { width: 100%; height: 1; min-width: 10; border: none;
        text-align: left; content-align: left middle; }
    SubworkflowPicker .pick-row:focus { background: HIGHLIGHT; color: $text; text-style: bold; }
    SubworkflowPicker #pick-preview { height: auto; }
    """.replace("HIGHLIGHT", ROW_HIGHLIGHT)

    def __init__(self, entries: List[Dict[str, Any]], current: str = "") -> None:
        super().__init__()
        self.entries = list(entries)
        self.current = current
        self.shown: List[Dict[str, Any]] = list(entries)
        self.highlighted = current

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="fill-modal"):
            yield Label("Choose a subworkflow", classes="modal-title")
            yield _field("Search:", CommandInput(value="", placeholder="type to filter", id="pick-search"),
                         "pick-search-row")
            yield VerticalScroll(id="pick-list")
            yield Static("", id="pick-count", classes="form-description", markup=False)
            yield Static("", id="pick-preview")
            yield Static("", id="row-error", classes="field-error", markup=False)
            with Horizontal(classes="button-row"):
                yield Button("Choose", id="confirm-row", variant="primary")
                yield Button("Cancel", id="cancel-row", variant="default")
            yield StatusBar("w/s move | e search or choose | ctrl+s choose | esc cancel")

    async def on_mount(self) -> None:
        self.query_one("#row-error", Static).display = False
        await self._fill()
        buttons = list(self.query(".pick-row"))
        chosen = next((b for b in buttons if getattr(b, "workflow_id", "") == self.current), None)
        self.app.set_focus(chosen or (buttons[0] if buttons else self.query_one("#pick-search")))

    async def _fill(self) -> None:
        holder = self.query_one("#pick-list", VerticalScroll)
        await holder.remove_children()
        buttons = []
        for entry in self.shown:
            button = Button(Text(str(entry["name"])), classes="pick-row", compact=True)
            button.workflow_id = entry["id"]
            buttons.append(button)
        if buttons:
            await holder.mount_all(buttons)
        else:
            await holder.mount(Static("No subworkflows match." if self.entries else
                                      "No subworkflows yet. Copy a workflow to Subworkflows in the File window.",
                                      classes="form-description", markup=False))
        total = len(self.entries)
        count = f"{total} subworkflow{'s' if total != 1 else ''}"
        if len(self.shown) != total:
            count = f"{len(self.shown)} of {count}"
        self.query_one("#pick-count", Static).update(count)
        self._preview(self.highlighted if any(e["id"] == self.highlighted for e in self.shown) else
                      (self.shown[0]["id"] if self.shown else ""))

    def _preview(self, workflow_id: str) -> None:
        self.highlighted = workflow_id
        child = info.describe(workflow_id) if workflow_id else None
        text = Text()
        if child is not None:
            text.append(f"{child['name']}\n", style="bold")
            for label, rows in (("Inputs:   ", child["inputs"]), ("Payloads: ", child["results"])):
                text.append(f"  {label}")
                if not rows:
                    text.append("none")
                for index, row in enumerate(rows):
                    text.append(", " if index else "")
                    text.append(f"{row['name']} ")
                    text.append(f"[{row['type']}]", style=TYPE_COLOR)
                    if label.startswith("Inputs") and row["required"]:
                        text.append(" required")
                text.append("\n")
            if child["asks"]:
                text.append("  ⚠ may stop and ask you something", style=YELLOW)
        self.query_one("#pick-preview", Static).update(text)

    def on_descendant_focus(self, event) -> None:
        workflow_id = getattr(event.widget, "workflow_id", None)
        if workflow_id:
            self._preview(workflow_id)

    async def on_input_changed(self, event) -> None:
        if getattr(event.input, "id", "") != "pick-search":
            return
        wanted = str(event.value).strip().casefold()
        self.shown = [e for e in self.entries if wanted in str(e["name"]).casefold()]
        await self._fill()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        workflow_id = getattr(event.button, "workflow_id", None)
        if workflow_id:
            event.stop()
            self.dismiss(workflow_id)
            return
        super().on_button_pressed(event)

    def action_submit(self) -> None:
        self._end_edits()
        if not self.highlighted:
            self._problem("Pick a subworkflow")
            return
        self.dismiss(self.highlighted)

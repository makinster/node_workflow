"""The Stash screen (Stash S2): paste or drop paths and text, manage entries.

Two tabs: **1 Paste / drop** and **2 Entries**. The editor opens it on tab 1
(`p`); the node-config field insert (S3) opens it on tab 2 through
``initial_tab="entries"``. Pastes are collected only here; every other text
field keeps receiving pastes as text. All rules live in
``backend/stash_manager.py`` and ``backend/paste_parser.py``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.markup import escape
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static, TabbedContent, TabPane

from backend.file_refs import reference_path
from backend.stash_manager import (
    StashDuplicate, StashError, StashManager, duplicates_message, preview, type_word,
)
from frontend import notifications
from frontend.io_contract import type_label
from frontend.screens.confirm import ConfirmScreen
from frontend.screens.workflow_library import NamePromptScreen
from frontend.widgets.command_input import CommandInput, CommandTextArea
from frontend.widgets.list_navigation import focus_list, move_list_highlight
from frontend.widgets.status_bar import StatusBar

ADD_TAB = "stash-tab-add"
ENTRIES_TAB = "stash-tab-entries"
_TABS = {"add": ADD_TAB, "entries": ENTRIES_TAB}
_FILTERS = [None, "file", "string"]  # T cycles: all → files → text
_INSERT_HELP = "E/Enter insert | W/S move | / search | R rename | Esc close"
_HELP = {  # short enough for a 100-column terminal; tab labels show 1/2
    ADD_TAB: "E type, Enter add | T keep as text | R rename | Esc close",
    ENTRIES_TAB: "W/S move | / search | T filter | R rename | X delete | Esc close",
}


def entry_row(entry: Dict[str, Any], prefix: str = "") -> str:
    """``name  [type]  value`` as Rich markup (the bracketed teal type)."""
    name = escape(entry["name"])
    return f"{prefix}{name:<20} {type_label(type_word(entry['type']))}  {escape(preview(entry))}"


def _full_text(entry: Dict[str, Any]) -> str:
    """The whole searchable value: a file's path, or all of the text."""
    return reference_path(entry["value"]) if entry["type"] == "file" else str(entry["value"])


class _PasteBox(CommandTextArea):
    """The paste target. A paste or drop is added at once; Enter adds what
    was typed (so a multi-line drop never needs Enter)."""

    class Submitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    async def _on_paste(self, event: events.Paste) -> None:
        event.stop()
        event.prevent_default()
        self.post_message(self.Submitted(event.text))

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.Submitted(self.text))
            return
        await super()._on_key(event)


class _SearchInput(CommandInput):
    """Live search box: Enter or Esc hands focus back to the entry list, so
    the screen's letter shortcuts work again."""

    class Done(Message):
        pass

    async def _on_key(self, event: events.Key) -> None:
        if self.editing and event.key in ("enter", "escape"):
            self.end_edit()
            event.stop()
            event.prevent_default()
            self.post_message(self.Done())
            return
        await super()._on_key(event)


class StashScreen(ModalScreen):
    """Manage the Stash, or pick an entry to insert into a field.

    Manage mode dismisses with None. Insert mode (``insert_into`` set, from
    node config's P) shows only entries the field accepts and dismisses with
    the chosen entry.
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
        # Priority: a focused text box that isn't editing would swallow the
        # digit. check_action turns them off while typing.
        Binding("1", "show_tab('add')", "Paste / drop", priority=True),
        Binding("2", "show_tab('entries')", "Entries", priority=True),
        ("w", "cursor_up", "Up"),
        ("s", "cursor_down", "Down"),
        ("slash", "search", "Search"),
        ("t", "toggle", "Filter / keep as text"),
        ("r", "rename", "Rename"),
        ("x", "delete", "Delete"),
        ("e", "edit", "Edit"),
    ]

    def __init__(
        self,
        stash: Optional[StashManager] = None,
        initial_tab: str = "add",
        insert_into: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self.stash = stash or StashManager()
        self.initial_tab = _TABS.get(initial_tab, ADD_TAB)
        # {"label": field label, "accepts": {"file"} or {"string"}} in insert mode.
        self.insert_into = insert_into
        self.allowed = sorted(insert_into["accepts"]) if insert_into else None
        self.added: List[Dict[str, Any]] = []
        self.rejected_paste: Optional[str] = None
        self.type_filter: Optional[str] = (
            self.allowed[0] if self.allowed and len(self.allowed) == 1 else None)
        self.shown: List[Dict[str, Any]] = []
        self._rejected: List[Any] = []

    # -- layout ----------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="fill-modal stash-modal"):
            title = "Stash"
            if self.insert_into:
                title = f"Stash · insert into {escape(self.insert_into['label'])}"
            yield Label(title, classes="modal-title")
            with TabbedContent(id="stash-tabs", initial=self.initial_tab, classes="node-config-tabs"):
                with TabPane("1 Paste / drop", id=ADD_TAB):
                    yield Label("Paste or drop files here, or type text and press Enter",
                                classes="form-label")
                    yield _PasteBox(id="stash-paste", classes="stash-paste")
                    with Horizontal(classes="button-row"):
                        yield Button("Add", id="stash-add", variant="primary")
                        yield Button("Keep as text", id="stash-keep-text", variant="default")
                        yield Button("Rename", id="stash-rename-added", variant="default")
                    yield Label("Just added", id="stash-added-label", classes="form-label nav-section")
                    yield ListView(id="stash-added", classes="stash-list")
                with TabPane("2 Entries", id=ENTRIES_TAB):
                    yield _SearchInput(id="stash-search", placeholder="/ search names and values")
                    yield Static("", id="stash-count", classes="form-label")
                    yield ListView(id="stash-entries", classes="stash-list")
                    with Horizontal(classes="button-row"):
                        if self.insert_into:
                            yield Button("Insert", id="stash-insert", variant="primary")
                        yield Button("Rename", id="stash-rename", variant="default")
                        yield Button("Delete", id="stash-delete", variant="warning")
                        yield Button("Show: all", id="stash-filter", variant="default")
            with Horizontal(classes="button-row"):
                yield Button("Close", id="stash-close", variant="default")
            yield StatusBar(self._help_for(self.initial_tab))

    def on_mount(self) -> None:
        self.query_one("#stash-keep-text", Button).display = False
        self._refresh_added()
        self._refresh_entries()
        self._focus_tab(self.initial_tab)

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        # While a text box is being typed in, letters and digits are text.
        if getattr(self.app.focused, "editing", False):
            return False
        return True

    # -- tabs ------------------------------------------------------------------

    def _active_tab(self) -> str:
        return self.query_one("#stash-tabs", TabbedContent).active

    def action_show_tab(self, tab: str) -> None:
        tab_id = _TABS[tab]
        self.query_one("#stash-tabs", TabbedContent).active = tab_id
        self._focus_tab(tab_id)

    def _help_for(self, tab_id: str) -> str:
        return _INSERT_HELP if self.insert_into and tab_id == ENTRIES_TAB else _HELP[tab_id]

    def on_tabbed_content_tab_activated(self, _event: TabbedContent.TabActivated) -> None:
        self.query_one(StatusBar).set_bindings_text(self._help_for(self._active_tab()))

    def _focus_tab(self, tab_id: str) -> None:
        if tab_id == ADD_TAB:
            self.query_one("#stash-paste", _PasteBox).begin_edit()
        else:
            entries = self.query_one("#stash-entries", ListView)
            focus_list(self.app, entries, len(self.shown))

    # -- paste / add -----------------------------------------------------------

    @on(_PasteBox.Submitted)
    def _paste_submitted(self, event: _PasteBox.Submitted) -> None:
        self._ingest(event.text)

    def on_paste(self, event: events.Paste) -> None:
        # A drop while focus is elsewhere on this screen still lands here.
        if self._active_tab() == ADD_TAB:
            event.stop()
            self._ingest(event.text)

    def _ingest(self, text: str) -> None:
        box = self.query_one("#stash-paste", _PasteBox)
        if not text.strip():
            return
        try:
            entries, result = self.stash.add_paste(text)
        except StashError as exc:
            notifications.notify_error(self.app, str(exc))
            return
        self.added = entries + self.added
        self._rejected = list(result.rejected) if result.rejected else []
        self.rejected_paste = text if result.rejected and not entries else None
        box.text = ""
        if box.editing:
            box.end_edit()
        # Keys now act on what was just added (T, R, W/S); E types again.
        listing = self.query_one("#stash-added", ListView)
        if result.duplicates:
            # The same reference is never stashed twice; say so briefly.
            notifications.notify_info(self.app, duplicates_message(result.duplicates))
        warnings = [w for e in entries for w in self.stash.warnings_for(e)]
        for warning in warnings:
            notifications.notify_info(self.app, warning)
        self.query_one("#stash-keep-text", Button).display = self.rejected_paste is not None
        self._refresh_added()
        self._refresh_entries()
        focus_list(self.app, listing, len(self._rejected) + len(self.added))

    def action_keep_as_text(self) -> None:
        if self.rejected_paste is None:
            return
        try:
            entry = self.stash.add_text(self.rejected_paste)
        except StashDuplicate as duplicate:
            notifications.notify_info(self.app, duplicates_message([duplicate.entry]))
            entry = None
        if entry is not None:
            self.added.insert(0, entry)
        self.rejected_paste = None
        self._rejected = []
        self.query_one("#stash-keep-text", Button).display = False
        self._refresh_added()
        self._refresh_entries()

    # -- lists -----------------------------------------------------------------

    def _refresh_added(self) -> None:
        listing = self.query_one("#stash-added", ListView)
        listing.clear()
        rejected = self._rejected
        for item in rejected:
            listing.append(ListItem(Static(
                f"! not stored  {escape(item.piece)}: {escape(item.reason)}", classes="stash-row")))
        for entry in self.added:
            listing.append(ListItem(Static(entry_row(entry, "+ "), classes="stash-row")))
        self.query_one("#stash-added-label", Label).display = bool(self.added or rejected)

    def _refresh_entries(self, keep_id: Optional[str] = None) -> None:
        query = self.query_one("#stash-search", CommandInput).value.strip().casefold()
        entries = self.stash.list_entries(self.type_filter)
        if self.allowed:
            entries = [e for e in entries if e["type"] in self.allowed]
        if query:
            entries = [e for e in entries
                       if query in e["name"].casefold() or query in _full_text(e).casefold()]
        self.shown = entries
        listing = self.query_one("#stash-entries", ListView)
        old = listing.index
        listing.clear()
        for entry in entries:
            listing.append(ListItem(Static(entry_row(entry), classes="stash-row")))
        if not entries:
            listing.append(ListItem(Static(
                "The Stash is empty: paste or drop on tab 1" if not self.stash.list_entries()
                else "Nothing matches", classes="stash-row")))
        total = len([e for e in self.stash.list_entries()
                     if not self.allowed or e["type"] in self.allowed])
        label = {None: "All", "file": "Files", "string": "Text"}[self.type_filter]
        self.query_one("#stash-count", Static).update(f"{label} · {len(entries)} of {total}")
        self.query_one("#stash-filter", Button).label = f"Show: {label.lower()}"
        if entries:
            ids = [e["id"] for e in entries]
            listing.index = ids.index(keep_id) if keep_id in ids else min(old or 0, len(entries) - 1)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "stash-search":
            self._refresh_entries()

    @on(_SearchInput.Done)
    def _search_done(self, _event: _SearchInput.Done) -> None:
        focus_list(self.app, self.query_one("#stash-entries", ListView), len(self.shown))

    def _highlighted(self) -> Optional[Dict[str, Any]]:
        if self._active_tab() == ADD_TAB:
            # The highlighted just-added entry (rejected lines come first).
            listing = self.query_one("#stash-added", ListView)
            offset = len(self._rejected)
            index = (listing.index or 0) - offset
            return self.added[index] if 0 <= index < len(self.added) else (self.added[0] if self.added else None)
        listing = self.query_one("#stash-entries", ListView)
        index = listing.index
        return self.shown[index] if index is not None and 0 <= index < len(self.shown) else None

    # -- actions ---------------------------------------------------------------

    def action_cursor_up(self) -> None:
        self._move(-1)

    def action_cursor_down(self) -> None:
        self._move(1)

    def _move(self, delta: int) -> None:
        if self._active_tab() == ENTRIES_TAB:
            move_list_highlight(self.app, self.query_one("#stash-entries", ListView), len(self.shown), delta)
        else:
            count = len(self.added) + len(self._rejected)
            move_list_highlight(self.app, self.query_one("#stash-added", ListView), count, delta)

    def action_search(self) -> None:
        if self._active_tab() != ENTRIES_TAB:
            self.action_show_tab("entries")
        self.query_one("#stash-search", CommandInput).begin_edit()

    def action_toggle(self) -> None:
        if self._active_tab() == ADD_TAB:
            self.action_keep_as_text()
            return
        filters = _FILTERS
        if self.allowed:
            # Insert mode only ever shows types the field accepts.
            filters = [None, *self.allowed] if len(self.allowed) > 1 else list(self.allowed)
        self.type_filter = filters[(filters.index(self.type_filter) + 1) % len(filters)] \
            if self.type_filter in filters else filters[0]
        self._refresh_entries()

    def action_rename(self) -> None:
        entry = self._highlighted()
        if entry is None:
            return

        def done(name: Optional[str]) -> None:
            if not name:
                return
            renamed = self.stash.rename(entry["id"], name)
            self.added = [renamed if e["id"] == renamed["id"] else e for e in self.added]
            self._refresh_added()
            self._refresh_entries(keep_id=renamed["id"])

        self.app.push_screen(
            NamePromptScreen("Rename Stash entry", entry["name"],
                             lambda name: self.stash.name_problem(name, exclude_id=entry["id"])),
            done,
        )

    def action_delete(self) -> None:
        if self._active_tab() != ENTRIES_TAB:
            return
        entry = self._highlighted()
        if entry is None:
            return

        def done(confirmed: bool) -> None:
            if confirmed:
                self.stash.remove(entry["id"])
                self.added = [e for e in self.added if e["id"] != entry["id"]]
                self._refresh_added()
                self._refresh_entries()

        self.app.push_screen(
            ConfirmScreen(f"Delete '{entry['name']}' from the Stash?", yes_label="Delete", no_label="Cancel"),
            done,
        )

    def action_edit(self) -> None:
        if self._active_tab() == ADD_TAB:
            self.query_one("#stash-paste", _PasteBox).begin_edit()
        elif self.insert_into:
            self.action_insert()
        else:
            self.action_rename()

    def action_close(self) -> None:
        self.dismiss(None)

    def action_insert(self) -> None:
        """Insert mode: dismiss with the highlighted entry if the field takes it."""
        entry = self._highlighted()
        if entry is None or not self.insert_into:
            return
        if entry["type"] not in self.insert_into["accepts"]:
            wanted = " or ".join(f"[{type_word(t)}]" for t in sorted(self.insert_into["accepts"]))
            notifications.notify_info(
                self.app, f"'{entry['name']}' is [{type_word(entry['type'])}]; this field takes {wanted}")
            return
        self.dismiss(entry)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Enter/E on an entry: insert it (insert mode) or rename it (manage mode).
        if event.list_view.id == "stash-entries":
            if self.insert_into:
                self.action_insert()
            else:
                self.action_rename()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        handlers = {
            "stash-add": lambda: self._ingest(self.query_one("#stash-paste", _PasteBox).text),
            "stash-keep-text": self.action_keep_as_text,
            "stash-rename-added": self.action_rename,
            "stash-rename": self.action_rename,
            "stash-delete": self.action_delete,
            "stash-filter": self.action_toggle,
            "stash-close": self.action_close,
            "stash-insert": self.action_insert,
        }
        handler = handlers.get(event.button.id or "")
        if handler is not None:
            handler()

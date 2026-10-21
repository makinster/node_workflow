"""Stash S2: the Stash screen (tabs, paste/drop, entries, buttons).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_stash_screen.py -v
"""

import asyncio

import pytest
from textual import events
from textual.widgets import Button, ListView, Static, TabbedContent

from backend import persistence
from backend.stash_manager import StashManager
from tests.test_debug_nodes import _make_services


@pytest.fixture
def stash(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "STASH_DIR", tmp_path / "stash")
    return StashManager()


@pytest.fixture
def files(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    plain, spaced = folder / "march.csv", folder / "q1 notes.txt"
    plain.write_text("a")
    spaced.write_text("b")
    return plain, spaced


def _app(stash):
    from frontend.app import AttackOfTheNodesApp

    master, workflow_map, memory_bank, bus = _make_services()
    workflow_map.create_new("Stash test")
    workflow_map.add_node("start_node")
    return AttackOfTheNodesApp(bus, workflow_map._factory, workflow_map, memory_bank, master,
                               stash_manager=stash)


def _rows(screen, list_id):
    return [str(item.query_one(Static).render()) for item in screen.query_one(f"#{list_id}", ListView).children]


def _run(coro_factory):
    asyncio.run(coro_factory())


def test_p_opens_on_paste_tab_and_field_insert_opens_on_entries(stash):
    async def go():
        from frontend.screens.stash import ADD_TAB, ENTRIES_TAB, StashScreen

        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            await pilot.press("p")
            await pilot.pause(0.05)
            assert isinstance(app.screen, StashScreen)
            assert app.screen.query_one("#stash-tabs", TabbedContent).active == ADD_TAB
            assert app.screen.query_one("#stash-paste").editing  # typing starts at once
            await pilot.click("#stash-close")
            await pilot.pause(0.05)
            assert not isinstance(app.screen, StashScreen)
            app.action_stash(initial_tab="entries")  # what S3's field hotkey will call
            await pilot.pause(0.05)
            assert app.screen.query_one("#stash-tabs", TabbedContent).active == ENTRIES_TAB
    _run(go)


def test_a_drop_adds_files_and_reports_what_was_not_stored(stash, files):
    async def go():
        plain, spaced = files
        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash()
            await pilot.pause(0.05)
            screen = app.screen
            screen.query_one("#stash-paste").post_message(
                events.Paste(f"'{spaced}' {plain} /nowhere/x.txt"))
            await pilot.pause(0.05)
            rows = _rows(screen, "stash-added")
            assert rows[0] == "! not stored  /nowhere/x.txt: not found on this machine"
            assert rows[1].startswith("+ q1 notes") and "[file]" in rows[1]
            # Long paths keep their end, so the file name stays visible.
            assert rows[2].startswith("+ march") and rows[2].endswith("/data/march.csv")
            assert [e["name"] for e in stash.list_entries()] == ["march", "q1 notes"]
            assert not screen.query_one("#stash-keep-text", Button).display  # files were added
            assert not screen.query_one("#stash-paste").editing  # keys act on the list now
    _run(go)


def test_a_refused_paste_can_be_kept_as_text(stash):
    async def go():
        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash()
            await pilot.pause(0.05)
            screen = app.screen
            screen.query_one("#stash-paste").post_message(events.Paste("/nowhere/x.txt"))
            await pilot.pause(0.05)
            assert screen.query_one("#stash-keep-text", Button).display
            assert stash.list_entries() == []
            await pilot.press("t")
            await pilot.pause(0.05)
            [entry] = stash.list_entries()
            assert entry["type"] == "string" and entry["value"] == "/nowhere/x.txt"
            assert "[string]" in _rows(screen, "stash-added")[0]
    _run(go)


def test_typing_is_text_not_shortcuts_and_enter_adds(stash):
    async def go():
        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash()
            await pilot.pause(0.05)
            await pilot.press(*"tone: 1 r x", "enter")
            await pilot.pause(0.05)
            [entry] = stash.list_entries()
            assert entry["value"] == "tone: 1 r x" and entry["type"] == "string"
            assert app.screen.query_one("#stash-tabs", TabbedContent).active == "stash-tab-add"
    _run(go)


def test_entries_filter_search_rename_delete(stash, files):
    async def go():
        from frontend.screens.workflow_library import NamePromptScreen
        from frontend.screens.confirm import ConfirmScreen
        from frontend.widgets.command_input import CommandInput

        plain, _ = files
        stash.add_file(str(plain))
        stash.add_text("Plain British English", name="tone")
        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash(initial_tab="entries")
            await pilot.pause(0.05)
            screen = app.screen
            assert screen.query_one("#stash-count", Static).render().plain == "All · 2 of 2"
            await pilot.press("t")  # files only
            await pilot.pause(0.05)
            assert [r.split()[0] for r in _rows(screen, "stash-entries")] == ["march"]
            await pilot.press("t", "t")  # text, then all again
            await pilot.pause(0.05)
            await pilot.press("slash", *"brit")
            await pilot.pause(0.05)
            assert [r.split()[0] for r in _rows(screen, "stash-entries")] == ["tone"]
            await pilot.press("enter")  # leave search, back to the list
            await pilot.press("r")
            await pilot.pause(0.05)
            assert isinstance(app.screen, NamePromptScreen)
            app.screen.query_one("#name-input", CommandInput).value = "MARCH"
            await pilot.press("enter")  # taken (ignoring case): the prompt stays
            await pilot.pause(0.05)
            assert isinstance(app.screen, NamePromptScreen)
            app.screen.query_one("#name-input", CommandInput).value = "voice"
            await pilot.press("enter")
            await pilot.pause(0.05)
            assert stash.get("voice")["value"] == "Plain British English"
            await pilot.press("x")
            await pilot.pause(0.05)
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.press("y")
            await pilot.pause(0.05)
            assert stash.get("voice") is None and stash.get("march") is not None
    _run(go)


def test_every_action_has_a_button(stash, files):
    async def go():
        plain, _ = files
        stash.add_file(str(plain))
        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash(initial_tab="entries")
            await pilot.pause(0.05)
            ids = {b.id for b in app.screen.query(Button)}
            assert {"stash-add", "stash-keep-text", "stash-rename-added", "stash-rename",
                    "stash-delete", "stash-filter", "stash-close"} <= ids
            await pilot.click("#stash-filter")
            await pilot.pause(0.05)
            assert str(app.screen.query_one("#stash-filter", Button).label) == "Show: files"
            await pilot.click("#stash-filter")
            await pilot.pause(0.05)
            # The type is named "string" everywhere (owner, 2026-10-20).
            assert str(app.screen.query_one("#stash-filter", Button).label) == "Show: strings"
    _run(go)


# -- review of #71 ------------------------------------------------------------------

def test_number_keys_switch_tabs_after_leaving_the_paste_box(stash):
    async def go():
        from frontend.screens.stash import ADD_TAB, ENTRIES_TAB

        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash()
            await pilot.pause(0.05)
            tabs = app.screen.query_one("#stash-tabs", TabbedContent)
            await pilot.press("escape")  # leave typing; focus stays on the box
            await pilot.press("2")
            await pilot.pause(0.05)
            assert tabs.active == ENTRIES_TAB
            await pilot.press("1")
            await pilot.pause(0.05)
            assert tabs.active == ADD_TAB
            await pilot.press(*"12")  # typing again: digits are text
            await pilot.pause(0.05)
            assert tabs.active == ADD_TAB and app.screen.query_one("#stash-paste").text == "12"
    _run(go)


def test_e_after_adding_types_again(stash):
    async def go():
        from frontend.screens.workflow_library import NamePromptScreen

        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash()
            await pilot.pause(0.05)
            await pilot.press(*"first", "enter")
            await pilot.pause(0.05)
            await pilot.press("e")
            await pilot.pause(0.05)
            assert not isinstance(app.screen, NamePromptScreen)
            assert app.screen.query_one("#stash-paste").editing
    _run(go)


def test_search_matches_the_whole_value(stash):
    async def go():
        stash.add_text("x" * 12_000 + " needle", name="long")
        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash(initial_tab="entries")
            await pilot.pause(0.05)
            await pilot.press("slash", *"needle")
            await pilot.pause(0.05)
            assert [r.split()[0] for r in _rows(app.screen, "stash-entries")] == ["long"]
    _run(go)


def test_a_duplicate_paste_shows_a_toast_and_adds_nothing(stash, files, monkeypatch):
    async def go():
        from frontend import notifications

        plain, _ = files
        stash.add_file(str(plain))
        shown = []
        monkeypatch.setattr(notifications, "notify_info", lambda app, message: shown.append(message))
        app = _app(stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash()
            await pilot.pause(0.05)
            app.screen.query_one("#stash-paste").post_message(events.Paste(str(plain)))
            await pilot.pause(0.05)
            assert shown == ["Duplicate found: 'march'"]
            assert len(stash.list_entries()) == 1
            assert _rows(app.screen, "stash-added") == []
    _run(go)

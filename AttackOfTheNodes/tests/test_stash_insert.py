"""Stash S3: insert a Stash entry into a node config field.

P (or the Insert from Stash button) on a highlighted field opens the Stash on
Entries in insert mode, showing only entries the field accepts. A focused file field takes [file]; a focused text field takes [string].
Source selectors refuse Stash insertion rather than filling another field.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_stash_insert.py -v
"""

import asyncio

import pytest
from textual.widgets import Button, Input, ListView, Static

from backend import persistence
from backend.field_types import stash_insert_target
from backend.node_factory import NodeFactory
from backend.stash_manager import StashManager
from tests.test_debug_nodes import _make_services

SCHEMAS = {m["type"]: m["config_schema"] for m in NodeFactory().get_node_types_metadata()}


@pytest.fixture
def stash(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "STASH_DIR", tmp_path / "stash")
    return StashManager()


@pytest.fixture
def report(tmp_path):
    path = tmp_path / "march.csv"
    path.write_text("a,b\n")
    return path


# -- the target rule ------------------------------------------------------------------

def test_a_file_field_takes_files():
    target = stash_insert_target(SCHEMAS["file_reader_node"], "file_path")
    assert target == {"field": "file_path", "label": "File path", "accepts": {"file"},
                      "set_source": None, "source_label": None}


def test_source_rows_never_fill_another_field():
    for kind, field in [("file_reader_node", "input_source"),
                        ("file_output_node", "file_path_source"),
                        ("file_output_node", "content_source")]:
        assert stash_insert_target(SCHEMAS[kind], field) is None


def test_text_fields_take_text_and_others_take_nothing():
    assert stash_insert_target(SCHEMAS["file_output_node"], "content")["accepts"] == {"string"}
    for field in ("write_mode", "binary_content", "open_after_write"):
        assert stash_insert_target(SCHEMAS["file_output_node"], field) is None, field


# -- the UI ---------------------------------------------------------------------------

def _config_app(stash, node_type, config=None):
    from frontend.app import AttackOfTheNodesApp
    from frontend.screens.node_config import NodeConfigScreen

    master, workflow_map, memory_bank, bus = _make_services()
    workflow_map.create_new("Insert test")
    workflow_map.add_node("start_node")
    node_id = workflow_map.add_node(node_type)
    if config:
        workflow_map.update_node_config(node_id, {**workflow_map.get_node_data(node_id)["config"], **config})
    app = AttackOfTheNodesApp(bus, workflow_map._factory, workflow_map, memory_bank, master,
                              stash_manager=stash)

    async def open_config(pilot):
        app.push_screen(NodeConfigScreen(workflow_map._factory, workflow_map, node_id,
                                         workflow_map.get_node_data(node_id)))
        await pilot.pause(0.2)
        return app.screen

    return app, open_config


def test_p_on_a_source_row_refuses_without_changing_source_or_path(stash, report):
    async def go():
        from frontend import notifications
        from frontend.screens.stash import StashScreen
        shown = []
        original = notifications.notify_info
        notifications.notify_info = lambda app, message: shown.append(message)
        try:
            app, open_config = _config_app(stash, "file_reader_node", {"input_source": "Upstream payload"})
            async with app.run_test(size=(100, 30)) as pilot:
                config = await open_config(pilot)
                config.query_one("#field-input_source").focus()
                await pilot.press("p"); await pilot.pause()
                assert app.screen is config and not isinstance(app.screen, StashScreen)
                assert config._get_form_values()["input_source"] == "Upstream payload"
                assert config._get_form_values()["file_path"] == ""
                assert shown == ["Stash text can't go into this field"]
        finally:
            notifications.notify_info = original
    asyncio.run(go())


def test_the_button_inserts_into_the_last_focused_field(stash, report):
    async def go():
        stash.add_file(str(report))
        app, open_config = _config_app(stash, "file_reader_node", {"input_source": "Configured"})
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.05)
            config = await open_config(pilot)
            await pilot.press("2")  # Parameters tab
            await pilot.pause(0.05)
            app.set_focus(config.query_one("#field-file_path"))
            await pilot.pause(0.05)
            await pilot.click("#stash-insert-node-config")
            await pilot.pause(0.1)
            await pilot.click("#stash-insert")
            await pilot.pause(0.1)
            assert config.query_one("#field-file_path", Input).value == str(report)
    asyncio.run(go())


def test_a_field_that_takes_nothing_says_so(stash):
    async def go():
        from frontend import notifications
        from frontend.screens.stash import StashScreen

        shown = []
        original = notifications.notify_info
        notifications.notify_info = lambda app, message: shown.append(message)
        try:
            app, open_config = _config_app(stash, "file_output_node")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause(0.05)
                config = await open_config(pilot)
                await pilot.press("2")
                await pilot.pause(0.05)
                app.set_focus(config.query_one("#field-binary_content"))
                await pilot.pause(0.05)
                await pilot.press("p")
                await pilot.pause(0.05)
                assert not isinstance(app.screen, StashScreen)
                assert shown == ["Stash text can't go into this field"]
        finally:
            notifications.notify_info = original
    asyncio.run(go())


def test_p_while_typing_is_a_letter(stash):
    async def go():
        from frontend.screens.stash import StashScreen

        app, open_config = _config_app(stash, "file_reader_node", {"input_source": "Configured"})
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.05)
            config = await open_config(pilot)
            await pilot.press("2")
            await pilot.pause(0.05)
            field = config.query_one("#field-file_path")
            app.set_focus(field)
            field.begin_edit()
            await pilot.press(*"/tmp/p")
            await pilot.pause(0.05)
            assert not isinstance(app.screen, StashScreen)
            assert field.value.endswith("/tmp/p")
    asyncio.run(go())


def test_insert_mode_refuses_an_entry_the_field_does_not_take(stash):
    async def go():
        from frontend import notifications
        from frontend.screens.stash import StashScreen

        stash.add_text("just words", name="words")
        shown = []
        original = notifications.notify_info
        notifications.notify_info = lambda app, message: shown.append(message)
        results = []
        try:
            from frontend.app import AttackOfTheNodesApp

            master, workflow_map, memory_bank, bus = _make_services()
            workflow_map.create_new("x")
            app = AttackOfTheNodesApp(bus, workflow_map._factory, workflow_map, memory_bank, master,
                                      stash_manager=stash)
            async with app.run_test(size=(100, 30)) as pilot:
                await pilot.pause(0.05)
                app.action_stash("add", insert_into={"label": "File path", "accepts": {"file"}},
                                 callback=results.append)
                await pilot.pause(0.05)
                screen = app.screen
                assert isinstance(screen, StashScreen)
                screen.added = [stash.get("words")]
                screen._refresh_added()
                screen.action_insert()
                await pilot.pause(0.05)
                assert app.screen is screen and results == []
                assert shown == ["'words' is [string]; this field takes [file]"]
        finally:
            notifications.notify_info = original
    asyncio.run(go())


def test_manage_mode_has_no_insert_button(stash):
    async def go():
        from frontend.app import AttackOfTheNodesApp

        master, workflow_map, memory_bank, bus = _make_services()
        workflow_map.create_new("x")
        app = AttackOfTheNodesApp(bus, workflow_map._factory, workflow_map, memory_bank, master,
                                  stash_manager=stash)
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.action_stash()
            await pilot.pause(0.05)
            assert "stash-insert" not in {b.id for b in app.screen.query(Button)}
    asyncio.run(go())


# -- Start's Default (owner, 2026-10-20: the type is "string") ---------------------------

@pytest.mark.parametrize("row_type, accepts", [("string", ["string"]), ("number", ["string"]),
                                               ("file", ["file"])])
def test_p_in_starts_default_asks_for_the_canonical_type(row_type, accepts):
    """P in Start's Default asked the Stash for "text", a type no entry has,
    so no text entry could be inserted there."""
    from textual.app import App

    from frontend.widgets.contract_rows import INPUT, ContractRowEditor

    asked = []

    class Host(App):
        def action_stash(self, initial_tab="add", insert_into=None, callback=None):
            asked.append((initial_tab, insert_into))

    async def go():
        app = Host()
        async with app.run_test(size=(100, 40)) as pilot:
            app.push_screen(ContractRowEditor(INPUT, {"name": "who", "type": row_type}, []))
            await pilot.pause(0.05)
            app.screen.query_one('#row-value').focus()
            await pilot.pause(0.05)
            app.screen.action_stash_insert()
            await pilot.pause(0.05)
    asyncio.run(go())
    assert asked == [("entries", {"label": "Default", "accepts": accepts})]

"""UX5: Connections tab with jumps, save and stay, Save / Discard / Stay (U3, U9)."""

from __future__ import annotations

import asyncio
import os

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.connection_rows import NO_PAYLOAD, connection_rows, vault_read_keys

FACTORY = NodeFactory()
CSS = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.tcss")


def _line():
    """start -> HTTP Request "Fetch" -> No Op "After"."""
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("ux5")
    start = workflow_map.add_node("start_node")
    fetch = workflow_map.add_node("http_request_node", alias="Fetch")
    after = workflow_map.add_node("no_op_node", alias="After")
    workflow_map.connect(start, "default", fetch, "input")
    workflow_map.connect(fetch, "default", after, "input")
    return workflow_map, start, fetch, after


def _run(workflow_map, node_id, check):
    """Mount the editor, open ``node_id``'s config through it, run ``check``."""
    from textual.app import App

    from frontend.screens.editor import EditorScreen

    editor = EditorScreen(FACTORY, workflow_map)

    class EditorApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(editor)

    async def body():
        async with EditorApp().run_test(size=(110, 40)) as pilot:
            await pilot.pause()
            editor._open_node_config(node_id)
            await pilot.pause()
            await pilot.pause()
            await check(pilot.app, editor, pilot)

    asyncio.run(body())


async def _settle(pilot, times=3):
    for _ in range(times):
        await pilot.pause()


def _alias_input(screen):
    from frontend.widgets.command_input import CommandInput

    return screen.query_one("#alias-input", CommandInput)


# --- Rows -------------------------------------------------------------------


def test_rows_name_both_ends_and_what_flows():
    workflow_map, start, fetch, after = _line()
    rows = connection_rows(workflow_map, FACTORY, fetch)
    assert [row["target"] for row in rows["incoming"]] == [start]
    assert [row["target"] for row in rows["outgoing"]] == [after]
    incoming = rows["incoming"][0]["text"]
    assert incoming.startswith(f"Start ({start}): ")
    assert "→ Input" in incoming
    outgoing = rows["outgoing"][0]["text"]
    assert f"→ After ({after}): Input" in outgoing
    assert rows["vault"] == []


def test_a_source_that_publishes_nothing_shows_no_payload():
    workflow_map, start, fetch, _after = _line()
    workflow_map.update_node_config(start, {**workflow_map.get_node_data(start)["config"],
                                            "transient_output": False})
    rows = connection_rows(workflow_map, FACTORY, fetch)
    assert rows["incoming"][0]["text"].endswith(f"({NO_PAYLOAD})")


def test_vault_reads_are_listed_separately_with_their_writers():
    workflow_map, start, fetch, after = _line()
    workflow_map.update_node_config(start, {**workflow_map.get_node_data(start)["config"],
                                            "vault_write": True, "vault_write_key": "greeting_copy"})
    workflow_map.update_node_config(after, {"membank_inputs": ["greeting_copy", "missing_key"]})
    rows = connection_rows(workflow_map, FACTORY, after)
    assert rows["vault"] == [
        {"target": start, "text": f"greeting_copy: written by Start ({start})"},
        {"target": None, "text": "missing_key: no node writes it"},
    ]


def test_inputs_sourced_from_the_vault_count_as_reads():
    config = {"membank_inputs": ["a"], "content_source": "Vault", "content_vault_key": "b",
              "file_path_source": "Configured", "file_path_vault_key": "unused"}
    assert vault_read_keys(config) == ["a", "b"]


def test_error_mux_marks_connections_of_unpicked_branches():
    workflow_map, _start, fetch, after = _line()
    rows = connection_rows(workflow_map, FACTORY, fetch, mux_ports={"other"})
    assert "removed on save" in rows["outgoing"][0]["text"]


# --- Jumps ------------------------------------------------------------------


def test_enter_on_a_row_opens_that_nodes_editor():
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, _start, fetch, after = _line()

    async def check(app, editor, pilot):
        assert isinstance(app.screen, NodeConfigScreen) and app.screen.node_id == fetch
        await pilot.press("4")
        await _settle(pilot)
        row = app.screen.query_one("#connection-outgoing-0")
        row.focus()
        await pilot.press("enter")
        await _settle(pilot)
        assert isinstance(app.screen, NodeConfigScreen)
        assert app.screen.node_id == after
        assert editor.selected_node_id == after

    _run(workflow_map, fetch, check)


def test_a_jump_to_a_node_the_view_does_not_show_opens_and_saves_that_node():
    """Two targets on one port: the editor shows one path, the jump still
    opens (and saves) the other node, not whatever is selected."""
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, _start, fetch, after = _line()
    other = workflow_map.add_node("no_op_node", alias="Other")
    workflow_map.connect(fetch, "default", other, "input")

    async def check(app, editor, pilot):
        await pilot.press("4")
        await _settle(pilot)
        rows = {str(w.label): w for w in app.screen.query(".connection-row")}
        next(w for label, w in rows.items() if "Other" in label).focus()
        await pilot.press("enter")
        await _settle(pilot)
        assert isinstance(app.screen, NodeConfigScreen) and app.screen.node_id == other
        _alias_input(app.screen).value = "Other renamed"
        await pilot.press("ctrl+s")
        await _settle(pilot)
        await pilot.press("escape")
        await _settle(pilot)
        assert app.screen is editor
        assert workflow_map.get_node_data(other)["alias"] == "Other renamed"
        assert workflow_map.get_node_data(after)["alias"] == "After"

    _run(workflow_map, fetch, check)


def test_jumping_with_edits_asks_and_discard_leaves_the_node_unchanged():
    from frontend.screens.node_config import NodeConfigScreen
    from frontend.screens.unsaved_changes import UnsavedChangesScreen

    workflow_map, start, fetch, _after = _line()

    async def check(app, editor, pilot):
        _alias_input(app.screen).value = "Renamed"
        await pilot.press("4")
        await _settle(pilot)
        app.screen.query_one("#connection-incoming-0").focus()
        await pilot.press("enter")
        await _settle(pilot)
        assert isinstance(app.screen, UnsavedChangesScreen)
        app.screen.query_one("#unsaved-discard").press()
        await _settle(pilot)
        assert isinstance(app.screen, NodeConfigScreen) and app.screen.node_id == start
        assert workflow_map.get_node_data(fetch)["alias"] == "Fetch"

    _run(workflow_map, fetch, check)


def test_jumping_with_edits_and_save_keeps_them():
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, start, fetch, _after = _line()

    async def check(app, editor, pilot):
        _alias_input(app.screen).value = "Renamed"
        await pilot.press("4")
        await _settle(pilot)
        app.screen.query_one("#connection-incoming-0").focus()
        await pilot.press("enter")
        await _settle(pilot)
        app.screen.query_one("#unsaved-save").press()
        await _settle(pilot)
        assert isinstance(app.screen, NodeConfigScreen) and app.screen.node_id == start
        assert workflow_map.get_node_data(fetch)["alias"] == "Renamed"

    _run(workflow_map, fetch, check)


# --- Save and stay ----------------------------------------------------------


def test_ctrl_s_saves_and_keeps_the_editor_open():
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, _start, fetch, _after = _line()

    async def check(app, editor, pilot):
        screen = app.screen
        _alias_input(screen).value = "Renamed"
        assert screen._is_dirty()
        await pilot.press("ctrl+s")
        await _settle(pilot)
        assert app.screen is screen and isinstance(screen, NodeConfigScreen)
        assert workflow_map.get_node_data(fetch)["alias"] == "Renamed"
        assert not screen._is_dirty()
        # Nothing left to ask about: Esc closes straight away.
        await pilot.press("escape")
        await _settle(pilot)
        assert app.screen is editor

    _run(workflow_map, fetch, check)


def test_ctrl_enter_saves_and_stays_like_ctrl_s():
    workflow_map, _start, fetch, _after = _line()

    async def check(app, editor, pilot):
        screen = app.screen
        _alias_input(screen).value = "Renamed"
        await pilot.press("ctrl+enter")
        await _settle(pilot)
        assert app.screen is screen
        assert workflow_map.get_node_data(fetch)["alias"] == "Renamed"

    _run(workflow_map, fetch, check)


def test_ctrl_s_commits_a_text_area_being_edited():
    from frontend.widgets.command_input import CommandTextArea

    workflow_map, start, _fetch, _after = _line()
    writer = workflow_map.add_node("file_output_node")
    workflow_map.update_node_config(writer, {**workflow_map.get_node_data(writer)["config"],
                                             "content_source": "Configured"})
    workflow_map.connect(start, "default", writer, "input")

    async def check(app, editor, pilot):
        screen = app.screen
        await pilot.press("2")
        await _settle(pilot)
        content = screen.query_one("#field-content", CommandTextArea)
        content.focus()
        await pilot.press("e")
        assert content.editing
        await pilot.press("h", "i", "enter", "x")
        assert content.text == "hi\nx"  # Enter stays a newline
        await pilot.press("ctrl+s")
        await _settle(pilot)
        assert not content.editing
        assert app.screen is screen
        assert workflow_map.get_node_data(writer)["config"]["content"] == "hi\nx"

    _run(workflow_map, writer, check)


def test_a_port_changing_save_refreshes_the_rows():
    from textual.widgets import SelectionList

    workflow_map, _start, fetch, _after = _line()
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "slow", "label": "Slow", "codes": ["timeout"], "forward": "error"}]})
    handler = workflow_map.add_node("no_op_node", alias="Handler")
    workflow_map.connect(fetch, "default", mux, "input")
    workflow_map.connect(mux, "slow", handler, "input")

    async def check(app, editor, pilot):
        screen = app.screen
        await pilot.press("4")
        await _settle(pilot)
        rows = lambda: [str(w.label) for w in screen.query(".connection-row")]
        assert any("Handler" in row for row in rows())
        screen.query_one("#mux-recover-from", SelectionList).deselect("timeout")
        await _settle(pilot)
        if screen is not app.screen:  # U1 prompt: leave the branch unlinked
            app.screen.query_one("#unpick-leave").press()
            await _settle(pilot)
        assert any("removed on save" in row for row in rows())
        await pilot.press("ctrl+s")
        await _settle(pilot)
        assert not any("Handler" in row for row in rows())

    _run(workflow_map, mux, check)


# --- Close with unsaved changes ---------------------------------------------


def test_escape_without_edits_closes_without_asking():
    workflow_map, _start, fetch, _after = _line()

    async def check(app, editor, pilot):
        await pilot.press("escape")
        await _settle(pilot)
        assert app.screen is editor

    _run(workflow_map, fetch, check)


def test_escape_with_edits_asks_save_discard_or_stay():
    from frontend.screens.node_config import NodeConfigScreen
    from frontend.screens.unsaved_changes import UnsavedChangesScreen

    workflow_map, _start, fetch, _after = _line()

    async def check(app, editor, pilot):
        screen = app.screen
        _alias_input(screen).value = "Renamed"
        await pilot.press("escape")
        await _settle(pilot)
        assert isinstance(app.screen, UnsavedChangesScreen)
        await pilot.press("escape")  # Esc in the prompt means Stay
        await _settle(pilot)
        assert app.screen is screen and isinstance(screen, NodeConfigScreen)
        await pilot.press("escape")
        await _settle(pilot)
        app.screen.query_one("#unsaved-discard").press()
        await _settle(pilot)
        assert app.screen is editor
        assert workflow_map.get_node_data(fetch)["alias"] == "Fetch"

    _run(workflow_map, fetch, check)


def test_escape_with_edits_then_save_saves_and_closes():
    workflow_map, _start, fetch, _after = _line()

    async def check(app, editor, pilot):
        _alias_input(app.screen).value = "Renamed"
        await pilot.press("escape")
        await _settle(pilot)
        app.screen.query_one("#unsaved-save").press()
        await _settle(pilot)
        assert app.screen is editor
        assert workflow_map.get_node_data(fetch)["alias"] == "Renamed"

    _run(workflow_map, fetch, check)


def test_a_fresh_error_resolver_saved_while_open_is_kept_on_close():
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, _start, fetch, _after = _line()

    async def check(app, editor, pilot):
        editor._catch_errors_for(fetch)
        await _settle(pilot)
        mux_screen = app.screen
        assert isinstance(mux_screen, NodeConfigScreen)
        mux_id = mux_screen.node_id
        _alias_input(mux_screen).value = "Catch Fetch"
        await pilot.press("ctrl+s")
        await _settle(pilot)
        await pilot.press("escape")
        await _settle(pilot)
        assert app.screen is not mux_screen
        assert workflow_map.get_node_data(mux_id)["alias"] == "Catch Fetch"

    _run(workflow_map, fetch, check)


def test_without_an_on_save_the_last_save_is_returned_on_close():
    from textual.app import App

    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, _start, fetch, _after = _line()
    results = []

    class ConfigApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(NodeConfigScreen(FACTORY, workflow_map, fetch,
                                              workflow_map.get_node_data(fetch)), results.append)

    async def body():
        async with ConfigApp().run_test(size=(110, 40)) as pilot:
            await _settle(pilot)
            _alias_input(pilot.app.screen).value = "Renamed"
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert results == []  # still open
            await pilot.press("escape")
            await _settle(pilot)

    asyncio.run(body())
    assert results and results[-1]["alias"] == "Renamed"

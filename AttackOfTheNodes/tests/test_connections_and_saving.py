"""UX5: Connections tab with jumps, save and stay, Save / Discard / Stay (U3, U9)."""

from __future__ import annotations

import asyncio
import os

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from backend.vault_declarations import active_vault_reads, active_vault_writes
from frontend.connection_rows import ERROR_PAYLOAD, NO_PAYLOAD, NO_WRITER, connection_rows

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
    assert incoming.startswith("Start: ")  # UX6: friendly label, no id
    assert "→ Input" in incoming
    outgoing = rows["outgoing"][0]["text"]
    assert "→ After: Input" in outgoing
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
    assert [(row["target"], row["text"]) for row in rows["vault"]] == [
        (start, "greeting_copy: written by Start"),
        (None, f"missing_key: {NO_WRITER}"),
    ]


def test_inputs_sourced_from_the_vault_count_as_reads():
    config = {"membank_inputs": ["a"], "content_source": "Vault", "content_vault_key": "b",
              "file_path_source": "Configured", "file_path_vault_key": "unused"}
    assert active_vault_reads("file_output_node", config, {}) == ["a", "b"]


# Review of #51, finding 2: every active read, from the shared model.


def test_branch_seeds_variable_readers_and_continuations_are_reads():
    assert active_vault_reads("branch_node", {
        "branch_count": 2,
        "branch_payload_sources": {"path_a": "vault:seed", "path_b": "input",
                                   "path_c": "vault:hidden"}}, {}) == ["seed"]
    assert active_vault_reads("get_variable_node", {"variable_name": "greeting"}, {}) == ["greeting"]
    assert active_vault_reads("get_variable_node", {}, {}) == ["value"]  # the node's default
    assert active_vault_reads("variable_reader_node", {"variable_name": "x"}, {}) == ["x"]
    assert active_vault_reads("conditional_node", {"left_value_source": "variable",
                                                   "variable_name": "flag"}, {}) == ["flag"]
    assert active_vault_reads("conditional_node", {"left_value_source": "input",
                                                   "variable_name": "flag"}, {}) == []
    chat = {"prompt_source": "Continue AI session", "continue_session_key": "session"}
    assert active_vault_reads("chat_completion_node", chat, {}) == ["session"]
    # A continuation key kept while another prompt mode is active is not read.
    stale = {**chat, "prompt_source": "Configured"}
    assert active_vault_reads("chat_completion_node", stale, {}) == []


def test_a_hidden_repeatable_slot_is_not_a_read():
    config = {"item_input_count": 1, "item_1_source": "Vault", "item_1_vault_key": "a",
              "item_2_source": "Vault", "item_2_vault_key": "b"}
    assert active_vault_reads("concat_node", config, {}) == ["a"]


def test_rows_for_the_three_reproduced_reads_point_to_their_writers():
    workflow_map, start, fetch, after = _line()
    setter = workflow_map.add_node("set_variable_node")
    workflow_map.update_node_config(setter, {"variable_name": "greeting", "value_source": "literal",
                                             "value": "hi"})
    getter = workflow_map.add_node("get_variable_node")
    workflow_map.update_node_config(getter, {"variable_name": "greeting"})
    branch = workflow_map.add_node("branch_node")
    workflow_map.update_node_config(branch, {"branch_count": 2,
                                             "branch_payload_sources": {"path_a": "vault:greeting"}})
    chat = workflow_map.add_node("chat_completion_node")
    workflow_map.update_node_config(chat, {**workflow_map.get_node_data(chat)["config"],
                                           "prompt_source": "Continue AI session",
                                           "continue_session_key": "greeting"})
    for reader in (getter, branch, chat):
        rows = connection_rows(workflow_map, FACTORY, reader)["vault"]
        assert [row["target"] for row in rows] == [setter], reader


# Review of #51, finding 3: config-driven writers are found.


def test_a_set_variable_writer_is_listed_and_jumpable():
    workflow_map, start, fetch, after = _line()
    setter = workflow_map.add_node("set_variable_node", alias="Remember")
    workflow_map.update_node_config(setter, {"variable_name": "greeting", "value_source": "literal",
                                             "value": "hi"})
    output = workflow_map.add_node("text_output_node")
    workflow_map.update_node_config(output, {**workflow_map.get_node_data(output)["config"],
                                             "input_source": "Vault", "input_vault_key": "greeting"})
    rows = connection_rows(workflow_map, FACTORY, output)["vault"]
    assert rows == [{"key": ("vault", "greeting", setter), "target": setter,
                     "text": "greeting: written by Remember"}]


def test_writers_are_listed_once_and_every_writer_is_listed():
    workflow_map, start, fetch, after = _line()
    # Standard and legacy declarations naming the same key: one writer row.
    workflow_map.update_node_config(start, {**workflow_map.get_node_data(start)["config"],
                                            "vault_write": True, "vault_write_key": "k",
                                            "membank_outputs": [{"id": "k"}]})
    assert active_vault_writes("start_node", workflow_map.get_node_data(start)["config"], {}) == ["k"]
    setter = workflow_map.add_node("variable_setter_node")
    workflow_map.update_node_config(setter, {"variable_name": "k"})
    workflow_map.update_node_config(after, {"membank_inputs": ["k"]})
    rows = connection_rows(workflow_map, FACTORY, after)["vault"]
    assert sorted(row["target"] for row in rows) == sorted([start, setter])


# Review of #51, finding 4: the Publish toggle only governs the normal output.


def test_an_error_port_still_carries_error_details_when_normal_output_is_off():
    workflow_map, start, _fetch, _after = _line()
    writer = workflow_map.add_node("file_output_node")
    workflow_map.update_node_config(writer, {**workflow_map.get_node_data(writer)["config"],
                                             "transient_output": False})
    workflow_map.connect(start, "default", writer, "input")
    normal = workflow_map.add_node("no_op_node", alias="Normal")
    handler = workflow_map.add_node("no_op_node", alias="Handler")
    workflow_map.connect(writer, "default", normal, "input")
    workflow_map.connect(writer, "error", handler, "input")
    rows = {row["target"]: row["text"] for row in connection_rows(workflow_map, FACTORY, writer)["outgoing"]}
    assert rows[normal].endswith(f"({NO_PAYLOAD})")
    assert rows[handler].endswith(f"({ERROR_PAYLOAD})")


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


# Review of #51, finding 1: a save keeps focus on the same connection.


def test_saving_from_a_row_keeps_that_connection_focused():
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, start, fetch, after = _line()

    async def check(app, editor, pilot):
        screen = app.screen
        await pilot.press("4")
        await _settle(pilot)
        screen.query_one("#connection-outgoing-0").focus()
        _alias_input(screen).value = "Renamed"
        await pilot.press("ctrl+s")
        await _settle(pilot)
        assert screen._connection_keys[app.focused.id] == ("out", "default", after, "input")
        await pilot.press("enter")
        await _settle(pilot)
        assert isinstance(app.screen, NodeConfigScreen) and app.screen.node_id == after

    _run(workflow_map, fetch, check)


def test_a_save_that_removes_the_focused_connection_moves_focus_to_a_row():
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
        screen.query_one("#mux-recover-from", SelectionList).deselect("timeout")
        await _settle(pilot)
        if screen is not app.screen:  # U1 prompt: leave the branch unlinked
            app.screen.query_one("#unpick-leave").press()
            await _settle(pilot)
        handler_row = next(w for w in screen.query(".connection-row") if "Handler" in str(w.label))
        handler_row.focus()
        await pilot.press("ctrl+s")
        await _settle(pilot)
        assert not any("Handler" in str(w.label) for w in screen.query(".connection-row"))
        assert app.focused is not None and app.focused.has_class("connection-row")
        assert app.focused.screen is screen

    _run(workflow_map, mux, check)


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


# Node audit of #51, finding 1: one Vault model for every consumer. A Set
# Variable writer must agree across the Connections row, the Vault picker,
# preflight validation and the run itself.


def test_a_set_variable_key_agrees_across_rows_picker_validation_and_run(tmp_path, monkeypatch):
    from textual.app import App
    from textual.widgets import Select

    from backend import error_handler, output_manager, run_history
    from backend.configuration_manager import ConfigurationManager
    from backend.master_state import MasterState
    from backend.memory_bank import MemoryBank
    from backend.output_manager import OutputManager
    from backend.validator import validate_workflow
    from frontend.screens.node_config import NodeConfigScreen

    monkeypatch.setattr(error_handler, "RUN_ERRORS_DIR", tmp_path / "run_errors")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history")
    monkeypatch.setattr(output_manager, "RUN_OUTPUTS_DIR", tmp_path / "run_outputs")
    bus = EventBus()
    workflow_map = WorkflowMap(FACTORY, bus)
    workflow_map.create_new("ux5_vault")
    start = workflow_map.add_node("start_node")
    setter = workflow_map.add_node("set_variable_node", alias="Remember")
    workflow_map.update_node_config(setter, {"variable_name": "greeting", "value_source": "literal",
                                             "value": "hi"})
    output = workflow_map.add_node("text_output_node")
    workflow_map.connect(start, "default", setter, "input")
    workflow_map.connect(setter, "default", output, "input")

    # Picker: Text Output offers the key under its Vault source.
    offered = {}

    class ConfigApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(NodeConfigScreen(FACTORY, workflow_map, output,
                                              workflow_map.get_node_data(output)))

    async def pick():
        async with ConfigApp().run_test(size=(110, 40)) as pilot:
            await _settle(pilot)
            screen = pilot.app.screen
            source = screen.query_one("#field-input_source", Select)
            offered["sources"] = [value for _, value in source._options]
            source.value = "Vault"
            await _settle(pilot)
            key = screen.query_one("#field-input_vault_key", Select)
            offered["keys"] = [value for _, value in key._options]

    asyncio.run(pick())
    assert "Vault" in offered["sources"]
    assert "greeting" in offered["keys"]

    workflow_map.update_node_config(output, {**workflow_map.get_node_data(output)["config"],
                                             "input_source": "Vault", "input_vault_key": "greeting"})
    # Connections row.
    rows = connection_rows(workflow_map, FACTORY, output)["vault"]
    assert [row["target"] for row in rows] == [setter]
    # Preflight.
    result = validate_workflow(workflow_map, FACTORY)
    assert not [e for e in result["errors"] if "greeting" in e["message"]], result["errors"]
    # Run.
    master = MasterState(workflow_map, MemoryBank(bus), bus, output_manager=OutputManager(),
                         configuration_manager=ConfigurationManager())

    async def run():
        assert await master.start_workflow()
        await asyncio.wait_for(master.wait_for_completion(), timeout=5.0)

    asyncio.run(run())
    assert "hi" in str(master._memory_bank.read_transient(output, "default"))

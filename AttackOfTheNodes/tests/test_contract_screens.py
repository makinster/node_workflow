"""Step 4a-2: Start inputs, Return End results and "Send back to calling
workflow" in Node Config (owner-approved samples, 2026-10-18).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_contract_screens.py -v
"""

import asyncio

from textual.app import App
from textual.widgets import Checkbox, Select, Static, TabPane

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.command_input import CommandInput
from frontend.widgets.contract_rows import ContractRowEditor, ContractRowsField, row_line


def _map(callable_=False):
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new("Contracts")
    start = workflow_map.add_node("start_node", alias="Start")
    reader = workflow_map.add_node("file_reader_node", alias="Read config")
    end = workflow_map.add_node("end_node", alias="Done")
    workflow_map.connect(start, "default", reader, "input")
    workflow_map.connect(reader, "default", end, "input")
    workflow_map.set_callable(callable_)
    return factory, workflow_map, {"start": start, "reader": reader, "end": end}


def _config(workflow_map, node_id):
    return workflow_map.get_node_data(node_id)["config"]


def _set(workflow_map, node_id, **values):
    workflow_map.update_node_config(node_id, {**_config(workflow_map, node_id), **values})


def _open(factory, workflow_map, node_id, steps):
    """Mount Node Config for ``node_id`` and run ``await steps(app, screen, pilot)``."""

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(NodeConfigScreen(factory, workflow_map, node_id,
                                              workflow_map.get_node_data(node_id)))

    async def run():
        app = Host()
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause(0.1)
            return await steps(app, app.screen, pilot)

    return asyncio.run(run())


def _tabs(screen):
    return [str(pane._title) if hasattr(pane, "_title") else pane.id for pane in screen.query(TabPane)]


# -- rows ------------------------------------------------------------------------

def test_row_lines_match_the_samples():
    assert row_line("input", {"name": "greeting", "type": "string", "value": "Hi", "to": "Downstream"}) \
        == 'greeting   [string] → next node         "Hi"'
    assert row_line("input", {"name": "report", "type": "file", "required": True, "to": "Vault",
                              "vault_key": "report"}) \
        == 'report     [file]   → Vault "report"    required, no default'
    assert row_line("input", {"name": "max_items", "type": "number", "value": "10", "to": "Both"}) \
        == "max_items  [number] → next node, Vault  10"
    assert row_line("result", {"name": "summary", "type": "string", "required": True,
                               "source": "Vault key", "vault_key": "summary"}) \
        == 'summary    [string] required  from Vault "summary"'
    assert row_line("result", {"name": "item_count", "type": "number", "required": False,
                               "source": "Incoming payload"}) \
        == "item_count [number] optional  from incoming value"


# -- Start -----------------------------------------------------------------------

def test_standard_start_shows_inputs_and_no_results_tab():
    factory, workflow_map, ids = _map()

    async def steps(app, screen, pilot):
        ids_ = [pane.id for pane in screen.query(TabPane)]
        field = screen.query_one("#start-inputs", ContractRowsField)
        return ids_, field.rows, str(screen.query_one(".modal-title").render())

    tabs, rows, title = _open(factory, workflow_map, ids["start"], steps)
    assert "node-config-tab-results" not in tabs
    # The old greeting shows as one row; nothing else is needed.
    assert [(row["name"], row["to"], row["value"]) for row in rows] == [
        ("greeting", "Downstream", "Workflow started")]
    assert "[sub]" not in title


def test_saving_an_untouched_start_keeps_its_config():
    factory, workflow_map, ids = _map()
    before = dict(_config(workflow_map, ids["start"]))

    async def steps(app, screen, pilot):
        return screen._save_result()

    result = _open(factory, workflow_map, ids["start"], steps)
    assert result["config"] == before
    assert "rows" not in result["config"]


def test_adding_an_input_checks_it_and_keeps_the_greeting_as_a_row():
    factory, workflow_map, ids = _map()

    async def steps(app, screen, pilot):
        screen.query_one("#start-inputs-add").press()
        await pilot.pause(0.1)
        editor = app.screen
        assert isinstance(editor, ContractRowEditor)
        editor.query_one("#row-name", CommandInput).value = "greeting"
        editor.action_submit()
        await pilot.pause(0.05)
        duplicate = str(editor.query_one("#row-error", Static).render())
        editor.query_one("#row-name", CommandInput).value = "max_items"
        editor.query_one("#row-type", Select).value = "number"
        editor.query_one("#row-value", CommandInput).value = "lots"
        editor.action_submit()
        await pilot.pause(0.05)
        bad_number = str(editor.query_one("#row-error", Static).render())
        editor.query_one("#row-value", CommandInput).value = "10"
        editor.query_one("#row-to", Select).value = "Both"
        editor.action_submit()
        await pilot.pause(0.1)
        summary = str(screen.query_one("#start-next-summary", Static).render())
        return duplicate, bad_number, summary, screen._save_result()

    duplicate, bad_number, summary, result = _open(factory, workflow_map, ids["start"], steps)
    assert duplicate == '"greeting" is already used'
    assert bad_number.startswith("Default expects a number")
    assert summary == "Next node gets: greeting, max_items"
    rows = result["config"]["rows"]
    assert [(row["name"], row["type"], row["to"]) for row in rows] == [
        ("greeting", "string", "Downstream"), ("max_items", "number", "Both")]
    assert rows[1]["value"] == "10" and not any(key.startswith("_") for row in rows for key in row)


def test_subworkflow_start_lists_what_is_sent_back():
    factory, workflow_map, ids = _map(callable_=True)

    def results_text():
        async def steps(app, screen, pilot):
            await pilot.press("2")
            await pilot.pause(0.05)
            pane = screen.query_one("#node-config-tab-results", TabPane)
            return [str(static.render()) for static in pane.query(Static)]
        return _open(factory, workflow_map, ids["start"], steps)

    assert results_text() == ['Nothing sent back yet. Tick "Send results back" on an End node.']
    _set(workflow_map, ids["end"], return_end=True, results=[])
    assert results_text() == ['Nothing sent back yet. Add results on End "Done".']
    _set(workflow_map, ids["end"], results=[
        {"id": "out_1", "name": "summary", "type": "string", "source": "Vault key", "vault_key": "summary"}])
    assert results_text() == ['Sent back when called. Edit on End "Done".',
                              'summary    [string] required  from Vault "summary"']


# -- End -------------------------------------------------------------------------

def test_standard_end_has_no_send_back_controls():
    factory, workflow_map, ids = _map()

    async def steps(app, screen, pilot):
        return (bool(screen.query("#return-end")), bool(screen.query("#field-return_end")),
                bool(screen.query("#field-results")))

    assert _open(factory, workflow_map, ids["end"], steps) == (False, False, False)


def test_subworkflow_end_sends_results_back():
    factory, workflow_map, ids = _map(callable_=True)

    async def steps(app, screen, pilot):
        field = screen.query_one("#end-results", ContractRowsField)
        hidden = field.display
        screen.query_one("#return-end", Checkbox).value = True
        await pilot.pause(0.05)
        shown = field.display
        screen.query_one("#end-results-add").press()
        await pilot.pause(0.1)
        editor = app.screen
        editor.query_one("#row-name", CommandInput).value = "summary"
        editor.action_submit()
        await pilot.pause(0.1)
        return hidden, shown, str(screen.query_one(".modal-title").render()), screen._save_result()

    hidden, shown, title, result = _open(factory, workflow_map, ids["end"], steps)
    assert (hidden, shown) == (False, True)
    assert title.endswith("[sub]")
    assert result["config"]["return_end"] is True
    assert [(row["name"], row["source"], row["required"]) for row in result["config"]["results"]] == [
        ("summary", "Vault key", True)]


# -- Send back to calling workflow ------------------------------------------------

def _reader_send_back(workflow_map, factory, ids, tick):
    async def steps(app, screen, pilot):
        await pilot.press("3")
        await pilot.pause(0.05)
        boxes = screen.query("#send-back-default")
        if boxes and tick is not None:
            boxes.first().value = tick
            await pilot.pause(0.05)
            dirty = screen._is_dirty()
            screen._save_result()
            return True, dirty
        return bool(boxes), None
    return _open(factory, workflow_map, ids["reader"], steps)


def test_send_back_adds_and_removes_the_result_on_the_return_end():
    factory, workflow_map, ids = _map(callable_=True)
    _set(workflow_map, ids["reader"], vault_write=True, vault_write_key="config")
    _set(workflow_map, ids["end"], return_end=True, results=[])

    assert _reader_send_back(workflow_map, factory, ids, True) == (True, True)
    results = _config(workflow_map, ids["end"])["results"]
    assert [(row["name"], row["type"], row["source"], row["vault_key"]) for row in results] == [
        ("config", "string", "Vault key", "config")]

    assert _reader_send_back(workflow_map, factory, ids, False) == (True, True)
    assert _config(workflow_map, ids["end"])["results"] == []


def test_send_back_needs_a_return_end_and_a_subworkflow():
    factory, workflow_map, ids = _map(callable_=True)
    _set(workflow_map, ids["reader"], vault_write=True, vault_write_key="config")
    assert _reader_send_back(workflow_map, factory, ids, None) == (False, None)

    factory, workflow_map, ids = _map(callable_=False)
    _set(workflow_map, ids["reader"], vault_write=True, vault_write_key="config")
    _set(workflow_map, ids["end"], return_end=True, results=[])
    assert _reader_send_back(workflow_map, factory, ids, None) == (False, None)


def test_keyboard_reaches_a_row_and_opens_its_editor():
    factory, workflow_map, ids = _map()

    async def steps(app, screen, pilot):
        await pilot.press("s")
        await pilot.pause(0.05)
        focused = app.focused.id
        await pilot.press("e")
        await pilot.pause(0.1)
        editor = app.screen
        name = editor.query_one("#row-name", CommandInput).value if isinstance(editor, ContractRowEditor) else None
        await pilot.press("escape")
        await pilot.pause(0.05)
        return focused, name, app.screen is screen

    focused, name, back = _open(factory, workflow_map, ids["start"], steps)
    assert focused == "start-inputs-row-0"
    assert name == "greeting"
    assert back


# -- Review of #85 at f5ca052 ----------------------------------------------------

def _reader_steps(edit):
    """Open Read config on Payloads, run ``edit``, then save. Returns the
    save result (None when the save was refused)."""
    async def steps(app, screen, pilot):
        await pilot.press("3")
        await pilot.pause(0.05)
        await edit(screen, pilot)
        return screen._save_result()
    return steps


def test_renaming_a_sent_back_key_moves_its_result():
    factory, workflow_map, ids = _map(callable_=True)
    _set(workflow_map, ids["reader"], vault_write=True, vault_write_key="config")
    _set(workflow_map, ids["end"], return_end=True, results=[])
    _reader_send_back(workflow_map, factory, ids, True)

    async def rename(screen, pilot):
        screen.query_one("#vault-output-key-default", CommandInput).value = "renamed"

    _open(factory, workflow_map, ids["reader"], _reader_steps(rename))
    results = _config(workflow_map, ids["end"])["results"]
    assert [(row["name"], row["vault_key"]) for row in results] == [("renamed", "renamed")]


def test_send_back_refuses_a_result_name_that_is_taken():
    factory, workflow_map, ids = _map(callable_=True)
    _set(workflow_map, ids["reader"], vault_write=True, vault_write_key="config")
    taken = [{"id": "out_1", "name": "config", "type": "string", "source": "Incoming payload"}]
    _set(workflow_map, ids["end"], return_end=True, results=taken)

    async def tick(screen, pilot):
        screen.query_one("#send-back-default", Checkbox).value = True

    result = _open(factory, workflow_map, ids["reader"], _reader_steps(tick))
    assert result is None
    assert _config(workflow_map, ids["end"])["results"] == taken


def test_removing_every_input_leaves_no_inputs():
    from backend.contracts import start_rows

    factory, workflow_map, ids = _map()

    async def steps(app, screen, pilot):
        screen.query_one("#start-inputs-row-0").focus()
        screen.query_one("#start-inputs-remove").press()
        await pilot.pause(0.1)
        return screen._save_result()

    result = _open(factory, workflow_map, ids["start"], steps)
    assert start_rows(result["config"]) == []
    workflow_map.update_node_config(ids["start"], result["config"])

    async def reopen(app, screen, pilot):
        return screen.query_one("#start-inputs", ContractRowsField).rows

    assert _open(factory, workflow_map, ids["start"], reopen) == []


def test_an_object_default_survives_an_unchanged_confirm():
    from backend.contracts import parse_text

    factory, workflow_map, ids = _map()
    rows = [{"id": "in_1", "name": "options", "type": "var", "value": {"limit": 3}, "to": "Vault"}]
    _set(workflow_map, ids["start"], rows=rows)

    async def steps(app, screen, pilot):
        screen.query_one("#start-inputs-row-0").press()
        await pilot.pause(0.1)
        app.screen.action_submit()
        await pilot.pause(0.1)
        return screen._save_result()

    saved = _open(factory, workflow_map, ids["start"], steps)["config"]["rows"][0]["value"]
    assert parse_text("var", saved) == {"limit": 3}


def test_a_file_default_survives_an_unchanged_confirm(tmp_path):
    """Review of #85: a typed file reference used to save back as JSON text,
    which a run then read as a file name."""
    from backend.contracts import parse_text
    from backend.file_refs import file_reference

    real = tmp_path / "report.txt"
    real.write_text("x")
    reference = file_reference(str(real))
    factory, workflow_map, ids = _map()
    rows = [{"id": "in_1", "name": "report", "type": "file", "value": reference, "to": "Vault"}]
    _set(workflow_map, ids["start"], rows=rows)

    async def steps(app, screen, pilot):
        screen.query_one("#start-inputs-row-0").press()
        await pilot.pause(0.1)
        shown = app.screen.query_one("#row-value", CommandInput).value
        app.screen.action_submit()
        await pilot.pause(0.1)
        return shown, screen._save_result()

    shown, result = _open(factory, workflow_map, ids["start"], steps)
    assert shown == str(real)  # a path, not JSON
    saved = result["config"]["rows"][0]["value"]
    assert saved == reference  # unchanged text keeps the typed value
    assert parse_text("file", saved) == parse_text("file", reference)

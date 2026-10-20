"""Step 4d: Stash entries as inputs (a Subworkflow node's "Stash entry"
source, saved by name, and ``aotn run --input key=@stash:name``).

Owner decisions, 2026-10-20: no per-machine bindings; a missing entry is a
validation error; the CLI lists every input that can't be filled.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_stash_inputs.py -v
"""

import pytest
from textual.widgets import Select

from backend import persistence
from backend.run_service import EXIT_INVALID_INPUT, EXIT_OK
from backend.stash_manager import StashManager, stash_ref_name
from tests.test_subworkflow_calls import (
    Flow,
    _validate,
    caller,
    codes,
    greeter,
    res,
    row,
    run,
)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    from backend import configuration_manager, run_history

    for name in ("WORKFLOWS_DIR", "RUN_HISTORY_DIR", "RUN_ERRORS_DIR", "RUN_OUTPUTS_DIR",
                 "RUN_FILES_DIR", "SETTINGS_DIR"):
        monkeypatch.setattr(persistence, name, tmp_path / name.lower())
    monkeypatch.setattr(persistence, "STASH_DIR", tmp_path / "stash")
    monkeypatch.setattr(configuration_manager, "SETTINGS_DIR", tmp_path / "settings_dir")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history_dir")
    yield


def from_stash(name, entry):
    return {"id": name, "name": name, "source": "Stash", "stash_entry": entry}


@pytest.mark.parametrize("text, name", [
    ("@stash:Q3 report", "Q3 report"),
    ('@stash:"Q4 draft"', "Q4 draft"),
    ("plain", None),
    (3, None),
])
def test_stash_ref_name(text, name):
    assert stash_ref_name(text) == name


# -- the Subworkflow node ------------------------------------------------------------

def test_a_text_entry_fills_a_child_input_and_is_typed_by_its_row():
    StashManager().add_text("Kim", name="who")
    StashManager().add_text("3", name="three")
    child = greeter(extra_rows=[row("times", "number", required=True)],
                    results=[res("greeted", vault_key="who"), res("times", "number")])
    parent = (Flow("Parent", callable_=True)
              .node("start", "start_node")
              .node("call", "subworkflow_node", workflow_id=child,
                    inputs=[from_stash("who", "WHO"), from_stash("times", "three")],
                    results=[{"name": "times", "to": "Vault", "vault_key": "n"},
                             {"name": "greeted", "to": "Vault", "vault_key": "g"}])
              .node("end", "end_node", return_end=True, results=[res("n", "number"), res("g")])
              .link("start", "call", "end").save())
    result, _ = run(parent)
    assert result.final_state == "FINISHED", result.errors
    assert result.values == {"n": 3, "g": "Kim"}  # names match ignoring case


def test_a_file_entry_fills_a_file_input(tmp_path):
    path = tmp_path / "q3.txt"
    path.write_text("numbers")
    StashManager().add_file(path, name="Q3 report")
    child = (Flow("Reads", callable_=True)
             .node("start", "start_node", rows=[row("doc", "file", required=True)])
             .node("end", "end_node", return_end=True, results=[res("doc", "file")])
             .link("start", "end").save())
    parent = caller(child, [from_stash("doc", "Q3 report")], child_result="doc",
                    results=[res("got", "file")])
    result, _ = run(parent)
    assert result.final_state == "FINISHED", result.errors
    assert result.values["got"]["path"] == str(path.resolve())


def test_a_missing_entry_fails_the_call_and_validation():
    parent = caller(greeter(), [from_stash("who", "gone")])
    result, _ = run(parent)
    assert "child_input_missing" in codes(result)
    errors, _ = _validate(parent)
    assert "subworkflow_stash_missing" in errors


def test_validation_passes_once_the_entry_exists_and_wants_a_name():
    parent = caller(greeter(), [from_stash("who", "who")])
    StashManager().add_text("Kim", name="who")
    assert "subworkflow_stash_missing" not in _validate(parent)[0]
    blank = caller(greeter(), [from_stash("who", "")], name="Blank")
    assert "subworkflow_stash_missing" in _validate(blank)[0]


# -- the Subworkflow node's Inputs tab ---------------------------------------------

def test_picking_a_stash_entry_saves_it_by_name_and_shows_it_as_a_source():
    from frontend.widgets.subworkflow_rows import SubworkflowInputEditor, SubworkflowInputsField
    from tests import test_subworkflow_screens as screens

    entry = StashManager().add_text("Kim", name="Q3 name")
    flow = screens.caller(screens.greeter())

    async def steps(app, screen, pilot):
        inputs = screen.query_one("#sub-inputs", SubworkflowInputsField)
        inputs.open_row(0)
        await pilot.pause(0.1)
        editor = app.screen
        assert isinstance(editor, SubworkflowInputEditor)
        hidden = editor.query_one("#row-stash-row").display
        editor.action_submit()  # still "Typed value" with nothing typed: allowed
        await pilot.pause(0.1)
        inputs.open_row(0)
        await pilot.pause(0.1)
        editor = app.screen
        editor.query_one("#row-source", Select).value = "Stash"
        await pilot.pause(0.05)
        editor.action_submit()
        await pilot.pause(0.05)
        refused = str(editor.query_one("#row-error").render())
        editor._pick_stash_entry(entry)
        await pilot.pause(0.05)
        shown = str(editor.query_one("#row-stash").render())
        editor.action_submit()
        await pilot.pause(0.1)
        return hidden, refused, shown, screens.lines(inputs), screen._collected_config()["inputs"]

    hidden, refused, shown, rows, config = screens.open_config(flow, steps)
    assert hidden is False
    assert refused == "Pick a Stash entry (P)"
    assert shown == 'Stash entry "Q3 name"'
    assert rows[0].endswith('Stash entry "Q3 name"')
    assert [(r["name"], r["source"], r["stash_entry"]) for r in config] == [("who", "Stash", "Q3 name")]


def test_a_row_whose_entry_is_gone_says_so():
    from frontend.widgets.subworkflow_rows import SubworkflowInputsField
    from tests import test_subworkflow_screens as screens

    flow = screens.caller(screens.greeter(), inputs=[from_stash("who", "old notes")])

    async def steps(app, screen, pilot):
        return screens.lines(screen.query_one("#sub-inputs", SubworkflowInputsField))

    rows = screens.open_config(flow, steps)
    assert rows[0].endswith('Stash entry "old notes"  ✗ no such Stash entry')


# -- aotn run --input key=@stash:name ------------------------------------------------

def _two_input_flow():
    return (Flow("Summarize", callable_=True)
            .node("start", "start_node", rows=[row("who", required=True),
                                               row("tone", value="plain"),
                                               row("api_url", required=True)])
            .node("end", "end_node", return_end=True,
                  results=[res("who"), res("tone"), res("api_url")])
            .link("start", "end").save())


def test_cli_reads_stash_entries_and_lists_where_inputs_came_from(capsys):
    import aotn_cli

    StashManager().add_text("Kim", name="Q3 report")
    workflow = _two_input_flow()
    code = aotn_cli.main([workflow, "--input", 'who=@stash:"Q3 report"', "--input", "api_url=http://x"])
    err = capsys.readouterr().err
    assert code == EXIT_OK, err
    assert "Inputs:\n" in err
    assert '• who' in err and 'from Stash entry "Q3 report"' in err and '"Kim"' in err
    assert "from its default" in err and "from --input" in err


def test_cli_lists_a_missing_entry_with_every_other_missing_input(capsys):
    import aotn_cli

    code = aotn_cli.main([_two_input_flow(), "--input", 'who=@stash:"Q4 draft"'])
    err = capsys.readouterr().err
    assert code == EXIT_INVALID_INPUT
    assert err.startswith("Can't start: 2 required inputs have no value.\n")
    assert 'no Stash entry "Q4 draft"' in err
    assert "use --input api_url=..." in err
    assert "Inputs:" not in err

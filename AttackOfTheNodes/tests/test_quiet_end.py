"""A quiet End node (owner, 2026-10-20): "Add a line to the output", on by
default; off, the End adds nothing, so a scheduled check that finds nothing
prints nothing.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_quiet_end.py -v
"""

import asyncio

from textual.widgets import Checkbox

from tests.test_contract_screens import _map, _open
from tests.test_subworkflow_calls import Flow, _isolated, run  # noqa: F401


def lines(result):
    return [str(o.get("value") if isinstance(o, dict) else o) for o in result.outputs]


def ended(**end_config):
    return Flow("Quiet").node("start", "start_node").node("end", "end_node", **end_config) \
        .link("start", "end").save()


def test_the_line_is_on_by_default():
    result, _ = run(ended())
    assert [line for line in lines(result) if line.startswith("[END]")] == [
        "[END] Branch completed (received: Workflow started)"]


def test_off_the_end_adds_nothing():
    result, _ = run(ended(record_line=False))
    assert result.final_state == "FINISHED"
    assert not [line for line in lines(result) if line.startswith("[END]")]


def test_a_saved_end_without_the_setting_keeps_its_line():
    flow = Flow("Old").node("start", "start_node").node("end", "end_node").link("start", "end")
    config = dict(flow.map.get_node_data(flow.ids["end"])["config"])
    config.pop("record_line", None)
    flow.map.update_node_config(flow.ids["end"], config)
    result, _ = run(flow.save())
    assert any(line.startswith("[END]") for line in lines(result))


def test_unticking_hides_the_line_field():
    factory, workflow_map, ids = _map()

    async def steps(app, screen, pilot):
        box = screen.query_one("#field-record_line", Checkbox)
        line_shown = screen.query_one("#field-message").display
        box.value = False
        await pilot.pause(0.1)
        return box.value, line_shown, screen.query_one("#field-message").display, \
            screen._collected_config()["record_line"]

    assert _open(factory, workflow_map, ids["end"], steps) == (False, True, False, False)

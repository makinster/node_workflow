"""Step 4c-1: the Subworkflow node in Node Config, the picker and the map
(owner-approved samples, 2026-10-19, revision 2).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_subworkflow_screens.py -v
"""

import asyncio

import pytest
from textual.app import App
from textual.widgets import Select, Static, TabPane

from backend import persistence
from backend.contracts import asking_nodes, call_contract
from frontend import subworkflow_info
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.command_input import CommandInput
from frontend.widgets.subworkflow_rows import (
    SubworkflowInputEditor,
    SubworkflowInputsField,
    SubworkflowPayloadEditor,
    SubworkflowPayloadsField,
    SubworkflowPicker,
)
from tests.test_subworkflow_calls import FACTORY, Flow, _isolated, res, row  # noqa: F401


def greeter(name="Greeter", asks=True):
    flow = (Flow(name, callable_=True)
            .node("start", "start_node", rows=[row("who", required=True), row("times", "number", value=2),
                                               row("tone", value="plain")]))
    if asks:
        flow.node("ask", "user_text_input_node", alias="Ask name")
    flow.node("end", "end_node", return_end=True,
              results=[res("greeted", vault_key="who"), res("config", "file", vault_key="cfg")])
    flow.link(*(["start", "ask", "end"] if asks else ["start", "end"]))
    return flow.save()


def caller(child_id, **config):
    flow = (Flow("Fetch report").node("start", "start_node")
            .node("greet", "subworkflow_node", alias="Greet", workflow_id=child_id, **config)
            .node("end", "end_node").link("start", "greet", "end"))
    flow.save()
    return flow


def open_config(flow, steps, size=(100, 50)):
    node_id = flow.ids["greet"]

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(NodeConfigScreen(FACTORY, flow.map, node_id, flow.map.get_node_data(node_id)))

    async def run():
        app = Host()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.1)
            return await steps(app, app.screen, pilot)

    return asyncio.run(asyncio.wait_for(run(), timeout=20))


def lines(field):
    return [str(button.label) for button in field.query(".sub-row")]


# -- what a caller sees ------------------------------------------------------------------

def test_call_contract_lists_inputs_results_and_the_nodes_that_ask():
    child = persistence.load_workflow(greeter())
    contract = call_contract(child)
    assert [r["name"] for r in contract["inputs"]] == ["who", "times", "tone"]
    assert [r["name"] for r in contract["results"]] == ["greeted", "config"]
    assert contract["asks"] == ["Ask name"]


def test_asking_nodes_follow_nested_calls_once():
    inner = greeter("Inner")
    outer = Flow("Outer", callable_=True).node("start", "start_node") \
        .node("call", "subworkflow_node", workflow_id=inner).node("again", "subworkflow_node", workflow_id=inner)
    outer_id = outer.save()
    assert asking_nodes(persistence.load_workflow(outer_id), persistence.load_workflow) == ["Ask name"]


def test_describe_rereads_a_saved_edit():
    child_id = greeter(asks=False)
    assert subworkflow_info.describe(child_id)["asks"] == []
    data = persistence.load_workflow(child_id)
    data["name"] = "Greeter 2"
    persistence.save_workflow(child_id, data)
    import os
    path = persistence.WORKFLOWS_DIR / f"{child_id}.json"
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
    assert subworkflow_info.describe(child_id)["name"] == "Greeter 2"


# -- Node Config --------------------------------------------------------------------------

def test_inputs_tab_shows_the_table_and_the_warning():
    child_id = greeter()
    flow = caller(child_id, inputs=[{"id": "m1", "name": "who", "source": "Configured", "value": "Kim"},
                                    {"id": "m2", "name": "times", "source": "Vault", "vault_key": "count"}])

    async def steps(app, screen, pilot):
        panes = [pane.id for pane in screen.query(TabPane)]
        field = screen.query_one("#sub-inputs", SubworkflowInputsField)
        header = str(field.query_one(".sub-header").render())
        return (panes, str(screen.query_one("#sub-name").render()), str(screen.query_one("#sub-asks").render()),
                header, lines(field))

    panes, name, asks, header, rows = open_config(flow, steps)
    assert panes == ["node-config-tab-core", "node-config-tab-outputs", "node-config-tab-connections"]
    assert name == "Greeter [sub]"
    assert asks == "⚠ Greeter may stop and ask you something (at its node Ask name)."
    assert header.split() == ["Input", "Type", "Required?", "Value", "comes", "from"]
    assert [r.split()[:3] for r in rows] == [["who", "[string]", "yes"], ["times", "[number]", "no"],
                                            ["tone", "[string]", "no"]]
    assert rows[0].endswith('typed: "Kim"') and rows[1].endswith('Vault key "count"')
    assert rows[2].endswith('its default: "plain"')


def test_payloads_tab_routes_and_the_next_node_line():
    flow = caller(greeter(), results=[{"id": "r1", "name": "config", "to": "Vault", "vault_key": ""}])

    async def steps(app, screen, pilot):
        field = screen.query_one("#sub-payloads", SubworkflowPayloadsField)
        return lines(field), str(screen.query_one("#sub-next").render())

    rows, next_line = open_config(flow, steps)
    assert rows[0].split()[:2] == ["greeted", "[string]"] and rows[0].endswith("next node")
    assert rows[1].endswith('Vault key "config"')  # blank key: the payload's own name
    assert next_line == "The next node receives: greeted"


def test_editing_an_input_and_a_payload_saves_the_rows():
    flow = caller(greeter())

    async def steps(app, screen, pilot):
        inputs = screen.query_one("#sub-inputs", SubworkflowInputsField)
        inputs.open_row(1)
        await pilot.pause(0.1)
        editor = app.screen
        assert isinstance(editor, SubworkflowInputEditor)
        editor.query_one("#row-source", Select).value = "Vault"
        await pilot.pause(0.05)
        editor.query_one("#row-vault-key", CommandInput).value = "count"
        editor.action_submit()
        await pilot.pause(0.1)
        payloads = screen.query_one("#sub-payloads", SubworkflowPayloadsField)
        payloads.open_row(0)
        await pilot.pause(0.1)
        editor = app.screen
        assert isinstance(editor, SubworkflowPayloadEditor)
        editor.query_one("#row-to", Select).value = "Both"
        await pilot.pause(0.05)
        editor.action_submit()
        await pilot.pause(0.1)
        return screen._collected_config(), str(screen.query_one("#sub-next").render())

    config, next_line = open_config(flow, steps)
    assert [(r["name"], r["source"], r["vault_key"]) for r in config["inputs"]] == [("times", "Vault", "count")]
    assert [(r["name"], r["to"], r["vault_key"]) for r in config["results"]] == [("greeted", "Both", "")]
    assert next_line == "The next node receives: greeted, config (as one object)"


def test_its_default_removes_the_mapping_and_a_bad_typed_value_is_refused():
    flow = caller(greeter(), inputs=[{"id": "m2", "name": "times", "source": "Configured", "value": "3"}])

    async def steps(app, screen, pilot):
        inputs = screen.query_one("#sub-inputs", SubworkflowInputsField)
        inputs.open_row(1)
        await pilot.pause(0.1)
        editor = app.screen
        editor.query_one("#row-value", CommandInput).value = "lots"
        editor.action_submit()
        await pilot.pause(0.05)
        refused = str(editor.query_one("#row-error").render())
        editor.query_one("#row-source", Select).value = "default"
        await pilot.pause(0.05)
        editor.action_submit()
        await pilot.pause(0.1)
        return refused, screen._collected_config()["inputs"]

    refused, inputs = open_config(flow, steps)
    assert refused.startswith("Value") and inputs == []


def test_a_required_input_without_a_default_cannot_use_its_default():
    flow = caller(greeter())

    async def steps(app, screen, pilot):
        screen.query_one("#sub-inputs", SubworkflowInputsField).open_row(0)
        await pilot.pause(0.1)
        return [value for _, value in app.screen.query_one("#row-source", Select)._options if value]

    assert "default" not in open_config(flow, steps)


def test_opening_and_closing_without_edits_changes_nothing():
    flow = caller(greeter())

    async def steps(app, screen, pilot):
        await pilot.pause(0.1)
        return screen._collected_config()

    config = open_config(flow, steps)
    assert config["inputs"] == [] and config["results"] == []
    assert config["workflow_id"] == flow.map.get_node_data(flow.ids["greet"])["config"]["workflow_id"]


# -- the picker ------------------------------------------------------------------------------

def test_picker_lists_subworkflows_searches_and_counts():
    for index in range(12):
        greeter(f"Helper {index:02d}", asks=False)
    child_id = greeter()
    flow = caller("")

    async def steps(app, screen, pilot):
        screen._open_subworkflow_picker()
        await pilot.pause(0.2)
        picker = app.screen
        assert isinstance(picker, SubworkflowPicker)
        everything = str(picker.query_one("#pick-count").render()), len(picker.query(".pick-row"))
        picker.query_one("#pick-search", CommandInput).value = "greet"
        await pilot.pause(0.2)
        found = str(picker.query_one("#pick-count").render()), str(picker.query_one("#pick-preview").render())
        picker.query_one(".pick-row").press()
        await pilot.pause(0.2)
        return everything, found, str(screen.query_one("#sub-name").render()), screen._collected_config()

    everything, found, name, config = open_config(flow, steps)
    assert everything == ("13 subworkflows", 13)
    assert found[0] == "1 of 13 subworkflows"
    assert "who [string] required" in found[1] and "may stop and ask you something" in found[1]
    assert name == "Greeter [sub]" and config["workflow_id"] == child_id


def test_changing_the_subworkflow_keeps_only_matching_mappings():
    first = greeter()
    other = Flow("Other", callable_=True).node("start", "start_node", rows=[row("who", required=True)]) \
        .node("end", "end_node", return_end=True, results=[res("done")]).link("start", "end").save()
    flow = caller(first, inputs=[{"id": "m1", "name": "who", "source": "Configured", "value": "Kim"},
                                 {"id": "m2", "name": "times", "source": "Configured", "value": "3"}],
                  results=[{"id": "r1", "name": "config", "to": "Vault", "vault_key": ""}])

    async def steps(app, screen, pilot):
        screen._open_subworkflow_picker()
        await pilot.pause(0.2)
        next(b for b in app.screen.query(".pick-row") if b.workflow_id == other).press()
        await pilot.pause(0.2)
        return screen._collected_config(), str(screen.query_one("#sub-asks").render())

    config, asks = open_config(flow, steps)
    assert config["workflow_id"] == other
    assert [r["name"] for r in config["inputs"]] == ["who"] and config["results"] == []
    assert asks == ""


# -- the editor map ----------------------------------------------------------------------------

def test_map_card_names_the_call_counts_vault_payloads_and_details_list_them():
    from frontend.screens.editor import EditorScreen

    flow = caller(greeter(), inputs=[{"id": "m1", "name": "who", "source": "Configured", "value": "Kim"}],
                  results=[{"id": "r1", "name": "config", "to": "Vault", "vault_key": ""},
                           {"id": "r2", "name": "greeted", "to": "Both", "vault_key": "hello"}])
    editor = EditorScreen(FACTORY, flow.map)
    row_ = next(r for r in editor._build_visible_rows() if r.get("node_id") == flow.ids["greet"])
    details = editor._format_node_details(flow.ids["greet"], flow.map.get_node_data(flow.ids["greet"]))
    assert row_["node"]["_display_label"] == "Greet (Greeter [sub])"
    assert row_["node"]["_editor_gap_marker"].endswith("➥ (2)")
    assert r"Runs: Greeter \[sub]" in details and "may ask you something (Ask name)" in details
    assert r'who [#4EC9B0]\[string][/] ← typed: "Kim"' in details
    assert r'greeted [#4EC9B0]\[string][/] → next node and Vault key "hello"' in details


def test_the_subworkflow_node_can_be_added_from_the_selector():
    from frontend.screens.node_selector import HIDDEN_NODE_TYPES

    assert "subworkflow_node" not in HIDDEN_NODE_TYPES


def test_a_highlighted_row_is_one_solid_colour():
    from frontend.widgets.subworkflow_rows import ROW_HIGHLIGHT

    flow = caller(greeter())

    async def steps(app, screen, pilot):
        await pilot.press("2")
        await pilot.pause(0.1)
        rows = list(screen.query("#sub-payloads .sub-row"))
        app.set_focus(rows[0])
        await pilot.pause(0.1)
        focused = rows[0].label.spans, rows[0].styles.background.hex.lower()
        app.set_focus(rows[1])
        await pilot.pause(0.1)
        return focused, bool(rows[0].label.spans)

    (spans, background), coloured_again = open_config(flow, steps)
    assert spans == [] and background == ROW_HIGHLIGHT
    assert coloured_again


# -- #91 review fixes (2026-10-20) ---------------------------------------------------------

def test_confirming_an_unchanged_object_value_keeps_the_object():
    child = Flow("Settings child", callable_=True).node(
        "start", "start_node", rows=[row("options", "var", required=True)]).node("end", "end_node").link(
        "start", "end").save()
    flow = caller(child, inputs=[{"id": "m1", "name": "options", "source": "Configured",
                                  "value": {"enabled": True}}])

    async def steps(app, screen, pilot):
        screen.query_one("#sub-inputs", SubworkflowInputsField).open_row(0)
        await pilot.pause(0.1)
        shown = app.screen.query_one("#row-value", CommandInput).value
        app.screen.action_submit()
        await pilot.pause(0.1)
        return shown, screen._collected_config()["inputs"][0]["value"]

    shown, saved = open_config(flow, steps)
    assert shown == '{"enabled": true}' and saved == {"enabled": True}


def test_picker_buttons_and_hints_fit_a_small_terminal():
    child_id = greeter()
    flow = caller(child_id)

    async def steps(app, screen, pilot):
        screen._open_subworkflow_picker()
        await pilot.pause(0.2)
        picker = app.screen
        card = picker.query_one("#modal-card").content_region
        return all(card.contains_region(picker.query_one(f"#{name}").region)
                   for name in ("confirm-row", "cancel-row"))

    assert open_config(flow, steps, size=(80, 24))


def test_a_prompt_added_in_a_nested_subworkflow_shows_up():
    import os

    inner = Flow("Inner", callable_=True)
    inner.node("start", "start_node").node("end", "end_node").link("start", "end")
    inner_id = inner.save()
    outer_id = Flow("Outer", callable_=True).node("start", "start_node") \
        .node("call", "subworkflow_node", workflow_id=inner_id).save()
    assert subworkflow_info.describe(outer_id)["asks"] == []
    inner.node("ask", "user_text_input_node", alias="Ask added")
    inner.save()
    path = persistence.WORKFLOWS_DIR / f"{inner_id}.json"
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
    assert subworkflow_info.describe(outer_id)["asks"] == ["Ask added"]

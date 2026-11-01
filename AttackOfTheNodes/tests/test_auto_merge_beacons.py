"""A save gives direct Merge joins the editor's Beacon shape."""

from __future__ import annotations

import asyncio
import copy

import pytest
from textual.app import App

from backend.authoring import _checked_graph
from backend.flow_behaviors import analyze_flow
from backend.merge_beacons import insert_merge_beacons
from frontend.screens.editor import EditorScreen
from frontend.screens.node_config import NodeConfigScreen, merge_input_options
from tests.test_merge_arrival_runtime import Engine

TWO_PATHS = {
    "format": "aotn-workflow/1",
    "name": "Two paths",
    "nodes": {
        "start": {"type": "start_node"},
        "split": {"type": "branch_node"},
        "a": {"type": "text_transform_node", "alias": "A"},
        "b": {"type": "text_transform_node", "alias": "B"},
        "join": {"type": "merge_node"},
        "end": {"type": "end_node"},
    },
    "connections": [
        {"from": "start.default", "to": "split.input"},
        {"from": "split.path_a", "to": "a.input"},
        {"from": "split.path_b", "to": "b.input"},
        {"from": "a.default", "to": "join.path_a"},
        {"from": "b.default", "to": "join.path_b"},
        {"from": "join.default", "to": "end.input"},
    ],
}

SPLIT_AGAIN = copy.deepcopy(TWO_PATHS)
SPLIT_AGAIN["name"] = "Split again"
SPLIT_AGAIN["nodes"].update({
    "inner": {"type": "branch_node"},
    "b1": {"type": "text_transform_node", "alias": "B1"},
    "b2": {"type": "text_transform_node", "alias": "B2"},
})
SPLIT_AGAIN["connections"] = [c for c in TWO_PATHS["connections"] if c["from"] != "b.default"] + [
    {"from": "b.default", "to": "inner.input"},
    {"from": "inner.path_a", "to": "b1.input"},
    {"from": "inner.path_b", "to": "b2.input"},
    {"from": "b1.default", "to": "join.path_b"},
    {"from": "b2.default", "to": "join.path_b"},
]

BRANCH_STRAIGHT_IN = copy.deepcopy(TWO_PATHS)
BRANCH_STRAIGHT_IN["name"] = "Branch straight in"
del BRANCH_STRAIGHT_IN["nodes"]["b"]
BRANCH_STRAIGHT_IN["connections"] = [
    c for c in TWO_PATHS["connections"] if "b." not in c["from"] + c["to"]
] + [{"from": "split.path_b", "to": "join.path_b"}]


EITHER_OR = copy.deepcopy(TWO_PATHS)
EITHER_OR["name"] = "Either-or into one slot"
EITHER_OR["nodes"].update({
    "pick": {"type": "conditional_node"},
    "yes": {"type": "text_transform_node", "alias": "Yes"},
    "no": {"type": "text_transform_node", "alias": "No"},
})
EITHER_OR["connections"] = [c for c in TWO_PATHS["connections"] if c["from"] != "b.default"] + [
    {"from": "b.default", "to": "pick.input"},
    {"from": "pick.true", "to": "yes.input"},
    {"from": "pick.false", "to": "no.input"},
    {"from": "yes.default", "to": "join.path_b"},
    {"from": "no.default", "to": "join.path_b"},
]

REVERSE_WIRING = copy.deepcopy(TWO_PATHS)
REVERSE_WIRING["name"] = "Inner split wired in reverse"
REVERSE_WIRING["nodes"].update({
    "inner": {"type": "branch_node"},
    "one": {"type": "text_transform_node", "alias": "One"},
    "two": {"type": "text_transform_node", "alias": "Two"},
    "rejoin": {"type": "text_transform_node", "alias": "Rejoin"},
})
REVERSE_WIRING["connections"] = [c for c in TWO_PATHS["connections"] if c["from"] != "b.default"] + [
    {"from": "b.default", "to": "inner.input"},
    {"from": "inner.path_b", "to": "two.input"},
    {"from": "inner.path_a", "to": "one.input"},
    {"from": "one.default", "to": "rejoin.input"},
    {"from": "two.default", "to": "rejoin.input"},
    {"from": "rejoin.default", "to": "join.path_b"},
]

SHAPES = [TWO_PATHS, SPLIT_AGAIN, BRANCH_STRAIGHT_IN, EITHER_OR, REVERSE_WIRING]


def _built(spec):
    engine = Engine()
    report, built = _checked_graph(engine.factory, spec)
    assert report["ok"], report["diagnostics"]
    return engine.factory, built, report["nodes"]


def _inputs(wm, node_id):
    return wm.get_node_data(node_id)["connections"]["inputs"]


def test_the_joining_path_gets_a_preconfigured_beacon():
    factory, wm, ids = _built(TWO_PATHS)
    added = insert_merge_beacons(wm, factory)

    assert [(a["source"], a["slot"]) for a in added] == [(ids["b"], "path_b")]
    beacon = added[0]["beacon"]
    by_slot = {c["target_port"]: c["source_node_id"] for c in _inputs(wm, ids["join"])}
    assert by_slot == {"path_a": ids["a"], "path_b": beacon}
    assert _inputs(wm, beacon)[0]["source_node_id"] == ids["b"]
    config = wm.get_node_data(ids["join"])["config"]
    assert config["branches_to_close"] == [f"{ids['split']}:path_b"]
    assert config["carry_forward_branch_id"] == "home:path_a"


@pytest.mark.parametrize("spec", SHAPES, ids=lambda s: s["name"])
def test_the_check_and_the_editor_accept_the_new_shape(spec):
    factory, wm, ids = _built(spec)
    insert_merge_beacons(wm, factory)
    assert not [f for f in analyze_flow(wm.get_all_node_data(), factory).findings if f.level == "error"]

    join = ids["join"]
    offered = {f"{o['branch_id']}:{o['branch_port']}" for o in merge_input_options(wm, join)}
    assert set(wm.get_node_data(join)["config"]["branches_to_close"]) == offered

    before = sorted((c["source_node_id"], c["target_port"]) for c in _inputs(wm, join))

    async def no_edit_save():
        screen = NodeConfigScreen(factory, wm, join, wm.get_node_data(join))

        class ConfigApp(App):
            saved = None

            def on_mount(self):
                self.push_screen(screen, lambda result: setattr(self, "saved", result))

        app = ConfigApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            screen.action_save()
            await pilot.pause()
        return app.saved

    saved = asyncio.run(no_edit_save())
    assert sorted(saved["config"]["branches_to_close"]) == sorted(offered)
    assert saved["config"]["carry_forward_branch_id"] == "home:path_a"
    wm.update_node_config(join, saved["config"])
    EditorScreen(factory, wm)._sync_merge_branch_end_connections(join, saved["config"], reconcile_unselected=True)
    assert sorted((c["source_node_id"], c["target_port"]) for c in _inputs(wm, join)) == before


def test_a_second_pass_changes_nothing():
    factory, wm, _ = _built(TWO_PATHS)
    insert_merge_beacons(wm, factory)
    assert insert_merge_beacons(wm, factory) == []


def test_a_saved_build_reports_the_beacon_it_added(tmp_path, monkeypatch):
    from backend import authoring

    monkeypatch.setattr(authoring.persistence, "WORKFLOWS_DIR", tmp_path)
    engine = Engine()
    report = authoring.build_workflow(engine.factory, TWO_PATHS)
    assert report["ok"], report["diagnostics"]
    assert len(report["added_beacons"]) == 1

"""A directly wired Merge in the editor: one path shows it, the others join it."""

from __future__ import annotations

import asyncio

from textual.app import App
from textual.widgets import Select, SelectionList, Static

from backend.authoring import _checked_graph
from frontend.app import AttackOfTheNodesApp
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.node_list import NodeList
from tests.test_merge_arrival_runtime import Engine

SPEC = {
    "format": "aotn-workflow/1",
    "name": "Two values",
    "nodes": {
        "start": {"type": "start_node"},
        "split": {"type": "branch_node", "alias": "Split"},
        "temp": {"type": "json_path_node", "alias": "Temperature", "config": {"path": "a"}},
        "rain": {"type": "json_path_node", "alias": "Rain chance", "config": {"path": "b"}},
        "join": {"type": "merge_node", "alias": "Collect values"},
        "words": {"type": "concat_node", "alias": "Write message"},
        "end": {"type": "end_node"},
    },
    "connections": [
        {"from": "start.default", "to": "split.input"},
        {"from": "split.path_a", "to": "temp.input"},
        {"from": "split.path_b", "to": "rain.input"},
        {"from": "temp.default", "to": "join.path_a"},
        {"from": "rain.default", "to": "join.path_b"},
        {"from": "join.default", "to": "words.input"},
        {"from": "words.default", "to": "end.input"},
    ],
}


def _engine():
    engine = Engine()
    report, built = _checked_graph(engine.factory, SPEC)
    assert report["ok"], report["diagnostics"]
    nodes = built.get_all_node_data()
    engine.wm.load_data({"id": "two_values", "name": SPEC["name"], "nodes": nodes})
    return engine, next(key for key, node in nodes.items() if node["type"] == "merge_node")


def _visible(rows, names):
    return [
        names[row["node_id"]] if row["kind"] == "node" else row.get("active_label")
        for row in rows
        if row["kind"] in ("node", "merge_beacon_select")
    ]


def test_only_the_home_path_lists_merge_and_the_other_path_ends_by_joining_it():
    async def scenario():
        engine, merge = _engine()
        names = {key: node.get("alias") or node.get("name") for key, node in engine.wm.get_all_node_data().items()}
        app = AttackOfTheNodesApp(engine.bus, engine.factory, engine.wm, engine.memory, engine.master)
        async with app.run_test(size=(110, 60)) as pilot:
            await pilot.pause()
            screen = app.screen
            screen.refresh_from_backend()
            await pilot.pause()
            node_list = screen.query_one(NodeList)
            assert _visible(node_list._rows, names) == [
                names[next(k for k, n in engine.wm.get_all_node_data().items() if n["type"] == "start_node")],
                "Split", "Temperature", "Collect values", "Write message",
                names[next(k for k, n in engine.wm.get_all_node_data().items() if n["type"] == "end_node")],
            ]

            node_list.index = next(i for i, row in enumerate(node_list._rows) if row["kind"] == "branch_select")
            node_list.focus()
            await pilot.pause()
            await pilot.press("right")
            await pilot.pause()
            visible = _visible(node_list._rows, names)
            assert visible[-2:] == ["Rain chance", "Joins Collect values"]
            assert "Write message" not in visible

            join_index = next(i for i, row in enumerate(node_list._rows) if row.get("direct_join"))
            assert node_list._rows[join_index]["merge_slot"] == "path_b"
            node_list.index = join_index
            await pilot.pause()
            screen.action_edit_selected()
            await pilot.pause()
            assert screen.selected_node_id == merge
            assert "Write message" in _visible(node_list._rows, names)

    asyncio.run(scenario())


def _merge_screen(engine, merge):
    return NodeConfigScreen(engine.factory, engine.wm, merge, engine.wm.get_node_data(merge))


def test_merge_form_shows_its_slots_and_the_keyboard_reaches_every_control():
    async def scenario():
        engine, merge = _engine()
        before = dict(engine.wm.get_node_data(merge)["config"])
        screen = _merge_screen(engine, merge)

        class ConfigApp(App):
            saved = None

            def on_mount(self):
                self.push_screen(screen, lambda result: setattr(self, "saved", result))

        app = ConfigApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            slots = str(screen.query_one("#merge-slots", Static).render())
            assert "Path A: Temperature. Read later as {input[path_a]}." in slots
            assert "Path B: Rain chance. Read later as {input[path_b]}." in slots
            assert not screen.query(SelectionList)
            assert isinstance(app.focused, Select)
            start = app.focused
            await pilot.press("s")
            await pilot.pause()
            assert app.focused is not start
            await pilot.press("w")
            await pilot.pause()
            assert app.focused is start
            screen.action_save()
            await pilot.pause()
        for key, value in app.saved["config"].items():
            if key in before:
                assert value == before[key], key

    asyncio.run(scenario())


def test_cursor_moves_past_any_empty_selection_list():
    async def scenario():
        engine, merge = _engine()
        screen = _merge_screen(engine, merge)

        class ConfigApp(App):
            def on_mount(self):
                self.push_screen(screen)

        app = ConfigApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            empty = SelectionList()
            assert screen._selection_list_at_top(empty)
            assert screen._selection_list_at_bottom(empty)

    asyncio.run(scenario())

"""Node selector: T switches between all nodes and nodes that take the upstream payload.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_selector_upstream_filter.py -v
"""

import asyncio
import os

import pytest

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.port_types import accepts_producers
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()
CSS = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.tcss")
DICE = {"name": "Dice", "types": ["number"]}


@pytest.fixture(autouse=True)
def _reset_toggle():
    from frontend.screens.node_selector import NodeSelectorScreen

    NodeSelectorScreen.show_fitting_only = False
    yield
    NodeSelectorScreen.show_fitting_only = False


# --- Backend rule --------------------------------------------------------------


@pytest.mark.parametrize("node_type, types, fits", [
    ("file_reader_node", ["number"], False),
    ("file_reader_node", ["file"], True),
    ("file_output_node", ["number"], False),
    ("file_output_node", ["string"], True),
    ("file_output_node", ["file"], True),
    ("no_op_node", ["number"], True),
    ("chat_completion_node", ["file"], False),
    ("start_node", ["string"], False),
    ("file_reader_node", [], True),
    ("file_reader_node", ["number", "file"], True),
])
def test_accepts_producers(node_type, types, fits):
    assert accepts_producers(FACTORY, node_type, types) is fits


# --- Selector screen -------------------------------------------------------------


def _visible_types(screen):
    """Every node type the selector lists across all tabs (groups expanded)."""
    from frontend.screens.node_selector import TABS

    seen = set()
    for tab in TABS:
        screen._set_active_tab(tab)
        for entry in screen._entries:
            if entry["kind"] == "node":
                seen.add(entry["node"]["type"])
            elif entry["kind"] == "group":
                seen.update(member["type"] for member in entry["members"])
    screen._set_active_tab(TABS[0])
    return seen


def _run_selector(upstream, body):
    from textual.app import App

    from frontend.screens.node_selector import NodeSelectorScreen

    screen = NodeSelectorScreen(FACTORY, upstream)

    class SelectorApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(screen)

    async def run():
        async with SelectorApp().run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.1)
            await body(pilot, screen)

    asyncio.run(run())


def _text(screen, selector):
    from textual.widgets import Label, Static

    widget = screen.query_one(selector)
    return str(widget.render()) if isinstance(widget, (Label, Static)) else ""


def test_toggle_hides_nodes_that_cannot_take_the_upstream_type():
    async def body(pilot, screen):
        everything = _visible_types(screen)
        assert {"file_reader_node", "no_op_node"} <= everything
        assert _text(screen, "#node-selector-title") == "Add Node · after Dice (number)"
        assert "T fitting only" in _text(screen, "#selector-help")

        await pilot.press("t")
        await pilot.pause(0.05)
        fitting = _visible_types(screen)
        assert "file_reader_node" not in fitting
        assert "file_output_node" not in fitting
        assert "no_op_node" in fitting
        assert fitting == {t for t in everything if accepts_producers(FACTORY, t, ["number"])}
        assert "T show all" in _text(screen, "#selector-help")

        await pilot.press("t")
        await pilot.pause(0.05)
        assert _visible_types(screen) == everything

    _run_selector(DICE, body)


def test_toggle_is_remembered_for_the_next_selector():
    from frontend.screens.node_selector import NodeSelectorScreen

    async def first(pilot, screen):
        await pilot.press("t")
        await pilot.pause(0.05)

    async def second(pilot, screen):
        assert "file_reader_node" not in _visible_types(screen)
        assert "T show all" in _text(screen, "#selector-help")

    _run_selector(DICE, first)
    assert NodeSelectorScreen.show_fitting_only is True
    _run_selector(DICE, second)


def test_typing_t_in_the_filter_does_not_toggle():
    from frontend.widgets.command_input import CommandInput

    async def body(pilot, screen):
        filter_input = screen.query_one("#node-filter", CommandInput)
        await pilot.press("/")
        await pilot.pause(0.05)
        if not filter_input.editing:
            await pilot.press("e")
            await pilot.pause(0.05)
        await pilot.press("t")
        await pilot.pause(0.05)
        assert filter_input.value == "t"
        assert "T fitting only" in _text(screen, "#selector-help")

    _run_selector(DICE, body)


def test_without_upstream_there_is_no_toggle():
    async def body(pilot, screen):
        everything = _visible_types(screen)
        assert _text(screen, "#node-selector-title") == "Add Node"
        assert "T " not in _text(screen, "#selector-help")
        await pilot.press("t")
        await pilot.pause(0.05)
        assert _visible_types(screen) == everything

    _run_selector(None, body)


def test_empty_list_explains_and_offers_show_all():
    from textual.widgets import ListView, Static

    def first_row(screen):
        item = screen.query_one("#node-type-list", ListView).children[0]
        return str(item.query_one(Static).render())

    async def body(pilot, screen):
        await pilot.press("t")
        await pilot.pause(0.05)
        # Searching for File Reader while only number-taking nodes are listed.
        from frontend.widgets.command_input import CommandInput

        screen.query_one("#node-filter", CommandInput).value = "file reader"
        await pilot.pause(0.05)
        assert not screen._entries
        assert first_row(screen) == "Nothing here takes number; T shows all"
        await pilot.press("t")
        await pilot.pause(0.05)
        assert [e["node"]["type"] for e in screen._entries] == ["file_reader_node"]

    _run_selector(DICE, body)


# --- Editor passes the upstream ---------------------------------------------------


def test_editor_insert_passes_the_traced_upstream():
    from textual.app import App

    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_selector import NodeSelectorScreen

    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("selector_upstream")
    start = workflow_map.add_node("start_node")
    dice = workflow_map.add_node("random_number_node", alias="Dice")
    pause = workflow_map.add_node("sleep_node", alias="Pause")
    workflow_map.connect(start, "default", dice, "input")
    workflow_map.connect(dice, "default", pause, "input")
    editor = EditorScreen(FACTORY, workflow_map)

    class EditorApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(editor)

    seen = {}

    async def run():
        async with EditorApp().run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.1)
            editor.selected_node_id = pause
            editor.selected_row = {"kind": "node", "node_id": pause}
            editor.action_insert_node()
            await pilot.pause(0.1)
            screen = pilot.app.screen
            seen["screen"] = type(screen).__name__
            seen["upstream"] = getattr(screen, "upstream", None)

    asyncio.run(run())
    assert seen["screen"] == NodeSelectorScreen.__name__
    # Sleep forwards Dice's number, so the selector is told "number".
    assert seen["upstream"] == {"name": "Pause", "types": ["number"]}

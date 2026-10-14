"""UX6 (U5, Q8): friendly node labels with a suffix only when a name repeats."""

from __future__ import annotations

import asyncio
import os

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.node_labels import SUFFIX_START, friendly_label, friendly_labels

FACTORY = NodeFactory()
CSS = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.tcss")


def _map():
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("ux6")
    return workflow_map


def test_unique_names_have_no_suffix_and_repeats_count_from_1000():
    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    first = workflow_map.add_node("http_request_node", alias="Fetch")
    other = workflow_map.add_node("no_op_node", alias="After")
    second = workflow_map.add_node("http_request_node", alias="Fetch")
    third = workflow_map.add_node("no_op_node", alias="Fetch")
    labels = friendly_labels(workflow_map)
    assert SUFFIX_START == 1000
    assert labels[start] == "Start" and labels[other] == "After"
    # Every node sharing the name is numbered, in workflow order.
    assert [labels[first], labels[second], labels[third]] == [
        "Fetch ·1000", "Fetch ·1001", "Fetch ·1002"]
    assert friendly_label(workflow_map, second) == "Fetch ·1001"


def test_labels_are_display_only():
    workflow_map = _map()
    first = workflow_map.add_node("no_op_node", alias="Step")
    workflow_map.add_node("no_op_node", alias="Step")
    friendly_labels(workflow_map)
    assert workflow_map.get_node_data(first)["alias"] == "Step"


def test_renaming_one_removes_the_suffix_from_the_other():
    workflow_map = _map()
    first = workflow_map.add_node("no_op_node", alias="Step")
    second = workflow_map.add_node("no_op_node", alias="Step")
    workflow_map.update_node_alias(second, "Other")
    labels = friendly_labels(workflow_map)
    assert labels[first] == "Step" and labels[second] == "Other"


def test_connections_rows_and_editor_cards_use_the_friendly_label():
    from textual.app import App

    from frontend.connection_rows import connection_rows
    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import NodeCard

    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    first = workflow_map.add_node("no_op_node", alias="Step")
    second = workflow_map.add_node("no_op_node", alias="Step")
    workflow_map.connect(start, "default", first, "input")
    workflow_map.connect(first, "default", second, "input")
    rows = connection_rows(workflow_map, FACTORY, first)
    assert rows["outgoing"][0]["text"].startswith("Output → Step ·1001: ")
    assert rows["incoming"][0]["text"].startswith("Start: ")

    editor = EditorScreen(FACTORY, workflow_map)
    seen = {}

    class EditorApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(editor)

    async def body():
        async with EditorApp().run_test(size=(110, 40)) as pilot:
            await pilot.pause()
            await pilot.pause()
            for card in editor.query(NodeCard):
                seen[card.node_id] = card.node_data.get("_display_label")

    asyncio.run(body())
    assert seen[first] == "Step ·1000" and seen[second] == "Step ·1001"
    assert seen[start] == "Start"

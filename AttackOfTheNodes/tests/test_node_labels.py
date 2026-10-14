"""Node names and where a node is (owner, 2026-10-14).

The UX6 numbered suffix for repeated names was rolled back: nodes show their
alias (or type name), and the node ID gets its own line in the node editor,
the details panel and error messages, whose first line names the node, its
type, depth and branch.
"""

from __future__ import annotations

import asyncio
import os

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.node_labels import friendly_label, friendly_labels
from frontend.node_location import MAIN_PATH, node_depth, node_heading

FACTORY = NodeFactory()
CSS = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.tcss")


def _map():
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("labels")
    return workflow_map


def test_repeated_names_are_shown_as_they_are():
    workflow_map = _map()
    first = workflow_map.add_node("no_op_node", alias="Step")
    second = workflow_map.add_node("no_op_node", alias="Step")
    labels = friendly_labels(workflow_map)
    assert labels[first] == labels[second] == "Step"
    assert friendly_label(workflow_map, second) == "Step"


def test_heading_names_type_depth_and_branch():
    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    fetch = workflow_map.add_node("http_request_node", alias="Fetch")
    branch = workflow_map.add_node("branch_node")
    inside = workflow_map.add_node("no_op_node", alias="Inside")
    loose = workflow_map.add_node("no_op_node", alias="Loose")
    workflow_map.connect(start, "default", fetch, "input")
    workflow_map.connect(fetch, "default", branch, "input")
    workflow_map.connect(branch, "path_b", inside, "input")
    assert node_depth(workflow_map, start) == 0 and node_depth(workflow_map, inside) == 3
    assert node_heading(workflow_map, FACTORY, fetch) == f"Fetch (HTTP Request) · depth 1 · {MAIN_PATH}"
    inside_heading = node_heading(workflow_map, FACTORY, inside)
    assert inside_heading.startswith("Inside (") and "· depth 3 · " in inside_heading
    assert not inside_heading.endswith(MAIN_PATH)  # it sits on a Branch path
    assert node_heading(workflow_map, FACTORY, loose).endswith("not reachable from Start")


def test_editor_cards_details_and_node_editor_keep_the_id_on_its_own_line():
    from textual.app import App

    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.node_card import NodeCard

    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    step = workflow_map.add_node("no_op_node", alias="Step")
    workflow_map.connect(start, "default", step, "input")
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
            card = next(c for c in editor.query(NodeCard) if c.node_id == step)
            seen["card"] = card.display_text
            seen["details"] = editor._format_node_details(step, workflow_map.get_node_data(step))
            pilot.app.push_screen(NodeConfigScreen(FACTORY, workflow_map, step,
                                                   workflow_map.get_node_data(step)))
            await pilot.pause()
            await pilot.pause()
            screen = pilot.app.screen
            seen["title"] = str(screen.query_one(".modal-title").content)
            seen["id_line"] = str(screen.query_one("#node-config-id").content)

    asyncio.run(body())
    assert step not in seen["card"]
    assert "Name: Step\n" in seen["details"] and f"Node ID: {step}" in seen["details"]
    assert seen["title"] == "Edit Node: Step"
    assert seen["id_line"] == f"Node ID: {step}"


def test_error_details_open_with_the_plain_heading_then_the_id():
    from textual.app import App

    from frontend.screens.error_details import ErrorDetailsScreen

    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    fetch = workflow_map.add_node("http_request_node", alias="Fetch")
    workflow_map.connect(start, "default", fetch, "input")
    seen = {}

    class ErrorApp(App):
        CSS_PATH = CSS

        def __init__(self):
            super().__init__()
            self.workflow_map = workflow_map
            self.factory = FACTORY

        def on_mount(self):
            self.push_screen(ErrorDetailsScreen({
                "node_id": fetch, "branch_id": "main",
                "error": {"message": "timed out", "category": "node"}}))

    async def body():
        async with ErrorApp().run_test(size=(110, 40)) as pilot:
            await pilot.pause()
            seen["text"] = str(pilot.app.screen.query_one("#error-details").content)

    asyncio.run(body())
    lines = seen["text"].splitlines()
    assert lines[0] == f"Fetch (HTTP Request) · depth 1 · {MAIN_PATH}"
    assert lines[1] == f"Node ID: {fetch}"

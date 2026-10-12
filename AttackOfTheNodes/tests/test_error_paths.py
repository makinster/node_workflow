"""Error paths on every node in the editor (port model P3).

The engine routes a failure along `error` from any node (D7). The editor
always shows it on nodes that list it (HTTP Request, JSON Path); any other
node shows it once its Errors section asks for it or once it is wired.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap
from frontend.error_paths import SHOW_ERROR_PATH, editor_output_ports, shows_error_path


def _map():
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new("Error paths")
    return factory, workflow_map


def test_error_path_is_hidden_until_asked_for_or_wired():
    factory, workflow_map = _map()
    logger = workflow_map.add_node("logger_node")
    handler = workflow_map.add_node("no_op_node")
    node = workflow_map.get_node_data(logger)
    assert editor_output_ports(factory, node) == ["default"]
    assert not shows_error_path(factory, node)

    workflow_map.update_node_config(logger, {**node["config"], SHOW_ERROR_PATH: True})
    assert editor_output_ports(factory, workflow_map.get_node_data(logger)) == ["default", "error"]

    workflow_map.update_node_config(logger, {**node["config"], SHOW_ERROR_PATH: False})
    workflow_map.connect(logger, "error", handler, "input")
    assert editor_output_ports(factory, workflow_map.get_node_data(logger)) == ["default", "error"]


def test_nodes_that_list_error_show_it_once():
    factory, workflow_map = _map()
    http = workflow_map.add_node("http_request_node")
    assert editor_output_ports(factory, workflow_map.get_node_data(http)) == ["default", "error"]


def test_the_backend_port_list_never_includes_the_engine_error_port():
    factory, workflow_map = _map()
    logger = workflow_map.add_node("logger_node")
    workflow_map.update_node_config(logger, {SHOW_ERROR_PATH: True})
    assert workflow_map.output_ports(logger) == ["default"]


def test_editor_and_node_config_helpers_add_the_shown_error_path():
    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import _node_output_ports

    factory, workflow_map = _map()
    logger = workflow_map.add_node("logger_node")
    workflow_map.update_node_config(logger, {SHOW_ERROR_PATH: True})
    node = workflow_map.get_node_data(logger)
    meta = {m["type"]: m for m in factory.get_node_types_metadata()}
    editor = SimpleNamespace(factory=factory, _metadata_for_type=meta.get)

    assert EditorScreen._output_ports_for_node(editor, node) == ["default", "error"]
    assert _node_output_ports(workflow_map, node) == ["default", "error"]


def test_a_wired_error_path_from_any_node_validates_and_restores():
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    logger = workflow_map.add_node("logger_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", logger, "input")
    workflow_map.connect(logger, "error", handler, "input")

    result = validate_workflow(workflow_map, factory)
    assert not [e for e in result["errors"] if e.get("node_id") == logger]

    adapter = EditorWorkflowAdapter(workflow_map, factory)
    assert adapter.replace_with_placeholder(handler)
    assert adapter.materialize_deleted_nodes() == 1
    report = adapter.restore_tombstone(handler)
    assert report.input_errors == []
    assert workflow_map.get_node_data(handler)["connections"]["inputs"] == [
        {"target_port": "input", "source_node_id": logger, "source_port": "error"}]


def test_wiring_an_error_path_into_a_new_mux_fills_its_routes():
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    http = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    editor = EditorScreen(factory, workflow_map)

    editor._connect_new_node(http, "error", mux)

    node = workflow_map.get_node_data(mux)
    assert node["connections"]["inputs"] == [
        {"target_port": "error", "source_node_id": http, "source_port": "error"}]
    assert [r["codes"] for r in node["config"]["routes"]] == [
        ["node_error"], ["missing_url"], ["timeout"], ["network"], ["http_status"]]


def test_errors_section_offers_the_toggle_only_where_error_is_not_listed():
    from textual.app import App
    from textual.widgets import Checkbox

    from frontend.screens.node_config import NodeConfigScreen

    factory, workflow_map = _map()
    logger = workflow_map.add_node("logger_node")
    http = workflow_map.add_node("http_request_node")

    async def mounted(node_id):
        screen = NodeConfigScreen(factory, workflow_map, node_id, workflow_map.get_node_data(node_id))

        class ConfigApp(App):
            def compose(self):
                yield screen

        app = ConfigApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            boxes = list(app.query("#show-error-path"))
            values = screen._error_path_config_values()
            if boxes:
                boxes[0].value = True
                await pilot.pause()
                values = (values, screen._error_path_config_values())
            return boxes, values

    boxes, values = asyncio.run(mounted(logger))
    assert len(boxes) == 1 and isinstance(boxes[0], Checkbox)
    assert values == ({SHOW_ERROR_PATH: False}, {SHOW_ERROR_PATH: True})

    boxes, values = asyncio.run(mounted(http))
    assert boxes == [] and values == {}

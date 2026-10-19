"""Owner bug report 2026-10-18 (Test Bench - C1/C2 checks).

1. Inserting a node after Dice lost everything below it: the next node (Pause)
   also had a second parent, so its input looked "occupied" and the insert
   never reconnected it.
2. HTTP Request and JSON Path showed an error path as soon as they were
   added. Errors go to the default handler until the user picks one to
   handle in the node's Errors tab.
3. A node's error path re-coloured the normal path below it.
"""

from __future__ import annotations

import asyncio

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.error_paths import SHOW_ERROR_PATH, editor_output_ports


def _map():
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new("Insert fan-in")
    return factory, workflow_map


def _targets(workflow_map, node_id, port="default"):
    node = workflow_map.get_node_data(node_id) or {}
    return [
        conn["target_node_id"]
        for conn in node["connections"]["outputs"]
        if conn["source_port"] == port
    ]


def test_insert_before_a_node_with_two_parents_keeps_it_downstream():
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    dice = workflow_map.add_node("random_number_node")
    note = workflow_map.add_node("no_op_node")
    pause = workflow_map.add_node("sleep_node")
    workflow_map.connect(dice, "default", pause, "input")
    workflow_map.connect(note, "default", pause, "input")
    http = workflow_map.add_node("http_request_node")
    editor = EditorScreen(factory, workflow_map)

    editor._connect_new_node(dice, "default", http)

    assert _targets(workflow_map, dice) == [http]
    assert _targets(workflow_map, http) == [pause]
    # The other parent is untouched.
    assert _targets(workflow_map, note) == [pause]


def test_http_request_and_json_path_show_no_error_path_until_asked():
    factory, workflow_map = _map()
    for node_type in ("http_request_node", "json_path_node"):
        node_id = workflow_map.add_node(node_type)
        node = workflow_map.get_node_data(node_id)
        assert factory.node_output_ports(node) == ["default"]
        assert editor_output_ports(factory, node) == ["default"]
        workflow_map.update_node_config(node_id, {**node["config"], SHOW_ERROR_PATH: True})
        assert editor_output_ports(factory, workflow_map.get_node_data(node_id)) == [
            "default", "error"]


def _run(node_type, config, inputs=None):
    factory = NodeFactory()
    node = factory.create_node(node_type, "n1")
    node.config.update(config)
    done, errors = [], []
    context = NodeContext(
        node_id="n1", branch_id="b", run_id="r",
        inputs=inputs or {"input": ""}, memory_bank=MemoryBank(EventBus()),
        signal_done=done.append, signal_error=errors.append,
        signal_waiting_for_input=lambda p: None,
        wait_for_nodes=lambda t, timeout: None,
        wait_for_merge=lambda n, b, p, i, timeout: None,
    )
    asyncio.run(node.execute(context))
    return done, errors


def test_http_request_failures_are_coded_node_errors():
    done, errors = _run("http_request_node", {"url": ""})
    assert done == []
    assert isinstance(errors[0], NodeError) and errors[0].code == "missing_url"


def test_json_path_invalid_json_is_a_coded_node_error():
    done, errors = _run("json_path_node", {"path": "a"}, {"input": "{nope"})
    assert done == []
    assert isinstance(errors[0], NodeError) and errors[0].code == "invalid_json"


def test_error_path_keeps_the_normal_path_colour():
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    fan = workflow_map.add_node("branch_node")
    logger = workflow_map.add_node("logger_node")
    after = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", fan, "input")
    workflow_map.connect(fan, "path_a", logger, "input")
    workflow_map.connect(logger, "default", after, "input")
    workflow_map.update_node_config(
        logger, {**workflow_map.get_node_data(logger)["config"], SHOW_ERROR_PATH: True})
    editor = EditorScreen(factory, workflow_map)

    rows = editor._build_visible_rows()
    keys = {row["node_id"]: row["node"].get("_editor_branch_color_key")
            for row in rows if row["kind"] == "node"}
    assert keys[after] == keys[logger]
    selectors = [row for row in rows if row["kind"] == "branch_select"]
    assert selectors[-1]["branch_node_id"] == logger
    assert selectors[-1]["active_color_key"] == keys[logger]

    # The error path itself still gets its own colour.
    editor.active_branch_ports[logger] = "error"
    rows = editor._build_visible_rows()
    error_row = [row for row in rows if row["kind"] == "branch_select"][-1]
    assert error_row["active_color_key"] != keys[logger]

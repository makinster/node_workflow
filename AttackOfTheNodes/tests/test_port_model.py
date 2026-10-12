"""Port model (spin-off P1): the backend resolves each node's ports from config.

Metadata ``output_ports`` is a node type's full list. ``Node.resolve_output_ports``
narrows or extends it per node (Branch shows only ``branch_count`` paths), and
every consumer — validator, editor, node config, tombstone restore — asks the
backend instead of re-deriving the rule.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.nodes.branch_node import (
    MAX_BRANCH_COUNT,
    MIN_BRANCH_COUNT,
    BranchNode,
    branch_count_from_config,
)
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
ALL_PATHS = ["path_a", "path_b", "path_c", "path_d", "path_e"]


def _map():
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new("Ports")
    return factory, workflow_map


@pytest.mark.parametrize("config,count", [
    ({}, 2),
    ({"branch_count": 3}, 3),
    ({"branch_count": "4"}, 4),
    ({"branch_count": 5}, 5),
    ({"branch_count": 1}, MIN_BRANCH_COUNT),
    ({"branch_count": 99}, MAX_BRANCH_COUNT),
    ({"branch_count": "lots"}, 2),
    ({"branch_count": None}, 2),
])
def test_branch_ports_follow_the_path_count(config, count):
    factory = NodeFactory()
    assert branch_count_from_config(config) == count
    assert BranchNode.resolve_output_ports(config) == ALL_PATHS[:count]
    assert factory.output_ports_for("branch_node", config) == ALL_PATHS[:count]
    assert factory.node_output_ports({"type": "branch_node", "config": config}) == ALL_PATHS[:count]


def test_metadata_keeps_the_full_type_list():
    factory = NodeFactory()
    meta = {m["type"]: m for m in factory.get_node_types_metadata()}
    assert meta["branch_node"]["output_ports"] == ALL_PATHS


def test_fixed_port_nodes_resolve_to_their_class_list():
    factory = NodeFactory()
    for meta in factory.get_node_types_metadata():
        if meta["type"] == "branch_node":
            continue
        resolved = factory.output_ports_for(meta["type"], meta["default_config"])
        assert resolved == list(meta["output_ports"]), meta["type"]


def test_unknown_types_and_empty_data_have_no_ports():
    factory = NodeFactory()
    assert factory.output_ports_for("no_such_node", {}) == []
    assert factory.node_output_ports(None) == []
    assert factory.node_output_ports({"type": "branch_node"}) == ALL_PATHS[:2]


def test_instances_and_the_workflow_map_agree_with_the_factory():
    factory, workflow_map = _map()
    branch = workflow_map.add_node("branch_node")
    workflow_map.update_node_config(branch, {"branch_count": 4})

    assert workflow_map.output_ports(branch) == ALL_PATHS[:4]
    assert workflow_map.get_node_instance(branch).get_output_ports() == ALL_PATHS[:4]
    assert workflow_map.output_ports("missing") == []


def _branch_workflow(count: int, port: str):
    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    tail = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(branch, {"branch_count": count})
    workflow_map.connect(start, "default", branch, "input")
    workflow_map.connect(branch, port, tail, "input")
    return factory, workflow_map, branch


def _messages(entries, node_id):
    return [e["message"] for e in entries if e.get("node_id") == node_id]


def test_validator_warns_about_a_connection_on_a_hidden_branch_path():
    factory, workflow_map, branch = _branch_workflow(2, "path_d")

    result = validate_workflow(workflow_map, factory)

    assert not any("path_d" in m for m in _messages(result["errors"], branch))
    assert any("hidden output 'path_d' never runs" in m
               for m in _messages(result["warnings"], branch))


def test_validator_accepts_a_visible_branch_path_without_a_hidden_warning():
    factory, workflow_map, branch = _branch_workflow(4, "path_d")

    result = validate_workflow(workflow_map, factory)

    assert not any("path_d" in m for m in _messages(result["errors"], branch))
    assert not any("hidden output" in m for m in _messages(result["warnings"], branch))


def test_validator_still_rejects_a_port_the_type_never_had():
    factory, workflow_map, branch = _branch_workflow(2, "path_z")

    result = validate_workflow(workflow_map, factory)

    assert any("undeclared port 'path_z'" in m for m in _messages(result["errors"], branch))


def test_hidden_branch_paths_never_fire():
    """The warning matches the engine: a Branch only spawns its counted paths."""
    factory, workflow_map, branch = _branch_workflow(2, "path_d")
    instance = workflow_map.get_node_instance(branch)
    sent = {}
    context = SimpleNamespace(
        node_id=branch,
        inputs={"input": "x"},
        memory_bank=SimpleNamespace(store_transient=lambda *a: None,
                                    read_persistent=lambda k, d=None: d),
        signal_done=lambda payload: sent.update(payload),
    )
    import asyncio
    asyncio.run(instance.execute(context))
    assert [b["output_port"] for b in sent["branches"]] == ALL_PATHS[:2]


# ---------------------------------------------------------------------------
# Frontend consumers ask the backend instead of re-deriving the rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count", [2, 3, 4, 5])
def test_editor_and_node_config_use_the_backend_ports(count):
    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import _node_output_ports

    factory, workflow_map = _map()
    branch = workflow_map.add_node("branch_node")
    workflow_map.update_node_config(branch, {"branch_count": count})
    node = workflow_map.get_node_data(branch)
    meta = {m["type"]: m for m in factory.get_node_types_metadata()}
    editor = SimpleNamespace(factory=factory,
                             _metadata_for_type=lambda node_type: meta.get(node_type))

    expected = ALL_PATHS[:count]
    assert EditorScreen._output_ports_for_node(editor, node) == expected
    assert _node_output_ports(workflow_map, node) == expected


def test_node_config_falls_back_to_connections_for_unknown_types():
    from frontend.screens.node_config import _node_output_ports

    factory, workflow_map = _map()
    node = {"type": "retired_node", "connections": {"outputs": [
        {"source_port": "b"}, {"source_port": "a"}]}}
    assert _node_output_ports(workflow_map, node) == ["a", "b"]


def test_frontend_no_longer_re_derives_branch_ports():
    """The count rule lives in backend/nodes/branch_node.py only."""
    for path in FRONTEND.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "min(5" not in text, path
        assert 'metadata.get("output_ports")' not in text, path
        assert 'meta.get("output_ports")' not in text, path


def test_tombstone_restore_checks_the_sources_resolved_ports():
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    left = workflow_map.add_node("no_op_node")
    right = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(branch, {"branch_count": 3})
    workflow_map.connect(start, "default", branch, "input")
    workflow_map.connect(branch, "path_a", left, "input")
    workflow_map.connect(branch, "path_c", right, "input")

    adapter = EditorWorkflowAdapter(workflow_map, factory)
    for node in (left, right):
        assert adapter.replace_with_placeholder(node)
    assert adapter.materialize_deleted_nodes() == 2
    # Lower the count: path_c is now hidden on the source.
    workflow_map.update_node_config(branch, {"branch_count": 2})

    assert adapter.restore_tombstone(left).input_errors == []
    report = adapter.restore_tombstone(right)
    assert [(e["port"], e["reason"]) for e in report.input_errors] == [
        ("path_c", "source_port_missing")]

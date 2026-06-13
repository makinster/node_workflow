"""Tests for Tombstone Phase B: legacy save migration.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_tombstone_migration.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_wm():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    wm = WorkflowMap(factory, bus)
    return wm, factory


def _legacy_deleted_node(
    original_type="concat_node",
    original_display_name="Concat",
    original_input_ports=None,
    original_output_ports=None,
):
    return {
        "type": "branch_end_node",
        "alias": "Deleted node",
        "config": {
            "_system_role": "deleted_node_branch_end",
            "deleted_node": {
                "original_type": original_type,
                "original_display_name": original_display_name,
                "original_input_ports": original_input_ports or ["input"],
                "original_output_ports": original_output_ports or ["default"],
            },
        },
        "connections": {"inputs": [], "outputs": []},
    }


def test_migrate_legacy_deleted_node_rewrites_type_and_config():
    from frontend.editor_workflow_adapter import migrate_legacy_deleted_node

    node = _legacy_deleted_node(
        original_type="concat_node",
        original_display_name="Concat",
        original_input_ports=["input"],
        original_output_ports=["default"],
    )
    result = migrate_legacy_deleted_node(node)

    assert result is node, "Should return the same object (in-place)"
    assert result["type"] == "tombstone_node"
    assert result["config"]["original_type"] == "concat_node"
    assert result["config"]["original_display_name"] == "Concat"
    assert result["config"]["original_input_ports"] == ["input"]
    assert result["config"]["original_output_ports"] == ["default"]
    assert "_system_role" not in result["config"]
    assert "deleted_node" not in result["config"]

    print("test_migrate_legacy_deleted_node_rewrites_type_and_config PASSED")


def test_migrate_legacy_deleted_node_carries_full_restore_data():
    from frontend.editor_workflow_adapter import migrate_legacy_deleted_node

    node = _legacy_deleted_node()
    node["config"]["deleted_node"].update(
        {
            "original_alias": "My Concat",
            "original_config": {"separator": ", "},
            "original_input_connections": [
                {"target_port": "input", "source_node_id": "n0", "source_port": "default"}
            ],
            "original_output_connections": [
                {"source_port": "default", "target_node_id": "n9", "target_port": "input"}
            ],
        }
    )
    result = migrate_legacy_deleted_node(node)

    assert result["config"]["original_alias"] == "My Concat"
    assert result["config"]["original_config"] == {"separator": ", "}
    assert result["config"]["original_inputs"] == [
        {"target_port": "input", "source_node_id": "n0", "source_port": "default"}
    ]
    assert result["config"]["original_outputs"] == [
        {"source_port": "default", "target_node_id": "n9", "target_port": "input"}
    ]

    print("test_migrate_legacy_deleted_node_carries_full_restore_data PASSED")


def test_migrate_legacy_deleted_node_is_no_op_for_plain_branch_end():
    from frontend.editor_workflow_adapter import migrate_legacy_deleted_node

    node = {
        "type": "branch_end_node",
        "alias": "Merge Beacon",
        "config": {},
        "connections": {"inputs": [], "outputs": []},
    }
    original_config = dict(node["config"])
    result = migrate_legacy_deleted_node(node)
    assert result["type"] == "branch_end_node"
    assert result["config"] == original_config

    print("test_migrate_legacy_deleted_node_is_no_op_for_plain_branch_end PASSED")


def test_migrate_legacy_deleted_node_is_no_op_for_tombstone():
    from frontend.editor_workflow_adapter import migrate_legacy_deleted_node

    node = {
        "type": "tombstone_node",
        "alias": "Deleted node",
        "config": {"original_type": "echo_node", "original_display_name": "Echo"},
    }
    result = migrate_legacy_deleted_node(node)
    assert result["type"] == "tombstone_node"
    assert result["config"]["original_type"] == "echo_node"

    print("test_migrate_legacy_deleted_node_is_no_op_for_tombstone PASSED")


def test_migrate_legacy_deleted_node_is_no_op_for_other_types():
    from frontend.editor_workflow_adapter import migrate_legacy_deleted_node

    for node_type in ("logger_node", "start_node", "echo_node"):
        node = {"type": node_type, "alias": "X", "config": {}}
        result = migrate_legacy_deleted_node(node)
        assert result["type"] == node_type, f"Unexpectedly mutated {node_type}"

    print("test_migrate_legacy_deleted_node_is_no_op_for_other_types PASSED")


def test_migrate_workflow_on_load_counts_migrations():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    bus = EventBus()
    factory = NodeFactory()
    wm = WorkflowMap(factory, bus)
    adapter = EditorWorkflowAdapter(wm, factory)

    # Build a fake all_nodes dict (bypassing WorkflowMap's CRUD)
    all_nodes = {
        "n1": _legacy_deleted_node("concat_node", "Concat"),
        "n2": _legacy_deleted_node("echo_node", "Echo"),
        "n3": {
            "type": "logger_node",
            "alias": "Logger",
            "config": {},
            "connections": {"inputs": [], "outputs": []},
        },
    }

    count = adapter.migrate_workflow_on_load(all_nodes)
    assert count == 2, f"Expected 2 migrations, got {count}"
    assert all_nodes["n1"]["type"] == "tombstone_node"
    assert all_nodes["n2"]["type"] == "tombstone_node"
    assert all_nodes["n3"]["type"] == "logger_node"

    print("test_migrate_workflow_on_load_counts_migrations PASSED")


def test_migrate_workflow_on_load_zero_when_nothing_to_migrate():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    bus = EventBus()
    factory = NodeFactory()
    wm = WorkflowMap(factory, bus)
    adapter = EditorWorkflowAdapter(wm, factory)

    all_nodes = {
        "n1": {"type": "start_node", "alias": "Start", "config": {}},
        "n2": {
            "type": "tombstone_node",
            "alias": "Deleted node",
            "config": {"original_type": "echo_node"},
        },
    }

    count = adapter.migrate_workflow_on_load(all_nodes)
    assert count == 0

    print("test_migrate_workflow_on_load_zero_when_nothing_to_migrate PASSED")


def test_migrate_preserves_validator_tombstone_error():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("migration_validator_check")
    start = wm.add_node("start_node")
    tomb = wm.add_node("tombstone_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", tomb, "input")
    wm.connect(tomb, "default", end, "input")
    wm.update_node_config(
        tomb,
        {
            "original_type": "concat_node",
            "original_display_name": "Concat",
            "original_input_ports": ["input"],
            "original_output_ports": ["default"],
        },
    )

    result = validate_workflow(wm, factory)
    assert not result["success"]
    assert any(e["node_id"] == tomb for e in result["errors"]), (
        "Tombstone error not present after migration"
    )

    print("test_migrate_preserves_validator_tombstone_error PASSED")

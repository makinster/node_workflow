"""Tests for Tombstone Phase B: editor_only flag and validator port context.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_tombstone_phase_b.py -v
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
    return WorkflowMap(factory, bus), factory


def test_tombstone_identity_has_editor_only_flag():
    _, factory = _make_wm()
    metadata = factory.get_node_types_metadata()
    by_type = {m["type"]: m for m in metadata}

    assert "tombstone_node" in by_type, "tombstone_node not registered"
    assert by_type["tombstone_node"]["editor_only"] is True

    for node_type, meta in by_type.items():
        if node_type != "tombstone_node":
            assert meta.get("editor_only") is False, (
                f"{node_type} unexpectedly has editor_only=True"
            )

    print("test_tombstone_identity_has_editor_only_flag PASSED")


def test_validator_tombstone_error_includes_port_context():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("tombstone_port_context")
    start = wm.add_node("start_node")
    tomb = wm.add_node("tombstone_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", tomb, "input")
    wm.connect(tomb, "default", end, "input")
    wm.update_node_config(
        tomb,
        {
            "original_display_name": "Concat",
            "original_type": "concat_node",
            "original_input_ports": ["input"],
            "original_output_ports": ["default"],
        },
    )

    result = validate_workflow(wm, factory)
    assert not result["success"]

    tomb_errors = [e for e in result["errors"] if e["node_id"] == tomb]
    assert tomb_errors, "No tombstone error emitted"
    msg = tomb_errors[0]["message"]
    assert "orphaned inputs: input" in msg, f"Missing port context in: {msg!r}"
    assert "orphaned outputs: default" in msg, f"Missing port context in: {msg!r}"

    print("test_validator_tombstone_error_includes_port_context PASSED")


def test_validator_tombstone_error_without_port_context():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("tombstone_no_ports")
    start = wm.add_node("start_node")
    tomb = wm.add_node("tombstone_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", tomb, "input")
    wm.connect(tomb, "default", end, "input")
    wm.update_node_config(
        tomb,
        {
            "original_display_name": "Concat",
            "original_input_ports": [],
            "original_output_ports": [],
        },
    )

    result = validate_workflow(wm, factory)
    assert not result["success"]
    tomb_errors = [e for e in result["errors"] if e["node_id"] == tomb]
    assert tomb_errors, "No tombstone error emitted"
    msg = tomb_errors[0]["message"]
    assert "Deleted node stub" in msg
    assert "orphaned" not in msg, f"Unexpected port context in: {msg!r}"

    print("test_validator_tombstone_error_without_port_context PASSED")


def test_validator_tombstone_error_multiple_ports():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("tombstone_multi_ports")
    start = wm.add_node("start_node")
    tomb = wm.add_node("tombstone_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", tomb, "input")
    wm.connect(tomb, "default", end, "input")
    wm.update_node_config(
        tomb,
        {
            "original_display_name": "Branch",
            "original_input_ports": ["input"],
            "original_output_ports": ["path_a", "path_b", "path_c"],
        },
    )

    result = validate_workflow(wm, factory)
    tomb_errors = [e for e in result["errors"] if e["node_id"] == tomb]
    msg = tomb_errors[0]["message"]
    assert "path_a" in msg and "path_b" in msg and "path_c" in msg, (
        f"Multi-port context missing in: {msg!r}"
    )

    print("test_validator_tombstone_error_multiple_ports PASSED")

"""Tests for Headless Plan H2: tombstone restore with connection validation.

Covers the restore procedure from BACKEND_FRONTEND_BOUNDARY.md: identity is
always restored, each stored connection is validated against the current
workflow, and drift is reported per category instead of blocking.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_tombstone_restore.py -v
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


def _tombstoned_logger(wm, factory):
    """Build start → logger → end, tombstone the logger, return ids + adapter."""
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    start = wm.add_node("start_node")
    logger = wm.add_node("logger_node", alias="Trace")
    end = wm.add_node("end_node")
    wm.update_node_config(logger, {"message": "hello"})
    wm.connect(start, "default", logger, "input")
    wm.connect(logger, "default", end, "input")

    adapter = EditorWorkflowAdapter(wm, factory)
    assert adapter.replace_with_placeholder(logger)
    assert adapter.materialize_deleted_nodes() == 1
    return adapter, start, logger, end


def test_clean_restore_reconnects_everything():
    wm, factory = _make_wm()
    wm.create_new("restore_clean")
    adapter, start, logger, end = _tombstoned_logger(wm, factory)

    report = adapter.restore_tombstone(logger)
    assert report.restored
    assert report.clean
    assert report.input_errors == []
    assert report.output_errors == []
    assert report.membank_warnings == []

    restored = wm.get_node_data(logger)
    assert restored["type"] == "logger_node"
    assert restored["alias"] == "Trace"
    assert restored["config"] == {"message": "hello"}
    assert restored["connections"]["inputs"] == [
        {"target_port": "input", "source_node_id": start, "source_port": "default"}
    ]
    assert restored["connections"]["outputs"] == [
        {"source_port": "default", "target_node_id": end, "target_port": "input"}
    ]
    assert wm.get_node_data(end)["connections"]["inputs"] == [
        {"target_port": "input", "source_node_id": logger, "source_port": "default"}
    ]
    print("test_clean_restore_reconnects_everything PASSED")


def test_restore_with_source_gone_leaves_input_unconnected():
    wm, factory = _make_wm()
    wm.create_new("restore_source_gone")
    adapter, start, logger, end = _tombstoned_logger(wm, factory)
    assert wm.delete_node(start)

    report = adapter.restore_tombstone(logger)
    assert report.restored
    assert not report.clean
    assert report.input_errors == [
        {
            "source_node_id": start,
            "source_alias": "",
            "port": "default",
            "reason": "source_missing",
        }
    ]
    restored = wm.get_node_data(logger)
    assert restored["type"] == "logger_node"
    assert restored["connections"]["inputs"] == []
    # Output side untouched by the input drift
    assert report.output_errors == []
    assert restored["connections"]["outputs"] == [
        {"source_port": "default", "target_node_id": end, "target_port": "input"}
    ]
    print("test_restore_with_source_gone_leaves_input_unconnected PASSED")


def test_restore_with_source_port_gone_reports_alias():
    wm, factory = _make_wm()
    wm.create_new("restore_source_port_gone")
    adapter, start, logger, end = _tombstoned_logger(wm, factory)

    # Tombstone the upstream source too: tombstone_node declares no output
    # ports, so the stored source port no longer exists on that node.
    assert adapter.replace_with_placeholder(start)
    assert adapter.materialize_deleted_nodes() == 1

    report = adapter.restore_tombstone(logger)
    assert report.restored
    assert report.input_errors == [
        {
            "source_node_id": start,
            "source_alias": "Deleted node",
            "port": "default",
            "reason": "source_port_missing",
        }
    ]
    assert wm.get_node_data(logger)["connections"]["inputs"] == []
    print("test_restore_with_source_port_gone_reports_alias PASSED")


def test_restore_with_target_gone_leaves_output_unconnected():
    wm, factory = _make_wm()
    wm.create_new("restore_target_gone")
    adapter, start, logger, end = _tombstoned_logger(wm, factory)
    assert wm.delete_node(end)

    report = adapter.restore_tombstone(logger)
    assert report.restored
    assert report.output_errors == [
        {
            "target_node_id": end,
            "target_alias": "",
            "port": "input",
            "reason": "target_missing",
        }
    ]
    restored = wm.get_node_data(logger)
    assert restored["connections"]["outputs"] == []
    assert restored["connections"]["inputs"] == [
        {"target_port": "input", "source_node_id": start, "source_port": "default"}
    ]
    print("test_restore_with_target_gone_leaves_output_unconnected PASSED")


def test_restore_with_target_port_occupied_reports_occupancy():
    wm, factory = _make_wm()
    wm.create_new("restore_target_occupied")
    adapter, start, logger, end = _tombstoned_logger(wm, factory)

    # While the logger is tombstoned, another node takes over the end node's
    # input port.
    usurper = wm.add_node("logger_node", alias="Usurper")
    wm.connect(start, "default", usurper, "input")
    wm.connect(usurper, "default", end, "input")

    report = adapter.restore_tombstone(logger)
    assert report.restored
    assert report.output_errors == [
        {
            "target_node_id": end,
            "target_alias": wm.get_node_data(end).get("alias", ""),
            "port": "input",
            "reason": "target_port_occupied",
        }
    ]
    restored = wm.get_node_data(logger)
    assert restored["connections"]["outputs"] == []
    # The usurper's wiring is untouched
    end_inputs = wm.get_node_data(end)["connections"]["inputs"]
    assert {
        "target_port": "input",
        "source_node_id": usurper,
        "source_port": "default",
    } in end_inputs
    print("test_restore_with_target_port_occupied_reports_occupancy PASSED")


def test_restore_flags_missing_membank_source():
    wm, factory = _make_wm()
    wm.create_new("restore_membank_missing")

    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    start = wm.add_node("start_node")
    logger = wm.add_node("logger_node", alias="Reader")
    end = wm.add_node("end_node")
    wm.update_node_config(logger, {"membank_inputs": ["shared_counter"]})
    wm.connect(start, "default", logger, "input")
    wm.connect(logger, "default", end, "input")

    adapter = EditorWorkflowAdapter(wm, factory)
    assert adapter.replace_with_placeholder(logger)
    assert adapter.materialize_deleted_nodes() == 1

    report = adapter.restore_tombstone(logger)
    assert report.restored
    assert report.membank_warnings == [
        {"variable": "shared_counter", "reason": "membank_source_missing"}
    ]
    # The declaration is restored with the config regardless of the warning
    assert wm.get_node_data(logger)["config"]["membank_inputs"] == ["shared_counter"]
    print("test_restore_flags_missing_membank_source PASSED")


def test_restore_membank_with_declared_source_is_clean():
    wm, factory = _make_wm()
    wm.create_new("restore_membank_declared")

    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    start = wm.add_node("start_node")
    writer = wm.add_node("logger_node", alias="Writer")
    logger = wm.add_node("logger_node", alias="Reader")
    end = wm.add_node("end_node")
    wm.update_node_config(writer, {"membank_outputs": ["shared_counter"]})
    wm.update_node_config(logger, {"membank_inputs": ["shared_counter"]})
    wm.connect(start, "default", writer, "input")
    wm.connect(writer, "default", logger, "input")
    wm.connect(logger, "default", end, "input")

    adapter = EditorWorkflowAdapter(wm, factory)
    assert adapter.replace_with_placeholder(logger)
    assert adapter.materialize_deleted_nodes() == 1

    report = adapter.restore_tombstone(logger)
    assert report.restored
    assert report.membank_warnings == []
    print("test_restore_membank_with_declared_source_is_clean PASSED")


def test_restore_non_tombstone_is_rejected():
    wm, factory = _make_wm()
    wm.create_new("restore_not_tombstone")

    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    logger = wm.add_node("logger_node")
    adapter = EditorWorkflowAdapter(wm, factory)

    report = adapter.restore_tombstone(logger)
    assert not report.restored
    assert report.failure_reason == "not_a_tombstone"
    assert wm.get_node_data(logger)["type"] == "logger_node"

    missing = adapter.restore_tombstone("no_such_node")
    assert not missing.restored
    assert missing.failure_reason == "not_a_tombstone"
    print("test_restore_non_tombstone_is_rejected PASSED")


def test_restore_without_restore_data_is_rejected():
    wm, factory = _make_wm()
    wm.create_new("restore_no_data")

    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    tomb = wm.add_node("tombstone_node")
    adapter = EditorWorkflowAdapter(wm, factory)

    report = adapter.restore_tombstone(tomb)
    assert not report.restored
    assert report.failure_reason == "no_restore_data"
    assert wm.get_node_data(tomb)["type"] == "tombstone_node"
    print("test_restore_without_restore_data_is_rejected PASSED")


def test_replace_placeholder_with_original_type_returns_restore_report():
    wm, factory = _make_wm()
    wm.create_new("replace_returns_report")
    adapter, start, logger, end = _tombstoned_logger(wm, factory)
    assert wm.delete_node(end)

    result = adapter.replace_placeholder(logger, "logger_node")
    assert result["replaced"] is True
    assert result["restored_original"] is True
    report = result["restore_report"]
    assert report.restored
    assert report.output_errors[0]["reason"] == "target_missing"
    print("test_replace_placeholder_with_original_type_returns_restore_report PASSED")


def test_partial_restore_clears_tombstone_validator_error():
    """A partially restored node must validate as loose ends, not a tombstone."""
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("restore_partial_validates")
    adapter, start, logger, end = _tombstoned_logger(wm, factory)
    assert wm.delete_node(end)

    report = adapter.restore_tombstone(logger)
    assert report.restored and report.output_errors

    result = validate_workflow(wm, factory)
    assert not any(
        "Deleted node stub" in e["message"] for e in result["errors"]
    ), "Tombstone error still present after restore"
    print("test_partial_restore_clears_tombstone_validator_error PASSED")

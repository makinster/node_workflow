"""Tests for parallel-branch vault key race condition warnings in the validator.

Design rule: Error = key not declared anywhere. Warning = key declared but only
on a parallel branch where execution order cannot be guaranteed. The validator
must NOT infer timing from node count or type.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_validator_race_warnings.py -v
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


def _race_warning_for(result, node_id, key):
    return any(
        w["node_id"] == node_id and "parallel branches" in w["message"] and key in w["message"]
        for w in result["warnings"]
    )


def test_no_warning_when_writer_is_upstream():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("race_upstream")
    start = wm.add_node("start_node")
    setter = wm.add_node("set_variable_node")
    reader = wm.add_node("get_variable_node")
    end = wm.add_node("end_node")

    wm.connect(start, "default", setter, "input")
    wm.connect(setter, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    wm.update_node_config(setter, {"membank_outputs": [{"id": "k1"}]})
    wm.update_node_config(reader, {"membank_inputs": [{"id": "k1"}]})

    result = validate_workflow(wm, factory)
    assert result["success"] is True
    assert not _race_warning_for(result, reader, "k1"), (
        f"Unexpected race warning: {result['warnings']}"
    )

    print("test_no_warning_when_writer_is_upstream PASSED")


def test_warning_when_writer_is_on_parallel_branch():
    from backend.validator import validate_workflow

    # start → branch → [path_a: setter(writes k)] [path_b: reader(reads k)] → end
    wm, factory = _make_wm()
    wm.create_new("race_parallel")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    setter = wm.add_node("set_variable_node")
    reader = wm.add_node("get_variable_node")
    end_a = wm.add_node("end_node")
    end_b = wm.add_node("end_node")

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", setter, "input")
    wm.connect(branch, "path_b", reader, "input")
    wm.connect(setter, "default", end_a, "input")
    wm.connect(reader, "default", end_b, "input")

    wm.update_node_config(setter, {"membank_outputs": [{"id": "k1"}]})
    wm.update_node_config(reader, {"membank_inputs": [{"id": "k1"}]})

    result = validate_workflow(wm, factory)
    assert result["success"] is True, "Should be warning, not error"
    assert _race_warning_for(result, reader, "k1"), (
        f"Expected race warning for k1, got: {result['warnings']}"
    )

    print("test_warning_when_writer_is_on_parallel_branch PASSED")


def test_no_warning_when_merge_provides_guaranteed_path():
    from backend.validator import validate_workflow

    # start → branch → [path_a: setter → merge] [path_b: merge] → reader → end
    # setter is an ancestor of reader via merge output
    wm, factory = _make_wm()
    wm.create_new("race_merge_path")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    setter = wm.add_node("set_variable_node")
    beacon_a = wm.add_node("branch_end_node")
    beacon_b = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    reader = wm.add_node("get_variable_node")
    end = wm.add_node("end_node")

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", setter, "input")
    wm.connect(setter, "default", beacon_a, "input")
    wm.connect(branch, "path_b", beacon_b, "input")
    wm.connect(beacon_a, "default", merge, "path_a")
    wm.connect(beacon_b, "default", merge, "path_b")
    wm.connect(merge, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    wm.update_node_config(setter, {"membank_outputs": [{"id": "k1"}]})
    wm.update_node_config(reader, {"membank_inputs": [{"id": "k1"}]})

    result = validate_workflow(wm, factory)
    assert not _race_warning_for(result, reader, "k1"), (
        f"Unexpected race warning after merge: {result['warnings']}"
    )

    print("test_no_warning_when_merge_provides_guaranteed_path PASSED")


def test_warning_absent_when_no_membank_inputs():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("race_no_inputs")
    start = wm.add_node("start_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", end, "input")

    result = validate_workflow(wm, factory)
    assert result["success"] is True
    assert not any("parallel branches" in w["message"] for w in result["warnings"]), (
        f"Unexpected race warning: {result['warnings']}"
    )

    print("test_warning_absent_when_no_membank_inputs PASSED")


def test_multiple_writers_one_upstream_no_warning():
    from backend.validator import validate_workflow

    # Two writers: setter_a is upstream of reader; setter_b is on a parallel branch.
    # At least one upstream writer → no race warning.
    wm, factory = _make_wm()
    wm.create_new("race_multi_writer")
    start = wm.add_node("start_node")
    setter_a = wm.add_node("set_variable_node")
    branch = wm.add_node("branch_node")
    setter_b = wm.add_node("set_variable_node")
    reader = wm.add_node("get_variable_node")
    end_b = wm.add_node("end_node")
    end_r = wm.add_node("end_node")

    wm.connect(start, "default", setter_a, "input")
    wm.connect(setter_a, "default", branch, "input")
    wm.connect(branch, "path_a", setter_b, "input")
    wm.connect(branch, "path_b", reader, "input")
    wm.connect(setter_b, "default", end_b, "input")
    wm.connect(reader, "default", end_r, "input")

    wm.update_node_config(setter_a, {"membank_outputs": [{"id": "k1"}]})
    wm.update_node_config(setter_b, {"membank_outputs": [{"id": "k1"}]})
    wm.update_node_config(reader, {"membank_inputs": [{"id": "k1"}]})

    result = validate_workflow(wm, factory)
    assert not _race_warning_for(result, reader, "k1"), (
        f"Unexpected race warning (setter_a is upstream): {result['warnings']}"
    )

    print("test_multiple_writers_one_upstream_no_warning PASSED")


def test_race_warning_is_not_an_error():
    from backend.validator import validate_workflow

    # Same parallel branch setup as test_warning_when_writer_is_on_parallel_branch.
    # Confirm result["success"] is True (warning, not error).
    wm, factory = _make_wm()
    wm.create_new("race_not_error")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    setter = wm.add_node("set_variable_node")
    reader = wm.add_node("get_variable_node")
    end_a = wm.add_node("end_node")
    end_b = wm.add_node("end_node")

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", setter, "input")
    wm.connect(branch, "path_b", reader, "input")
    wm.connect(setter, "default", end_a, "input")
    wm.connect(reader, "default", end_b, "input")

    wm.update_node_config(setter, {"membank_outputs": [{"id": "kx"}]})
    wm.update_node_config(reader, {"membank_inputs": [{"id": "kx"}]})

    result = validate_workflow(wm, factory)
    assert result["success"] is True, (
        f"Race condition should be a warning, not an error. Errors: {result['errors']}"
    )
    assert _race_warning_for(result, reader, "kx"), (
        f"Expected race warning, got: {result['warnings']}"
    )

    print("test_race_warning_is_not_an_error PASSED")

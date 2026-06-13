"""Tests for Headless Plan H5: backend branch health derivation.

Builds workflows through WorkflowMap so the structure matches real saves, then
asserts the derived per-branch state. Pure logic — no Textual.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_branch_health.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.branch_health import (
    ENDED_UNMERGED,
    FLOATING,
    VALID,
    branch_health_by_port,
    derive_branch_health,
    output_types_from_factory,
)
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap


def _make_wm():
    bus = EventBus()
    factory = NodeFactory()
    wm = WorkflowMap(factory, bus)
    wm.create_new("branch_health")
    return wm, factory


def _states(wm, factory=None):
    output_types = output_types_from_factory(factory) if factory else None
    return {
        (h.branch_node_id, h.port): h.state
        for h in derive_branch_health(wm.get_all_node_data(), output_types)
    }


# ---------------------------------------------------------------------------
# Single-state workflows
# ---------------------------------------------------------------------------


def test_floating_branch_dead_ends():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    a = wm.add_node("logger_node")
    b = wm.add_node("logger_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", a, "input")
    wm.connect(branch, "path_b", b, "input")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == FLOATING
    assert states[(branch, "path_b")] == FLOATING
    print("test_floating_branch_dead_ends PASSED")


def test_valid_branch_reaches_output_node():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    out_a = wm.add_node("text_output_node")
    end_b = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", out_a, "input")
    wm.connect(branch, "path_b", end_b, "input")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == VALID
    assert states[(branch, "path_b")] == VALID
    print("test_valid_branch_reaches_output_node PASSED")


def test_valid_branch_reaches_output_through_chain():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    mid = wm.add_node("logger_node")
    out = wm.add_node("text_output_node")
    other = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", mid, "input")
    wm.connect(mid, "default", out, "input")
    wm.connect(branch, "path_b", other, "input")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == VALID  # logger → text_output
    print("test_valid_branch_reaches_output_through_chain PASSED")


def test_ended_unmerged_beacon_not_connected_to_merge():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    beacon_a = wm.add_node("branch_end_node")
    beacon_b = wm.add_node("branch_end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", beacon_a, "input")
    wm.connect(branch, "path_b", beacon_b, "input")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == ENDED_UNMERGED
    assert states[(branch, "path_b")] == ENDED_UNMERGED
    print("test_ended_unmerged_beacon_not_connected_to_merge PASSED")


def test_valid_beacon_connected_to_merge():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    beacon_a = wm.add_node("branch_end_node")
    beacon_b = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", beacon_a, "input")
    wm.connect(branch, "path_b", beacon_b, "input")
    wm.connect(beacon_a, "default", merge, "path_a")
    wm.connect(beacon_b, "default", merge, "path_b")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == VALID
    assert states[(branch, "path_b")] == VALID
    print("test_valid_beacon_connected_to_merge PASSED")


def test_valid_branch_reaches_merge_directly():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    merge = wm.add_node("merge_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", merge, "path_a")
    wm.connect(branch, "path_b", merge, "path_b")
    wm.connect(merge, "default", end, "input")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == VALID
    assert states[(branch, "path_b")] == VALID
    print("test_valid_branch_reaches_merge_directly PASSED")


# ---------------------------------------------------------------------------
# Mixed and structural edge cases
# ---------------------------------------------------------------------------


def test_mixed_states_in_one_branch():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    end_a = wm.add_node("end_node")          # valid
    beacon_b = wm.add_node("branch_end_node")  # ended_unmerged
    dead_c = wm.add_node("logger_node")      # floating
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", end_a, "input")
    wm.connect(branch, "path_b", beacon_b, "input")
    wm.connect(branch, "path_c", dead_c, "input")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == VALID
    assert states[(branch, "path_b")] == ENDED_UNMERGED
    assert states[(branch, "path_c")] == FLOATING
    print("test_mixed_states_in_one_branch PASSED")


def test_nested_branch_classifies_outer_and_inner():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    outer = wm.add_node("branch_node")
    inner = wm.add_node("branch_node")
    end_outer = wm.add_node("end_node")
    end_inner_a = wm.add_node("end_node")
    floating_inner = wm.add_node("logger_node")
    wm.connect(start, "default", outer, "input")
    wm.connect(outer, "path_a", inner, "input")  # outer path_a -> nested branch
    wm.connect(outer, "path_b", end_outer, "input")
    wm.connect(inner, "path_a", end_inner_a, "input")
    wm.connect(inner, "path_b", floating_inner, "input")

    states = _states(wm, factory)
    # Outer path into a nested branch is structurally valid (leads onward)
    assert states[(outer, "path_a")] == VALID
    assert states[(outer, "path_b")] == VALID
    # Inner branches classified on their own merits
    assert states[(inner, "path_a")] == VALID
    assert states[(inner, "path_b")] == FLOATING
    print("test_nested_branch_classifies_outer_and_inner PASSED")


def test_unconnected_branch_port_is_floating():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    end_a = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", end_a, "input")
    # path_b intentionally left unconnected → not an edge, so absent from output

    health = derive_branch_health(wm.get_all_node_data())
    ports = {h.port for h in health}
    assert ports == {"path_a"}
    assert all(h.state == VALID for h in health if h.port == "path_a")
    print("test_unconnected_branch_port_is_floating PASSED")


def test_cycle_without_terminus_is_floating():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    a = wm.add_node("logger_node")
    b = wm.add_node("logger_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", a, "input")
    wm.connect(a, "default", b, "input")
    wm.connect(b, "default", a, "input")  # cycle a <-> b, no terminus
    wm.connect(branch, "path_b", end, "input")

    states = _states(wm, factory)
    assert states[(branch, "path_a")] == FLOATING
    assert states[(branch, "path_b")] == VALID
    print("test_cycle_without_terminus_is_floating PASSED")


def test_no_branch_nodes_yields_empty():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", end, "input")

    assert derive_branch_health(wm.get_all_node_data()) == []
    print("test_no_branch_nodes_yields_empty PASSED")


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_by_port_mapping_matches_list():
    wm, factory = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    end_a = wm.add_node("end_node")
    beacon_b = wm.add_node("branch_end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", end_a, "input")
    wm.connect(branch, "path_b", beacon_b, "input")

    nodes = wm.get_all_node_data()
    mapping = branch_health_by_port(nodes)
    assert mapping[(branch, "path_a")].state == VALID
    assert mapping[(branch, "path_b")].state == ENDED_UNMERGED
    assert len(mapping) == 2
    print("test_by_port_mapping_matches_list PASSED")


def test_output_types_from_factory_includes_outputs_family():
    _, factory = _make_wm()
    types = output_types_from_factory(factory)
    assert "end_node" in types
    assert "text_output_node" in types
    # branch/merge are handled separately, not treated as plain outputs
    assert "branch_node" not in types
    print("test_output_types_from_factory_includes_outputs_family PASSED")


def test_default_output_types_classify_without_factory():
    """Without a factory the default set still recognizes end/output nodes."""
    wm, _ = _make_wm()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    out = wm.add_node("text_output_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", out, "input")
    wm.connect(branch, "path_b", end, "input")

    states = {
        (h.branch_node_id, h.port): h.state
        for h in derive_branch_health(wm.get_all_node_data())
    }
    assert states[(branch, "path_a")] == VALID
    assert states[(branch, "path_b")] == VALID
    print("test_default_output_types_classify_without_factory PASSED")

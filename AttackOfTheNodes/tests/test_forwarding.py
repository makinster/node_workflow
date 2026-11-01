"""C4: fixed forwarding is declared, traced and shown read-only.

No-Op, Logger, Probe, Memory Snapshot, Join Merge and Repeat Counter pass
their input through unchanged (Sleep and Counter already declared it). The
declaration (ui_hints pass_through + forwarded_input_port) makes the output
type follow the input everywhere types are read.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_forwarding.py -v
"""

import asyncio
from types import SimpleNamespace

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.port_types import is_pass_through_node, trace_producers
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()
FORWARDING = ["no_op_node", "logger_node", "probe_node", "memory_snapshot_node",
              "branch_end_node", "repeat_counter_node", "sleep_node", "counter_node"]


def _meta(node_type):
    return next(m for m in FACTORY.get_node_types_metadata() if m["type"] == node_type)


@pytest.mark.parametrize("node_type", FORWARDING)
def test_forwarding_is_declared(node_type):
    hints = _meta(node_type)["ui_hints"]
    assert hints.get("pass_through"), node_type
    assert is_pass_through_node(FACTORY, {"type": node_type, "config": {}}, "default")


@pytest.mark.parametrize("node_type", FORWARDING)
def test_declared_forwarding_matches_execution(node_type):
    """The declaration is true: the node emits its input unchanged."""
    node = FACTORY.create_node(node_type, "n")
    payload = {"marker": 42}
    done = []
    context = SimpleNamespace(
        inputs={"input": payload}, memory_bank=MemoryBank(EventBus()), branch_id="b",
        node_id="n", run_id="r", signal_done=done.append, signal_error=lambda e: done.append(e),
        signal_waiting_for_input=lambda p: None,
    )
    if node_type == "sleep_node":
        node.config["duration"] = 0
    asyncio.run(node.execute(context))
    assert done and isinstance(done[0], dict), done
    assert done[0]["data"]["default"] is payload


@pytest.mark.parametrize("node_type", [t for t in FORWARDING if t != "branch_end_node"])
def test_type_flows_through_and_mismatch_is_found(node_type):
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new(f"c4_{node_type}")
    start = workflow_map.add_node("start_node")
    dice = workflow_map.add_node("random_number_node", alias="Dice")
    middle = workflow_map.add_node(node_type)
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(start, "default", dice, "input")
    workflow_map.connect(dice, "default", middle, "input")
    workflow_map.connect(middle, "default", reader, "input")
    config = dict(workflow_map.get_node_data(reader)["config"])
    config["input_source"] = "Upstream payload"
    workflow_map.update_node_config(reader, config)
    assert trace_producers(workflow_map.get_all_node_data(), FACTORY, middle, "default") == [(dice, "number")]
    messages = [w["message"] for w in validate_workflow(workflow_map, FACTORY)["warnings"]
                if w.get("code") == "type_mismatch"]
    assert messages == ["Input 'File' expects file but Dice sends number"]


@pytest.mark.parametrize("node_type", FORWARDING)
def test_error_output_is_not_forwarded(node_type):
    """The error port carries the failure record, not the node's input, so
    its type does not follow the input (review of #64)."""
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new(f"c4_err_{node_type}")
    start = workflow_map.add_node("start_node")
    dice = workflow_map.add_node("random_number_node", alias="Dice")
    middle = workflow_map.add_node(node_type)
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(start, "default", dice, "input")
    workflow_map.connect(dice, "default", middle, "input")
    workflow_map.connect(middle, "error", reader, "input")
    config = dict(workflow_map.get_node_data(reader)["config"])
    config["input_source"] = "Upstream payload"
    workflow_map.update_node_config(reader, config)
    node = workflow_map.get_node_data(middle)
    assert not is_pass_through_node(FACTORY, node, "error")
    assert trace_producers(workflow_map.get_all_node_data(), FACTORY, middle, "error") == [(middle, "any")]
    assert not [w for w in validate_workflow(workflow_map, FACTORY)["warnings"]
                if w.get("code") == "type_mismatch"]


def test_echo_is_not_forwarding():
    """Echo computes its output; it must not be declared as forwarding."""
    assert not is_pass_through_node(FACTORY, {"type": "echo_node", "config": {}}, "default")


def test_editor_shows_a_read_only_forwarding_summary():
    from frontend.screens.node_config import NodeConfigScreen

    screen = NodeConfigScreen.__new__(NodeConfigScreen)
    assert NodeConfigScreen._pass_through_note(screen, _meta("logger_node")) == (
        "Dead drop payload: Logs the payload, then forwards it unchanged.")

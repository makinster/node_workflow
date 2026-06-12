"""Focused tests for generated node random_number_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("random_number_node")]


def test_random_number_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("random_number_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "random_number_node")
    assert metadata["display_name"] == 'Random Number'
    assert metadata["default_alias"] == 'Random Number'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default']


async def _run_random(mode="integer", min_val=0, max_val=100, seed=""):
    factory = NodeFactory()
    node = factory.create_node("random_number_node", "n1")
    node.config["mode"] = mode
    node.config["min_value"] = min_val
    node.config["max_value"] = max_val
    node.config["seed"] = seed
    memory = MemoryBank(EventBus())
    done = []
    context = NodeContext(
        node_id="n1", branch_id="b", run_id="r",
        inputs={"input": ""}, memory_bank=memory,
        signal_done=done.append, signal_error=lambda e: None,
        signal_waiting_for_input=lambda p: None,
        wait_for_nodes=lambda t, timeout: None,
        wait_for_merge=lambda n, b, p, i, timeout: None,
    )
    await node.execute(context)
    return done[0]["data"]["default"]


@pytest.mark.asyncio
async def test_random_number_node_execute_template_smoke():
    factory = NodeFactory()
    node = factory.create_node("random_number_node", "generated")
    memory = MemoryBank(EventBus())
    done = []
    errors = []
    context = NodeContext(
        node_id="generated", branch_id="branch", run_id="run",
        inputs={"input": "seed"}, memory_bank=memory,
        signal_done=done.append, signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
    )
    await node.execute(context)
    assert not errors
    assert done


@pytest.mark.asyncio
async def test_random_number_integer_in_range():
    result = await _run_random(mode="integer", min_val=5, max_val=10)
    assert isinstance(result, int)
    assert 5 <= result <= 10


@pytest.mark.asyncio
async def test_random_number_float_in_range():
    result = await _run_random(mode="float", min_val=0, max_val=1)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


@pytest.mark.asyncio
async def test_random_number_seeded_is_deterministic():
    a = await _run_random(mode="integer", min_val=0, max_val=1000, seed="test-seed")
    b = await _run_random(mode="integer", min_val=0, max_val=1000, seed="test-seed")
    assert a == b

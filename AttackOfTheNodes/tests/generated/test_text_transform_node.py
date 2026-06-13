"""Focused tests for generated node text_transform_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("text_transform_node")]


def test_text_transform_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("text_transform_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "text_transform_node")
    assert metadata["display_name"] == 'Text Transform'
    assert metadata["default_alias"] == 'Text Transform'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default']


async def _run_transform(operation: str, text: str) -> str:
    factory = NodeFactory()
    node = factory.create_node("text_transform_node", "n1")
    node.config["operation"] = operation
    memory = MemoryBank(EventBus())
    done = []
    context = NodeContext(
        node_id="n1",
        branch_id="b",
        run_id="r",
        inputs={"input": text},
        memory_bank=memory,
        signal_done=done.append,
        signal_error=lambda e: None,
        signal_waiting_for_input=lambda p: None,
        wait_for_nodes=lambda t, timeout: None,
        wait_for_merge=lambda n, b, p, i, timeout: None,
    )
    await node.execute(context)
    return done[0]["data"]["default"]


@pytest.mark.asyncio
async def test_text_transform_node_execute_template_smoke():
    factory = NodeFactory()
    node = factory.create_node("text_transform_node", "generated")
    memory = MemoryBank(EventBus())
    done = []
    errors = []
    context = NodeContext(
        node_id="generated",
        branch_id="branch",
        run_id="run",
        inputs={"input": "seed"},
        memory_bank=memory,
        signal_done=done.append,
        signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
    )
    await node.execute(context)
    assert not errors
    assert done


@pytest.mark.asyncio
async def test_text_transform_uppercase():
    assert await _run_transform("uppercase", "hello") == "HELLO"


@pytest.mark.asyncio
async def test_text_transform_lowercase():
    assert await _run_transform("lowercase", "WORLD") == "world"


@pytest.mark.asyncio
async def test_text_transform_strip():
    assert await _run_transform("strip", "  hello  ") == "hello"


@pytest.mark.asyncio
async def test_text_transform_title():
    assert await _run_transform("title", "hello world") == "Hello World"


@pytest.mark.asyncio
async def test_text_transform_reverse():
    assert await _run_transform("reverse", "abc") == "cba"

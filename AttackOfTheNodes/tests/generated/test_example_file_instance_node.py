"""Focused tests for generated node example_file_instance_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("example_file_instance_node")]


def test_example_file_instance_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("example_file_instance_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "example_file_instance_node")
    assert metadata["display_name"] == 'File Instance'
    assert metadata["default_alias"] == 'File Instance'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default']


@pytest.mark.asyncio
async def test_example_file_instance_node_execute_template_smoke():
    factory = NodeFactory()
    node = factory.create_node("example_file_instance_node", "generated")
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

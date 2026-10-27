"""Focused tests for generated node node_catalogue_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("node_catalogue_node")]


def test_node_catalogue_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("node_catalogue_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "node_catalogue_node")
    assert metadata["display_name"] == 'Node catalogue'
    assert metadata["default_alias"] == 'Node catalogue'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default']
    # Every declared port exposes the per-port I/O contract (handoff §4/§6):
    # data_type defaults to "any", required defaults to False.
    for direction in ("input_port_metadata", "output_port_metadata"):
        for info in metadata[direction].values():
            assert info["data_type"] in {
                "string", "number", "bool", "var", "file", "ai_session", "any",
            }
            assert isinstance(info["required"], bool)
    # Declared error codes (D7); the default generic code is always first.
    assert [error["code"] for error in metadata["errors"]] == ['node_error', 'invalid_config', 'catalogue_empty', 'catalogue_too_large']


@pytest.mark.asyncio
async def test_node_catalogue_node_execute_template_smoke():
    factory = NodeFactory()
    node = factory.create_node("node_catalogue_node", "generated")
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

"""Focused tests for generated node hermes_ask_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("hermes_ask_node")]


def test_hermes_ask_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("hermes_ask_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "hermes_ask_node")
    assert metadata["display_name"] == 'Ask Hermes'
    assert metadata["default_alias"] == 'Ask Hermes'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default', 'details']
    # Every declared port exposes the per-port I/O contract (handoff §4/§6):
    # data_type defaults to "any", required defaults to False.
    for direction in ("input_port_metadata", "output_port_metadata"):
        for info in metadata[direction].values():
            assert info["data_type"] in {
                "string", "number", "bool", "var", "file", "ai_session", "any",
            }
            assert isinstance(info["required"], bool)
    # Declared error codes (D7); the default generic code is always first.
    assert [error["code"] for error in metadata["errors"]] == ['node_error', 'not_installed', 'unsupported_runtime', 'auth_failed', 'folder_missing', 'not_allowed', 'text_too_long', 'timed_out', 'turn_limit', 'permission_denied', 'agent_failed', 'invalid_response', 'record_failed', 'cleanup_failed']


@pytest.mark.asyncio
async def test_hermes_ask_node_execute_template_smoke():
    factory = NodeFactory()
    node = factory.create_node("hermes_ask_node", "generated")
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
    # The generated defaults intentionally require a question and folder.
    # Smoke must refuse without launching a provider, not fake a response.
    assert not done
    assert errors and errors[0].code == "node_error"

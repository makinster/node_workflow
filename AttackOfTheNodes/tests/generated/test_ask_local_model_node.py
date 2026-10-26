"""Focused tests for generated node ask_local_model_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("ask_local_model_node")]


def test_ask_local_model_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("ask_local_model_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "ask_local_model_node")
    assert metadata["display_name"] == 'Ask local model'
    assert metadata["default_alias"] == 'Ask local model'
    assert metadata["input_ports"] == ['input', 'context']
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
    assert [error["code"] for error in metadata["errors"]] == ['node_error', 'settings_invalid', 'invalid_config', 'server_unreachable', 'model_missing', 'local_model_required', 'server_busy', 'timed_out', 'server_error', 'response_too_large', 'incomplete_reply', 'invalid_response', 'thinking_unsupported', 'text_too_long', 'context_too_long']


@pytest.mark.asyncio
async def test_ask_local_model_node_default_requires_question(monkeypatch):
    from backend.integrations import local_model
    async def forbidden(**kwargs):
        raise AssertionError("A blank Question must fail before HTTP")
    monkeypatch.setattr(local_model, "ask", forbidden)
    factory = NodeFactory()
    node = factory.create_node("ask_local_model_node", "generated")
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
    assert not done
    assert len(errors) == 1 and errors[0].code == "invalid_config"
    assert errors[0].retryable is False

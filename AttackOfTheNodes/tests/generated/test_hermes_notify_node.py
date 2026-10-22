"""Focused tests for generated node hermes_notify_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("hermes_notify_node")]


def test_hermes_notify_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("hermes_notify_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "hermes_notify_node")
    assert metadata["display_name"] == 'Notify me'
    assert metadata["default_alias"] == 'Notify me'
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
    assert [error["code"] for error in metadata["errors"]] == ['node_error', 'outbox_unwritable', 'unknown_destination']


@pytest.mark.asyncio
async def test_hermes_notify_node_execute_template_smoke(tmp_path, monkeypatch):
    # Never the owner's real ~/.hermes/aotn.
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    factory = NodeFactory()
    node = factory.create_node("hermes_notify_node", "generated")
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
    assert (tmp_path / "aotn" / "outbox.jsonl").is_file()

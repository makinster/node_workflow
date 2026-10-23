"""Focused tests for generated node hermes_investigation_result_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("hermes_investigation_result_node")]


def test_hermes_investigation_result_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("hermes_investigation_result_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "hermes_investigation_result_node")
    assert metadata["display_name"] == 'Investigation result'
    assert metadata["default_alias"] == 'Investigation result'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default', 'state']
    # Every declared port exposes the per-port I/O contract (handoff §4/§6):
    # data_type defaults to "any", required defaults to False.
    for direction in ("input_port_metadata", "output_port_metadata"):
        for info in metadata[direction].values():
            assert info["data_type"] in {
                "string", "number", "bool", "var", "file", "ai_session", "any",
            }
            assert isinstance(info["required"], bool)
    # Declared error codes (D7); the default generic code is always first.
    assert [error["code"] for error in metadata["errors"]] == ['node_error', 'invalid_request_id', 'request_not_found', 'record_invalid', 'inbox_busy', 'inbox_unreadable']


@pytest.mark.asyncio
async def test_hermes_investigation_result_node_execute_template_smoke(tmp_path, monkeypatch):
    factory = NodeFactory()
    node = factory.create_node("hermes_investigation_result_node", "generated")
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
    from backend import hermes_folder, hermes_investigations as inbox
    monkeypatch.setenv('HERMES_HOME', str(tmp_path/'hermes'))
    rid = inbox.enqueue(context, 'Check failed', '', 'Find a likely cause')
    node.config['input'] = rid
    await node.execute(context)
    assert not errors
    assert done
    assert done[0]['data']['default'] == 'not ready yet'

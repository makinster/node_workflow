"""Focused tests for generated node file_reader_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("file_reader_node")]


def test_file_reader_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("file_reader_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "file_reader_node")
    assert metadata["display_name"] == 'File Reader'
    assert metadata["default_alias"] == 'File Reader'
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


@pytest.mark.asyncio
async def test_file_reader_node_execute_template_smoke(tmp_path):
    factory = NodeFactory()
    node = factory.create_node("file_reader_node", "generated")
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
    path = tmp_path / "text.txt"
    path.write_text("read me", encoding="utf-8")
    node.config["file_path"] = str(path)
    await node.execute(context)
    assert not errors
    assert done[0]["data"]["default"] == "read me"

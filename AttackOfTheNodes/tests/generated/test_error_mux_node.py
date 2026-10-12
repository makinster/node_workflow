"""Focused tests for generated node error_mux_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("error_mux_node")]


def test_error_mux_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("error_mux_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "error_mux_node")
    assert metadata["display_name"] == 'Error Mux'
    assert metadata["default_alias"] == 'Error Mux'
    assert metadata["input_ports"] == ['error']
    assert metadata["output_ports"] == ['path_a', 'path_b', 'path_c']
    # Every declared port exposes the per-port I/O contract (handoff §4/§6):
    # data_type defaults to "any", required defaults to False.
    for direction in ("input_port_metadata", "output_port_metadata"):
        for info in metadata[direction].values():
            assert info["data_type"] in {
                "string", "number", "bool", "var", "file", "ai_session", "any",
            }
            assert isinstance(info["required"], bool)
    # Declared error codes (D7); the default generic code is always first.
    assert [error["code"] for error in metadata["errors"]] == ['node_error']


def _context(inputs, done, errors):
    return NodeContext(
        node_id="generated",
        branch_id="branch",
        run_id="run",
        inputs=inputs,
        memory_bank=MemoryBank(EventBus()),
        signal_done=done.append,
        signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
    )


@pytest.mark.asyncio
async def test_error_mux_node_execute_template_smoke():
    node = NodeFactory().create_node("error_mux_node", "generated")
    node.config["path_b_codes"] = "timeout, network"
    payload = {"version": 1, "code": "network", "message": "refused"}
    done, errors = [], []
    await node.execute(_context({"error": payload}, done, errors))
    assert not errors
    assert done == [{"data": {"path_b": payload}, "output_port": "path_b"}]


@pytest.mark.asyncio
async def test_error_mux_without_a_matching_path_signals_an_error():
    node = NodeFactory().create_node("error_mux_node", "generated")
    node.config["path_a_codes"] = "timeout"
    done, errors = [], []
    await node.execute(_context({"error": {"code": "http_status"}}, done, errors))
    assert errors and not done


def test_error_mux_accepts_only_listed_codes_first_path_wins():
    node = NodeFactory().create_node("error_mux_node", "generated")
    node.config.update({"path_a_codes": "timeout", "path_c_codes": "timeout,\nnode_error"})
    assert node.accepts_error_code("timeout")
    assert node.route_for_code("timeout") == "path_a"
    assert node.route_for_code("node_error") == "path_c"
    assert not node.accepts_error_code("network")
    assert not node.accepts_error_code(None)

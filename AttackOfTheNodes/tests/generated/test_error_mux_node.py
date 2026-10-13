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
    assert metadata["default_alias"] == 'Error Resolver'
    assert metadata["input_ports"] == ['input', 'error']
    assert metadata["output_ports"] == ['default', 'unmatched']
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


def _mux(*routes, **config):
    node = NodeFactory().create_node("error_mux_node", "generated")
    node.config.update(config)
    node.config["routes"] = [
        {"id": route_id, "label": route_id.title(), "codes": codes, **extra}
        for route_id, codes, *rest in routes for extra in (rest[0] if rest else {},)
    ]
    return node


@pytest.mark.asyncio
async def test_error_mux_node_execute_template_smoke():
    """No failure: the input continues on No error (default)."""
    node = _mux(("retry", ["timeout"]))
    done, errors = [], []
    await node.execute(_context({"input": "seed"}, done, errors))
    assert not errors
    assert done == [{"data": {"default": "seed"}, "output_port": "default"}]


@pytest.mark.asyncio
async def test_error_mux_routes_a_picked_error_to_its_branch():
    node = _mux(("retry", ["timeout"]), ("alert", ["timeout", "network"]))
    payload = {"version": 1, "code": "network", "message": "refused"}
    done, errors = [], []
    await node.execute(_context({"input": None, "error": payload}, done, errors))
    assert not errors
    assert done == [{"data": {"alert": payload}, "output_port": "alert"}]


@pytest.mark.asyncio
async def test_error_mux_without_a_matching_branch_signals_an_error():
    node = _mux(("retry", ["timeout"]))
    done, errors = [], []
    await node.execute(_context({"error": {"code": "http_status"}}, done, errors))
    assert errors and not done


def test_error_mux_ports_and_matching():
    node = _mux(("first", ["timeout"]), ("second", ["timeout", "node_error"]), unmatched_route=True)
    assert node.get_output_ports() == ["default", "first", "second", "unmatched"]
    assert node.route_for_code("timeout") == "first"
    assert node.route_for_code("node_error") == "second"
    assert node.route_for_code("network") == "unmatched"
    assert not node.accepts_error_code(None)


@pytest.mark.asyncio
async def test_error_mux_branch_can_pass_along_the_failed_nodes_input():
    node = _mux(("retry", ["timeout"], {"forward": "failed_input"}))
    done, errors = [], []
    inputs = {"error": {"code": "timeout"}, "failed_input": {"url": "http://x"}}
    await node.execute(_context(inputs, done, errors))
    assert not errors
    assert done == [{"data": {"retry": {"url": "http://x"}}, "output_port": "retry"}]


def test_error_mux_legacy_path_codes_migrate_to_routes():
    node = NodeFactory().create_node(
        "error_mux_node", "generated",
        {"forward": "error", "path_a_codes": "timeout", "path_b_codes": "", "path_c_codes": "network"},
    )
    assert [r["id"] for r in node.config["routes"]] == ["path_a", "path_b", "path_c"]
    assert node.route_for_code("network") == "path_c"

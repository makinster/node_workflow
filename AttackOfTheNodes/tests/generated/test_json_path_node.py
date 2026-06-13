"""Focused tests for generated node json_path_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("json_path_node")]


def test_json_path_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("json_path_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "json_path_node")
    assert metadata["display_name"] == 'JSON Path'
    assert metadata["default_alias"] == 'JSON Path'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default', 'error']


import json as _json


async def _run_json_path(json_input, path: str, default_value: str = "") -> dict:
    factory = NodeFactory()
    node = factory.create_node("json_path_node", "n1")
    node.config["path"] = path
    node.config["default_value"] = default_value
    raw = _json.dumps(json_input) if not isinstance(json_input, str) else json_input
    memory = MemoryBank(EventBus())
    done = []
    context = NodeContext(
        node_id="n1", branch_id="b", run_id="r",
        inputs={"input": raw}, memory_bank=memory,
        signal_done=done.append, signal_error=lambda e: None,
        signal_waiting_for_input=lambda p: None,
        wait_for_nodes=lambda t, timeout: None,
        wait_for_merge=lambda n, b, p, i, timeout: None,
    )
    await node.execute(context)
    return done[0]["data"]


@pytest.mark.asyncio
async def test_json_path_node_execute_template_smoke():
    factory = NodeFactory()
    node = factory.create_node("json_path_node", "generated")
    memory = MemoryBank(EventBus())
    done = []
    errors = []
    context = NodeContext(
        node_id="generated", branch_id="branch", run_id="run",
        inputs={"input": '{"key": "value"}'},
        memory_bank=memory, signal_done=done.append, signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
    )
    await node.execute(context)
    assert not errors
    assert done


@pytest.mark.asyncio
async def test_json_path_extracts_nested_value():
    data = await _run_json_path({"user": {"name": "Alice"}}, "user.name")
    assert data["default"] == "Alice"


@pytest.mark.asyncio
async def test_json_path_missing_key_returns_default():
    data = await _run_json_path({"a": 1}, "b", default_value="MISSING")
    assert data["default"] == "MISSING"


@pytest.mark.asyncio
async def test_json_path_invalid_json_routes_to_error():
    data = await _run_json_path("not json at all", "key")
    assert "error" in data
    assert "Invalid JSON" in data["error"]


@pytest.mark.asyncio
async def test_json_path_top_level_key():
    data = await _run_json_path({"count": 42}, "count")
    assert data["default"] == 42

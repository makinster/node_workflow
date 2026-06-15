"""Focused tests for generated node http_request_node."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("http_request_node")]


def test_http_request_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("http_request_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "http_request_node")
    assert metadata["display_name"] == 'HTTP Request'
    assert metadata["default_alias"] == 'HTTP Request'
    assert metadata["input_ports"] == ['input']
    assert metadata["output_ports"] == ['default', 'error']


async def _run_http(url="", method="GET", body=""):
    factory = NodeFactory()
    node = factory.create_node("http_request_node", "n1")
    node.config["url"] = url
    node.config["method"] = method
    node.config["body"] = body
    memory = MemoryBank(EventBus())
    done = []
    context = NodeContext(
        node_id="n1", branch_id="b", run_id="r",
        inputs={"input": ""}, memory_bank=memory,
        signal_done=done.append, signal_error=lambda e: None,
        signal_waiting_for_input=lambda p: None,
        wait_for_nodes=lambda t, timeout: None,
        wait_for_merge=lambda n, b, p, i, timeout: None,
    )
    await node.execute(context)
    return done[0]["data"]


@pytest.mark.asyncio
async def test_http_request_node_execute_template_smoke():
    """Empty URL routes to error port without crashing."""
    data = await _run_http(url="")
    assert "error" in data


@pytest.mark.asyncio
async def test_http_request_empty_url_signals_error():
    data = await _run_http(url="")
    assert "error" in data
    assert "URL" in data["error"] or "required" in data["error"].lower()


@pytest.mark.asyncio
async def test_http_request_mocked_get_success():
    from unittest.mock import MagicMock, patch

    mock_response = MagicMock()
    mock_response.read.return_value = b"hello world"
    mock_response.headers.get.return_value = "text/plain; charset=utf-8"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        data = await _run_http(url="http://example.com/test")

    assert data.get("default") == "hello world"


@pytest.mark.asyncio
async def test_http_request_mocked_url_error_routes_to_error_port():
    import urllib.error
    from unittest.mock import patch

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        data = await _run_http(url="http://example.com/test")

    assert "error" in data
    assert "timeout" in data["error"]

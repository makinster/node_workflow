"""Focused tests for backend/llm_provider.py — mocked transport, no network.

Run from AttackOfTheNodes/:
    python -m pytest tests/test_llm_provider.py -v
"""

import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.llm_provider import (  # noqa: E402
    DEFAULT_MODEL_ID,
    SUPPORTED_MODELS,
    AnthropicClient,
    get_client,
    supported_model_ids,
)


def _success_body(text="Hello from Claude", stop_reason="end_turn"):
    return json.dumps(
        {
            "content": [{"type": "text", "text": text}],
            "stop_reason": stop_reason,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
    )


class RecordingTransport:
    """Captures the request and returns a canned (status, body) response."""

    def __init__(self, status=200, body=None, exception=None):
        self.status = status
        self.body = body if body is not None else _success_body()
        self.exception = exception
        self.url = None
        self.payload = None
        self.headers = None
        self.timeout = None

    def __call__(self, url, body, headers, timeout):
        self.url = url
        self.payload = json.loads(body.decode("utf-8"))
        self.headers = dict(headers)
        self.timeout = timeout
        if self.exception is not None:
            raise self.exception
        return self.status, self.body


def test_supported_models_shape():
    assert DEFAULT_MODEL_ID == supported_model_ids()[0]
    for model_id, info in SUPPORTED_MODELS.items():
        assert info.model_id == model_id
        assert info.display_name


def test_complete_success():
    transport = RecordingTransport()
    client = AnthropicClient(transport=transport)
    result = client.complete(
        model=DEFAULT_MODEL_ID,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=1024,
        temperature=1.0,
        api_key="sk-test-key",
    )
    assert result.ok
    assert result.text == "Hello from Claude"
    assert result.error is None
    assert result.usage == {"input_tokens": 10, "output_tokens": 5}
    assert transport.headers["x-api-key"] == "sk-test-key"
    assert transport.payload["model"] == DEFAULT_MODEL_ID
    assert transport.payload["max_tokens"] == 1024
    assert transport.payload["messages"] == [{"role": "user", "content": "Hi"}]


def test_temperature_omitted_for_models_that_reject_it():
    transport = RecordingTransport()
    client = AnthropicClient(transport=transport)
    client.complete(
        model="claude-opus-4-8",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=64,
        temperature=0.5,
        api_key="k",
    )
    assert "temperature" not in transport.payload

    client.complete(
        model="claude-haiku-4-5",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=64,
        temperature=0.5,
        api_key="k",
    )
    assert transport.payload["temperature"] == 0.5


def test_api_error_returns_ok_false():
    body = json.dumps(
        {
            "type": "error",
            "error": {"type": "authentication_error", "message": "invalid x-api-key"},
        }
    )
    transport = RecordingTransport(status=401, body=body)
    client = AnthropicClient(transport=transport)
    result = client.complete(
        model=DEFAULT_MODEL_ID,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=64,
        temperature=1.0,
        api_key="sk-secret-value",
    )
    assert not result.ok
    assert result.text == ""
    assert "401" in result.error
    assert "authentication_error" in result.error
    # The API key must never leak into the error surface.
    assert "sk-secret-value" not in result.error


def test_network_error_returns_ok_false():
    transport = RecordingTransport(exception=urllib.error.URLError("timed out"))
    client = AnthropicClient(transport=transport)
    result = client.complete(
        model=DEFAULT_MODEL_ID,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=64,
        temperature=1.0,
        api_key="k",
    )
    assert not result.ok
    assert "Network error" in result.error


def test_refusal_stop_reason_is_an_error():
    transport = RecordingTransport(body=_success_body(text="", stop_reason="refusal"))
    client = AnthropicClient(transport=transport)
    result = client.complete(
        model=DEFAULT_MODEL_ID,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=64,
        temperature=1.0,
        api_key="k",
    )
    assert not result.ok
    assert "refusal" in result.error


def test_invalid_json_response_is_an_error():
    transport = RecordingTransport(body="<html>gateway error</html>")
    client = AnthropicClient(transport=transport)
    result = client.complete(
        model=DEFAULT_MODEL_ID,
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=64,
        temperature=1.0,
        api_key="k",
    )
    assert not result.ok
    assert "Invalid JSON" in result.error


def test_get_client_registry():
    client = get_client("anthropic")
    assert client is get_client("anthropic")
    try:
        get_client("openai")
    except ValueError as exc:
        assert "openai" in str(exc)
    else:
        raise AssertionError("unknown provider should raise ValueError")

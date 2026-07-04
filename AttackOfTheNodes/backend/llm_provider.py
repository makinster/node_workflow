"""
LLM provider clients for AI nodes.

Backend-only module: nodes call get_client(provider) and complete(); the
frontend never imports this file. The curated model list (SUPPORTED_MODELS)
reaches the frontend only through node config_schema options exposed via
NodeFactory.get_node_types_metadata().

V1 uses raw HTTPS through urllib (same stdlib path as http_request_node) —
no SDK dependency. One POST to the Anthropic Messages API per completion,
single attempt, explicit timeout. The API key is sent in a header and must
never appear in logs or error strings.
"""

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class ModelInfo:
    """One curated model entry.

    supports_temperature: Opus 4.8 / Sonnet 5 reject sampling parameters
    with a 400; the client omits temperature from the request body for
    models where this is False.
    """

    model_id: str
    display_name: str
    supports_temperature: bool = True


# The single curated model list (verified against Anthropic docs 2026-07-04).
# Dict order defines dropdown order; the first entry is the config default.
SUPPORTED_MODELS: Dict[str, ModelInfo] = {
    "claude-opus-4-8": ModelInfo(
        "claude-opus-4-8", "Claude Opus 4.8", supports_temperature=False
    ),
    "claude-sonnet-5": ModelInfo(
        "claude-sonnet-5", "Claude Sonnet 5", supports_temperature=False
    ),
    "claude-sonnet-4-6": ModelInfo("claude-sonnet-4-6", "Claude Sonnet 4.6"),
    "claude-haiku-4-5": ModelInfo("claude-haiku-4-5", "Claude Haiku 4.5"),
}

DEFAULT_MODEL_ID = next(iter(SUPPORTED_MODELS))


def supported_model_ids() -> List[str]:
    """Model IDs in dropdown order."""
    return list(SUPPORTED_MODELS)


@dataclass
class CompletionResult:
    """Outcome of one completion call. ok=False carries a user-safe error."""

    text: str
    ok: bool
    error: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)


# transport(url, body_bytes, headers, timeout) -> (status_code, response_text)
Transport = Callable[[str, bytes, Dict[str, str], float], Tuple[int, str]]


def _http_transport(
    url: str, body: bytes, headers: Dict[str, str], timeout: float
) -> Tuple[int, str]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # Non-2xx still carries a JSON error body worth parsing.
        return exc.code, exc.read().decode("utf-8", errors="replace")


class AnthropicClient:
    """Minimal Anthropic Messages API client (single attempt, no retries)."""

    def __init__(
        self,
        transport: Optional[Transport] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._transport = transport or _http_transport
        self._timeout = timeout

    def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        api_key: str,
    ) -> CompletionResult:
        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": int(max_tokens),
            "messages": messages,
        }
        info = SUPPORTED_MODELS.get(model)
        if info is not None and info.supports_temperature:
            payload["temperature"] = float(temperature)

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
        body = json.dumps(payload).encode("utf-8")

        try:
            status, response_text = self._transport(
                ANTHROPIC_API_URL, body, headers, self._timeout
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", None) or exc
            return CompletionResult(text="", ok=False, error=f"Network error: {reason}")

        if status < 200 or status >= 300:
            return CompletionResult(
                text="", ok=False, error=_api_error_message(status, response_text)
            )

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return CompletionResult(
                text="", ok=False, error="Invalid JSON in API response"
            )

        stop_reason = data.get("stop_reason")
        if stop_reason == "refusal":
            return CompletionResult(
                text="", ok=False, error="Request declined by the model (refusal)"
            )

        text = "\n".join(
            block.get("text", "")
            for block in data.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        )
        return CompletionResult(text=text, ok=True, usage=data.get("usage") or {})


def _api_error_message(status: int, response_text: str) -> str:
    """Condense an API error body into one user-safe line."""
    try:
        error = json.loads(response_text).get("error") or {}
        detail = error.get("message") or ""
        kind = error.get("type") or "api_error"
    except (json.JSONDecodeError, AttributeError):
        detail, kind = "", "api_error"
    message = f"API error {status} ({kind})"
    if detail:
        message += f": {detail}"
    return message


_CLIENTS: Dict[str, AnthropicClient] = {}


def get_client(provider: str = "anthropic") -> AnthropicClient:
    """Provider seam: a second provider later is a new registry entry here."""
    if provider != "anthropic":
        raise ValueError(f"Unknown LLM provider: {provider}")
    if provider not in _CLIENTS:
        _CLIENTS[provider] = AnthropicClient()
    return _CLIENTS[provider]

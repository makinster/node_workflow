"""Focused tests for ChatCompletionNode real execution and AI sessions.

Run from AttackOfTheNodes/:
    python -m pytest tests/test_chat_completion_node.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest  # noqa: E402

from backend.event_bus import EventBus  # noqa: E402
from backend.llm_provider import CompletionResult  # noqa: E402
from backend.memory_bank import MemoryBank  # noqa: E402
from backend.node_base import NodeContext  # noqa: E402
from backend.nodes.chat_completion_node import ChatCompletionNode  # noqa: E402
from backend.run_session import RunSession  # noqa: E402


class FakeClient:
    """Records complete() calls and returns queued results."""

    def __init__(self, results=None):
        self.calls = []
        self.results = list(results or [])

    def complete(self, model, messages, max_tokens, temperature, api_key):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "api_key": api_key,
            }
        )
        if self.results:
            return self.results.pop(0)
        return CompletionResult(text="mock response", ok=True, usage={})


class FakeSecrets:
    def __init__(self, secrets=None):
        self._secrets = dict(secrets or {})

    def get_secret(self, key):
        return self._secrets.get(key)


def _make_node(**config_overrides):
    config = dict(ChatCompletionNode.default_config)
    config.update(
        {
            "prompt_source": "Configured",
            "prompt": "Summarize this",
            "api_key_secret": "anthropic_key",
        }
    )
    config.update(config_overrides)
    return ChatCompletionNode("chat-1", config)


def _make_context(inputs=None, memory_bank=None, run_session=None, secrets=None):
    bus = EventBus()
    signals = {}

    async def _unused_wait(prompt):
        raise AssertionError("unused")

    async def _unused_wait_nodes(node_ids, timeout):
        raise AssertionError("unused")

    async def _unused_wait_merge(a, b, c, d, e):
        raise AssertionError("unused")

    context = NodeContext(
        node_id="chat-1",
        branch_id="branch-1",
        run_id="run-1",
        inputs=dict(inputs or {}),
        memory_bank=memory_bank or MemoryBank(bus),
        signal_done=lambda payload: signals.__setitem__("done", payload),
        signal_error=lambda exc: signals.__setitem__("error", exc),
        signal_waiting_for_input=_unused_wait,
        wait_for_nodes=_unused_wait_nodes,
        wait_for_merge=_unused_wait_merge,
        run_session=run_session if run_session is not None else RunSession("run-1"),
        secrets_manager=secrets
        if secrets is not None
        else FakeSecrets({"anthropic_key": "sk-test"}),
    )
    return context, signals


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(
        "backend.nodes.chat_completion_node.get_client", lambda provider="anthropic": client
    )


async def test_success_writes_vault_and_forwards_dead_drop(monkeypatch):
    client = FakeClient()
    _patch_client(monkeypatch, client)
    node = _make_node(vault_write=True, vault_write_key="llm_result")
    context, signals = _make_context(inputs={"document": "the doc payload"})

    await node.execute(context)

    assert "error" not in signals
    # Default routing: dead-drop passthrough forwards the incoming payload.
    assert signals["done"]["data"]["default"] == "the doc payload"
    assert context.memory_bank.read_persistent("llm_result") == "mock response"
    # The document rides along in the user turn.
    assert client.calls[0]["messages"] == [
        {"role": "user", "content": "Summarize this\n\nthe doc payload"}
    ]
    assert client.calls[0]["api_key"] == "sk-test"


async def test_transient_output_sends_result_downstream(monkeypatch):
    _patch_client(monkeypatch, FakeClient())
    node = _make_node(transient_output=True, dead_drop_passthrough=False, vault_write=False)
    context, signals = _make_context()

    await node.execute(context)

    assert signals["done"]["data"]["default"] == "mock response"


async def test_failure_signals_error_and_skips_vault_write(monkeypatch):
    failing = FakeClient(results=[CompletionResult(text="", ok=False, error="API error 500")])
    _patch_client(monkeypatch, failing)
    node = _make_node(vault_write=True, vault_write_key="llm_result")
    context, signals = _make_context()

    await node.execute(context)

    assert "done" not in signals
    assert "API error 500" in str(signals["error"])
    assert context.memory_bank.read_persistent("llm_result") is None


async def test_missing_secret_fails_safely(monkeypatch):
    client = FakeClient()
    _patch_client(monkeypatch, client)
    node = _make_node()
    context, signals = _make_context(secrets=FakeSecrets({}))

    await node.execute(context)

    assert "done" not in signals
    assert "anthropic_key" in str(signals["error"])
    assert client.calls == []


async def test_empty_prompt_fails_safely(monkeypatch):
    client = FakeClient()
    _patch_client(monkeypatch, client)
    node = _make_node(prompt="")
    context, signals = _make_context()

    await node.execute(context)

    assert "done" not in signals
    assert "Prompt" in str(signals["error"])
    assert client.calls == []


async def test_vault_prompt_source(monkeypatch):
    client = FakeClient()
    _patch_client(monkeypatch, client)
    node = _make_node(prompt_source="Vault", prompt_vault_key="stored_prompt", prompt="")
    context, signals = _make_context()
    context.memory_bank.store_persistent("stored_prompt", "prompt from vault")

    await node.execute(context)

    assert "error" not in signals
    assert client.calls[0]["messages"][0]["content"] == "prompt from vault"


async def test_session_shared_across_nodes(monkeypatch):
    client = FakeClient(
        results=[
            CompletionResult(text="first answer", ok=True),
            CompletionResult(text="second answer", ok=True),
        ]
    )
    _patch_client(monkeypatch, client)
    run_session = RunSession("run-1")
    bus = EventBus()
    memory_bank = MemoryBank(bus)

    node_a = _make_node(use_chat_session=True, session_key="research", prompt="First question")
    ctx_a, sig_a = _make_context(memory_bank=memory_bank, run_session=run_session)
    await node_a.execute(ctx_a)
    assert "error" not in sig_a

    node_b = _make_node(use_chat_session=True, session_key="research", prompt="Follow-up")
    ctx_b, sig_b = _make_context(memory_bank=memory_bank, run_session=run_session)
    await node_b.execute(ctx_b)
    assert "error" not in sig_b

    # Second call carried the first exchange as history.
    assert client.calls[1]["messages"] == [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "Follow-up"},
    ]
    # Vault holds only the typed reference, tagged ai_session.
    entry = memory_bank.read_persistent("research")
    assert entry == {"type": "ai_session", "ref_key": "research"}
    assert memory_bank.read_persistent_by_type("ai_session") == {"research": entry}
    # History lives in RunSession.
    assert len(run_session.get_chat_history("research")) == 4


async def test_sessions_with_different_keys_are_isolated(monkeypatch):
    _patch_client(monkeypatch, FakeClient())
    run_session = RunSession("run-1")
    bus = EventBus()
    memory_bank = MemoryBank(bus)

    node_a = _make_node(use_chat_session=True, session_key="alpha")
    ctx_a, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await node_a.execute(ctx_a)

    node_b = _make_node(use_chat_session=True, session_key="beta", prompt="Other topic")
    ctx_b, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await node_b.execute(ctx_b)

    assert len(run_session.get_chat_history("alpha")) == 2
    assert len(run_session.get_chat_history("beta")) == 2
    beta_history = run_session.get_chat_history("beta")
    assert beta_history[0]["content"] == "Other topic"


async def test_failed_call_leaves_history_untouched(monkeypatch):
    client = FakeClient(
        results=[
            CompletionResult(text="ok", ok=True),
            CompletionResult(text="", ok=False, error="rate limited"),
        ]
    )
    _patch_client(monkeypatch, client)
    run_session = RunSession("run-1")
    bus = EventBus()
    memory_bank = MemoryBank(bus)

    node = _make_node(use_chat_session=True, session_key="chat")
    ctx, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await node.execute(ctx)
    assert len(run_session.get_chat_history("chat")) == 2

    node2 = _make_node(use_chat_session=True, session_key="chat", prompt="Again")
    ctx2, sig2 = _make_context(memory_bank=memory_bank, run_session=run_session)
    await node2.execute(ctx2)

    assert "error" in sig2
    assert len(run_session.get_chat_history("chat")) == 2


async def test_continue_session_mode_with_document_turn(monkeypatch):
    client = FakeClient(
        results=[
            CompletionResult(text="seeded answer", ok=True),
            CompletionResult(text="continued answer", ok=True),
        ]
    )
    _patch_client(monkeypatch, client)
    run_session = RunSession("run-1")
    bus = EventBus()
    memory_bank = MemoryBank(bus)

    seeder = _make_node(use_chat_session=True, session_key="thread", prompt="Seed turn")
    ctx1, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await seeder.execute(ctx1)

    # Continue AI session prompt-source mode: no prompt; the document (here an
    # upstream payload) becomes the next turn; the continued history is read
    # but NOT extended (keep-active checkbox off).
    continuer = _make_node(
        prompt_source="Continue AI session",
        continue_session_key="thread",
        document_source="Upstream payload",
        prompt="",
    )
    ctx2, sig2 = _make_context(
        inputs={"document": "next question"},
        memory_bank=memory_bank,
        run_session=run_session,
    )
    await continuer.execute(ctx2)

    assert "error" not in sig2
    assert client.calls[1]["messages"][0]["content"] == "Seed turn"
    assert client.calls[1]["messages"][-1]["content"] == "next question"
    assert len(run_session.get_chat_history("thread")) == 2


async def test_continue_session_mode_requires_document(monkeypatch):
    client = FakeClient(results=[CompletionResult(text="seeded answer", ok=True)])
    _patch_client(monkeypatch, client)
    run_session = RunSession("run-1")
    bus = EventBus()
    memory_bank = MemoryBank(bus)

    seeder = _make_node(use_chat_session=True, session_key="thread", prompt="Seed turn")
    ctx1, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await seeder.execute(ctx1)

    # Continue mode with no document text: fail loudly instead of sending a
    # bare nudge that produces responses unrelated to the user's intent.
    continuer = _make_node(
        prompt_source="Continue AI session",
        continue_session_key="thread",
        document_source="Configured",
        document="",
        prompt="",
    )
    ctx2, sig2 = _make_context(memory_bank=memory_bank, run_session=run_session)
    await continuer.execute(ctx2)

    assert "done" not in sig2
    assert "Document" in str(sig2["error"])
    assert len(client.calls) == 1  # no second call made


async def test_continue_session_reuse_extends_resumed_session(monkeypatch):
    client = FakeClient(
        results=[
            CompletionResult(text="seed answer", ok=True),
            CompletionResult(text="continued answer", ok=True),
        ]
    )
    _patch_client(monkeypatch, client)
    run_session = RunSession("run-1")
    bus = EventBus()
    memory_bank = MemoryBank(bus)

    seeder = _make_node(use_chat_session=True, session_key="thread", prompt="Seed turn")
    ctx1, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await seeder.execute(ctx1)

    # Continue "thread" AND keep the session active: the same session is
    # extended in place — no separate onward key.
    continuer = _make_node(
        prompt_source="Continue AI session",
        continue_session_key="thread",
        document_source="Configured",
        document="Follow-up question",
        use_chat_session=True,
        prompt="",
    )
    ctx2, sig2 = _make_context(memory_bank=memory_bank, run_session=run_session)
    await continuer.execute(ctx2)

    assert "error" not in sig2
    # The resumed history (seed exchange) plus the new document turn was sent.
    assert client.calls[1]["messages"] == [
        {"role": "user", "content": "Seed turn"},
        {"role": "assistant", "content": "seed answer"},
        {"role": "user", "content": "Follow-up question"},
    ]
    # The resumed session was extended in place: 4 turns, no forked copy.
    assert len(run_session.get_chat_history("thread")) == 4


async def test_continue_session_mode_requires_existing_history(monkeypatch):
    client = FakeClient()
    _patch_client(monkeypatch, client)
    node = _make_node(
        prompt_source="Continue AI session",
        continue_session_key="ghost",
        prompt="",
    )
    context, signals = _make_context()

    await node.execute(context)

    assert "done" not in signals
    assert "ghost" in str(signals["error"])
    assert client.calls == []

    # And with no session selected at all, fail before any network call.
    node2 = _make_node(prompt_source="Continue AI session", prompt="")
    ctx2, sig2 = _make_context()
    await node2.execute(ctx2)
    assert "done" not in sig2
    assert "Select an AI session" in str(sig2["error"])


async def test_normal_mode_seeds_new_session_key_from_history(monkeypatch):
    """Non-continue mode with its own new session key seeds from any prior
    turns in that key (fresh key stays empty until this node writes)."""
    client = FakeClient(
        results=[
            CompletionResult(text="a1", ok=True),
            CompletionResult(text="b1", ok=True),
        ]
    )
    _patch_client(monkeypatch, client)
    run_session = RunSession("run-1")
    bus = EventBus()
    memory_bank = MemoryBank(bus)

    first = _make_node(use_chat_session=True, session_key="alpha", prompt="Turn one")
    ctx1, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await first.execute(ctx1)

    second = _make_node(use_chat_session=True, session_key="alpha", prompt="Turn two")
    ctx2, _ = _make_context(memory_bank=memory_bank, run_session=run_session)
    await second.execute(ctx2)

    history = run_session.get_chat_history("alpha")
    assert [m["content"] for m in history] == [
        "Turn one",
        "a1",
        "Turn two",
        "b1",
    ]


async def test_model_and_parameters_forwarded(monkeypatch):
    client = FakeClient()
    _patch_client(monkeypatch, client)
    node = _make_node(model="claude-haiku-4-5", max_tokens=256, temperature=0.3)
    context, _ = _make_context()

    await node.execute(context)

    call = client.calls[0]
    assert call["model"] == "claude-haiku-4-5"
    assert call["max_tokens"] == 256
    assert call["temperature"] == pytest.approx(0.3)

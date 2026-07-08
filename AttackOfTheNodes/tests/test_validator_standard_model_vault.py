"""Validator derivation of vault declarations from standard-model config.

Nodes using the standard source/routing model (vault_write_key, session_key,
<port>_vault_key, continue_session_key) no longer edit membank_inputs/outputs
in the config UI; the validator derives the equivalent declarations so the
existence / ai_session-mismatch / parallel-race checks keep working.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_validator_standard_model_vault.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.validator import validate_workflow  # noqa: E402


def _make_wm():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    return WorkflowMap(factory, bus), factory


def _chat_config(wm, node_id, **overrides):
    config = dict(wm.get_node_data(node_id)["config"])
    config["api_key_secret"] = "anthropic_key"
    config.update(overrides)
    wm.update_node_config(node_id, config)


def _messages(items):
    return [entry["message"] for entry in items]


def test_session_write_satisfies_continuation_read():
    wm, factory = _make_wm()
    wm.create_new("std_session_chain")
    start = wm.add_node("start_node")
    first = wm.add_node("chat_completion_node")
    second = wm.add_node("chat_completion_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", first, "prompt")
    wm.connect(first, "default", second, "prompt")
    wm.connect(second, "default", end, "input")

    _chat_config(wm, first, use_chat_session=True, session_key="research")
    _chat_config(wm, second, prompt_source="Continue AI session", continue_session_key="research")

    result = validate_workflow(wm, factory)
    assert result["success"] is True, _messages(result["errors"])
    assert not any("research" in m for m in _messages(result["warnings"])), (
        result["warnings"]
    )
    print("test_session_write_satisfies_continuation_read PASSED")


def test_undeclared_continuation_key_is_an_error():
    wm, factory = _make_wm()
    wm.create_new("std_session_undeclared")
    start = wm.add_node("start_node")
    node = wm.add_node("chat_completion_node")
    wm.connect(start, "default", node, "prompt")
    _chat_config(wm, node, prompt_source="Continue AI session", continue_session_key="ghost_session")

    result = validate_workflow(wm, factory)
    assert result["success"] is False
    assert any(
        "Membank input source not declared: ghost_session" in m
        for m in _messages(result["errors"])
    ), _messages(result["errors"])
    print("test_undeclared_continuation_key_is_an_error PASSED")


def test_untyped_writer_triggers_ai_session_mismatch_warning():
    wm, factory = _make_wm()
    wm.create_new("std_session_mismatch")
    start = wm.add_node("start_node")
    setter = wm.add_node("set_variable_node")
    chat = wm.add_node("chat_completion_node")
    wm.connect(start, "default", setter, "input")
    wm.connect(setter, "default", chat, "prompt")

    wm.update_node_config(setter, {"membank_outputs": [{"id": "not_a_session"}]})
    _chat_config(wm, chat, prompt_source="Continue AI session", continue_session_key="not_a_session")

    result = validate_workflow(wm, factory)
    assert result["success"] is True, _messages(result["errors"])
    assert any(
        "read as ai_session" in m and "not_a_session" in m
        for m in _messages(result["warnings"])
    ), result["warnings"]
    print("test_untyped_writer_triggers_ai_session_mismatch_warning PASSED")


def test_vault_prompt_read_checked_for_existence():
    wm, factory = _make_wm()
    wm.create_new("std_prompt_vault")
    start = wm.add_node("start_node")
    setter = wm.add_node("set_variable_node")
    chat = wm.add_node("chat_completion_node")
    wm.connect(start, "default", setter, "input")
    wm.connect(setter, "default", chat, "prompt")

    wm.update_node_config(setter, {"membank_outputs": [{"id": "stored_prompt"}]})
    _chat_config(
        wm, chat, prompt_source="Vault", prompt_vault_key="stored_prompt", prompt=""
    )
    result = validate_workflow(wm, factory)
    assert result["success"] is True, _messages(result["errors"])

    # Now point the read at a key nobody declares.
    _chat_config(
        wm, chat, prompt_source="Vault", prompt_vault_key="missing_key", prompt=""
    )
    result = validate_workflow(wm, factory)
    assert result["success"] is False
    assert any(
        "Membank input source not declared: missing_key" in m
        for m in _messages(result["errors"])
    ), _messages(result["errors"])
    print("test_vault_prompt_read_checked_for_existence PASSED")


def test_standard_vault_write_satisfies_legacy_reader():
    wm, factory = _make_wm()
    wm.create_new("std_write_legacy_read")
    start = wm.add_node("start_node")
    chat = wm.add_node("chat_completion_node")
    reader = wm.add_node("get_variable_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", chat, "prompt")
    wm.connect(chat, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    _chat_config(wm, chat, vault_write=True, vault_write_key="llm_result")
    wm.update_node_config(reader, {"membank_inputs": [{"id": "llm_result"}]})

    result = validate_workflow(wm, factory)
    assert result["success"] is True, _messages(result["errors"])
    print("test_standard_vault_write_satisfies_legacy_reader PASSED")


def test_parallel_session_writer_triggers_race_warning():
    wm, factory = _make_wm()
    wm.create_new("std_session_race")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    writer = wm.add_node("chat_completion_node")
    reader = wm.add_node("chat_completion_node")
    end_a = wm.add_node("end_node")
    end_b = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", writer, "prompt")
    wm.connect(branch, "path_b", reader, "prompt")
    wm.connect(writer, "default", end_a, "input")
    wm.connect(reader, "default", end_b, "input")

    _chat_config(wm, writer, use_chat_session=True, session_key="shared_chat")
    _chat_config(wm, reader, prompt_source="Continue AI session", continue_session_key="shared_chat")

    result = validate_workflow(wm, factory)
    assert result["success"] is True, _messages(result["errors"])
    assert any(
        "parallel branches" in m and "shared_chat" in m
        for m in _messages(result["warnings"])
    ), result["warnings"]
    print("test_parallel_session_writer_triggers_race_warning PASSED")

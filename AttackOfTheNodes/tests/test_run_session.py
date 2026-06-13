"""Focused tests for the per-run RunSession resource lifecycle.

Run from AttackOfTheNodes/:
    python -m pytest tests/test_run_session.py -v
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.run_session import RunSession  # noqa: E402


def _make_services():
    """Construct a fresh set of backend services for one test run."""
    from backend.configuration_manager import ConfigurationManager
    from backend.event_bus import EventBus
    from backend.master_state import MasterState
    from backend.memory_bank import MemoryBank
    from backend.node_factory import NodeFactory
    from backend.output_manager import OutputManager
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    memory_bank = MemoryBank(bus)
    master = MasterState(
        workflow_map,
        memory_bank,
        bus,
        output_manager=OutputManager(),
        configuration_manager=ConfigurationManager(),
    )
    return master, workflow_map, memory_bank, bus


# ---------------------------------------------------------------------------
# RunSession unit behavior
# ---------------------------------------------------------------------------

def test_open_file_caches_handle_per_path_and_mode(tmp_path):
    target = tmp_path / "input.txt"
    target.write_text("hello", encoding="utf-8")

    session = RunSession("run_test")
    first = session.open_file(str(target), mode="r")
    second = session.open_file(str(target), mode="r")
    assert first is second, "Same path+mode must reuse the cached handle"
    assert first.read() == "hello"
    session.close_all()
    assert first.closed


def test_close_all_closes_everything_and_blocks_reuse(tmp_path):
    target = tmp_path / "input.txt"
    target.write_text("data", encoding="utf-8")

    session = RunSession("run_test")
    handle = session.open_file(str(target), mode="r")

    closed_flags = []
    session.register_resource(
        "listener", object(), close=lambda _h: closed_flags.append(True)
    )

    session.close_all()
    assert handle.closed
    assert closed_flags == [True], "Registered close hook must run"
    assert session.is_closed
    assert session.get_resource("listener") is None

    # Idempotent: a second close is a no-op
    session.close_all()

    with pytest.raises(RuntimeError):
        session.open_file(str(target), mode="r")
    with pytest.raises(RuntimeError):
        session.register_resource("x", object())


def test_open_file_reopens_externally_closed_handle(tmp_path):
    target = tmp_path / "input.txt"
    target.write_text("contents", encoding="utf-8")

    session = RunSession("run_test")
    first = session.open_file(str(target), mode="r")
    first.close()

    second = session.open_file(str(target), mode="r")
    assert second is not first, "A closed cached handle must be replaced"
    assert second.read() == "contents"
    session.close_all()
    assert second.closed


def test_register_and_get_resource():
    session = RunSession("run_test")
    marker = object()
    session.register_resource("browser", marker)
    assert session.get_resource("browser") is marker
    assert session.get_resource("missing") is None
    session.close_all()


def test_validate_path(tmp_path):
    target = tmp_path / "exists.txt"
    target.write_text("x", encoding="utf-8")

    session = RunSession("run_test")
    ok, reason = session.validate_path(str(target))
    assert ok and reason == ""

    ok, reason = session.validate_path(str(tmp_path / "missing.txt"))
    assert not ok and "not found" in reason.lower()

    ok, reason = session.validate_path("   ")
    assert not ok and "empty" in reason.lower()
    session.close_all()


# ---------------------------------------------------------------------------
# Run lifecycle: created at run start, used by nodes, closed at finalization
# ---------------------------------------------------------------------------

def test_run_session_lifecycle_through_workflow(tmp_path):
    asyncio.run(_test_run_session_lifecycle_through_workflow(tmp_path))


async def _test_run_session_lifecycle_through_workflow(tmp_path):
    target = tmp_path / "workflow_input.txt"
    target.write_text("file contents from disk", encoding="utf-8")

    master, wm, mb, _ = _make_services()
    wm.create_new("test_run_session")
    start = wm.add_node("start_node")
    reader = wm.add_node("file_reader_node")
    end = wm.add_node("end_node")

    wm.update_node_config(reader, {"file_path": str(target)})
    wm.connect(start, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    await master.start_workflow()
    session = master._run_session
    assert session is not None
    assert session.run_id == master.current_run_id
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    assert session.is_closed, "Session must be closed once the run is recorded"
    assert mb.read_transient(reader, "default") == "file contents from disk"


def test_two_readers_share_cached_handle_and_both_get_contents(tmp_path):
    asyncio.run(_test_two_readers_share_cached_handle(tmp_path))


async def _test_two_readers_share_cached_handle(tmp_path):
    target = tmp_path / "shared.txt"
    target.write_text("shared file body", encoding="utf-8")

    master, wm, mb, _ = _make_services()
    wm.create_new("test_shared_handle")
    start = wm.add_node("start_node")
    reader1 = wm.add_node("file_reader_node")
    reader2 = wm.add_node("file_reader_node")
    end = wm.add_node("end_node")

    wm.update_node_config(reader1, {"file_path": str(target)})
    wm.update_node_config(reader2, {"file_path": str(target)})
    wm.connect(start, "default", reader1, "input")
    wm.connect(reader1, "default", reader2, "input")
    wm.connect(reader2, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    # The second reader reuses the cached handle; seek(0) must make the
    # full contents readable again instead of returning an empty string.
    assert mb.read_transient(reader1, "default") == "shared file body"
    assert mb.read_transient(reader2, "default") == "shared file body"


def test_back_to_back_runs_get_fresh_sessions(tmp_path):
    asyncio.run(_test_back_to_back_runs_get_fresh_sessions(tmp_path))


async def _test_back_to_back_runs_get_fresh_sessions(tmp_path):
    target = tmp_path / "rerun.txt"
    target.write_text("first body", encoding="utf-8")

    master, wm, mb, _ = _make_services()
    wm.create_new("test_rerun")
    start = wm.add_node("start_node")
    reader = wm.add_node("file_reader_node")
    end = wm.add_node("end_node")
    wm.update_node_config(reader, {"file_path": str(target)})
    wm.connect(start, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    await master.start_workflow()
    first_session = master._run_session
    await master.wait_for_completion()
    assert master.state.value == "FINISHED"
    assert first_session.is_closed

    # Second run must build a new session and re-read current file contents.
    target.write_text("second body", encoding="utf-8")
    await master.start_workflow()
    second_session = master._run_session
    assert second_session is not first_session
    assert second_session.run_id == master.current_run_id
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    assert second_session.is_closed
    assert mb.read_transient(reader, "default") == "second body"


def test_run_session_closed_on_error_termination(tmp_path):
    asyncio.run(_test_run_session_closed_on_error_termination(tmp_path))


async def _test_run_session_closed_on_error_termination(tmp_path):
    master, wm, _, bus = _make_services()
    wm.create_new("test_run_session_error")
    start = wm.add_node("start_node")
    err = wm.add_node("error_node")
    wm.connect(start, "default", err, "input")

    from backend.events import RECOVERY_OPTIONS_AVAILABLE

    def terminate(payload):
        master.submit_recovery_action(payload["branch_id"], "TERMINATE_WORKFLOW")

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, terminate)

    await master.start_workflow()
    session = master._run_session
    assert session is not None
    await master.wait_for_completion()

    assert master.state.value == "ERROR"
    assert session.is_closed, "Session must be closed when the run terminates"


# ---------------------------------------------------------------------------
# Validator: file path_hint fields
# ---------------------------------------------------------------------------

def test_validator_flags_missing_and_unfound_file_paths(tmp_path):
    from backend.node_factory import NodeFactory
    from backend.validator import validate_workflow

    master, wm, _, _ = _make_services()
    factory = NodeFactory()
    wm.create_new("test_file_validation")
    start = wm.add_node("start_node")
    reader = wm.add_node("file_reader_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    # Empty required file path -> error
    result = validate_workflow(wm, factory)
    assert any(
        e["node_id"] == reader and "file path" in e["message"].lower()
        for e in result["errors"]
    ), f"Expected missing-file-path error, got {result['errors']}"

    # Path set but not on disk -> warning, not error
    wm.update_node_config(reader, {"file_path": str(tmp_path / "nope.txt")})
    result = validate_workflow(wm, factory)
    assert not any(
        e["node_id"] == reader and "file path" in e["message"].lower()
        for e in result["errors"]
    )
    assert any(
        w["node_id"] == reader and "not found" in w["message"].lower()
        for w in result["warnings"]
    ), f"Expected not-found warning, got {result['warnings']}"

    # Existing path -> clean
    target = tmp_path / "real.txt"
    target.write_text("x", encoding="utf-8")
    wm.update_node_config(reader, {"file_path": str(target)})
    result = validate_workflow(wm, factory)
    assert not any(w["node_id"] == reader for w in result["warnings"])
    assert result["success"], f"Expected success, got {result['errors']}"


# ---------------------------------------------------------------------------
# Chat session tests
# ---------------------------------------------------------------------------


def test_chat_session_created_on_first_access():
    session = RunSession("r1")
    history = session.get_or_create_chat_session("conv_a")
    assert history == []


def test_chat_session_reused_by_key():
    session = RunSession("r1")
    session.append_chat_message("conv_a", "user", "hello")
    history = session.get_or_create_chat_session("conv_a")
    assert len(history) == 1
    assert history[0]["content"] == "hello"


def test_chat_history_returns_copy():
    session = RunSession("r1")
    session.append_chat_message("conv_a", "user", "hello")
    copy = session.get_chat_history("conv_a")
    copy[0]["role"] = "MUTATED"
    assert session.get_chat_history("conv_a")[0]["role"] == "user"


def test_chat_sessions_are_independent():
    session = RunSession("r1")
    session.append_chat_message("conv_a", "user", "from a")
    session.append_chat_message("conv_b", "user", "from b")
    assert len(session.get_chat_history("conv_a")) == 1
    assert session.get_chat_history("conv_a")[0]["content"] == "from a"
    assert len(session.get_chat_history("conv_b")) == 1
    assert session.get_chat_history("conv_b")[0]["content"] == "from b"


def test_chat_session_accumulates_messages():
    session = RunSession("r1")
    session.append_chat_message("conv_a", "user", "hi")
    session.append_chat_message("conv_a", "assistant", "hello")
    session.append_chat_message("conv_a", "user", "bye")
    history = session.get_chat_history("conv_a")
    assert len(history) == 3
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[2]["content"] == "bye"


def test_close_all_clears_chat_sessions():
    session = RunSession("r1")
    session.append_chat_message("conv_a", "user", "hi")
    session.close_all()
    assert session.get_chat_history("conv_a") == []


def test_get_chat_history_returns_empty_list_for_unknown_key():
    session = RunSession("r1")
    assert session.get_chat_history("no_such_key") == []


def test_validator_warns_missing_session_key():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.validator import validate_workflow
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    wm = WorkflowMap(factory, bus)
    wm.create_new("chat_session_key_check")
    start = wm.add_node("start_node")
    node = wm.add_node("echo_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", node, "input")
    wm.connect(node, "default", end, "input")

    # use_chat_session with empty key → warning
    wm.update_node_config(node, {"use_chat_session": True, "session_key": ""})
    result = validate_workflow(wm, factory)
    assert result["success"] is True
    assert any(
        "session_key" in w["message"] for w in result["warnings"]
    ), f"Expected session_key warning, got: {result['warnings']}"

    # With a key → no warning
    wm.update_node_config(node, {"use_chat_session": True, "session_key": "my_key"})
    result2 = validate_workflow(wm, factory)
    assert not any(
        "session_key" in w["message"] for w in result2["warnings"]
    ), f"Unexpected warning: {result2['warnings']}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

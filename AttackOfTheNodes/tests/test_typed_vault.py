"""Tests for typed vault entries in MemoryBank and related validator warnings.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_typed_vault.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_bank():
    from backend.event_bus import EventBus
    from backend.memory_bank import MemoryBank

    return MemoryBank(EventBus())


def _make_wm():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    return WorkflowMap(factory, bus), factory


def test_store_and_read_typed_entry():
    bank = _make_bank()
    obj = {"messages": [{"role": "user", "content": "hello"}]}
    bank.store_persistent("session", obj, type_tag="ai_session")

    assert bank.read_persistent("session") is obj
    assert bank.read_persistent_by_type("ai_session") == {"session": obj}

    print("test_store_and_read_typed_entry PASSED")


def test_untyped_entry_excluded_from_typed_read():
    bank = _make_bank()
    bank.store_persistent("plain", "x")
    assert bank.read_persistent_by_type("ai_session") == {}
    assert bank.read_persistent_by_type("string") == {}

    print("test_untyped_entry_excluded_from_typed_read PASSED")


def test_multiple_types_filtered_independently():
    bank = _make_bank()
    bank.store_persistent("s1", "hello", type_tag="string")
    bank.store_persistent("n1", 42, type_tag="number")
    bank.store_persistent("a1", {}, type_tag="ai_session")
    bank.store_persistent("plain", True)

    assert bank.read_persistent_by_type("string") == {"s1": "hello"}
    assert bank.read_persistent_by_type("number") == {"n1": 42}
    assert bank.read_persistent_by_type("ai_session") == {"a1": {}}
    assert bank.read_persistent_by_type("file") == {}

    print("test_multiple_types_filtered_independently PASSED")


def test_typed_vault_round_trips_through_state():
    bank = _make_bank()
    bank.store_persistent("k1", "v1", type_tag="string")
    bank.store_persistent("k2", 99, type_tag="number")
    bank.store_persistent("k3", "untyped")

    snapshot = bank.get_state()

    bank2 = _make_bank()
    bank2.load_state(snapshot)

    assert bank2.read_persistent("k1") == "v1"
    assert bank2.read_persistent_by_type("string") == {"k1": "v1"}
    assert bank2.read_persistent_by_type("number") == {"k2": 99}
    assert bank2.read_persistent_by_type("ai_session") == {}

    print("test_typed_vault_round_trips_through_state PASSED")


def test_load_state_without_type_tags_is_backward_compatible():
    bank = _make_bank()
    bank.load_state({"persistent": {"k": "v"}, "transient": {}})

    assert bank.read_persistent("k") == "v"
    assert bank.read_persistent_by_type("ai_session") == {}

    print("test_load_state_without_type_tags_is_backward_compatible PASSED")


def test_overwrite_preserves_new_type_tag():
    bank = _make_bank()
    bank.store_persistent("k", 1, type_tag="number")
    bank.store_persistent("k", 2, type_tag="string")

    assert bank.read_persistent_by_type("string") == {"k": 2}
    assert bank.read_persistent_by_type("number") == {}

    print("test_overwrite_preserves_new_type_tag PASSED")


def test_clear_removes_type_tags():
    bank = _make_bank()
    bank.store_persistent("k", "v", type_tag="string")
    bank.clear()

    assert bank.read_persistent_by_type("string") == {}
    assert bank.read_persistent("k") is None

    print("test_clear_removes_type_tags PASSED")


def test_validator_warns_ai_session_type_mismatch():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("ai_session_type_mismatch")
    start = wm.add_node("start_node")
    writer = wm.add_node("set_variable_node")
    reader = wm.add_node("get_variable_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", writer, "input")
    wm.connect(writer, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    # Writer declares key "sess" with no type_tag; reader reads it as ai_session
    wm.update_node_config(
        writer,
        {"membank_outputs": [{"id": "sess", "description": "Session"}]},
    )
    wm.update_node_config(
        reader,
        {"membank_inputs": [{"id": "sess", "type_tag": "ai_session"}]},
    )

    result = validate_workflow(wm, factory)
    assert result["success"] is True, "Workflow should still be valid (warning only)"
    assert any(
        "ai_session" in w["message"] and "sess" in w["message"]
        for w in result["warnings"]
    ), f"Expected ai_session warning, got: {result['warnings']}"

    print("test_validator_warns_ai_session_type_mismatch PASSED")


def test_validator_no_warning_when_type_tags_match():
    from backend.validator import validate_workflow

    wm, factory = _make_wm()
    wm.create_new("ai_session_type_match")
    start = wm.add_node("start_node")
    writer = wm.add_node("set_variable_node")
    reader = wm.add_node("get_variable_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", writer, "input")
    wm.connect(writer, "default", reader, "input")
    wm.connect(reader, "default", end, "input")

    wm.update_node_config(
        writer,
        {"membank_outputs": [{"id": "sess", "type_tag": "ai_session"}]},
    )
    wm.update_node_config(
        reader,
        {"membank_inputs": [{"id": "sess", "type_tag": "ai_session"}]},
    )

    result = validate_workflow(wm, factory)
    assert result["success"] is True
    assert not any(
        "ai_session" in w["message"] for w in result["warnings"]
    ), f"Unexpected ai_session warning: {result['warnings']}"

    print("test_validator_no_warning_when_type_tags_match PASSED")

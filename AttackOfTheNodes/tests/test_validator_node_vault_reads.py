"""C1: preflight checks for node-specific Vault reads.

Get Variable, Variable Reader, Conditional (variable source), Counter and
Branch ``vault:`` seeds read Vault keys named by their own config fields.
Each such read has a runtime fallback, so the shared model marks it optional
and the validator warns (never errors) when no node writes the key.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_validator_node_vault_reads.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.validator import validate_workflow  # noqa: E402
from backend.vault_declarations import (  # noqa: E402
    active_vault_reads,
    config_vault_read_entries,
    vault_read_entries,
)


def _make_wm():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    return WorkflowMap(factory, bus), factory


def _set(wm, node_id, **overrides):
    config = dict(wm.get_node_data(node_id)["config"])
    config.update(overrides)
    wm.update_node_config(node_id, config)


def _chain(wm, *node_types):
    ids = [wm.add_node(node_type) for node_type in node_types]
    for source, target in zip(ids, ids[1:]):
        wm.connect(source, "default", target, "input")
    return ids


def _unwritten(result, node_id):
    return [
        warning["message"] for warning in result["warnings"]
        if warning["node_id"] == node_id and "no node writes" in warning["message"]
    ]


def test_get_variable_default_key_without_writer_warns_but_runs():
    wm, factory = _make_wm()
    wm.create_new("c1_get_variable")
    _, reader, _ = _chain(wm, "start_node", "get_variable_node", "end_node")

    result = validate_workflow(wm, factory)
    assert result["success"] is True, result["errors"]
    assert _unwritten(result, reader) == [
        "Reads Vault key 'value' but no node writes it; the node uses its fallback value"
    ]


def test_set_variable_writer_silences_the_warning():
    wm, factory = _make_wm()
    wm.create_new("c1_set_then_get")
    _, writer, reader, _ = _chain(
        wm, "start_node", "set_variable_node", "get_variable_node", "end_node"
    )
    _set(wm, writer, variable_name="topic")
    _set(wm, reader, variable_name="topic")

    result = validate_workflow(wm, factory)
    assert result["success"] is True, result["errors"]
    assert _unwritten(result, reader) == []


def test_declared_membank_output_counts_as_a_writer():
    wm, factory = _make_wm()
    wm.create_new("c1_membank_writer")
    _, writer, reader, _ = _chain(
        wm, "start_node", "no_op_node", "variable_reader_node", "end_node"
    )
    _set(wm, writer, membank_outputs=[{"source_id": "shared", "type_tag": "string"}])
    _set(wm, reader, variable_name="shared")

    result = validate_workflow(wm, factory)
    assert _unwritten(result, reader) == []


def test_variable_reader_and_conditional_without_writer_warn():
    wm, factory = _make_wm()
    wm.create_new("c1_reader_conditional")
    _, reader, conditional = _chain(
        wm, "start_node", "variable_reader_node", "conditional_node"
    )
    _set(wm, reader, variable_name="ghost")
    _set(wm, conditional, left_value_source="variable", variable_name="phantom")

    result = validate_workflow(wm, factory)
    assert not any("ghost" in e["message"] or "phantom" in e["message"]
                   for e in result["errors"]), result["errors"]
    assert _unwritten(result, reader) == [
        "Reads Vault key 'ghost' but no node writes it; the node uses its fallback value"
    ]
    assert _unwritten(result, conditional) == [
        "Reads Vault key 'phantom' but no node writes it; the node uses its fallback value"
    ]


def test_conditional_on_input_reads_no_vault_key():
    wm, factory = _make_wm()
    wm.create_new("c1_conditional_input")
    _, conditional = _chain(wm, "start_node", "conditional_node")
    _set(wm, conditional, left_value_source="input", variable_name="stale")

    result = validate_workflow(wm, factory)
    assert _unwritten(result, conditional) == []


def test_counter_is_its_own_writer():
    wm, factory = _make_wm()
    wm.create_new("c1_counter")
    _, counter, _ = _chain(wm, "start_node", "counter_node", "end_node")

    result = validate_workflow(wm, factory)
    assert _unwritten(result, counter) == []


def test_branch_vault_seed_without_writer_names_the_path():
    wm, factory = _make_wm()
    wm.create_new("c1_branch_seed")
    _, branch = _chain(wm, "start_node", "branch_node")
    _set(wm, branch, branch_payload_sources={"path_a": "vault:seed", "path_b": "input"})

    result = validate_workflow(wm, factory)
    assert _unwritten(result, branch) == [
        "Path 'Branch 1' seeds from Vault key 'seed' but no node writes it; "
        "the path gets the input payload"
    ]


def test_branch_seed_on_hidden_path_is_ignored():
    wm, factory = _make_wm()
    wm.create_new("c1_branch_hidden_seed")
    _, branch = _chain(wm, "start_node", "branch_node")
    _set(wm, branch, branch_count=2, branch_payload_sources={"path_c": "vault:stale"})

    result = validate_workflow(wm, factory)
    assert _unwritten(result, branch) == []


def test_shared_model_flags_reads_required_or_optional():
    config = {
        "membank_inputs": [{"source_id": "declared"}],
        "prompt_source": "Vault",
        "prompt_vault_key": "standard",
        "variable_name": "named",
    }
    metadata = {"input_port_metadata": {"prompt": {"data_type": "string"}}}
    entries = vault_read_entries("get_variable_node", config, metadata)
    assert entries == [
        {"source_id": "declared", "target_port": "membank_inputs", "required": True},
        {"source_id": "standard", "target_port": "prompt", "required": True},
        {"source_id": "named", "target_port": "variable_name", "required": False},
    ]
    assert active_vault_reads("get_variable_node", config, metadata) == [
        "declared", "standard", "named",
    ]


def test_every_node_specific_read_is_optional_today():
    cases = [
        ("get_variable_node", {}),
        ("variable_reader_node", {"variable_name": "a"}),
        ("conditional_node", {"left_value_source": "variable", "variable_name": "b"}),
        ("counter_node", {}),
        ("branch_node", {"branch_payload_sources": {"path_b": "vault:c"}}),
    ]
    for node_type, config in cases:
        entries = config_vault_read_entries(node_type, config)
        assert entries, node_type
        assert all(entry["required"] is False for entry in entries), (node_type, entries)


def test_required_node_specific_read_without_writer_is_an_error(monkeypatch):
    import backend.validator as validator

    def required_reads(node_type, config):
        if node_type != "get_variable_node":
            return []
        return [{"source_id": "must_exist", "target_port": "variable_name", "required": True}]

    monkeypatch.setattr(validator, "config_vault_read_entries", required_reads)
    wm, factory = _make_wm()
    wm.create_new("c1_required_read")
    _, reader, _ = _chain(wm, "start_node", "get_variable_node", "end_node")

    result = validate_workflow(wm, factory)
    assert result["success"] is False
    assert {"node_id": reader, "code": "undeclared_vault_key",
            "message": "Membank input source not declared: must_exist"} in result["errors"]
    assert _unwritten(result, reader) == []


def test_validation_details_labels_the_warning():
    from frontend.screens.error_details import ErrorDetailsScreen

    screen = ErrorDetailsScreen({"validation": {"errors": [], "warnings": []}})
    message = "Reads Vault key 'value' but no node writes it; the node uses its fallback value"
    assert screen._validation_type({"code": "unwritten_vault_key", "message": message}) == "Unwritten Vault key"


def test_node_specific_read_with_parallel_writer_gets_race_warning():
    wm, factory = _make_wm()
    wm.create_new("c1_parallel_writer")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    setter = wm.add_node("set_variable_node")
    reader = wm.add_node("get_variable_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", setter, "input")
    wm.connect(branch, "path_b", reader, "input")
    _set(wm, setter, variable_name="topic")
    _set(wm, reader, variable_name="topic")

    result = validate_workflow(wm, factory)
    assert result["success"] is True, result["errors"]
    assert _unwritten(result, reader) == []
    assert any(
        w["node_id"] == reader and "parallel branches" in w["message"] and "'topic'" in w["message"]
        for w in result["warnings"]
    ), result["warnings"]

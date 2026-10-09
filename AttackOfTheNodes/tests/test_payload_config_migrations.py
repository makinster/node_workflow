"""Saved workflow compatibility and explicit terminal classification."""

from copy import deepcopy

import pytest

from backend.config_migrations import normalize_node_config
from backend.branch_health import FLOATING, VALID, derive_branch_health, output_types_from_factory
from tests.test_debug_nodes import _make_services


@pytest.mark.parametrize("node_type", ["file_output_node", "file_view_node"])
@pytest.mark.parametrize("old_flag", [False, True])
def test_file_completion_flag_retired_with_evidence_and_unknown_config_preserved(node_type, old_flag):
    old = {"terminate_branch": old_flag, "custom": {"keep": [1, 2]}}
    before = deepcopy(old)
    upgraded = normalize_node_config(node_type, old)
    assert "terminate_branch" not in upgraded
    assert upgraded["_config_migrations"]["file_io_continuation_v1"] == {"terminate_branch": old_flag}
    assert upgraded["custom"] == old["custom"]
    assert normalize_node_config(node_type, upgraded) == upgraded
    assert old == before


def test_migrations_apply_when_loading_saving_and_instantiating_old_configs():
    _, wm, _, _ = _make_services()
    wm.load_data({"id": "legacy", "nodes": {"writer": {"type": "file_output_node",
                  "config": {"terminate_branch": True, "file_path": '"C:\\Users\\a.txt"'},
                  "connections": {"inputs": [], "outputs": []}}}})
    assert "terminate_branch" not in wm.get_workflow_data_for_save()["nodes"]["writer"]["config"]
    wm.update_node_config("writer", {"terminate_branch": True, "file_path": "a.txt"})
    assert "terminate_branch" not in wm.get_node_instance("writer").config
    node = wm._factory.create_node("file_view_node", "direct", {"terminate_branch": True})
    assert "terminate_branch" not in node.config


def test_unambiguous_legacy_text_sources_migrate_but_explicit_sources_win():
    old = {"membank_inputs": [{"source_id": "greeting"}], "template": "{input}"}
    config = normalize_node_config("text_output_node", old)
    assert config["input_source"] == "Vault" and config["input_vault_key"] == "greeting"
    assert config["_config_migrations"]["text_output_source_v1"]["membank_inputs"] == old["membank_inputs"]
    assert "membank_inputs" not in config
    assert normalize_node_config("text_output_node", {**old, "input_source": "Upstream payload"})["input_source"] == "Upstream payload"
    ambiguous = normalize_node_config("text_output_node", {"membank_inputs": ["one", "two"]})
    assert ambiguous["input_source"] == "Vault" and ambiguous["input_vault_key"] == ""


def test_start_legacy_write_and_reader_configured_path_upgrade():
    start = normalize_node_config("start_node", {"membank_outputs": [{"output": "greeting", "description": "Hello"}]})
    assert start["vault_write"] and start["vault_write_key"] == "greeting"
    assert start["vault_write_description"] == "Hello"
    path = '"C:\\Users\\a.txt"'
    assert normalize_node_config("file_reader_node", {"file_path": path}) == {
        "file_path": path, "input_source": "Configured",
    }


def test_file_output_family_is_not_a_terminal_branch():
    _, wm, _, _ = _make_services()
    wm.create_new("file_continues")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    file_node = wm.add_node("file_view_node")
    output = wm.add_node("text_output_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", file_node, "file")
    wm.connect(branch, "path_b", output, "input")
    terminal = output_types_from_factory(wm._factory)
    assert "file_view_node" not in terminal
    assert "file_output_node" not in terminal
    states = {item.port: item.state for item in derive_branch_health(wm.get_all_node_data(), terminal)}
    assert states == {"path_a": FLOATING, "path_b": VALID}


def test_repeatable_default_rows_are_owned_by_each_node():
    _, wm, _, _ = _make_services()
    wm.create_new("independent_managers")
    first = wm.add_node("file_view_node")
    second = wm.add_node("file_view_node")
    wm.get_node_data(first)["config"]["additional_files"].append({"id": "one", "path": "one.md"})
    assert wm.get_node_data(second)["config"]["additional_files"] == []
    instance = wm._factory.create_node("file_view_node", "instance")
    instance.config["additional_files"].append({"id": "local"})
    assert wm._factory.create_node("file_view_node", "next").config["additional_files"] == []

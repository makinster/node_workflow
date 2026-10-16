"""Every validator issue carries a stable code; the UI labels issues by code.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_validation_codes.py -v
"""

import ast
from pathlib import Path

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.validation_codes import ISSUE_CODES
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()
VALIDATOR = Path(__file__).resolve().parent.parent / "backend" / "validator.py"


def _issue_dicts():
    """Every dict literal in validator.py that has a "message" key: an issue.

    Parsed with ``ast``, so formatting, wrapping and helper functions do not
    matter (PR 58 review: counting source snippets was formatting-sensitive).
    """
    tree = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = {key.value: value for key, value in zip(node.keys, node.values)
                    if isinstance(key, ast.Constant)}
            if "message" in keys:
                yield node.lineno, keys


def test_every_issue_carries_a_registered_literal_code():
    issues = list(_issue_dicts())
    assert len(issues) >= len(ISSUE_CODES)
    for line, keys in issues:
        code = keys.get("code")
        assert isinstance(code, ast.Constant) and isinstance(code.value, str), f"line {line}: no literal code"
        assert code.value in ISSUE_CODES, f"line {line}: unregistered code {code.value!r}"


def test_every_registered_code_is_reported_somewhere():
    used = {keys["code"].value for _, keys in _issue_dicts()}
    assert set(ISSUE_CODES) - used == set(), "registered but never reported"


def test_every_code_has_a_label():
    from frontend.screens.error_details import VALIDATION_LABELS

    assert set(VALIDATION_LABELS) == set(ISSUE_CODES)
    assert all(label.strip() for label in VALIDATION_LABELS.values())


def _messy_workflow():
    """A workflow that trips many checks at once."""
    wm = WorkflowMap(FACTORY, EventBus())
    wm.create_new("codes_messy")
    start = wm.add_node("start_node")
    dice = wm.add_node("random_number_node", alias="Dice")
    reader = wm.add_node("file_reader_node")
    getter = wm.add_node("get_variable_node")
    loose = wm.add_node("no_op_node")
    chat = wm.add_node("chat_completion_node")
    wm.connect(start, "default", dice, "input")
    wm.connect(dice, "default", reader, "input")
    wm.connect(reader, "default", getter, "input")
    wm.connect(getter, "default", chat, "prompt")
    config = dict(wm.get_node_data(reader)["config"])
    config["input_source"] = "Upstream payload"
    wm.update_node_config(reader, config)
    config = dict(wm.get_node_data(chat)["config"])
    config.update(prompt_source="Vault", prompt_vault_key="", vault_write=True, vault_write_key="")
    wm.update_node_config(chat, config)
    data = wm.get_workflow_data_for_save()
    data["nodes"][loose]["connections"]["outputs"].append(
        {"source_port": "default", "target_node_id": "node_gone", "target_port": "input"})
    data["nodes"]["node_weird"] = {"type": "not_a_real_type", "alias": "", "config": {},
                                   "connections": {"inputs": [], "outputs": []}}
    wm.load_data(data)
    return wm, {"dice": dice, "reader": reader, "getter": getter, "loose": loose, "chat": chat}


def test_real_issues_all_carry_registered_codes():
    wm, ids = _messy_workflow()
    result = validate_workflow(wm, FACTORY)
    issues = result["errors"] + result["warnings"]
    assert issues
    assert all(issue.get("code") in ISSUE_CODES for issue in issues), [
        issue for issue in issues if issue.get("code") not in ISSUE_CODES]
    codes = {issue["code"] for issue in issues}
    assert {"type_mismatch", "unwritten_vault_key", "unreachable", "missing_node",
            "unknown_node_type", "vault_source_key_missing", "vault_output_key_missing"} <= codes


def test_issue_details_name_the_port_and_source():
    wm, ids = _messy_workflow()
    result = validate_workflow(wm, FACTORY)
    mismatch = next(w for w in result["warnings"] if w["code"] == "type_mismatch")
    assert mismatch["node_id"] == ids["reader"]
    assert mismatch["port"] == "input"
    assert mismatch["source_node_id"] == ids["dice"]
    unwritten = next(w for w in result["warnings"] if w["code"] == "unwritten_vault_key")
    assert unwritten["port"] == "variable_name"


def test_label_does_not_depend_on_message_wording():
    from frontend.screens.error_details import ErrorDetailsScreen

    screen = ErrorDetailsScreen({"validation": {"errors": [], "warnings": []}})
    assert screen._validation_type({"code": "unreachable", "message": "anything at all"}) == "Unreachable node"
    assert screen._validation_type({"code": "type_mismatch", "message": ""}) == "Type mismatch"
    assert screen._validation_type({"message": "Node is not reachable"}) == "Validation issue"
    assert screen._validation_type({"code": "brand_new_code", "message": "x"}) == "Validation issue"

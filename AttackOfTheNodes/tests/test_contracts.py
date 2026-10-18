"""Step 4a-1: workflow contracts (Start rows in, the Return End out).

Design: docs/SUBWORKFLOWS_PROPOSAL.md (C1-C10, C26-C27).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_contracts.py -v
"""

import asyncio
import json

import pytest

from backend import persistence
from backend.contracts import (
    ContractError, ContractInputError, check, downstream_payload, parse_text, resolve_inputs,
    start_rows, workflow_revision,
)
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.run_service import EXIT_FINISHED_WITH_ERRORS, EXIT_INVALID_INPUT, EXIT_OK, RunService
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    for name in ("WORKFLOWS_DIR", "RUN_HISTORY_DIR", "RUN_ERRORS_DIR", "RUN_OUTPUTS_DIR", "RUN_FILES_DIR"):
        monkeypatch.setattr(persistence, name, tmp_path / name.lower())
    yield


def row(name, kind="string", value=None, required=False, to="Vault", vault_key=""):
    return {"id": name, "name": name, "type": kind, "value": value, "required": required,
            "to": to, "vault_key": vault_key}


def result(name, kind="string", source="Vault key", vault_key="", required=True):
    return {"id": name, "name": name, "type": kind, "source": source, "vault_key": vault_key,
            "required": required}


def build(rows, results=None, callable_=True, extra=None):
    """Start (rows) → End; the End is the Return End when results are given."""
    wm = WorkflowMap(FACTORY, EventBus())
    wm.create_new("contract test")
    start = wm.add_node("start_node")
    end = wm.add_node("end_node", alias="Done")
    wm.update_node_config(start, {**wm.get_node_data(start)["config"], "rows": rows})
    if results is not None:
        wm.update_node_config(end, {**wm.get_node_data(end)["config"], "return_end": True, "results": results})
    wm.connect(start, "default", end, "input")
    wm.set_callable(callable_)
    return wm, start, end


def run(wm, inputs=None):
    """Save the workflow, run it through RunService, return the RunResult."""
    from backend.save_manager import SaveManager

    SaveManager(wm).save_current_workflow()
    service = RunService.create()
    service.load(wm.workflow_id)

    async def go():
        from backend.run_policies import unattended_policies

        # Unattended, as the CLI runs headless: an error never waits for a choice.
        policy, provider = unattended_policies("terminate_branch")
        await service.start(inputs=inputs or {}, recovery_policy=policy, input_provider=provider)
        return await asyncio.wait_for(service.wait(), timeout=20)
    try:
        return asyncio.run(go())
    finally:
        service.close()


# -- values -------------------------------------------------------------------------

@pytest.mark.parametrize("kind, raw, expected", [
    ("number", "3", 3), ("number", "2.5", 2.5),
    ("bool", "true", True), ("bool", "no", False),
    ("string", "", ""), ("string", "7", "7"),
    ("var", '{"a": [1, 2]}', {"a": [1, 2]}), ("var", "plain text", "plain text"),
])
def test_parse_text(kind, raw, expected):
    assert parse_text(kind, raw) == expected


@pytest.mark.parametrize("kind, value", [("number", 0), ("bool", False), ("string", ""),
                                         ("var", "false"), ("var", {"a": 1})])
def test_check_keeps_typed_values(kind, value):
    assert check(kind, value) == value


@pytest.mark.parametrize("parse, kind, raw", [
    (True, "number", "ten"), (False, "number", True), (False, "number", "3"), (True, "bool", "maybe"),
    (False, "string", {"a": 1}), (False, "string", 7), (True, "file", "/nowhere/x.txt")])
def test_rejects(parse, kind, raw):
    with pytest.raises(ContractError):
        (parse_text if parse else check)(kind, raw)


def test_var_values_are_copies():
    original = {"items": [1]}
    copy = check("var", original)
    copy["items"].append(2)
    assert original == {"items": [1]}


def test_fill_order_and_missing_versus_empty():
    rows = [row("tone", value="plain"), row("count", "number", value="", required=True),
            row("flag", "bool", required=True), row("note")]
    # Supplied beats default; 0, False and "" are values, not "missing".
    assert resolve_inputs(rows, {"tone": "", "count": 0, "flag": False}, strict=False) == {
        "tone": "", "count": 0, "flag": False}
    # A stored "" means "no default" for every type, so it is missing.
    with pytest.raises(ContractInputError) as caught:
        resolve_inputs(rows, {}, strict=False)
    assert caught.value.missing == ["count", "flag"]
    with pytest.raises(ContractInputError) as caught:
        resolve_inputs([row("who", value="", required=True)], {}, strict=True)
    assert caught.value.missing == ["who"]
    assert resolve_inputs([row("who", value="", required=True)], {"who": ""}, strict=True) == {"who": ""}


def test_invalid_explicit_value_never_falls_back_and_unknown_is_strict():
    rows = [row("count", "number", value="5")]
    with pytest.raises(ContractInputError) as caught:
        resolve_inputs(rows, {"count": "lots", "extra": 1}, strict=True)
    assert caught.value.invalid == {"count": "expects a number, got str"}
    assert caught.value.unknown == ["extra"]
    assert resolve_inputs(rows, {"extra": 1}, strict=False) == {"count": 5}  # standard workflows


def test_downstream_one_row_as_itself_several_as_object():
    one = [row("a", to="Downstream"), row("b", to="Vault")]
    assert downstream_payload(one, {"a": 1, "b": 2}) == (True, 1)
    two = [row("a", to="Both"), row("b", to="Downstream")]
    assert downstream_payload(two, {"a": 1, "b": 2}) == (True, {"a": 1, "b": 2})
    assert downstream_payload([row("a", to="Vault")], {"a": 1}) == (False, None)


def test_legacy_start_is_one_greeting_row():
    rows = start_rows({"greeting": "Hi", "transient_output": True})
    assert [(r["name"], r["type"], r["value"]) for r in rows] == [("greeting", "string", "Hi")]


# -- port types ------------------------------------------------------------------------

def test_start_output_type_follows_its_rows():
    from backend.nodes.start_node import StartNode

    assert StartNode.describe_output_ports({}) == {}  # legacy greeting: unchanged
    one = StartNode.describe_output_ports({"rows": [row("n", "number", to="Downstream")]})
    assert one["default"]["data_type"] == "number" and one["default"]["name"] == "n"
    two = StartNode.describe_output_ports({"rows": [row("a", to="Both"), row("b", to="Downstream")]})
    assert two["default"]["data_type"] == "var"


# -- runs ---------------------------------------------------------------------------------

def test_a_contract_workflow_returns_typed_values():
    wm, _, _ = build(
        [row("tone", value="plain"), row("limit", "number", required=True)],
        [result("tone_out", vault_key="tone"), result("limit_out", "number", vault_key="limit")],
    )
    outcome = run(wm, {"limit": 3})
    assert outcome.final_state == "FINISHED" and outcome.exit_code == EXIT_OK
    assert outcome.values == {"tone_out": "plain", "limit_out": 3}
    # The revision is of what ran: the saved definition as loaded.
    loaded = WorkflowMap(FACTORY, EventBus())
    loaded.load_data(persistence.load_workflow(wm.workflow_id))
    assert outcome.revision == workflow_revision(loaded.get_workflow_data_for_save())


def test_missing_required_input_stops_before_the_run():
    wm, _, _ = build([row("limit", "number", required=True)], [result("x", vault_key="limit")])
    with pytest.raises(ContractInputError) as caught:
        run(wm, {})
    assert caught.value.missing == ["limit"]


def test_required_result_missing_when_the_return_end_never_runs():
    # The only End is not a Return End, so the callable workflow returns nothing.
    wm = WorkflowMap(FACTORY, EventBus())
    wm.create_new("never returns")
    start = wm.add_node("start_node")
    plain_end = wm.add_node("end_node")
    returner = wm.add_node("end_node", alias="Return")
    wm.update_node_config(returner, {**wm.get_node_data(returner)["config"], "return_end": True,
                                     "results": [result("x")]})
    wm.connect(start, "default", plain_end, "input")
    wm.set_callable(True)
    outcome = run(wm)
    assert outcome.values == {}
    assert outcome.exit_code == EXIT_FINISHED_WITH_ERRORS
    assert "required result(s) not produced: x" in outcome.errors[0]["message"]


def test_the_return_end_publishes_once():
    from backend.master_state import MasterState
    from backend.run_context import RunContext

    master = MasterState.__new__(MasterState)
    run_ctx = RunContext.__new__(RunContext)
    run_ctx.return_values = None
    assert MasterState._publish_result(master, run_ctx, {"a": 1}) is True
    assert MasterState._publish_result(master, run_ctx, {"a": 2}) is False
    assert run_ctx.return_values == {"a": 1}


def test_a_missing_required_result_fails_the_return_end():
    wm, _, _ = build([row("tone", value="plain")], [result("never_written")])
    outcome = run(wm)
    assert outcome.exit_code == EXIT_FINISHED_WITH_ERRORS
    assert outcome.errors[0]["code"] == "result_missing"


# -- validator ------------------------------------------------------------------------------

def codes(wm):
    report = validate_workflow(wm, FACTORY)
    return ({i["code"] for i in report["errors"]}, {i["code"] for i in report["warnings"]})


def test_validator_contract_rules():
    wm, _, end = build([row("a"), row("a")], [result("x", kind="ai_session")])
    errors, _ = codes(wm)
    assert "contract_row_invalid" in errors
    wm, _, _ = build([row("must", required=True)], [], callable_=False)
    errors, warnings = codes(wm)
    assert "input_required_no_value" in warnings and "return_end_not_callable" in warnings


def test_validator_one_return_end_after_merges():
    wm = WorkflowMap(FACTORY, EventBus())
    wm.create_new("branches")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    end_a = wm.add_node("end_node")
    end_b = wm.add_node("end_node")
    for end in (end_a, end_b):
        wm.update_node_config(end, {**wm.get_node_data(end)["config"], "return_end": True, "results": []})
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", end_a, "input")
    wm.connect(branch, "path_b", end_b, "input")
    wm.set_callable(True)
    errors, _ = codes(wm)
    assert "multiple_return_ends" in errors
    wm.update_node_config(end_b, {**wm.get_node_data(end_b)["config"], "return_end": False})
    errors, _ = codes(wm)
    assert "return_end_unmerged" in errors


def test_validator_accepts_a_return_end_after_a_merge():
    wm = WorkflowMap(FACTORY, EventBus())
    wm.create_new("merged")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    merge = wm.add_node("merge_node")
    end = wm.add_node("end_node")
    wm.update_node_config(end, {**wm.get_node_data(end)["config"], "return_end": True, "results": []})
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", merge, "input_1")
    wm.connect(branch, "path_b", merge, "input_2")
    wm.connect(merge, "default", end, "input")
    wm.set_callable(True)
    errors, _ = codes(wm)
    assert not {"multiple_return_ends", "return_end_unmerged"} & errors


# -- callable flag, authoring, revision -------------------------------------------------------

def test_callable_is_saved_only_when_true_and_survives_reload():
    from backend.save_manager import SaveManager

    wm, _, _ = build([row("a")], callable_=False)
    assert "callable" not in wm.get_workflow_data_for_save()
    wm.set_callable(True)
    assert wm.is_dirty
    SaveManager(wm).save_current_workflow()
    fresh = WorkflowMap(FACTORY, EventBus())
    fresh.load_data(persistence.load_workflow(wm.workflow_id))
    assert fresh.callable is True
    fresh.create_new("another")
    assert fresh.callable is False


def test_authoring_spec_can_be_callable():
    from backend.authoring import build_workflow

    spec = {"format": "aotn-workflow/1", "name": "Callable helper", "callable": True,
            "nodes": {"start": {"type": "start_node"}, "end": {"type": "end_node"}},
            "connections": [{"from": "start.default", "to": "end.input"}]}
    report = build_workflow(FACTORY, spec, write=True)
    assert report["ok"], report
    assert persistence.load_workflow(report["workflow_id"]).get("callable") is True
    report = build_workflow(FACTORY, {**spec, "name": "bad", "callable": "yes"}, write=False)
    assert any(d["code"] == "spec_invalid" for d in report["diagnostics"])


def test_revision_changes_with_the_definition():
    wm, start, _ = build([row("a")])
    before = workflow_revision(wm.get_workflow_data_for_save())
    assert before == workflow_revision(wm.get_workflow_data_for_save())
    wm.update_node_config(start, {**wm.get_node_data(start)["config"], "rows": [row("b")]})
    assert workflow_revision(wm.get_workflow_data_for_save()) != before


# -- CLI ---------------------------------------------------------------------------------------

def test_cli_typed_inputs_inputs_file_and_values(tmp_path, capsys):
    import aotn_cli
    from backend.save_manager import SaveManager

    wm, _, _ = build([row("limit", "number", required=True), row("tone", value="plain")],
                     [result("limit_out", "number", vault_key="limit"), result("tone_out", vault_key="tone")])
    SaveManager(wm).save_current_workflow()
    inputs_file = tmp_path / "inputs.json"
    inputs_file.write_text(json.dumps({"limit": 1, "tone": "from file"}))
    code = aotn_cli.main([wm.workflow_id, "--inputs-file", str(inputs_file), "--input", "limit=4", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert out["values"] == {"limit_out": 4, "tone_out": "from file"}  # --input wins, file fills the rest

    code = aotn_cli.main([wm.workflow_id])
    assert code == EXIT_INVALID_INPUT
    assert "missing required input(s): limit" in capsys.readouterr().err


# -- review of #80 ------------------------------------------------------------------

def test_start_vault_rows_are_declared_writers():
    """A node reading a Start row's Vault key passes preflight (finding 1)."""
    from backend.vault_declarations import typed_vault_writes

    config = {"rows": [row("message", "string", value="hi", to="Vault"),
                       row("count", "number", value="2", to="Both", vault_key="n"),
                       row("only_down", to="Downstream", value="x")]}
    meta = next(m for m in FACTORY.get_node_types_metadata() if m["type"] == "start_node")
    assert typed_vault_writes("start_node", config, meta) == {"message": "string", "n": "number"}

    wm = WorkflowMap(FACTORY, EventBus())
    wm.create_new("reads a start row")
    start = wm.add_node("start_node")
    out = wm.add_node("text_output_node")
    wm.update_node_config(start, {**wm.get_node_data(start)["config"], **config})
    wm.update_node_config(out, {**wm.get_node_data(out)["config"],
                                "input_source": "Vault", "input_vault_key": "message"})
    wm.connect(start, "default", out, "input")
    report = validate_workflow(wm, FACTORY)
    assert not [e for e in report["errors"] if e["code"] == "undeclared_vault_key"], report["errors"]


def test_var_never_reparses_an_already_typed_value():
    """An inputs-file string stays a string; only CLI text is parsed (finding 2)."""
    from backend.contracts import parse_text, collect_results

    rows = [row("data", "var", required=True)]
    assert resolve_inputs(rows, {"data": "false"}, strict=True) == {"data": "false"}
    assert resolve_inputs(rows, {"data": "null"}, strict=True) == {"data": "null"}
    assert resolve_inputs(rows, {"data": {"a": 1}}, strict=True) == {"data": {"a": 1}}
    # Text from the command line (or an editor default) is parsed by type.
    assert parse_text("var", "false") is False and parse_text("var", "hello") == "hello"
    assert parse_text("number", "3") == 3
    # A number input from a file must already be a number.
    with pytest.raises(ContractInputError):
        resolve_inputs([row("n", "number", required=True)], {"n": "3"}, strict=True)
    # Results are checked, never parsed: a stored "null" string is a value.
    values, missing, invalid = collect_results([result("r", "var")], lambda key: "null", None)
    assert (values, missing, invalid) == ({"r": "null"}, [], {})


def test_cli_parses_input_text_by_row_type(tmp_path, capsys):
    import aotn_cli
    from backend.save_manager import SaveManager

    wm, _, _ = build([row("data", "var", required=True), row("label", required=True)],
                     [result("data_out", "var", vault_key="data"), result("label_out", vault_key="label")])
    SaveManager(wm).save_current_workflow()
    inputs_file = tmp_path / "inputs.json"
    inputs_file.write_text(json.dumps({"label": "false"}))
    code = aotn_cli.main([wm.workflow_id, "--input", "data=false", "--inputs-file", str(inputs_file), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK
    assert out["values"] == {"data_out": False, "label_out": "false"}


def test_an_ordinary_workflow_does_not_enforce_return_end_results():
    """Results are ignored unless the workflow is callable, as the validator says (finding 3)."""
    wm, _, _ = build([row("tone", value="plain")], [result("never_written")], callable_=False)
    outcome = run(wm)
    assert outcome.exit_code == EXIT_OK and outcome.errors == [] and outcome.values == {}

"""Workflow authoring tool v1: list, describe and build (backend/authoring.py, aotn_author.py).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_authoring.py -v
"""

import io
import json

import pytest

from backend import authoring, persistence
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()


@pytest.fixture(autouse=True)
def _isolated_workflows(tmp_path, monkeypatch):
    """Builds write only to a temporary workflows folder."""
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    yield tmp_path / "workflows"


def _spec(**overrides):
    spec = {
        "format": authoring.FORMAT,
        "name": "Pause and wait",
        "nodes": {
            "start": {"type": "start_node", "config": {"greeting": "hi"}},
            "nap": {"type": "sleep_node", "alias": "Nap", "config": {"duration": 0.2}},
            "fan": {"type": "branch_node", "config": {"branch_count": 2}},
            "a": {"type": "no_op_node"},
            "b": {"type": "no_op_node"},
            "wait": {"type": "wait_until_node", "config": {"target_node_ids": ["a"]}},
            "end": {"type": "end_node"},
        },
        "connections": [
            {"from": "start.default", "to": "nap.input"},
            {"from": "nap.default", "to": "fan.input"},
            {"from": "fan.path_a", "to": "a.input"},
            {"from": "fan.path_b", "to": "b.input"},
            {"from": "b.default", "to": "wait.input"},
            {"from": "wait.default", "to": "end.input"},
        ],
    }
    spec.update(overrides)
    return spec


def _codes(report, level="error"):
    return [(d["node"], d["code"]) for d in report["diagnostics"] if d["level"] == level]


# --- discover / describe ----------------------------------------------------------------


def test_list_excludes_internal_types():
    types = {row["type"] for row in authoring.list_node_types(FACTORY)}
    assert "sleep_node" in types and "start_node" in types
    assert "tombstone_node" not in types


def test_describe_resolves_ports_for_the_config():
    http = authoring.describe_node_type(FACTORY, "http_request_node", {"response_mode": "file"})
    outputs = {port["port"]: port["data_type"] for port in http["outputs"]}
    assert outputs == {"default": "file", "error": "any"}
    branch = authoring.describe_node_type(FACTORY, "branch_node", {"branch_count": 3})
    assert [p["port"] for p in branch["outputs"]] == ["path_a", "path_b", "path_c", "error"]


def test_describe_reports_fields_limits_visibility_and_references():
    sleep = authoring.describe_node_type(FACTORY, "sleep_node")
    duration = next(f for f in sleep["fields"] if f["key"] == "duration")
    assert (duration["min"], duration["max"], duration["default"]) == (0.0, 60.0, 0.1)
    http = authoring.describe_node_type(FACTORY, "http_request_node")
    assert next(f for f in http["fields"] if f["key"] == "body")["visible"] is False
    assert authoring.describe_node_type(FACTORY, "wait_until_node")["node_reference_fields"] == ["target_node_ids"]


def test_describe_marks_keys_without_schema_as_unchecked():
    merge = authoring.describe_node_type(FACTORY, "merge_node")
    assert "input_slots" in merge["unchecked_keys"]


def test_describe_reports_vault_effects():
    getter = authoring.describe_node_type(FACTORY, "get_variable_node", {"variable_name": "topic"})
    assert getter["vault_reads"] == [{"source_id": "topic", "target_port": "variable_name", "required": False}]
    chat = authoring.describe_node_type(FACTORY, "chat_completion_node",
                                        {"vault_write": True, "vault_write_key": "reply"})
    assert {"key": "reply", "data_type": "string"} in chat["vault_writes"]


def test_describe_unknown_type():
    with pytest.raises(authoring.AuthoringError):
        authoring.describe_node_type(FACTORY, "tombstone_node")


# --- build -------------------------------------------------------------------------------


def test_build_writes_a_workflow_that_reloads_and_validates(_isolated_workflows):
    report = authoring.build_workflow(FACTORY, _spec())
    assert report["ok"], report["diagnostics"]
    assert _codes(report) == []
    saved = json.loads((_isolated_workflows / f"{report['workflow_id']}.json").read_text())
    assert saved["name"] == "Pause and wait"
    ids = report["nodes"]
    assert saved["nodes"][ids["nap"]]["alias"] == "Nap"
    assert saved["nodes"][ids["nap"]]["config"]["duration"] == 0.2
    # Node references were given as handles and saved as generated ids.
    assert saved["nodes"][ids["wait"]]["config"]["target_node_ids"] == ids["a"]
    # Both sides of every connection exist, written by the backend.
    assert {"source_port": "path_b", "target_node_id": ids["b"], "target_port": "input"} in \
        saved["nodes"][ids["fan"]]["connections"]["outputs"]
    assert "input_sources" in saved["nodes"][ids["nap"]]  # SaveManager's save preparation

    fresh = WorkflowMap(FACTORY, EventBus())
    assert fresh.load(report["workflow_id"])
    assert validate_workflow(fresh, FACTORY)["success"] is True


def test_check_mode_writes_nothing(_isolated_workflows):
    report = authoring.build_workflow(FACTORY, _spec(), write=False)
    assert report["ok"] and "path" not in report
    assert not list(_isolated_workflows.glob("*.json")) if _isolated_workflows.exists() else True


def test_every_problem_is_reported_and_nothing_is_written(_isolated_workflows):
    spec = _spec(nodes={
        "start": {"type": "start_node"},
        "nap": {"type": "sleep_node", "config": {"duraton": 5, "duration": -1}},
        "Wait": {"type": "wait_until_node", "config": {"target_node_ids": ["ghost"]}},
        "odd": {"type": "tombstone_node"},
    }, connections=[
        {"from": "start.default", "to": "nap.no_such_port"},
        {"from": "start.default", "to": "nap.input"},
        {"from": "start.default", "to": "nap.input"},
    ])
    report = authoring.build_workflow(FACTORY, spec)
    assert report["ok"] is False and "workflow_id" not in report
    assert set(_codes(report)) >= {
        ("Wait", "bad_handle"),
        ("nap", "unknown_config_key"),
        ("nap", "invalid_number"),
        ("Wait", "unknown_reference"),
        ("odd", "unknown_node_type"),
        ("nap", "unknown_port"),
        (None, "duplicate_connection"),
    }
    # The validator does not repeat the bad number the spec check reported.
    assert _codes(report).count(("nap", "invalid_number")) == 1
    assert not _isolated_workflows.exists() or not list(_isolated_workflows.glob("*.json"))


def test_validator_errors_block_the_build():
    spec = _spec(nodes={"reader": {"type": "file_reader_node",
                                   "config": {"input_source": "Configured", "file_path": ""}}},
                 connections=[])
    report = authoring.build_workflow(FACTORY, spec)
    assert report["ok"] is False
    assert (None, "no_start_node") in _codes(report)


def test_existing_name_is_not_overwritten():
    first = authoring.build_workflow(FACTORY, _spec())
    second = authoring.build_workflow(FACTORY, _spec())
    assert first["ok"] and not second["ok"]
    assert _codes(second) == [(None, "duplicate_name")]


@pytest.mark.parametrize("bad, message", [
    ([], "must be a JSON object"),
    ({"format": "x", "name": "n", "nodes": {"s": {"type": "start_node"}}}, "\"format\" must be"),
    ({"format": authoring.FORMAT, "name": "", "nodes": {}}, "\"name\" must be"),
])
def test_malformed_specs(bad, message):
    report = authoring.build_workflow(FACTORY, bad)
    assert report["ok"] is False
    assert any(message in d["message"] for d in report["diagnostics"])


def test_save_is_atomic(_isolated_workflows, monkeypatch):
    """A failed write leaves neither a partial file nor a temp file."""
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(persistence.json, "dump", boom)
    with pytest.raises(OSError):
        persistence.save_workflow("wf_test", {"id": "wf_test"})
    assert list(_isolated_workflows.iterdir()) == []


# --- CLI ----------------------------------------------------------------------------------


def _cli(command, argv, stdin=None):
    import aotn_author

    out = io.StringIO()
    code = aotn_author.main(command, argv, stdin=stdin, stdout=out)
    return code, out.getvalue()


def test_cli_nodes_and_describe():
    code, text = _cli("nodes", ["--json"])
    assert code == 0 and any(row["type"] == "sleep_node" for row in json.loads(text))
    code, text = _cli("describe", ["branch_node", "--set", "branch_count=3"])
    assert code == 0 and "path_c [any]" in text


def test_cli_build_from_stdin(_isolated_workflows):
    code, text = _cli("build", ["-", "--json"], stdin=io.StringIO(json.dumps(_spec())))
    report = json.loads(text)
    assert code == 0 and report["ok"]
    assert (_isolated_workflows / f"{report['workflow_id']}.json").exists()
    code, text = _cli("build", ["-"], stdin=io.StringIO(json.dumps(_spec(name="Other", nodes={
        "start": {"type": "start_node", "config": {"bogus": 1}}}, connections=[]))))
    assert code == 1 and "unknown_config_key" in text and "Not written" in text


def test_main_dispatches_authoring_commands(capsys):
    import main

    assert main.main(["describe", "sleep_node"]) == 0
    assert "Sleep" in capsys.readouterr().out


# --- PR 61 review --------------------------------------------------------------------------


def test_concurrent_saves_never_publish_partial_json(_isolated_workflows):
    import threading

    big = {"id": "wf_race", "nodes": {f"n{i}": {"x": "y" * 2000} for i in range(300)}}
    failures = []

    def save():
        try:
            persistence.save_workflow("wf_race", big)
        except Exception as exc:  # noqa: BLE001
            failures.append(exc)

    threads = [threading.Thread(target=save) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    assert json.loads((_isolated_workflows / "wf_race.json").read_text()) == big
    assert [p.name for p in _isolated_workflows.iterdir()] == ["wf_race.json"]


def _fan_out_spec(extra_nodes=None, extra_connections=None):
    nodes = {"start": {"type": "start_node"}, "a": {"type": "no_op_node"}, "b": {"type": "no_op_node"}}
    nodes.update(extra_nodes or {})
    connections = [{"from": "start.default", "to": "a.input"}]
    connections += extra_connections or []
    return _spec(name="Fan out", nodes=nodes, connections=connections)


def test_one_output_with_two_destinations_fails_the_build():
    spec = _fan_out_spec(extra_connections=[{"from": "start.default", "to": "b.input"}])
    report = authoring.build_workflow(FACTORY, spec, write=False)
    assert report["ok"] is False
    assert ("start", "ignored_fan_out") in _codes(report)
    message = next(d["message"] for d in report["diagnostics"] if d["code"] == "ignored_fan_out")
    assert "only the first" in message and "Parallel Branch" in message


def test_fan_out_is_a_validator_warning_for_the_editor_too():
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("fan_out_editor")
    start = workflow_map.add_node("start_node")
    a = workflow_map.add_node("no_op_node")
    b = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", a, "input")
    workflow_map.connect(start, "default", b, "input")
    result = validate_workflow(workflow_map, FACTORY)
    assert result["success"] is True
    assert [w["code"] for w in result["warnings"] if w["node_id"] == start] == ["ignored_fan_out"]


def test_inline_error_mux_and_error_routes_are_not_fan_out():
    spec = _fan_out_spec(
        extra_nodes={"mux": {"type": "error_mux_node"}, "mux2": {"type": "error_mux_node"}},
        extra_connections=[
            {"from": "a.default", "to": "mux.input"},
            {"from": "a.default", "to": "b.input"},
            {"from": "b.error", "to": "mux2.error"},
        ],
    )
    report = authoring.build_workflow(FACTORY, spec, write=False)
    assert "ignored_fan_out" not in [d["code"] for d in report["diagnostics"]]


def test_names_differing_only_in_case_are_duplicates():
    assert authoring.build_workflow(FACTORY, _spec(name="Example"))["ok"]
    report = authoring.build_workflow(FACTORY, _spec(name="example"))
    assert report["ok"] is False and _codes(report) == [(None, "duplicate_name")]


def test_json_output_stays_parseable_with_an_unreadable_workflow(_isolated_workflows, capsys, caplog):
    """Real stdout, as a shell pipe sees it: only the JSON report."""
    import aotn_author

    _isolated_workflows.mkdir(parents=True, exist_ok=True)
    (_isolated_workflows / "wf_broken.json").write_text("{not json")
    code = aotn_author.main("build", ["-", "--json"],
                            stdin=io.StringIO(json.dumps(_spec(name="Third"))))
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["ok"] is True
    assert "wf_broken" in caplog.text  # a log warning (stderr), not stdout


def test_build_uses_the_shared_name_rules():
    """Review of #85: a built name ending in [sub] could never be run by name."""
    report = authoring.build_workflow(FACTORY, _spec(name="Report [sub]"))
    assert report["ok"] is False
    assert [code for _, code in _codes(report)] == ["name_invalid"]

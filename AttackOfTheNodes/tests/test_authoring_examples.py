"""Authoring tool PR 2: inspect reports and the checked-in example specs.

Every spec in examples/ is built (into a temporary folder) and inspected, so a
contract change that breaks an example fails here.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_authoring_examples.py -v
"""

import io
import json
from pathlib import Path

import pytest

from backend import authoring, persistence
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

#: Warnings each example is expected to produce when built on a fresh machine.
EXPECTED_WARNINGS = {
    "pause_and_wait.json": set(),
    "ask_and_branch.json": set(),
    "vault_handoff.json": set(),
    "fetch_and_save.json": set(),
    "catch_http_errors.json": set(),
    "summarise_file.json": {"file_not_found"},
}

#: Lines (substrings) each example's execution outline must contain.
EXPECTED_OUTLINE = {
    "pause_and_wait.json": ["splits into 2 parallel paths:", "Wait for quick (Wait Until); waits for Quick path (No-Op)"],
    "ask_and_branch.json": ["Said yes? (Conditional)", "takes one of:", "[true]", "[false]"],
    "vault_handoff.json": ["Remember topic (Set Variable)", "Show note (Text Output)"],
    "fetch_and_save.json": ["Fetch page (HTTP Request)", "Save page (File Write)", "Show page (File Manager)"],
    "catch_http_errors.json": ["Catch errors (Error Mux)", "takes one of:", "[offline]", "[unmatched]"],
    "summarise_file.json": ["Read notes (File Reader)", "Summarise (Chat Completion)"],
}


@pytest.fixture(autouse=True)
def _isolated_workflows(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    yield tmp_path / "workflows"


def _build_and_load(spec):
    report = authoring.build_workflow(FACTORY, spec)
    assert report["ok"], report["diagnostics"]
    workflow_map = WorkflowMap(FACTORY, EventBus())
    assert workflow_map.load(report["workflow_id"])
    return report, workflow_map


def test_every_example_is_listed():
    assert sorted(p.name for p in EXAMPLES.glob("*.json")) == sorted(EXPECTED_WARNINGS)


@pytest.mark.parametrize("name", sorted(EXPECTED_WARNINGS))
def test_example_builds_and_inspects(name):
    spec = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    assert spec["name"].startswith("Example - ")
    report, workflow_map = _build_and_load(spec)
    warnings = {d["code"] for d in report["diagnostics"] if d["level"] == "warning"}
    assert warnings == EXPECTED_WARNINGS[name]
    inspected = authoring.inspect_workflow(FACTORY, workflow_map)
    outline = "\n".join(inspected["execution"])
    for expected in EXPECTED_OUTLINE[name]:
        assert expected in outline, outline
    assert "Not reached from Start" not in outline
    assert not [f for f in inspected["data_flow"] if f["status"] == "mismatch"]


# --- inspect ------------------------------------------------------------------------------


def _spec(nodes, connections, name="Inspect"):
    return {"format": authoring.FORMAT, "name": name, "nodes": nodes, "connections": connections}


def _inspect(nodes, connections):
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("inspect")
    ids = {}
    for handle, node in nodes.items():
        ids[handle] = workflow_map.add_node(node["type"], alias=node.get("alias", ""))
        if node.get("config"):
            config = dict(workflow_map.get_node_data(ids[handle])["config"])
            config.update(node["config"])
            workflow_map.update_node_config(ids[handle], config)
    for source, target in connections:
        (s, sp), (t, tp) = source.split("."), target.split(".")
        workflow_map.connect(ids[s], sp, ids[t], tp)
    return authoring.inspect_workflow(FACTORY, workflow_map), ids


def test_vault_ordering_before_parallel_and_missing():
    report, ids = _inspect(
        {"start": {"type": "start_node"},
         "fan": {"type": "branch_node"},
         "set": {"type": "set_variable_node", "alias": "Writer", "config": {"variable_name": "k"}},
         "get": {"type": "get_variable_node", "alias": "Parallel reader", "config": {"variable_name": "k"}},
         "after": {"type": "get_variable_node", "alias": "After reader", "config": {"variable_name": "k"}},
         "ghost": {"type": "get_variable_node", "alias": "Ghost reader", "config": {"variable_name": "nobody"}}},
        [("start.default", "fan.input"), ("fan.path_a", "set.input"), ("fan.path_b", "get.input"),
         ("set.default", "after.input"), ("after.default", "ghost.input")],
    )
    by_key = {entry["key"]: entry for entry in report["vault"]}
    orders = {r["name"]: r["order"] for r in by_key["k"]["readers"]}
    assert orders["Parallel reader (Get Variable)"].startswith("not guaranteed")
    assert orders["After reader (Get Variable)"] == "before"
    assert by_key["nobody"]["writers"] == []
    assert by_key["nobody"]["readers"][0]["order"] == "no writer"


def test_outline_shows_ignored_connections_loops_and_error_paths():
    report, _ = _inspect(
        {"start": {"type": "start_node"},
         "a": {"type": "no_op_node", "alias": "A"},
         "b": {"type": "no_op_node", "alias": "B"},
         "c": {"type": "counter_node", "alias": "C"},
         "log": {"type": "logger_node", "alias": "On failure"}},
        [("start.default", "a.input"), ("start.default", "b.input"),
         ("a.default", "c.input"), ("c.default", "a.input"), ("a.error", "log.input")],
    )
    outline = "\n".join(report["execution"])
    assert "(default -> B (No-Op): never runs; only the first connection does)" in outline
    assert "-> back to A (No-Op) (loop)" in outline
    assert "on error ->" in outline and "On failure (Logger)" in outline
    assert "Not reached from Start: B (No-Op)" in outline


def test_duplicate_names_get_an_id_suffix():
    report, ids = _inspect(
        {"start": {"type": "start_node"}, "fan": {"type": "branch_node"},
         "x": {"type": "no_op_node"}, "y": {"type": "no_op_node"}},
        [("start.default", "fan.input"), ("fan.path_a", "x.input"), ("fan.path_b", "y.input")],
    )
    names = {n["id"]: n["name"] for n in report["nodes"]}
    assert names[ids["x"]] == f"No-Op #{ids['x'][-4:]}"
    assert names[ids["start"]] == "Start"


def test_data_flow_statuses():
    report, ids = _inspect(
        {"start": {"type": "start_node"},
         "dice": {"type": "random_number_node", "alias": "Dice"},
         "read": {"type": "file_reader_node", "config": {"input_source": "Upstream payload"}},
         "noop": {"type": "no_op_node"},
         "read2": {"type": "file_reader_node", "alias": "Read 2", "config": {"input_source": "Upstream payload"}},
         "read3": {"type": "file_reader_node", "alias": "Read 3"}},
        [("start.default", "dice.input"), ("dice.default", "read.input"), ("read.default", "noop.input"),
         ("noop.default", "read2.input"), ("read2.default", "read3.input")],
    )
    status = {(f["from"], f["to"]): f["status"] for f in report["data_flow"]}
    assert status[(ids["dice"], ids["read"])] == "mismatch"
    assert status[(ids["read"], ids["noop"])] == "ok (accepts any)"
    assert status[(ids["noop"], ids["read2"])] == "unchecked"
    assert status[(ids["read2"], ids["read3"])] == "not used (source is not Upstream payload)"


def test_unchecked_and_changed_config_are_reported():
    report, ids = _inspect(
        {"start": {"type": "start_node"},
         "nap": {"type": "sleep_node", "config": {"duration": 2}},
         "catch": {"type": "error_mux_node", "config": {"routes": [{"id": "r", "codes": ["timeout"]}]}}},
        [("start.default", "nap.input"), ("nap.default", "catch.input")],
    )
    changed = {n["id"]: n["changed"] for n in report["nodes"]}
    assert changed[ids["nap"]] == {"duration": 2.0}
    unchecked = {u["node"]: u["keys"] for u in report["unchecked"]}
    assert unchecked[ids["catch"]] == ["routes"]


# --- custom config keys ------------------------------------------------------------------


def test_declared_custom_keys_are_accepted_and_described():
    described = authoring.describe_node_type(FACTORY, "error_mux_node")
    assert set(described["custom_keys"]) == {"routes", "unmatched_route"}
    assert {"routes", "unmatched_route"} <= set(described["unchecked_keys"])
    spec = _spec({"start": {"type": "start_node"},
                  "catch": {"type": "error_mux_node", "config": {"routes": [], "unmatched_route": True,
                                                                 "bogus": 1}}},
                 [{"from": "start.default", "to": "catch.input"}])
    report = authoring.build_workflow(FACTORY, spec, write=False)
    keys = [d["message"] for d in report["diagnostics"] if d["code"] == "unknown_config_key"]
    assert len(keys) == 1 and "'bogus'" in keys[0]


# --- CLI ------------------------------------------------------------------------------------


def test_cli_inspect_by_name_path_and_json(tmp_path, capsys):
    import aotn_author

    spec = json.loads((EXAMPLES / "pause_and_wait.json").read_text(encoding="utf-8"))
    report = authoring.build_workflow(FACTORY, spec)
    assert aotn_author.main("inspect", ["Example - Pause and wait"]) == 0
    text = capsys.readouterr().out
    assert "Execution:" in text and "splits into 2 parallel paths:" in text
    saved = persistence.WORKFLOWS_DIR / f"{report['workflow_id']}.json"
    assert aotn_author.main("inspect", [str(saved), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["name"] == "Example - Pause and wait"
    with pytest.raises(SystemExit):
        aotn_author.main("inspect", ["No such workflow"])

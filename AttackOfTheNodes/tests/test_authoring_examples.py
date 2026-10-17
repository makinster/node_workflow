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
    mux_keys = {"routes", "unmatched_route", "unmatched_label", "unmatched_forward"}
    assert set(described["custom_keys"]) == mux_keys
    assert mux_keys <= set(described["unchecked_keys"])
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


# --- PR 63 review ---------------------------------------------------------------------------


def test_writer_on_one_conditional_branch_is_not_a_guarantee():
    report, _ = _inspect(
        {"start": {"type": "start_node"},
         "cond": {"type": "conditional_node", "config": {"right_value": "x"}},
         "set": {"type": "set_variable_node", "alias": "Writer", "config": {"variable_name": "k"}},
         "get": {"type": "get_variable_node", "alias": "Reader", "config": {"variable_name": "k"}}},
        [("start.default", "cond.input"), ("cond.true", "set.input"), ("set.default", "get.input"),
         ("cond.false", "get.input")],
    )
    order = next(r["order"] for e in report["vault"] if e["key"] == "k" for r in e["readers"])
    assert order == "not guaranteed (a path reaches it without passing a writer)"


def test_writer_on_every_path_is_before_and_self_reads_are_named():
    report, _ = _inspect(
        {"start": {"type": "start_node"},
         "set": {"type": "set_variable_node", "config": {"variable_name": "k"}},
         "cond": {"type": "conditional_node", "config": {"right_value": "x"}},
         "a": {"type": "get_variable_node", "alias": "A", "config": {"variable_name": "k"}},
         "b": {"type": "get_variable_node", "alias": "B", "config": {"variable_name": "k"}},
         "count": {"type": "counter_node", "config": {"counter_name": "n"}}},
        [("start.default", "set.input"), ("set.default", "cond.input"), ("cond.true", "a.input"),
         ("cond.false", "b.input"), ("a.default", "count.input")],
    )
    orders = {e["key"]: [r["order"] for r in e["readers"]] for e in report["vault"]}
    assert orders["k"] == ["before", "before"]
    assert orders["n"] == ["its own key (the first visit reads the fallback)"]


def test_hidden_branch_outputs_are_not_executed():
    report, ids = _inspect(
        {"start": {"type": "start_node"}, "fan": {"type": "branch_node", "config": {"branch_count": 3}},
         "a": {"type": "no_op_node", "alias": "A"}, "b": {"type": "no_op_node", "alias": "B"},
         "c": {"type": "no_op_node", "alias": "C"}},
        [("start.default", "fan.input"), ("fan.path_a", "a.input"), ("fan.path_b", "b.input"),
         ("fan.path_c", "c.input")],
    )
    # Reconfigure to two paths, keeping the path_c connection (as the editor can).
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("hidden")
    start = workflow_map.add_node("start_node")
    fan = workflow_map.add_node("branch_node")
    nodes = [workflow_map.add_node("no_op_node", alias=alias) for alias in ("A", "B", "C")]
    config = dict(workflow_map.get_node_data(fan)["config"])
    config["branch_count"] = 3
    workflow_map.update_node_config(fan, config)
    workflow_map.connect(start, "default", fan, "input")
    for port, node in zip(("path_a", "path_b", "path_c"), nodes):
        workflow_map.connect(fan, port, node, "input")
    config["branch_count"] = 2
    workflow_map.update_node_config(fan, config)
    outline = "\n".join(authoring.inspect_workflow(FACTORY, workflow_map)["execution"])
    assert "splits into 2 parallel paths:" in outline
    assert "(path_c -> C (No-Op): hidden output, never runs)" in outline
    assert "Not reached from Start: C (No-Op)" in outline


def test_wait_until_targets_saved_as_a_list():
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("wait_list")
    start = workflow_map.add_node("start_node")
    a = workflow_map.add_node("no_op_node", alias="A")
    wait = workflow_map.add_node("wait_until_node")
    workflow_map.connect(start, "default", a, "input")
    workflow_map.connect(a, "default", wait, "input")
    config = dict(workflow_map.get_node_data(wait)["config"])
    config["target_node_ids"] = [a]
    workflow_map.update_node_config(wait, config)
    outline = "\n".join(authoring.inspect_workflow(FACTORY, workflow_map)["execution"])
    assert "Wait Until; waits for A (No-Op)" in outline


def test_error_mux_catch_all_settings_build():
    spec = _spec({"start": {"type": "start_node"},
                  "catch": {"type": "error_mux_node",
                            "config": {"unmatched_route": True, "unmatched_label": "Other",
                                       "unmatched_forward": "failed_input"}},
                  "log": {"type": "logger_node"}},
                 [{"from": "start.default", "to": "catch.input"},
                  {"from": "catch.unmatched", "to": "log.input"}])
    report = authoring.build_workflow(FACTORY, spec, write=False)
    assert report["ok"], report["diagnostics"]


@pytest.mark.parametrize("content", ["[]", "{}", '{"id": "x", "nodes": []}', '"text"'])
def test_inspect_rejects_files_that_are_not_workflows(tmp_path, content, capsys):
    import aotn_author

    path = tmp_path / "bad.json"
    path.write_text(content)
    with pytest.raises(SystemExit) as raised:
        aotn_author.main("inspect", [str(path)])
    assert raised.value.code == 2
    assert "is not a workflow" in capsys.readouterr().err


def test_error_path_listed_once_for_types_that_declare_error():
    """HTTP Request lists `error` among its own outputs; the outline must not
    show its error path twice (found in a final review of PR 63)."""
    report, _ = _inspect(
        {"start": {"type": "start_node"},
         "fetch": {"type": "http_request_node", "alias": "Fetch", "config": {"url": "https://example.com"}},
         "log": {"type": "logger_node", "alias": "Failed"}},
        [("start.default", "fetch.input"), ("fetch.error", "log.input")],
    )
    outline = "\n".join(report["execution"])
    assert outline.count("on error ->") == 1
    assert outline.count("Failed (Logger)") == 1

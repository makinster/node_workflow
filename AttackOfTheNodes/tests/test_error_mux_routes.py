"""Error Mux routes (port model P2).

Routes are config-driven ports: ``routes: [{id, label, codes}]`` plus an
optional ``unmatched`` route. The backend owns what a route is
(``backend.node_errors``); the config UI only proposes values (upstream code
pickers, auto-fill, refill).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

import pytest

from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import NODE_EXECUTION_UPDATE
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_errors import (
    UNMATCHED_ROUTE,
    error_codes,
    mux_output_ports,
    mux_route_for_code,
    mux_route_problems,
    mux_routes,
)
from backend.node_factory import NodeFactory
from backend.output_manager import OutputManager
from backend.run_policies import TerminatePolicy
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap


RUN_TIMEOUT = 5.0


@pytest.fixture(autouse=True)
def _run_records_in_tmp(tmp_path, monkeypatch):
    from backend import error_handler, output_manager, run_history

    monkeypatch.setattr(error_handler, "RUN_ERRORS_DIR", tmp_path / "run_errors")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history")
    monkeypatch.setattr(output_manager, "RUN_OUTPUTS_DIR", tmp_path / "run_outputs")


def _route(route_id, codes, label=None):
    return {"id": route_id, "label": label or route_id.title(), "codes": codes}


# ---------------------------------------------------------------------------
# Route model (backend.node_errors)
# ---------------------------------------------------------------------------


def test_routes_keep_order_and_skip_unusable_entries():
    config = {"routes": [
        _route("retry", "timeout, network"),
        {"id": "", "codes": ["x"]},
        _route("error", ["x"]),
        _route(UNMATCHED_ROUTE, ["x"]),
        _route("retry", ["dup"]),
        "not a route",
        {"id": "alert", "codes": ["http_status", "http_status"]},
    ]}
    routes = mux_routes(config)
    assert [r["id"] for r in routes] == ["retry", "alert"]
    assert routes[0]["codes"] == ["timeout", "network"]
    assert routes[1] == {"id": "alert", "label": "Route 2", "codes": ["http_status"]}


def test_route_problems_name_each_mistake():
    problems = mux_route_problems({"routes": [
        _route("a", ["timeout"], "First"), {"codes": []}, _route("error", []),
        _route("a", []), _route("b", ["timeout"]), 7,
    ]})
    assert problems == [
        "route 2 has no id",
        "route id 'error' is reserved",
        "route id 'a' is used twice",
        "code 'timeout' is listed on two routes; the first (First) wins",
        "route 6 is not an object",
    ]
    assert mux_route_problems({}) == []
    assert mux_route_problems({"routes": "x"}) == ["routes must be a list"]


def test_first_listing_wins_then_unmatched_catches_the_rest():
    config = {"routes": [_route("a", ["timeout"]), _route("b", ["timeout", "network"])]}
    assert mux_route_for_code(config, "timeout") == "a"
    assert mux_route_for_code(config, "network") == "b"
    assert mux_route_for_code(config, "http_status") is None
    assert mux_route_for_code(config, None) is None
    config["unmatched_route"] = True
    assert mux_route_for_code(config, "http_status") == UNMATCHED_ROUTE
    assert mux_route_for_code(config, "") is None
    assert mux_output_ports(config) == ["a", "b", UNMATCHED_ROUTE]


def test_error_codes_accept_lists_and_text():
    assert error_codes("a, b\nc,, a") == ["a", "b", "c"]
    assert error_codes(["a", " b ", ""]) == ["a", "b"]
    assert error_codes(None) == []


def test_factory_resolves_route_ports_and_names():
    factory = NodeFactory()
    node = {"type": "error_mux_node", "config": {
        "routes": [_route("route_1", ["timeout"], "Retry later"), _route("route_2", [])],
        "unmatched_route": True,
    }}
    assert factory.node_output_ports(node) == ["route_1", "route_2", UNMATCHED_ROUTE]
    meta = factory.node_output_port_metadata(node)
    assert meta["route_1"]["name"] == "Retry later"
    assert "timeout" in meta["route_1"]["description"]
    assert "no codes yet" in meta["route_2"]["description"]
    assert meta[UNMATCHED_ROUTE]["name"] == "Unmatched"
    assert meta["route_1"]["data_type"] == "any"
    # Fixed-port nodes keep their declared metadata.
    logger = factory.node_output_port_metadata({"type": "logger_node", "config": {}})
    assert set(logger) == set(factory.output_ports_for("logger_node"))


def test_display_names_use_the_route_label():
    from frontend.node_io_display import output_display_name

    factory = NodeFactory()
    node = {"type": "error_mux_node", "config": {"routes": [_route("route_1", ["x"], "Notify me")]}}
    assert output_display_name(factory, node, "route_1") == "Notify me"


# ---------------------------------------------------------------------------
# Migration of pre-P2 configs
# ---------------------------------------------------------------------------


def _services():
    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    master = MasterState(workflow_map, MemoryBank(bus), bus,
                         output_manager=OutputManager(),
                         configuration_manager=ConfigurationManager())
    workflow_map.create_new("Mux routes")
    return bus, factory, workflow_map, master


def test_legacy_path_codes_become_routes_and_keep_their_connections():
    bus, factory, workflow_map, master = _services()
    start = workflow_map.add_node("start_node")
    parse = workflow_map.add_node("json_path_node")
    mux = workflow_map.add_node("error_mux_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(start, {"greeting": "not json"})
    workflow_map.connect(start, "default", parse, "input")
    workflow_map.connect(parse, "error", mux, "error")
    workflow_map.connect(mux, "path_b", handler, "input")
    workflow_map.update_node_config(mux, {"forward": "error", "path_a_codes": "",
                                          "path_b_codes": "invalid_json", "path_c_codes": ""})

    config = workflow_map.get_node_data(mux)["config"]
    assert [r["id"] for r in config["routes"]] == ["path_a", "path_b", "path_c"]
    assert config["routes"][1] == {"id": "path_b", "label": "Path B", "codes": ["invalid_json"]}
    assert not any(key.endswith("_codes") for key in config)
    assert set(config["_config_migrations"]["error_mux_routes_v1"]) == {
        "path_a_codes", "path_b_codes", "path_c_codes"}
    assert workflow_map.output_ports(mux) == ["path_a", "path_b", "path_c"]
    result = validate_workflow(workflow_map, factory)
    assert not [e for e in result["errors"] if e.get("node_id") == mux]


def test_a_new_mux_has_no_routes_and_no_migration():
    factory = NodeFactory()
    node = factory.create_node("error_mux_node", "m", {"forward": "error", "routes": []})
    assert node.config == {"forward": "error", "routes": []}
    assert node.get_output_ports() == []


# ---------------------------------------------------------------------------
# Engine: routing along route ids and the unmatched route
# ---------------------------------------------------------------------------


def _mux_workflow(workflow_map, routes, unmatched=False):
    start = workflow_map.add_node("start_node")
    parse = workflow_map.add_node("json_path_node")
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.update_node_config(start, {"greeting": "not json"})
    workflow_map.update_node_config(mux, {"forward": "error", "routes": routes,
                                          "unmatched_route": unmatched})
    workflow_map.connect(start, "default", parse, "input")
    workflow_map.connect(parse, "error", mux, "error")
    handlers = {}
    for port in workflow_map.output_ports(mux):
        handlers[port] = workflow_map.add_node("no_op_node")
        workflow_map.connect(mux, port, handlers[port], "input")
    return parse, mux, handlers


def _run(master, workflow_map) -> List[Dict[str, Any]]:
    async def go():
        assert await master.start_workflow(recovery_policy=TerminatePolicy("terminate_branch"))
        await asyncio.wait_for(master.wait_for_completion(), timeout=RUN_TIMEOUT)
    asyncio.run(go())
    return master.error_handler.get_errors_for_run(master.current_run_id)


def _statuses(bus):
    events = []
    bus.subscribe(NODE_EXECUTION_UPDATE, events.append)
    return events


def test_a_failure_takes_the_route_that_lists_its_code():
    bus, factory, workflow_map, master = _services()
    events = _statuses(bus)
    parse, mux, handlers = _mux_workflow(workflow_map, [
        _route("route_retry", ["timeout"]), _route("route_bad", ["invalid_json"])])

    errors = _run(master, workflow_map)

    assert [(e["code"], e["handled"]) for e in errors] == [("invalid_json", True)]
    ran = {e["node_id"] for e in events if e["status"] == "done"}
    assert handlers["route_bad"] in ran and handlers["route_retry"] not in ran
    assert master.run_context.skip_reasons.get(handlers["route_retry"]) == "not_taken"
    assert master._memory_bank.read_transient(mux, "route_bad")["code"] == "invalid_json"


def test_the_unmatched_route_takes_codes_no_route_lists():
    bus, factory, workflow_map, master = _services()
    events = _statuses(bus)
    parse, mux, handlers = _mux_workflow(
        workflow_map, [_route("route_retry", ["timeout"])], unmatched=True)

    errors = _run(master, workflow_map)

    assert [e["handled"] for e in errors] == [True]
    ran = {e["node_id"] for e in events if e["status"] == "done"}
    assert handlers[UNMATCHED_ROUTE] in ran


def test_without_a_matching_route_or_unmatched_the_failure_is_unhandled():
    bus, factory, workflow_map, master = _services()
    parse, mux, handlers = _mux_workflow(workflow_map, [_route("route_retry", ["timeout"])])

    errors = _run(master, workflow_map)

    assert [e["handled"] for e in errors] == [False]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def _messages(result, key, node_id):
    return [e["message"] for e in result[key] if e.get("node_id") == node_id]


def test_validator_checks_route_codes_connections_and_mistakes():
    bus, factory, workflow_map, master = _services()
    parse, mux, handlers = _mux_workflow(workflow_map, [
        _route("route_a", ["invalid_json"], "Bad input"),
        _route("route_b", ["no_such_code"], "Typo"),
        _route("route_c", ["invalid_json"], "Again"),
    ], unmatched=True)
    workflow_map.disconnect(mux, UNMATCHED_ROUTE, handlers[UNMATCHED_ROUTE], "input")
    workflow_map.disconnect(mux, "route_c", handlers["route_c"], "input")

    result = validate_workflow(workflow_map, factory)
    errors = _messages(result, "errors", mux)
    warnings = _messages(result, "warnings", mux)

    assert any("route 'Typo' lists code 'no_such_code'" in m for m in errors)
    assert not any("Bad input" in m for m in errors)
    assert "Error Mux unmatched route is on but has no connection" in warnings
    assert "Error Mux route 'Again' lists codes but has no connection" in warnings
    assert any("code 'invalid_json' is listed on two routes" in m for m in warnings)


def test_validator_errors_on_a_connection_to_a_deleted_route():
    bus, factory, workflow_map, master = _services()
    parse, mux, handlers = _mux_workflow(workflow_map, [_route("route_a", ["invalid_json"])])
    workflow_map.update_node_config(mux, {"forward": "error", "routes": []})

    result = validate_workflow(workflow_map, factory)

    assert any("undeclared port 'route_a'" in m for m in _messages(result, "errors", mux))


def test_a_mux_with_only_the_unmatched_route_is_not_flagged_as_empty():
    bus, factory, workflow_map, master = _services()
    parse, mux, handlers = _mux_workflow(workflow_map, [], unmatched=True)

    result = validate_workflow(workflow_map, factory)

    assert not any("never routes" in m for m in _messages(result, "warnings", mux))


# ---------------------------------------------------------------------------
# Pruning connections on removed ports
# ---------------------------------------------------------------------------


def test_prune_drops_deleted_routes_but_keeps_hidden_branch_paths_and_error():
    bus, factory, workflow_map, master = _services()
    parse, mux, handlers = _mux_workflow(
        workflow_map, [_route("keep", ["invalid_json"]), _route("gone", ["timeout"])])
    fallback = workflow_map.add_node("no_op_node")
    workflow_map.connect(mux, "error", fallback, "input")
    stale = workflow_map.add_node("no_op_node")
    workflow_map.connect(mux, "never_a_port", stale, "input")  # already invalid
    previous = workflow_map.output_ports(mux)
    workflow_map.update_node_config(mux, {"forward": "error",
                                          "routes": [_route("keep", ["invalid_json"])]})

    assert workflow_map.prune_removed_output_connections(mux, previous) == 1
    ports = [c["source_port"] for c in workflow_map.get_node_data(mux)["connections"]["outputs"]]
    # The already-invalid connection is left for the validator to report.
    assert sorted(ports) == ["error", "keep", "never_a_port"]
    assert not workflow_map.get_node_data(handlers["gone"])["connections"]["inputs"]

    branch = workflow_map.add_node("branch_node")
    tail = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(branch, {"branch_count": 4})
    workflow_map.connect(branch, "path_d", tail, "input")
    previous = workflow_map.output_ports(branch)
    workflow_map.update_node_config(branch, {"branch_count": 2})
    assert workflow_map.prune_removed_output_connections(branch, previous) == 0
    assert workflow_map.prune_removed_output_connections("missing", ["x"]) == 0


# ---------------------------------------------------------------------------
# UI-side entry: upstream codes, auto-fill, refill (frontend only)
# ---------------------------------------------------------------------------


def _wired_mux(workflow_map, source_type="http_request_node"):
    source = workflow_map.add_node(source_type)
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.connect(source, "error", mux, "error")
    return source, mux


def test_upstream_definitions_come_from_the_error_source():
    from frontend.error_mux_ui import code_options, upstream_error_definitions

    bus, factory, workflow_map, master = _services()
    source, mux = _wired_mux(workflow_map)
    codes = [d["code"] for d in upstream_error_definitions(factory, workflow_map, mux)]
    assert codes == ["node_error", "missing_url", "timeout", "network", "http_status"]

    options = [value for _, value in code_options(
        upstream_error_definitions(factory, workflow_map, mux),
        [{"codes": ["legacy_code"]}])]
    assert options[:5] == codes
    assert "engine.upstream_unreachable" in options
    assert options[-1] == "legacy_code"


def test_routes_from_definitions_keep_ids_of_single_code_routes():
    from frontend.error_mux_ui import routes_from_definitions

    definitions = [{"code": "timeout"}, {"code": "http_status"}]
    existing = [_route("route_keep", ["timeout"], "Slow"), _route("route_multi", ["a", "b"])]
    routes = routes_from_definitions(definitions, existing)
    assert routes[0] == {"id": "route_keep", "label": "Slow", "codes": ["timeout"]}
    assert routes[1]["id"].startswith("route_") and routes[1]["id"] != "route_multi"
    assert routes[1]["label"] == "Http status" and routes[1]["codes"] == ["http_status"]


def test_autofill_fills_only_an_empty_mux_wired_to_an_error_port():
    from frontend.error_mux_ui import autofill_mux_routes

    bus, factory, workflow_map, master = _services()
    loose = workflow_map.add_node("error_mux_node")
    assert not autofill_mux_routes(factory, workflow_map, loose)
    source, mux = _wired_mux(workflow_map, "json_path_node")
    assert autofill_mux_routes(factory, workflow_map, mux)
    routes = workflow_map.get_node_data(mux)["config"]["routes"]
    assert [r["codes"] for r in routes] == [["node_error"], ["invalid_json"]]
    assert not autofill_mux_routes(factory, workflow_map, mux)  # already has routes
    assert not autofill_mux_routes(factory, workflow_map, source)  # not a mux


def test_config_screen_prefills_routes_offers_upstream_codes_and_refills():
    from textual.app import App
    from textual.widgets import Button, SelectionList

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.form_generator import ObjectListField

    bus, factory, workflow_map, master = _services()
    source, mux = _wired_mux(workflow_map)
    screen = NodeConfigScreen(factory, workflow_map, mux, workflow_map.get_node_data(mux))

    class ConfigApp(App):
        def compose(self):
            yield screen

    async def check():
        app = ConfigApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            field = app.query_one("#field-routes", ObjectListField)
            routes = field.value
            assert [r["codes"] for r in routes] == [
                ["node_error"], ["missing_url"], ["timeout"], ["network"], ["http_status"]]
            assert all(r["id"].startswith("route_") for r in routes)
            labels = [str(b.label) for b in field.query(Button)]
            assert labels.count("Remove route") == 5
            assert "Add route" in labels and "Refill from upstream" in labels
            picker = field.query(SelectionList).first()
            offered = [picker.get_option_at_index(i).value for i in range(picker.option_count)]
            assert offered[:5] == ["node_error", "missing_url", "timeout", "network", "http_status"]

            # Trim to one route, then refill: the kept route keeps its id.
            kept = routes[2]
            await field.replace_rows([kept])
            await pilot.pause()
            assert [r["id"] for r in field.value] == [kept["id"]]
            app.query_one("#field-routes-refill", Button).press()
            await pilot.pause()
            await pilot.pause()
            refilled = field.value
            assert len(refilled) == 5
            assert refilled[2]["id"] == kept["id"]
            assert screen._get_form_values()["routes"] == refilled
            # Route names live in the routes list, not in generated
            # "<port>_label" fields.
            assert not list(app.query("#field-" + refilled[0]["id"] + "_label"))

    asyncio.run(check())

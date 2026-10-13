"""Error Mux: an inline catch with a No error branch and recovery branches.

The mux sits right after a node. When the node succeeds, its output continues
on ``default`` ("No error"). When it fails with an error the user picked, the
failure is handled (no error stop, no recovery prompt) and leaves on that
error's recovery branch, which passes along either the error details or the
failed node's input. The backend owns the route model (``node_errors``); the
config UI (Source / Parameters / Payloads) is frontend-only.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import NODE_EXECUTION_UPDATE, RECOVERY_OPTIONS_AVAILABLE
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_errors import (
    UNMATCHED_ROUTE,
    error_codes,
    mux_forward_for,
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


def _route(route_id, codes, label=None, forward=None):
    route = {"id": route_id, "label": label or route_id.title(), "codes": codes}
    if forward:
        route["forward"] = forward
    return route


def _services():
    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    master = MasterState(workflow_map, MemoryBank(bus), bus,
                         output_manager=OutputManager(),
                         configuration_manager=ConfigurationManager())
    workflow_map.create_new("Mux")
    return bus, factory, workflow_map, master


# ---------------------------------------------------------------------------
# Route model (backend.node_errors)
# ---------------------------------------------------------------------------


def test_ports_are_no_error_then_branches_then_any_other_error():
    config = {"routes": [_route("a", ["timeout"]), _route("b", ["network"])]}
    assert mux_output_ports(config) == ["default", "a", "b"]
    config["unmatched_route"] = True
    assert mux_output_ports(config) == ["default", "a", "b", UNMATCHED_ROUTE]
    assert mux_output_ports({}) == ["default"]


def test_routes_skip_unusable_entries_and_reserve_default():
    config = {"routes": [
        _route("retry", "timeout, network"), {"id": "", "codes": ["x"]},
        _route("error", ["x"]), _route("default", ["x"]), _route(UNMATCHED_ROUTE, ["x"]),
        _route("retry", ["dup"]), "not a route",
    ]}
    assert [r["id"] for r in mux_routes(config)] == ["retry"]
    assert mux_routes(config)[0]["codes"] == ["timeout", "network"]
    assert "route id 'default' is reserved" in mux_route_problems(config)


def test_each_branch_chooses_what_it_passes_along():
    config = {"routes": [_route("a", ["timeout"], forward="failed_input"), _route("b", ["x"])],
              "unmatched_route": True, "unmatched_forward": "failed_input"}
    assert mux_forward_for(config, "a") == "failed_input"
    assert mux_forward_for(config, "b") == "error"
    assert mux_forward_for(config, UNMATCHED_ROUTE) == "failed_input"
    # A pre-P4 node-wide `forward` is the fallback for branches without one.
    legacy = {"forward": "failed_input", "routes": [_route("a", ["timeout"])]}
    assert mux_forward_for(legacy, "a") == "failed_input"


def test_first_listing_wins_then_any_other_error():
    config = {"routes": [_route("a", ["timeout"]), _route("b", ["timeout", "network"])]}
    assert mux_route_for_code(config, "timeout") == "a"
    assert mux_route_for_code(config, "network") == "b"
    assert mux_route_for_code(config, "http_status") is None
    config["unmatched_route"] = True
    assert mux_route_for_code(config, "http_status") == UNMATCHED_ROUTE
    assert mux_route_for_code(config, None) is None


def test_error_codes_accept_lists_and_text():
    assert error_codes("a, b\nc,, a") == ["a", "b", "c"]
    assert error_codes(None) == []


def test_port_names_come_from_branch_names():
    from frontend.node_io_display import output_display_name

    factory = NodeFactory()
    node = {"type": "error_mux_node", "config": {
        "routes": [_route("route_1", ["timeout"], "Retry later")],
        "unmatched_route": True, "unmatched_label": "Give up"}}
    assert factory.node_output_ports(node) == ["default", "route_1", UNMATCHED_ROUTE]
    assert output_display_name(factory, node, "default") == "No error"
    assert output_display_name(factory, node, "route_1") == "Retry later"
    assert output_display_name(factory, node, UNMATCHED_ROUTE) == "Give up"


def test_legacy_path_codes_still_migrate_to_routes():
    factory = NodeFactory()
    node = factory.create_node("error_mux_node", "m", {
        "forward": "error", "path_a_codes": "timeout", "path_b_codes": "", "path_c_codes": "x"})
    assert [r["id"] for r in node.config["routes"]] == ["path_a", "path_b", "path_c"]
    assert node.route_for_code("x") == "path_c"


# ---------------------------------------------------------------------------
# Engine: inline catch, No error, handled failures
# ---------------------------------------------------------------------------


def _inline(workflow_map, greeting, routes, unmatched=False, forward=None):
    """start -> json_path -> mux; mux: default -> ok, each branch -> handler."""
    start = workflow_map.add_node("start_node")
    parse = workflow_map.add_node("json_path_node")
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.update_node_config(start, {"greeting": greeting})
    config: Dict[str, Any] = {"routes": routes, "unmatched_route": unmatched}
    if forward:
        config["unmatched_forward"] = forward
    workflow_map.update_node_config(mux, config)
    workflow_map.connect(start, "default", parse, "input")
    workflow_map.connect(parse, "default", mux, "input")
    outs = {}
    for port in workflow_map.output_ports(mux):
        outs[port] = workflow_map.add_node("no_op_node")
        workflow_map.connect(mux, port, outs[port], "input")
    return parse, mux, outs


def _run(bus, master, policy=None) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = []
    prompts: List[Dict[str, Any]] = []
    bus.subscribe(NODE_EXECUTION_UPDATE, events.append)
    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, prompts.append)

    async def go():
        assert await master.start_workflow(recovery_policy=policy)
        await asyncio.wait_for(master.wait_for_completion(), timeout=RUN_TIMEOUT)
    asyncio.run(go())
    done = {e["node_id"] for e in events if e["status"] == "done"}
    return {"events": events, "prompts": prompts, "done": done,
            "errors": master.error_handler.get_errors_for_run(master.current_run_id)}


def test_success_continues_on_no_error_with_the_nodes_output():
    bus, factory, workflow_map, master = _services()
    parse, mux, outs = _inline(workflow_map, '{"a": 1}', [_route("route_bad", ["invalid_json"])])

    result = _run(bus, master)

    assert outs["default"] in result["done"] and outs["route_bad"] not in result["done"]
    assert result["errors"] == []
    assert master._memory_bank.read_transient(mux, "default") == \
        master._memory_bank.read_transient(parse, "default")
    assert master.run_context.skip_reasons.get(outs["route_bad"]) == "not_taken"


def test_a_picked_error_takes_its_branch_and_is_shown_as_recovered():
    bus, factory, workflow_map, master = _services()
    parse, mux, outs = _inline(workflow_map, "not json", [_route("route_bad", ["invalid_json"])])

    result = _run(bus, master)

    assert result["prompts"] == []
    assert outs["route_bad"] in result["done"] and outs["default"] not in result["done"]
    assert [(e["code"], e["handled"]) for e in result["errors"]] == [("invalid_json", True)]
    parse_status = [e for e in result["events"] if e["node_id"] == parse]
    assert [e["status"] for e in parse_status] == ["running", "recovered"]
    assert parse_status[-1]["reason"] == "invalid_json"
    assert master._memory_bank.read_transient(mux, "route_bad")["code"] == "invalid_json"
    assert master.run_context.skip_reasons.get(outs["default"]) == "not_taken"
    assert master.state.value == "FINISHED"


def test_any_other_error_can_pass_along_the_failed_nodes_input():
    bus, factory, workflow_map, master = _services()
    parse, mux, outs = _inline(workflow_map, "not json", [_route("route_t", ["timeout"])],
                               unmatched=True, forward="failed_input")

    result = _run(bus, master)

    assert outs[UNMATCHED_ROUTE] in result["done"]
    assert master._memory_bank.read_transient(mux, UNMATCHED_ROUTE) == "not json"


def test_an_error_nobody_picked_still_stops_as_an_error():
    bus, factory, workflow_map, master = _services()
    parse, mux, outs = _inline(workflow_map, "not json", [_route("route_t", ["timeout"])])

    result = _run(bus, master, TerminatePolicy("terminate_branch"))

    assert [e["handled"] for e in result["errors"]] == [False]
    assert [e["status"] for e in result["events"] if e["node_id"] == parse][-1] == "errored"
    assert not (result["done"] & set(outs.values()))


def test_a_mux_wired_from_the_error_port_still_works():
    bus, factory, workflow_map, master = _services()
    start = workflow_map.add_node("start_node")
    parse = workflow_map.add_node("json_path_node")
    mux = workflow_map.add_node("error_mux_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(start, {"greeting": "not json"})
    workflow_map.update_node_config(mux, {"routes": [_route("r", ["invalid_json"])]})
    workflow_map.connect(start, "default", parse, "input")
    workflow_map.connect(parse, "error", mux, "error")
    workflow_map.connect(mux, "r", handler, "input")

    result = _run(bus, master)

    assert handler in result["done"]
    assert [e["handled"] for e in result["errors"]] == [True]


# ---------------------------------------------------------------------------
# Validator and pruning
# ---------------------------------------------------------------------------


def _messages(result, key, node_id):
    return [e["message"] for e in result[key] if e.get("node_id") == node_id]


def test_validator_accepts_the_inline_layout_and_checks_codes():
    bus, factory, workflow_map, master = _services()
    parse, mux, outs = _inline(workflow_map, "x", [
        _route("route_a", ["invalid_json"], "Bad input"),
        _route("route_b", ["no_such_code"], "Typo")])

    result = validate_workflow(workflow_map, factory)

    errors = _messages(result, "errors", mux)
    assert any("route 'Typo' lists code 'no_such_code'" in m for m in errors)
    assert not any("Bad input" in m for m in errors)
    assert not any("comes from port" in m for m in errors)


def test_validator_flags_a_mux_with_nothing_feeding_it():
    bus, factory, workflow_map, master = _services()
    mux = workflow_map.add_node("error_mux_node")

    result = validate_workflow(workflow_map, factory)

    assert "Error Mux has no incoming connection" in _messages(result, "warnings", mux)


def test_unpicking_an_error_drops_its_branch_connection():
    bus, factory, workflow_map, master = _services()
    parse, mux, outs = _inline(workflow_map, "x", [_route("keep", ["invalid_json"]),
                                                   _route("gone", ["timeout"])])
    previous = workflow_map.output_ports(mux)
    workflow_map.update_node_config(mux, {"routes": [_route("keep", ["invalid_json"])]})

    assert workflow_map.prune_removed_output_connections(mux, previous) == 1
    ports = sorted(c["source_port"] for c in workflow_map.get_node_data(mux)["connections"]["outputs"])
    assert ports == ["default", "keep"]


# ---------------------------------------------------------------------------
# Config UI (frontend only): readable choices, picks -> branches
# ---------------------------------------------------------------------------


def test_errors_are_offered_in_plain_words():
    from frontend.error_mux_ui import (
        ANY_OTHER_ERROR, friendly_error_choice, friendly_error_name, recovery_choices,
        upstream_error_definitions)

    bus, factory, workflow_map, master = _services()
    http = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.connect(http, "default", mux, "input")

    definitions = upstream_error_definitions(factory, workflow_map, mux)
    assert [d["code"] for d in definitions] == [
        "node_error", "missing_url", "timeout", "network", "http_status"]
    assert friendly_error_name("http_status") == "HTTP status"
    assert friendly_error_name("missing_url") == "Missing URL"
    assert friendly_error_name("node_error") == "Unexpected failure"
    assert friendly_error_name("engine.upstream_unreachable") == \
        "A node it waits for can no longer finish"
    timeout = next(d for d in definitions if d["code"] == "timeout")
    assert friendly_error_choice(timeout) == \
        "Timeout: The server did not answer within the timeout. Retrying may help."

    choices = recovery_choices(definitions, {"routes": [_route("r", ["gone_code"])]})
    texts = [text for text, _ in choices]
    assert all("_" not in text.split(":")[0] for text in texts)
    assert choices[-2] == ("Gone code: not raised by the connected node", "gone_code")
    assert choices[-1][1] == ANY_OTHER_ERROR


def test_picks_become_branches_that_keep_their_ids():
    from frontend.error_mux_ui import ANY_OTHER_ERROR, routes_for_selection

    existing = {"routes": [_route("route_keep", ["timeout"], "Slow", forward="failed_input"),
                           _route("path_a", ["a", "b"], "Legacy")]}
    routes = routes_for_selection(["timeout", "b", "http_status", ANY_OTHER_ERROR], existing)

    assert routes[0] == {"id": "route_keep", "label": "Slow", "codes": ["timeout"],
                         "forward": "failed_input"}
    assert routes[1]["id"] == "path_a" and routes[1]["codes"] == ["b"]
    assert routes[2]["id"].startswith("route_")
    assert routes[2]["label"] == "HTTP status" and routes[2]["forward"] == "error"
    assert len(routes) == 3


def test_config_tabs_source_picks_fill_parameters_and_payloads():
    from textual.app import App
    from textual.widgets import Select, SelectionList

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    bus, factory, workflow_map, master = _services()
    http = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.connect(http, "default", mux, "input")
    screen = NodeConfigScreen(factory, workflow_map, mux, workflow_map.get_node_data(mux))

    class ConfigApp(App):
        def compose(self):
            yield screen

    async def check():
        app = ConfigApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            picker = app.query_one("#mux-recover-from", SelectionList)
            assert picker.selected == []
            assert not list(app.query(".mux-branch-row"))
            assert "HTTP Request" in str(app.query_one("#mux-guarded").render())

            picker.select("timeout")
            picker.select("http_status")
            await pilot.pause()
            await pilot.pause()
            rows = list(app.query(".mux-branch-row"))
            assert len(rows) == 2 and len(app.query(".mux-forward-row")) == 2
            labels = [w.value for w in app.query(CommandInput) if (w.id or "").startswith("mux-route-label-")]
            assert labels == ["Timeout", "HTTP status"]

            # Rename one branch and make it pass along the failed input.
            label_input = [w for w in app.query(CommandInput)
                           if (w.id or "").startswith("mux-route-label-")][0]
            label_input.value = "Try again"
            forward = [w for w in app.query(Select)
                       if (w.id or "").startswith("mux-route-forward-")][0]
            forward.value = "failed_input"
            await pilot.pause()

            # Unpick and re-pick: the branch comes back with its name and id.
            first_id = label_input.id.removeprefix("mux-route-label-")
            picker.deselect("timeout")
            await pilot.pause()
            await pilot.pause()
            assert len(app.query(".mux-branch-row")) == 1
            picker.select("timeout")
            picker.select("__any_other__")
            await pilot.pause()
            await pilot.pause()

            values = screen._error_mux_config_values()
            assert [r["codes"] for r in values["routes"]] == [["timeout"], ["http_status"]]
            assert values["routes"][0]["id"] == first_id
            assert values["routes"][0]["label"] == "Try again"
            assert values["routes"][0]["forward"] == "failed_input"
            assert values["routes"][1]["forward"] == "error"
            assert values["unmatched_route"] is True
            assert values["unmatched_label"] == "Any other error"

    asyncio.run(check())


def test_a_recovered_node_is_not_shown_as_an_error():
    from frontend.execution_state import ExecutionDisplayState
    from frontend.widgets.node_card import NodeCard

    state = ExecutionDisplayState()
    state.reset("run")
    base = {"run_id": "run", "branch_id": "b", "visit_index": 0, "node_id": "x"}
    state.node({**base, "attempt_index": 1, "status": "running"})
    state.node({**base, "attempt_index": 1, "status": "recovered", "reason": "http_status"})
    assert state.node_statuses() == {"x": "recovered"}
    assert state.skip_reasons() == {"x": "http_status"}

    card = NodeCard("x", {"type": "http_request_node", "alias": "Fetch"}, "recovered")
    card.status_detail = "http_status"
    card.refresh_card()
    assert "[recovered: HTTP status]" in card.display_text
    assert "✗" not in card.display_text

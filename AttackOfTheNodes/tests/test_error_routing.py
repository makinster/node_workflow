"""[error] routing, error codes and the skipped status (distributed step 3).

D7: errors match on stable codes; every node has the default `node_error`.
D8: the Errors section sits beside Connections.
D9: skipped is its own status with a reason, spreads downstream until it
rejoins something live, and is never counted as completed.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import (
    ERROR_LOGGED,
    NODE_EXECUTION_UPDATE,
    RECOVERY_OPTIONS_AVAILABLE,
)
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_errors import (
    DEFAULT_ERROR_CODE,
    ENGINE_UPSTREAM_UNREACHABLE,
    NodeError,
    normalize_error_definitions,
)
from backend.node_factory import NodeFactory
from backend.output_manager import OutputManager
from backend.run_policies import TerminatePolicy
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap


RUN_TIMEOUT = 5.0
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _run_records_in_tmp(tmp_path, monkeypatch):
    from backend import error_handler, output_manager, run_history

    monkeypatch.setattr(error_handler, "RUN_ERRORS_DIR", tmp_path / "run_errors")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history")
    monkeypatch.setattr(output_manager, "RUN_OUTPUTS_DIR", tmp_path / "run_outputs")


def _services() -> Tuple[EventBus, WorkflowMap, MasterState]:
    bus = EventBus()
    workflow_map = WorkflowMap(NodeFactory(), bus)
    master = MasterState(workflow_map, MemoryBank(bus), bus,
                         output_manager=OutputManager(),
                         configuration_manager=ConfigurationManager())
    workflow_map.create_new("Error routing")
    return bus, workflow_map, master


def _events(bus: EventBus) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    bus.subscribe(NODE_EXECUTION_UPDATE, events.append)
    return events


def _status(events, node_id) -> List[str]:
    return [e["status"] for e in events if e["node_id"] == node_id]


def _answer(bus, master, action) -> List[Dict[str, Any]]:
    seen: List[Dict[str, Any]] = []

    def respond(payload):
        seen.append(payload)
        master.submit_recovery_action(payload["branch_id"], action)

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, respond)
    return seen


async def _finish(master: MasterState) -> None:
    await asyncio.wait_for(master.wait_for_completion(), timeout=RUN_TIMEOUT)


def _chain(workflow_map: WorkflowMap, first: str, count: int) -> List[str]:
    ids, previous = [], first
    for _ in range(count):
        node = workflow_map.add_node("no_op_node")
        workflow_map.connect(previous, "default", node, "input")
        ids.append(node)
        previous = node
    return ids


def _never_matches(workflow_map: WorkflowMap, node: str) -> None:
    workflow_map.update_node_config(node, {"condition_type": "equals", "right_value": "never"})


# ---------------------------------------------------------------------------
# D9: skipped status and spreading
# ---------------------------------------------------------------------------


async def test_skip_spreads_through_a_linear_chain():
    bus, workflow_map, master = _services()
    events = _events(bus)
    _answer(bus, master, "TERMINATE_BRANCH")
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    workflow_map.connect(start, "default", failing, "input")
    a, b, c = _chain(workflow_map, failing, 3)

    assert await master.start_workflow()
    await _finish(master)

    reasons = master.run_context.skip_reasons
    assert reasons == {a: "upstream_failed", b: "upstream_skipped", c: "upstream_skipped"}
    for node in (a, b, c):
        assert _status(events, node) == ["skipped"]
        assert node not in master.completed_nodes
    skip_events = [e for e in events if e["status"] == "skipped"]
    assert {e["reason"] for e in skip_events} == {"upstream_failed", "upstream_skipped"}
    assert all(e["run_id"] == master.current_run_id for e in skip_events)
    history = master.run_history.list_runs()[0]
    assert history["skipped_nodes"] == reasons
    assert master.state.value == "FINISHED"


async def test_skip_stops_at_a_merge_with_a_live_sibling():
    bus, workflow_map, master = _services()
    events = _events(bus)
    _answer(bus, master, "TERMINATE_BRANCH")
    start = workflow_map.add_node("start_node")
    fork = workflow_map.add_node("branch_node")
    failing = workflow_map.add_node("error_node")
    dead = workflow_map.add_node("no_op_node")
    slow = workflow_map.add_node("sleep_node")
    merge = workflow_map.add_node("merge_node")
    after = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(slow, {"duration": 0.05})
    workflow_map.update_node_config(merge, {"selected_input_port": "path_b"})
    workflow_map.connect(start, "default", fork, "input")
    workflow_map.connect(fork, "path_a", failing, "input")
    workflow_map.connect(failing, "default", dead, "input")
    workflow_map.connect(dead, "default", merge, "path_a")
    workflow_map.connect(fork, "path_b", slow, "input")
    workflow_map.connect(slow, "default", merge, "path_b")
    workflow_map.connect(merge, "default", after, "input")

    assert await master.start_workflow()
    await _finish(master)

    assert master.run_context.skip_reasons == {dead: "upstream_failed"}
    assert "done" in _status(events, merge)
    assert "done" in _status(events, after)
    assert merge in master.completed_nodes


async def test_untaken_conditional_port_is_skipped_not_taken():
    bus, workflow_map, master = _services()
    events = _events(bus)
    start = workflow_map.add_node("start_node")
    condition = workflow_map.add_node("conditional_node")
    _never_matches(workflow_map, condition)
    true_a = workflow_map.add_node("no_op_node")
    true_b = workflow_map.add_node("no_op_node")
    false_path = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", condition, "input")
    workflow_map.connect(condition, "true", true_a, "input")
    workflow_map.connect(true_a, "default", true_b, "input")
    workflow_map.connect(condition, "false", false_path, "input")

    assert await master.start_workflow()
    await _finish(master)

    assert master.run_context.skip_reasons == {
        true_a: "not_taken", true_b: "upstream_skipped"}
    assert _status(events, false_path)[-1] == "done"


async def test_routing_to_the_error_port_skips_the_default_path():
    bus, workflow_map, master = _services()
    events = _events(bus)
    recoveries = _answer(bus, master, "TERMINATE_BRANCH")
    start = workflow_map.add_node("start_node")
    parse = workflow_map.add_node("json_path_node")
    default_next = workflow_map.add_node("no_op_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(start, {"greeting": "not json"})
    workflow_map.connect(start, "default", parse, "input")
    workflow_map.connect(parse, "default", default_next, "input")
    workflow_map.connect(parse, "error", handler, "input")

    assert await master.start_workflow()
    await _finish(master)

    assert recoveries == []
    assert master.run_context.skip_reasons == {default_next: "not_taken"}
    assert parse not in master.completed_nodes
    assert _status(events, parse) == ["running", "errored"]
    assert _status(events, handler)[-1] == "done"
    payload = master._memory_bank.read_transient(parse, "error")
    assert payload["code"] == "invalid_json"


async def test_recovery_skip_ends_the_branch_and_spreads():
    bus, workflow_map, master = _services()
    events = _events(bus)
    _answer(bus, master, "SKIP")
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    workflow_map.connect(start, "default", failing, "input")
    a, b = _chain(workflow_map, failing, 2)

    assert await master.start_workflow()
    await _finish(master)

    assert master.run_context.skip_reasons == {
        failing: "recovery_skip", a: "upstream_skipped", b: "upstream_skipped"}
    assert "running" not in _status(events, a)
    skipped = [e for e in events if e["node_id"] == failing and e["status"] == "skipped"]
    assert skipped and skipped[0]["reason"] == "recovery_skip"
    assert not {failing, a, b} & master.completed_nodes


async def test_wait_until_on_a_skipped_target_fails_with_upstream_unreachable():
    bus, workflow_map, master = _services()
    recoveries = _answer(bus, master, "TERMINATE_BRANCH")
    start = workflow_map.add_node("start_node")
    fork = workflow_map.add_node("branch_node")
    condition = workflow_map.add_node("conditional_node")
    _never_matches(workflow_map, condition)
    target = workflow_map.add_node("no_op_node")
    waiter = workflow_map.add_node("wait_until_node")
    workflow_map.update_node_config(waiter, {"target_node_ids": target})
    workflow_map.connect(start, "default", fork, "input")
    workflow_map.connect(fork, "path_a", waiter, "input")
    workflow_map.connect(fork, "path_b", condition, "input")
    workflow_map.connect(condition, "true", target, "input")

    assert await master.start_workflow()
    await _finish(master)

    assert master.run_context.skip_reasons[target] == "not_taken"
    waiter_failures = [r for r in recoveries if r["node_id"] == waiter]
    assert len(waiter_failures) == 1
    assert waiter_failures[0]["code"] == ENGINE_UPSTREAM_UNREACHABLE
    assert waiter_failures[0]["error"]["code"] == ENGINE_UPSTREAM_UNREACHABLE


def _mux_workflow(workflow_map: WorkflowMap, codes: str):
    start = workflow_map.add_node("start_node")
    parse = workflow_map.add_node("json_path_node")
    mux = workflow_map.add_node("error_mux_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(start, {"greeting": "not json"})
    workflow_map.update_node_config(mux, {"path_a_codes": codes})
    workflow_map.connect(start, "default", parse, "input")
    workflow_map.connect(parse, "error", mux, "error")
    workflow_map.connect(mux, "path_a", handler, "input")
    return parse, mux, handler


async def test_mux_with_a_matching_code_routes_to_its_path():
    bus, workflow_map, master = _services()
    events = _events(bus)
    recoveries = _answer(bus, master, "TERMINATE_BRANCH")
    parse, mux, handler = _mux_workflow(workflow_map, "timeout, invalid_json")

    assert await master.start_workflow()
    await _finish(master)

    assert recoveries == []
    assert _status(events, mux)[-1] == "done"
    assert _status(events, handler)[-1] == "done"
    routed = master._memory_bank.read_transient(mux, "path_a")
    assert routed["code"] == "invalid_json"


@pytest.mark.parametrize("policy,state", [
    ("terminate_branch", "FINISHED"), ("terminate_workflow", "ERROR")])
async def test_mux_without_a_matching_code_falls_through_to_the_policy(policy, state):
    bus, workflow_map, master = _services()
    events = _events(bus)
    parse, mux, handler = _mux_workflow(workflow_map, "node_error")

    assert await master.start_workflow(recovery_policy=TerminatePolicy(policy))
    await _finish(master)

    assert master.state.value == state
    assert "running" not in _status(events, mux)
    errors = master.error_handler.get_errors_for_run(master.current_run_id)
    assert [e["code"] for e in errors] == ["invalid_json"]


async def test_mux_can_pass_the_failed_nodes_input_down_its_path():
    bus, workflow_map, master = _services()
    recoveries = _answer(bus, master, "TERMINATE_BRANCH")
    parse, mux, handler = _mux_workflow(workflow_map, "invalid_json")
    workflow_map.update_node_config(mux, {"path_a_codes": "invalid_json", "forward": "failed_input"})

    assert await master.start_workflow()
    await _finish(master)

    assert recoveries == []
    given = master._memory_bank.read_transient(
        *workflow_map.find_input_source(parse, "input").values()
    )
    assert given is not None
    assert master._memory_bank.read_transient(mux, "path_a") == given
    # The error payload is still on the failed node's error slot.
    assert master._memory_bank.read_transient(parse, "error")["code"] == "invalid_json"
    assert handler in master.completed_nodes


async def test_a_catch_all_node_does_not_get_the_failed_input():
    bus, workflow_map, master = _services()
    _answer(bus, master, "TERMINATE_BRANCH")
    seen: List[Dict[str, Any]] = []
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", failing, "input")
    workflow_map.connect(failing, "error", handler, "input")
    original = master._new_supervisor

    def spy(run, **kwargs):
        supervisor = original(run, **kwargs)
        prepare = supervisor._prepare_inputs

        def record(node):
            inputs = prepare(node)
            seen.append(inputs)
            return inputs

        supervisor._prepare_inputs = record
        return supervisor

    master._new_supervisor = spy
    assert await master.start_workflow()
    await _finish(master)

    assert seen and all("failed_input" not in inputs for inputs in seen)


async def test_mux_without_a_matching_code_pauses_for_recovery_when_attended():
    bus, workflow_map, master = _services()
    recoveries = _answer(bus, master, "TERMINATE_BRANCH")
    parse, _, _ = _mux_workflow(workflow_map, "node_error")

    assert await master.start_workflow()
    await _finish(master)

    assert [r["node_id"] for r in recoveries] == [parse]
    assert recoveries[0]["code"] == "invalid_json"


async def test_a_skipped_node_is_never_counted_as_completed():
    bus, workflow_map, master = _services()
    completed_calls: List[str] = []
    original = master.mark_node_completed

    async def spy(node_id):
        completed_calls.append(node_id)
        await original(node_id)

    master.mark_node_completed = spy
    _answer(bus, master, "SKIP")
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    workflow_map.connect(start, "default", failing, "input")
    (after,) = _chain(workflow_map, failing, 1)

    assert await master.start_workflow()
    await _finish(master)

    skipped = set(master.run_context.skip_reasons)
    assert skipped == {failing, after}
    assert not skipped & set(completed_calls)
    assert not skipped & master.completed_nodes


# ---------------------------------------------------------------------------
# Engine-level error port and the error payload
# ---------------------------------------------------------------------------


async def test_any_node_can_route_failures_along_its_error_port():
    bus, workflow_map, master = _services()
    events = _events(bus)
    recoveries = _answer(bus, master, "TERMINATE_BRANCH")
    logged: List[Dict[str, Any]] = []
    bus.subscribe(ERROR_LOGGED, logged.append)
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", failing, "input")
    workflow_map.connect(failing, "error", handler, "input")

    assert await master.start_workflow()
    await _finish(master)

    assert recoveries == []
    assert _status(events, handler)[-1] == "done"
    payload = master._memory_bank.read_transient(failing, "error")
    assert payload == {
        "version": 1,
        "code": DEFAULT_ERROR_CODE,
        "message": "Deliberate error from ErrorNode",
        "node_id": failing,
        "run_id": master.current_run_id,
        "stage": "execute",
        "details": {},
        "retryable": False,
        "error_id": logged[0]["error"]["id"],
    }
    assert logged[0]["error"]["code"] == DEFAULT_ERROR_CODE
    result = validate_workflow(workflow_map, workflow_map._factory)
    assert not [e for e in result["errors"] if "undeclared port 'error'" in e["message"]]


async def test_undeclared_node_error_code_falls_back_to_the_default():
    from backend.nodes.debug.error_node import ErrorNode
    from backend.supervisor import Supervisor

    bus = EventBus()
    supervisor = Supervisor("r", "b", 0, "n", WorkflowMap(NodeFactory(), bus), MemoryBank(bus), bus)
    node = ErrorNode("n")
    failure = supervisor._describe_failure(node, NodeError("made_up", "boom", details={"x": 1}))
    assert failure.code == DEFAULT_ERROR_CODE
    assert failure.details == {"x": 1, "undeclared_code": "made_up"}
    plain = supervisor._describe_failure(node, ValueError("bad"))
    assert plain.code == DEFAULT_ERROR_CODE and plain.retryable is False


async def test_declared_retryable_flag_reaches_the_payload():
    from backend.supervisor import Supervisor

    bus = EventBus()
    factory = NodeFactory()
    supervisor = Supervisor("r", "b", 0, "n", WorkflowMap(factory, bus), MemoryBank(bus), bus)
    node = factory.create_node("http_request_node", "n")
    failure = supervisor._describe_failure(node, NodeError("timeout", "slow"))
    assert failure.code == "timeout" and failure.retryable is True


@pytest.mark.parametrize("failure,code", [
    (TimeoutError("timed out"), "timeout"),
    (__import__("urllib.error").error.URLError("refused"), "network"),
    (__import__("urllib.error").error.URLError(TimeoutError("t")), "timeout"),
])
async def test_http_request_failures_carry_declared_codes(failure, code):
    from unittest.mock import patch
    from tests.test_run_lifecycle import _http_context

    node = NodeFactory().create_node("http_request_node", "n1")
    node.config["url"] = "http://example.invalid/"
    done: List[Dict[str, Any]] = []
    with patch("urllib.request.urlopen", side_effect=failure):
        await node.execute(_http_context(done))
    assert done[0]["output_port"] == "error"
    assert done[0]["data"]["code"] == code
    assert done[0]["data"]["error"]


# ---------------------------------------------------------------------------
# Regressions from the step 3 review
# ---------------------------------------------------------------------------


async def test_shared_mux_reads_the_payload_of_the_node_that_failed():
    bus, workflow_map, master = _services()
    recoveries = _answer(bus, master, "TERMINATE_BRANCH")
    start = workflow_map.add_node("start_node")
    healthy = workflow_map.add_node("no_op_node")
    failing = workflow_map.add_node("error_node")
    mux = workflow_map.add_node("error_mux_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(mux, {"path_a_codes": DEFAULT_ERROR_CODE})
    workflow_map.connect(start, "default", healthy, "input")
    workflow_map.connect(healthy, "default", failing, "input")
    # The healthy node's error slot is connected first and stays empty.
    workflow_map.connect(healthy, "error", mux, "error")
    workflow_map.connect(failing, "error", mux, "error")
    workflow_map.connect(mux, "path_a", handler, "input")

    assert await master.start_workflow()
    await _finish(master)

    assert recoveries == []
    routed = master._memory_bank.read_transient(mux, "path_a")
    assert routed["node_id"] == failing
    assert routed["code"] == DEFAULT_ERROR_CODE
    assert handler in master.completed_nodes


async def test_non_json_error_details_and_inputs_are_logged_safely():
    import json

    from backend.nodes.debug.error_node import ErrorNode
    from backend.supervisor import Supervisor

    bus = EventBus()
    supervisor = Supervisor("r", "b", 0, "n", WorkflowMap(NodeFactory(), bus), MemoryBank(bus), bus)
    supervisor.current_node_id = "n"
    failure = supervisor._describe_failure(
        ErrorNode("n"), NodeError(DEFAULT_ERROR_CODE, "boom", details={"stderr": b"\xff oops"})
    )
    assert failure.details == {"stderr": "\ufffd oops"}
    record = supervisor._log_failure(failure, {"input": b"\x00\xff", "other": {1, 2}})
    json.dumps(record)
    assert record["code"] == DEFAULT_ERROR_CODE
    second = supervisor._log_failure(failure, {})
    assert second["code"] == DEFAULT_ERROR_CODE


async def test_a_long_linear_run_does_not_rescan_for_skips_per_node(monkeypatch):
    from backend.run_context import RunContext

    calls: List[int] = []
    original = RunContext.skip_candidates

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(RunContext, "skip_candidates", counting)
    bus, workflow_map, master = _services()
    start = workflow_map.add_node("start_node")
    _chain(workflow_map, start, 30)

    assert await master.start_workflow()
    await _finish(master)

    assert master.state.value == "FINISHED"
    assert len(calls) <= 2


async def test_an_unused_error_path_is_skipped_after_a_completed_node():
    bus, workflow_map, master = _services()
    start = workflow_map.add_node("start_node")
    (worker,) = _chain(workflow_map, start, 1)
    handler = workflow_map.add_node("no_op_node")
    workflow_map.connect(worker, "error", handler, "input")

    assert await master.start_workflow()
    await _finish(master)

    assert master.run_context.skip_reasons == {handler: "not_taken"}


async def test_stop_during_a_recovery_prompt_does_not_mark_skips():
    bus, workflow_map, master = _services()
    # Stop from inside the prompt: the supervisor resolves its own pending
    # recovery as terminate rather than being cancelled.
    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, lambda payload: master.stop())
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    workflow_map.connect(start, "default", failing, "input")
    _chain(workflow_map, failing, 2)

    assert await master.start_workflow()
    await _finish(master)

    assert master.run_context.skip_reasons == {}


# ---------------------------------------------------------------------------
# D7 declarations, D8 Errors section, validator
# ---------------------------------------------------------------------------


def test_every_node_lists_the_default_generic_code_first():
    for meta in NodeFactory().get_node_types_metadata():
        assert meta["errors"][0]["code"] == DEFAULT_ERROR_CODE, meta["type"]
        assert meta["error_port"] == "error"


def test_engine_codes_are_declared_where_they_are_raised():
    by_type = {m["type"]: m for m in NodeFactory().get_node_types_metadata()}
    assert ENGINE_UPSTREAM_UNREACHABLE in [e["code"] for e in by_type["wait_until_node"]["errors"]]
    assert "engine.unattended_input" in [
        e["code"] for e in by_type["user_text_input_node"]["errors"]]


@pytest.mark.parametrize("bad", [
    [{"code": "Bad Code", "description": "x"}],
    [{"code": "engine.mine", "description": "x"}],
    [{"code": "node_error", "description": "x"}],
    [{"code": "a", "description": "x"}, {"code": "a", "description": "y"}],
    [{"code": "a", "description": ""}],
    [{"code": "a", "description": "x", "retryable": "yes"}],
    [{"code": "a", "description": "x", "extra": 1}],
])
def test_bad_error_declarations_are_rejected(bad):
    with pytest.raises(ValueError):
        normalize_error_definitions(bad)


def test_helper_generator_validates_and_emits_errors(tmp_path):
    sys.path.insert(0, str(WORKSPACE_ROOT))
    from aotn_node_helper.generator import normalize_spec, render_node_file, render_test_file

    spec = {
        "node_type": "coded_probe_node", "primary_family": "Utility",
        "input_ports": ["input"], "output_ports": ["default"],
        "errors": [{"code": "too_big", "description": "Input too big", "retryable": True}],
    }
    normalized = normalize_spec(spec)
    assert normalized["error_definitions"] == [
        {"code": "too_big", "description": "Input too big", "retryable": True}]
    assert "error_definitions: ClassVar" in render_node_file(normalized)
    assert "['node_error', 'too_big']" in render_test_file(normalized)
    with pytest.raises(ValueError):
        normalize_spec({**spec, "errors": [{"code": "engine.x", "description": "no"}]})


@pytest.mark.parametrize("node_type", [
    "error_mux_node", "http_request_node", "wait_until_node", "user_text_input_node"])
def test_errors_section_renders_beside_connections(node_type):
    sys.path.insert(0, str(WORKSPACE_ROOT))
    from aotn_node_helper.ui_checks import run_ui_check

    problems = [p for p in run_ui_check(node_type) if "Error" in p or "Connections" in p]
    assert problems == []


def test_validator_checks_mux_codes_against_upstream_declarations():
    _, workflow_map, _ = _services()
    _, mux, _ = _mux_workflow(workflow_map, "invalid_json, timeout")
    result = validate_workflow(workflow_map, workflow_map._factory)
    messages = [e["message"] for e in result["errors"] if e["node_id"] == mux]
    assert len(messages) == 1 and "'timeout'" in messages[0]

    workflow_map.update_node_config(mux, {"path_a_codes": "invalid_json, node_error, "
                                                          "engine.upstream_unreachable"})
    result = validate_workflow(workflow_map, workflow_map._factory)
    assert not [e for e in result["errors"] if e["node_id"] == mux]


def test_validator_rejects_a_mux_fed_from_a_non_error_port():
    _, workflow_map, _ = _services()
    start = workflow_map.add_node("start_node")
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.update_node_config(mux, {"path_a_codes": "node_error"})
    workflow_map.connect(start, "default", mux, "error")
    result = validate_workflow(workflow_map, workflow_map._factory)
    assert any("connect a node's 'error' port" in e["message"]
               for e in result["errors"] if e["node_id"] == mux)


# ---------------------------------------------------------------------------
# Execution screen shows skipped distinctly, with its reason
# ---------------------------------------------------------------------------


def test_execution_state_keeps_skip_reasons_and_cards_show_them():
    from frontend.execution_state import ExecutionDisplayState
    from frontend.widgets.node_card import NodeCard

    state = ExecutionDisplayState()
    state.reset("run")
    base = {"run_id": "run", "branch_id": "b", "attempt_index": 0}
    state.node({**base, "node_id": "x", "visit_index": 0, "status": "skipped",
                "reason": "not_taken"})
    state.node({**base, "node_id": "y", "visit_index": 1, "attempt_index": 1, "status": "done"})
    assert state.node_statuses() == {"x": "skipped", "y": "done"}
    assert state.skip_reasons() == {"x": "not_taken"}

    card = NodeCard("x", {"type": "no_op_node", "alias": "X"}, "skipped")
    card.status_detail = "not_taken"
    card.refresh_card()
    assert "[skipped: not taken]" in card.display_text

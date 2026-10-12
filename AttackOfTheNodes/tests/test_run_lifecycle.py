"""Run lifecycle regression tests built from the 2026-10-09 probes.

Covers distributed build plan step 1: error-port routing (1a), Stop and the
leak into the next run (1b-fix), and the unattended policy (1c).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import pytest

from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import (
    NODE_EXECUTION_UPDATE,
    RECOVERY_OPTIONS_AVAILABLE,
)
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_factory import NodeFactory
from backend.output_manager import OutputManager
from backend.workflow_map import WorkflowMap


RUN_TIMEOUT = 5.0


def _services() -> Tuple[EventBus, WorkflowMap, MasterState]:
    bus = EventBus()
    workflow_map = WorkflowMap(NodeFactory(), bus)
    master = MasterState(
        workflow_map,
        MemoryBank(bus),
        bus,
        output_manager=OutputManager(),
        configuration_manager=ConfigurationManager(),
    )
    workflow_map.create_new("Run lifecycle")
    return bus, workflow_map, master


def _record_node_events(bus: EventBus) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    bus.subscribe(NODE_EXECUTION_UPDATE, events.append)
    return events


def _ran(events: List[Dict[str, Any]], node_id: str, run_id: str = "") -> bool:
    return any(
        event["node_id"] == node_id
        and event["status"] == "done"
        and (not run_id or event["run_id"] == run_id)
        for event in events
    )


async def _finish(master: MasterState) -> None:
    await asyncio.wait_for(master.wait_for_completion(), timeout=RUN_TIMEOUT)


def _json_path_workflow(workflow_map: WorkflowMap, connect_error: bool):
    """start -> json_path (fed invalid JSON) -> default_sink [/ error_sink]."""
    start = workflow_map.add_node("start_node")
    parse = workflow_map.add_node("json_path_node")
    default_sink = workflow_map.add_node("no_op_node")
    error_sink = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(start, {"greeting": "not json"})
    workflow_map.update_node_config(parse, {"path": "key"})
    workflow_map.connect(start, "default", parse, "input")
    workflow_map.connect(parse, "default", default_sink, "input")
    if connect_error:
        workflow_map.connect(parse, "error", error_sink, "input")
    return parse, default_sink, error_sink


# ---------------------------------------------------------------------------
# 1a. Error-port routing
# ---------------------------------------------------------------------------


async def test_failure_routes_along_connected_error_port():
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    recoveries: List[Dict[str, Any]] = []
    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, recoveries.append)
    parse, default_sink, error_sink = _json_path_workflow(workflow_map, True)

    assert await master.start_workflow()
    await _finish(master)

    assert master.state.value == "FINISHED"
    assert recoveries == []
    assert _ran(events, error_sink)
    assert not _ran(events, default_sink)
    assert "Invalid JSON" in master._memory_bank.read_transient(parse, "error")


async def test_failure_on_unconnected_error_port_requests_recovery():
    """No silent routing of failures down ``default``."""
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    recoveries: List[Dict[str, Any]] = []

    def terminate_branch(payload: Dict[str, Any]) -> None:
        recoveries.append(payload)
        master.submit_recovery_action(payload["branch_id"], "TERMINATE_BRANCH")

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, terminate_branch)
    parse, default_sink, _ = _json_path_workflow(workflow_map, False)

    assert await master.start_workflow()
    await _finish(master)

    assert len(recoveries) == 1
    assert recoveries[0]["node_id"] == parse
    assert "Invalid JSON" in recoveries[0]["error_message"]
    assert not _ran(events, default_sink)
    assert any(
        event["node_id"] == parse and event["status"] == "errored" for event in events
    )
    errors = master.error_handler.get_errors_for_run(master.current_run_id)
    assert len(errors) == 1


async def test_retry_after_unconnected_error_port_reruns_the_node():
    bus, workflow_map, master = _services()
    actions = iter(["RETRY", "TERMINATE_BRANCH"])
    recoveries: List[Dict[str, Any]] = []

    def respond(payload: Dict[str, Any]) -> None:
        recoveries.append(payload)
        master.submit_recovery_action(payload["branch_id"], next(actions))

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, respond)
    _json_path_workflow(workflow_map, False)

    assert await master.start_workflow()
    await _finish(master)

    assert len(recoveries) == 2


def _http_context(done: List[Dict[str, Any]]) -> NodeContext:
    return NodeContext(
        node_id="n1",
        branch_id="b",
        run_id="r",
        inputs={"input": ""},
        memory_bank=MemoryBank(EventBus()),
        signal_done=done.append,
        signal_error=lambda exc: None,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
    )


@pytest.mark.parametrize(
    "failure",
    [TimeoutError("timed out"), __import__("urllib.error").error.URLError("refused")],
    ids=["socket-timeout", "url-error"],
)
async def test_http_request_failures_signal_the_error_port(failure):
    node = NodeFactory().create_node("http_request_node", "n1")
    node.config["url"] = "http://example.invalid/"
    done: List[Dict[str, Any]] = []
    with patch("urllib.request.urlopen", side_effect=failure):
        await node.execute(_http_context(done))
    assert done[0]["output_port"] == "error"
    assert done[0]["data"]["error"]


async def test_http_request_missing_url_signals_the_error_port():
    node = NodeFactory().create_node("http_request_node", "n1")
    done: List[Dict[str, Any]] = []
    await node.execute(_http_context(done))
    assert done[0]["output_port"] == "error"
    assert "URL" in done[0]["data"]["error"]


async def test_json_path_success_still_routes_default():
    node = NodeFactory().create_node("json_path_node", "n1")
    node.config["path"] = "a"
    done: List[Dict[str, Any]] = []
    context = _http_context(done)
    context.inputs = {"input": '{"a": 1}'}
    await node.execute(context)
    assert done[0] == {"data": {"default": 1}}


# ---------------------------------------------------------------------------
# 1b-fix. Stop and the leak into the next run
# ---------------------------------------------------------------------------


def _wait_until_workflow(workflow_map: WorkflowMap):
    """start -> wait_until(target) -> after; target is never reached."""
    start = workflow_map.add_node("start_node")
    waiter = workflow_map.add_node("wait_until_node")
    after = workflow_map.add_node("no_op_node")
    target = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(waiter, {"target_node_ids": target})
    workflow_map.connect(start, "default", waiter, "input")
    workflow_map.connect(waiter, "default", after, "input")
    return waiter, after, target


async def _until_waiting(events: List[Dict[str, Any]], node_id: str, run_id: str) -> None:
    async def poll() -> None:
        while not any(
            event["node_id"] == node_id
            and event["run_id"] == run_id
            and event["status"] == "running"
            for event in events
        ):
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), timeout=RUN_TIMEOUT)
    # Let the node reach its await on the completion condition.
    await asyncio.sleep(0.02)


async def test_stop_releases_a_waiting_wait_until():
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    waiter, after, _ = _wait_until_workflow(workflow_map)

    assert await master.start_workflow()
    run_id = master.current_run_id
    await _until_waiting(events, waiter, run_id)
    assert master.state.value == "RUNNING"

    master.stop()
    await _finish(master)

    assert master.state.value != "RUNNING"
    assert master._supervisor_tasks == {}
    assert not _ran(events, after)
    assert any(
        event["node_id"] == waiter and event["status"] == "stopped" for event in events
    )
    assert master.run_history.list_runs()[0]["run_id"] == run_id


async def test_stopped_wait_until_does_not_wake_in_the_next_run():
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    waiter, after, target = _wait_until_workflow(workflow_map)

    assert await master.start_workflow()
    first_run = master.current_run_id
    await _until_waiting(events, waiter, first_run)
    master.stop()

    assert await master.start_workflow()
    second_run = master.current_run_id
    assert second_run != first_run
    await _until_waiting(events, waiter, second_run)

    # The target completes in the second run; only that run's waiter may wake.
    await master.mark_node_completed(target)
    await _finish(master)
    # A leaked task is not tracked by wait_for_completion; give it time to run.
    await asyncio.sleep(0.1)

    assert _ran(events, after, second_run)
    # The first run's waiter must neither finish (writing its output into the
    # second run's memory) nor run its downstream node.
    assert not _ran(events, waiter, first_run)
    assert not any(
        event["run_id"] == first_run and event["node_id"] == after
        for event in events
    )


async def test_starting_a_new_run_without_stop_cancels_leftover_supervisors():
    """start_workflow must cancel and await old tasks, not just forget them."""
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    waiter, after, target = _wait_until_workflow(workflow_map)

    assert await master.start_workflow()
    first_run = master.current_run_id
    await _until_waiting(events, waiter, first_run)
    leftover = list(master._supervisor_tasks.values())

    assert await master.start_workflow()
    second_run = master.current_run_id
    assert all(task.done() for task in leftover)

    await _until_waiting(events, waiter, second_run)
    await master.mark_node_completed(target)
    await _finish(master)

    assert _ran(events, after, second_run)
    assert not _ran(events, after, first_run)


# ---------------------------------------------------------------------------
# 1c. Unattended policy
# ---------------------------------------------------------------------------

POLICIES = ["terminate_branch", "terminate_workflow"]
EXPECTED_FINAL_STATE = {"terminate_branch": "FINISHED", "terminate_workflow": "ERROR"}


def _client_prompts(bus: EventBus) -> List[str]:
    """Record every request that would need a client to answer."""
    from backend.events import BREAKPOINT_HIT, USER_INPUT_NEEDED

    prompts: List[str] = []
    for event in (RECOVERY_OPTIONS_AVAILABLE, USER_INPUT_NEEDED, BREAKPOINT_HIT):
        bus.subscribe(event, lambda payload, name=event: prompts.append(name))
    return prompts


@pytest.mark.parametrize("policy", POLICIES)
async def test_unattended_run_does_not_hang_on_an_error(policy):
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    prompts = _client_prompts(bus)
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    after = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", failing, "input")
    workflow_map.connect(failing, "default", after, "input")

    assert await master.start_workflow(unattended=policy)
    await _finish(master)

    assert prompts == []
    assert master.state.value == EXPECTED_FINAL_STATE[policy]
    assert not _ran(events, after)
    history = master.run_history.list_runs()[0]
    assert history["run_id"] == master.current_run_id
    assert history["error_count"] == 1


@pytest.mark.parametrize("policy", POLICIES)
async def test_unattended_run_does_not_hang_on_an_input_request(policy):
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    prompts = _client_prompts(bus)
    logged: List[Dict[str, Any]] = []
    from backend.events import ERROR_LOGGED

    bus.subscribe(ERROR_LOGGED, logged.append)
    start = workflow_map.add_node("start_node")
    ask = workflow_map.add_node("user_text_input_node")
    after = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", ask, "input")
    workflow_map.connect(ask, "default", after, "input")

    assert await master.start_workflow(unattended=policy)
    await _finish(master)

    assert prompts == []
    assert master.state.value == EXPECTED_FINAL_STATE[policy]
    assert not _ran(events, after)
    assert any(event["node_id"] == ask and event["status"] == "errored" for event in events)
    assert len(logged) == 1
    assert "unattended" in str(logged[0]).lower()


@pytest.mark.parametrize("policy", POLICIES)
async def test_unattended_run_skips_breakpoints(policy):
    bus, workflow_map, master = _services()
    events = _record_node_events(bus)
    prompts = _client_prompts(bus)
    start = workflow_map.add_node("start_node")
    paused = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", paused, "input")
    workflow_map.set_breakpoint(paused, True)

    assert await master.start_workflow(unattended=policy)
    await _finish(master)

    assert prompts == []
    assert master.state.value == "FINISHED"
    assert _ran(events, paused)


async def test_unattended_policy_applies_to_branch_supervisors():
    bus, workflow_map, master = _services()
    prompts = _client_prompts(bus)
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    workflow_map.connect(start, "default", branch, "input")
    ports = [port for port in workflow_map.get_node_instance(branch).get_output_ports()]
    for port in ports[:2]:
        failing = workflow_map.add_node("error_node")
        workflow_map.connect(branch, port, failing, "input")

    assert await master.start_workflow(unattended="terminate_branch")
    await _finish(master)

    assert prompts == []
    assert master.state.value == "FINISHED"
    assert master.run_history.list_runs()[0]["error_count"] == 2


async def test_attended_run_still_waits_for_a_recovery_choice():
    """The TUI passes nothing; recovery keeps waiting for the client."""
    bus, workflow_map, master = _services()
    recoveries: List[Dict[str, Any]] = []
    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, recoveries.append)
    start = workflow_map.add_node("start_node")
    failing = workflow_map.add_node("error_node")
    workflow_map.connect(start, "default", failing, "input")

    assert await master.start_workflow()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(master.wait_for_completion()), 0.2)
    assert len(recoveries) == 1
    master.submit_recovery_action(recoveries[0]["branch_id"], "TERMINATE_BRANCH")
    await _finish(master)


async def test_unknown_unattended_policy_is_rejected():
    _, workflow_map, master = _services()
    workflow_map.add_node("start_node")
    with pytest.raises(ValueError):
        await master.start_workflow(unattended="ignore")

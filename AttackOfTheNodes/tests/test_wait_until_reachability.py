"""Structural unreachable rule (D5) and Wait Until (distributed step 1b).

A waited-on node is unreachable when every incoming connection's source is
final, none of them routed to it, and no live supervisor can still reach those
sources. The rule never uses a timeout.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import pytest

from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import (
    ERROR_LOGGED,
    NODE_EXECUTION_UPDATE,
    RECOVERY_OPTIONS_AVAILABLE,
    USER_INPUT_NEEDED,
)
from backend.flow_behaviors import MergePlanError
from backend.run_context import MergePlan, MergeSlot
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.output_manager import OutputManager
from backend.run_context import RunContext
from backend.run_session import RunSession
from backend.wait_registry import TargetUnreachableError
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
    workflow_map.create_new("Reachability")
    return bus, workflow_map, master


def _statuses(bus: EventBus) -> List[Tuple[str, str]]:
    events: List[Tuple[str, str]] = []
    bus.subscribe(NODE_EXECUTION_UPDATE, lambda p: events.append((p["node_id"], p["status"])))
    return events


def _recoveries(bus: EventBus, master: MasterState, action: str = "TERMINATE_BRANCH"):
    seen: List[Dict[str, Any]] = []

    def respond(payload: Dict[str, Any]) -> None:
        seen.append(payload)
        master.submit_recovery_action(payload["branch_id"], action)

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, respond)
    return seen


async def _finish(master: MasterState) -> None:
    await asyncio.wait_for(master.wait_for_completion(), timeout=RUN_TIMEOUT)


def _fork(workflow_map: WorkflowMap):
    """start -> branch_node; returns (branch_node, path_a, path_b)."""
    start = workflow_map.add_node("start_node")
    fork = workflow_map.add_node("branch_node")
    workflow_map.connect(start, "default", fork, "input")
    return fork, "path_a", "path_b"


def _waiter_on(workflow_map: WorkflowMap, target: str, upstream: str, port: str) -> str:
    waiter = workflow_map.add_node("wait_until_node")
    workflow_map.update_node_config(waiter, {"target_node_ids": target})
    workflow_map.connect(upstream, port, waiter, "input")
    after = workflow_map.add_node("no_op_node")
    workflow_map.connect(waiter, "default", after, "input")
    return waiter


# ---------------------------------------------------------------------------
# Wait Until in real runs
# ---------------------------------------------------------------------------


async def test_wait_until_fails_when_its_target_errors_and_its_branch_is_terminated():
    """The Oct 9 hang: target errored, branch terminated, waiter waited forever."""
    bus, workflow_map, master = _services()
    events = _statuses(bus)
    recoveries = _recoveries(bus, master)
    fork, path_a, path_b = _fork(workflow_map)
    slow = workflow_map.add_node("sleep_node")
    workflow_map.update_node_config(slow, {"duration": 0.05})
    target = workflow_map.add_node("error_node")
    workflow_map.connect(fork, path_b, slow, "input")
    workflow_map.connect(slow, "default", target, "input")
    waiter = _waiter_on(workflow_map, target, fork, path_a)

    assert await master.start_workflow()
    await _finish(master)

    failed = [r for r in recoveries if r["node_id"] == waiter]
    assert len(failed) == 1
    assert target in failed[0]["error_message"]
    assert "can no longer complete" in failed[0]["error_message"]
    assert (waiter, "errored") in events
    assert master.state.value == "FINISHED"


async def test_wait_until_fails_when_its_targets_only_source_fails():
    """Target one hop past a terminated failure: its source is final, no delivery."""
    bus, workflow_map, master = _services()
    recoveries = _recoveries(bus, master)
    fork, path_a, path_b = _fork(workflow_map)
    failing = workflow_map.add_node("error_node")
    target = workflow_map.add_node("no_op_node")
    workflow_map.connect(fork, path_b, failing, "input")
    workflow_map.connect(failing, "default", target, "input")
    waiter = _waiter_on(workflow_map, target, fork, path_a)

    assert await master.start_workflow()
    await _finish(master)

    assert [r["node_id"] for r in recoveries].count(waiter) == 1


async def test_target_with_no_incoming_connections_is_refused_before_start():
    bus, workflow_map, master = _services()
    recoveries = _recoveries(bus, master)
    start = workflow_map.add_node("start_node")
    orphan = workflow_map.add_node("no_op_node")
    _waiter_on(workflow_map, orphan, start, "default")

    with pytest.raises(MergePlanError, match="cannot run on an active control path"):
        await master.start_workflow()
    assert master.current_run_id is None and master.run_context is None
    assert not recoveries and not master._supervisor_tasks


async def test_target_on_an_untaken_conditional_port_is_unreachable():
    bus, workflow_map, master = _services()
    recoveries = _recoveries(bus, master)
    fork, path_a, path_b = _fork(workflow_map)
    condition = workflow_map.add_node("conditional_node")
    workflow_map.update_node_config(
        condition, {"condition_type": "equals", "right_value": "never matches"}
    )
    target = workflow_map.add_node("no_op_node")
    taken = workflow_map.add_node("no_op_node")
    workflow_map.connect(fork, path_b, condition, "input")
    workflow_map.connect(condition, "true", target, "input")
    workflow_map.connect(condition, "false", taken, "input")
    waiter = _waiter_on(workflow_map, target, fork, path_a)

    assert await master.start_workflow()
    await _finish(master)

    assert [r["node_id"] for r in recoveries] == [waiter]


async def test_long_wait_on_a_reachable_target_is_never_failed_by_the_rule():
    """No timeout: a target behind a pending input request stays reachable."""
    bus, workflow_map, master = _services()
    events = _statuses(bus)
    recoveries = _recoveries(bus, master)
    asked = asyncio.Event()
    requests: List[Dict[str, Any]] = []

    def on_input(payload: Dict[str, Any]) -> None:
        requests.append(payload)
        asked.set()

    bus.subscribe(USER_INPUT_NEEDED, on_input)
    fork, path_a, path_b = _fork(workflow_map)
    ask = workflow_map.add_node("user_text_input_node")
    target = workflow_map.add_node("no_op_node")
    workflow_map.connect(fork, path_b, ask, "input")
    workflow_map.connect(ask, "default", target, "input")
    waiter = _waiter_on(workflow_map, target, fork, path_a)

    assert await master.start_workflow()
    await asyncio.wait_for(asked.wait(), RUN_TIMEOUT)
    # Well past any configured node timeout scale for this test; nothing fails.
    await asyncio.sleep(0.3)
    assert recoveries == []
    assert (waiter, "done") not in events

    master.submit_user_input(requests[0]["branch_id"], "answer")
    await _finish(master)

    assert recoveries == []
    assert (waiter, "done") in events
    assert master.state.value == "FINISHED"


async def test_wait_until_completes_normally_when_target_finishes_later():
    bus, workflow_map, master = _services()
    events = _statuses(bus)
    recoveries = _recoveries(bus, master)
    fork, path_a, path_b = _fork(workflow_map)
    slow = workflow_map.add_node("sleep_node")
    workflow_map.update_node_config(slow, {"duration": 0.1})
    workflow_map.connect(fork, path_b, slow, "input")
    waiter = _waiter_on(workflow_map, slow, fork, path_a)

    assert await master.start_workflow()
    await _finish(master)

    assert recoveries == []
    assert (waiter, "done") in events


@pytest.mark.parametrize("policy", ["terminate_branch", "terminate_workflow"])
async def test_unattended_run_with_wait_on_a_failed_target_finishes(policy):
    """Closes the step 1 gap: no unattended hang on a Wait Until."""
    bus, workflow_map, master = _services()
    logged: List[Dict[str, Any]] = []
    bus.subscribe(ERROR_LOGGED, logged.append)
    fork, path_a, path_b = _fork(workflow_map)
    target = workflow_map.add_node("error_node")
    workflow_map.connect(fork, path_b, target, "input")
    _waiter_on(workflow_map, target, fork, path_a)

    assert await master.start_workflow(unattended=policy)
    await _finish(master)

    assert master.state.value in {"FINISHED", "ERROR"}
    assert master._supervisor_tasks == {}


async def test_stale_supervisor_marks_completions_only_in_its_own_run():
    bus, workflow_map, master = _services()
    events: List[Dict[str, Any]] = []
    bus.subscribe(NODE_EXECUTION_UPDATE, events.append)
    start = workflow_map.add_node("start_node")
    waiter = workflow_map.add_node("wait_until_node")
    target = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(waiter, {"target_node_ids": target})
    fork = workflow_map.add_node("branch_node")
    delay = workflow_map.add_node("sleep_node")
    workflow_map.update_node_config(delay, {"duration": 0.5})
    workflow_map.connect(start, "default", fork, "input")
    workflow_map.connect(fork, "path_a", waiter, "input")
    workflow_map.connect(fork, "path_b", delay, "input")
    workflow_map.connect(delay, "default", target, "input")

    assert await master.start_workflow()
    first_run = master.run_context
    root = next(iter(first_run.live_supervisors.values()))
    stale_mark = root._mark_node_completed

    assert await master.start_workflow()
    second_run = master.run_context
    assert second_run is not first_run

    await stale_mark(target)
    assert target in first_run.completed_nodes
    assert target not in second_run.completed_nodes
    master.stop()
    await _finish(master)


@pytest.mark.parametrize("policy", [None, "terminate_branch"])
async def test_target_two_hops_past_a_failure_is_unreachable(policy):
    """The middle node never runs, and nothing live can reach it."""
    bus, workflow_map, master = _services()
    recoveries = _recoveries(bus, master)
    fork, path_a, path_b = _fork(workflow_map)
    failing = workflow_map.add_node("error_node")
    middle = workflow_map.add_node("no_op_node")
    target = workflow_map.add_node("no_op_node")
    workflow_map.connect(fork, path_b, failing, "input")
    workflow_map.connect(failing, "default", middle, "input")
    workflow_map.connect(middle, "default", target, "input")
    waiter = _waiter_on(workflow_map, target, fork, path_a)
    logged: List[Dict[str, Any]] = []
    bus.subscribe(ERROR_LOGGED, logged.append)

    assert await master.start_workflow(unattended=policy)
    await _finish(master)

    waiter_errors = [e for e in logged if e["error"]["node_id"] == waiter]
    assert len(waiter_errors) == 1
    if policy is None:
        assert waiter in [r["node_id"] for r in recoveries]


async def test_target_two_hops_down_an_untaken_conditional_port_is_unreachable():
    bus, workflow_map, master = _services()
    recoveries = _recoveries(bus, master)
    fork, path_a, path_b = _fork(workflow_map)
    condition = workflow_map.add_node("conditional_node")
    workflow_map.update_node_config(
        condition, {"condition_type": "equals", "right_value": "never matches"}
    )
    middle = workflow_map.add_node("no_op_node")
    target = workflow_map.add_node("no_op_node")
    taken = workflow_map.add_node("no_op_node")
    workflow_map.connect(fork, path_b, condition, "input")
    workflow_map.connect(condition, "true", middle, "input")
    workflow_map.connect(middle, "default", target, "input")
    workflow_map.connect(condition, "false", taken, "input")
    waiter = _waiter_on(workflow_map, target, fork, path_a)

    assert await master.start_workflow()
    await _finish(master)

    assert [r["node_id"] for r in recoveries] == [waiter]


async def test_branch_refused_by_the_depth_limit_does_not_count_as_delivered(monkeypatch):
    bus, workflow_map, master = _services()
    recoveries = _recoveries(bus, master)
    # Depth 1: the outer fork's children run; the inner fork's are refused.
    monkeypatch.setitem(master._configuration_manager._settings, "max_branch_depth", 1)
    logged: List[Dict[str, Any]] = []
    bus.subscribe(ERROR_LOGGED, logged.append)
    outer, path_a, path_b = _fork(workflow_map)
    inner = workflow_map.add_node("branch_node")
    target = workflow_map.add_node("no_op_node")
    workflow_map.connect(outer, path_b, inner, "input")
    workflow_map.connect(inner, "path_a", target, "input")
    waiter = _waiter_on(workflow_map, target, outer, path_a)

    assert await master.start_workflow(unattended="terminate_branch")
    await _finish(master)

    assert master._supervisor_tasks == {}
    assert target not in master.completed_nodes
    assert [e["error"]["node_id"] for e in logged] == [inner, waiter]
    assert recoveries == []


async def test_wait_on_a_node_after_a_merge_completes():
    bus, workflow_map, master = _services()
    events = _statuses(bus)
    recoveries = _recoveries(bus, master)
    start = workflow_map.add_node("start_node")
    fork = workflow_map.add_node("branch_node")
    workflow_map.update_node_config(fork, {"branch_count": 3})
    merge = workflow_map.add_node("merge_node")
    target = workflow_map.add_node("no_op_node")
    first = workflow_map.add_node("sleep_node")
    second = workflow_map.add_node("sleep_node")
    workflow_map.update_node_config(first, {"duration": 0.02})
    workflow_map.update_node_config(second, {"duration": 0.04})
    workflow_map.connect(start, "default", fork, "input")
    workflow_map.connect(fork, "path_a", first, "input")
    workflow_map.connect(fork, "path_b", second, "input")
    workflow_map.connect(first, "default", merge, "path_a")
    workflow_map.connect(second, "default", merge, "path_b")
    workflow_map.connect(merge, "default", target, "input")
    waiter = _waiter_on(workflow_map, first, fork, "path_c")

    assert await master.start_workflow(merge_plans={merge: MergePlan(fork, {
        "path_a": MergeSlot("one", ((0,),)), "path_b": MergeSlot("one", ((1,),))})})
    await _finish(master)

    assert recoveries == []
    assert (waiter, "done") in events
    assert (target, "done") in events


async def test_wait_on_a_target_reached_on_a_later_loop_iteration():
    """A real loop: the target is only reached once the loop exits."""
    bus, workflow_map, master = _services()
    events = _statuses(bus)
    recoveries = _recoveries(bus, master)
    fork, path_a, path_b = _fork(workflow_map)
    counter = workflow_map.add_node("counter_node")
    check = workflow_map.add_node("conditional_node")
    pause = workflow_map.add_node("sleep_node")
    target = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(pause, {"duration": 0.01})
    workflow_map.connect(fork, path_b, counter, "input")
    workflow_map.connect(counter, "default", check, "input")
    workflow_map.connect(check, "false", pause, "input")
    workflow_map.connect(pause, "default", counter, "input")
    workflow_map.connect(check, "true", target, "input")
    waiter = _waiter_on(workflow_map, target, fork, path_a)
    # The conditional matches once the counter's Vault variable reaches 3.
    workflow_map.update_node_config(check, {
        "condition_type": "equals", "left_value_source": "variable",
        "variable_name": "counter", "right_value": "3"})

    assert await master.start_workflow()
    await _finish(master)

    assert recoveries == []
    assert (waiter, "done") in events
    assert (target, "done") in events


# ---------------------------------------------------------------------------
# The rule itself, on a real WorkflowMap with stand-in supervisors
# ---------------------------------------------------------------------------


class _At:
    """Stand-in for a live supervisor at a node."""

    def __init__(self, node_id: Optional[str]) -> None:
        self.position = node_id


def _context() -> RunContext:
    bus = EventBus()
    return RunContext(run_id="run_x", memory_bank=MemoryBank(bus), run_session=RunSession("run_x"))


def _loop_map() -> Tuple[WorkflowMap, str, str, str]:
    """a -> b; b(true) -> a (loop); b(false) -> t."""
    workflow_map = WorkflowMap(NodeFactory(), EventBus())
    workflow_map.create_new("Loop")
    a = workflow_map.add_node("no_op_node")
    b = workflow_map.add_node("conditional_node")
    t = workflow_map.add_node("no_op_node")
    workflow_map.connect(a, "default", b, "input")
    workflow_map.connect(b, "true", a, "input")
    workflow_map.connect(b, "false", t, "input")
    return workflow_map, a, b, t


def test_target_inside_a_loop_is_reachable_while_a_live_supervisor_can_reach_it():
    workflow_map, a, b, t = _loop_map()
    run = _context()
    # First iteration: b looped back to a, not to t.
    run.record_outcome(a, "completed", [b])
    run.record_outcome(b, "completed", [a])
    run.live_supervisors["looping"] = _At(a)
    assert run.unreachable_reason(t, workflow_map) is None

    # The loop's supervisor ends without ever routing to t.
    run.live_supervisors.clear()
    assert run.unreachable_reason(t, workflow_map) is not None


def test_a_delivering_source_keeps_the_target_reachable():
    workflow_map, a, b, t = _loop_map()
    run = _context()
    run.record_outcome(b, "completed", [t])
    assert run.unreachable_reason(t, workflow_map) is None


def test_a_source_that_a_live_supervisor_can_still_run_keeps_the_target_reachable():
    """Never a timeout: however long it takes, a reachable source may deliver."""
    workflow_map, a, b, t = _loop_map()
    run = _context()
    run.live_supervisors["slow"] = _At(a)
    assert run.unreachable_reason(t, workflow_map) is None


def test_a_source_that_never_ran_and_cannot_run_settles_the_target():
    """A dead source never routes to the target (D9 will mark it skipped)."""
    workflow_map, a, b, t = _loop_map()
    run = _context()
    assert run.unreachable_reason(t, workflow_map) is not None


def test_a_completed_target_is_never_unreachable():
    workflow_map, a, b, t = _loop_map()
    run = _context()
    run.mark_completed(t)
    run.record_outcome(b, "completed", [a])
    assert run.unreachable_reason(t, workflow_map) is None


def test_a_failed_target_is_reachable_again_while_a_live_supervisor_can_revisit_it():
    workflow_map, a, b, t = _loop_map()
    run = _context()
    run.record_outcome(a, "failed")
    run.live_supervisors["other"] = _At(b)
    assert run.unreachable_reason(a, workflow_map) is None
    run.live_supervisors.clear()
    assert "failed" in run.unreachable_reason(a, workflow_map)


def test_unreachable_error_names_the_target():
    error = TargetUnreachableError("Wait target 'X' (node_1) can no longer complete")
    assert "node_1" in str(error)

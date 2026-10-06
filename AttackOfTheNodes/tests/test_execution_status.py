"""Execution lifecycle and mounted run-screen regressions."""
import asyncio

import pytest
from textual.screen import ModalScreen

from backend.events import RECOVERY_OPTIONS_AVAILABLE
from frontend.app import AttackOfTheNodesApp
from frontend.screens.execution import ExecutionScreen
from frontend.widgets.node_card import NodeCard
from tests.test_debug_nodes import _make_services


def make_app():
    master, wm, memory, bus = _make_services()
    wm.create_new("execution_status")
    app = AttackOfTheNodesApp(bus, wm._factory, wm, memory, master)
    return app, master, wm, memory, bus


def linear(wm):
    ids = [wm.add_node(t) for t in
           ("start_node", "sleep_node", "sleep_node", "end_node")]
    for node in ids[1:3]:
        wm.update_node_config(node, {"duration": 0.06})
    for source, target in zip(ids, ids[1:]):
        wm.connect(source, "default", target, "input")
    return ids


def test_linear_symbols_follow_actual_execution():
    async def check():
        app, master, wm, memory, bus = make_app()
        ids = linear(wm)
        untouched = wm.add_node("no_op_node")
        async with app.run_test() as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            assert await master.start_workflow()
            await until(lambda: app.node_statuses.get(ids[1]) == "running")
            await pilot.pause(0.001)
            live_card = next(c for c in screen.query(NodeCard) if c.node_id == ids[1])
            assert live_card.status == "running"
            assert "▶" in live_card.display_text
            await master.wait_for_completion()
            await pilot.pause()
            cards = {card.node_id: card for card in screen.query(NodeCard)}
            assert [app.node_statuses.get(n, "idle") for n in ids] == ["done"] * 4
            assert [cards[n].status for n in ids] == ["done"] * 4
            assert all("✓" in cards[n].display_text for n in ids)
            assert cards[untouched].status == "idle"
    asyncio.run(asyncio.wait_for(check(), timeout=15))


@pytest.mark.parametrize("action,expected", [
    ("TERMINATE_BRANCH", "errored"), ("TERMINATE_WORKFLOW", "errored"),
    ("SKIP", "skipped"),
])
def test_recovery_outcomes_are_not_success(action, expected):
    async def check():
        app, master, wm, memory, bus = make_app()
        start = wm.add_node("start_node")
        failed = wm.add_node("error_node")
        end = wm.add_node("end_node")
        wm.update_node_config(failed, {"message": "probe", "error_mode": "fail"})
        wm.connect(start, "default", failed, "input")
        wm.connect(failed, "default", end, "input")
        app._on_backend_event = lambda payload=None: None
        app._error_modal_open = True
        bus.subscribe(RECOVERY_OPTIONS_AVAILABLE,
                      lambda p: master.submit_recovery_action(p["branch_id"], action))
        await master.start_workflow()
        await master.wait_for_completion()
        assert app.node_statuses[failed] == expected
        if action == "SKIP":
            assert app.node_statuses[end] == "done"
        else:
            assert app.node_statuses.get(end, "idle") == "idle"
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_modal_resume_refreshes_latest_symbols():
    async def check():
        app, master, wm, memory, bus = make_app()
        ids = linear(wm)
        async with app.run_test() as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            await app.push_screen(ModalScreen())
            await master.start_workflow()
            await master.wait_for_completion()
            app.pop_screen()
            await pilot.pause()
            cards = {card.node_id: card for card in screen.query(NodeCard)}
            assert all(cards[n].status == "done" for n in ids)
    asyncio.run(asyncio.wait_for(check(), timeout=15))


async def until(predicate):
    for _ in range(300):
        if predicate():
            return
        await asyncio.sleep(0.002)
    raise AssertionError("execution did not reach expected state")


def test_parallel_shared_node_keeps_independent_visits():
    async def check():
        from backend.node_base import Node
        app, master, wm, memory, bus = make_app()
        releases = [asyncio.Event(), asyncio.Event()]
        entered = []

        class Shared(Node):
            node_type = "shared_probe"
            input_ports = ["input"]
            output_ports = ["default"]

            async def execute(self, context):
                index = len(entered)
                entered.append(context.branch_id)
                await releases[index].wait()
                context.signal_done({"terminate_branch": True})

        wm._factory._node_registry[Shared.node_type] = Shared
        start = wm.add_node("start_node")
        fork = wm.add_node("branch_node")
        shared = wm.add_node(Shared.node_type)
        wm.update_node_config(fork, {"branch_count": 2})
        wm.connect(start, "default", fork, "input")
        wm.connect(fork, "path_a", shared, "input")
        wm.connect(fork, "path_b", shared, "input")
        app._on_backend_event = lambda payload=None: None
        await master.start_workflow()
        try:
            await until(lambda: len(entered) == 2)
            releases[0].set()
            await until(lambda: app.execution_state.node_statuses(entered[0]).get(shared) == "done")
            assert app.node_statuses[shared] == "running"
            assert app.execution_state.node_statuses(entered[1])[shared] == "running"
            assert app.supervisors[entered[0]]["parent_branch_id"] is not None
        finally:
            for release in releases:
                release.set()
            await master.wait_for_completion()
        assert app.node_statuses[shared] == "done"
        assert len(app.supervisors) == 3  # root and ended children retained
        assert all(b["state"] == "TERMINATED" for b in app.supervisors.values())
        assert all(b["visits"] for b in app.supervisors.values())
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_retry_and_repeat_visits_keep_separate_history():
    async def check():
        from backend.node_base import Node
        app, master, wm, memory, bus = make_app()
        calls = []

        class FlakyLoop(Node):
            node_type = "flaky_loop_probe"
            input_ports = ["input"]
            output_ports = ["default"]

            async def execute(self, context):
                calls.append(context.node_id)
                if len(calls) == 1:
                    context.signal_error(RuntimeError("first attempt"))
                else:
                    context.signal_done(
                        {"next_node_id": context.node_id} if len(calls) == 2
                        else {"terminate_branch": True})

        wm._factory._node_registry[FlakyLoop.node_type] = FlakyLoop
        start = wm.add_node("start_node")
        node = wm.add_node(FlakyLoop.node_type)
        wm.connect(start, "default", node, "input")
        app._on_backend_event = lambda payload=None: None
        app._error_modal_open = True
        bus.subscribe(RECOVERY_OPTIONS_AVAILABLE,
                      lambda p: master.submit_recovery_action(p["branch_id"], "RETRY"))
        await master.start_workflow()
        await master.wait_for_completion()
        branch = next(iter(app.supervisors.values()))
        visits = [v for v in branch["visits"].values() if v["node_id"] == node]
        assert len(visits) == 2
        assert visits[0]["attempts"][1]["status"] == "errored"
        assert visits[0]["attempts"][2]["status"] == "done"
        assert visits[1]["attempts"][1]["status"] == "done"
        assert all(v["seconds"] > 0 for v in visits)
        assert app.node_statuses[node] == "done"
    asyncio.run(asyncio.wait_for(check(), timeout=15))


@pytest.mark.parametrize("stop", [False, True])
def test_user_input_wait_resume_and_stop(stop):
    async def check():
        from backend.events import USER_INPUT_NEEDED
        app, master, wm, memory, bus = make_app()
        start = wm.add_node("start_node")
        node = wm.add_node("user_text_input_node")
        end = wm.add_node("end_node")
        wm.connect(start, "default", node, "input")
        wm.connect(node, "default", end, "input")
        app._on_backend_event = lambda payload=None: None
        app._user_input_modal_open = True
        requests = []
        bus.subscribe(USER_INPUT_NEEDED, lambda p: requests.append(p))
        await master.start_workflow()
        await until(lambda: bool(requests))
        assert app.node_statuses[node] == "waiting"
        assert requests[0]["run_id"] == master.current_run_id
        if stop:
            master.stop()
        else:
            master.submit_user_input(requests[0]["branch_id"], "answer")
        await master.wait_for_completion()
        assert app.node_statuses[node] == ("stopped" if stop else "done")
        assert app.node_statuses.get(end, "idle") == ("idle" if stop else "done")
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_new_run_and_cleared_run_ignore_old_events():
    async def check():
        from backend.events import NODE_EXECUTION_UPDATE, NODE_TIMING_UPDATE, SUPERVISOR_TERMINATING
        app, master, wm, memory, bus = make_app()
        ids = linear(wm)
        app._on_backend_event = lambda payload=None: None
        await master.start_workflow()
        await master.wait_for_completion()
        old_run = master.current_run_id
        old_branch = next(iter(app.supervisors))
        await master.start_workflow()
        assert app.node_statuses == {}
        stale = {"run_id": old_run, "branch_id": old_branch, "node_id": ids[1],
                 "visit_index": 2, "attempt_index": 1, "status": "errored", "seconds": 100}
        bus.publish(NODE_EXECUTION_UPDATE, stale)
        bus.publish(NODE_TIMING_UPDATE, stale)
        bus.publish(SUPERVISOR_TERMINATING, dict(stale, final_state="ERROR"))
        assert app.node_statuses == {}
        assert app.node_timings == {}
        assert old_branch not in app.supervisors
        await master.wait_for_completion()
        assert app.node_statuses[ids[1]] == "done"
        app._reset_run_display_state()
        from backend.events import WORKFLOW_STATE_UPDATE
        bus.publish(WORKFLOW_STATE_UPDATE, {"run_id": master.current_run_id, "state": "RUNNING"})
        bus.publish(NODE_EXECUTION_UPDATE, dict(stale, run_id=master.current_run_id))
        assert app.node_statuses == {}
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_breakpoint_and_safe_point_pause_do_not_execute_queued_node():
    async def check():
        app, master, wm, memory, bus = make_app()
        ids = linear(wm)
        wm.set_breakpoint(ids[1], True)
        app._on_backend_event = lambda payload=None: None
        await master.start_workflow()
        await until(lambda: master.state.value == "PAUSED")
        assert app.node_statuses[ids[0]] == "done"
        assert app.node_statuses.get(ids[1], "idle") == "idle"
        master.resume()
        await until(lambda: app.node_statuses.get(ids[1]) == "running")
        master.pause()
        await until(lambda: app.node_statuses.get(ids[1]) == "done")
        assert app.node_statuses.get(ids[2], "idle") == "idle"
        master.stop()
        await master.wait_for_completion()
        assert app.node_statuses[ids[1]] == "done"  # safe-point stop after success
        assert app.node_statuses.get(ids[2], "idle") == "idle"
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_unhandled_setup_error_reports_failure():
    async def check():
        app, master, wm, memory, bus = make_app()
        node = wm.add_node("start_node")
        app._on_backend_event = lambda payload=None: None
        def broken(_node):
            raise RuntimeError("factory failure")
        wm.get_node_instance = broken
        await master.start_workflow()
        await master.wait_for_completion()
        assert app.node_statuses[node] == "errored"
        assert master.state.value == "ERROR"
    asyncio.run(asyncio.wait_for(check(), timeout=15))


@pytest.mark.parametrize("width", [60, 100, 140])
def test_render_updates_preserve_cards_highlight_and_scroll(width):
    async def check():
        from frontend.widgets.node_list import NodeList
        from backend.events import NODE_EXECUTION_UPDATE
        app, master, wm, memory, bus = make_app()
        ids = linear(wm)
        for _ in range(25):
            wm.add_node("sleep_node")
        async with app.run_test(size=(width, 24)) as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            await master.start_workflow()
            await master.wait_for_completion()
            await pilot.pause()
            node_list = screen.query_one(NodeList)
            node_list.index = 20
            await pilot.pause()
            cards = list(screen.query(NodeCard))
            scroll = node_list.scroll_y
            branch_id = next(iter(app.supervisors))
            bus.publish(NODE_EXECUTION_UPDATE, {
                "run_id": master.current_run_id, "branch_id": branch_id,
                "node_id": ids[1], "visit_index": 20, "attempt_index": 1,
                "status": "skipped"})
            await pilot.pause()
            assert list(screen.query(NodeCard)) == cards
            assert node_list.index == 20
            assert node_list.scroll_y == scroll
            card = next(c for c in cards if c.node_id == ids[1])
            assert "[skipped]" in card.display_text
            assert "✓" not in card.display_text
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_lifecycle_events_are_scoped_serializable_and_per_node():
    async def check():
        import json
        from backend.events import NODE_EXECUTION_UPDATE, NODE_TIMING_UPDATE, SUPERVISOR_STATE_UPDATE
        app, master, wm, memory, bus = make_app()
        ids = linear(wm)
        app._on_backend_event = lambda payload=None: None
        trace = []
        states = []
        bus.subscribe(NODE_EXECUTION_UPDATE, lambda p: trace.append(p))
        bus.subscribe(SUPERVISOR_STATE_UPDATE, lambda p: states.append(p))
        await master.start_workflow()
        await master.wait_for_completion()
        assert [p["node_id"] for p in trace if p["status"] == "running"] == ids
        assert [p["node_id"] for p in trace if p["status"] == "done"] == ids
        assert [p["visit_index"] for p in trace if p["status"] == "done"] == [1, 2, 3, 4]
        assert all(p["run_id"] == master.current_run_id for p in trace + states)
        json.dumps(trace + states)
        assert any(p["node_phase"] == "queued" for p in states)
        assert any(p["node_phase"] == "executing" for p in states)
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_cancellation_preserves_failed_attempt_and_stops_active_attempt():
    async def check():
        from backend.events import USER_INPUT_NEEDED
        for node_type, expected in [("user_text_input_node", "stopped"),
                                    ("error_node", "errored")]:
            app, master, wm, memory, bus = make_app()
            start = wm.add_node("start_node")
            node = wm.add_node(node_type)
            wm.connect(start, "default", node, "input")
            app._on_backend_event = lambda payload=None: None
            app._user_input_modal_open = True
            app._error_modal_open = True
            await master.start_workflow()
            await until(lambda: app.node_statuses.get(node) in {"waiting", "errored"})
            tasks = list(master._supervisor_tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            assert app.node_statuses[node] == expected
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_skip_does_not_mark_next_node_completed_before_execution():
    async def check():
        from backend.events import NODE_EXECUTION_UPDATE
        app, master, wm, memory, bus = make_app()
        start = wm.add_node("start_node")
        failed = wm.add_node("error_node")
        end = wm.add_node("end_node")
        wm.connect(start, "default", failed, "input")
        wm.connect(failed, "default", end, "input")
        app._on_backend_event = lambda payload=None: None
        app._error_modal_open = True
        premature = []
        bus.subscribe(RECOVERY_OPTIONS_AVAILABLE,
                      lambda p: master.submit_recovery_action(p["branch_id"], "SKIP"))
        bus.subscribe(NODE_EXECUTION_UPDATE,
                      lambda p: premature.append(end in master.completed_nodes)
                      if p["node_id"] == end and p["status"] == "running" else None)
        await master.start_workflow()
        await master.wait_for_completion()
        assert premature == [False]
        assert end in master.completed_nodes
        assert failed not in master.completed_nodes
    asyncio.run(asyncio.wait_for(check(), timeout=15))


def test_workflow_replacement_clears_retained_branches():
    async def check():
        app, master, wm, memory, bus = make_app()
        linear(wm)
        async with app.run_test() as pilot:
            await master.start_workflow()
            await master.wait_for_completion()
            assert app.supervisors
            app._create_new_workflow()
            await pilot.pause()
            assert app.node_statuses == {}
            assert app.supervisors == {}
            assert app.execution_state.run_id is None
    asyncio.run(asyncio.wait_for(check(), timeout=15))


@pytest.mark.parametrize("barrier", ["wait_until_node", "merge_node"])
def test_barriers_keep_runtime_wait_semantics_and_finish_symbols(barrier):
    async def check():
        app, master, wm, memory, bus = make_app()
        start = wm.add_node("start_node")
        fork = wm.add_node("branch_node")
        slow = wm.add_node("sleep_node")
        wait = wm.add_node(barrier)
        end = wm.add_node("end_node")
        wm.update_node_config(slow, {"duration": 0.08})
        wm.connect(start, "default", fork, "input")
        wm.connect(fork, "path_a", slow, "input")
        if barrier == "wait_until_node":
            wm.update_node_config(wait, {"target_node_ids": slow, "timeout_seconds": 1})
            wm.connect(fork, "path_b", wait, "input")
        else:
            wm.update_node_config(wait, {"selected_input_port": "path_b"})
            wm.connect(slow, "default", wait, "path_a")
            wm.connect(fork, "path_b", wait, "path_b")
        wm.connect(wait, "default", end, "input")
        app._on_backend_event = lambda payload=None: None
        await master.start_workflow()
        await until(lambda: app.node_statuses.get(wait) == "running")
        assert slow not in master.completed_nodes
        assert app.node_statuses.get(end, "idle") == "idle"
        await master.wait_for_completion()
        assert master.state.value == "FINISHED"
        assert all(app.node_statuses.get(n) == "done" for n in [start, fork, slow, wait, end])
    asyncio.run(asyncio.wait_for(check(), timeout=15))

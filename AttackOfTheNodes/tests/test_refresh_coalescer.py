"""Refresh coalescer: run telemetry refreshes the screen on a timer.

Distributed build plan, "Any time — Refresh coalescer (frontend only)".
"""

from __future__ import annotations

import asyncio
import math
import time

from backend.events import (
    ERROR_LOGGED,
    MEMORY_UPDATE,
    NODE_EXECUTION_UPDATE,
    NODE_TIMING_UPDATE,
    SUPERVISOR_STATE_UPDATE,
)
from frontend.app import REFRESH_COALESCE_SECONDS
from frontend.screens.execution import ExecutionScreen
from frontend.widgets.node_card import NodeCard
from tests.test_execution_status import make_app


def _count_refreshes(screen) -> list:
    calls: list = []
    original = screen.refresh_from_backend

    def counted(*args, **kwargs):
        calls.append(time.perf_counter())
        return original(*args, **kwargs)

    screen.refresh_from_backend = counted
    return calls


def _chain(wm, sleeps: int, duration: float):
    ids = [wm.add_node("start_node")]
    for _ in range(sleeps):
        node = wm.add_node("sleep_node")
        wm.update_node_config(node, {"duration": duration})
        ids.append(node)
    ids.append(wm.add_node("end_node"))
    for source, target in zip(ids, ids[1:]):
        wm.connect(source, "default", target, "input")
    return ids


def test_coalesce_interval_is_75_ms():
    assert REFRESH_COALESCE_SECONDS == 0.075


def test_refresh_calls_are_bounded_by_the_timer_and_final_frame_is_correct():
    async def check():
        app, master, wm, memory, bus = make_app()
        ids = _chain(wm, sleeps=30, duration=0.005)
        telemetry = []
        for name in (NODE_EXECUTION_UPDATE, SUPERVISOR_STATE_UPDATE, NODE_TIMING_UPDATE):
            bus.subscribe(name, telemetry.append)
        async with app.run_test() as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            calls = _count_refreshes(screen)
            started = time.perf_counter()
            assert await master.start_workflow()
            await master.wait_for_completion()
            elapsed = time.perf_counter() - started
            # No manual flush: the final frame must arrive on its own.
            await pilot.pause(REFRESH_COALESCE_SECONDS * 3)

            # One timer refresh per interval, plus the immediate flushes for
            # RUNNING and FINISHED, plus the trailing timer.
            bound = math.ceil(elapsed / REFRESH_COALESCE_SECONDS) + 4
            assert len(calls) <= bound, (len(calls), bound, elapsed)
            assert len(telemetry) >= 5 * len(ids) - 5
            assert len(calls) * 5 < len(telemetry)

            cards = {card.node_id: card for card in screen.query(NodeCard)}
            assert [cards[node].status for node in ids] == ["done"] * len(ids)
            assert app.workflow_state == "FINISHED"
            assert app._refresh_timer is None
            assert app._refresh_dirty is False
    asyncio.run(asyncio.wait_for(check(), timeout=20))


def test_telemetry_events_do_not_refresh_synchronously():
    async def check():
        app, master, wm, memory, bus = make_app()
        _chain(wm, sleeps=1, duration=0.0)
        async with app.run_test() as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            calls = _count_refreshes(screen)
            run_id = master.current_run_id
            for name in (NODE_EXECUTION_UPDATE, SUPERVISOR_STATE_UPDATE,
                         NODE_TIMING_UPDATE, MEMORY_UPDATE):
                bus.publish(name, {"run_id": run_id, "branch_id": "b", "node_id": "n",
                                   "status": "running", "state": "RUNNING", "seconds": 0.0,
                                   "current_node_id": "n", "visit_index": 1,
                                   "attempt_index": 1})
            assert calls == []
            assert app._refresh_dirty is True
            await pilot.pause(REFRESH_COALESCE_SECONDS * 2)
            assert len(calls) == 1
    asyncio.run(asyncio.wait_for(check(), timeout=10))


def test_flush_refresh_refreshes_now_and_cancels_the_pending_timer():
    async def check():
        app, master, wm, memory, bus = make_app()
        _chain(wm, sleeps=1, duration=0.0)
        async with app.run_test() as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            calls = _count_refreshes(screen)
            app.schedule_refresh()
            assert app._refresh_timer is not None
            app.flush_refresh()
            assert len(calls) == 1
            assert app._refresh_timer is None
            await pilot.pause(REFRESH_COALESCE_SECONDS * 2)
            assert len(calls) == 1
    asyncio.run(asyncio.wait_for(check(), timeout=10))


def test_error_events_act_at_once():
    async def check():
        app, master, wm, memory, bus = make_app()
        _chain(wm, sleeps=1, duration=0.0)
        async with app.run_test() as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            calls = _count_refreshes(screen)
            app.schedule_refresh()
            bus.publish(ERROR_LOGGED, {"run_id": master.current_run_id, "message": "x"})
            assert len(calls) == 1
            assert app._refresh_timer is None
    asyncio.run(asyncio.wait_for(check(), timeout=10))


def test_input_request_opens_its_modal_and_refreshes_at_once():
    async def check():
        from frontend.screens.user_input import UserInputScreen

        app, master, wm, memory, bus = make_app()
        start = wm.add_node("start_node")
        ask = wm.add_node("user_text_input_node")
        wm.connect(start, "default", ask, "input")
        async with app.run_test() as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            calls = _count_refreshes(screen)
            assert await master.start_workflow()
            for _ in range(200):
                if isinstance(app.screen, UserInputScreen):
                    break
                await asyncio.sleep(0.002)
            assert isinstance(app.screen, UserInputScreen)
            # The flush happened in the same publish, not on the timer.
            assert calls and app._refresh_dirty is False
            master.stop()
            await master.wait_for_completion()
    asyncio.run(asyncio.wait_for(check(), timeout=10))

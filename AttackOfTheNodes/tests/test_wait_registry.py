"""Unit tests for the per-run WaitRegistry (distributed build plan step 1b).

Proposal v2's own test list was not available in the repo; these cover the
behavior the plan specifies: tuple keys, sticky completion, wait-for-all,
unreachable keys failing a wait at once, a ``stopped`` result instead of a
raised ``CancelledError``, and no timeout-based decisions.
"""

from __future__ import annotations

import asyncio

import pytest

from backend.wait_registry import WaitOutcome, WaitRegistry, WaitStatus, node_key


A, B, C = node_key("a"), node_key("b"), node_key("c")


async def _started(coro):
    task = asyncio.create_task(coro)
    await asyncio.sleep(0)
    return task


async def test_wait_for_all_completes_when_every_key_completes():
    registry = WaitRegistry()
    task = await _started(registry.wait_for_all([A, B]))
    registry.mark_completed(A)
    await asyncio.sleep(0)
    assert not task.done()
    registry.mark_completed(B)
    assert (await task) == WaitOutcome(WaitStatus.COMPLETED)
    assert registry.waiter_count == 0


async def test_completion_is_sticky_for_later_waiters():
    registry = WaitRegistry()
    registry.mark_completed(A)
    outcome = await registry.wait_for_all([A])
    assert outcome.status == WaitStatus.COMPLETED
    assert registry.is_completed(A)


async def test_empty_wait_completes_immediately():
    assert (await WaitRegistry().wait_for_all([])).status == WaitStatus.COMPLETED


async def test_any_unreachable_key_fails_a_wait_for_all_at_once():
    registry = WaitRegistry()
    task = await _started(registry.wait_for_all([A, B, C]))
    registry.mark_completed(A)
    registry.mark_unreachable(C, "gone")
    outcome = await task
    assert outcome == WaitOutcome(WaitStatus.UNREACHABLE, key=C, reason="gone")


async def test_waiting_on_an_already_unreachable_key_fails_without_suspending():
    registry = WaitRegistry()
    registry.mark_unreachable(B, "no inputs")
    outcome = await registry.wait_for_all([A, B])
    assert outcome.status == WaitStatus.UNREACHABLE and outcome.key == B


async def test_completed_key_is_never_marked_unreachable():
    registry = WaitRegistry()
    registry.mark_completed(A)
    registry.mark_unreachable(A)
    assert not registry.is_unreachable(A)
    assert (await registry.wait_for_all([A])).status == WaitStatus.COMPLETED


async def test_completion_overrides_an_earlier_unreachable_verdict():
    registry = WaitRegistry()
    registry.mark_unreachable(A)
    registry.mark_completed(A)
    assert (await registry.wait_for_all([A])).status == WaitStatus.COMPLETED


async def test_stop_resolves_waiters_with_stopped_not_cancelled():
    registry = WaitRegistry()
    task = await _started(registry.wait_for_all([A]))
    registry.stop()
    outcome = await task
    assert outcome.status == WaitStatus.STOPPED
    assert not task.cancelled()


async def test_waits_after_stop_return_stopped_at_once():
    registry = WaitRegistry()
    registry.stop()
    assert (await registry.wait_for_all([A])).status == WaitStatus.STOPPED


async def test_one_completion_releases_every_waiter_on_that_key():
    registry = WaitRegistry()
    tasks = [await _started(registry.wait_for_all([A])) for _ in range(3)]
    registry.mark_completed(A)
    outcomes = await asyncio.gather(*tasks)
    assert {outcome.status for outcome in outcomes} == {WaitStatus.COMPLETED}


async def test_unreachable_only_fails_waiters_that_need_the_key():
    registry = WaitRegistry()
    needs_b = await _started(registry.wait_for_all([A, B]))
    needs_a = await _started(registry.wait_for_all([A]))
    registry.mark_unreachable(B)
    assert (await needs_b).status == WaitStatus.UNREACHABLE
    assert not needs_a.done()
    registry.mark_completed(A)
    assert (await needs_a).status == WaitStatus.COMPLETED


async def test_positive_timeout_raises_and_removes_the_waiter():
    registry = WaitRegistry()
    with pytest.raises(asyncio.TimeoutError):
        await registry.wait_for_all([A], timeout=0.01)
    assert registry.waiter_count == 0
    assert registry.pending_keys() == set()


async def test_zero_or_none_timeout_waits_indefinitely():
    registry = WaitRegistry()
    for timeout in (None, 0.0, -1.0):
        task = await _started(registry.wait_for_all([A], timeout=timeout))
        await asyncio.sleep(0.02)
        assert not task.done()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert registry.waiter_count == 0


async def test_cancelled_waiter_no_longer_counts_as_pending():
    registry = WaitRegistry()
    task = await _started(registry.wait_for_all([A, B]))
    assert registry.pending_keys() == {A, B}
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert registry.pending_keys() == set()


async def test_pending_keys_shrink_as_keys_complete():
    registry = WaitRegistry()
    task = await _started(registry.wait_for_all([A, B]))
    registry.mark_completed(A)
    assert registry.pending_keys() == {B}
    registry.mark_completed(B)
    await task


async def test_on_registered_sees_the_new_keys_before_suspending():
    registry = WaitRegistry()
    seen = []

    def check() -> None:
        seen.append(registry.pending_keys())
        registry.mark_unreachable(B, "decided at registration")

    outcome = await registry.wait_for_all([A, B], on_registered=check)
    assert seen == [{A, B}]
    assert outcome.key == B


async def test_keys_are_tuples_and_can_carry_a_visit_number():
    registry = WaitRegistry()
    visit_two = ("node", "a", 2)
    task = await _started(registry.wait_for_all([visit_two]))
    registry.mark_completed(("node", "a", 1))
    await asyncio.sleep(0)
    assert not task.done()
    registry.mark_completed(visit_two)
    assert (await task).status == WaitStatus.COMPLETED

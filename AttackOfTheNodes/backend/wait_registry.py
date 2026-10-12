"""
Per-run wait registry for AttackOfTheNodes.

Waiters park on one Future until every key they wait for is completed. Keys
are tuples such as ``("node", node_id)`` so a visit or iteration number can be
added later without an API change. Completion is sticky for the run.

A key can also be marked unreachable (it can no longer complete in this run);
that fails every wait-for-all containing it at once. Stopping the registry
resolves every waiter with a ``stopped`` result instead of raising
``CancelledError``, which would confuse ``asyncio.timeout``/``TaskGroup``
bookkeeping in the waiting task.

The registry never decides reachability itself and never uses timeouts to do
so; ``MasterState`` evaluates the structural rule (D5) and calls
``mark_unreachable``. A caller-supplied timeout only bounds one wait.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Hashable, Iterable, List, Optional, Set, Tuple


WaitKey = Tuple[Hashable, ...]


def node_key(node_id: str) -> WaitKey:
    """Wait key for "this node has completed at least once in the run"."""
    return ("node", node_id)


class WaitStatus(str, Enum):
    COMPLETED = "completed"
    UNREACHABLE = "unreachable"
    STOPPED = "stopped"


@dataclass(frozen=True)
class WaitOutcome:
    """How a wait ended. ``key`` names the unreachable key, when there is one."""

    status: WaitStatus
    key: Optional[WaitKey] = None
    reason: str = ""


class TargetUnreachableError(RuntimeError):
    """A waited-on target can no longer complete in this run."""

    def __init__(self, message: str, key: Optional[WaitKey] = None) -> None:
        super().__init__(message)
        self.key = key


class WaitStoppedError(RuntimeError):
    """The run was stopped while the node was waiting."""


@dataclass(eq=False)
class _Waiter:
    remaining: Set[WaitKey]
    future: "asyncio.Future[WaitOutcome]" = field(repr=False)


class WaitRegistry:
    """Futures-based completion registry owned by one ``RunContext``."""

    def __init__(self) -> None:
        self._completed: Set[WaitKey] = set()
        self._unreachable: dict[WaitKey, str] = {}
        self._waiters: List[_Waiter] = []
        self._stopped = False

    # -- state ---------------------------------------------------------------

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def completed_keys(self) -> Set[WaitKey]:
        return set(self._completed)

    def is_completed(self, key: WaitKey) -> bool:
        return key in self._completed

    def is_unreachable(self, key: WaitKey) -> bool:
        return key in self._unreachable

    def pending_keys(self) -> Set[WaitKey]:
        """Keys that at least one live waiter still needs."""
        self._prune()
        pending: Set[WaitKey] = set()
        for waiter in self._waiters:
            pending |= waiter.remaining
        return pending

    @property
    def waiter_count(self) -> int:
        self._prune()
        return len(self._waiters)

    # -- updates -------------------------------------------------------------

    def mark_completed(self, key: WaitKey) -> None:
        """Record a completion (sticky) and release waiters it satisfies."""
        self._completed.add(key)
        # A completion always wins over an earlier unreachable verdict.
        self._unreachable.pop(key, None)
        for waiter in list(self._waiters):
            waiter.remaining.discard(key)
            if not waiter.remaining:
                self._resolve(waiter, WaitOutcome(WaitStatus.COMPLETED))

    def mark_unreachable(self, key: WaitKey, reason: str = "") -> None:
        """Fail every wait-for-all that still needs ``key``."""
        if key in self._completed:
            return
        self._unreachable[key] = reason
        for waiter in list(self._waiters):
            if key in waiter.remaining:
                self._resolve(
                    waiter, WaitOutcome(WaitStatus.UNREACHABLE, key=key, reason=reason)
                )

    def stop(self) -> None:
        """Resolve every waiter with ``stopped``; later waits stop at once."""
        self._stopped = True
        for waiter in list(self._waiters):
            self._resolve(waiter, WaitOutcome(WaitStatus.STOPPED))

    # -- waiting -------------------------------------------------------------

    async def wait_for_all(
        self,
        keys: Iterable[WaitKey],
        timeout: Optional[float] = None,
        on_registered: Optional[Callable[[], None]] = None,
    ) -> WaitOutcome:
        """Wait until every key completes, one becomes unreachable, or stop.

        ``on_registered`` runs synchronously after the waiter is registered and
        before the first suspension, so a caller can evaluate reachability for
        the new keys without a race. A positive ``timeout`` raises
        ``asyncio.TimeoutError``; ``None`` or ``<= 0`` waits indefinitely.
        """
        wanted = set(keys)
        if self._stopped:
            return WaitOutcome(WaitStatus.STOPPED)
        for key in wanted:
            if key in self._unreachable and key not in self._completed:
                return WaitOutcome(
                    WaitStatus.UNREACHABLE, key=key, reason=self._unreachable[key]
                )
        remaining = wanted - self._completed
        if not remaining:
            return WaitOutcome(WaitStatus.COMPLETED)

        future: asyncio.Future[WaitOutcome] = asyncio.get_running_loop().create_future()
        waiter = _Waiter(remaining=remaining, future=future)
        self._waiters.append(waiter)
        try:
            if on_registered is not None:
                on_registered()
            if timeout is None or timeout <= 0:
                return await future
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            if waiter in self._waiters:
                self._waiters.remove(waiter)

    # -- internals -----------------------------------------------------------

    def _resolve(self, waiter: _Waiter, outcome: WaitOutcome) -> None:
        if waiter in self._waiters:
            self._waiters.remove(waiter)
        if not waiter.future.done():
            waiter.future.set_result(outcome)

    def _prune(self) -> None:
        self._waiters = [w for w in self._waiters if not w.future.done()]

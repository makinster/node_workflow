"""Benchmark: WaitRegistry completion cost and D5 evaluation cost (backend only).

Run from ``AttackOfTheNodes/``::

    ../.venv/bin/python benchmarks/bench_wait_registry.py [waiters] [keys]

Measures ``mark_completed`` with many parked waiters, and one structural
unreachable evaluation (D5) over a long chain with live supervisors. Not
collected by pytest (D6).
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.event_bus import EventBus  # noqa: E402
from backend.memory_bank import MemoryBank  # noqa: E402
from backend.node_factory import NodeFactory  # noqa: E402
from backend.run_context import RunContext  # noqa: E402
from backend.run_session import RunSession  # noqa: E402
from backend.wait_registry import WaitRegistry, node_key  # noqa: E402
from backend.workflow_map import WorkflowMap  # noqa: E402


async def bench_completions(waiters: int, keys: int) -> None:
    registry = WaitRegistry()
    all_keys = [node_key(f"n{i}") for i in range(keys)]
    tasks = [
        asyncio.create_task(registry.wait_for_all(all_keys[i % keys:] or all_keys))
        for i in range(waiters)
    ]
    await asyncio.sleep(0)
    started = time.perf_counter()
    for key in all_keys:
        registry.mark_completed(key)
    elapsed = time.perf_counter() - started
    await asyncio.gather(*tasks)
    print(f"mark_completed: {keys} keys, {waiters} waiters -> "
          f"{elapsed * 1000:.2f} ms total, {elapsed / keys * 1e6:.1f} us per key")


class _At:
    def __init__(self, node_id: str) -> None:
        self.position = node_id


def bench_unreachable(chain: int, live: int) -> None:
    workflow_map = WorkflowMap(NodeFactory(), EventBus())
    workflow_map.create_new("bench_d5")
    ids = [workflow_map.add_node("no_op_node") for _ in range(chain)]
    for source, target in zip(ids, ids[1:]):
        workflow_map.connect(source, "default", target, "input")
    run = RunContext(run_id="bench", memory_bank=MemoryBank(EventBus()),
                     run_session=RunSession("bench"))
    for index in range(live):
        run.live_supervisors[str(index)] = _At(ids[index])
    started = time.perf_counter()
    reach = run.live_reach(workflow_map)
    for node_id in ids:
        run.unreachable_reason(node_id, workflow_map, reach)
    elapsed = time.perf_counter() - started
    print(f"D5 evaluation: chain {chain}, {live} live supervisors -> "
          f"{elapsed * 1000:.2f} ms for {chain} keys")


if __name__ == "__main__":
    waiters = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    keys = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    asyncio.run(bench_completions(waiters, keys))
    bench_unreachable(chain=keys, live=4)

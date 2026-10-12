"""Benchmark: event volume and wall time of a linear run (backend only).

Run from ``AttackOfTheNodes/``::

    ../.venv/bin/python benchmarks/bench_linear_run.py [nodes] [runs]

Reports events published per node by event type (the plan's "about 5 events
per node" fact) and the mean run time. Not collected by pytest (D6).
"""

from __future__ import annotations

import asyncio
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.configuration_manager import ConfigurationManager  # noqa: E402
from backend.event_bus import EventBus  # noqa: E402
from backend.master_state import MasterState  # noqa: E402
from backend.memory_bank import MemoryBank  # noqa: E402
from backend.node_factory import NodeFactory  # noqa: E402
from backend.output_manager import OutputManager  # noqa: E402
from backend.workflow_map import WorkflowMap  # noqa: E402


class CountingBus(EventBus):
    def __init__(self) -> None:
        super().__init__()
        self.counts: Counter = Counter()

    def publish(self, event_name, payload):  # type: ignore[override]
        self.counts[event_name] += 1
        return super().publish(event_name, payload)


async def one_run(nodes: int) -> tuple[float, Counter]:
    bus = CountingBus()
    workflow_map = WorkflowMap(NodeFactory(), bus)
    master = MasterState(
        workflow_map,
        MemoryBank(bus),
        bus,
        output_manager=OutputManager(),
        configuration_manager=ConfigurationManager(),
    )
    workflow_map.create_new("bench_linear")
    previous = workflow_map.add_node("start_node")
    for _ in range(nodes - 1):
        current = workflow_map.add_node("no_op_node")
        workflow_map.connect(previous, "default", current, "input")
        previous = current
    bus.counts.clear()
    started = time.perf_counter()
    await master.start_workflow(unattended="terminate_workflow")
    await master.wait_for_completion()
    return time.perf_counter() - started, bus.counts


async def main(nodes: int, runs: int) -> None:
    times = []
    counts: Counter = Counter()
    for _ in range(runs):
        elapsed, run_counts = await one_run(nodes)
        times.append(elapsed)
        counts = run_counts
    print(f"linear run: {nodes} nodes x {runs} runs")
    print(f"  mean {statistics.mean(times) * 1000:.2f} ms, "
          f"per node {statistics.mean(times) / nodes * 1e6:.1f} us")
    total = sum(counts.values())
    print(f"  events per node: {total / nodes:.2f}")
    for name, count in counts.most_common():
        print(f"    {name:<28} {count / nodes:.2f}")


if __name__ == "__main__":
    asyncio.run(main(
        int(sys.argv[1]) if len(sys.argv) > 1 else 200,
        int(sys.argv[2]) if len(sys.argv) > 2 else 5,
    ))

"""Benchmark: the cost of subworkflow calls (Step 4b, C16 and C18).

Run from ``AttackOfTheNodes/``::

    ../.venv/bin/python benchmarks/bench_subworkflow_calls.py

Everything runs in a temporary data folder. Reports, for 10/50/100/200
children running at once (each waiting on a sleep, or busy running a chain
of nodes), the wall time, the peak memory, and whether every child stack was
released afterwards; then a chain of nested calls, and many short calls one
after another with a large saved run history (C18: the history is read once,
not per call). The live-run default in Settings comes from these numbers.
Not collected by pytest (D6).
"""

from __future__ import annotations

import asyncio
import gc
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import configuration_manager, persistence, run_history  # noqa: E402


def _isolate(root: Path) -> None:
    for name in ("WORKFLOWS_DIR", "RUN_HISTORY_DIR", "RUN_ERRORS_DIR", "RUN_OUTPUTS_DIR",
                 "RUN_FILES_DIR", "SETTINGS_DIR"):
        setattr(persistence, name, root / name.lower())
    configuration_manager.SETTINGS_DIR = root / "settings"
    run_history.RUN_HISTORY_DIR = persistence.RUN_HISTORY_DIR


_isolate(Path(tempfile.mkdtemp(prefix="aotn_bench_")))

from backend.event_bus import EventBus  # noqa: E402
from backend.master_state import MasterState  # noqa: E402
from backend.node_factory import NodeFactory  # noqa: E402
from backend.run_policies import unattended_policies  # noqa: E402
from backend.run_service import RunService  # noqa: E402
from backend.save_manager import SaveManager  # noqa: E402
from backend.subworkflow_calls import call_subworkflow  # noqa: E402
from backend.workflow_map import WorkflowMap  # noqa: E402

FACTORY = NodeFactory()


def _save(name, build, callable_=True):
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new(name)
    workflow_map.set_callable(callable_)
    build(workflow_map)
    SaveManager(workflow_map).save_current_workflow()
    return workflow_map.workflow_id


def _chain(workflow_map, node_type, count, **config):
    previous = workflow_map.add_node("start_node")
    for _ in range(count):
        node = workflow_map.add_node(node_type)
        if config:
            workflow_map.update_node_config(node, {**workflow_map.get_node_data(node)["config"], **config})
        workflow_map.connect(previous, "default", node, "input")
        previous = node
    end = workflow_map.add_node("end_node")
    workflow_map.update_node_config(end, {**workflow_map.get_node_data(end)["config"], "return_end": True})
    workflow_map.connect(previous, "default", end, "input")


WAITING = _save("Waiting child", lambda m: _chain(m, "sleep_node", 1, duration=0.5))
BUSY = _save("Busy child", lambda m: _chain(m, "no_op_node", 60))
HOLDER = _save("Holder", lambda m: _chain(m, "sleep_node", 1, duration=60), callable_=False)


def _nested(depth):
    child = _save("Nested 0", lambda m: _chain(m, "no_op_node", 1))
    for level in range(1, depth):
        def build(m, target=child):
            start = m.add_node("start_node")
            call = m.add_node("subworkflow_node")
            m.update_node_config(call, {**m.get_node_data(call)["config"], "workflow_id": target})
            end = m.add_node("end_node")
            m.update_node_config(end, {**m.get_node_data(end)["config"], "return_end": True})
            m.connect(start, "default", call, "input")
            m.connect(call, "default", end, "input")
        child = _save(f"Nested {level}", build)
    return child


async def _with_root(body, max_live=1000, max_depth=10):
    """Run ``body(master, run)`` while a root run (a long sleep) is active."""
    service = RunService.create()
    service.configuration.set("max_live_subworkflow_runs", max_live)
    service.configuration.set("max_subworkflow_depth", max_depth)
    service.load(HOLDER)
    policy, provider = unattended_policies("terminate_branch")
    await service.start(recovery_policy=policy, input_provider=provider, validate=False)
    master = service.master_state
    try:
        return await body(master, master.run_context)
    finally:
        service.stop()
        await service.wait()
        service.close()


async def concurrent(child, count):
    root_bus_subscribers = {}

    async def body(master, run):
        root_bus_subscribers["before"] = sum(len(v) for v in master.event_bus._subscribers.values())
        tracemalloc.start()
        started = time.perf_counter()
        results = await asyncio.gather(*[
            call_subworkflow(master, run, "bench", "bench", child, {}) for _ in range(count)
        ], return_exceptions=True)
        seconds = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        failures = [r for r in results if isinstance(r, Exception)]
        root_bus_subscribers["after"] = sum(len(v) for v in master.event_bus._subscribers.values())
        return seconds, peak, failures, master.call_tree_for(run).live

    seconds, peak, failures, live = await _with_root(body)
    gc.collect()
    masters = sum(isinstance(o, MasterState) for o in gc.get_objects())
    return seconds, peak, len(failures), live, masters, root_bus_subscribers


async def nested(depth):
    top = _nested(depth)

    async def body(master, run):
        started = time.perf_counter()
        await call_subworkflow(master, run, "bench", "bench", top, {})
        return time.perf_counter() - started

    return await _with_root(body)


async def sequential(calls, history_records):
    for index in range(history_records):
        persistence.save_json_record(persistence.RUN_HISTORY_DIR, f"old_{index}",
                                     {"run_id": f"old_{index}", "started_at": f"2026-01-01T00:{index:06d}"})
    child = _save("Short", lambda m: _chain(m, "no_op_node", 2))

    async def body(master, run):
        started = time.perf_counter()
        for _ in range(calls):
            await call_subworkflow(master, run, "bench", "bench", child, {})
        return (time.perf_counter() - started) / calls

    return await _with_root(body)


def main() -> None:
    print("Concurrent children (wall time, peak traced memory, failures, live after, "
          "MasterState objects after gc, root bus subscriptions before/after)")
    for label, child in (("waiting 0.5 s", WAITING), ("busy 60 nodes", BUSY)):
        for count in (10, 50, 100, 200):
            seconds, peak, failures, live, masters, subs = asyncio.run(concurrent(child, count))
            print(f"  {label:14} x{count:<4} {seconds:7.3f} s  {peak / 1e6:7.1f} MB  "
                  f"failed {failures}  live {live}  masters {masters}  subs {subs['before']}/{subs['after']}")
    for depth in (2, 4, 8):
        print(f"Nested chain, depth {depth}: {asyncio.run(nested(depth)) * 1000:.1f} ms")
    per_call = asyncio.run(sequential(100, 2000))
    print(f"Sequential short calls with 2000 saved history records: {per_call * 1000:.2f} ms per call")


if __name__ == "__main__":
    main()

"""Acceptance tests for the debug node library.

Run from attackofthenodes_v05/:
    python -m pytest tests/test_debug_nodes.py -v
or standalone:
    python tests/test_debug_nodes.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Allow running as `python3 attackofthenodes_v05/tests/test_debug_nodes.py`
# or `python -m pytest tests/test_debug_nodes.py` from attackofthenodes_v05/
sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_services():
    """Construct a fresh set of backend services for one test run."""
    from backend.configuration_manager import ConfigurationManager
    from backend.event_bus import EventBus
    from backend.master_state import MasterState
    from backend.memory_bank import MemoryBank
    from backend.node_factory import NodeFactory
    from backend.output_manager import OutputManager
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    memory_bank = MemoryBank(bus)
    master = MasterState(
        workflow_map,
        memory_bank,
        bus,
        output_manager=OutputManager(),
        configuration_manager=ConfigurationManager(),
    )
    return master, workflow_map, memory_bank, bus


# ---------------------------------------------------------------------------
# 1. Linear traversal order
# ---------------------------------------------------------------------------

def test_linear_traversal_order():
    asyncio.run(_test_linear_traversal_order())


async def _test_linear_traversal_order():
    master, wm, mb, _ = _make_services()
    wm.create_new("test_linear")
    start = wm.add_node("start_node")
    l1 = wm.add_node("logger_node")
    l2 = wm.add_node("logger_node")
    l3 = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.update_node_config(l1, {"label": "step1", "include_input": False})
    wm.update_node_config(l2, {"label": "step2", "include_input": False})
    wm.update_node_config(l3, {"label": "step3", "include_input": False})

    wm.connect(start, "default", l1, "input")
    wm.connect(l1, "default", l2, "input")
    wm.connect(l2, "default", l3, "input")
    wm.connect(l3, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    log = mb.read_persistent("output_log", default=[])
    assert master.state.value == "FINISHED", f"Expected FINISHED, got {master.state.value}"
    labels = [str(e) for e in log]
    # All three logger labels must be present (EndNode may also write entries)
    assert any("step1" in s for s in labels), f"step1 not found in {labels}"
    assert any("step2" in s for s in labels), f"step2 not found in {labels}"
    assert any("step3" in s for s in labels), f"step3 not found in {labels}"
    # step1 must appear before step2, step2 before step3
    idx1 = next(i for i, s in enumerate(labels) if "step1" in s)
    idx2 = next(i for i, s in enumerate(labels) if "step2" in s)
    idx3 = next(i for i, s in enumerate(labels) if "step3" in s)
    assert idx1 < idx2 < idx3, f"Log out of order: {idx1} {idx2} {idx3} in {labels}"
    print("test_linear_traversal_order PASSED")


# ---------------------------------------------------------------------------
# 2. Counter accumulates
# ---------------------------------------------------------------------------

def test_counter_accumulates():
    asyncio.run(_test_counter_accumulates())


async def _test_counter_accumulates():
    master, wm, mb, _ = _make_services()
    wm.create_new("test_counter")
    start = wm.add_node("start_node")
    c1 = wm.add_node("counter_node")
    c2 = wm.add_node("counter_node")
    c3 = wm.add_node("counter_node")
    end = wm.add_node("end_node")

    for c in (c1, c2, c3):
        wm.update_node_config(c, {"counter_name": "n"})

    wm.connect(start, "default", c1, "input")
    wm.connect(c1, "default", c2, "input")
    wm.connect(c2, "default", c3, "input")
    wm.connect(c3, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    assert mb.read_persistent("n") == 3
    print("test_counter_accumulates PASSED")


# ---------------------------------------------------------------------------
# 3. Sleep does not block event loop
# ---------------------------------------------------------------------------

def test_sleep_does_not_block():
    asyncio.run(_test_sleep_does_not_block())


async def _test_sleep_does_not_block():
    master, wm, mb, _ = _make_services()
    wm.create_new("test_sleep")
    start = wm.add_node("start_node")
    sleep = wm.add_node("sleep_node")
    end = wm.add_node("end_node")

    wm.update_node_config(sleep, {"duration": 0.2})
    wm.connect(start, "default", sleep, "input")
    wm.connect(sleep, "default", end, "input")

    t0 = time.monotonic()
    await master.start_workflow()
    await master.wait_for_completion()
    elapsed = time.monotonic() - t0

    assert master.state.value == "FINISHED"
    assert elapsed < 0.7, f"Sleep took too long: {elapsed:.2f}s"
    print(f"test_sleep_does_not_block PASSED ({elapsed:.3f}s)")


# ---------------------------------------------------------------------------
# 4. Error node fails workflow
# ---------------------------------------------------------------------------

def test_error_node_fails_workflow():
    asyncio.run(_test_error_node_fails_workflow())


async def _test_error_node_fails_workflow():
    master, wm, mb, bus = _make_services()
    from backend.events import RECOVERY_OPTIONS_AVAILABLE

    wm.create_new("test_error")
    start = wm.add_node("start_node")
    err = wm.add_node("error_node")
    end = wm.add_node("end_node")

    wm.update_node_config(err, {"message": "deliberate test error", "error_mode": "fail"})
    wm.connect(start, "default", err, "input")
    wm.connect(err, "default", end, "input")

    # Auto-terminate on recovery prompt
    def auto_terminate(payload):
        async def act():
            await asyncio.sleep(0)
            master.submit_recovery_action(payload["branch_id"], "TERMINATE_WORKFLOW")
        asyncio.create_task(act())

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, auto_terminate)

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "ERROR", f"Expected ERROR, got {master.state.value}"
    print("test_error_node_fails_workflow PASSED")


# ---------------------------------------------------------------------------
# 5. Deep branch respects depth limit
# ---------------------------------------------------------------------------

def test_deep_branch_respects_depth_limit():
    asyncio.run(_test_deep_branch_respects_depth_limit())


async def _test_deep_branch_respects_depth_limit():
    master, wm, mb, _ = _make_services()
    wm.create_new("test_deep_branch")
    start = wm.add_node("start_node")
    deep = wm.add_node("deep_branch_node")
    end = wm.add_node("end_node")

    # Only the default port connects forward; branch port has no target (rejected gracefully)
    wm.connect(start, "default", deep, "input")
    wm.connect(deep, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value in ("FINISHED", "ERROR"), (
        f"Unexpected state: {master.state.value}"
    )
    print(f"test_deep_branch_respects_depth_limit PASSED (state={master.state.value})")


# ---------------------------------------------------------------------------
# 6. Variable round-trip
# ---------------------------------------------------------------------------

def test_variable_round_trip():
    asyncio.run(_test_variable_round_trip())


async def _test_variable_round_trip():
    master, wm, mb, _ = _make_services()
    wm.create_new("test_var_round_trip")
    start = wm.add_node("start_node")
    setter = wm.add_node("variable_setter_node")
    reader = wm.add_node("variable_reader_node")
    logger = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.update_node_config(setter, {"variable_name": "x", "value": "hello"})
    wm.update_node_config(reader, {"variable_name": "x", "default": ""})
    wm.update_node_config(logger, {"label": "round_trip", "include_input": True})

    wm.connect(start, "default", setter, "input")
    wm.connect(setter, "default", reader, "input")
    wm.connect(reader, "default", logger, "input")
    wm.connect(logger, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    log = mb.read_persistent("output_log", default=[])
    assert any("hello" in str(e) for e in log), f"'hello' not found in log: {log}"
    print("test_variable_round_trip PASSED")


# ---------------------------------------------------------------------------
# 7. Conditional routes correctly (uses existing ConditionalNode + supervisor patch)
# ---------------------------------------------------------------------------

def test_conditional_routes_correctly():
    asyncio.run(_test_conditional_routes_correctly())


async def _test_conditional_routes_correctly():
    master, wm, mb, _ = _make_services()
    wm.create_new("test_conditional")
    start = wm.add_node("start_node")
    cond = wm.add_node("conditional_node")
    true_logger = wm.add_node("logger_node")
    false_logger = wm.add_node("logger_node")
    end_true = wm.add_node("end_node")
    end_false = wm.add_node("end_node")

    wm.update_node_config(start, {"greeting": "needle"})
    wm.update_node_config(cond, {
        "condition_type": "contains",
        "left_value_source": "input",
        "variable_name": "",
        "right_value": "needle",
    })
    wm.update_node_config(true_logger, {"label": "true_path", "include_input": False})
    wm.update_node_config(false_logger, {"label": "false_path", "include_input": False})

    wm.connect(start, "default", cond, "input")
    wm.connect(cond, "true", true_logger, "input")
    wm.connect(cond, "false", false_logger, "input")
    wm.connect(true_logger, "default", end_true, "input")
    wm.connect(false_logger, "default", end_false, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    log = mb.read_persistent("output_log", default=[])
    log_strs = [str(e) for e in log]
    assert any("true_path" in s for s in log_strs), f"Expected true_path in log: {log_strs}"
    assert not any("false_path" in s for s in log_strs), f"false_path should not appear: {log_strs}"
    print("test_conditional_routes_correctly PASSED")


# ---------------------------------------------------------------------------
# 8. Repeat counter detects loops
# ---------------------------------------------------------------------------

def test_repeat_counter_detects_loops():
    asyncio.run(_test_repeat_counter_detects_loops())


async def _test_repeat_counter_detects_loops():
    master, wm, mb, bus = _make_services()
    from backend.events import RECOVERY_OPTIONS_AVAILABLE

    wm.create_new("test_repeat")
    start = wm.add_node("start_node")
    repeat = wm.add_node("repeat_counter_node")

    wm.update_node_config(repeat, {"max_visits": 3})
    wm.connect(start, "default", repeat, "input")
    # Self-loop: repeat's default output feeds back into its own input
    wm.connect(repeat, "default", repeat, "input")

    def auto_terminate(payload):
        async def act():
            await asyncio.sleep(0)
            master.submit_recovery_action(payload["branch_id"], "TERMINATE_WORKFLOW")
        asyncio.create_task(act())

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, auto_terminate)

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "ERROR", f"Expected ERROR, got {master.state.value}"
    print("test_repeat_counter_detects_loops PASSED")


# ---------------------------------------------------------------------------
# Memory-leak regression helpers
# ---------------------------------------------------------------------------

async def _run_trivial(master, wm) -> None:
    """Run the workflow on wm (must already have start→end connected) once."""
    await master.start_workflow()
    await master.wait_for_completion()


# ---------------------------------------------------------------------------
# 9. OutputManager evicts in-memory outputs after finalization
# ---------------------------------------------------------------------------

def test_output_manager_evicts_after_run():
    asyncio.run(_test_output_manager_evicts_after_run())


async def _test_output_manager_evicts_after_run():
    master, wm, _, _ = _make_services()
    wm.create_new("leak_om")
    start = wm.add_node("start_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", end, "input")

    for i in range(3):
        await _run_trivial(master, wm)
        assert master.state.value == "FINISHED", f"Run {i} did not finish"
        leaked = len(master._output_manager._outputs_by_run)
        assert leaked == 0, (
            f"Run {i}: OutputManager._outputs_by_run has {leaked} entry/entries "
            f"after finalization — keys: {list(master._output_manager._outputs_by_run)}"
        )
    print("test_output_manager_evicts_after_run PASSED")


# ---------------------------------------------------------------------------
# 10. ErrorHandler evicts in-memory errors after finalization
# ---------------------------------------------------------------------------

def test_error_handler_evicts_after_run():
    asyncio.run(_test_error_handler_evicts_after_run())


async def _test_error_handler_evicts_after_run():
    master, wm, _, _ = _make_services()
    wm.create_new("leak_eh")
    start = wm.add_node("start_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", end, "input")

    for i in range(3):
        await _run_trivial(master, wm)
        assert master.state.value == "FINISHED", f"Run {i} did not finish"
        leaked = len(master._error_handler._errors_by_run)
        assert leaked == 0, (
            f"Run {i}: ErrorHandler._errors_by_run has {leaked} entry/entries "
            f"after finalization — keys: {list(master._error_handler._errors_by_run)}"
        )
    print("test_error_handler_evicts_after_run PASSED")


# ---------------------------------------------------------------------------
# 11. RunHistory._runs respects _MAX_IN_MEMORY cap
# ---------------------------------------------------------------------------

def test_run_history_respects_memory_cap():
    asyncio.run(_test_run_history_respects_memory_cap())


async def _test_run_history_respects_memory_cap():
    from backend.run_history import RunHistory

    master, wm, _, _ = _make_services()
    wm.create_new("leak_cap")
    start = wm.add_node("start_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", end, "input")

    cap = RunHistory._MAX_IN_MEMORY
    initial = len(master.run_history._runs)
    runs = 20  # enough to verify trimming without hitting the full cap
    for i in range(runs):
        await _run_trivial(master, wm)
        assert master.state.value == "FINISHED", f"Run {i} did not finish"

    in_memory = len(master.run_history._runs)
    assert in_memory <= cap, (
        f"RunHistory._runs has {in_memory} entries, exceeds cap of {cap}"
    )
    expected = min(cap, initial + runs)
    assert in_memory == expected, (
        f"Expected {expected} entries after {runs} runs from an initial "
        f"{initial}, got {in_memory}"
    )
    print(f"test_run_history_respects_memory_cap PASSED ({in_memory}/{cap})")


# ---------------------------------------------------------------------------
# 12. RunHistory records do not embed raw output values
# ---------------------------------------------------------------------------

def test_run_history_record_has_no_embedded_outputs():
    asyncio.run(_test_run_history_record_has_no_embedded_outputs())


async def _test_run_history_record_has_no_embedded_outputs():
    master, wm, _, _ = _make_services()
    wm.create_new("leak_embed")
    start = wm.add_node("start_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", end, "input")

    await _run_trivial(master, wm)
    assert master.state.value == "FINISHED"

    records = master.run_history.list_runs()
    assert records, "No history records found"
    latest = records[0]
    assert "outputs" not in latest, (
        f"RunHistory record embeds raw output values — remove the 'outputs' key. "
        f"Keys found: {list(latest)}"
    )
    assert "output_count" in latest, "History record is missing 'output_count'"
    print("test_run_history_record_has_no_embedded_outputs PASSED")


# ---------------------------------------------------------------------------
# 13. WorkflowMap forward reachability helper
# ---------------------------------------------------------------------------

def test_nodes_reachable_from_branching_graph():
    master, wm, _, _ = _make_services()
    wm.create_new("reachability")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    left = wm.add_node("logger_node")
    right = wm.add_node("logger_node")
    left_child = wm.add_node("logger_node")
    right_child = wm.add_node("logger_node")
    dangling = wm.add_node("logger_node")

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", left, "input")
    wm.connect(branch, "path_b", right, "input")
    wm.connect(left, "default", left_child, "input")
    wm.connect(right, "default", right_child, "input")
    wm.connect(left_child, "default", left_child, "input")  # self-loop guard

    assert wm.nodes_reachable_from(branch) == {left, right, left_child, right_child}
    assert wm.nodes_reachable_from(left) == {left_child}
    assert wm.nodes_reachable_from(right) == {right_child}
    assert wm.nodes_reachable_from(left_child) == set()
    assert wm.nodes_reachable_from(dangling) == set()
    assert start not in wm.nodes_reachable_from(branch)
    assert right not in wm.nodes_reachable_from(left)
    assert branch not in wm.nodes_reachable_from(left)
    print("test_nodes_reachable_from_branching_graph PASSED")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_linear_traversal_order,
        test_counter_accumulates,
        test_sleep_does_not_block,
        test_error_node_fails_workflow,
        test_deep_branch_respects_depth_limit,
        test_variable_round_trip,
        test_conditional_routes_correctly,
        test_repeat_counter_detects_loops,
        test_output_manager_evicts_after_run,
        test_error_handler_evicts_after_run,
        test_run_history_respects_memory_cap,
        test_run_history_record_has_no_embedded_outputs,
        test_nodes_reachable_from_branching_graph,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as exc:
            print(f"FAILED {t.__name__}: {exc}")
            failed.append(t.__name__)
    if failed:
        print(f"\n{len(failed)} test(s) FAILED: {failed}")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} tests PASSED")

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
# 14. SaveManager writes derived input_sources
# ---------------------------------------------------------------------------

def test_save_manager_writes_input_sources():
    from backend.persistence import delete_workflow, load_workflow
    from backend.save_manager import SaveManager

    _, wm, _, _ = _make_services()
    wm.create_new("input_sources_save")
    start = wm.add_node("start_node")
    consumer = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.update_node_config(consumer, {"membank_inputs": ["session_id"]})
    wm.connect(start, "default", consumer, "input")
    wm.connect(consumer, "default", end, "input")

    workflow_id = wm.workflow_id
    try:
        assert SaveManager(wm).save_current_workflow()
        saved = load_workflow(workflow_id) or {}
    finally:
        delete_workflow(workflow_id)

    sources = saved["nodes"][consumer]["input_sources"]
    assert {"type": "node", "source_id": start, "port": "default"} in sources
    assert {"type": "membank", "source_id": "session_id"} in sources
    assert "input_sources" in saved["nodes"][start]
    print("test_save_manager_writes_input_sources PASSED")


# ---------------------------------------------------------------------------
# 15. Validator flags missing derived input sources
# ---------------------------------------------------------------------------

def test_validator_flags_missing_input_sources():
    from backend.validator import validate_workflow

    _, wm, _, _ = _make_services()
    factory = wm._factory
    wm.create_new("input_sources_validation")
    start = wm.add_node("start_node")
    consumer = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.connect(start, "default", consumer, "input")
    wm.connect(consumer, "default", end, "input")
    consumer_data = wm.get_node_data(consumer)
    consumer_data["connections"]["inputs"].append(
        {
            "target_port": "input",
            "source_node_id": "missing_node",
            "source_port": "default",
        }
    )

    result = validate_workflow(wm, factory)
    assert not result["success"]
    assert any(
        err["node_id"] == consumer
        and "Input source missing node: missing_node" in err["message"]
        for err in result["errors"]
    ), result["errors"]
    print("test_validator_flags_missing_input_sources PASSED")


def test_validator_flags_missing_membank_input_sources():
    from backend.validator import validate_workflow

    _, wm, _, _ = _make_services()
    factory = wm._factory
    wm.create_new("membank_validation")
    start = wm.add_node("start_node")
    consumer = wm.add_node("logger_node")
    writer = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.update_node_config(consumer, {"membank_inputs": ["session_id"]})
    wm.connect(start, "default", consumer, "input")
    wm.connect(consumer, "default", end, "input")

    missing_result = validate_workflow(wm, factory)
    assert any(
        err["node_id"] == consumer
        and "Membank input source not declared: session_id" in err["message"]
        for err in missing_result["errors"]
    ), missing_result["errors"]

    wm.update_node_config(
        writer,
        {"membank_outputs": [{"id": "session_id", "description": "Session id"}]},
    )
    declared_result = validate_workflow(wm, factory)
    assert not any(
        "Membank input source not declared: session_id" in err["message"]
        for err in declared_result["errors"]
    ), declared_result["errors"]
    print("test_validator_flags_missing_membank_input_sources PASSED")


# ---------------------------------------------------------------------------
# 17. Membank registry filters downstream-only writers
# ---------------------------------------------------------------------------

def test_membank_registry_filters_downstream_writers():
    from frontend.screens.node_config import (
        build_membank_registry,
        membank_input_options,
        normalize_membank_inputs,
        normalize_membank_outputs,
    )

    _, wm, _, _ = _make_services()
    wm.create_new("membank_registry")
    upstream = wm.add_node("logger_node")
    consumer = wm.add_node("logger_node")
    downstream = wm.add_node("logger_node")
    sibling = wm.add_node("logger_node")

    wm.update_node_config(
        upstream,
        {"membank_outputs": [{"id": "session_id", "description": "Session id"}]},
    )
    wm.update_node_config(
        downstream,
        {"membank_outputs": [{"id": "future_value", "description": "Future"}]},
    )
    wm.update_node_config(
        sibling,
        {"membank_outputs": [{"output": "sibling_value", "description": "Sibling"}]},
    )
    wm.update_node_config(
        consumer,
        {"membank_outputs": [{"id": "own_value", "description": "Own"}]},
    )
    wm.connect(upstream, "default", consumer, "input")
    wm.connect(consumer, "default", downstream, "input")

    registry = build_membank_registry(wm)
    assert registry["session_id"]["writers"] == [upstream]
    assert normalize_membank_outputs(wm.get_node_data(upstream)["config"]) == [
        {"id": "session_id", "output": "session_id", "description": "Session id"}
    ]
    assert normalize_membank_inputs({"membank_inputs": [{"id": "session_id"}]}) == [
        "session_id"
    ]

    option_rows = membank_input_options(wm, consumer)
    option_values = {value for _, value in option_rows}
    assert "session_id" in option_values
    assert "sibling_value" in option_values
    assert "future_value" not in option_values
    assert "own_value" not in option_values
    assert any(
        label.startswith("Output Description: Session id | Output: session_id")
        for label, value in option_rows
        if value == "session_id"
    )
    print("test_membank_registry_filters_downstream_writers PASSED")


# ---------------------------------------------------------------------------
# 18. Insert-between rewires below the selected source node
# ---------------------------------------------------------------------------

def test_insert_between_rewires_below_source_node():
    _, wm, _, _ = _make_services()
    wm.create_new("insert_between")
    start = wm.add_node("start_node")
    highlighted = wm.add_node("logger_node")
    downstream = wm.add_node("logger_node")
    inserted = wm.add_node("logger_node")

    wm.connect(start, "default", highlighted, "input")
    wm.connect(highlighted, "default", downstream, "input")

    old_edge = wm.get_node_data(highlighted)["connections"]["outputs"][0]
    assert old_edge["target_node_id"] == downstream
    assert wm.disconnect(
        highlighted,
        "default",
        downstream,
        old_edge.get("target_port", "input"),
    )
    assert wm.connect(highlighted, "default", inserted, "input")
    assert wm.connect(inserted, "default", downstream, "input")

    highlighted_outputs = wm.get_node_data(highlighted)["connections"]["outputs"]
    inserted_outputs = wm.get_node_data(inserted)["connections"]["outputs"]
    downstream_inputs = wm.get_node_data(downstream)["connections"]["inputs"]

    assert highlighted_outputs == [
        {
            "source_port": "default",
            "target_node_id": inserted,
            "target_port": "input",
        }
    ]
    assert inserted_outputs == [
        {
            "source_port": "default",
            "target_node_id": downstream,
            "target_port": "input",
        }
    ]
    assert downstream_inputs == [
        {
            "target_port": "input",
            "source_node_id": inserted,
            "source_port": "default",
        }
    ]
    print("test_insert_between_rewires_below_source_node PASSED")


# ---------------------------------------------------------------------------
# 19. Tombstone delete does not cascade downstream branch nodes
# ---------------------------------------------------------------------------

def test_tombstone_delete_does_not_cascade_branch_nodes():
    _, wm, _, _ = _make_services()
    wm.create_new("delete_no_cascade")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    left = wm.add_node("logger_node")
    right = wm.add_node("logger_node")

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", left, "input")
    wm.connect(branch, "path_b", right, "input")

    assert wm.replace_with_tombstone(branch)
    all_nodes = wm.get_all_node_data()
    assert branch in all_nodes
    assert all_nodes[branch]["type"] == "tombstone_node"
    assert left in all_nodes
    assert right in all_nodes
    print("test_tombstone_delete_does_not_cascade_branch_nodes PASSED")


def test_tombstone_restore_preserves_original_and_swap_invalidates_timing():
    _, wm, _, _ = _make_services()
    wm.create_new("tombstone_restore")
    node_id = wm.add_node("logger_node", alias="Original Logger")
    wm.update_node_config(node_id, {"message": "original"})

    assert wm.replace_with_tombstone(node_id)
    tombstone = wm.get_node_data(node_id)
    assert tombstone["type"] == "tombstone_node"
    assert tombstone["config"]["original_alias"] == "Original Logger"
    assert tombstone["config"]["original_config"] == {"message": "original"}

    assert wm.replace_node_type(node_id, "logger_node")
    restored = wm.get_node_data(node_id)
    assert restored["type"] == "logger_node"
    assert restored["alias"] == "Original Logger"
    assert restored["config"] == {"message": "original"}
    assert restored["_timing_invalidated"] is False

    assert wm.replace_with_tombstone(node_id)
    assert wm.replace_node_type(node_id, "sleep_node")
    swapped = wm.get_node_data(node_id)
    assert swapped["type"] == "sleep_node"
    assert swapped["_timing_invalidated"] is True
    print("test_tombstone_restore_preserves_original_and_swap_invalidates_timing PASSED")


# ---------------------------------------------------------------------------
# 20. Utility memory writers can pass input through
# ---------------------------------------------------------------------------

def test_set_variable_node_can_pass_input_through():
    asyncio.run(_test_set_variable_node_can_pass_input_through())


async def _test_set_variable_node_can_pass_input_through():
    master, wm, mb, _ = _make_services()
    wm.create_new("set_variable_pass_through")
    start = wm.add_node("start_node")
    setter = wm.add_node("set_variable_node")
    logger = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.update_node_config(start, {"greeting": "original-input"})
    wm.update_node_config(
        setter,
        {
            "variable_name": "saved",
            "value_source": "literal",
            "value": "stored-value",
            "pass_through": True,
        },
    )
    wm.update_node_config(logger, {"label": "after_set", "include_input": True})
    wm.connect(start, "default", setter, "input")
    wm.connect(setter, "default", logger, "input")
    wm.connect(logger, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert mb.read_persistent("saved") == "stored-value"
    log = [str(entry) for entry in mb.read_persistent("output_log", default=[])]
    assert any("original-input" in entry for entry in log), log
    print("test_set_variable_node_can_pass_input_through PASSED")


def test_branch_node_default_labels_are_configurable():
    from backend.nodes.branch_node import BranchNode

    assert BranchNode.default_config["path_a_label"] == "Path A"
    assert BranchNode.default_config["path_b_label"] == "Path B"
    assert "path_a_label" in BranchNode.config_schema
    assert "path_b_label" in BranchNode.config_schema
    assert BranchNode.config_schema["path_a_label"]["label"] == "Path A branch name"
    assert BranchNode.config_schema["path_a_label"]["group"] == "Branch Names"
    print("test_branch_node_default_labels_are_configurable PASSED")


def test_branch_config_uses_generated_labels_without_memory_outputs():
    asyncio.run(_test_branch_config_uses_generated_labels_without_memory_outputs())


async def _test_branch_config_uses_generated_labels_without_memory_outputs():
    from textual.app import App, ComposeResult

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.screens.editor import EditorScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()
    wm.create_new("branch_config_labels")
    branch = wm.add_node("random_branch_node")
    wm.update_node_config(
        branch,
        {
            "seed": "stable",
            "path_a_label": "Approve",
            "path_b_label": "Reject",
            "membank_outputs": [{"id": "should_not_render"}],
        },
    )
    node_data = wm.get_node_data(branch)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, branch, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.query_one(NodeConfigScreen)
        assert app.query_one("#field-path_a_label", CommandInput).value == "Approve"
        assert app.query_one("#field-path_b_label", CommandInput).value == "Reject"
        assert not app.query("#membank-writes")
        values = screen._membank_config_values()
        assert values["membank_outputs"] == []

    editor = EditorScreen(wm._factory, wm)
    labels = editor._branch_port_labels(wm.get_node_data(branch))
    assert labels["path_a"] == "Approve"
    assert labels["path_b"] == "Reject"
    print("test_branch_config_uses_generated_labels_without_memory_outputs PASSED")


def test_sleep_config_shows_pass_through_hint():
    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("sleep_pass_through_hint")
    sleep = wm.add_node("sleep_node")
    screen = NodeConfigScreen(wm._factory, wm, sleep, wm.get_node_data(sleep))
    metadata = screen._metadata_for_type("sleep_node")

    assert metadata["ui_hints"]["pass_through"]
    assert "forwards the previous node output" in screen._pass_through_note(metadata)
    print("test_sleep_config_shows_pass_through_hint PASSED")


# ---------------------------------------------------------------------------
# 22. Form generator groups config fields into tabs only when useful
# ---------------------------------------------------------------------------

def test_form_generator_groups_schema_for_tabs():
    from frontend.widgets.form_generator import group_config_schema, schema_uses_tabs

    single_group_schema = {
        "duration": {"type": "float", "label": "Seconds", "group": "Timing"},
        "jitter": {"type": "float", "label": "Jitter", "group": "Timing"},
    }
    grouped_schema = {
        "duration": {"type": "float", "label": "Seconds", "group": "Timing"},
        "mode": {"type": "select", "label": "Mode", "group": "Behavior"},
        "notes": {"type": "string", "label": "Notes"},
    }

    assert not schema_uses_tabs(single_group_schema)
    assert [name for name, _ in group_config_schema(single_group_schema)] == ["Timing"]

    assert schema_uses_tabs(grouped_schema)
    groups = group_config_schema(grouped_schema)
    assert [name for name, _ in groups] == ["Timing", "Behavior", "Settings"]
    assert list(groups[0][1]) == ["duration"]
    assert list(groups[1][1]) == ["mode"]
    assert list(groups[2][1]) == ["notes"]
    print("test_form_generator_groups_schema_for_tabs PASSED")


def test_form_generator_mounts_tabbed_and_single_group_forms():
    asyncio.run(_test_form_generator_mounts_tabbed_and_single_group_forms())


async def _test_form_generator_mounts_tabbed_and_single_group_forms():
    from textual.app import App, ComposeResult
    from textual.widgets import Input, TabbedContent

    from frontend.widgets.form_generator import build_form

    grouped_schema = {
        "duration": {"type": "float", "label": "Seconds", "group": "Timing"},
        "mode": {
            "type": "select",
            "label": "Mode",
            "group": "Behavior",
            "options": ["short", "long"],
        },
    }
    single_group_schema = {
        "duration": {"type": "float", "label": "Seconds", "group": "Timing"},
    }

    class GroupedFormApp(App):
        def compose(self) -> ComposeResult:
            form, _ = build_form(grouped_schema, {"duration": 0})
            yield form

    class SingleGroupFormApp(App):
        def compose(self) -> ComposeResult:
            form, _ = build_form(single_group_schema, {"duration": 0})
            yield form

    grouped_app = GroupedFormApp()
    async with grouped_app.run_test():
        assert grouped_app.query_one("#generated-form-tabs", TabbedContent)
        assert grouped_app.query_one("#field-duration", Input).value == "0"

    single_app = SingleGroupFormApp()
    async with single_app.run_test():
        assert not single_app.query("#generated-form-tabs")
        assert single_app.query_one("#field-duration", Input).value == "0"

    print("test_form_generator_mounts_tabbed_and_single_group_forms PASSED")


def test_form_generator_honors_generic_schema_hints():
    asyncio.run(_test_form_generator_honors_generic_schema_hints())


async def _test_form_generator_honors_generic_schema_hints():
    from textual.app import App, ComposeResult
    from textual.validation import Number
    from textual.widgets import Input, SelectionList, TextArea

    from frontend.widgets.form_generator import build_form

    schema = {
        "duration": {
            "type": "float",
            "label": "Duration",
            "placeholder": "0.25",
            "min": 0.0,
            "max": 60.0,
        },
        "notes": {
            "type": "multiline",
            "label": "Notes",
            "placeholder": "Optional long text",
            "height": 6,
        },
        "modes": {
            "type": "multiselect",
            "label": "Modes",
            "options": ["fast", "safe", "verbose"],
        },
    }

    getter_holder = {}

    class HintFormApp(App):
        def compose(self) -> ComposeResult:
            form, getter = build_form(
                schema,
                {"duration": 0, "notes": "", "modes": ["safe", "verbose"]},
            )
            getter_holder["get_values"] = getter
            yield form

    app = HintFormApp()
    async with app.run_test():
        duration = app.query_one("#field-duration", Input)
        notes = app.query_one("#field-notes", TextArea)
        modes = app.query_one("#field-modes", SelectionList)

        assert duration.value == "0"
        assert duration.placeholder == "0.25"
        assert any(isinstance(validator, Number) for validator in duration.validators)
        assert notes.placeholder == "Optional long text"
        assert notes.styles.height.value == 6
        assert set(modes.selected) == {"safe", "verbose"}
        assert getter_holder["get_values"]()["modes"] == ["safe", "verbose"]

    print("test_form_generator_honors_generic_schema_hints PASSED")


# ---------------------------------------------------------------------------
# 24. Breakpoints pause before node execution and resume cleanly
# ---------------------------------------------------------------------------

def test_workflow_map_breakpoint_flags_are_persisted_in_node_data():
    _, wm, _, _ = _make_services()
    wm.create_new("breakpoint_flags")
    node_id = wm.add_node("logger_node")

    node = wm.get_node_data(node_id)
    assert node["breakpoint"] is False

    assert wm.set_breakpoint(node_id, True)
    assert wm.get_node_data(node_id)["breakpoint"] is True
    saved = wm.get_workflow_data_for_save()
    assert saved["nodes"][node_id]["breakpoint"] is True

    assert wm.clear_all_breakpoints() == 1
    assert wm.get_node_data(node_id)["breakpoint"] is False
    print("test_workflow_map_breakpoint_flags_are_persisted_in_node_data PASSED")


def test_breakpoint_pauses_before_node_execution_and_resumes():
    asyncio.run(_test_breakpoint_pauses_before_node_execution_and_resumes())


async def _test_breakpoint_pauses_before_node_execution_and_resumes():
    from backend.events import BREAKPOINT_HIT

    master, wm, mb, bus = _make_services()
    hits = []
    bus.subscribe(BREAKPOINT_HIT, hits.append)

    wm.create_new("breakpoint_run")
    start = wm.add_node("start_node")
    logger_node = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.update_node_config(logger_node, {"label": "breakpoint_logger", "include_input": False})
    wm.set_breakpoint(logger_node, True)
    wm.connect(start, "default", logger_node, "input")
    wm.connect(logger_node, "default", end, "input")

    await master.start_workflow()
    for _ in range(100):
        if master.state.value == "PAUSED":
            break
        await asyncio.sleep(0.01)

    assert master.state.value == "PAUSED"
    assert hits and hits[-1]["node_id"] == logger_node
    paused_log = [str(entry) for entry in mb.read_persistent("output_log", default=[])]
    assert not any("breakpoint_logger" in entry for entry in paused_log), paused_log

    master.resume()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    final_log = [str(entry) for entry in mb.read_persistent("output_log", default=[])]
    assert any("breakpoint_logger" in entry for entry in final_log), final_log
    print("test_breakpoint_pauses_before_node_execution_and_resumes PASSED")


# ---------------------------------------------------------------------------
# 26. Per-node execution timing is recorded in run history
# ---------------------------------------------------------------------------

def test_node_timings_are_recorded_for_run_history():
    asyncio.run(_test_node_timings_are_recorded_for_run_history())


async def _test_node_timings_are_recorded_for_run_history():
    from backend.events import NODE_TIMING_UPDATE

    master, wm, _, bus = _make_services()
    timing_events = []
    bus.subscribe(NODE_TIMING_UPDATE, timing_events.append)

    wm.create_new("node_timing")
    start = wm.add_node("start_node")
    sleep = wm.add_node("sleep_node")
    end = wm.add_node("end_node")

    wm.update_node_config(sleep, {"duration": 0.05})
    wm.connect(start, "default", sleep, "input")
    wm.connect(sleep, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    assert sleep in master.node_timings
    assert master.node_timings[sleep] >= 0.04, master.node_timings
    assert any(event.get("node_id") == sleep for event in timing_events)

    latest = master.run_history.list_runs()[0]
    assert latest["node_timings"][sleep] == master.node_timings[sleep]
    print("test_node_timings_are_recorded_for_run_history PASSED")


# ---------------------------------------------------------------------------
# 27. WaitUntilNode gates one branch on another branch's completion
# ---------------------------------------------------------------------------

def test_wait_until_node_gates_cross_branch_completion():
    asyncio.run(_test_wait_until_node_gates_cross_branch_completion())


async def _test_wait_until_node_gates_cross_branch_completion():
    master, wm, mb, _ = _make_services()
    wm.create_new("wait_until")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    sleep = wm.add_node("sleep_node")
    first = wm.add_node("logger_node")
    wait = wm.add_node("wait_until_node")
    second = wm.add_node("logger_node")
    end_a = wm.add_node("end_node")
    end_b = wm.add_node("end_node")

    wm.update_node_config(branch, {"condition": "always_branch"})
    wm.update_node_config(sleep, {"duration": 0.05})
    wm.update_node_config(first, {"label": "first_branch", "include_input": False})
    wm.update_node_config(
        wait,
        {"target_node_ids": first, "timeout_seconds": 1.0},
    )
    wm.update_node_config(second, {"label": "second_branch", "include_input": False})

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", sleep, "input")
    wm.connect(sleep, "default", first, "input")
    wm.connect(first, "default", end_a, "input")
    wm.connect(branch, "path_b", wait, "input")
    wm.connect(wait, "default", second, "input")
    wm.connect(second, "default", end_b, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    assert first in master.completed_nodes
    log = [str(entry) for entry in mb.read_persistent("output_log", default=[])]
    first_index = next(i for i, entry in enumerate(log) if "first_branch" in entry)
    second_index = next(i for i, entry in enumerate(log) if "second_branch" in entry)
    assert first_index < second_index, log
    print("test_wait_until_node_gates_cross_branch_completion PASSED")


def test_wait_target_options_exclude_downstream_nodes():
    from frontend.screens.node_config import (
        normalize_wait_target_ids,
        wait_target_options,
    )

    _, wm, _, _ = _make_services()
    wm.create_new("wait_target_options")
    upstream = wm.add_node("logger_node")
    wait = wm.add_node("wait_until_node")
    downstream = wm.add_node("logger_node")
    sibling = wm.add_node("logger_node")

    wm.connect(upstream, "default", wait, "input")
    wm.connect(wait, "default", downstream, "input")

    assert normalize_wait_target_ids({"target_node_ids": f"{upstream}, {sibling}"}) == [
        upstream,
        sibling,
    ]
    option_values = [value for _label, value in wait_target_options(wm, wait)]
    assert upstream in option_values
    assert sibling in option_values
    assert wait not in option_values
    assert downstream not in option_values
    print("test_wait_target_options_exclude_downstream_nodes PASSED")


def test_merge_node_waits_and_forwards_selected_input():
    asyncio.run(_test_merge_node_waits_and_forwards_selected_input())


async def _test_merge_node_waits_and_forwards_selected_input():
    master, wm, mb, _ = _make_services()
    wm.create_new("merge_selected_input")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    slow = wm.add_node("sleep_node")
    left = wm.add_node("echo_node")
    right = wm.add_node("echo_node")
    merge = wm.add_node("merge_node")
    after = wm.add_node("logger_node")
    end = wm.add_node("end_node")

    wm.update_node_config(branch, {"condition": "always_branch"})
    wm.update_node_config(slow, {"duration": 0.05})
    wm.update_node_config(left, {"label": "left"})
    wm.update_node_config(right, {"label": "right"})
    wm.update_node_config(merge, {"selected_input_port": "path_a"})
    wm.update_node_config(after, {"label": "merged", "include_input": True})

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", slow, "input")
    wm.connect(slow, "default", left, "input")
    wm.connect(left, "default", merge, "path_a")
    wm.connect(branch, "path_b", right, "input")
    wm.connect(right, "default", merge, "path_b")
    wm.connect(merge, "default", after, "input")
    wm.connect(after, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    assert master.state.value == "FINISHED"
    log = [str(entry) for entry in mb.read_persistent("output_log", default=[])]
    merged_entries = [entry for entry in log if "[merged]" in entry]
    assert len(merged_entries) == 1, log
    assert "[left]" in merged_entries[0], merged_entries
    assert "[right]" not in merged_entries[0], merged_entries
    print("test_merge_node_waits_and_forwards_selected_input PASSED")


def test_merge_config_uses_multi_branch_selector_and_carry_forward_dropdown():
    asyncio.run(_test_merge_config_uses_multi_branch_selector_and_carry_forward_dropdown())


async def _test_merge_config_uses_multi_branch_selector_and_carry_forward_dropdown():
    from textual.app import App, ComposeResult
    from textual.widgets import Select, SelectionList

    from frontend.screens.node_config import NodeConfigScreen, merge_input_options

    _, wm, _, _ = _make_services()
    wm.create_new("merge_config")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    left = wm.add_node("logger_node")
    right = wm.add_node("logger_node")
    merge = wm.add_node("merge_node")
    wm.update_node_config(
        branch,
        {
            "condition": "always_branch",
            "path_a_label": "Approve Path",
            "path_b_label": "Review Path",
        },
    )
    wm.update_node_config(
        left,
        {"membank_outputs": [{"id": "approved_text", "description": "Approved output"}]},
    )
    wm.update_node_config(
        right,
        {"membank_outputs": [{"id": "review_text", "description": "Review output"}]},
    )
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", left, "input")
    wm.connect(branch, "path_b", right, "input")
    wm.update_node_config(
        merge,
        {
            "selected_branch_id": f"{branch}:path_b",
            "branches_to_close": [f"{branch}:path_a", f"{branch}:path_b"],
            "carry_forward_branch_id": f"{branch}:path_b",
            "selected_input_port": "path_b",
        },
    )
    node_data = wm.get_node_data(merge)

    options = merge_input_options(wm, merge)
    assert [option["port"] for option in options] == ["path_a", "path_b"]
    assert options[0]["branch_label"] == "Approve Path"
    assert options[0]["branch_id"] == branch
    assert options[0]["branch_port"] == "path_a"
    assert options[0]["output_name"] == "approved_text"
    assert options[0]["output_description"] == "Approved output"
    assert options[1]["branch_label"] == "Review Path"
    assert options[1]["branch_id"] == branch
    assert options[1]["branch_port"] == "path_b"

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, merge, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        branch_selector = app.query_one("#merge-branches-to-close", SelectionList)
        carry_selector = app.query_one("#merge-carry-forward-selector", Select)
        details = app.query_one("#merge-selected-output-details")
        assert not app.query("#show-previous-output")
        assert not app.query("#membank-reads")
        assert not app.query("#membank-writes")
        assert not app.query("#field-timeout_seconds")
        assert not app.query("#merge-output-name")
        assert not app.query("#merge-output-description")
        assert set(branch_selector.selected) == {f"{branch}:path_a", f"{branch}:path_b"}
        assert carry_selector.value == f"{branch}:path_b"
        assert details.display is True
        assert options[1]["output_description"] == "Review output"

        branch_selector.deselect(f"{branch}:path_b")
        await pilot.pause()
        screen = app.query_one(NodeConfigScreen)
        assert carry_selector.value == f"{branch}:path_a"
        assert screen._merge_config_values() == {
            "branches_to_close": [f"{branch}:path_a"],
            "carry_forward_branch_id": f"{branch}:path_a",
            "selected_branch_id": f"{branch}:path_a",
            "selected_input_port": "path_a",
        }
        app.set_focus(carry_selector)
        screen.action_activate_focused()
        await pilot.pause()
        assert carry_selector.expanded is True

    print("test_merge_config_uses_multi_branch_selector_and_carry_forward_dropdown PASSED")


def test_merge_config_does_not_autocheck_open_branches():
    asyncio.run(_test_merge_config_does_not_autocheck_open_branches())


async def _test_merge_config_does_not_autocheck_open_branches():
    from textual.app import App, ComposeResult
    from textual.widgets import Select, SelectionList

    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("merge_no_autocheck")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    left = wm.add_node("logger_node")
    right = wm.add_node("logger_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", left, "input")
    wm.connect(branch, "path_b", right, "input")
    node_data = wm.get_node_data(merge)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, merge, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        branch_selector = app.query_one("#merge-branches-to-close", SelectionList)
        carry_selector = app.query_one("#merge-carry-forward-selector", Select)
        assert list(branch_selector.selected) == []
        assert carry_selector.disabled is True

    print("test_merge_config_does_not_autocheck_open_branches PASSED")


def test_merge_options_exclude_current_merge_path_and_branch_end_card_turns_green():
    asyncio.run(_test_merge_options_exclude_current_merge_path_and_branch_end_card_turns_green())


async def _test_merge_options_exclude_current_merge_path_and_branch_end_card_turns_green():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import merge_input_options
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("merge_filter_branch_end")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    branch_end = wm.add_node("branch_end_node")
    sibling = wm.add_node("logger_node")
    merge = wm.add_node("merge_node")
    wm.update_node_config(
        branch,
        {"path_a_label": "Current Merge Path", "path_b_label": "Needs Merge"},
    )
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", branch_end, "input")
    wm.connect(branch_end, "default", merge, "path_a")
    wm.connect(branch, "path_b", sibling, "input")

    options = merge_input_options(wm, merge)
    values = {f"{option['branch_id']}:{option['branch_port']}" for option in options}
    assert values == {f"{branch}:path_b"}

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        cards = [card for card in app.query(NodeCard) if card.node_id == branch_end]
        assert len(cards) == 1
        assert cards[0].has_class("branch-end-connected")
        assert not cards[0].has_class("branch-end-open")

    print("test_merge_options_exclude_current_merge_path_and_branch_end_card_turns_green PASSED")


def test_merge_branch_selector_moves_focus_down_at_bottom():
    asyncio.run(_test_merge_branch_selector_moves_focus_down_at_bottom())


async def _test_merge_branch_selector_moves_focus_down_at_bottom():
    from textual.app import App, ComposeResult
    from textual.widgets import Select, SelectionList

    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("merge_selector_exit")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    left = wm.add_node("logger_node")
    right = wm.add_node("logger_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", left, "input")
    wm.connect(branch, "path_b", right, "input")
    wm.update_node_config(
        merge,
        {
            "branches_to_close": [f"{branch}:path_a"],
            "carry_forward_branch_id": f"{branch}:path_a",
        },
    )
    node_data = wm.get_node_data(merge)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, merge, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(NodeConfigScreen)
        branch_selector = app.query_one("#merge-branches-to-close", SelectionList)
        carry_selector = app.query_one("#merge-carry-forward-selector", Select)
        app.set_focus(branch_selector)
        branch_selector.highlighted = len(branch_selector._options) - 1
        screen.action_cursor_down()
        assert app.focused is carry_selector

    print("test_merge_branch_selector_moves_focus_down_at_bottom PASSED")


def test_node_config_select_activates_from_keyboard():
    asyncio.run(_test_node_config_select_activates_from_keyboard())


async def _test_node_config_select_activates_from_keyboard():
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Select

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_navigation import select_overlay

    _, wm, _, _ = _make_services()
    wm.create_new("branch_select_keyboard")
    branch = wm.add_node("branch_node")
    node_data = wm.get_node_data(branch)
    node_data["config"]["condition"] = "string_match"

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, branch, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        condition = app.query_one("#field-condition", Select)
        screen = app.query_one(NodeConfigScreen)
        assert getattr(app.focused, "id", None) == "alias-input"
        await pilot.press("s")
        assert getattr(app.focused, "id", None) == "show-previous-output"
        await pilot.press("s")
        assert getattr(app.focused, "id", None) == "membank-reads"
        await pilot.press("s")
        assert app.focused is condition
        await pilot.press("e")
        await pilot.pause()
        assert condition.expanded is True
        overlay = select_overlay(condition)
        assert overlay.highlighted == 0
        await pilot.press("s")
        assert overlay.highlighted == 1
        await pilot.press("w")
        assert overlay.highlighted == 0
        await pilot.press("down")
        assert overlay.highlighted == 1
        await pilot.press("up")
        assert overlay.highlighted == 0
        screen.action_cancel()
        await pilot.pause()
        assert condition.expanded is False
        assert app.focused is condition
        await pilot.press("e")
        await pilot.pause()
        assert condition.expanded is True
        overlay = select_overlay(condition)
        assert overlay.highlighted == 0
        await pilot.press("down")
        assert overlay.highlighted == 1
        await pilot.press("down")
        assert overlay.highlighted == 2
        await pilot.press("e")
        await pilot.pause()
        assert condition.value == "path_a_only"

        save_button = app.query_one("#save-node-config", Button)
        saved_results = []
        screen.dismiss = saved_results.append
        for _ in range(20):
            if app.focused is save_button:
                break
            await pilot.press("s")
        assert app.focused is save_button
        await pilot.press("e")
        await pilot.pause()
        assert saved_results
        assert saved_results[-1]["config"]["condition"] == "path_a_only"

    print("test_node_config_select_activates_from_keyboard PASSED")


def test_node_config_dynamic_membank_output_rows():
    asyncio.run(_test_node_config_dynamic_membank_output_rows())


def test_node_config_pass_through_disables_membank_outputs():
    asyncio.run(_test_node_config_pass_through_disables_membank_outputs())


async def _test_node_config_pass_through_disables_membank_outputs():
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox

    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("pass_through_outputs")
    node_id = wm.add_node("set_variable_node")
    node_data = wm.get_node_data(node_id)
    node_data["config"].update(
        {
            "pass_through": True,
            "membank_outputs": [{"id": "stale_output", "description": "Stale"}],
        }
    )

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node_id, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        pass_through = app.query_one("#field-pass_through", Checkbox)
        writes = app.query_one("#membank-writes", Checkbox)
        screen = app.query_one(NodeConfigScreen)
        assert pass_through.value is True
        assert writes.disabled is True
        assert screen._membank_config_values()["membank_outputs"] == []

    print("test_node_config_pass_through_disables_membank_outputs PASSED")


def test_dynamic_row_helper_preserves_visible_rows_only():
    from frontend.widgets.dynamic_sections import (
        clamp_dynamic_row_count,
        preserved_dynamic_rows,
    )

    mounted_rows = {0: {"id": "edited", "description": "Edited"}}

    def read_existing(index: int):
        return mounted_rows.get(index)

    rows = preserved_dynamic_rows(
        3,
        5,
        read_existing,
        [{"id": "initial-1"}, {"id": "initial-2"}],
        {"id": "", "description": ""},
    )

    assert rows == [
        {"id": "edited", "description": "Edited"},
        {"id": "initial-2"},
        {"id": "", "description": ""},
    ]
    assert preserved_dynamic_rows(1, 5, read_existing, [{"id": "hidden"}]) == [
        {"id": "edited", "description": "Edited"}
    ]
    assert clamp_dynamic_row_count("99", 5) == 5
    assert clamp_dynamic_row_count("bad", 5) == 0
    print("test_dynamic_row_helper_preserves_visible_rows_only PASSED")


def test_dynamic_selection_helper_filters_stale_values():
    from frontend.widgets.dynamic_sections import (
        dynamic_selection_rows,
        selected_values_from_widget,
    )

    options = [("Alpha", "a"), ("Beta", "b")]
    rows = dynamic_selection_rows(options, ["b", "missing"])

    assert rows == [("Alpha", "a", False), ("Beta", "b", True)]
    assert dynamic_selection_rows(
        options,
        [],
        select_all_when_empty=True,
    ) == [("Alpha", "a", True), ("Beta", "b", True)]

    class FakeSelectionList:
        selected = ["a", "b"]

    assert selected_values_from_widget(FakeSelectionList()) == {"a", "b"}
    print("test_dynamic_selection_helper_filters_stale_values PASSED")


def test_frontend_notification_helpers_standardize_copy_and_severity():
    from frontend import notifications

    class FakeApp:
        def __init__(self) -> None:
            self.calls = []

        def notify(self, message, **kwargs):
            self.calls.append((message, kwargs))

    app = FakeApp()
    notifications.workflow_saved(app)
    notifications.workflow_start_failed(app)
    notifications.missing_service(app, "Export")
    notifications.workflow_exported(app, "/tmp/workflow.json", True)
    notifications.workflow_deleted(app, False)
    notifications.cannot_delete_start_node(app)
    notifications.node_added(app, inserted=True)
    notifications.no_run_errors(app)

    assert app.calls == [
        ("Workflow saved", {}),
        ("Workflow did not start", {"severity": "error"}),
        ("Export requires SaveManager", {"severity": "error"}),
        ("Exported workflow to /tmp/workflow.json", {}),
        ("Workflow was not found", {}),
        ("Cannot delete the Start node", {"severity": "error"}),
        ("Node inserted", {}),
        ("No errors for this run", {}),
    ]
    print("test_frontend_notification_helpers_standardize_copy_and_severity PASSED")


def test_frontend_notifications_are_routed_through_helper():
    from pathlib import Path

    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    direct_calls = []
    for source_path in frontend_dir.rglob("*.py"):
        if source_path.name == "notifications.py":
            continue
        source = source_path.read_text(encoding="utf-8")
        if ".notify(" in source:
            direct_calls.append(source_path.relative_to(frontend_dir).as_posix())

    assert direct_calls == []
    print("test_frontend_notifications_are_routed_through_helper PASSED")


async def _test_node_config_dynamic_membank_output_rows():
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox, Input, TextArea

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput, CommandTextArea

    _, wm, _, _ = _make_services()
    wm.create_new("dynamic_membank_outputs")
    node_id = wm.add_node("logger_node")
    node_data = wm.get_node_data(node_id)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node_id, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        screen = app.query_one(NodeConfigScreen)
        writes = app.query_one("#membank-writes", Checkbox)
        count = app.query_one("#membank-output-count", CommandInput)

        assert count.disabled is True
        assert count.has_class("compact-number-field")
        assert not app.query("#membank-output-id-0")

        writes.value = True
        await screen._refresh_membank_output_rows()
        await pilot.pause()
        assert count.disabled is False
        assert count.value == "1"
        app.set_focus(count)
        screen.action_activate_focused()
        assert count.editing is True
        for key in ("up", "down", "left", "right"):
            await pilot.press(key)
            assert app.focused is count
            assert count.editing is True
        await pilot.press("escape")
        assert app.focused is count
        assert count.editing is False
        await pilot.press("s")
        assert app.focused is not count

        first_output = app.query_one("#membank-output-id-0", TextArea)
        assert first_output
        assert first_output.has_class("membank-output-field")
        assert first_output.parent and first_output.parent.id == "membank-output-rows"
        assert str(first_output.styles.height) == "6"
        first_desc = app.query_one("#membank-output-desc-0", Input)
        assert first_desc.has_class("membank-output-description-field")
        assert str(first_desc.styles.height) == "3"
        output_textarea = app.query_one("#membank-output-id-0", CommandTextArea)
        app.set_focus(output_textarea)
        screen.action_activate_focused()
        scroll = app.query_one("#node-config-scroll")
        before_scroll_y = scroll.scroll_y
        assert output_textarea.editing is True
        for key in ("up", "down", "left", "right"):
            await pilot.press(key)
            assert app.focused is output_textarea
            assert output_textarea.editing is True
            assert scroll.scroll_y == before_scroll_y

        app.query_one("#membank-output-id-0", TextArea).text = "first"
        app.query_one("#membank-output-desc-0", Input).value = "First output"
        count.value = "3"
        await screen._refresh_membank_output_rows()
        await pilot.pause()

        output_id_inputs = [
            widget for widget in app.query(TextArea) if str(widget.id or "").startswith("membank-output-id-")
        ]
        assert len(output_id_inputs) == 3
        assert all(widget.has_class("membank-output-field") for widget in output_id_inputs)
        assert app.query_one("#membank-output-id-0", TextArea).text == "first"
        assert app.query_one("#membank-output-desc-0", Input).value == "First output"
        saved_values = screen._membank_config_values()["membank_outputs"]
        assert saved_values[0]["id"] == "first"
        assert saved_values[0]["output"] == "first"
        assert saved_values[0]["description"] == "First output"

        count.value = "2"
        await screen._refresh_membank_output_rows()
        await pilot.pause()
        output_id_inputs = [
            widget for widget in app.query(TextArea) if str(widget.id or "").startswith("membank-output-id-")
        ]
        assert len(output_id_inputs) == 2
        saved_values = screen._membank_config_values()["membank_outputs"]
        assert len(saved_values) == 1
        assert saved_values[0]["id"] == "first"

    print("test_node_config_dynamic_membank_output_rows PASSED")


def test_editor_hides_empty_start_until_first_node_added():
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("hidden_empty_start")
    start = wm.add_node("start_node")
    screen = EditorScreen(wm._factory, wm)

    assert screen._build_visible_rows() == []
    assert screen._source_for_new_node() == {"node_id": start, "port": "default"}
    assert screen._source_for_insert_node() == {"node_id": start, "port": "default"}

    first = wm.add_node("logger_node")
    wm.connect(start, "default", first, "input")
    rows = screen._build_visible_rows()

    assert [row["node_id"] for row in rows if row["kind"] == "node"] == [start, first]
    print("test_editor_hides_empty_start_until_first_node_added PASSED")


def test_node_config_previous_output_preview_reads_transient_source():
    from frontend.screens.node_config import NodeConfigScreen

    _, wm, mb, _ = _make_services()
    wm.create_new("previous_output_preview")
    source = wm.add_node("logger_node")
    target = wm.add_node("logger_node")
    wm.connect(source, "default", target, "input")
    mb.store_transient(source, "default", {"message": "hello"})

    screen = NodeConfigScreen(
        wm._factory,
        wm,
        target,
        wm.get_node_data(target),
        memory_bank=mb,
    )
    text = screen._previous_output_text()

    assert "Source:" in text
    assert source in text
    assert "hello" in text
    print("test_node_config_previous_output_preview_reads_transient_source PASSED")


def test_node_selector_filter_auto_edits_when_focused():
    asyncio.run(_test_node_selector_filter_auto_edits_when_focused())


async def _test_node_selector_filter_auto_edits_when_focused():
    from textual.app import App, ComposeResult
    from textual.widgets import ListView

    from frontend.screens.node_selector import NodeSelectorScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()

    class SelectorApp(App):
        def compose(self) -> ComposeResult:
            yield NodeSelectorScreen(wm._factory)

    app = SelectorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(NodeSelectorScreen)
        node_list = app.query_one("#node-type-list", ListView)
        filter_input = app.query_one("#node-filter", CommandInput)

        screen._focus_node_list()
        assert app.focused is node_list
        assert node_list.index == 0

        screen.action_cursor_up()
        assert app.focused is filter_input
        assert filter_input.editing is True
        assert filter_input.value == ""

        await pilot.press("s")
        assert filter_input.value == "s"
        await pilot.press("escape")
        assert filter_input.editing is False
        await pilot.press("tab")
        assert app.focused is node_list
        assert node_list.index == 0
        screen.action_focus_filter()
        assert app.focused is filter_input
        assert filter_input.editing is True
        await pilot.press("escape")
        screen.action_cursor_down()
        assert app.focused is node_list
        assert node_list.index == 0

    print("test_node_selector_filter_auto_edits_when_focused PASSED")


def test_branch_selector_uses_shared_list_navigation():
    asyncio.run(_test_branch_selector_uses_shared_list_navigation())


async def _test_branch_selector_uses_shared_list_navigation():
    from textual.app import App, ComposeResult
    from textual.widgets import ListView

    from frontend.screens.branch_selector import BranchSelectorScreen

    class BranchApp(App):
        def compose(self) -> ComposeResult:
            yield BranchSelectorScreen(
                "branch-1",
                "Branch",
                ["path_a", "path_b", "path_c"],
                "path_b",
                {
                    "path_a": "North",
                    "path_b": "Middle",
                    "path_c": "South",
                },
            )

    app = BranchApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(BranchSelectorScreen)
        branch_list = app.query_one("#branch-port-list", ListView)

        assert app.focused is branch_list
        assert branch_list.index == 1

        screen.action_cursor_up()
        assert app.focused is branch_list
        assert branch_list.index == 0

        screen.action_cursor_up()
        assert branch_list.index == 0

        screen.action_cursor_down()
        assert branch_list.index == 1

    print("test_branch_selector_uses_shared_list_navigation PASSED")


def test_workflow_library_uses_shared_list_navigation():
    asyncio.run(_test_workflow_library_uses_shared_list_navigation())


async def _test_workflow_library_uses_shared_list_navigation():
    from textual.app import App, ComposeResult
    from textual.widgets import ListView

    import frontend.screens.workflow_library as workflow_library_module
    from frontend.screens.workflow_library import WorkflowLibraryScreen

    original_list_workflows = workflow_library_module.list_workflows
    workflow_library_module.list_workflows = lambda: [
        {"id": "wf-1", "name": "First"},
        {"id": "wf-2", "name": "Second"},
    ]

    class LibraryApp(App):
        def compose(self) -> ComposeResult:
            yield WorkflowLibraryScreen()

    try:
        app = LibraryApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            screen = app.query_one(WorkflowLibraryScreen)
            workflow_list = app.query_one("#workflow-list", ListView)

            assert app.focused is workflow_list
            assert workflow_list.index == 0

            screen.action_cursor_down()
            assert workflow_list.index == 1
            screen.action_cursor_down()
            assert workflow_list.index == 1
            screen.action_cursor_up()
            assert workflow_list.index == 0
    finally:
        workflow_library_module.list_workflows = original_list_workflows

    print("test_workflow_library_uses_shared_list_navigation PASSED")


def test_memory_viewer_uses_command_navigation():
    asyncio.run(_test_memory_viewer_uses_command_navigation())


async def _test_memory_viewer_uses_command_navigation():
    from textual.app import App, ComposeResult
    from textual.widgets import Button, DataTable

    from backend.event_bus import EventBus
    from backend.memory_bank import MemoryBank
    from frontend.screens.memory_viewer import MemoryViewerScreen

    memory_bank = MemoryBank(EventBus())
    for index in range(8):
        memory_bank.store_persistent(f"key_{index}", f"value_{index}")

    class MemoryApp(App):
        def compose(self) -> ComposeResult:
            yield MemoryViewerScreen(memory_bank)

    app = MemoryApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        table = app.query_one("#memory-table", DataTable)
        close_button = app.query_one("#close-memory", Button)
        assert app.focused is table
        start_row = table.cursor_row
        await pilot.press("s")
        assert table.cursor_row >= start_row

        closed = []
        screen = app.query_one(MemoryViewerScreen)
        screen.dismiss = closed.append
        app.set_focus(close_button)
        await pilot.press("e")
        await pilot.pause()
        assert closed == [None]

    print("test_memory_viewer_uses_command_navigation PASSED")


def test_command_input_auto_edit_on_focus_is_opt_in():
    asyncio.run(_test_command_input_auto_edit_on_focus_is_opt_in())


async def _test_command_input_auto_edit_on_focus_is_opt_in():
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Vertical
    from textual.screen import ModalScreen
    from textual.widgets import Button

    from frontend.widgets.command_input import CommandInput
    from frontend.widgets.command_navigation import move_command_focus

    class AutoEditScreen(ModalScreen):
        BINDINGS = [
            Binding("s", "cursor_down", "Down", priority=True),
        ]

        def compose(self) -> ComposeResult:
            with Vertical():
                yield CommandInput(id="manual-input")
                yield CommandInput(id="auto-input", auto_edit_on_focus=True)
                yield Button("Done", id="done-button")

        def on_mount(self) -> None:
            self.app.set_focus(self.query_one("#manual-input", CommandInput))

        def action_cursor_down(self) -> None:
            move_command_focus(self, 1, self._keyboard_focus_widgets())

        def _keyboard_focus_widgets(self):
            return [
                self.query_one("#manual-input", CommandInput),
                self.query_one("#auto-input", CommandInput),
                self.query_one("#done-button", Button),
            ]

    class AutoEditApp(App):
        def compose(self) -> ComposeResult:
            yield AutoEditScreen()

    app = AutoEditApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        manual_input = app.query_one("#manual-input", CommandInput)
        auto_input = app.query_one("#auto-input", CommandInput)
        done_button = app.query_one("#done-button", Button)

        assert app.focused is manual_input
        assert manual_input.editing is False
        assert auto_input.editing is False

        await pilot.press("s")
        assert app.focused is auto_input
        assert auto_input.editing is True
        await pilot.press("x")
        assert auto_input.value == "x"
        await pilot.press("escape")
        assert app.focused is auto_input
        assert auto_input.editing is False
        await pilot.press("s")
        assert app.focused is done_button

    print("test_command_input_auto_edit_on_focus_is_opt_in PASSED")


def test_node_config_command_inputs_require_activation():
    asyncio.run(_test_node_config_command_inputs_require_activation())


async def _test_node_config_command_inputs_require_activation():
    from textual import events
    from textual.app import App, ComposeResult

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()
    wm.create_new("command_input_config")
    node_id = wm.add_node("logger_node")
    node_data = wm.get_node_data(node_id)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node_id, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(NodeConfigScreen)
        alias = app.query_one("#alias-input", CommandInput)
        app.set_focus(alias)
        assert app.focused is alias
        assert alias.editing is False

        screen.action_cursor_down()
        assert alias.value == node_data.get("alias", "")
        assert app.focused is not alias

        screen.action_cursor_up()
        assert app.focused is alias
        assert alias.editing is False

        screen.action_activate_focused()
        assert alias.editing is True
        await pilot.press("x")
        assert alias.value.endswith("x")
        await pilot.press("w", "s")
        assert app.focused is alias
        assert alias.editing is True
        assert alias.value.endswith("xws")
        for key in ("up", "down", "left", "right"):
            await pilot.press(key)
            assert app.focused is alias
            assert alias.editing is True
        await pilot.press("escape")
        assert alias.editing is False
        assert app.focused is alias
        assert alias.value == node_data.get("alias", "")
        screen.action_activate_focused()
        await pilot.press("y")
        await pilot.press("enter")
        assert alias.editing is False
        assert alias.value != node_data.get("alias", "")
        assert "y" in alias.value
        await pilot.press("s")
        assert not alias.value.endswith("xs")
        assert app.focused is not alias

    print("test_node_config_command_inputs_require_activation PASSED")


def test_simple_command_modals_use_shared_navigation_helpers():
    asyncio.run(_test_simple_command_modals_use_shared_navigation_helpers())


async def _test_simple_command_modals_use_shared_navigation_helpers():
    from textual import events
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox

    from backend.configuration_manager import DEFAULT_SETTINGS
    from frontend.screens.settings import SettingsScreen
    from frontend.widgets.command_input import CommandInput

    class FakeConfigurationManager:
        def get_all(self):
            return dict(DEFAULT_SETTINGS)

    class SettingsApp(App):
        def compose(self) -> ComposeResult:
            yield SettingsScreen(FakeConfigurationManager())

    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(SettingsScreen)
        max_depth = app.query_one("#setting-max_branch_depth", CommandInput)
        timeout = app.query_one("#setting-node_timeout_seconds", CommandInput)
        auto_save = app.query_one("#setting-auto_save_enabled", Checkbox)

        assert app.focused is max_depth
        assert max_depth.editing is False

        screen.action_activate_focused()
        assert max_depth.editing is True
        assert screen.check_action("cancel", ()) is False

        await max_depth._on_key(events.Key("escape", None))
        assert max_depth.editing is False
        screen.action_cursor_down()
        assert app.focused is timeout
        screen.action_cursor_down()
        assert app.focused is auto_save

        previous = auto_save.value
        screen.action_activate_focused()
        assert auto_save.value is (not previous)

    print("test_simple_command_modals_use_shared_navigation_helpers PASSED")


def test_prompt_modals_use_shared_command_activation():
    asyncio.run(_test_prompt_modals_use_shared_command_activation())


async def _test_prompt_modals_use_shared_command_activation():
    from textual import events
    from textual.app import App, ComposeResult

    from frontend.screens.user_input import UserInputScreen
    from frontend.screens.workflow_library import PathPromptScreen
    from frontend.widgets.command_input import CommandInput

    class PathApp(App):
        def compose(self) -> ComposeResult:
            yield PathPromptScreen("Export", "/tmp/workflow.json")

    path_app = PathApp()
    async with path_app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = path_app.query_one(PathPromptScreen)
        path_input = path_app.query_one("#path-input", CommandInput)
        assert path_app.focused is path_input
        assert path_input.editing is True
        path_input.value = ""
        await pilot.press("a", "b", "c")
        assert path_input.value == "abc"
        assert screen.check_action("cancel", ()) is False
        submitted_paths = []
        screen.dismiss = submitted_paths.append
        await pilot.press("ctrl+enter")
        await pilot.pause()
        assert submitted_paths == ["abc"]
        await path_input._on_key(events.Key("escape", None))
        assert path_input.editing is False

    class UserInputApp(App):
        def compose(self) -> ComposeResult:
            yield UserInputScreen("branch-1", "node-1", "Enter value")

    user_app = UserInputApp()
    async with user_app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = user_app.query_one(UserInputScreen)
        user_input = user_app.query_one("#user-input-value", CommandInput)
        assert user_app.focused is user_input
        assert user_input.editing is True
        await pilot.press("o", "k")
        assert user_input.value == "ok"
        assert screen.check_action("cancel", ()) is False
        submitted_values = []
        screen.dismiss = submitted_values.append
        await pilot.press("ctrl+enter")
        await pilot.pause()
        assert submitted_values == [{"branch_id": "branch-1", "value": "ok"}]

    print("test_prompt_modals_use_shared_command_activation PASSED")


def test_editor_click_selects_and_double_click_edits():
    asyncio.run(_test_editor_click_selects_and_double_click_edits())


async def _test_editor_click_selects_and_double_click_edits():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("editor_clicks")
    start = wm.add_node("start_node")
    logger = wm.add_node("logger_node")
    wm.connect(start, "default", logger, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        opened = []
        screen.action_edit_selected = lambda: opened.append(screen.selected_node_id)

        screen.on_node_card_clicked(NodeCard.Clicked(logger, 1))
        assert screen.selected_node_id == logger
        assert opened == []

        screen.on_node_card_clicked(NodeCard.Clicked(logger, 2))
        assert screen.selected_node_id == logger
        assert opened == [logger]

    print("test_editor_click_selects_and_double_click_edits PASSED")


def test_command_text_click_enters_editing_mode():
    asyncio.run(_test_command_text_click_enters_editing_mode())


async def _test_command_text_click_enters_editing_mode():
    from textual import events
    from textual.app import App, ComposeResult

    from frontend.widgets.command_input import CommandInput, CommandTextArea

    def click(widget, chain: int) -> events.Click:
        return events.Click(
            widget,
            0,
            0,
            0,
            0,
            1,
            False,
            False,
            False,
            chain=chain,
        )

    class InputApp(App):
        def compose(self) -> ComposeResult:
            yield CommandInput(id="click-input")
            yield CommandTextArea(id="click-textarea")
            yield CommandInput(id="auto-click-input", auto_edit_on_focus=True)

    app = InputApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        text_input = app.query_one("#click-input", CommandInput)
        textarea = app.query_one("#click-textarea", CommandTextArea)
        auto_input = app.query_one("#auto-click-input", CommandInput)

        text_input.on_click(click(text_input, 1))
        assert app.focused is text_input
        assert text_input.editing is True

        textarea.on_click(click(textarea, 1))
        assert app.focused is textarea
        assert text_input.editing is False
        assert textarea.editing is True

        auto_input.on_click(click(auto_input, 1))
        assert app.focused is auto_input
        assert auto_input.editing is True

    print("test_command_text_click_enters_editing_mode PASSED")


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
        test_save_manager_writes_input_sources,
        test_validator_flags_missing_input_sources,
        test_validator_flags_missing_membank_input_sources,
        test_membank_registry_filters_downstream_writers,
        test_insert_between_rewires_below_source_node,
        test_tombstone_delete_does_not_cascade_branch_nodes,
        test_tombstone_restore_preserves_original_and_swap_invalidates_timing,
        test_set_variable_node_can_pass_input_through,
        test_branch_node_default_labels_are_configurable,
        test_branch_config_uses_generated_labels_without_memory_outputs,
        test_sleep_config_shows_pass_through_hint,
        test_form_generator_groups_schema_for_tabs,
        test_form_generator_mounts_tabbed_and_single_group_forms,
        test_form_generator_honors_generic_schema_hints,
        test_workflow_map_breakpoint_flags_are_persisted_in_node_data,
        test_breakpoint_pauses_before_node_execution_and_resumes,
        test_node_timings_are_recorded_for_run_history,
        test_wait_until_node_gates_cross_branch_completion,
        test_wait_target_options_exclude_downstream_nodes,
        test_merge_node_waits_and_forwards_selected_input,
        test_merge_config_uses_multi_branch_selector_and_carry_forward_dropdown,
        test_merge_config_does_not_autocheck_open_branches,
        test_merge_options_exclude_current_merge_path_and_branch_end_card_turns_green,
        test_merge_branch_selector_moves_focus_down_at_bottom,
        test_node_config_select_activates_from_keyboard,
        test_dynamic_row_helper_preserves_visible_rows_only,
        test_dynamic_selection_helper_filters_stale_values,
        test_frontend_notification_helpers_standardize_copy_and_severity,
        test_node_config_dynamic_membank_output_rows,
        test_node_config_pass_through_disables_membank_outputs,
        test_editor_hides_empty_start_until_first_node_added,
        test_node_config_previous_output_preview_reads_transient_source,
        test_node_selector_filter_auto_edits_when_focused,
        test_branch_selector_uses_shared_list_navigation,
        test_workflow_library_uses_shared_list_navigation,
        test_memory_viewer_uses_command_navigation,
        test_command_input_auto_edit_on_focus_is_opt_in,
        test_node_config_command_inputs_require_activation,
        test_simple_command_modals_use_shared_navigation_helpers,
        test_prompt_modals_use_shared_command_activation,
        test_editor_click_selects_and_double_click_edits,
        test_command_text_click_enters_editing_mode,
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

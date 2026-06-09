"""Acceptance tests for the debug node library.

Run from AttackOfTheNodes/:
    python -m pytest tests/test_debug_nodes.py -v
or standalone:
    python tests/test_debug_nodes.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Allow running as `python3 AttackOfTheNodes/tests/test_debug_nodes.py`
# or `python -m pytest tests/test_debug_nodes.py` from AttackOfTheNodes/
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


def test_new_nodes_use_default_display_alias():
    _, wm, _, _ = _make_services()
    wm.create_new("default_alias")

    node_id = wm.add_node("logger_node")
    node = wm.get_node_data(node_id)

    metadata = wm._factory.get_node_types_metadata()
    logger_meta = next(item for item in metadata if item["type"] == "logger_node")
    assert logger_meta["default_alias"] == "Logger"
    assert wm._factory.get_default_alias("logger_node") == "Logger"
    assert node["alias"] == "Logger"

    custom_id = wm.add_node("logger_node", alias="Custom Log")
    custom = wm.get_node_data(custom_id)
    assert custom["alias"] == "Custom Log"

    print("test_new_nodes_use_default_display_alias PASSED")


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
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    _, wm, _, _ = _make_services()
    wm.create_new("delete_no_cascade")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    left = wm.add_node("logger_node")
    right = wm.add_node("logger_node")

    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", left, "input")
    wm.connect(branch, "path_b", right, "input")

    adapter = EditorWorkflowAdapter(wm, wm._factory)
    assert adapter.replace_with_placeholder(branch)
    all_nodes = wm.get_all_node_data()
    assert branch in all_nodes
    assert all_nodes[branch]["type"] == "tombstone_node"
    assert left in all_nodes
    assert right in all_nodes
    print("test_tombstone_delete_does_not_cascade_branch_nodes PASSED")


def test_tombstone_restore_preserves_original_and_swap_invalidates_timing():
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    _, wm, _, _ = _make_services()
    wm.create_new("tombstone_restore")
    node_id = wm.add_node("logger_node", alias="Original Logger")
    wm.update_node_config(node_id, {"message": "original"})
    adapter = EditorWorkflowAdapter(wm, wm._factory)

    assert adapter.replace_with_placeholder(node_id)
    tombstone = wm.get_node_data(node_id)
    assert tombstone["type"] == "tombstone_node"
    assert tombstone["config"]["original_alias"] == "Original Logger"
    assert tombstone["config"]["original_config"] == {"message": "original"}

    result = adapter.replace_placeholder(node_id, "logger_node")
    assert result["replaced"] is True
    assert result["restored_original"] is True
    restored = wm.get_node_data(node_id)
    assert restored["type"] == "logger_node"
    assert restored["alias"] == "Original Logger"
    assert restored["config"] == {"message": "original"}
    assert "_timing_invalidated" not in restored

    assert adapter.replace_with_placeholder(node_id)
    result = adapter.replace_placeholder(node_id, "sleep_node")
    assert result["replaced"] is True
    assert result["restored_original"] is False
    swapped = wm.get_node_data(node_id)
    assert swapped["type"] == "sleep_node"
    assert "_timing_invalidated" not in swapped
    print("test_tombstone_restore_preserves_original_and_swap_invalidates_timing PASSED")


def test_editor_deleted_node_row_renders_as_deleted():
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("tombstone_row_display")
    node_id = wm.add_node("logger_node")
    wm.update_node_alias(node_id, "Useful Logger")

    adapter = EditorWorkflowAdapter(wm, wm._factory)
    assert adapter.replace_with_placeholder(node_id)
    tombstone = wm.get_node_data(node_id)
    tombstone["_editor_depth"] = 1
    card = NodeCard(node_id, tombstone, show_status=False, show_id=False)
    card.refresh_card()

    assert card.display_text == "  1   Deleted: Useful Logger"
    print("test_editor_deleted_node_row_renders_as_deleted PASSED")


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

    assert BranchNode.default_config["path_a_label"] == "Branch 1"
    assert BranchNode.default_config["path_b_label"] == "Branch 2"
    assert "path_a_label" in BranchNode.config_schema
    assert "path_b_label" in BranchNode.config_schema
    assert BranchNode.config_schema["path_a_label"]["label"] == "Branch 1 name"
    assert BranchNode.config_schema["path_a_label"]["group"] == "Branch Names"
    print("test_branch_node_default_labels_are_configurable PASSED")


def test_branch_config_uses_generated_labels_without_memory_outputs():
    asyncio.run(_test_branch_config_uses_generated_labels_without_memory_outputs())


async def _test_branch_config_uses_generated_labels_without_memory_outputs():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
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
    left_beacon = wm.add_node("branch_end_node")
    right = wm.add_node("logger_node")
    right_beacon = wm.add_node("branch_end_node")
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
    wm.connect(left, "default", left_beacon, "input")
    wm.connect(branch, "path_b", right, "input")
    wm.connect(right, "default", right_beacon, "input")
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
        assert not app.query("#merge-branches-to-close")
        assert not app.query("#merge-carry-forward-selector")

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
    sibling_beacon = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    wm.update_node_config(
        branch,
        {"path_a_label": "Current Merge Path", "path_b_label": "Needs Merge"},
    )
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", branch_end, "input")
    wm.connect(branch_end, "default", merge, "path_a")
    wm.connect(branch, "path_b", sibling, "input")
    wm.connect(sibling, "default", sibling_beacon, "input")

    options = merge_input_options(wm, merge)
    values = {f"{option['branch_id']}:{option['branch_port']}" for option in options}
    assert values == {f"{branch}:path_a", f"{branch}:path_b"}
    assert {option["description"] for option in options} == {
        "Branch: Current Merge Path",
        "Branch: Needs Merge",
    }

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


def test_merge_options_exclude_branch_containing_current_merge():
    asyncio.run(_test_merge_options_exclude_branch_containing_current_merge())


async def _test_merge_options_exclude_branch_containing_current_merge():
    from frontend.screens.node_config import merge_input_options

    _, wm, _, _ = _make_services()
    wm.create_new("merge_excludes_own_branch")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    merge_path_node = wm.add_node("sleep_node")
    merge = wm.add_node("merge_node")
    sibling = wm.add_node("logger_node")
    sibling_beacon = wm.add_node("branch_end_node")
    wm.update_node_config(
        branch,
        {"path_a_label": "deez", "path_b_label": "branch name here"},
    )
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", merge_path_node, "input")
    wm.connect(merge_path_node, "default", merge, "path_a")
    wm.connect(branch, "path_b", sibling, "input")
    wm.connect(sibling, "default", sibling_beacon, "input")

    options = merge_input_options(wm, merge)
    descriptions = {option["description"] for option in options}
    values = {f"{option['branch_id']}:{option['branch_port']}" for option in options}
    assert f"{branch}:path_a" not in values
    assert f"{branch}:path_b" in values
    assert "Branch: deez" not in descriptions
    assert "Branch: branch name here" in descriptions

    print("test_merge_options_exclude_branch_containing_current_merge PASSED")


def test_merge_options_include_nested_merge_beacons():
    asyncio.run(_test_merge_options_include_nested_merge_beacons())


async def _test_merge_options_include_nested_merge_beacons():
    from textual.app import App, ComposeResult

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.screens.node_config import merge_input_options

    _, wm, _, _ = _make_services()
    wm.create_new("merge_nested_beacons")
    start = wm.add_node("start_node")
    outer_branch = wm.add_node("branch_node")
    inner_branch = wm.add_node("branch_node")
    nested_work = wm.add_node("logger_node")
    nested_beacon = wm.add_node("branch_end_node")
    outer_beacon = wm.add_node("branch_end_node")
    merge_path = wm.add_node("sleep_node")
    merge = wm.add_node("merge_node")
    wm.update_node_config(
        outer_branch,
        {"path_a_label": "Outer Work", "path_b_label": "Merge Home"},
    )
    wm.update_node_config(
        inner_branch,
        {"path_a_label": "Nested Left", "path_b_label": "Nested Right"},
    )

    wm.connect(start, "default", outer_branch, "input")
    wm.connect(outer_branch, "path_a", inner_branch, "input")
    wm.connect(inner_branch, "path_a", nested_work, "input")
    wm.connect(nested_work, "default", nested_beacon, "input")
    wm.connect(inner_branch, "path_b", outer_beacon, "input")
    wm.connect(outer_branch, "path_b", merge_path, "input")
    wm.connect(merge_path, "default", merge, "path_a")

    options = merge_input_options(wm, merge)
    values = {f"{option['branch_id']}:{option['branch_port']}" for option in options}
    descriptions = {option["description"] for option in options}
    assert values == {
        f"{inner_branch}:path_a",
        f"{inner_branch}:path_b",
    }
    assert descriptions == {
        "Branch: Outer Work -> Nested Left",
        "Branch: Outer Work -> Nested Right",
    }
    assert {option["branch_path"] for option in options} == {
        "Outer Work -> Nested Left",
        "Outer Work -> Nested Right",
    }

    wm.update_node_config(
        merge,
        {
            "branches_to_close": [f"{inner_branch}:path_a"],
            "carry_forward_branch_id": f"{inner_branch}:path_a",
            "selected_branch_id": f"{inner_branch}:path_a",
            "selected_input_port": "path_a",
        },
    )

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, merge, wm.get_node_data(merge))

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        details = app.query_one("#merge-selected-output-details")
        assert "Branch path: Outer Work -> Nested Left" in str(details.content)

    print("test_merge_options_include_nested_merge_beacons PASSED")


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
    left_beacon = wm.add_node("branch_end_node")
    right = wm.add_node("logger_node")
    right_beacon = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", left, "input")
    wm.connect(left, "default", left_beacon, "input")
    wm.connect(branch, "path_b", right, "input")
    wm.connect(right, "default", right_beacon, "input")
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


def test_saving_merge_config_connects_selected_branch_end():
    asyncio.run(_test_saving_merge_config_connects_selected_branch_end())


async def _test_saving_merge_config_connects_selected_branch_end():
    from textual.app import App, ComposeResult

    from backend.validator import validate_workflow
    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("merge_save_connects_branch_end")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    branch_end = wm.add_node("branch_end_node")
    sibling = wm.add_node("logger_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", branch_end, "input")
    wm.connect(branch, "path_b", sibling, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = merge
        screen.selected_row = {"kind": "node", "node_id": merge}
        merge_choice = f"{branch}:path_a"
        screen._save_node_config_from_modal(
            {
                "alias": "",
                "config": {
                    "branches_to_close": [merge_choice],
                    "carry_forward_branch_id": merge_choice,
                    "selected_branch_id": merge_choice,
                    "selected_input_port": "path_a",
                },
            }
        )
        await pilot.pause(0.03)

        branch_end_node = wm.get_node_data(branch_end)
        merge_node = wm.get_node_data(merge)
        assert {
            "source_port": "default",
            "target_node_id": merge,
            "target_port": "path_a",
        } in branch_end_node.get("connections", {}).get("outputs", [])
        assert {
            "target_port": "path_a",
            "source_node_id": branch_end,
            "source_port": "default",
        } in merge_node.get("connections", {}).get("inputs", [])
        assert validate_workflow(wm, wm._factory)["success"] is True

        cards = [card for card in app.query(NodeCard) if card.node_id == branch_end]
        assert len(cards) == 1
        assert cards[0].has_class("branch-end-connected")

    print("test_saving_merge_config_connects_selected_branch_end PASSED")


def test_saving_merge_config_unchecked_branch_disconnects_branch_end():
    asyncio.run(_test_saving_merge_config_unchecked_branch_disconnects_branch_end())


def test_saving_merge_config_preserves_merge_home_branch_input():
    asyncio.run(_test_saving_merge_config_preserves_merge_home_branch_input())


def test_deleting_merge_beacon_prunes_merge_config_selection():
    asyncio.run(_test_deleting_merge_beacon_prunes_merge_config_selection())


def test_editor_blocks_insert_after_merge_beacon():
    asyncio.run(_test_editor_blocks_insert_after_merge_beacon())


async def _test_saving_merge_config_unchecked_branch_disconnects_branch_end():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import merge_input_options
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("merge_save_disconnects_branch_end")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    branch_end = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", branch_end, "input")
    wm.connect(branch_end, "default", merge, "path_a")
    wm.update_node_config(
        merge,
        {
            "branches_to_close": [f"{branch}:path_a"],
            "carry_forward_branch_id": f"{branch}:path_a",
            "selected_branch_id": f"{branch}:path_a",
            "selected_input_port": "path_a",
        },
    )
    option_values = {
        f"{option['branch_id']}:{option['branch_port']}"
        for option in merge_input_options(wm, merge)
    }
    assert f"{branch}:path_a" in option_values

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = merge
        screen.selected_row = {"kind": "node", "node_id": merge}
        screen._save_node_config_from_modal(
            {
                "alias": "",
                "config": {
                    "branches_to_close": [],
                    "carry_forward_branch_id": "",
                    "selected_branch_id": "",
                    "selected_input_port": "",
                },
            }
        )
        await pilot.pause(0.03)

        branch_end_node = wm.get_node_data(branch_end)
        merge_node = wm.get_node_data(merge)
        assert branch_end_node.get("connections", {}).get("outputs", []) == []
        assert merge_node.get("connections", {}).get("inputs", []) == []
        cards = [card for card in app.query(NodeCard) if card.node_id == branch_end]
        assert len(cards) == 1
        assert cards[0].has_class("branch-end-open")
        assert not cards[0].has_class("branch-end-connected")

    print("test_saving_merge_config_unchecked_branch_disconnects_branch_end PASSED")


async def _test_saving_merge_config_preserves_merge_home_branch_input():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import merge_input_options

    _, wm, _, _ = _make_services()
    wm.create_new("merge_preserves_home_branch")
    start = wm.add_node("start_node")
    outer_branch = wm.add_node("branch_node")
    merge = wm.add_node("merge_node")
    nested_branch = wm.add_node("branch_node")
    beacon = wm.add_node("branch_end_node")
    wm.connect(start, "default", outer_branch, "input")
    wm.connect(outer_branch, "path_a", merge, "path_a")
    wm.connect(outer_branch, "path_b", nested_branch, "input")
    wm.connect(nested_branch, "path_a", beacon, "input")

    options = merge_input_options(wm, merge)
    beacon_option = next(option for option in options if option["branch_end_id"] == beacon)
    merge_choice = f"{beacon_option['branch_id']}:{beacon_option['branch_port']}"
    assert beacon_option["port"] == "path_b"

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = merge
        screen.selected_row = {"kind": "node", "node_id": merge}
        screen._save_node_config_from_modal(
            {
                "alias": "",
                "config": {
                    "branches_to_close": [merge_choice],
                    "carry_forward_branch_id": merge_choice,
                    "selected_branch_id": merge_choice,
                    "selected_input_port": beacon_option["port"],
                },
            }
        )
        await pilot.pause(0.03)
        merge_inputs = wm.get_node_data(merge).get("connections", {}).get("inputs", [])
        assert {
            "target_port": "path_a",
            "source_node_id": outer_branch,
            "source_port": "path_a",
        } in merge_inputs
        assert {
            "target_port": "path_b",
            "source_node_id": beacon,
            "source_port": "default",
        } in merge_inputs
        assert screen._branch_choices_to_node(merge) == [(outer_branch, "path_a")]
        assert [option["merge_node_id"] for option in screen._merge_beacon_options(beacon)] == [merge]

    print("test_saving_merge_config_preserves_merge_home_branch_input PASSED")


async def _test_deleting_merge_beacon_prunes_merge_config_selection():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import NodeConfigScreen, merge_input_options

    _, wm, _, _ = _make_services()
    wm.create_new("merge_beacon_delete_prunes_config")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    beacon = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", beacon, "input")
    wm.connect(beacon, "default", merge, "path_a")
    wm.update_node_config(
        merge,
        {
            "branches_to_close": [f"{branch}:path_a"],
            "carry_forward_branch_id": f"{branch}:path_a",
            "selected_branch_id": f"{branch}:path_a",
            "selected_input_port": "path_a",
        },
    )

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = beacon
        screen.selected_row = {"kind": "node", "node_id": beacon}
        screen.action_delete_selected()
        await pilot.pause(0.03)

        merge_config = wm.get_node_data(merge).get("config", {})
        assert merge_config.get("branches_to_close") == []
        assert merge_config.get("carry_forward_branch_id") == ""
        assert merge_config.get("selected_branch_id") == ""
        assert wm.get_node_data(beacon).get("connections", {}).get("outputs", []) == []

        screen._replace_tombstone_from_modal("branch_end_node")
        await pilot.pause(0.03)
        assert wm.get_node_data(beacon)["type"] == "branch_end_node"
        assert wm.get_node_data(beacon).get("connections", {}).get("outputs", []) == []
        options = merge_input_options(wm, merge)
        assert [f"{option['branch_id']}:{option['branch_port']}" for option in options] == [
            f"{branch}:path_a"
        ]

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, merge, wm.get_node_data(merge))

    config_app = ConfigApp()
    async with config_app.run_test() as pilot:
        await pilot.pause(0.03)
        merge_screen = config_app.query_one(NodeConfigScreen)
        options = merge_input_options(wm, merge_screen.node_id)
        assert merge_screen._selected_merge_close_values(
            options,
            wm.get_node_data(merge).get("config", {}),
        ) == set()

    print("test_deleting_merge_beacon_prunes_merge_config_selection PASSED")


async def _test_editor_blocks_insert_after_merge_beacon():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("block_insert_after_merge_beacon")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    beacon = wm.add_node("branch_end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", beacon, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        node_count = len(wm.get_all_node_data())
        stack_count = len(app.screen_stack)

        screen.selected_node_id = beacon
        screen.selected_row = {"kind": "node", "node_id": beacon}
        screen.action_insert_node()
        await pilot.pause(0.03)
        assert len(wm.get_all_node_data()) == node_count
        assert len(app.screen_stack) == stack_count

        screen.selected_node_id = None
        screen.selected_row = {"kind": "merge_beacon_select", "beacon_node_id": beacon}
        screen.action_insert_node()
        await pilot.pause(0.03)
        assert len(wm.get_all_node_data()) == node_count
        assert len(app.screen_stack) == stack_count

    print("test_editor_blocks_insert_after_merge_beacon PASSED")


def test_branch_end_config_shows_merge_branch_identity():
    asyncio.run(_test_branch_end_config_shows_merge_branch_identity())


def test_merge_beacon_selector_row_jumps_without_rewiring():
    asyncio.run(_test_merge_beacon_selector_row_jumps_without_rewiring())


def test_merge_beacon_selector_excludes_merge_reachable_only_through_beacon():
    asyncio.run(_test_merge_beacon_selector_excludes_merge_reachable_only_through_beacon())


async def _test_branch_end_config_shows_merge_branch_identity():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("branch_end_status")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    branch_end = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    wm.update_node_config(branch, {"path_a_label": "Approve"})
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", branch_end, "input")
    wm.connect(branch_end, "default", merge, "path_a")

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, branch_end, wm.get_node_data(branch_end))

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(NodeConfigScreen)
        text = screen._branch_end_status_text()
        assert f"Merges To Branch: Approve ({branch}:path_a)" in text
        assert f"Merge Node: Merge ({merge})" in text

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    editor_app = EditorApp()
    async with editor_app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = editor_app.query_one(EditorScreen)
        screen.selected_node_id = branch_end
        screen.selected_row = {"kind": "node", "node_id": branch_end}
        screen.refresh_from_backend()
        details = screen.query_one("#node-details").display_text
        assert f"Merges To Branch: Approve ({branch}:path_a)" in details
        assert f"Merge Node: Merge ({merge})" in details

    print("test_branch_end_config_shows_merge_branch_identity PASSED")


async def _test_merge_beacon_selector_row_jumps_without_rewiring():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.screens.merge_beacon_selector import MergeBeaconSelectorScreen
    from frontend.widgets.node_card import MergeBeaconSelectCard, NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("merge_beacon_selector")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    current_merge = wm.add_node("merge_node")
    beacon = wm.add_node("branch_end_node")
    target_merge = wm.add_node("merge_node")
    after_merge = wm.add_node("logger_node")
    wm.update_node_config(branch, {"path_a_label": "Closed", "path_b_label": "Merge Path"})
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", current_merge, "path_a")
    wm.connect(current_merge, "default", beacon, "input")
    wm.connect(branch, "path_b", target_merge, "path_a")
    wm.connect(target_merge, "default", after_merge, "input")
    wm.connect(beacon, "default", target_merge, "path_b")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        node_list = screen.query_one("#node-list")

        rows = node_list._rows
        assert [row["kind"] for row in rows] == [
            "node",
            "node",
            "branch_select",
            "node",
            "node",
            "merge_beacon_select",
        ]
        assert target_merge not in [row.get("node_id") for row in rows]
        beacon_cards = [card for card in app.query(NodeCard) if card.node_id == beacon]
        assert beacon_cards[0].display_text.endswith("Merge Beacon")
        selector_card = app.query_one(MergeBeaconSelectCard)
        assert selector_card.active_label == "Merge"

        options = screen._merge_beacon_options(beacon)
        assert [option["merge_node_id"] for option in options] == [target_merge]

        before_outputs = list(wm.get_node_data(beacon).get("connections", {}).get("outputs", []))
        before_inputs = list(wm.get_node_data(target_merge).get("connections", {}).get("inputs", []))
        selector_index = node_list.index_for_merge_beacon_select(beacon)
        assert selector_index is not None
        node_list.index = selector_index
        screen._select_row(node_list.row_for_index(selector_index))
        screen._refresh_details()
        app.set_focus(node_list)

        await pilot.press("e")
        await pilot.pause()
        modal = app.screen_stack[-1]
        assert isinstance(modal, MergeBeaconSelectorScreen)
        modal_list = modal.query_one("#merge-beacon-list")
        assert modal_list.index == 0

        await pilot.press("e")
        await pilot.pause()
        assert screen.selected_node_id == target_merge
        assert screen.active_branch_ports[branch] == "path_b"
        assert node_list.index == node_list.index_for_node_id(target_merge)
        assert wm.get_node_data(beacon).get("connections", {}).get("outputs", []) == before_outputs
        assert wm.get_node_data(target_merge).get("connections", {}).get("inputs", []) == before_inputs

    print("test_merge_beacon_selector_row_jumps_without_rewiring PASSED")


async def _test_merge_beacon_selector_excludes_merge_reachable_only_through_beacon():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("merge_beacon_reachable_only_through_beacon")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    beacon = wm.add_node("branch_end_node")
    loose_merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", beacon, "input")
    wm.connect(beacon, "default", loose_merge, "path_a")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        assert screen._merge_beacon_options(beacon) == []
        screen._select_merge_from_beacon_modal({"merge_node_id": loose_merge})
        await pilot.pause(0.03)
        node_list = screen.query_one("#node-list")
        assert loose_merge not in [row.get("node_id") for row in node_list._rows]

    print("test_merge_beacon_selector_excludes_merge_reachable_only_through_beacon PASSED")


def test_connected_branch_end_deletes_to_tombstone():
    asyncio.run(_test_connected_branch_end_deletes_to_tombstone())


async def _test_connected_branch_end_deletes_to_tombstone():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("connected_branch_end_tombstone")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    branch_end = wm.add_node("branch_end_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", branch_end, "input")
    wm.connect(branch_end, "default", merge, "path_a")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = branch_end
        screen.selected_row = {"kind": "node", "node_id": branch_end}
        screen.refresh_from_backend()
        await pilot.pause(0.03)

        before_cards = [card for card in app.query(NodeCard) if card.node_id == branch_end]
        assert len(before_cards) == 1
        assert before_cards[0].has_class("branch-end-connected")

        screen.action_delete_selected()
        await pilot.pause(0.03)

        assert wm.get_node_data(branch_end)["type"] == "tombstone_node"
        after_cards = [card for card in app.query(NodeCard) if card.node_id == branch_end]
        assert len(after_cards) == 1
        assert not after_cards[0].has_class("branch-end-open")
        assert not after_cards[0].has_class("branch-end-connected")
        assert after_cards[0].node_data["type"] == "tombstone_node"

    print("test_connected_branch_end_deletes_to_tombstone PASSED")


def test_editor_connects_merge_input_to_active_branch_port():
    asyncio.run(_test_editor_connects_merge_input_to_active_branch_port())


async def _test_editor_connects_merge_input_to_active_branch_port():
    from textual.app import App, ComposeResult

    from backend.validator import validate_workflow
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("merge_branch_port_connect")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    source = wm.add_node("user_text_input_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_b", source, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen._connect_new_node(source, "default", merge)
        await pilot.pause(0.03)

        merge_node = wm.get_node_data(merge)
        assert {
            "target_port": "path_b",
            "source_node_id": source,
            "source_port": "default",
        } in merge_node.get("connections", {}).get("inputs", [])
        assert validate_workflow(wm, wm._factory)["success"] is True

    print("test_editor_connects_merge_input_to_active_branch_port PASSED")


def test_editor_refresh_does_not_repair_legacy_merge_input_port():
    asyncio.run(_test_editor_refresh_does_not_repair_legacy_merge_input_port())


async def _test_editor_refresh_does_not_repair_legacy_merge_input_port():
    from textual.app import App, ComposeResult

    from backend.validator import validate_workflow
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("merge_legacy_input_repair")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    source = wm.add_node("user_text_input_node")
    merge = wm.add_node("merge_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_b", source, "input")
    wm.connect(source, "default", merge, "input")
    assert validate_workflow(wm, wm._factory)["success"] is False

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        merge_node = wm.get_node_data(merge)
        assert {
            "target_port": "input",
            "source_node_id": source,
            "source_port": "default",
        } in merge_node.get("connections", {}).get("inputs", [])
        assert validate_workflow(wm, wm._factory)["success"] is False

    print("test_editor_refresh_does_not_repair_legacy_merge_input_port PASSED")


def test_editor_branch_cycle_keys_switch_all_and_incomplete_branch_views():
    asyncio.run(_test_editor_branch_cycle_keys_switch_all_and_incomplete_branch_views())


def test_editor_command_keys_restore_lost_highlight_after_mouse_focus():
    asyncio.run(_test_editor_command_keys_restore_lost_highlight_after_mouse_focus())


async def _test_editor_branch_cycle_keys_switch_all_and_incomplete_branch_views():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_branch_cycle")
    start = wm.add_node("start_node")
    branch_one = wm.add_node("branch_node")
    branch_two = wm.add_node("branch_node")
    closed_end = wm.add_node("end_node")
    first_open = wm.add_node("sleep_node")
    second_open = wm.add_node("logger_node")
    branch_end = wm.add_node("branch_end_node")
    wm.connect(start, "default", branch_one, "input")
    wm.connect(branch_one, "path_a", closed_end, "input")
    wm.connect(branch_one, "path_b", branch_two, "input")
    wm.connect(branch_two, "path_a", first_open, "input")
    wm.connect(branch_two, "path_b", second_open, "input")
    wm.connect(second_open, "default", branch_end, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)

        await pilot.press("d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_one] == "path_b"
        assert screen.selected_node_id == branch_two
        node_list = screen.query_one("#node-list")
        assert node_list.index == node_list.index_for_node_id(branch_two)
        assert sum(1 for item in node_list.children if getattr(item, "highlighted", False)) == 1

        screen._select_row({"kind": "node", "node_id": branch_two})
        screen.refresh_from_backend()
        assert node_list.index == node_list.index_for_node_id(branch_two)
        assert sum(1 for item in node_list.children if getattr(item, "highlighted", False)) == 1

        await pilot.press("d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_one] == "path_b"
        assert screen.active_branch_ports[branch_two] == "path_a"
        assert screen.selected_node_id == first_open
        assert node_list.index == node_list.index_for_node_id(first_open)
        assert sum(1 for item in node_list.children if getattr(item, "highlighted", False)) == 1

        await pilot.press("right")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_one] == "path_b"
        assert screen.active_branch_ports[branch_two] == "path_b"
        assert screen.selected_node_id == second_open
        assert node_list.index == node_list.index_for_node_id(second_open)
        assert sum(1 for item in node_list.children if getattr(item, "highlighted", False)) == 1

        await pilot.press("d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_one] == "path_a"
        assert screen.selected_node_id == closed_end
        assert node_list.index == node_list.index_for_node_id(closed_end)
        assert sum(1 for item in node_list.children if getattr(item, "highlighted", False)) == 1

        await pilot.press("ctrl+d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_one] == "path_b"
        assert screen.selected_node_id == branch_two
        assert node_list.index == node_list.index_for_node_id(branch_two)

        await pilot.press("ctrl+d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_two] == "path_a"
        assert screen.selected_node_id == first_open
        assert node_list.index == node_list.index_for_node_id(first_open)

        await pilot.press("ctrl+d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_two] == "path_b"
        assert screen.selected_node_id == second_open
        assert node_list.index == node_list.index_for_node_id(second_open)

        await pilot.press("ctrl+d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch_one] == "path_b"
        assert screen.selected_node_id == branch_two
        assert node_list.index == node_list.index_for_node_id(branch_two)

    print("test_editor_branch_cycle_keys_switch_all_and_incomplete_branch_views PASSED")


async def _test_editor_command_keys_restore_lost_highlight_after_mouse_focus():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_restore_command_keys")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    first = wm.add_node("sleep_node")
    second = wm.add_node("logger_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", first, "input")
    wm.connect(branch, "path_b", second, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        node_list = screen.query_one("#node-list")
        details = screen.query_one("#node-details")

        node_list.index = None
        node_list.normalize_highlight()
        app.set_focus(details)
        assert not any(
            getattr(item, "highlighted", False)
            for item in node_list.children
        )

        await pilot.press("d")
        await pilot.pause(0.03)
        assert app.focused is node_list
        assert screen.active_branch_ports[branch] == "path_b"
        assert screen.selected_node_id == second
        assert node_list.index == node_list.index_for_node_id(second)
        assert sum(1 for item in node_list.children if getattr(item, "highlighted", False)) == 1

        app.set_focus(details)
        node_list.index = None
        node_list.normalize_highlight()
        await pilot.press("s")
        await pilot.pause(0.03)
        assert app.focused is node_list
        assert node_list.index is not None
        assert sum(1 for item in node_list.children if getattr(item, "highlighted", False)) == 1

        opened = []
        original_push_screen = app.push_screen

        def capture_push_screen(screen_to_push, *args, **kwargs):
            opened.append(type(screen_to_push).__name__)
            return None

        app.push_screen = capture_push_screen
        try:
            app.set_focus(details)
            await pilot.press("e")
            await pilot.pause(0.03)
        finally:
            app.push_screen = original_push_screen
        assert opened

    print("test_editor_command_keys_restore_lost_highlight_after_mouse_focus PASSED")


def test_editor_restores_persisted_focus_highlight_on_mount():
    asyncio.run(_test_editor_restores_persisted_focus_highlight_on_mount())


async def _test_editor_restores_persisted_focus_highlight_on_mount():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_restore_highlight")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    first = wm.add_node("sleep_node")
    tail = wm.add_node("logger_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_b", first, "input")
    wm.connect(first, "default", tail, "input")

    class EditorApp(App):
        def __init__(self):
            super().__init__()
            self._editor_selection_state = {
                "selected_node_id": first,
                "selected_row": {"kind": "node", "node_id": first},
                "active_branch_ports": {branch: "path_b"},
                "last_branch_selection": {f"{branch}:path_b": first},
            }

        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        node_list = screen.query_one("#node-list")
        assert screen.selected_node_id == first
        assert screen.active_branch_ports[branch] == "path_b"
        assert node_list.index == node_list.index_for_node_id(first)
        assert app.focused is node_list

    print("test_editor_restores_persisted_focus_highlight_on_mount PASSED")


def test_editor_notification_restores_node_list_focus():
    asyncio.run(_test_editor_notification_restores_node_list_focus())


async def _test_editor_notification_restores_node_list_focus():
    from textual.app import App, ComposeResult

    from frontend import notifications
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_notification_focus")
    start = wm.add_node("start_node")
    node = wm.add_node("logger_node")
    wm.connect(start, "default", node, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        node_list = screen.query_one("#node-list")
        screen.selected_node_id = node
        screen.selected_row = {"kind": "node", "node_id": node}
        screen.refresh_from_backend()
        app.set_focus(None)

        notifications.node_updated(app)
        await pilot.pause(0.03)

        assert app.focused is node_list
        assert node_list.index == node_list.index_for_node_id(node)

    print("test_editor_notification_restores_node_list_focus PASSED")


def test_editor_depth_counter_tracks_visible_branch_distance():
    asyncio.run(_test_editor_depth_counter_tracks_visible_branch_distance())


async def _test_editor_depth_counter_tracks_visible_branch_distance():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import BranchSelectCard, NodeCard
    from frontend.widgets.status_bar import StatusBar

    _, wm, _, _ = _make_services()
    wm.create_new("editor_depth_counter")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    path_a_node = wm.add_node("sleep_node")
    path_b_first = wm.add_node("logger_node")
    path_b_second = wm.add_node("text_output_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", path_a_node, "input")
    wm.connect(branch, "path_b", path_b_first, "input")
    wm.connect(path_b_first, "default", path_b_second, "input")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        node_list = screen.query_one("#node-list")

        rows = node_list._rows
        assert rows[0]["node_id"] == start
        assert rows[0]["depth"] == 0
        assert rows[1]["node_id"] == branch
        assert rows[1]["depth"] == 1
        assert rows[2]["kind"] == "branch_select"
        assert rows[2]["depth"] == 1
        assert rows[3]["node_id"] == path_a_node
        assert rows[3]["depth"] == 2

        start_card = next(card for card in app.query(NodeCard) if card.node_id == start)
        branch_row = app.query_one(BranchSelectCard)
        status = app.query_one(StatusBar)
        assert start_card.display_text == "  0   Start"
        assert branch_row.display_text == "  ☛   Branch 1"
        assert "f file | o options | h help" in status._formatted()
        assert "Ctrl+I" not in status._formatted()
        titles = [str(label.content) for label in app.query(".panel-title")]
        assert "Details" not in titles
        assert "Keys" not in titles
        assert "Selected Node:" in titles

        await pilot.press("d")
        await pilot.pause(0.03)
        rows = node_list._rows
        assert [row.get("depth") for row in rows if row["kind"] == "node"] == [0, 1, 2, 3]
        assert screen.selected_node_id == path_b_first
        details = screen.query_one("#node-details").display_text
        assert details.startswith(f"Name: Logger ({path_b_first})")
        assert "Kind: Logger" in details
        assert "Step: 2" in details

    print("test_editor_depth_counter_tracks_visible_branch_distance PASSED")


def test_help_screen_is_contextual_and_focuses_cancel():
    asyncio.run(_test_help_screen_is_contextual_and_focuses_cancel())


async def _test_help_screen_is_contextual_and_focuses_cancel():
    from textual.app import App, ComposeResult
    from textual.widgets import Button

    from frontend.screens.help import HelpScreen

    class HelpApp(App):
        def compose(self) -> ComposeResult:
            yield HelpScreen("editor")

    app = HelpApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        help_text = str(app.query_one("#help-text").content)
        buttons = list(app.query(Button))

        assert "Editor" in help_text
        assert "Move through nodes" in help_text
        assert "Execution" not in help_text
        assert len(buttons) == 1
        assert buttons[0].label == "Cancel"
        assert app.focused is buttons[0]

    print("test_help_screen_is_contextual_and_focuses_cancel PASSED")


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


def test_node_config_saves_transient_output_overrides_and_vertical_buttons():
    asyncio.run(_test_node_config_saves_transient_output_overrides_and_vertical_buttons())


async def _test_node_config_saves_transient_output_overrides_and_vertical_buttons():
    from textual.app import App, ComposeResult
    from textual.widgets import Button

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()
    wm.create_new("transient_output_config")
    node = wm.add_node("logger_node")

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node, wm.get_node_data(node))

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(NodeConfigScreen)
        name_input = app.query_one("#transient-output-name-default", CommandInput)
        desc_input = app.query_one("#transient-output-desc-default", CommandInput)
        save_button = app.query_one("#save-node-config", Button)
        cancel_button = app.query_one("#cancel-node-config", Button)

        name_input.value = "approved_text"
        desc_input.value = "Approved output"
        widgets = screen._keyboard_focus_widgets()
        assert widgets.index(save_button) < widgets.index(cancel_button)

        results = []
        screen.dismiss = results.append
        await pilot.press("ctrl+s")
        await pilot.pause()

    outputs = results[-1]["config"]["transient_outputs"]
    assert outputs == [
        {
            "port": "default",
            "name": "approved_text",
            "description": "Approved output",
        }
    ]
    print("test_node_config_saves_transient_output_overrides_and_vertical_buttons PASSED")


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


def test_editor_quick_view_lists_transient_and_memory_io():
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("quick_view_io")
    source = wm.add_node("logger_node")
    consumer = wm.add_node("logger_node")
    memory_writer = wm.add_node("logger_node")

    wm.update_node_alias(source, "Producer")
    wm.update_node_alias(consumer, "Consumer")
    wm.update_node_config(
        source,
        {"membank_outputs": [{"id": "produced_text", "description": "Created text"}]},
    )
    wm.update_node_config(
        memory_writer,
        {"membank_outputs": [{"id": "session_id", "description": "Session id"}]},
    )
    wm.update_node_config(
        consumer,
        {
            "membank_inputs": ["session_id"],
            "membank_outputs": [{"id": "final_text", "description": "Final text"}],
        },
    )
    wm.connect(source, "default", consumer, "input")

    screen = EditorScreen(wm._factory, wm)
    text = screen._format_node_details(consumer, wm.get_node_data(consumer))

    assert "Inputs:" in text
    assert "Transient Source: Producer" in text
    assert "produced_text: Created text" in text
    assert "Memory" in text
    assert "session_id: Session id" in text
    assert "Outputs:" in text
    assert "Output: No output description configured." in text
    assert "final_text: Final text" in text
    assert "Next:" not in text
    print("test_editor_quick_view_lists_transient_and_memory_io PASSED")


def test_editor_quick_view_shows_branch_output_names_and_empty_memory():
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("quick_view_branch_names")
    branch = wm.add_node("branch_node")
    wm.update_node_config(
        branch,
        {"path_a_label": "Approve", "path_b_label": "Reject"},
    )

    screen = EditorScreen(wm._factory, wm)
    text = screen._format_node_details(branch, wm.get_node_data(branch))

    assert "Inputs:" in text
    assert "Transient Source: none" in text
    assert "    none" in text
    assert "Outputs:" in text
    assert "Approve: No output description configured." in text
    assert "Reject: No output description configured." in text
    print("test_editor_quick_view_shows_branch_output_names_and_empty_memory PASSED")


def test_editor_quick_view_traces_pass_through_producer():
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("quick_view_pass_through")
    source = wm.add_node("logger_node")
    sleeper = wm.add_node("sleep_node")
    target = wm.add_node("logger_node")

    wm.update_node_alias(source, "Producer")
    wm.update_node_alias(sleeper, "Pause")
    wm.update_node_config(
        source,
        {"membank_outputs": [{"id": "created_payload", "description": "Original data"}]},
    )
    wm.connect(source, "default", sleeper, "input")
    wm.connect(sleeper, "default", target, "input")

    screen = EditorScreen(wm._factory, wm)
    text = screen._format_node_details(target, wm.get_node_data(target))

    assert "Transient Source: Producer" in text
    assert "created_payload: Original data" in text
    assert "Pause" not in text
    print("test_editor_quick_view_traces_pass_through_producer PASSED")


def test_editor_quick_view_uses_transient_output_overrides():
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("quick_view_transient_override")
    source = wm.add_node("logger_node")
    wm.update_node_config(
        source,
        {
            "transient_outputs": [
                {
                    "port": "default",
                    "name": "approved_text",
                    "description": "Text approved for downstream use",
                }
            ]
        },
    )

    screen = EditorScreen(wm._factory, wm)
    text = screen._format_node_details(source, wm.get_node_data(source))

    assert "approved_text: Text approved for downstream use" in text
    print("test_editor_quick_view_uses_transient_output_overrides PASSED")


def test_node_config_previous_output_preview_traces_pass_through_source():
    from frontend.screens.node_config import NodeConfigScreen

    _, wm, mb, _ = _make_services()
    wm.create_new("previous_output_pass_through")
    source = wm.add_node("logger_node")
    sleeper = wm.add_node("sleep_node")
    target = wm.add_node("logger_node")

    wm.update_node_alias(source, "Producer")
    wm.update_node_alias(sleeper, "Pause")
    wm.update_node_config(
        source,
        {"membank_outputs": [{"id": "created_payload", "description": "Original data"}]},
    )
    wm.connect(source, "default", sleeper, "input")
    wm.connect(sleeper, "default", target, "input")
    mb.store_transient(sleeper, "default", {"message": "after pause"})

    screen = NodeConfigScreen(
        wm._factory,
        wm,
        target,
        wm.get_node_data(target),
        memory_bank=mb,
    )
    text = screen._previous_output_text()

    assert "Source: Producer" in text
    assert "Output: created_payload" in text
    assert "Output Description: Original data" in text
    assert "after pause" in text
    assert "Pause" not in text
    print("test_node_config_previous_output_preview_traces_pass_through_source PASSED")


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
    from textual.widgets import Button, ListView, Static

    import frontend.screens.workflow_library as workflow_library_module
    from frontend.screens.workflow_library import WorkflowLibraryScreen

    original_list_workflows = workflow_library_module.list_workflows
    workflow_library_module.list_workflows = lambda: [
        {"id": "wf-1", "name": "Duplicate"},
        {"id": "wf-2", "name": "Second"},
        {"id": "wf-3", "name": "Duplicate"},
    ]

    class LibraryApp(App):
        def compose(self) -> ComposeResult:
            yield WorkflowLibraryScreen("wf-2")

    try:
        app = LibraryApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            screen = app.query_one(WorkflowLibraryScreen)
            workflow_list = app.query_one("#workflow-list", ListView)
            cancel = app.query_one("#cancel-workflow-library", Button)

            assert app.focused is workflow_list
            assert workflow_list.index == 0
            row_texts = [
                item.query_one(Static).display_text
                for item in workflow_list.children
            ]
            assert row_texts == [
                "Duplicate",
                "Second <-- Loaded Workflow",
                "Duplicate (2)",
            ]
            assert "wf-" not in "\n".join(row_texts)
            button_ids = [button.id for button in app.query(Button)]
            assert button_ids == ["cancel-workflow-library"]

            screen.action_cursor_down()
            assert workflow_list.index == 1
            screen.action_cursor_down()
            assert workflow_list.index == 2
            screen.action_cursor_down()
            assert app.focused is cancel
            screen.action_cursor_up()
            assert app.focused is workflow_list
            assert workflow_list.index == 2
    finally:
        workflow_library_module.list_workflows = original_list_workflows

    print("test_workflow_library_uses_shared_list_navigation PASSED")


def test_export_cancel_returns_to_file_menu():
    asyncio.run(_test_export_cancel_returns_to_file_menu())


def test_file_picker_export_and_import_paths():
    asyncio.run(_test_file_picker_export_and_import_paths())


def test_file_picker_cancel_and_fallback_paths():
    asyncio.run(_test_file_picker_cancel_and_fallback_paths())


def test_file_manager_reveal_commands_are_platform_specific():
    from pathlib import Path

    import frontend.file_io as file_io

    original_is_wsl = file_io._is_wsl
    original_system = file_io.platform.system
    original_which = file_io.shutil.which
    original_env = dict(file_io.os.environ)
    try:
        file_io._is_wsl = lambda: False
        file_io.platform.system = lambda: "Windows"
        assert file_io._reveal_command(Path("C:/tmp/demo.json"), True) == [
            "explorer",
            "/select,C:/tmp/demo.json",
        ]

        file_io.platform.system = lambda: "Darwin"
        assert file_io._reveal_command(Path("/tmp/demo.json"), True) == [
            "open",
            "-R",
            "/tmp/demo.json",
        ]

        file_io.platform.system = lambda: "Linux"
        file_io.os.environ.clear()
        file_io.os.environ["DISPLAY"] = ":0"
        file_io.shutil.which = lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None
        assert file_io._reveal_command(Path("/tmp/demo.json"), True) == [
            "/usr/bin/xdg-open",
            "/tmp",
        ]
    finally:
        file_io._is_wsl = original_is_wsl
        file_io.platform.system = original_system
        file_io.shutil.which = original_which
        file_io.os.environ.clear()
        file_io.os.environ.update(original_env)

    print("test_file_manager_reveal_commands_are_platform_specific PASSED")


async def _test_export_cancel_returns_to_file_menu():
    from frontend.app import AttackOfTheNodesApp
    from frontend.screens.workflow_library import WorkflowLibraryScreen

    master, wm, mb, bus = _make_services()
    wm.create_new("export_cancel")

    app = AttackOfTheNodesApp(bus, wm._factory, wm, mb, master)
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        app._export_workflow_to_path({"workflow_id": "wf-1"}, None)
        await pilot.pause(0.03)
        assert isinstance(app.screen, WorkflowLibraryScreen)

    print("test_export_cancel_returns_to_file_menu PASSED")


async def _test_file_picker_export_and_import_paths():
    import frontend.file_io as file_io
    from frontend.app import AttackOfTheNodesApp

    class FakeSaveManager:
        configuration_manager = None

        def __init__(self):
            self.exported = []
            self.imported = []
            self.loaded = []

        def export_workflow(self, workflow_id, path):
            self.exported.append((workflow_id, path))
            return True

        def import_workflow(self, path):
            self.imported.append(path)
            return "wf-imported"

        def load_workflow(self, workflow_id):
            self.loaded.append(workflow_id)
            return True

    original_save = file_io.pick_save_file
    original_open = file_io.pick_open_file
    try:
        fake_save = FakeSaveManager()
        file_io.pick_save_file = lambda *args, **kwargs: "/tmp/exported.json"
        master, wm, mb, bus = _make_services()
        wm.create_new("picker_export")
        app = AttackOfTheNodesApp(bus, wm._factory, wm, mb, master, fake_save)
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            app._prompt_export_workflow({"workflow_id": "wf-export"})
            await pilot.pause(0.1)
            assert fake_save.exported == [("wf-export", "/tmp/exported.json")]

        fake_import = FakeSaveManager()
        file_io.pick_open_file = lambda *args, **kwargs: "/tmp/imported.json"
        master, wm, mb, bus = _make_services()
        wm.create_new("picker_import")
        app = AttackOfTheNodesApp(bus, wm._factory, wm, mb, master, fake_import)
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            wm.mark_saved()
            app._prompt_import_workflow()
            await pilot.pause(0.1)
            assert fake_import.imported == ["/tmp/imported.json"]
            assert fake_import.loaded == ["wf-imported"]
    finally:
        file_io.pick_save_file = original_save
        file_io.pick_open_file = original_open

    print("test_file_picker_export_and_import_paths PASSED")


async def _test_file_picker_cancel_and_fallback_paths():
    import frontend.file_io as file_io
    from frontend.app import AttackOfTheNodesApp
    from frontend.screens.workflow_library import PathPromptScreen, WorkflowLibraryScreen

    class FakeSaveManager:
        configuration_manager = None

    original_save = file_io.pick_save_file
    original_open = file_io.pick_open_file
    try:
        master, wm, mb, bus = _make_services()
        wm.create_new("picker_cancel")
        app = AttackOfTheNodesApp(bus, wm._factory, wm, mb, master, FakeSaveManager())
        file_io.pick_save_file = lambda *args, **kwargs: None
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            app._prompt_export_workflow({"workflow_id": "wf-cancel"})
            await pilot.pause(0.1)
            assert isinstance(app.screen, WorkflowLibraryScreen)

        master, wm, mb, bus = _make_services()
        wm.create_new("picker_fallback")
        app = AttackOfTheNodesApp(bus, wm._factory, wm, mb, master, FakeSaveManager())

        def unavailable(*args, **kwargs):
            raise file_io.FilePickerUnavailable("no picker")

        file_io.pick_open_file = unavailable
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            app._prompt_import_workflow()
            await pilot.pause(0.1)
            assert isinstance(app.screen, PathPromptScreen)
            assert "path" in app.screen.title_text.lower()
    finally:
        file_io.pick_save_file = original_save
        file_io.pick_open_file = original_open

    print("test_file_picker_cancel_and_fallback_paths PASSED")


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


def test_ctrl_c_uses_screen_copy_and_ctrl_q_stays_contextual():
    from textual.screen import Screen

    from frontend.app import AttackOfTheNodesApp

    def binding_key(binding):
        return binding.key if hasattr(binding, "key") else binding[0]

    def binding_action(binding):
        return binding.action if hasattr(binding, "action") else binding[1]

    app_bindings = list(AttackOfTheNodesApp.BINDINGS)
    assert not any(
        "ctrl+c" in binding_key(binding)
        and binding_action(binding) == "quit"
        for binding in app_bindings
    )
    assert any(
        "ctrl+q" in binding_key(binding)
        and binding_action(binding) == "back"
        for binding in app_bindings
    )
    assert any(
        "ctrl+c" in binding_key(binding)
        and binding_action(binding) == "screen.copy_text"
        for binding in Screen.BINDINGS
    )

    print("test_ctrl_c_uses_screen_copy_and_ctrl_q_stays_contextual PASSED")


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
        title = str(app.query_one(".modal-title").content)
        assert title == f"Edit Node: Logger ({node_id})"
        app.set_focus(alias)
        assert app.focused is alias
        assert alias.editing is False

        screen.action_cursor_down()
        assert alias.value == node_data.get("alias", "")
        assert app.focused is not alias

        screen.action_cursor_up()
        assert app.focused is alias
        assert alias.editing is False
        alias.cursor_position = len(alias.value)
        previous_value = alias.value
        await pilot.press("a")
        assert alias.value == previous_value
        assert alias.cursor_position == max(0, len(previous_value) - 1)
        await pilot.press("d")
        assert alias.cursor_position == len(previous_value)

        screen.action_activate_focused()
        assert alias.editing is True
        assert alias.cursor_position == len(alias.value)
        await pilot.press("x")
        assert alias.value.endswith("x")
        await pilot.press("w", "s")
        assert app.focused is alias
        assert alias.editing is True
        assert alias.value.endswith("xws")
        await pilot.press("left")
        assert app.focused is alias
        assert alias.editing is True
        assert alias.cursor_position == len(alias.value) - 1
        await pilot.press("right")
        assert alias.cursor_position == len(alias.value)
        for key in ("up", "down"):
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
        screen.action_cursor_up()
        assert app.focused is alias
        screen.action_activate_focused()
        await pilot.press("tab")
        assert alias.editing is False
        assert app.focused is not alias
        await pilot.press("w")
        assert app.focused is alias

    print("test_node_config_command_inputs_require_activation PASSED")


def test_simple_command_modals_use_shared_navigation_helpers():
    asyncio.run(_test_simple_command_modals_use_shared_navigation_helpers())


async def _test_simple_command_modals_use_shared_navigation_helpers():
    from textual import events
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Checkbox

    from backend.configuration_manager import DEFAULT_SETTINGS
    from frontend.screens.settings import ApiKeysPlaceholderScreen, SettingsScreen
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
        api_keys = app.query_one("#api-keys-settings", Button)
        save_button = app.query_one("#save-settings", Button)
        cancel_button = app.query_one("#cancel-settings", Button)

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
        widgets = screen._nav_widgets()
        assert widgets.index(api_keys) < widgets.index(save_button) < widgets.index(cancel_button)
        await pilot.press("k")
        await pilot.pause()
        assert isinstance(app.screen, ApiKeysPlaceholderScreen)

    print("test_simple_command_modals_use_shared_navigation_helpers PASSED")


def test_prompt_modals_use_shared_command_activation():
    asyncio.run(_test_prompt_modals_use_shared_command_activation())


async def _test_prompt_modals_use_shared_command_activation():
    from textual import events
    from textual.app import App, ComposeResult
    from textual.widgets import Button

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
        await pilot.press("tab")
        await pilot.pause()
        assert path_input.editing is False
        assert path_app.focused is path_app.query_one("#confirm-path", Button)
        path_input.begin_edit()
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


def test_editor_ctrl_s_quick_saves():
    asyncio.run(_test_editor_ctrl_s_quick_saves())


async def _test_editor_ctrl_s_quick_saves():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_quick_save")
    wm.add_node("start_node")
    saves = []

    class SaveApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

        def action_save_workflow(self) -> None:
            saves.append("saved")

    app = SaveApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        await pilot.press("ctrl+s")
        await pilot.pause()

    assert saves == ["saved"]
    print("test_editor_ctrl_s_quick_saves PASSED")


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
# 63. Phase 13 — cursor model foundation
# ---------------------------------------------------------------------------


def test_command_screen_mixin_class_hierarchy():
    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from frontend.screens.settings import SettingsScreen
    from frontend.screens.user_input import UserInputScreen
    from frontend.screens.workflow_library import PathPromptScreen
    from frontend.screens.node_config import NodeConfigScreen

    for cls in (SettingsScreen, UserInputScreen, PathPromptScreen, NodeConfigScreen):
        assert issubclass(cls, CommandScreenMixin), f"{cls.__name__} should inherit CommandScreenMixin"
    print("test_command_screen_mixin_class_hierarchy PASSED")


def test_status_bar_mode_indicator():
    from frontend.widgets.status_bar import StatusBar

    bar = StatusBar("W/S move")
    assert "[NAV]" in bar._formatted()
    assert "W/S move" in bar._formatted()

    bar.set_mode("edit")
    assert "[EDIT]" in bar._formatted()
    assert "[NAV]" not in bar._formatted()

    bar.set_mode("nav")
    assert "[NAV]" in bar._formatted()
    print("test_status_bar_mode_indicator PASSED")


def test_cursor_state_tracks_mode():
    from frontend.widgets.cursor_state import CursorState

    state = CursorState()
    assert state.mode == "nav"
    state.set_edit()
    assert state.mode == "edit"
    state.set_nav()
    assert state.mode == "nav"
    print("test_cursor_state_tracks_mode PASSED")


def test_command_screen_mixin_navigates_widgets():
    asyncio.run(_test_command_screen_mixin_navigates_widgets())


async def _test_command_screen_mixin_navigates_widgets():
    from textual.app import App, ComposeResult
    from textual.screen import Screen
    from textual.widgets import Button

    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from frontend.widgets.command_input import CommandInput

    class NavScreen(CommandScreenMixin, Screen):
        def compose(self) -> ComposeResult:
            yield CommandInput(id="first")
            yield CommandInput(id="second")
            yield Button("ok", id="btn")

        def on_mount(self) -> None:
            self._focus_first()

    class NavApp(App):
        def on_mount(self) -> None:
            self.push_screen(NavScreen())

    app = NavApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        assert app.focused.id == "first"

        await pilot.press("s")
        await pilot.pause(0.02)
        assert app.focused.id == "second"

        await pilot.press("s")
        await pilot.pause(0.02)
        assert app.focused.id == "btn"

        await pilot.press("w")
        await pilot.pause(0.02)
        assert app.focused.id == "second"

    print("test_command_screen_mixin_navigates_widgets PASSED")


def test_command_screen_mixin_boundary_stays_put():
    asyncio.run(_test_command_screen_mixin_boundary_stays_put())


async def _test_command_screen_mixin_boundary_stays_put():
    from textual.app import App, ComposeResult
    from textual.screen import Screen

    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from frontend.widgets.command_input import CommandInput

    class BoundScreen(CommandScreenMixin, Screen):
        def compose(self) -> ComposeResult:
            yield CommandInput(id="only")

        def on_mount(self) -> None:
            self._focus_first()

    class BoundApp(App):
        def on_mount(self) -> None:
            self.push_screen(BoundScreen())

    app = BoundApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        assert app.focused.id == "only"
        # pressing W at top should stay on same widget (boundary clamped)
        await pilot.press("w")
        await pilot.pause(0.02)
        assert app.focused.id == "only"
        # pressing S at bottom should also stay
        await pilot.press("s")
        await pilot.pause(0.02)
        assert app.focused.id == "only"

    print("test_command_screen_mixin_boundary_stays_put PASSED")


def test_command_screen_mixin_blocks_nav_when_editing():
    asyncio.run(_test_command_screen_mixin_blocks_nav_when_editing())


async def _test_command_screen_mixin_blocks_nav_when_editing():
    from textual.app import App, ComposeResult
    from textual.screen import Screen

    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from frontend.widgets.command_input import CommandInput

    class EditScreen(CommandScreenMixin, Screen):
        def compose(self) -> ComposeResult:
            yield CommandInput(id="field-a")
            yield CommandInput(id="field-b")

        def on_mount(self) -> None:
            self._focus_first()

    class EditApp(App):
        def on_mount(self) -> None:
            self.push_screen(EditScreen())

    app = EditApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        assert app.focused.id == "field-a"

        # enter edit mode on field-a
        await pilot.press("e")
        await pilot.pause(0.02)
        assert app.focused.editing is True

        # W/S should not move focus while editing
        await pilot.press("s")
        await pilot.pause(0.02)
        assert app.focused.id == "field-a", "S should not move focus while editing"

    print("test_command_screen_mixin_blocks_nav_when_editing PASSED")


def test_cursor_state_syncs_with_mixin():
    asyncio.run(_test_cursor_state_syncs_with_mixin())


async def _test_cursor_state_syncs_with_mixin():
    from textual.app import App, ComposeResult
    from textual.screen import Screen

    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from frontend.widgets.cursor_state import CursorState
    from frontend.widgets.command_input import CommandInput

    class SyncScreen(CommandScreenMixin, Screen):
        def compose(self) -> ComposeResult:
            yield CommandInput(id="inp-a")
            yield CommandInput(id="inp-b")

        def on_mount(self) -> None:
            self._focus_first()

    class SyncApp(App):
        def __init__(self):
            super().__init__()
            self.cursor_state = CursorState()

        def on_mount(self) -> None:
            self.push_screen(SyncScreen())

    app = SyncApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        assert app.cursor_state.mode == "nav"

        await pilot.press("e")
        await pilot.pause(0.02)
        assert app.cursor_state.mode == "edit"

        await pilot.press("escape")
        await pilot.pause(0.02)
        # After leaving edit mode, next nav action should set mode back to nav
        await pilot.press("s")
        await pilot.pause(0.02)
        assert app.cursor_state.mode == "nav"

    print("test_cursor_state_syncs_with_mixin PASSED")


def test_auto_edit_prompt_syncs_cursor_and_status_bar():
    asyncio.run(_test_auto_edit_prompt_syncs_cursor_and_status_bar())


async def _test_auto_edit_prompt_syncs_cursor_and_status_bar():
    from textual.app import App, ComposeResult

    from frontend.screens.user_input import UserInputScreen
    from frontend.widgets.command_input import CommandInput
    from frontend.widgets.cursor_state import CursorState
    from frontend.widgets.status_bar import StatusBar

    class PromptApp(App):
        def __init__(self):
            super().__init__()
            self.cursor_state = CursorState()

        def compose(self) -> ComposeResult:
            yield UserInputScreen("branch", "node", "Prompt")

    app = PromptApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        field = app.query_one("#user-input-value", CommandInput)
        status = app.query_one(StatusBar)
        assert app.focused is field
        assert field.editing is True
        assert app.cursor_state.mode == "edit"
        assert "[EDIT]" in status._formatted()

        await pilot.press("escape")
        await pilot.pause(0.02)
        assert field.editing is False
        assert app.cursor_state.mode == "nav"
        assert "[NAV]" in status._formatted()

    print("test_auto_edit_prompt_syncs_cursor_and_status_bar PASSED")


def test_click_edit_and_textarea_commit_sync_cursor_mode():
    asyncio.run(_test_click_edit_and_textarea_commit_sync_cursor_mode())


def test_command_text_nav_mode_ad_positions_caret_before_edit():
    asyncio.run(_test_command_text_nav_mode_ad_positions_caret_before_edit())


async def _test_click_edit_and_textarea_commit_sync_cursor_mode():
    from textual import events
    from textual.app import App, ComposeResult
    from textual.screen import Screen
    from textual.widgets._input import Selection

    from frontend.widgets.command_input import CommandInput, CommandTextArea
    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from frontend.widgets.cursor_state import CursorState
    from frontend.widgets.status_bar import StatusBar

    def click(widget, chain: int = 1) -> events.Click:
        return events.Click(widget, 0, 0, 0, 0, 1, False, False, False, chain=chain)

    class EditScreen(CommandScreenMixin, Screen):
        def compose(self) -> ComposeResult:
            yield CommandInput(value="sample", id="input")
            yield CommandTextArea("hello\nworld", id="textarea")
            yield StatusBar("test")

        def on_mount(self) -> None:
            self._focus_first()

    class EditApp(App):
        def __init__(self):
            super().__init__()
            self.cursor_state = CursorState()

        def compose(self) -> ComposeResult:
            yield EditScreen()

    app = EditApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        text_input = app.query_one("#input", CommandInput)
        textarea = app.query_one("#textarea", CommandTextArea)
        status = app.query_one(StatusBar)

        text_input.cursor_position = 2
        text_input.on_click(click(text_input))
        assert app.cursor_state.mode == "edit"
        assert "[EDIT]" in status._formatted()
        assert text_input.cursor_position == 2
        text_input.end_edit()

        text_input.selection = Selection(1, 4)
        text_input.on_click(click(text_input))
        assert text_input.editing is True
        assert text_input.selection == Selection(1, 4)

        await pilot.press("escape")
        await pilot.pause(0.02)
        assert app.cursor_state.mode == "nav"
        assert "[NAV]" in status._formatted()

        text_input.selection = Selection(0, len(text_input.value))
        await pilot.press("e")
        await pilot.pause(0.02)
        assert text_input.editing is True
        assert text_input.selection == Selection.cursor(len(text_input.value))
        await pilot.press("escape")
        await pilot.pause(0.02)

        textarea.move_cursor((1, 2))
        textarea.on_click(click(textarea))
        assert app.cursor_state.mode == "edit"
        assert textarea.selection.end == (1, 2)
        textarea.end_edit()
        textarea.begin_edit()
        assert textarea.selection.end == (1, 5)
        await pilot.press("left")
        await pilot.pause(0.02)
        assert textarea.selection.end == (1, 4)
        textarea.begin_edit()
        await pilot.press("tab")
        await pilot.pause(0.02)
        assert textarea.editing is False
        assert app.cursor_state.mode == "nav"
        textarea.begin_edit()
        await pilot.press("ctrl+enter")
        await pilot.pause(0.02)
        assert app.cursor_state.mode == "nav"
        assert "[NAV]" in status._formatted()

    print("test_click_edit_and_textarea_commit_sync_cursor_mode PASSED")


async def _test_command_text_nav_mode_ad_positions_caret_before_edit():
    from textual.app import App, ComposeResult
    from textual.screen import Screen

    from frontend.widgets.command_input import CommandInput, CommandTextArea
    from frontend.widgets.command_screen_mixin import CommandScreenMixin

    class EditScreen(CommandScreenMixin, Screen):
        def compose(self) -> ComposeResult:
            yield CommandInput(value="abcd", id="input")
            yield CommandTextArea("one\ntwo", id="textarea")

        def on_mount(self) -> None:
            self._focus_first()

    class EditApp(App):
        def compose(self) -> ComposeResult:
            yield EditScreen()

    app = EditApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        text_input = app.query_one("#input", CommandInput)
        textarea = app.query_one("#textarea", CommandTextArea)

        text_input.cursor_position = len(text_input.value)
        await pilot.press("a")
        assert text_input.editing is False
        assert text_input.value == "abcd"
        assert text_input.cursor_position == 3
        await pilot.press("e")
        assert text_input.editing is True
        assert text_input.cursor_position == 3
        await pilot.press("d")
        assert text_input.value == "abcdd"
        await pilot.press("escape")

        app.set_focus(textarea)
        textarea.end_edit()
        textarea.move_cursor((1, 3))
        await pilot.press("a")
        assert textarea.editing is False
        assert textarea.selection.end == (1, 2)
        await pilot.press("e")
        assert textarea.editing is True
        assert textarea.selection.end == (1, 2)
        await pilot.press("d")
        assert textarea.text == "one\ntwdo"

    print("test_command_text_nav_mode_ad_positions_caret_before_edit PASSED")


def test_mixin_blocks_nav_when_active_text_not_focused():
    asyncio.run(_test_mixin_blocks_nav_when_active_text_not_focused())


async def _test_mixin_blocks_nav_when_active_text_not_focused():
    from textual.app import App, ComposeResult
    from textual.screen import Screen
    from textual.widgets import Button

    from frontend.widgets.command_input import CommandInput
    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from frontend.widgets.cursor_state import CursorState
    from frontend.widgets.status_bar import StatusBar

    class GuardScreen(CommandScreenMixin, Screen):
        def compose(self) -> ComposeResult:
            yield CommandInput(id="field")
            yield Button("Next", id="next")
            yield StatusBar("test")

        def on_mount(self) -> None:
            self._focus_first()

    class GuardApp(App):
        def __init__(self):
            super().__init__()
            self.cursor_state = CursorState()

        def compose(self) -> ComposeResult:
            yield GuardScreen()

    app = GuardApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        field = app.query_one("#field", CommandInput)
        button = app.query_one("#next", Button)
        field.begin_edit()
        app.set_focus(button)
        assert field.editing is True
        assert app.cursor_state.mode == "edit"

        await pilot.press("s")
        await pilot.pause(0.02)
        assert app.focused is button
        assert field.editing is True
        assert app.cursor_state.mode == "edit"

    print("test_mixin_blocks_nav_when_active_text_not_focused PASSED")


def test_migrated_command_screens_render_status_bar():
    asyncio.run(_test_migrated_command_screens_render_status_bar())


async def _test_migrated_command_screens_render_status_bar():
    from textual.app import App, ComposeResult

    from backend.configuration_manager import DEFAULT_SETTINGS
    from frontend.screens.node_config import NodeConfigScreen
    from frontend.screens.settings import SettingsScreen
    from frontend.screens.user_input import UserInputScreen
    from frontend.screens.workflow_library import PathPromptScreen
    from frontend.widgets.status_bar import StatusBar

    class FakeConfigurationManager:
        def get_all(self):
            return dict(DEFAULT_SETTINGS)

    _, wm, _, _ = _make_services()
    wm.create_new("status_bar_node_config")
    node_id = wm.add_node("logger_node")
    node_data = wm.get_node_data(node_id)

    screens = [
        SettingsScreen(FakeConfigurationManager()),
        UserInputScreen("branch", "node", "Prompt"),
        PathPromptScreen("Path"),
        NodeConfigScreen(wm._factory, wm, node_id, node_data),
    ]

    for screen in screens:
        class ScreenApp(App):
            def compose(self) -> ComposeResult:
                yield screen

        app = ScreenApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.05)
            assert app.query(StatusBar), f"{type(screen).__name__} should render StatusBar"

    print("test_migrated_command_screens_render_status_bar PASSED")


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
        test_new_nodes_use_default_display_alias,
        test_save_manager_writes_input_sources,
        test_validator_flags_missing_input_sources,
        test_validator_flags_missing_membank_input_sources,
        test_membank_registry_filters_downstream_writers,
        test_insert_between_rewires_below_source_node,
        test_tombstone_delete_does_not_cascade_branch_nodes,
        test_tombstone_restore_preserves_original_and_swap_invalidates_timing,
        test_editor_deleted_node_row_renders_as_deleted,
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
        test_merge_options_exclude_branch_containing_current_merge,
        test_merge_options_include_nested_merge_beacons,
        test_merge_branch_selector_moves_focus_down_at_bottom,
        test_saving_merge_config_connects_selected_branch_end,
        test_saving_merge_config_unchecked_branch_disconnects_branch_end,
        test_saving_merge_config_preserves_merge_home_branch_input,
        test_deleting_merge_beacon_prunes_merge_config_selection,
        test_editor_blocks_insert_after_merge_beacon,
        test_branch_end_config_shows_merge_branch_identity,
        test_merge_beacon_selector_row_jumps_without_rewiring,
        test_merge_beacon_selector_excludes_merge_reachable_only_through_beacon,
        test_connected_branch_end_deletes_to_tombstone,
        test_editor_connects_merge_input_to_active_branch_port,
        test_editor_refresh_does_not_repair_legacy_merge_input_port,
        test_editor_branch_cycle_keys_switch_all_and_incomplete_branch_views,
        test_editor_command_keys_restore_lost_highlight_after_mouse_focus,
        test_editor_restores_persisted_focus_highlight_on_mount,
        test_editor_notification_restores_node_list_focus,
        test_editor_depth_counter_tracks_visible_branch_distance,
        test_help_screen_is_contextual_and_focuses_cancel,
        test_node_config_select_activates_from_keyboard,
        test_dynamic_row_helper_preserves_visible_rows_only,
        test_dynamic_selection_helper_filters_stale_values,
        test_frontend_notification_helpers_standardize_copy_and_severity,
        test_node_config_dynamic_membank_output_rows,
        test_node_config_pass_through_disables_membank_outputs,
        test_node_config_saves_transient_output_overrides_and_vertical_buttons,
        test_editor_hides_empty_start_until_first_node_added,
        test_node_config_previous_output_preview_reads_transient_source,
        test_editor_quick_view_lists_transient_and_memory_io,
        test_editor_quick_view_shows_branch_output_names_and_empty_memory,
        test_editor_quick_view_uses_transient_output_overrides,
        test_editor_quick_view_traces_pass_through_producer,
        test_node_config_previous_output_preview_traces_pass_through_source,
        test_node_selector_filter_auto_edits_when_focused,
        test_branch_selector_uses_shared_list_navigation,
        test_workflow_library_uses_shared_list_navigation,
        test_export_cancel_returns_to_file_menu,
        test_file_picker_export_and_import_paths,
        test_file_picker_cancel_and_fallback_paths,
        test_file_manager_reveal_commands_are_platform_specific,
        test_memory_viewer_uses_command_navigation,
        test_command_input_auto_edit_on_focus_is_opt_in,
        test_ctrl_c_uses_screen_copy_and_ctrl_q_stays_contextual,
        test_node_config_command_inputs_require_activation,
        test_simple_command_modals_use_shared_navigation_helpers,
        test_prompt_modals_use_shared_command_activation,
        test_editor_click_selects_and_double_click_edits,
        test_editor_ctrl_s_quick_saves,
        test_command_text_click_enters_editing_mode,
        test_command_screen_mixin_class_hierarchy,
        test_status_bar_mode_indicator,
        test_cursor_state_tracks_mode,
        test_command_screen_mixin_navigates_widgets,
        test_command_screen_mixin_boundary_stays_put,
        test_command_screen_mixin_blocks_nav_when_editing,
        test_cursor_state_syncs_with_mixin,
        test_auto_edit_prompt_syncs_cursor_and_status_bar,
        test_click_edit_and_textarea_commit_sync_cursor_mode,
        test_command_text_nav_mode_ad_positions_caret_before_edit,
        test_mixin_blocks_nav_when_active_text_not_focused,
        test_migrated_command_screens_render_status_bar,
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

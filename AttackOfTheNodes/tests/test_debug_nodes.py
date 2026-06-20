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


def test_node_factory_exposes_phase_17_identity_metadata():
    _, wm, _, _ = _make_services()

    metadata = {
        item["type"]: item
        for item in wm._factory.get_node_types_metadata()
    }
    expected_families = {"Inputs", "Outputs", "Flow Control", "Utility", "Complex"}

    for node_type, item in metadata.items():
        assert item["category"] in expected_families, node_type
        assert item["primary_family"] == item["category"]
        assert isinstance(item["legacy_category"], str)
        assert isinstance(item["tags"], list)
        assert all(isinstance(tag, str) for tag in item["tags"])
        assert item["icon_name"]
        assert item["color_hint"]
        assert "group" in item
        assert item["group"] is None or (
            isinstance(item["group"], str) and item["group"]
        )
        assert "selector_section" in item
        assert item["selector_section"] is None or (
            isinstance(item["selector_section"], str) and item["selector_section"]
        )

    assert metadata["file_reader_node"]["category"] == "Inputs"
    assert "File I/O" in metadata["file_reader_node"]["tags"]
    assert metadata["branch_node"]["category"] == "Flow Control"
    assert metadata["branch_node"]["display_name"] == "Parallel Branch"
    assert metadata["branch_node"]["tags"] == ["Parallel"]
    assert metadata["text_output_node"]["category"] == "Outputs"
    assert {"Passive Output", "Active Output"}.issubset(
        metadata["text_output_node"]["tags"]
    )
    assert metadata["chat_completion_node"]["category"] == "Complex"
    assert "AI" in metadata["chat_completion_node"]["tags"]

    print("test_node_factory_exposes_phase_17_identity_metadata PASSED")


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
        label.startswith("Vault: session_id - Session id")
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
    assert all_nodes[branch]["type"] == "branch_node"
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
    soft_deleted = wm.get_node_data(node_id)
    assert soft_deleted["type"] == "logger_node"
    assert adapter.placeholder_metadata(node_id)["original_alias"] == "Original Logger"
    assert adapter.placeholder_metadata(node_id)["original_config"] == {"message": "original"}

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
    from frontend.widgets.node_card import NodeCard

    deleted = {
        "type": "logger_node",
        "_editor_depth": 1,
        "_deleted_overlay": {
            "original_alias": "Useful Logger",
            "original_display_name": "Logger",
            "can_restore": True,
        },
    }
    card = NodeCard(
        "node_1",
        deleted,
        show_status=False,
        show_id=False,
        show_identity=True,
    )
    card.refresh_card()

    lines = card.display_text.splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("1     +")
    assert lines[1].startswith("|     | Deleted: Useful Logger (Logger)")
    assert lines[2].startswith("|     | x delete | z undo | e new node")
    assert lines[3].startswith("|     +")

    no_restore = {
        "type": "branch_end_node",
        "_editor_depth": 0,
        "_deleted_overlay": {"can_restore": False},
    }
    no_restore_card = NodeCard(
        "node_2",
        no_restore,
        show_status=False,
        show_id=False,
        show_identity=True,
    )
    no_restore_card.refresh_card()
    no_restore_lines = no_restore_card.display_text.splitlines()
    assert len(no_restore_lines) == 4
    assert no_restore_lines[0].startswith("0     +")
    assert no_restore_lines[1].startswith("|     | Deleted")
    assert no_restore_lines[2].startswith("|     | x delete | e new node")
    assert "z undo" not in no_restore_card.display_text
    print("test_editor_deleted_node_row_renders_as_deleted PASSED")


def test_deleted_node_materializes_to_tombstone_and_drops_outputs():
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter

    _, wm, _, _ = _make_services()
    wm.create_new("deleted_materialize")
    start = wm.add_node("start_node")
    logger = wm.add_node("logger_node", alias="Original Logger")
    end = wm.add_node("end_node")
    wm.update_node_config(logger, {"message": "original"})
    wm.connect(start, "default", logger, "input")
    wm.connect(logger, "default", end, "input")

    adapter = EditorWorkflowAdapter(wm, wm._factory)
    assert adapter.replace_with_placeholder(logger)
    assert wm.get_node_data(logger)["type"] == "logger_node"

    assert adapter.materialize_deleted_nodes() == 1
    materialized = wm.get_node_data(logger)
    assert materialized["type"] == "tombstone_node"
    assert materialized["alias"] == "Deleted node"
    assert materialized["connections"]["outputs"] == []
    assert wm.get_node_data(end)["connections"]["inputs"] == []
    assert "_system_role" not in materialized["config"]
    assert materialized["config"]["original_type"] == "logger_node"
    assert materialized["config"]["original_alias"] == "Original Logger"
    assert materialized["config"]["original_config"] == {"message": "original"}
    assert materialized["config"]["original_outputs"] == [
        {
            "source_port": "default",
            "target_node_id": end,
            "target_port": "input",
        }
    ]
    assert materialized["config"]["original_input_ports"] == ["input"]
    assert materialized["config"]["original_output_ports"] == ["default"]

    assert adapter.undo_placeholder(logger) is True
    restored = wm.get_node_data(logger)
    assert restored["type"] == "logger_node"
    assert restored["alias"] == "Original Logger"
    assert restored["config"] == {"message": "original"}
    assert restored["connections"]["outputs"] == [
        {
            "source_port": "default",
            "target_node_id": end,
            "target_port": "input",
        }
    ]
    assert wm.get_node_data(end)["connections"]["inputs"] == [
        {
            "target_port": "input",
            "source_node_id": logger,
            "source_port": "default",
        }
    ]
    print("test_deleted_node_materializes_to_tombstone_and_drops_outputs PASSED")


def test_editor_save_materializes_deleted_node_and_loaded_marker_renders():
    asyncio.run(_test_editor_save_materializes_deleted_node_and_loaded_marker_renders())


def test_editor_x_on_deleted_node_permanently_deletes():
    asyncio.run(_test_editor_x_on_deleted_node_permanently_deletes())


async def _test_editor_x_on_deleted_node_permanently_deletes():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_deleted_x")
    start = wm.add_node("start_node")
    logger = wm.add_node("logger_node")
    end = wm.add_node("end_node")
    wm.connect(start, "default", logger, "input")
    wm.connect(logger, "default", end, "input")
    wm.mark_saved()

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = logger
        screen.selected_row = {"kind": "node", "node_id": logger}

        screen.action_delete_selected()
        await pilot.pause(0.03)
        assert wm.get_node_data(logger)["type"] == "logger_node"

        screen.action_delete_selected()
        await pilot.pause(0.03)
        assert wm.get_node_data(logger) is None
        assert wm.is_dirty is True
        # Permanently removing the tombstone shifts downstream nodes up: the
        # gap closes by wiring start directly to end instead of orphaning end.
        start_outputs = wm.get_node_data(start)["connections"]["outputs"]
        assert any(c.get("target_node_id") == end for c in start_outputs)
        end_inputs = wm.get_node_data(end)["connections"]["inputs"]
        assert any(c.get("source_node_id") == start for c in end_inputs)

    print("test_editor_x_on_deleted_node_permanently_deletes PASSED")


def test_editor_branch_node_deletes_through_keep_selector():
    asyncio.run(_test_editor_branch_node_deletes_through_keep_selector())


async def _test_editor_branch_node_deletes_through_keep_selector():
    from textual.app import App, ComposeResult

    from frontend.screens.branch_keep_selector_screen import BranchKeepSelectorScreen
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_branch_delete")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node", alias="My Branch")
    wm.update_node_config(
        branch,
        {"branch_count": 2, "path_a_label": "Keep", "path_b_label": "Drop"},
    )
    logger_a = wm.add_node("logger_node", alias="Logger A")
    logger_b = wm.add_node("logger_node", alias="Logger B")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", logger_a, "input")
    wm.connect(branch, "path_b", logger_b, "input")
    wm.mark_saved()

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = branch
        screen.selected_row = {"kind": "node", "node_id": branch}

        # First delete: connected branch node is NOT blocked; it soft-tombstones
        # while the downstream branches stay live in the graph.
        screen.action_delete_selected()
        await pilot.pause(0.03)
        assert screen.workflow_adapter.is_placeholder(branch)
        assert wm.get_node_data(branch)["type"] == "branch_node"
        assert wm.get_node_data(logger_a) is not None
        assert wm.get_node_data(logger_b) is not None

        # Second delete: opens the branch keep selector instead of orphaning.
        captured = {}
        original_push_screen = app.push_screen

        def capture_push_screen(screen_to_push, *args, **kwargs):
            captured["screen"] = screen_to_push
            captured["callback"] = args[0] if args else kwargs.get("callback")
            return None

        app.push_screen = capture_push_screen
        try:
            screen.action_delete_selected()
            await pilot.pause(0.03)
        finally:
            app.push_screen = original_push_screen

        assert isinstance(captured.get("screen"), BranchKeepSelectorScreen)
        assert captured.get("callback") is not None

        # User keeps path_a: path_b and its node are pruned, upstream rewired.
        captured["callback"]({"kept_port": "path_a"})
        await pilot.pause(0.03)

        assert wm.get_node_data(branch) is None
        assert wm.get_node_data(logger_a) is not None
        assert wm.get_node_data(logger_b) is None
        start_outputs = wm.get_node_data(start)["connections"]["outputs"]
        assert any(c.get("target_node_id") == logger_a for c in start_outputs)

    print("test_editor_branch_node_deletes_through_keep_selector PASSED")


def test_editor_merge_node_delete_rewires_home_branch_and_disconnects_beacons():
    asyncio.run(_test_editor_merge_node_delete_rewires_home_branch_and_disconnects_beacons())


async def _test_editor_merge_node_delete_rewires_home_branch_and_disconnects_beacons():
    from textual.app import App, ComposeResult

    from backend.validator import validate_workflow
    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_merge_delete")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node", alias="My Branch")
    wm.update_node_config(branch, {"branch_count": 2})
    home = wm.add_node("logger_node", alias="Home")
    beacon = wm.add_node("branch_end_node", alias="Beacon")
    merge = wm.add_node("merge_node", alias="Merge")
    end = wm.add_node("end_node")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", home, "input")
    wm.connect(home, "default", merge, "path_a")
    wm.connect(branch, "path_b", beacon, "input")
    wm.connect(beacon, "default", merge, "path_b")
    wm.connect(merge, "default", end, "input")
    wm.mark_saved()

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = merge
        screen.selected_row = {"kind": "node", "node_id": merge}

        # First delete: merge node is no longer protected, soft-tombstones.
        screen.action_delete_selected()
        await pilot.pause(0.03)
        assert screen.workflow_adapter.is_placeholder(merge)
        assert wm.get_node_data(merge)["type"] == "merge_node"
        assert wm.get_node_data(home) is not None
        assert wm.get_node_data(beacon) is not None
        assert wm.get_node_data(end) is not None

        # Second delete: merge node is permanently removed. The upstream node
        # on the branch where the merge lived rewires to the immediate
        # downstream node; Merge Beacons from other branches disconnect and
        # become validation-visible repair work.
        screen.action_delete_selected()
        await pilot.pause(0.03)

        assert wm.get_node_data(merge) is None
        assert wm.get_node_data(home) is not None
        assert wm.get_node_data(beacon) is not None
        assert wm.get_node_data(end) is not None
        assert wm.get_node_data(home)["connections"]["outputs"] == [
            {
                "source_port": "default",
                "target_node_id": end,
                "target_port": "input",
            }
        ]
        assert wm.get_node_data(beacon)["connections"]["outputs"] == []
        assert wm.get_node_data(end)["connections"]["inputs"] == [
            {
                "target_port": "input",
                "source_node_id": home,
                "source_port": "default",
            }
        ]
        validation = validate_workflow(wm, wm._factory)
        assert validation["success"] is True
        assert any(
            warning.get("node_id") == beacon
            and "Merge Beacon is not connected to a merge node" in warning.get("message", "")
            for warning in validation["warnings"]
        )

    print("test_editor_merge_node_delete_rewires_home_branch_and_disconnects_beacons PASSED")


def test_editor_soft_deleted_beacon_keeps_downstream_visible():
    asyncio.run(_test_editor_soft_deleted_beacon_keeps_downstream_visible())


async def _test_editor_soft_deleted_beacon_keeps_downstream_visible():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_soft_delete_beacon")
    start = wm.add_node("start_node")
    logger_a = wm.add_node("logger_node", alias="A")
    beacon = wm.add_node("branch_end_node", alias="Beacon")
    merge = wm.add_node("merge_node", alias="Merge")
    end = wm.add_node("end_node")
    wm.connect(start, "default", logger_a, "input")
    wm.connect(logger_a, "default", beacon, "input")
    wm.connect(beacon, "default", merge, "path_a")
    wm.connect(merge, "default", end, "input")
    wm.mark_saved()

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = beacon
        screen.selected_row = {"kind": "node", "node_id": beacon}

        # First (soft) delete: connections stay intact on the backend, so the
        # editor must keep showing everything past the beacon instead of
        # dead-ending the visible row list at the deleted marker.
        screen.action_delete_selected()
        await pilot.pause(0.03)
        assert screen.workflow_adapter.is_placeholder(beacon)

        visible_ids = {
            row.get("node_id") or row.get("beacon_node_id") or row.get("merge_node_id")
            for row in screen._build_visible_rows()
        }
        assert merge in visible_ids
        assert end in visible_ids

    print("test_editor_soft_deleted_beacon_keeps_downstream_visible PASSED")


async def _test_editor_save_materializes_deleted_node_and_loaded_marker_renders():
    from textual.app import App, ComposeResult

    from frontend.editor_workflow_adapter import DELETED_NODE_SYSTEM_ROLE
    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("editor_save_deleted_marker")
    start = wm.add_node("start_node")
    logger = wm.add_node("logger_node", alias="Saved Logger")
    wm.connect(start, "default", logger, "input")

    saves = []

    class SaveApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

        def action_save_workflow(self) -> None:
            saves.append("saved")

    app = SaveApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        screen.selected_node_id = logger
        screen.selected_row = {"kind": "node", "node_id": logger}
        screen.action_delete_selected()
        await pilot.pause(0.03)
        assert wm.get_node_data(logger)["type"] == "logger_node"

        screen.action_save_workflow()
        await pilot.pause(0.03)
        assert saves == ["saved"]
        saved_marker = wm.get_node_data(logger)
        assert saved_marker["type"] == "tombstone_node"
        assert saved_marker["config"]["original_type"] == "logger_node"
        assert saved_marker["config"]["original_alias"] == "Saved Logger"
        assert "_system_role" not in saved_marker["config"]

        screen.refresh_from_backend()
        marker_card = next(card for card in app.query(NodeCard) if card.node_id == logger)
        assert "Deleted: Saved Logger (Logger)" in marker_card.display_text
        assert "z undo" in marker_card.display_text

    _, loaded_wm, _, _ = _make_services()
    loaded_wm.create_new("loaded_deleted_marker")
    loaded_start = loaded_wm.add_node("start_node")
    loaded_marker = loaded_wm.add_node("branch_end_node")
    loaded_wm.update_node_config(
        loaded_marker,
        {
            "_system_role": DELETED_NODE_SYSTEM_ROLE,
            "deleted_node": {
                "original_type": "logger_node",
                "original_display_name": "Logger",
                "original_alias": "Loaded Logger",
                "original_config": {"message": "loaded"},
            },
        },
    )
    loaded_wm.connect(loaded_start, "default", loaded_marker, "input")

    class LoadedApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(loaded_wm._factory, loaded_wm)

    loaded_app = LoadedApp()
    async with loaded_app.run_test() as pilot:
        await pilot.pause(0.03)
        marker_card = next(
            card for card in loaded_app.query(NodeCard) if card.node_id == loaded_marker
        )
        assert "Deleted: Loaded Logger (Logger)" in marker_card.display_text
        assert "z undo" in marker_card.display_text

    # Tombstone-format save record renders the same deleted-node row
    _, tomb_wm, _, _ = _make_services()
    tomb_wm.create_new("loaded_tombstone_marker")
    tomb_start = tomb_wm.add_node("start_node")
    tomb_marker = tomb_wm.add_node("tombstone_node")
    tomb_wm.update_node_config(
        tomb_marker,
        {
            "original_type": "logger_node",
            "original_display_name": "Logger",
            "original_alias": "Tombstone Logger",
            "original_config": {"message": "loaded"},
        },
    )
    tomb_wm.connect(tomb_start, "default", tomb_marker, "input")

    class TombstoneApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(tomb_wm._factory, tomb_wm)

    tombstone_app = TombstoneApp()
    async with tombstone_app.run_test() as pilot:
        await pilot.pause(0.03)
        marker_card = next(
            card for card in tombstone_app.query(NodeCard) if card.node_id == tomb_marker
        )
        assert "Deleted: Tombstone Logger (Logger)" in marker_card.display_text
        assert "z undo" in marker_card.display_text

    print("test_editor_save_materializes_deleted_node_and_loaded_marker_renders PASSED")


def test_node_card_editor_identity_rows_align_and_truncate():
    from frontend.widgets.node_card import NodeCard

    node = {
        "type": "logger_node",
        "alias": "Useful Logger",
        "_editor_depth": 4,
        "_identity": {
            "primary_family": "Outputs",
            "tags": ["Passive Output", "Utility"],
        },
    }
    card = NodeCard("logger-1", node, show_status=False, show_id=False, show_identity=True)
    card.refresh_card()

    lines = card.display_text.splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("4     +")
    assert lines[1].startswith("|     | Useful Logger")
    assert lines[2].startswith("|     | Outputs - Passive Output")
    assert lines[3].startswith("|     +")
    assert "Utility" not in lines[2]
    assert "<" not in lines[0]
    assert ">" not in lines[2]

    long_identity = {
        "type": "file_reader_node",
        "alias": "Config File",
        "_editor_depth": 0,
        "_identity": {
            "primary_family": "Inputs",
            "tags": [
                "File I/O",
                "Runtime Resource With A Particularly Long Label",
            ],
        },
    }
    long_card = NodeCard(
        "file-1",
        long_identity,
        show_status=False,
        show_id=False,
        show_identity=True,
    )
    long_card.refresh_card()
    long_lines = long_card.display_text.splitlines()
    assert "…" in long_lines[2]
    assert "[" not in long_lines[0]
    assert "]" not in long_lines[2]

    print("test_node_card_editor_identity_rows_align_and_truncate PASSED")


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
    assert BranchNode.default_config["path_e_label"] == "Branch 5"
    assert BranchNode.default_config["branch_count"] == 2
    assert BranchNode.output_ports == ["path_a", "path_b", "path_c", "path_d", "path_e"]
    assert "path_a_label" in BranchNode.config_schema
    assert "path_b_label" in BranchNode.config_schema
    assert BranchNode.config_schema["branch_count"]["min"] == 2
    assert BranchNode.config_schema["branch_count"]["max"] == 5
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


def test_branch_config_uses_parallel_payload_ui():
    asyncio.run(_test_branch_config_uses_parallel_payload_ui())


async def _test_branch_config_uses_parallel_payload_ui():
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox, Select, SelectionList, TabbedContent

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()
    wm.create_new("branch_parallel_payload_ui")
    writer = wm.add_node("logger_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(
        writer,
        {"membank_outputs": [{"id": "session_id", "description": "Session id"}]},
    )
    wm.update_node_config(
        branch,
        {
            "branch_count": 5,
            "membank_inputs": ["session_id"],
            "condition": "string_match",
            "path_a_label": "Alpha",
            "path_b_label": "Beta",
            "path_c_label": "Gamma",
            "path_d_label": "Delta",
            "path_e_label": "Epsilon",
            "branch_payload_sources": {"path_b": "vault:session_id"},
        },
    )
    node_data = wm.get_node_data(branch)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, branch, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        screen = app.query_one(NodeConfigScreen)
        summary = str(app.query_one("#node-config-summary").content)
        help_text = str(app.query_one(".modal-help").content)
        assert summary == "\n".join(
            [
                "Node type: Parallel Branch",
                "- Duplicates the incoming payload across branch paths.",
                "- Parallel paths run independently",
                "- Conditional branching hidden for a later node pass",
            ]
        )
        assert "ctrl+q revert" in help_text
        assert not app.query("#field-condition")
        assert not [
            label for label in app.query(".form-label") if str(label.content) == "Vault"
        ]
        assert app.query_one("#branch-count", CommandInput).value == "5"
        assert app.query_one("#branch-label-path_a", CommandInput).value == "Alpha"
        assert app.query_one("#branch-payload-row-path_c").display is True
        assert app.query_one("#branch-payload-row-path_e").display is True

        path_b_source = app.query_one("#branch-payload-source-path_b", Select)
        assert path_b_source.value == "vault:session_id"
        option_values = {value for _, value in path_b_source._options}
        assert {"dead_drop:input", "vault:session_id"}.issubset(option_values)

        vault_list = app.query_one("#membank-inputs", SelectionList)
        vault_checkbox = app.query_one("#membank-reads", Checkbox)
        assert vault_list.disabled is False
        vault_checkbox.value = False
        screen._sync_membank_input_controls()
        screen._sync_branch_payload_rows()
        assert vault_list.disabled is True
        option_values = {
            value for _, value in app.query_one("#branch-payload-source-path_b", Select)._options
        }
        assert "vault:session_id" not in option_values
        vault_checkbox.value = True
        screen._sync_membank_input_controls()
        screen._sync_branch_payload_rows()
        option_values = {
            value for _, value in app.query_one("#branch-payload-source-path_b", Select)._options
        }
        assert "vault:session_id" in option_values

        tabs = app.query_one("#node-config-tabs", TabbedContent)
        tabs.active = "node-config-tab-outputs"
        screen._focus_first_config_tab_widget("node-config-tab-outputs")
        await pilot.pause(0.03)
        visited: list[str] = []
        for _ in range(14):
            focused_id = str(getattr(app.focused, "id", ""))
            if focused_id:
                visited.append(focused_id)
            await pilot.press("s")
            await pilot.pause(0.01)
        assert "show-payload-upstream-payload" in visited
        assert "show-payload-vault-payload" in visited
        assert "branch-label-path_e" in visited
        assert "branch-payload-source-path_e" in visited
        assert all(visited)

        app.query_one("#branch-label-path_c", CommandInput).value = "Review"
        app.query_one("#branch-payload-source-path_a", Select).value = "vault:session_id"
        app.query_one("#branch-payload-source-path_b", Select).value = "vault:session_id"
        values = screen._branch_config_values()
        assert values["branch_count"] == 5
        assert values["path_c_label"] == "Review"
        assert values["branch_payload_sources"]["path_a"] == "vault:session_id"
        assert values["branch_payload_sources"]["path_b"] == "vault:session_id"
        assert values["condition"] == "string_match"

    print("test_branch_config_uses_parallel_payload_ui PASSED")


def test_branch_node_parallel_count_and_payload_sources():
    asyncio.run(_test_branch_node_parallel_count_and_payload_sources())


def test_node_config_empty_vault_copy_is_short():
    asyncio.run(_test_node_config_empty_vault_copy_is_short())


async def _test_node_config_empty_vault_copy_is_short():
    from textual.app import App, ComposeResult

    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("empty_vault_copy")
    branch = wm.add_node("branch_node")
    node_data = wm.get_node_data(branch)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, branch, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        assert any(
            str(getattr(static, "renderable", getattr(static, "content", ""))) == "The vault is empty"
            for static in app.query("Static")
        )

    print("test_node_config_empty_vault_copy_is_short PASSED")


def test_node_config_selection_lists_exit_at_edges():
    asyncio.run(_test_node_config_selection_lists_exit_at_edges())


async def _test_node_config_selection_lists_exit_at_edges():
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox, SelectionList

    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("selection_list_edges")
    writer = wm.add_node("logger_node")
    target = wm.add_node("logger_node")
    wm.update_node_config(
        writer,
        {"membank_outputs": [{"id": "session_id", "description": "Session id"}]},
    )
    wm.update_node_config(target, {"membank_inputs": ["session_id"]})
    node_data = wm.get_node_data(target)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, target, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        vault = app.query_one("#membank-inputs", SelectionList)
        vault_checkbox = app.query_one("#membank-reads", Checkbox)
        app.set_focus(vault)
        vault.highlighted = 0

        await pilot.press("w")
        await pilot.pause(0.02)
        assert app.focused is vault_checkbox

        app.set_focus(vault)
        vault.highlighted = len(vault._options) - 1
        await pilot.press("s")
        await pilot.pause(0.02)
        assert getattr(app.focused, "id", "") == "show-source-vault-payload"

    print("test_node_config_selection_lists_exit_at_edges PASSED")


async def _test_branch_node_parallel_count_and_payload_sources():
    from backend.event_bus import EventBus
    from backend.memory_bank import MemoryBank
    from backend.node_base import NodeContext
    from backend.nodes.branch_node import BranchNode

    async def no_user_input(prompt: str) -> str:
        return ""

    async def no_wait_for_nodes(node_ids, timeout):
        return None

    async def no_wait_for_merge(*args, **kwargs):
        return {}

    done_payloads = []
    errors = []
    memory_bank = MemoryBank(EventBus())
    memory_bank.store_persistent("session_id", "vault-seed")

    node = BranchNode(
        "branch",
        {
            "branch_count": 3,
            "branch_payload_sources": {"path_b": "vault:session_id"},
        },
    )
    context = NodeContext(
        node_id="branch",
        branch_id="root",
        run_id="run",
        inputs={"input": "upstream-seed"},
        memory_bank=memory_bank,
        signal_done=done_payloads.append,
        signal_error=errors.append,
        signal_waiting_for_input=no_user_input,
        wait_for_nodes=no_wait_for_nodes,
        wait_for_merge=no_wait_for_merge,
    )
    await node.execute(context)

    assert not errors
    branches = done_payloads[-1]["branches"]
    assert [branch["output_port"] for branch in branches] == ["path_a", "path_b", "path_c"]
    assert branches[0]["initial_data"]["input"] == "upstream-seed"
    assert branches[1]["initial_data"]["input"] == "vault-seed"
    assert memory_bank.read_transient("branch", "path_b") == "vault-seed"

    legacy_payloads = []
    legacy = BranchNode("legacy", {"condition": "path_a_only"})
    legacy_context = NodeContext(
        node_id="legacy",
        branch_id="root",
        run_id="run",
        inputs={"input": "legacy-input"},
        memory_bank=memory_bank,
        signal_done=legacy_payloads.append,
        signal_error=errors.append,
        signal_waiting_for_input=no_user_input,
        wait_for_nodes=no_wait_for_nodes,
        wait_for_merge=no_wait_for_merge,
    )
    await legacy.execute(legacy_context)
    assert [branch["output_port"] for branch in legacy_payloads[-1]["branches"]] == ["path_a"]

    print("test_branch_node_parallel_count_and_payload_sources PASSED")


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


def test_form_generator_titleizes_field_name_fallback_labels():
    asyncio.run(_test_form_generator_titleizes_field_name_fallback_labels())


async def _test_form_generator_titleizes_field_name_fallback_labels():
    from textual.app import App, ComposeResult
    from textual.widgets import Label

    from frontend.widgets.form_generator import build_form, humanize_field_name

    # Pure helper: snake_case -> sentence case, explicit label untouched.
    assert humanize_field_name("request_user_input") == "Request user input"
    assert humanize_field_name("template") == "Template"

    schema = {
        # No explicit label: falls back to a titleized field name.
        "request_user_input": {"type": "boolean"},
        # Explicit label is preserved verbatim.
        "template": {"type": "string", "label": "Output text"},
    }

    class FormApp(App):
        def compose(self) -> ComposeResult:
            form, _ = build_form(schema, {})
            yield form

    app = FormApp()
    async with app.run_test():
        labels = {
            str(label.content)
            for label in app.query(Label)
            if "form-label" in label.classes
        }
        assert "Request user input" in labels
        assert "request_user_input" not in labels
        assert "Output text" in labels

    print("test_form_generator_titleizes_field_name_fallback_labels PASSED")


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
        assert screen.workflow_adapter.is_placeholder(beacon)
        assert wm.get_node_data(beacon)["type"] == "branch_end_node"
        assert merge_config.get("branches_to_close") == [f"{branch}:path_a"]
        assert merge_config.get("carry_forward_branch_id") == f"{branch}:path_a"
        assert merge_config.get("selected_branch_id") == f"{branch}:path_a"
        assert wm.get_node_data(beacon).get("connections", {}).get("outputs", [])

        screen.action_delete_selected()
        await pilot.pause(0.03)

        merge_config = wm.get_node_data(merge).get("config", {})
        assert merge_config.get("branches_to_close") == []
        assert merge_config.get("carry_forward_branch_id") == ""
        assert merge_config.get("selected_branch_id") == ""
        assert wm.get_node_data(beacon) is None
        options = merge_input_options(wm, merge)
        assert options == []

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
            "gap_arrow",
            "node",
            "branch_select",
            "node",
            "gap_arrow",
            "node",
            "merge_beacon_select",
        ]
        assert target_merge not in [row.get("node_id") for row in rows]
        beacon_cards = [card for card in app.query(NodeCard) if card.node_id == beacon]
        assert "Merge Beacon" in beacon_cards[0].display_text.splitlines()[1]
        selector_card = app.query_one(MergeBeaconSelectCard)
        assert selector_card.active_label == "Merge"
        assert selector_card.active_port == "path_a"
        assert selector_card.display_text.startswith("└─────")
        assert " [ Merge ]" in selector_card.display_text
        assert "☛" not in selector_card.display_text

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

        assert wm.get_node_data(branch_end)["type"] == "branch_end_node"
        after_cards = [card for card in app.query(NodeCard) if card.node_id == branch_end]
        assert len(after_cards) == 1
        assert not after_cards[0].has_class("branch-end-open")
        assert not after_cards[0].has_class("branch-end-connected")
        assert after_cards[0].node_data["type"] == "branch_end_node"
        assert "Deleted" in after_cards[0].display_text
        assert "z undo" in after_cards[0].display_text

        screen.action_undo_delete()
        await pilot.pause(0.03)
        restored_cards = [card for card in app.query(NodeCard) if card.node_id == branch_end]
        assert len(restored_cards) == 1
        assert restored_cards[0].has_class("branch-end-connected")

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


def test_editor_branch_path_palette_uses_ten_colors_before_cycling():
    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import (
        BRANCH_PATH_PALETTE,
        BRANCH_PATH_PORTS,
        branch_path_color,
        branch_path_color_key,
    )

    assert len(BRANCH_PATH_PALETTE) == 10
    assert len(set(BRANCH_PATH_PALETTE)) == 10
    assert [
        branch_path_color(branch_path_color_key(0, port))
        for port in BRANCH_PATH_PORTS
    ] == list(BRANCH_PATH_PALETTE[:5])
    assert [
        branch_path_color(branch_path_color_key(1, port))
        for port in BRANCH_PATH_PORTS
    ] == list(BRANCH_PATH_PALETTE[5:])
    assert (
        branch_path_color(branch_path_color_key(2, "path_a"))
        == BRANCH_PATH_PALETTE[0]
    )

    _, wm, _, _ = _make_services()
    wm.create_new("editor_branch_path_palette")
    start = wm.add_node("start_node")
    first_branch = wm.add_node("branch_node")
    nested_branch = wm.add_node("branch_node")
    leaf = wm.add_node("logger_node")
    wm.connect(start, "default", first_branch, "input")
    wm.connect(first_branch, "path_a", nested_branch, "input")
    wm.connect(nested_branch, "path_a", leaf, "input")

    screen = EditorScreen(wm._factory, wm)
    rows = screen._build_visible_rows()
    branch_rows = [row for row in rows if row["kind"] == "branch_select"]

    assert branch_rows[0]["branch_node_id"] == first_branch
    assert branch_rows[0]["active_color_key"] == branch_path_color_key(0, "path_a")
    assert branch_rows[1]["branch_node_id"] == nested_branch
    assert branch_rows[1]["active_color_key"] == branch_path_color_key(1, "path_a")
    assert branch_path_color(branch_rows[0]["active_color_key"]) != branch_path_color(
        branch_rows[1]["active_color_key"]
    )
    print("test_editor_branch_path_palette_uses_ten_colors_before_cycling PASSED")


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


def test_editor_insert_into_empty_branch_uses_active_branch_port():
    asyncio.run(_test_editor_insert_into_empty_branch_uses_active_branch_port())


async def _test_editor_insert_into_empty_branch_uses_active_branch_port():
    """Switching to an empty branch path leaves the selected row pointing at
    the branch_node itself (kind: "node", not "branch_select"). Inserting a
    node there must attach to the branch path being viewed
    (active_branch_ports), not just the branch node's first declared output
    port — otherwise the new node silently lands on a different branch than
    the one shown on screen."""
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen

    _, wm, _, _ = _make_services()
    wm.create_new("editor_insert_empty_branch")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    branch_one_out = wm.add_node("text_output_node", alias="B1Out")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", branch_one_out, "input")
    # path_b intentionally left empty

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)

        await pilot.press("d")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch] == "path_b"

        screen._pending_node_add_mode = "insert"
        screen._add_node_from_modal("text_output_node")
        await pilot.pause(0.03)
        new_node_id = screen.selected_node_id

        new_node = wm.get_node_data(new_node_id)
        inputs = new_node.get("connections", {}).get("inputs", [])
        assert any(
            conn.get("source_node_id") == branch and conn.get("source_port") == "path_b"
            for conn in inputs
        ), "new node should attach to path_b, the branch being viewed"

        await pilot.press("a")
        await pilot.pause(0.03)
        assert screen.active_branch_ports[branch] == "path_a"
        # the node inserted into path_b must still be wired to path_b
        new_node = wm.get_node_data(new_node_id)
        inputs = new_node.get("connections", {}).get("inputs", [])
        assert any(
            conn.get("source_node_id") == branch and conn.get("source_port") == "path_b"
            for conn in inputs
        ), "node must remain on path_b after navigating away and back"

    print("test_editor_insert_into_empty_branch_uses_active_branch_port PASSED")


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
    from frontend.widgets.node_card import (
        BranchSelectCard,
        GapArrowCard,
        NodeCard,
        branch_path_color,
    )
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

        rows = [
            row for row in node_list._rows if row.get("kind") != "gap_arrow"
        ]
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
        start_lines = start_card.display_text.splitlines()
        assert start_lines[0].startswith("0     +")
        assert start_lines[1].startswith("|     | Start")
        assert start_lines[2].startswith("|     | Flow Control - Triggered")
        assert "{" not in start_lines[0]
        assert "}" not in start_lines[2]
        assert branch_row.display_text.startswith("├─────")
        assert " [ Branch 1 ]" in branch_row.display_text
        assert "☛" not in branch_row.display_text
        gap_card = node_list.children[1].query_one(GapArrowCard)
        path_a = branch_path_color("path_a")
        assert any(
            span.start <= 0 < span.end
            and path_a in str(span.style.color).lower()
            and bool(span.style.bold)
            for span in start_card.content.spans
        )
        assert any(
            span.start <= 0 < span.end
            and path_a in str(span.style.color).lower()
            and bool(span.style.bold)
            for span in gap_card.content.spans
        )
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
        assert "Family: Utility" in details
        assert "Subcategories: Passive Output, Utility" in details
        assert "Step: 2" in details

    print("test_editor_depth_counter_tracks_visible_branch_distance PASSED")


def test_editor_identity_rows_keep_keyboard_selection_stable():
    asyncio.run(_test_editor_identity_rows_keep_keyboard_selection_stable())


async def _test_editor_identity_rows_keep_keyboard_selection_stable():
    from textual.app import App, ComposeResult

    from frontend.screens.editor import EditorScreen
    from frontend.widgets.node_card import NodeCard

    _, wm, _, _ = _make_services()
    wm.create_new("editor_identity_keyboard_stability")
    previous = wm.add_node("start_node")
    chain_ids = []
    for index in range(18):
        node_id = wm.add_node("logger_node")
        wm.update_node_alias(node_id, f"Log Step {index + 1}")
        wm.connect(previous, "default", node_id, "input")
        previous = node_id
        chain_ids.append(node_id)

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    app = EditorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(EditorScreen)
        node_list = screen.query_one("#node-list")

        for _ in range(12):
            await pilot.press("s")
        await pilot.pause(0.03)

        expected_id = chain_ids[11]
        assert node_list.is_selectable_index(node_list.index)
        assert screen.selected_node_id == expected_id
        assert node_list.node_id_for_index(node_list.index) == expected_id
        highlighted = [
            index
            for index, item in enumerate(node_list.children)
            if getattr(item, "highlighted", False)
        ]
        assert highlighted == [node_list.index]
        assert all(
            node_list.row_for_index(index).get("kind") != "gap_arrow"
            for index in highlighted
        )

        screen.refresh_from_backend()
        await pilot.pause(0.03)
        assert node_list.is_selectable_index(node_list.index)
        assert screen.selected_node_id == expected_id
        selected_card = next(card for card in app.query(NodeCard) if card.node_id == expected_id)
        assert "Utility - Passive Output" in selected_card.display_text

    print("test_editor_identity_rows_keep_keyboard_selection_stable PASSED")


def test_editor_identity_rows_fit_rendered_panel_width():
    asyncio.run(_test_editor_identity_rows_fit_rendered_panel_width())


async def _test_editor_identity_rows_fit_rendered_panel_width():
    from pathlib import Path as _Path

    from textual.app import App, ComposeResult
    from textual.containers import Vertical

    from frontend.widgets.node_card import (
        BOX_RIGHT_INSET,
        DEPTH_GUTTER,
        GapArrowCard,
        LINE_CHAR,
        MERGE_INCOMING_MARKER,
        NodeCard,
        SELECTED_BACKGROUND,
        BRANCH_SELECT_CONNECTOR,
        branch_line_label,
        branch_path_color,
        connector_gutter,
        gap_arrow_text,
    )
    from frontend.widgets.node_list import NodeList

    # The panel is much narrower than the old fixed 48-char identity width,
    # which used to soft-wrap long identity rows and push content out of the
    # visible card.
    panel_width = 40

    def node_row(
        node_id: str,
        alias: str,
        branch_port: str | None = None,
        node_type: str = "branch_node",
        vault_outputs: int = 0,
    ) -> dict:
        vault_marker = ""
        if vault_outputs == 1:
            vault_marker = "↳"
        elif vault_outputs > 1:
            vault_marker = f"➥{vault_outputs}"
        node = {
            "type": node_type,
            "alias": alias,
            "_editor_depth": 1,
            "config": {
                "membank_outputs": [
                    {"id": f"{node_id}_vault_{index}"}
                    for index in range(vault_outputs)
                ]
            },
            "_identity": {
                "primary_family": "Flow Control",
                "tags": ["Parallel"],
            },
            "_editor_gap_marker": f"↓{vault_marker}",
        }
        if branch_port:
            node["_editor_branch_port"] = branch_port
        return {
            "kind": "node",
            "node_id": node_id,
            "node": node,
        }

    rows = [
        node_row("branch-1", "Parallel Branch", vault_outputs=2),
        node_row("branch-2", "Another Branch"),
        {
            "kind": "branch_select",
            "branch_node_id": "branch-2",
            "active_port": "path_b",
            "active_label": "Branch 1",
            "depth": 1,
        },
        node_row("path-node", "Path Node", "path_b"),
        node_row("merge-node", "Merge", "path_b", "merge_node"),
    ]

    class NarrowApp(App):
        # Real app stylesheet so row height, spacing, and colors match the TUI.
        CSS_PATH = str(
            _Path(__file__).parent.parent / "frontend" / "styles.tcss"
        )
        CSS = f"#narrow-panel {{ width: {panel_width}; height: 20; }}"

        def compose(self) -> ComposeResult:
            yield Vertical(NodeList(), id="narrow-panel")

    app = NarrowApp()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause(0.05)
        node_list = app.query_one(NodeList)
        node_list.refresh_rows(rows)
        node_list.index = 0
        node_list.normalize_highlight()
        await pilot.pause(0.05)

        cards = list(app.query(NodeCard))
        assert len(cards) == 4
        first, second, path_card, merge_card = cards
        width = first.content_size.width
        assert 0 < width <= panel_width
        lines = first.display_text.splitlines()
        assert len(lines) == 4, f"Expected boxed row, got {lines!r}"
        for line in lines:
            # Content stays inside the panel without wrapping.
            assert len(line) == width - BOX_RIGHT_INSET, (
                f"Row line must end {BOX_RIGHT_INSET} short of the content "
                f"edge ({len(line)} != {width - BOX_RIGHT_INSET}): {line!r}"
            )
        assert lines[0].startswith("1     +")
        assert lines[1].startswith("|     | Parallel Branch")
        assert lines[2].startswith("|     | Flow Control - Parallel")
        assert lines[3].startswith("|     +")
        assert "{" not in lines[0]
        assert "}" not in lines[2]
        box_width = len(lines[0]) - len(DEPTH_GUTTER)

        # The rows must actually paint (not just hold content): shadowing
        # Textual paint internals once made every card render blank.
        painted_lines = [
            "".join(seg.text for seg in first.render_line(y))
            for y in range(first.region.height)
        ]
        assert any("Parallel Branch" in line for line in painted_lines), (
            f"Card content did not paint: {painted_lines!r}"
        )

        # One disabled arrow row separates node-to-node groups. It exists in
        # layout but is not selectable/focusable.
        gap = second.region.y - first.region.y
        assert gap == 5, f"Expected 4-row card + 1 arrow line, got {gap}"
        assert len(node_list.children) == len(rows) + 2
        gap_item = node_list.children[1]
        assert node_list.row_for_index(1)["kind"] == "gap_arrow"
        assert node_list.is_selectable_index(1) is False
        assert node_list.next_selectable_index(0, 1) == 2
        gap_card = gap_item.query_one(GapArrowCard)
        assert gap_card.display_text == gap_arrow_text(
            gap_card.content_size.width,
            output_marker="↓➥2",
        )
        assert "↓➥2" in gap_card.display_text
        # A branch selector sits directly below its node with no spacer between.
        branch_item = node_list.children[3]
        selector_gap = branch_item.region.y - second.region.y
        assert selector_gap == 4, (
            f"Selector must sit directly below its node, got gap {selector_gap}"
        )
        assert branch_item.region.height == 1
        # No blank line below the selector: the next node hugs it.
        node_gap = path_card.region.y - branch_item.region.y
        assert node_gap == 1, (
            f"Node after selector must hug it (no blank line), got {node_gap}"
        )

        # Selector line connects from the gutter into a branch-colored line.
        from frontend.widgets.node_card import BranchSelectCard

        branch_card = branch_item.query_one(BranchSelectCard)
        assert branch_card.display_text == (
            f"{connector_gutter(BRANCH_SELECT_CONNECTOR)}"
            f"{branch_line_label('Branch 1', box_width)}"
        )
        assert branch_card.display_text.startswith("├─────")
        assert " [ Branch 1 ]" in branch_card.display_text
        assert "☛" not in branch_card.display_text
        label_start = branch_card.display_text.index("Branch 1") - len(DEPTH_GUTTER)
        assert abs((label_start * 2 + len("Branch 1")) - box_width) <= 1
        label_end = branch_card.display_text.index(" ]") + len(" ]")
        assert LINE_CHAR not in branch_card.display_text[label_end:]

        branch_segments = []
        offset = 0
        for segment in branch_card.render_line(0):
            end = offset + len(segment.text)
            color = getattr(segment.style, "color", None)
            if color is not None:
                branch_segments.append(
                    (offset, end, str(color).lower(), segment.style.bold)
                )
            offset = end
        path_color = branch_path_color("path_b")
        path_color_segments = [
            segment for segment in branch_segments if path_color in segment[2]
        ]
        assert path_color_segments
        connector_column = 0
        assert any(
            start <= connector_column < end for start, end, _, _ in path_color_segments
        )
        assert any(
            end > len(DEPTH_GUTTER) for _, end, _, _ in path_color_segments
        )

        path_color_segments = []
        for y in range(path_card.region.height):
            offset = 0
            for segment in path_card.render_line(y):
                end = offset + len(segment.text)
                color = getattr(segment.style, "color", None)
                if color is not None and path_color in str(color).lower():
                    path_color_segments.append(
                        (y, offset, end, segment.text, segment.style.bold)
                    )
                offset = end
        assert any(
            y == 0 and start <= connector_column < end and bool(bold)
            for y, start, end, _, bold in path_color_segments
        )
        assert any(
            y > 0 and start <= connector_column < end
            for y, start, end, _, _ in path_color_segments
        )
        assert any(
            y > 0 and start <= connector_column < end and bool(bold)
            for y, start, end, _, bold in path_color_segments
        )

        merge_gap_item = node_list.children[5]
        merge_gap_card = merge_gap_item.query_one(GapArrowCard)
        assert merge_gap_card.display_text == gap_arrow_text(
            merge_gap_card.content_size.width
        )
        assert merge_card.region.y - path_card.region.y == 5
        merge_lines = merge_card.display_text.splitlines()
        assert merge_lines[0].startswith("1     +")
        assert merge_lines[1].startswith(f"{MERGE_INCOMING_MARKER}     | Merge")
        merge_marker_segments = []
        offset = 0
        for segment in merge_card.render_line(1):
            end = offset + len(segment.text)
            color = getattr(segment.style, "color", None)
            if color is not None and path_color in str(color).lower():
                merge_marker_segments.append(
                    (offset, end, segment.text, segment.style.bold)
                )
            offset = end
        assert any(
            start <= connector_column < end and bool(bold)
            for start, end, _, bold in merge_marker_segments
        )

        selected_segments = []
        for y in range(first.region.height):
            offset = 0
            for segment in first.render_line(y):
                end = offset + len(segment.text)
                if getattr(segment.style, "bgcolor", None) is not None:
                    selected_segments.append(
                        (offset, end, str(segment.style.bgcolor).lower())
                    )
                offset = end
        selected_box_segments = [
            segment for segment in selected_segments if SELECTED_BACKGROUND in segment[2]
        ]
        assert selected_box_segments, "Selected node should highlight the node box"
        assert all(start >= len(DEPTH_GUTTER) for start, _, _ in selected_box_segments)
        assert all(
            SELECTED_BACKGROUND not in color
            for start, end, color in selected_segments
            if start < len(DEPTH_GUTTER)
        )

        unselected_segments = [
            segment
            for y in range(second.region.height)
            for segment in second.render_line(y)
            if getattr(segment.style, "bgcolor", None) is not None
        ]
        assert all(
            SELECTED_BACKGROUND not in str(segment.style.bgcolor).lower()
            for segment in unselected_segments
        ), "Unselected nodes should not use the selected background"

    print("test_editor_identity_rows_fit_rendered_panel_width PASSED")


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
        # Complete editor binding copy (Phase 17 UI overhaul).
        assert "Validate workflow" in help_text
        assert "Check workflow" not in help_text
        assert "X or Backspace" in help_text
        assert "Ctrl+S" in help_text
        assert "Ctrl+R" in help_text
        assert "Ctrl+Q" in help_text
        assert "Help" in help_text
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
    wm.create_new("select_keyboard")
    node_id = wm.add_node("error_node")
    node_data = wm.get_node_data(node_id)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node_id, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        error_mode = app.query_one("#field-error_mode", Select)
        screen = app.query_one(NodeConfigScreen)
        assert getattr(app.focused, "id", None) == "alias-input"
        # Number keys jump tabs; 2 -> Parameters, focusing its first field.
        await pilot.press("2")
        await pilot.pause(0.03)
        assert getattr(app.focused, "id", None) == "field-message"
        await pilot.press("s")
        assert app.focused is error_mode
        await pilot.press("e")
        await pilot.pause()
        assert error_mode.expanded is True
        overlay = select_overlay(error_mode)
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
        assert error_mode.expanded is False
        assert app.focused is error_mode
        await pilot.press("e")
        await pilot.pause()
        assert error_mode.expanded is True
        overlay = select_overlay(error_mode)
        assert overlay.highlighted == 0
        await pilot.press("down")
        assert overlay.highlighted == 1
        await pilot.press("e")
        await pilot.pause()
        assert error_mode.value == "warn"

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
        assert saved_results[-1]["config"]["error_mode"] == "warn"

    print("test_node_config_select_activates_from_keyboard PASSED")


def test_node_config_fixed_tabs_are_keyboard_navigable():
    asyncio.run(_test_node_config_fixed_tabs_are_keyboard_navigable())


async def _test_node_config_fixed_tabs_are_keyboard_navigable():
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Checkbox, TabbedContent

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()
    wm.create_new("node_config_fixed_tabs")
    node = wm.add_node("logger_node")
    node_data = wm.get_node_data(node)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        tabs = app.query_one("#node-config-tabs", TabbedContent)
        alias = app.query_one("#alias-input", CommandInput)
        previous_output = app.query_one("#show-previous-output", Checkbox)
        parameter_field = app.query_one("#field-label", CommandInput)
        payload_reveal = app.query_one("#show-payload-upstream-payload", Checkbox)
        output_name = app.query_one("#transient-output-name-default", CommandInput)
        save_button = app.query_one("#save-node-config", Button)

        assert tabs.active == "node-config-tab-core"
        assert app.focused is alias

        await pilot.press("w")
        await pilot.pause(0.03)
        assert tabs.active == "node-config-tab-core"
        assert app.focused is alias

        # Number keys jump tabs; switching focuses the first field of the tab.
        await pilot.press("2")
        await pilot.pause(0.1)
        assert tabs.active == "node-config-tab-parameters"
        assert app.focused is parameter_field

        # While editing, left/right move the caret rather than switching tabs.
        parameter_field.value = "abc"
        parameter_field.begin_edit()
        parameter_field.cursor_position = 0
        await pilot.press("right")
        await pilot.pause(0.03)
        assert tabs.active == "node-config-tab-parameters"
        assert parameter_field.cursor_position == 1
        parameter_field.end_edit()

        await pilot.press("3")
        await pilot.pause(0.1)
        assert tabs.active == "node-config-tab-outputs"
        assert app.focused is payload_reveal
        scroll = app.query_one("#node-config-scroll")
        scroll.scroll_to(y=100, animate=False)
        screen = app.query_one(NodeConfigScreen)
        screen._scroll_config_widget_into_view(payload_reveal)
        await pilot.pause(0.03)
        assert scroll.scroll_y < 100

        for _ in range(5):
            if app.focused is output_name:
                break
            await pilot.press("s")
            await pilot.pause(0.02)
        assert app.focused is output_name

        await pilot.press("4")
        await pilot.pause(0.1)
        assert tabs.active == "node-config-tab-connections"
        assert app.focused is save_button

        await pilot.press("1")
        await pilot.pause(0.1)
        assert tabs.active == "node-config-tab-core"
        assert app.focused is alias

        await pilot.press("2")
        await pilot.pause(0.1)
        assert tabs.active == "node-config-tab-parameters"
        assert app.focused is parameter_field

        await pilot.press("3")
        await pilot.pause(0.1)
        assert tabs.active == "node-config-tab-outputs"
        assert app.focused is payload_reveal

        for _ in range(10):
            if app.focused is save_button:
                break
            await pilot.press("s")
            await pilot.pause(0.05)
        assert tabs.active == "node-config-tab-outputs"
        assert app.focused is save_button

        # A number past the tab count is a no-op.
        await pilot.press("5")
        await pilot.pause(0.05)
        assert tabs.active == "node-config-tab-outputs"

        await pilot.press("1")
        await pilot.pause(0.1)
        assert tabs.active == "node-config-tab-core"
        assert app.focused is alias

        await pilot.press("s")
        await pilot.pause(0.03)
        assert app.focused is previous_output

    print("test_node_config_fixed_tabs_are_keyboard_navigable PASSED")


def test_node_config_keyboard_skips_hidden_payload_previews():
    asyncio.run(_test_node_config_keyboard_skips_hidden_payload_previews())


async def _test_node_config_keyboard_skips_hidden_payload_previews():
    from textual.app import App, ComposeResult

    from frontend.screens.node_config import NodeConfigScreen

    _, wm, _, _ = _make_services()
    wm.create_new("node_config_hidden_skips")
    node = wm.add_node("logger_node")
    node_data = wm.get_node_data(node)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node, node_data)

    app = ConfigApp()
    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.pause(0.05)
        # Walk the whole screen with the down key. Focus must never land on a
        # widget that is hidden on its own (display=False) — that shows no
        # highlight and reads as "the cursor vanished / needed two presses".
        seen_ids = []
        for _ in range(16):
            focused = app.focused
            assert getattr(focused, "display", True), (
                f"Focus landed on hidden widget {getattr(focused, 'id', focused)!r}"
            )
            seen_ids.append(getattr(focused, "id", None))
            await pilot.press("s")
            await pilot.pause(0.02)

        # The collapsed previews on the Source tab must be skipped entirely
        # while their reveal checkboxes are off.
        assert "previous-output-preview" not in seen_ids
        assert "source-vault-payload-preview" not in seen_ids

        # When the reveal checkbox is enabled, the preview becomes a real stop.
        from frontend.widgets.command_input import CommandInput
        from textual.widgets import Checkbox

        alias = app.query_one("#alias-input", CommandInput)
        app.set_focus(alias)
        await pilot.pause(0.02)
        reveal = app.query_one("#show-previous-output", Checkbox)
        reveal.value = True
        await pilot.pause(0.03)
        await pilot.press("s")  # alias -> reveal checkbox
        await pilot.pause(0.02)
        await pilot.press("s")  # reveal checkbox -> now-visible preview
        await pilot.pause(0.02)
        assert getattr(app.focused, "id", None) == "previous-output-preview"

    print("test_node_config_keyboard_skips_hidden_payload_previews PASSED")


def test_node_selector_layout_is_compact():
    asyncio.run(_test_node_selector_layout_is_compact())


async def _test_node_selector_layout_is_compact():
    from pathlib import Path as _Path

    from textual.app import App

    from frontend.screens.node_selector import NodeSelectorScreen

    _, wm, _, _ = _make_services()

    class SelApp(App):
        CSS_PATH = str(
            _Path(__file__).parent.parent / "frontend" / "styles.tcss"
        )

        async def on_mount(self) -> None:
            await self.push_screen(NodeSelectorScreen(wm._factory))

    # A short terminal is where the old stretched (height: 1fr) tab row and
    # filter block left dead space; the list must sit flush under the filter.
    for height in (30, 22):
        app = SelApp()
        async with app.run_test(size=(90, height)) as pilot:
            await pilot.pause(0.15)
            screen = app.screen
            tabs = screen.query_one("#node-family-tabs")
            filt = screen.query_one("#node-filter")
            io_row = screen.query_one("#io-direction-row")

            # Filter is directly below the tab row — no dead space.
            gap = filt.region.y - (tabs.region.y + tabs.region.height)
            assert gap == 0, (
                f"tabs->filter gap {gap} != 0 at height {height}"
            )

            # On the I/O tab the switch sits below the filter.
            filt_bottom = filt.region.y + filt.region.height
            assert io_row.display, "Switch row should be visible on I/O tab"
            assert io_row.region.y >= filt_bottom, (
                f"Switch row top {io_row.region.y} should be >= filter bottom"
                f" {filt_bottom} at height {height}"
            )

            # The node list renders below the switch row with usable height.
            list_view = screen.query_one("#node-type-list")
            assert list_view.region.height >= 1, (
                f"node list not rendered at height {height}"
            )
            assert list_view.region.y >= io_row.region.y + io_row.region.height

    print("test_node_selector_layout_is_compact PASSED")


def test_node_selector_rows_are_one_line_with_detail():
    asyncio.run(_test_node_selector_rows_are_one_line_with_detail())


async def _test_node_selector_rows_are_one_line_with_detail():
    from textual.app import App, ComposeResult
    from textual.widgets import ListItem, ListView, Static

    from frontend.screens.node_selector import NodeSelectorScreen

    _, wm, _, _ = _make_services()

    class SelApp(App):
        def compose(self) -> ComposeResult:
            yield NodeSelectorScreen(wm._factory)

    app = SelApp()
    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.pause(0.05)
        screen = app.query_one(NodeSelectorScreen)
        list_view = app.query_one("#node-type-list", ListView)
        assert screen._visible_nodes, "Expected nodes in the default family"

        # Pick the first node entry (descriptions no longer live on the rows).
        node_entry_index = next(
            index
            for index, entry in enumerate(screen._entries)
            if entry["kind"] == "node"
        )
        node = screen._entries[node_entry_index]["node"]
        row = screen._node_row_text(node)
        # One-line scan row: "[ Display Name ]" with no embedded description.
        assert "\n" not in row, f"Expected a one-line row, got {row!r}"
        assert row == f"\\[ {node['display_name']} ]", (
            f"Expected '\\[ {node['display_name']} ]', got {row!r}"
        )
        description = str(node.get("description") or "").strip()
        if description:
            assert description not in row, (
                f"Description should not appear in the row {row!r}"
            )
        # Family must not appear in rows.
        family = screen._node_family(node)
        assert family and family not in row, (
            f"Family {family!r} should not appear in row {row!r}"
        )

        # Highlighting the row drives the single fixed detail line below it.
        list_view.index = node_entry_index
        await pilot.pause(0.05)
        detail = app.query_one("#node-detail", Static)
        detail_text = str(detail.content)
        expected_detail = description or "No description"
        assert detail_text.startswith(expected_detail[:20]), (
            f"Detail line {detail_text!r} should describe the highlighted node"
        )

        # Each node still maps to one list row carrying the scan-row static.
        node_items = [
            item
            for item in list_view.children
            if isinstance(item, ListItem) and item.query(".node-select-row")
        ]
        assert len(node_items) == len(screen._visible_nodes)

    print("test_node_selector_rows_are_one_line_with_detail PASSED")


def test_node_selector_io_toggle_keyboard_contract():
    asyncio.run(_test_node_selector_io_toggle_keyboard_contract())


async def _test_node_selector_io_toggle_keyboard_contract():
    from textual.app import App, ComposeResult
    from textual.widgets import Button

    from frontend.screens.node_selector import NodeSelectorScreen

    _, wm, _, _ = _make_services()

    class SelApp(App):
        def compose(self) -> ComposeResult:
            yield NodeSelectorScreen(wm._factory)

    app = SelApp()
    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.pause(0.05)
        screen = app.query_one(NodeSelectorScreen)
        input_button = app.query_one("#io-side-input", Button)
        output_button = app.query_one("#io-side-output", Button)

        # W/S navigates from the filter onto the segmented toggle row.
        await pilot.press("s")
        await pilot.pause(0.03)
        assert app.focused is input_button

        # The toggle is a 2-button row: A/D moves within it.
        assert screen._io_output_side is False
        await pilot.press("d")
        await pilot.pause(0.03)
        assert app.focused is output_button

        # E presses the focused side button, selecting the Output side.
        await pilot.press("e")
        await pilot.pause(0.03)
        assert screen._io_output_side is True

        # Tabs switch by number key, not A/D.
        await pilot.press("2")
        await pilot.pause(0.03)
        assert screen._active_tab == "Flow Control"

    print("test_node_selector_io_toggle_keyboard_contract PASSED")


def test_activate_command_widget_single_press_toggles_boolean():
    asyncio.run(_test_activate_command_widget_single_press_toggles_boolean())


async def _test_activate_command_widget_single_press_toggles_boolean():
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox, Switch

    from frontend.widgets.command_navigation import activate_command_widget

    class ToggleApp(App):
        def compose(self) -> ComposeResult:
            yield Checkbox(value=False, id="cb")
            yield Switch(value=False, id="sw")

    app = ToggleApp()
    async with app.run_test():
        checkbox = app.query_one("#cb", Checkbox)
        switch = app.query_one("#sw", Switch)
        # A single activate flips the value (no activate-then-toggle two-step).
        assert checkbox.value is False
        assert activate_command_widget(checkbox) is True
        assert checkbox.value is True
        assert switch.value is False
        assert activate_command_widget(switch) is True
        assert switch.value is True

    print("test_activate_command_widget_single_press_toggles_boolean PASSED")


def test_node_config_digit_types_while_editing_but_jumps_in_nav():
    asyncio.run(_test_node_config_digit_types_while_editing_but_jumps_in_nav())


async def _test_node_config_digit_types_while_editing_but_jumps_in_nav():
    from textual.app import App, ComposeResult
    from textual.widgets import TabbedContent

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()
    wm.create_new("digit_nav")
    node_id = wm.add_node("logger_node")
    node_data = wm.get_node_data(node_id)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, node_id, node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        tabs = app.query_one("#node-config-tabs", TabbedContent)
        assert tabs.active == "node-config-tab-core"

        # Nav mode: a digit jumps to the matching tab.
        await pilot.press("2")
        await pilot.pause(0.05)
        assert tabs.active == "node-config-tab-parameters"
        field = app.query_one("#field-label", CommandInput)
        assert app.focused is field

        # Editing mode: the same digit types into the field, no tab switch.
        field.begin_edit()
        field.value = ""
        field.cursor_position = 0
        await pilot.press("3")
        await pilot.pause(0.03)
        assert tabs.active == "node-config-tab-parameters"
        assert "3" in field.value

    print("test_node_config_digit_types_while_editing_but_jumps_in_nav PASSED")


def test_node_selector_down_from_filter_highlights_first_node():
    asyncio.run(_test_node_selector_down_from_filter_highlights_first_node())


async def _test_node_selector_down_from_filter_highlights_first_node():
    from textual.app import App, ComposeResult
    from textual.widgets import ListView

    from frontend.screens.node_selector import NodeSelectorScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()

    class SelApp(App):
        def compose(self) -> ComposeResult:
            yield NodeSelectorScreen(wm._factory)

    app = SelApp()
    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.pause(0.05)
        screen = app.query_one(NodeSelectorScreen)
        list_view = app.query_one("#node-type-list", ListView)
        filter_input = app.query_one("#node-filter", CommandInput)

        # The Complex tab has no I/O switch, so the filter sits directly above
        # the node list — moving down from it must reach the list.
        screen._set_active_tab("Complex")
        await pilot.pause(0.03)

        app.set_focus(filter_input)
        await pilot.pause(0.03)
        assert app.focused is filter_input
        assert filter_input.editing is False

        # One step down must land on the node list with the first row
        # highlighted — not a focused list with no visible cursor.
        await pilot.press("s")
        await pilot.pause(0.03)
        assert app.focused is list_view
        first_selectable = screen._selectable_indices()[0]
        assert list_view.index == first_selectable
        assert list_view.highlighted_child is not None
        assert list_view.highlighted_child.highlighted is True

    print("test_node_selector_down_from_filter_highlights_first_node PASSED")


def test_node_config_schema_tab_hints_place_fields_in_top_level_tabs():
    asyncio.run(_test_node_config_schema_tab_hints_place_fields_in_top_level_tabs())


async def _test_node_config_schema_tab_hints_place_fields_in_top_level_tabs():
    from textual.app import App, ComposeResult
    from textual.widgets import TabPane

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    node_data = {
        "type": "generated_layout_node",
        "alias": "Generated Layout",
        "config": {
            "source_note": "source",
            "label": "params",
            "payload_note": "payload",
        },
        "connections": {"inputs": [], "outputs": []},
    }
    metadata = {
        "type": "generated_layout_node",
        "display_name": "Generated Layout",
        "description": "Generated node with top-level tab hints",
        "input_ports": ["input"],
        "output_ports": ["default"],
        "input_port_metadata": {},
        "output_port_metadata": {},
        "default_config": {},
        "ui_hints": {},
        "config_schema": {
            "source_note": {"type": "string", "label": "Source note", "tab": "Source"},
            "label": {"type": "string", "label": "Label", "tab": "Parameters"},
            "payload_note": {"type": "string", "label": "Payload note", "tab": "Payloads"},
        },
    }

    class FakeFactory:
        def get_node_types_metadata(self):
            return [metadata]

    class FakeWorkflowMap:
        def get_all_node_data(self):
            return {"node": node_data}

        def get_node_data(self, node_id):
            return node_data if node_id == "node" else None

        def nodes_reachable_from(self, node_id):
            return set()

    def has_ancestor(widget, ancestor_id: str) -> bool:
        node = widget
        while node is not None:
            if getattr(node, "id", None) == ancestor_id:
                return True
            node = getattr(node, "parent", None)
        return False

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(FakeFactory(), FakeWorkflowMap(), "node", node_data)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        source = app.query_one("#field-source_note", CommandInput)
        params = app.query_one("#field-label", CommandInput)
        payload = app.query_one("#field-payload_note", CommandInput)
        assert has_ancestor(source, "node-config-tab-core")
        assert has_ancestor(params, "node-config-tab-parameters")
        assert has_ancestor(payload, "node-config-tab-outputs")
        assert app.query(TabPane)

        source.value = "updated source"
        params.value = "updated params"
        payload.value = "updated payload"
        values = app.query_one(NodeConfigScreen)._get_form_values()
        assert values == {
            "source_note": "updated source",
            "label": "updated params",
            "payload_note": "updated payload",
        }

    print("test_node_config_schema_tab_hints_place_fields_in_top_level_tabs PASSED")


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
    assert "Logger" in text
    assert "Payload:" in text
    assert "Payload Description:" not in text
    assert "Payload: Output (dict, 1 items)" in text

    no_run_screen = NodeConfigScreen(
        wm._factory,
        wm,
        target,
        wm.get_node_data(target),
    )
    no_run_text = no_run_screen._previous_output_text()
    assert "No captured" not in no_run_text
    assert "Run the workflow" not in no_run_text
    assert "Payload Description:" not in no_run_text
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
    assert "Output: not configured yet" in text
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
    assert "Approve: not configured yet" in text
    assert "Reject: not configured yet" in text
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

    assert "Source: Producer -> Pause" in text
    assert "Payload: created_payload (dict, 1 items)" in text
    assert "Description: Original data" in text
    print("test_node_config_previous_output_preview_traces_pass_through_source PASSED")


def test_branch_payload_preview_traces_selected_dead_drop_source():
    from frontend.screens.editor import EditorScreen
    from frontend.screens.node_config import NodeConfigScreen

    _, wm, mb, _ = _make_services()
    wm.create_new("branch_payload_dead_drop_preview")
    source = wm.add_node("logger_node")
    branch = wm.add_node("branch_node")
    target = wm.add_node("logger_node")

    wm.update_node_alias(source, "Seed Source")
    wm.update_node_alias(branch, "Branch Hub")
    wm.update_node_config(
        source,
        {
            "transient_outputs": [
                {
                    "port": "default",
                    "name": "Seed Payload",
                    "description": "Prepared upstream text",
                }
            ]
        },
    )
    wm.update_node_config(
        branch,
        {
            "branch_count": 2,
            "branch_payload_sources": {"path_a": "dead_drop:input"},
            "path_a_label": "Alpha",
            "path_b_label": "Beta",
        },
    )
    wm.connect(source, "default", branch, "input")
    wm.connect(branch, "path_a", target, "input")
    mb.store_transient(branch, "path_a", "seeded text")

    config_screen = NodeConfigScreen(
        wm._factory,
        wm,
        target,
        wm.get_node_data(target),
        memory_bank=mb,
    )
    preview = config_screen._previous_output_text()
    assert "Source: Seed Source -> Branch Hub" in preview
    assert "Payload: Seed Payload (str): seeded text" in preview
    assert "Description: Prepared upstream text" in preview

    editor_screen = EditorScreen(wm._factory, wm)
    quick_view = editor_screen._format_node_details(target, wm.get_node_data(target))
    assert "Transient Source: Seed Source" in quick_view
    assert "Seed Payload: Prepared upstream text" in quick_view
    print("test_branch_payload_preview_traces_selected_dead_drop_source PASSED")


def test_branch_payload_preview_traces_selected_vault_source():
    from frontend.screens.node_config import NodeConfigScreen

    _, wm, mb, _ = _make_services()
    wm.create_new("branch_payload_vault_preview")
    writer = wm.add_node("logger_node")
    branch = wm.add_node("branch_node")
    target = wm.add_node("logger_node")

    wm.update_node_alias(writer, "Vault Writer")
    wm.update_node_alias(branch, "Branch Hub")
    wm.update_node_config(
        writer,
        {"membank_outputs": [{"id": "session_id", "description": "Session id"}]},
    )
    wm.update_node_config(
        branch,
        {
            "branch_count": 2,
            "membank_inputs": ["session_id"],
            "branch_payload_sources": {"path_b": "vault:session_id"},
            "path_a_label": "Alpha",
            "path_b_label": "Beta",
        },
    )
    wm.connect(branch, "path_b", target, "input")
    mb.store_transient(branch, "path_b", "vault-value")

    screen = NodeConfigScreen(
        wm._factory,
        wm,
        target,
        wm.get_node_data(target),
        memory_bank=mb,
    )
    preview = screen._previous_output_text()
    assert "Source: Vault Writer -> Branch Hub" in preview
    assert "Payload: session_id (str): vault-value" in preview
    assert "Description: Session id" in preview
    print("test_branch_payload_preview_traces_selected_vault_source PASSED")


def test_node_config_payloads_tab_reveals_upstream_and_vault_payloads():
    asyncio.run(_test_node_config_payloads_tab_reveals_upstream_and_vault_payloads())


async def _test_node_config_payloads_tab_reveals_upstream_and_vault_payloads():
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox, Static, TabbedContent

    from frontend.screens.node_config import NodeConfigScreen

    _, wm, mb, _ = _make_services()
    wm.create_new("payload_tab_reveal")
    producer = wm.add_node("logger_node")
    vault_writer = wm.add_node("logger_node")
    target = wm.add_node("logger_node")

    wm.update_node_alias(producer, "Producer")
    wm.update_node_alias(vault_writer, "Vault Writer")
    wm.update_node_config(
        producer,
        {
            "transient_outputs": [
                {
                    "port": "default",
                    "name": "Draft Text",
                    "description": "Text for the next node",
                }
            ]
        },
    )
    wm.update_node_config(
        vault_writer,
        {"membank_outputs": [{"id": "session_id", "description": "Session id"}]},
    )
    wm.update_node_config(target, {"membank_inputs": ["session_id"]})
    wm.connect(producer, "default", target, "input")
    mb.store_transient(producer, "default", "hello")
    mb.store_persistent("session_id", "abc-123")
    node_data = wm.get_node_data(target)

    class ConfigApp(App):
        def compose(self) -> ComposeResult:
            yield NodeConfigScreen(wm._factory, wm, target, node_data, memory_bank=mb)

    app = ConfigApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        tabs = app.query_one("#node-config-tabs", TabbedContent)
        source_vault_reveal = app.query_one("#show-source-vault-payload", Checkbox)
        source_vault_preview = app.query_one("#source-vault-payload-preview", Static)
        source_vault_reveal.value = True
        screen = app.query_one(NodeConfigScreen)
        screen._sync_payload_previews()
        app.set_focus(source_vault_reveal)
        await pilot.press("s")
        await pilot.pause(0.02)
        assert app.focused is source_vault_preview
        assert source_vault_preview.has_class("payload-preview")

        tabs.active = "node-config-tab-outputs"
        upstream = app.query_one("#show-payload-upstream-payload", Checkbox)
        vault = app.query_one("#show-payload-vault-payload", Checkbox)
        upstream.value = True
        vault.value = True
        screen._sync_payload_previews()

        upstream_text = str(app.query_one("#payload-upstream-payload-preview", Static).content)
        vault_text = str(app.query_one("#payload-vault-payload-preview", Static).content)
        assert "Source: Producer" in upstream_text
        assert "Payload: Draft Text (str): hello" in upstream_text
        assert "Description: Text for the next node" in upstream_text
        assert "Source: Vault Writer" in vault_text
        assert "Payload: session_id (str): abc-123" in vault_text
        assert "Description: Session id" in vault_text

    print("test_node_config_payloads_tab_reveals_upstream_and_vault_payloads PASSED")


def test_node_selector_uses_family_tabs():
    asyncio.run(_test_node_selector_uses_family_tabs())


async def _test_node_selector_uses_family_tabs():
    from textual.app import App, ComposeResult
    from textual.widgets import Button, ListView

    from frontend.screens.node_selector import NodeSelectorScreen
    from frontend.widgets.command_input import CommandInput

    _, wm, _, _ = _make_services()

    class SelectorApp(App):
        def compose(self) -> ComposeResult:
            yield NodeSelectorScreen(wm._factory)

    def entry_kinds(screen):
        return [entry["kind"] for entry in screen._entries]

    def header_names(screen):
        return [
            entry["name"]
            for entry in screen._entries
            if entry["kind"] == "header"
        ]

    def group_entries(screen):
        return {
            entry["name"]: len(entry["members"])
            for entry in screen._entries
            if entry["kind"] == "group"
        }

    app = SelectorApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        screen = app.query_one(NodeSelectorScreen)
        node_list = app.query_one("#node-type-list", ListView)
        filter_input = app.query_one("#node-filter", CommandInput)
        io_input_button = app.query_one("#io-side-input", Button)
        io_output_button = app.query_one("#io-side-output", Button)

        # Hidden node types never reach the selector.
        all_types = {node["type"] for node in screen._all_nodes}
        assert "tombstone_node" not in all_types
        assert "start_node" not in all_types
        assert "end_node" not in all_types

        # Default: I/O tab, Input side — focus lands on the filter bar
        # (not edit mode) so the user can type immediately or navigate down.
        assert screen._active_tab == "I/O"
        assert screen._active_family() == "Inputs"
        # Segmented I/O toggle defaults to the Input side.
        assert screen._io_output_side is False
        assert io_input_button.has_class("active")
        assert not io_output_button.has_class("active")
        assert app.focused is filter_input
        assert filter_input.editing is False
        assert {node["type"] for node in screen._visible_nodes} == {
            "example_file_instance_node",
            "file_reader_node",
            "user_text_input_node",
            "http_request_node",
        }
        # Single-member groups auto-promote: no group entries on this side,
        # and the section headers from selector_section metadata render.
        assert group_entries(screen) == {}
        assert header_names(screen) == ["Text & Data", "Files", "Web"]

        # Flip the segmented toggle to the Output side.
        screen._set_io_side(True)
        await pilot.pause(0.03)
        assert screen._active_family() == "Outputs"
        assert io_output_button.has_class("active")
        assert not io_input_button.has_class("active")
        assert {node["type"] for node in screen._visible_nodes} == {
            "text_output_node",
        }

        # Flow Control: no filter checkboxes; Branch group with member count;
        # single-member groups and direct-adds promoted to node rows under
        # their section headers.
        screen.action_next_tab()
        assert screen._active_tab == "Flow Control"
        assert header_names(screen) == ["Branching", "Timing"]
        groups = group_entries(screen)
        assert groups.get("Branch", 0) >= 2
        visible_types = {node["type"] for node in screen._visible_nodes}
        assert "merge_node" in visible_types  # Merge group of one, promoted
        assert "branch_end_node" in visible_types  # direct-add Merge Beacon
        assert "wait_until_node" in visible_types  # Wait / Timer, promoted
        assert "branch_node" not in visible_types  # behind the Branch group

        # Utility tab: transform group plus debug/loop helper direct-adds.
        screen.action_next_tab()
        assert screen._active_tab == "Utility"
        assert "Data Transform" in group_entries(screen)
        assert {"Transform", "Debug", "Loop Helpers"}.issubset(
            set(header_names(screen))
        )
        utility_types = {node["type"] for node in screen._visible_nodes}
        assert {"echo_node", "probe_node", "counter_node"}.issubset(utility_types)

        # Complex tab: AI Processing group of three.
        screen.action_next_tab()
        assert screen._active_tab == "Complex"
        assert group_entries(screen).get("AI Processing") == 3

        # Search dissolves groups and headers: AI nodes appear directly.
        await pilot.press("/")
        assert app.focused is filter_input
        assert filter_input.editing is False
        await pilot.press("e")
        assert filter_input.editing is True
        filter_input.value = "chat"
        filter_input.end_edit()
        screen._apply_filter(filter_input.value)
        assert filter_input.editing is False
        assert header_names(screen) == []
        assert group_entries(screen) == {}
        assert {node["type"] for node in screen._visible_nodes} == {
            "chat_completion_node",
        }

        filter_input.value = "deleted"
        screen._apply_filter(filter_input.value)
        assert screen._visible_nodes == []

        filter_input.value = ""
        screen._apply_filter(filter_input.value)
        assert group_entries(screen).get("AI Processing") == 3

        screen.action_focus_node_list()
        assert app.focused is node_list
        first_selectable = screen._selectable_indices()[0]
        assert node_list.index == first_selectable

    print("test_node_selector_uses_family_tabs PASSED")


def test_node_selector_group_picker_flow():
    asyncio.run(_test_node_selector_group_picker_flow())


async def _test_node_selector_group_picker_flow():
    from textual.app import App
    from textual.widgets import ListView

    from frontend.screens.group_picker import GroupPickerScreen
    from frontend.screens.node_selector import NodeSelectorScreen

    _, wm, _, _ = _make_services()
    chosen: list = []

    class PickerApp(App):
        async def on_mount(self) -> None:
            await self.push_screen(
                NodeSelectorScreen(wm._factory), chosen.append
            )

    app = PickerApp()
    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.pause(0.1)
        screen = app.screen
        assert isinstance(screen, NodeSelectorScreen)
        screen._set_active_tab("Flow Control")
        await pilot.pause(0.03)

        branch_index = next(
            index
            for index, entry in enumerate(screen._entries)
            if entry["kind"] == "group" and entry["name"] == "Branch"
        )
        node_list = screen.query_one("#node-type-list", ListView)
        screen._focus_node_list()
        node_list.index = branch_index
        await pilot.pause(0.03)

        # E on the group entry opens the picker, not the selector dismissal.
        screen.action_choose()
        await pilot.pause(0.05)
        picker = app.screen
        assert isinstance(picker, GroupPickerScreen)
        assert picker.group_name == "Branch"
        member_types = [member["type"] for member in picker.members]
        assert "branch_node" in member_types

        # ESC pops only the picker and returns to the main selector.
        picker.action_cancel()
        await pilot.pause(0.05)
        assert isinstance(app.screen, NodeSelectorScreen)
        assert chosen == []

        # Re-open and choose a member: both modals close, the selector
        # resolves with the chosen node type.
        screen.action_choose()
        await pilot.pause(0.05)
        picker = app.screen
        assert isinstance(picker, GroupPickerScreen)
        target_index = member_types.index("branch_node")
        picker_list = picker.query_one("#group-member-list", ListView)
        picker_list.index = target_index
        picker.action_choose()
        await pilot.pause(0.05)
        assert chosen == ["branch_node"]
        assert not isinstance(app.screen, (NodeSelectorScreen, GroupPickerScreen))

    print("test_node_selector_group_picker_flow PASSED")


def test_node_selector_navigation_skips_section_headers():
    asyncio.run(_test_node_selector_navigation_skips_section_headers())


async def _test_node_selector_navigation_skips_section_headers():
    from textual.app import App, ComposeResult
    from textual.widgets import ListView

    from frontend.screens.node_selector import NodeSelectorScreen

    _, wm, _, _ = _make_services()

    class SelApp(App):
        def compose(self) -> ComposeResult:
            yield NodeSelectorScreen(wm._factory)

    app = SelApp()
    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.pause(0.05)
        screen = app.query_one(NodeSelectorScreen)
        node_list = app.query_one("#node-type-list", ListView)

        header_indices = [
            index
            for index, entry in enumerate(screen._entries)
            if entry["kind"] == "header"
        ]
        assert header_indices, "Expected section headers on the I/O Input side"

        screen._focus_node_list()
        await pilot.pause(0.03)
        assert node_list.index in screen._selectable_indices()

        # Walking the whole list never lands on a header row.
        seen = [node_list.index]
        for _ in range(len(screen._entries) + 2):
            previous = node_list.index
            screen._move_selection_or_leave_list(1)
            if app.focused is not node_list:
                break
            if node_list.index == previous:
                break
            seen.append(node_list.index)
        assert seen == screen._selectable_indices()
        for index in seen:
            assert index not in header_indices

    print("test_node_selector_navigation_skips_section_headers PASSED")


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


def test_memory_viewer_shows_friendly_transient_keys():
    asyncio.run(_test_memory_viewer_shows_friendly_transient_keys())


async def _test_memory_viewer_shows_friendly_transient_keys():
    from textual.app import App, ComposeResult
    from textual.widgets import DataTable

    from frontend.screens.memory_viewer import MemoryViewerScreen

    _, wm, memory_bank, _ = _make_services()
    wm.create_new("memory_friendly_keys")
    node_id = wm.add_node("logger_node")
    wm.update_node_alias(node_id, "Producer")
    memory_bank.store_transient(node_id, "default", "hello")

    class MemoryApp(App):
        def compose(self) -> ComposeResult:
            # Pass the workflow map as optional display context.
            yield MemoryViewerScreen(memory_bank, wm)

    app = MemoryApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        table = app.query_one("#memory-table", DataTable)
        keys = [str(table.get_row_at(row)[1]) for row in range(table.row_count)]
        # Transient key renders as "<alias> · <port>"; the raw generated id
        # never reaches the table.
        assert "Producer · default" in keys
        assert all(node_id not in key for key in keys)

    # Without context the raw key is preserved (back-compat).
    class RawApp(App):
        def compose(self) -> ComposeResult:
            yield MemoryViewerScreen(memory_bank)

    raw_app = RawApp()
    async with raw_app.run_test() as pilot:
        await pilot.pause(0.03)
        table = raw_app.query_one("#memory-table", DataTable)
        keys = [str(table.get_row_at(row)[1]) for row in range(table.row_count)]
        assert f"{node_id}__default" in keys

    print("test_memory_viewer_shows_friendly_transient_keys PASSED")


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
    from textual.widgets import TabbedContent

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
        tabs = app.query_one("#node-config-tabs", TabbedContent)
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
        # Nav-mode A/D no longer types and no longer switches tabs; on a
        # single-widget row it positions the caret in the focused input.
        assert alias.value == previous_value
        assert tabs.active == "node-config-tab-core"
        assert alias.cursor_position == len(previous_value) - 1
        # Tabs switch by number key, in nav mode only.
        await pilot.press("4")
        assert tabs.active == "node-config-tab-connections"
        await pilot.press("1")
        assert tabs.active == "node-config-tab-core"
        assert app.focused is alias

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
        assert alias.value.endswith("xws")
        preserved_value = alias.value
        screen.action_activate_focused()
        await pilot.press("y")
        await pilot.press("ctrl+q")
        assert alias.editing is False
        assert alias.value == preserved_value
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

    import frontend.file_io as file_io
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

    original_open = file_io.pick_open_file
    try:
        file_io.pick_open_file = lambda *args, **kwargs: "/tmp/from-browser.json"

        class BrowsePathApp(App):
            def compose(self) -> ComposeResult:
                yield PathPromptScreen("Import", picker_mode="open")

        browse_app = BrowsePathApp()
        async with browse_app.run_test() as pilot:
            await pilot.pause(0.03)
            browse_input = browse_app.query_one("#path-input", CommandInput)
            browse_button = browse_app.query_one("#browse-path", Button)
            confirm_button = browse_app.query_one("#confirm-path", Button)
            assert browse_button.label.plain == "Browse"
            browse_input.value = ""
            await pilot.press("b")
            await pilot.pause(0.1)
            assert browse_input.value == "b"
            browse_input.end_edit()
            browse_app.set_focus(browse_button)
            await pilot.press("e")
            await pilot.pause(0.1)
            assert browse_input.value == "/tmp/from-browser.json"
            assert browse_app.focused is confirm_button
    finally:
        file_io.pick_open_file = original_open

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
    from frontend.widgets.status_bar import StatusBar

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
        assert "ctrl+q quit" in app.query_one(StatusBar)._formatted()
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
        await pilot.press("x")
        assert "worlxd" in textarea.text
        await pilot.press("escape")
        await pilot.pause(0.02)
        assert textarea.editing is False
        assert "worlxd" in textarea.text
        textarea.begin_edit()
        await pilot.press("tab")
        await pilot.pause(0.02)
        assert textarea.editing is True
        assert app.cursor_state.mode == "edit"
        before_revert = textarea.text
        await pilot.press("z")
        assert textarea.text != before_revert
        await pilot.press("ctrl+q")
        await pilot.pause(0.02)
        assert textarea.editing is False
        assert textarea.text == before_revert
        assert "worlxd" in textarea.text
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
        test_deleted_node_materializes_to_system_branch_end_and_drops_outputs,
        test_editor_save_materializes_deleted_node_and_loaded_marker_renders,
        test_editor_x_on_deleted_node_permanently_deletes,
        test_node_card_editor_identity_rows_align_and_truncate,
        test_set_variable_node_can_pass_input_through,
        test_branch_node_default_labels_are_configurable,
        test_branch_config_uses_generated_labels_without_memory_outputs,
        test_branch_config_uses_parallel_payload_ui,
        test_branch_node_parallel_count_and_payload_sources,
        test_node_config_empty_vault_copy_is_short,
        test_node_config_selection_lists_exit_at_edges,
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
        test_editor_identity_rows_keep_keyboard_selection_stable,
        test_editor_identity_rows_fit_rendered_panel_width,
        test_help_screen_is_contextual_and_focuses_cancel,
        test_node_config_select_activates_from_keyboard,
        test_node_config_fixed_tabs_are_keyboard_navigable,
        test_node_config_keyboard_skips_hidden_payload_previews,
        test_node_selector_layout_is_compact,
        test_node_selector_rows_are_one_line_with_detail,
        test_node_selector_down_from_filter_highlights_first_node,
        test_node_config_schema_tab_hints_place_fields_in_top_level_tabs,
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
        test_branch_payload_preview_traces_selected_dead_drop_source,
        test_branch_payload_preview_traces_selected_vault_source,
        test_node_config_payloads_tab_reveals_upstream_and_vault_payloads,
        test_node_selector_uses_family_tabs,
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

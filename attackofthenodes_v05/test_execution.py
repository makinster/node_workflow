"""Phase 2 acceptance tests for AttackOfTheNodes v0.5."""

import asyncio
import logging


logging.basicConfig(level=logging.WARNING)


def build_stack():
    """Create a fresh backend stack for one test scenario."""
    from backend.event_bus import EventBus
    from backend.configuration_manager import ConfigurationManager
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
    return bus, factory, workflow_map, memory_bank, master


async def scenario_linear() -> bool:
    """Start -> Text -> Text -> End."""
    print("\n=== SCENARIO 1: Linear workflow ===")
    _, _, workflow_map, memory_bank, master = build_stack()

    workflow_map.create_new("Linear")
    start = workflow_map.add_node("start_node")
    text1 = workflow_map.add_node("text_output_node")
    text2 = workflow_map.add_node("text_output_node")
    end = workflow_map.add_node("end_node")

    workflow_map.update_node_config(start, {"greeting": "alpha"})
    workflow_map.update_node_config(
        text1,
        {
            "label": "T1",
            "template": "first={input}",
            "request_user_input": False,
            "prompt": "",
        },
    )
    workflow_map.update_node_config(
        text2,
        {
            "label": "T2",
            "template": "second={input}",
            "request_user_input": False,
            "prompt": "",
        },
    )
    workflow_map.update_node_config(end, {"message": "done"})

    workflow_map.connect(start, "default", text1, "input")
    workflow_map.connect(text1, "default", text2, "input")
    workflow_map.connect(text2, "default", end, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    log = memory_bank.read_persistent("output_log", default=[])
    print(f"State: {master.state.value}")
    print(f"Log entries: {len(log)}")
    for entry in log:
        print(f"  {entry}")

    passed = master.state.value == "FINISHED" and len(log) == 3
    print(f"Scenario 1 {'PASSED' if passed else 'FAILED'}")
    return passed


async def scenario_user_input() -> bool:
    """Start -> Text(asking for input) -> End."""
    print("\n=== SCENARIO 2: User input workflow ===")
    bus, _, workflow_map, memory_bank, master = build_stack()

    workflow_map.create_new("UserInput")
    start = workflow_map.add_node("start_node")
    text = workflow_map.add_node("text_output_node")
    end = workflow_map.add_node("end_node")

    workflow_map.update_node_config(start, {"greeting": "ignored"})
    workflow_map.update_node_config(
        text,
        {
            "label": "Ask",
            "template": "you said: {input}",
            "request_user_input": True,
            "prompt": "Type something:",
        },
    )
    workflow_map.update_node_config(end, {"message": "done"})

    workflow_map.connect(start, "default", text, "input")
    workflow_map.connect(text, "default", end, "input")

    from backend.events import USER_INPUT_NEEDED

    def auto_respond(payload):
        async def submit_later():
            await asyncio.sleep(0)
            master.submit_user_input(payload["branch_id"], "hello from test")

        asyncio.create_task(submit_later())

    bus.subscribe(USER_INPUT_NEEDED, auto_respond)

    await master.start_workflow()
    await master.wait_for_completion()

    log = memory_bank.read_persistent("output_log", default=[])
    print(f"State: {master.state.value}")
    for entry in log:
        print(f"  {entry}")

    passed = master.state.value == "FINISHED" and any(
        "hello from test" in entry for entry in log
    )
    print(f"Scenario 2 {'PASSED' if passed else 'FAILED'}")
    return passed


async def scenario_branching() -> bool:
    """Start -> Branch -> [End_A, End_B]."""
    print("\n=== SCENARIO 3: Branching workflow ===")
    _, _, workflow_map, memory_bank, master = build_stack()

    workflow_map.create_new("Branching")
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    end_a = workflow_map.add_node("end_node")
    end_b = workflow_map.add_node("end_node")

    workflow_map.update_node_config(start, {"greeting": "fork"})
    workflow_map.update_node_config(branch, {"condition": "always_branch"})
    workflow_map.update_node_config(end_a, {"message": "path A complete"})
    workflow_map.update_node_config(end_b, {"message": "path B complete"})

    workflow_map.connect(start, "default", branch, "input")
    workflow_map.connect(branch, "path_a", end_a, "input")
    workflow_map.connect(branch, "path_b", end_b, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    log = memory_bank.read_persistent("output_log", default=[])
    print(f"State: {master.state.value}")
    for entry in log:
        print(f"  {entry}")

    has_a = any("path A complete" in entry for entry in log)
    has_b = any("path B complete" in entry for entry in log)
    passed = master.state.value == "FINISHED" and has_a and has_b
    print(f"Scenario 3 {'PASSED' if passed else 'FAILED'}")
    return passed


async def scenario_conditional_branch_match() -> bool:
    """Start -> Branch(string match) -> only matching path."""
    print("\n=== SCENARIO 4: Conditional branch match ===")
    _, _, workflow_map, memory_bank, master = build_stack()

    workflow_map.create_new("ConditionalMatch")
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    end_a = workflow_map.add_node("end_node")
    end_b = workflow_map.add_node("end_node")

    workflow_map.update_node_config(start, {"greeting": "approved"})
    workflow_map.update_node_config(
        branch,
        {
            "condition": "string_match",
            "match_value": "approved",
            "match_mode": "equals",
            "case_sensitive": False,
            "on_match": "path_a",
            "on_no_match": "path_b",
        },
    )
    workflow_map.update_node_config(end_a, {"message": "matched path"})
    workflow_map.update_node_config(end_b, {"message": "fallback path"})

    workflow_map.connect(start, "default", branch, "input")
    workflow_map.connect(branch, "path_a", end_a, "input")
    workflow_map.connect(branch, "path_b", end_b, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    log = memory_bank.read_persistent("output_log", default=[])
    for entry in log:
        print(f"  {entry}")
    passed = (
        master.state.value == "FINISHED"
        and any("matched path" in entry for entry in log)
        and not any("fallback path" in entry for entry in log)
    )
    print(f"Scenario 4 {'PASSED' if passed else 'FAILED'}")
    return passed


async def scenario_conditional_branch_no_match() -> bool:
    """Start -> Branch(string match) -> only no-match path."""
    print("\n=== SCENARIO 5: Conditional branch no match ===")
    _, _, workflow_map, memory_bank, master = build_stack()

    workflow_map.create_new("ConditionalNoMatch")
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    end_a = workflow_map.add_node("end_node")
    end_b = workflow_map.add_node("end_node")

    workflow_map.update_node_config(start, {"greeting": "denied"})
    workflow_map.update_node_config(
        branch,
        {
            "condition": "string_match",
            "match_value": "approved",
            "match_mode": "equals",
            "case_sensitive": False,
            "on_match": "path_a",
            "on_no_match": "path_b",
        },
    )
    workflow_map.update_node_config(end_a, {"message": "matched path"})
    workflow_map.update_node_config(end_b, {"message": "fallback path"})

    workflow_map.connect(start, "default", branch, "input")
    workflow_map.connect(branch, "path_a", end_a, "input")
    workflow_map.connect(branch, "path_b", end_b, "input")

    await master.start_workflow()
    await master.wait_for_completion()

    log = memory_bank.read_persistent("output_log", default=[])
    for entry in log:
        print(f"  {entry}")
    passed = (
        master.state.value == "FINISHED"
        and any("fallback path" in entry for entry in log)
        and not any("matched path" in entry for entry in log)
    )
    print(f"Scenario 5 {'PASSED' if passed else 'FAILED'}")
    return passed


async def main() -> None:
    """Run all Phase 2 acceptance scenarios."""
    results = [
        await scenario_linear(),
        await scenario_user_input(),
        await scenario_branching(),
        await scenario_conditional_branch_match(),
        await scenario_conditional_branch_no_match(),
    ]

    print(f"\n{'=' * 40}")
    print(f"Results: {sum(results)}/{len(results)} scenarios passed")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    asyncio.run(main())

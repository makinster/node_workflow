"""Smoke test for the extended v0.95 node library."""

import asyncio


async def main() -> None:
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

    workflow_map.create_new("v0.95 Node Smoke")
    start = workflow_map.add_node("start_node")
    user = workflow_map.add_node("user_text_input_node")
    chat = workflow_map.add_node("chat_completion_node")
    conditional = workflow_map.add_node("conditional_node")
    set_var = workflow_map.add_node("set_variable_node")
    get_var = workflow_map.add_node("get_variable_node")
    concat = workflow_map.add_node("concat_node")
    end_true = workflow_map.add_node("end_node")
    end_false = workflow_map.add_node("end_node")

    workflow_map.update_node_config(start, {"greeting": "seed"})
    workflow_map.update_node_config(user, {"prompt": "Say something"})
    # chat_completion_node now makes real LLM calls, so it is registered but
    # kept out of the execution path of this offline smoke test.
    workflow_map.update_node_config(conditional, {
        "condition_type": "contains",
        "left_value_source": "input",
        "variable_name": "",
        "right_value": "needle",
    })
    workflow_map.update_node_config(set_var, {
        "variable_name": "answer",
        "value_source": "input",
        "value": "",
    })
    workflow_map.update_node_config(get_var, {"variable_name": "answer", "default": ""})
    workflow_map.update_node_config(concat, {"template": "final={answer}"})
    workflow_map.update_node_config(end_true, {"message": "true path"})
    workflow_map.update_node_config(end_false, {"message": "false path"})
    workflow_map.set_bookmark(conditional, True)

    workflow_map.connect(start, "default", user, "input")
    workflow_map.connect(user, "default", conditional, "input")
    workflow_map.connect(conditional, "true", set_var, "input")
    workflow_map.connect(set_var, "default", get_var, "input")
    workflow_map.connect(get_var, "default", concat, "input")
    workflow_map.connect(concat, "default", end_true, "input")
    workflow_map.connect(conditional, "false", end_false, "input")

    from backend.events import USER_INPUT_NEEDED

    def auto_input(payload):
        async def submit():
            await asyncio.sleep(0)
            master.submit_user_input(payload["branch_id"], "needle")
        asyncio.create_task(submit())

    bus.subscribe(USER_INPUT_NEEDED, auto_input)
    await master.start_workflow()
    await master.wait_for_completion()

    log = memory_bank.read_persistent("output_log", default=[])
    assert master.state.value == "FINISHED"
    assert any("true path" in item for item in log)
    assert workflow_map.get_node_data(conditional).get("bookmarked") is True
    assert "conditional_node" in factory.get_registered_types()
    print("v0.95 node smoke PASSED")


if __name__ == "__main__":
    asyncio.run(main())

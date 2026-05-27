"""v0.8 recovery-flow smoke test."""

import asyncio
import logging


logging.basicConfig(level=logging.WARNING)


async def main() -> None:
    from backend.event_bus import EventBus
    from backend.configuration_manager import ConfigurationManager
    from backend.events import RECOVERY_OPTIONS_AVAILABLE
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

    workflow_map.create_new("Recovery")
    start = workflow_map.add_node("start_node")
    bad = workflow_map.add_node("text_output_node")
    end = workflow_map.add_node("end_node")

    workflow_map.update_node_config(start, {"greeting": "alpha"})
    workflow_map.update_node_config(
        bad,
        {
            "label": "Bad",
            "template": "{missing}",  # Intentionally invalid.
            "request_user_input": False,
            "prompt": "",
        },
    )
    workflow_map.update_node_config(end, {"message": "recovered"})
    workflow_map.connect(start, "default", bad, "input")
    workflow_map.connect(bad, "default", end, "input")

    recovery_events = []

    def choose_skip(payload):
        recovery_events.append(payload)
        master.submit_recovery_action(payload["branch_id"], "SKIP")

    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, choose_skip)

    await master.start_workflow()
    await master.wait_for_completion()

    errors = master.error_handler.get_errors_for_run(master.current_run_id)
    history = master.run_history.list_runs()
    passed = (
        master.state.value == "FINISHED"
        and len(recovery_events) == 1
        and len(errors) == 1
        and history
        and history[0]["error_count"] == 1
    )
    print(f"State: {master.state.value}")
    print(f"Recovery events: {len(recovery_events)}")
    print(f"Errors logged: {len(errors)}")
    print(f"History entries: {len(history)}")
    print(f"Recovery smoke {'PASSED' if passed else 'FAILED'}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

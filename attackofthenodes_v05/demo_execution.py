#!/usr/bin/env python3
"""Command-line Phase 2 execution demo kept alongside the Phase 3 UI."""

import asyncio
import logging


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


async def main() -> None:
    """Build and run a simple linear workflow through the execution stack."""
    from backend.event_bus import EventBus
    from backend.configuration_manager import ConfigurationManager
    from backend.master_state import MasterState
    from backend.memory_bank import MemoryBank
    from backend.node_factory import NodeFactory
    from backend.output_manager import OutputManager
    from backend.validator import validate_workflow
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

    workflow_map.create_new("Linear Demo")
    start_id = workflow_map.add_node("start_node", alias="Start")
    text_id = workflow_map.add_node("text_output_node", alias="Greet")
    end_id = workflow_map.add_node("end_node", alias="End")

    workflow_map.update_node_config(start_id, {"greeting": "Hello, world!"})
    workflow_map.update_node_config(
        text_id,
        {
            "label": "Greeting",
            "template": "Received: {input}",
            "request_user_input": False,
            "prompt": "",
        },
    )
    workflow_map.update_node_config(end_id, {"message": "Workflow complete"})

    workflow_map.connect(start_id, "default", text_id, "input")
    workflow_map.connect(text_id, "default", end_id, "input")

    result = validate_workflow(workflow_map, factory)
    print(
        f"Validation: success={result['success']} "
        f"errors={len(result['errors'])} warnings={len(result['warnings'])}"
    )
    if not result["success"]:
        for error in result["errors"]:
            print(f"  ERROR: {error}")
        return

    print("\nStarting workflow...")
    await master.start_workflow()
    await master.wait_for_completion()

    print(f"\nFinal state: {master.state.value}")
    print("Output log:")
    for line in memory_bank.read_persistent("output_log", default=[]):
        print(f"  {line}")


if __name__ == "__main__":
    asyncio.run(main())

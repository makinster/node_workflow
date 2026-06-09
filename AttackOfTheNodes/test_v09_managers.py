"""Smoke tests for v0.9 manager refactors."""

from pathlib import Path


def main() -> None:
    from backend.configuration_manager import ConfigurationManager
    from backend.event_bus import EventBus
    from backend.memory_bank import MemoryBank
    from backend.node_factory import NodeFactory
    from backend.persistence import delete_workflow, load_workflow
    from backend.save_manager import SaveManager
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    memory_bank = MemoryBank(bus)
    configuration = ConfigurationManager()
    save_manager = SaveManager(workflow_map, memory_bank, configuration)

    created_ids = []
    export_path = Path(__file__).resolve().parent / "_v09_export_test.json"
    try:
        workflow_id = workflow_map.create_new("Manager Smoke")
        created_ids.append(workflow_id)
        start_id = workflow_map.add_node("start_node", alias="Start")
        assert start_id is not None
        assert save_manager.save_current_workflow()
        assert load_workflow(workflow_id)["name"] == "Manager Smoke"

        assert save_manager.rename_current_workflow("Manager Smoke Renamed")
        assert load_workflow(workflow_id)["name"] == "Manager Smoke Renamed"

        duplicate_id = save_manager.duplicate_workflow(workflow_id)
        assert duplicate_id is not None
        created_ids.append(duplicate_id)
        assert load_workflow(duplicate_id)["name"].endswith("(Copy)")

        assert save_manager.export_workflow(workflow_id, str(export_path))
        imported_id = save_manager.import_workflow(str(export_path))
        assert imported_id is not None
        created_ids.append(imported_id)
        assert load_workflow(imported_id)["name"].endswith("(Imported)")

        assert save_manager.load_workflow(duplicate_id)
        assert save_manager.load_workflow(workflow_id)
        open_ids = {item["id"] for item in workflow_map.get_open_workflows()}
        assert workflow_id in open_ids and duplicate_id in open_ids
        assert workflow_map.switch_active_workflow(duplicate_id)
        assert workflow_map.workflow_id == duplicate_id

        print("v0.9 manager smoke PASSED")
    finally:
        for workflow_id in created_ids:
            delete_workflow(workflow_id)
        if export_path.exists():
            export_path.unlink()


if __name__ == "__main__":
    main()

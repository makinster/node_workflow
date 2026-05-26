#!/usr/bin/env python3
"""
AttackOfTheNodes v0.5 - Python Proof of Concept.

Phase 1 entry point and smoke test for the foundation components.
"""


def main() -> None:
    """Run the Phase 1 foundation smoke test."""
    print("AttackOfTheNodes v0.5 - Foundation Phase")

    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.persistence import list_workflows, load_workflow, save_workflow

    test_workflow = {
        "id": "test_workflow_001",
        "name": "Test Workflow",
        "nodes": {
            "start_1": {
                "type": "start_node",
                "alias": "Start",
                "config": {"greeting": "Hello World"},
                "position": {"x": 100, "y": 50},
                "connections": {
                    "inputs": [],
                    "outputs": [
                        {"target_node_id": "text_1", "target_port": "input"}
                    ],
                },
            }
        },
    }

    print("Testing persistence...")
    save_workflow("test_workflow_001", test_workflow)
    loaded = load_workflow("test_workflow_001")
    workflows = list_workflows()
    if loaded is None:
        raise RuntimeError("Expected test_workflow_001 to load after saving")
    print(f"Saved and loaded workflow: {loaded['name']}")
    print(f"Available workflows: {[w['name'] for w in workflows]}")

    print("\nTesting event bus...")
    bus = EventBus()

    def test_listener(event_data):
        print(f"Received event: {event_data}")

    bus.subscribe("TEST_EVENT", test_listener)
    bus.publish("TEST_EVENT", {"message": "Hello from event bus"})

    print("\nTesting node factory...")
    factory = NodeFactory()
    print(
        "Available node types: "
        f"{[nt['type'] for nt in factory.get_node_types_metadata()]}"
    )

    print("\nTesting node validation...")
    start_node = factory.create_node("start_node", "start_test", {"greeting": "Test"})
    if start_node is None:
        raise RuntimeError("Expected start_node to be registered")
    errors = start_node.validate_config()
    print(f"StartNode validation errors: {errors}")
    print(f"StartNode input ports: {start_node.get_input_ports()}")
    print(f"StartNode output ports: {start_node.get_output_ports()}")

    print("\nPhase 1 foundation complete!")


if __name__ == "__main__":
    main()

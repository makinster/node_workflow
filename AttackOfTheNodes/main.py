#!/usr/bin/env python3
"""AttackOfTheNodes entry point.

``aotn`` launches the Textual TUI; ``aotn run <workflow>`` runs a workflow
from the command line (see ``aotn_cli.py``) without importing Textual.
"""

import sys
from typing import List, Optional


def configure_logging(configuration) -> None:
    """Configure logging from settings (kept for existing callers)."""
    from backend.logging_setup import configure_logging as configure

    configure(configuration)


def main(argv: Optional[List[str]] = None) -> Optional[int]:
    """Launch the TUI, or dispatch ``aotn run`` / the authoring commands
    (``aotn nodes``, ``describe``, ``build``, ``inspect``)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "run":
        from aotn_cli import main as run_main

        return run_main(args[1:])
    if args and args[0] in ("nodes", "describe", "build", "inspect"):
        from aotn_author import main as author_main

        return author_main(args[0], args[1:])
    run_tui()
    return None


def run_tui() -> None:
    """Launch the Textual terminal UI."""
    from backend.event_bus import EventBus
    from backend.configuration_manager import ConfigurationManager
    from backend.master_state import MasterState
    from backend.memory_bank import MemoryBank
    from backend.node_factory import NodeFactory
    from backend.output_manager import OutputManager
    from backend.save_manager import SaveManager
    from backend.secrets_manager import SecretsManager
    from backend.workflow_map import WorkflowMap
    from frontend.app import App

    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    memory_bank = MemoryBank(bus)
    configuration = ConfigurationManager()
    configure_logging(configuration)
    output_manager = OutputManager()
    secrets_manager = SecretsManager()
    master = MasterState(
        workflow_map,
        memory_bank,
        bus,
        output_manager=output_manager,
        configuration_manager=configuration,
        secrets_manager=secrets_manager,
    )
    save_manager = SaveManager(workflow_map, memory_bank, configuration)

    app = App(
        bus,
        factory,
        workflow_map,
        memory_bank,
        master,
        save_manager,
        secrets_manager=secrets_manager,
    )
    app.run()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""AttackOfTheNodes v0.5 - Phase 3 tkinter application entry point."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def configure_logging(configuration) -> None:
    """Configure console and optional rotating file logging from settings."""
    level_name = str(configuration.get("log_level")).upper()
    level = getattr(logging, level_name, logging.WARNING)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(console)

    if configuration.get("log_to_file_enabled"):
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        handler = TimedRotatingFileHandler(
            logs_dir / "attackofthenodes.log",
            when="D",
            interval=1,
            backupCount=int(configuration.get("log_retention_days") or 7),
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)


def main() -> None:
    """Launch the Phase 3 editor UI."""
    from backend.event_bus import EventBus
    from backend.configuration_manager import ConfigurationManager
    from backend.master_state import MasterState
    from backend.memory_bank import MemoryBank
    from backend.node_factory import NodeFactory
    from backend.output_manager import OutputManager
    from backend.save_manager import SaveManager
    from backend.workflow_map import WorkflowMap
    from frontend.app import App

    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    memory_bank = MemoryBank(bus)
    configuration = ConfigurationManager()
    configure_logging(configuration)
    output_manager = OutputManager()
    master = MasterState(
        workflow_map,
        memory_bank,
        bus,
        output_manager=output_manager,
        configuration_manager=configuration,
    )
    save_manager = SaveManager(workflow_map, memory_bank, configuration)

    app = App(bus, factory, workflow_map, memory_bank, master, save_manager)
    app.mainloop()


if __name__ == "__main__":
    main()

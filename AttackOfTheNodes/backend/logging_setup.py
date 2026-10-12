"""Logging setup shared by every client (TUI, CLI, future server)."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from .persistence import LOGS_DIR


def configure_logging(configuration, logs_dir: Optional[Path] = None) -> None:
    """Configure console and optional rotating file logging from settings.

    The console handler writes WARNING and above to stderr. When
    ``log_to_file_enabled`` is set, a daily rotating file is written under the
    data directory's ``logs/`` folder.
    """
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
        target = Path(logs_dir) if logs_dir is not None else LOGS_DIR
        target.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            target / "attackofthenodes.log",
            when="D",
            interval=1,
            backupCount=int(configuration.get("log_retention_days") or 7),
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)

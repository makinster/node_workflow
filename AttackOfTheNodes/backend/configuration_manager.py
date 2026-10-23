"""
Configuration manager for AttackOfTheNodes.

Settings are stored as JSON, cached in memory, and constrained by
DEFAULT_SETTINGS so stray keys do not silently enter the application.
"""

from typing import Any, Dict

from .persistence import SETTINGS_DIR, load_json_record, save_json_record


DEFAULT_SETTINGS: Dict[str, Any] = {
    "max_branch_depth": 5,
    "node_timeout_seconds": 30,
    "auto_save_enabled": False,
    "auto_save_interval_seconds": 60,
    "last_active_workflow_id": "",
    "default_workflow_name_prefix": "Untitled Workflow",
    "log_level": "WARNING",
    "log_to_file_enabled": True,
    "log_retention_days": 7,
    # Step 4b (C16): subworkflow limits per root run; a call past either fails
    # at once. bench_subworkflow_calls.py (2026-10-19): a waiting child costs
    # about 45 KB, a busy 60-node child about 0.4 MB and 10 ms of CPU, both
    # linear; 64 busy children stay under 30 MB and a second.
    "max_subworkflow_depth": 4,
    "max_live_subworkflow_runs": 64,
    # C7 (owner, 2026-10-20): folders System nodes (Disk space, Git status,
    # File age) may look in, separated by ";". "~" is the home folder.
    "system_node_folders": "~",
    # C1 (owner, 2026-10-21): the names Notify me may send to, separated by
    # ";". A name is set up in Hermes (a drain job per name), never a chat
    # id. The shared folder itself is $HERMES_HOME/aotn (hermes_folder.py).
    "hermes_send_to_names": "home",
    # Ask Hermes never accepts installations/credentials from workflow config.
    "hermes_profile_home": "~/.hermes/profiles/aotn",
    "hermes_command": "~/.local/bin/hermes",
    "hermes_allow_no_budget": False,
    # C3c: account starts per UTC day, not a dollar cap.
    "hermes_investigations_per_day": 5,
    "hermes_investigation_profile_home": "~/.hermes/profiles/aotn",
}


class ConfigurationManager:
    """Loads, validates, caches, and persists global settings."""

    def __init__(self) -> None:
        record = load_json_record(SETTINGS_DIR, "settings") or {}
        loaded = record.get("settings", record)
        self._settings = dict(DEFAULT_SETTINGS)
        for key, value in loaded.items():
            if key in DEFAULT_SETTINGS:
                self._settings[key] = value

    def get(self, key: str) -> Any:
        """Return a setting value."""
        if key not in DEFAULT_SETTINGS:
            raise KeyError(f"Unknown setting: {key}")
        return self._settings[key]

    def set(self, key: str, value: Any) -> None:
        """Set and persist one setting."""
        if key not in DEFAULT_SETTINGS:
            raise KeyError(f"Unknown setting: {key}")
        self._settings[key] = value
        self.save()

    def get_all(self) -> Dict[str, Any]:
        """Return a copy of all settings."""
        return dict(self._settings)

    def save(self) -> None:
        """Persist settings to disk."""
        save_json_record(SETTINGS_DIR, "settings", {"settings": self._settings})

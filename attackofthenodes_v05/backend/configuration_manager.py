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

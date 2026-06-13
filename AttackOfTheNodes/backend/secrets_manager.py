"""
Secrets manager for AttackOfTheNodes.

Stores sensitive key-value pairs (API keys, passwords, tokens) separately
from workflow saves and runtime data.  Secrets are never written to MemoryBank,
run outputs, run history, or workflow JSON files.

Current phase: plain text JSON storage.
Future phase: at-rest encryption via a pluggable cipher backend — only this
module needs updating; no node or supervisor changes required.

File: AttackOfTheNodes/secrets/secrets.json  (gitignored)
Format: {"key_name": "secret_value", ...}

Nodes access secrets at execution time via NodeContext.get_secret(key).
They store only the key name in their config, never the value.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)

_SECRETS_FILENAME = "secrets.json"


class SecretsManager:
    """Persistent store for named secret values.

    Plain-text phase: values are stored as-is in a JSON file.
    Encryption is a drop-in replacement for load/save — the public API
    (get_secret, set_secret, list_keys) will not change.
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent / "secrets"
        self._storage_dir = Path(storage_dir)
        self._secrets: Dict[str, str] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_secret(self, key: str) -> Optional[str]:
        """Return the secret value for key, or None if not found.

        Loads from disk on first access (lazy load) so the manager can be
        constructed before the secrets file exists.
        """
        self._ensure_loaded()
        return self._secrets.get(str(key))

    def set_secret(self, key: str, value: str) -> None:
        """Store or update a secret and persist to disk immediately."""
        self._ensure_loaded()
        self._secrets[str(key)] = str(value)
        self._save()

    def delete_secret(self, key: str) -> bool:
        """Remove a secret by key.  Returns True if the key existed."""
        self._ensure_loaded()
        if str(key) not in self._secrets:
            return False
        del self._secrets[str(key)]
        self._save()
        return True

    def list_keys(self) -> List[str]:
        """Return all secret key names (no values) sorted alphabetically."""
        self._ensure_loaded()
        return sorted(self._secrets.keys())

    def has_key(self, key: str) -> bool:
        """Return True if the key exists in the store."""
        self._ensure_loaded()
        return str(key) in self._secrets

    def reload(self) -> None:
        """Re-read secrets from disk, discarding any in-memory state."""
        self._loaded = False
        self._secrets = {}
        self._ensure_loaded()

    # ------------------------------------------------------------------
    # Internal load / save
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        path = self._storage_dir / _SECRETS_FILENAME
        if not path.exists():
            self._secrets = {}
            return
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                self._secrets = {str(k): str(v) for k, v in data.items()}
            else:
                logger.warning("secrets.json has unexpected format; starting empty")
                self._secrets = {}
        except Exception:
            logger.exception("Failed to load secrets from %s; starting empty", path)
            self._secrets = {}

    def _save(self) -> None:
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            path = self._storage_dir / _SECRETS_FILENAME
            path.write_text(
                json.dumps(self._secrets, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save secrets to %s", self._storage_dir)

"""
Persistence layer for AttackOfTheNodes v0.5.

Reads and writes workflow JSON files. This layer intentionally performs no
schema interpretation or workflow logic.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Set this environment variable (or `aotn run --data-dir`) before the backend
# is imported to keep workflows, settings, secrets, logs and run records
# somewhere other than the project folder. Unset, nothing moves.
DATA_DIR_ENV = "AOTN_DATA_DIR"


def resolve_data_dir() -> Path:
    """Return the data directory: ``$AOTN_DATA_DIR`` or the project folder."""
    configured = os.environ.get(DATA_DIR_ENV, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _PROJECT_ROOT


DATA_DIR = resolve_data_dir()
WORKFLOWS_DIR = DATA_DIR / "workflows"
RUN_HISTORY_DIR = DATA_DIR / "run_history"
RUN_ERRORS_DIR = DATA_DIR / "run_errors"
SETTINGS_DIR = DATA_DIR / "settings"
RUN_OUTPUTS_DIR = DATA_DIR / "run_outputs"
SECRETS_DIR = DATA_DIR / "secrets"
LOGS_DIR = DATA_DIR / "logs"
# Run-owned temporary files (R4): run_files/<run_id>/, created on first use.
RUN_FILES_DIR = DATA_DIR / "run_files"
# Machine-local reusable paths and text (Stash S1): stash/entries.json.
STASH_DIR = DATA_DIR / "stash"


def write_json_atomic(file_path: Path, data: Any) -> None:
    """Write JSON to ``file_path`` through a temporary file and a rename.

    A failed write never leaves a partial file, and each write gets its own
    temporary file, so concurrent writers never share one.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        dir=file_path.parent, prefix=f".{file_path.stem}.", suffix=".tmp"
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, file_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def save_workflow(workflow_id: str, workflow_data: Dict[str, Any]) -> None:
    """Save a workflow to workflows/{workflow_id}.json.

    Atomic: the JSON is written to a temporary file next to the target and
    renamed over it, so a failed write never leaves a partial save.
    """
    write_json_atomic(WORKFLOWS_DIR / f"{workflow_id}.json", workflow_data)


def load_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
    """Load a workflow from disk, returning None when absent or unreadable."""
    file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Error loading workflow %s: %s", workflow_id, exc)
        return None


def list_workflows() -> List[Dict[str, str]]:
    """List saved workflows as {id, name, callable} dictionaries sorted by name.

    ``callable`` is True for a subworkflow (Step 4, C27)."""
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    workflows: List[Dict[str, str]] = []
    for file_path in WORKFLOWS_DIR.glob("*.json"):
        workflow_id = file_path.stem
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            workflows.append({"id": workflow_id, "name": data.get("name", workflow_id),
                              "callable": bool(data.get("callable"))})
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Error reading workflow file %s: %s", file_path, exc)
    return sorted(workflows, key=lambda workflow: workflow["name"])


def delete_workflow(workflow_id: str) -> bool:
    """Delete a workflow file. Returns True when a file was removed."""
    file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except OSError as exc:
        logger.warning("Error deleting workflow %s: %s", workflow_id, exc)
        return False


def workflow_exists(workflow_id: str) -> bool:
    """Return True when a workflow file exists on disk."""
    return (WORKFLOWS_DIR / f"{workflow_id}.json").exists()


def save_json_record(directory: Path, record_id: str, data: Dict[str, Any]) -> None:
    """Save an arbitrary JSON record under a project data directory."""
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / f"{record_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json_record(directory: Path, record_id: str) -> Optional[Dict[str, Any]]:
    """Load an arbitrary JSON record."""
    file_path = directory / f"{record_id}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Error loading record %s: %s", file_path, exc)
        return None


def list_json_records(directory: Path) -> List[Dict[str, Any]]:
    """List arbitrary JSON records in a project data directory."""
    directory.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = []
    for file_path in directory.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Error reading record %s: %s", file_path, exc)
    return records

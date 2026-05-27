"""
Persistence layer for AttackOfTheNodes v0.5.

Reads and writes workflow JSON files. This layer intentionally performs no
schema interpretation or workflow logic.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = _PROJECT_ROOT / "workflows"
RUN_HISTORY_DIR = _PROJECT_ROOT / "run_history"
RUN_ERRORS_DIR = _PROJECT_ROOT / "run_errors"
SETTINGS_DIR = _PROJECT_ROOT / "settings"
RUN_OUTPUTS_DIR = _PROJECT_ROOT / "run_outputs"


def save_workflow(workflow_id: str, workflow_data: Dict[str, Any]) -> None:
    """Save a workflow to workflows/{workflow_id}.json."""
    WORKFLOWS_DIR.mkdir(exist_ok=True)
    file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(workflow_data, f, indent=2, ensure_ascii=False)


def load_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
    """Load a workflow from disk, returning None when absent or unreadable."""
    file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error loading workflow {workflow_id}: {exc}")
        return None


def list_workflows() -> List[Dict[str, str]]:
    """List available workflows as {id, name} dictionaries sorted by name."""
    WORKFLOWS_DIR.mkdir(exist_ok=True)
    workflows: List[Dict[str, str]] = []
    for file_path in WORKFLOWS_DIR.glob("*.json"):
        workflow_id = file_path.stem
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            workflows.append({"id": workflow_id, "name": data.get("name", workflow_id)})
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Error reading workflow file {file_path}: {exc}")
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
        print(f"Error deleting workflow {workflow_id}: {exc}")
        return False


def workflow_exists(workflow_id: str) -> bool:
    """Return True when a workflow file exists on disk."""
    return (WORKFLOWS_DIR / f"{workflow_id}.json").exists()


def save_json_record(directory: Path, record_id: str, data: Dict[str, Any]) -> None:
    """Save an arbitrary JSON record under a project data directory."""
    directory.mkdir(exist_ok=True)
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
        print(f"Error loading record {file_path}: {exc}")
        return None


def list_json_records(directory: Path) -> List[Dict[str, Any]]:
    """List arbitrary JSON records in a project data directory."""
    directory.mkdir(exist_ok=True)
    records: List[Dict[str, Any]] = []
    for file_path in directory.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Error reading record {file_path}: {exc}")
    return records

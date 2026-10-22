"""
Save manager for AttackOfTheNodes.

Coordinates workflow save/load operations so UI code does not need to know
which backend components provide structure, memory, or execution state.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .configuration_manager import ConfigurationManager
from .memory_bank import MemoryBank
from .persistence import delete_workflow, list_workflows, load_workflow, save_workflow
from .saved_values import SavedValues, SavedValuesError
from .validator import derive_input_sources
from .workflow_names import name_problem, unused_copy_name, unused_name
from .workflow_map import WorkflowMap

logger = logging.getLogger(__name__)


def _move_saved_values(workflow_id: Optional[str], old_name: str, new_name: str) -> None:
    """A renamed workflow keeps its saved values (they follow the name, C2).

    A standard workflow and a subworkflow may share a name, and then share
    its values; while another workflow still has the old name the values
    stay with it. A failure is logged; the rename itself already happened.
    """
    if any(item["id"] != workflow_id and str(item["name"]).strip() == old_name.strip()
           for item in list_workflows()):
        return
    try:
        SavedValues().move_workflow(old_name, new_name)
    except SavedValuesError as exc:
        logger.warning("Saved values stayed under '%s': %s", old_name, exc)


class SaveManager:
    """Orchestrates workflow save/load/export/import."""

    def __init__(
        self,
        workflow_map: WorkflowMap,
        memory_bank: Optional[MemoryBank] = None,
        configuration_manager: Optional[ConfigurationManager] = None,
    ) -> None:
        self._workflow_map = workflow_map
        self._memory_bank = memory_bank
        self._configuration_manager = configuration_manager

    @property
    def configuration_manager(self) -> Optional[ConfigurationManager]:
        """Return the injected configuration manager, when present."""
        return self._configuration_manager

    def save_current_workflow(self, options: Optional[Dict[str, Any]] = None) -> bool:
        """Persist the currently loaded workflow."""
        if not self._workflow_map.is_loaded:
            return False
        data = self._workflow_data_with_input_sources(
            self._workflow_map.get_workflow_data_for_save()
        )
        if options and options.get("include_memory") and self._memory_bank is not None:
            data["memory_state"] = self._memory_bank.get_state()
        save_workflow(data["id"], data)
        self._workflow_map.mark_saved()
        if self._configuration_manager is not None:
            self._configuration_manager.set("last_active_workflow_id", data["id"])
        return True

    def load_workflow(self, workflow_id: str, restore_execution: bool = False) -> bool:
        """Load a workflow and optionally restore memory state."""
        data = load_workflow(workflow_id)
        if data is None:
            return False
        self._workflow_map.load_data(data)
        if restore_execution and self._memory_bank is not None:
            self._memory_bank.load_state(data.get("memory_state", {}))
        if self._configuration_manager is not None:
            self._configuration_manager.set("last_active_workflow_id", workflow_id)
        return True

    def export_workflow(self, workflow_id: str, file_path: str) -> bool:
        """Export a workflow JSON file to an arbitrary path."""
        if workflow_id == self._workflow_map.workflow_id:
            data = self._workflow_data_with_input_sources(
                self._workflow_map.get_workflow_data_for_save()
            )
        else:
            data = load_workflow(workflow_id)
            if data is None:
                return False
            data = self._workflow_data_with_input_sources(data)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True

    def import_workflow(self, file_path: str) -> Optional[str]:
        """Import a workflow JSON file as a new workflow id."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        data["id"] = workflow_id
        data["name"] = f"{data.get('name', 'Imported Workflow')} (Imported)"
        save_workflow(workflow_id, data)
        return workflow_id

    def _source_data(self, source_id: str) -> Optional[Dict[str, Any]]:
        if source_id == self._workflow_map.workflow_id:
            return self._workflow_data_with_input_sources(
                self._workflow_map.get_workflow_data_for_save()
            )
        data = load_workflow(source_id)
        return None if data is None else self._workflow_data_with_input_sources(data)

    def duplicate_workflow(self, workflow_id: Optional[str] = None) -> Optional[str]:
        """Create a persisted copy of a workflow and return the new id."""
        source_id = workflow_id or self._workflow_map.workflow_id
        if source_id is None:
            return None
        data = self._source_data(source_id)
        if data is None:
            return None
        new_id = f"wf_{uuid.uuid4().hex[:12]}"
        copy_data = json.loads(json.dumps(data))
        copy_data["id"] = new_id
        copy_data["name"] = unused_name(
            f"{copy_data.get('name', source_id)} (Copy)", callable_=bool(copy_data.get("callable")))
        save_workflow(new_id, copy_data)
        return new_id

    def copy_as_subworkflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Save a subworkflow copy of a standard workflow (owner, 2026-10-18).

        The copy keeps the name, numbered ``(2)``, ``(3)``... when a
        subworkflow already uses it; the original is not touched. A single
        End becomes the Return End (C27). Returns ``{"id", "name",
        "renamed", "ends"}``, or None when the source can't be read.
        """
        data = self._source_data(workflow_id)
        if data is None:
            return None
        copy_data = json.loads(json.dumps(data))
        base = str(copy_data.get("name") or workflow_id).strip()
        name = unused_copy_name(base, callable_=True)
        new_id = f"wf_{uuid.uuid4().hex[:12]}"
        copy_data.update(id=new_id, name=name, callable=True)
        ends = [node for node in (copy_data.get("nodes") or {}).values()
                if isinstance(node, dict) and node.get("type") == "end_node"]
        if len(ends) == 1:
            ends[0].setdefault("config", {})["return_end"] = True
        save_workflow(new_id, copy_data)
        return {"id": new_id, "name": name, "renamed": name != base, "ends": len(ends)}

    def rename_current_workflow(self, name: str) -> bool:
        """Rename and save the active workflow."""
        old_name = self._workflow_map.workflow_name
        if not self._workflow_map.rename_current_workflow(name):
            return False
        if not self.save_current_workflow():
            return False
        _move_saved_values(self._workflow_map.workflow_id, old_name, name)
        return True

    def rename_workflow(self, workflow_id: str, name: str) -> Optional[str]:
        """Rename a saved workflow; return why it can't be, or None.

        Only the name is written: unsaved edits in an open workflow stay
        unsaved (and dirty), so renaming never saves them by surprise.
        """
        data = load_workflow(workflow_id)
        if data is None:
            return "The saved workflow could not be read"
        problem = name_problem(name, exclude_id=workflow_id, callable_=bool(data.get("callable")))
        if problem:
            return problem
        name = name.strip()
        old_name = str(data.get("name") or "")
        data["name"] = name
        save_workflow(workflow_id, data)
        self._workflow_map.set_workflow_name(workflow_id, name)
        _move_saved_values(workflow_id, old_name, name)
        return None

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a persisted workflow and remove it from the open cache."""
        removed = delete_workflow(workflow_id)
        self._workflow_map.close_workflow(workflow_id)
        return removed

    def _workflow_data_with_input_sources(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return workflow save data with derived input source caches."""
        data = json.loads(json.dumps(data))
        nodes = data.get("nodes", {})
        for node_id, sources in derive_input_sources(nodes).items():
            nodes[node_id]["input_sources"] = sources
        return data

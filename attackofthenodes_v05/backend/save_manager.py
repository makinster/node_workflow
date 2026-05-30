"""
Save manager for AttackOfTheNodes.

Coordinates workflow save/load operations so UI code does not need to know
which backend components provide structure, memory, or execution state.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .configuration_manager import ConfigurationManager
from .memory_bank import MemoryBank
from .persistence import delete_workflow, load_workflow, save_workflow
from .validator import derive_input_sources
from .workflow_map import WorkflowMap


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

    def duplicate_workflow(self, workflow_id: Optional[str] = None) -> Optional[str]:
        """Create a persisted copy of a workflow and return the new id."""
        source_id = workflow_id or self._workflow_map.workflow_id
        if source_id is None:
            return None
        if source_id == self._workflow_map.workflow_id:
            data = self._workflow_data_with_input_sources(
                self._workflow_map.get_workflow_data_for_save()
            )
        else:
            data = load_workflow(source_id)
            if data is None:
                return None
            data = self._workflow_data_with_input_sources(data)
        new_id = f"wf_{uuid.uuid4().hex[:12]}"
        copy_data = json.loads(json.dumps(data))
        copy_data["id"] = new_id
        copy_data["name"] = f"{copy_data.get('name', source_id)} (Copy)"
        save_workflow(new_id, copy_data)
        return new_id

    def rename_current_workflow(self, name: str) -> bool:
        """Rename and save the active workflow."""
        if not self._workflow_map.rename_current_workflow(name):
            return False
        return self.save_current_workflow()

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

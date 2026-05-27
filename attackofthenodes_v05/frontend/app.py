"""Application root for the AttackOfTheNodes tkinter UI."""

import tkinter as tk
from tkinter import messagebox
from typing import Optional

from backend.events import (
    ERROR_OCCURRED,
    ERROR_LOGGED,
    MEMORY_UPDATE,
    RECOVERY_OPTIONS_AVAILABLE,
    SUPERVISOR_REGISTER,
    SUPERVISOR_STATE_UPDATE,
    SUPERVISOR_TERMINATING,
    USER_INPUT_NEEDED,
    WORKFLOW_DIRTY,
    WORKFLOW_STATE_UPDATE,
)
from backend.validator import validate_workflow

from .async_tk import AsyncTkPump
from .controls_panel import ControlsPanel
from .editor_panel import EditorPanel
from .execution_panel import ExecutionPanel
from .modals import (
    AboutModal,
    ErrorDetailsModal,
    HelpModal,
    LoadWorkflowModal,
    MemoryViewerModal,
    NodeConfigModal,
    NodeSelectorModal,
    OutputViewerModal,
    RunHistoryModal,
    SettingsModal,
    UserInputModal,
    WorkflowSettingsModal,
)
from .toolbar import Toolbar
from .ui_state import UIState, UI_STATE_CHANGED


class App(tk.Tk):
    """Main tkinter application window."""

    def __init__(
        self,
        event_bus,
        factory,
        workflow_map,
        memory_bank,
        master_state,
        save_manager=None,
    ) -> None:
        super().__init__()
        self.title("AttackOfTheNodes v0.5")
        self.geometry("920x620")
        self.minsize(760, 500)

        self._event_bus = event_bus
        self._factory = factory
        self._workflow_map = workflow_map
        self._memory_bank = memory_bank
        self._master_state = master_state
        self._save_manager = save_manager
        self._configuration_manager = (
            getattr(save_manager, "configuration_manager", None)
            if save_manager is not None
            else None
        )
        self._ui_state = UIState()
        self._ui_state.attach_event_bus(self._event_bus)
        self._async_pump = AsyncTkPump(self, interval_ms=20)
        self._running_task = None
        self._pending_input_queue = []
        self._input_modal_open = False

        self._event_bus.subscribe(UI_STATE_CHANGED, self._on_ui_state_changed)
        self._event_bus.subscribe(WORKFLOW_DIRTY, self._on_dirty_changed)
        self._event_bus.subscribe(WORKFLOW_STATE_UPDATE, self._on_workflow_state_update)
        self._event_bus.subscribe(SUPERVISOR_REGISTER, self._on_supervisor_register)
        self._event_bus.subscribe(SUPERVISOR_STATE_UPDATE, self._on_supervisor_state_update)
        self._event_bus.subscribe(SUPERVISOR_TERMINATING, self._on_supervisor_terminating)
        self._event_bus.subscribe(USER_INPUT_NEEDED, self._on_user_input_needed)
        self._event_bus.subscribe(ERROR_OCCURRED, self._on_error_occurred)
        self._event_bus.subscribe(ERROR_LOGGED, self._on_error_logged)
        self._event_bus.subscribe(
            RECOVERY_OPTIONS_AVAILABLE, self._on_recovery_options_available
        )

        self._build_layout()
        self._ensure_starter_workflow()
        self._refresh_all("Ready")
        self._async_pump.start()
        self._schedule_auto_save()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self.configure(bg="#e2e8f0")
        self._toolbar = Toolbar(
            self,
            on_workflow_library=self._open_load_modal,
            on_save=self._save_workflow,
            on_run=self._run_workflow,
            on_new=self._new_workflow,
            on_errors=self._open_current_errors,
            on_settings=self._open_settings,
            on_workflow_settings=self._open_workflow_settings,
            on_help=self._open_help,
            on_about=self._open_about,
        )
        self._toolbar.pack(side="top", fill="x")

        self._body = tk.Frame(self, bg="#e2e8f0")
        self._body.pack(side="top", fill="both", expand=True)

        self._left_region = tk.Frame(self._body, bg="#ffffff")
        self._left_region.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)

        self._controls_panel = ControlsPanel(
            self._body,
            on_validate=self._validate_workflow,
            on_save=self._save_workflow,
            on_load=self._open_load_modal,
            on_add_node=self._open_node_selector,
            on_run=self._run_workflow,
            on_pause_resume=self._pause_resume_workflow,
            on_stop=self._stop_workflow,
            on_select_supervisor=self._select_supervisor,
            on_view_memory=self._open_memory_viewer,
            on_view_output=self._open_output_viewer,
            on_view_history=self._open_run_history,
            on_jump_to_node=self._jump_to_node,
            get_jump_targets=self._get_jump_targets,
        )
        self._controls_panel.pack(side="right", fill="y", padx=(5, 10), pady=10)

        self._editor_panel = EditorPanel(
            self._left_region,
            self._workflow_map,
            on_node_selected=self._open_node_config,
            on_node_deleted=self._delete_node,
        )
        self._execution_panel = ExecutionPanel(
            self._left_region,
            self._workflow_map,
            self._ui_state,
            on_select_supervisor=self._select_supervisor,
        )
        self._editor_panel.pack(fill="both", expand=True)
        self._bind_shortcuts()

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-s>", lambda _event: self._save_workflow())
        self.bind_all("<Control-r>", lambda _event: self._run_workflow())
        self.bind_all("<Control-R>", lambda _event: self._stop_workflow())
        self.bind_all("<Control-n>", lambda _event: self._new_workflow())
        self.bind_all("<Control-o>", lambda _event: self._open_load_modal())
        self.bind_all("<Control-l>", lambda _event: self._open_load_modal())
        self.bind_all("<Escape>", lambda _event: self.focus_get().winfo_toplevel().destroy() if self.focus_get() and self.focus_get().winfo_toplevel() is not self else None)

    def _ensure_starter_workflow(self) -> None:
        if self._workflow_map.is_loaded:
            return
        if self._save_manager is not None and self._configuration_manager is not None:
            last_id = self._configuration_manager.get("last_active_workflow_id")
            if last_id and self._save_manager.load_workflow(last_id):
                self._ui_state.editor_center_node_id = self._workflow_map.find_start_node_id()
                return
        self._workflow_map.create_new("Untitled Workflow")
        start_id = self._workflow_map.add_node("start_node", alias="Start")
        if start_id:
            self._ui_state.editor_center_node_id = start_id

    def _new_workflow(self) -> None:
        self._workflow_map.create_new("Untitled Workflow")
        start_id = self._workflow_map.add_node("start_node", alias="Start")
        self._ui_state.editor_center_node_id = start_id
        self._refresh_all("New workflow created")

    def _create_named_workflow(self, name: str) -> None:
        self._workflow_map.create_new(name)
        start_id = self._workflow_map.add_node("start_node", alias="Start")
        self._ui_state.editor_center_node_id = start_id
        self._refresh_all("New workflow created")

    def _confirm_discard_dirty(self) -> bool:
        if not self._workflow_map.is_dirty:
            return True
        return messagebox.askyesno(
            "Unsaved Changes",
            "Discard unsaved changes?",
            parent=self,
        )

    def _open_node_selector(self) -> None:
        NodeSelectorModal(self, self._factory, self._add_node)

    def _add_node(self, node_type: str) -> None:
        existing_nodes = self._workflow_map.get_all_node_data()
        previous_tail = self._find_linear_tail()
        node_id = self._workflow_map.add_node(node_type)
        if node_id is None:
            messagebox.showerror("Add Node", f"Unknown node type: {node_type}", parent=self)
            return

        if previous_tail and previous_tail != node_id and existing_nodes:
            target_ports = self._node_input_ports(node_type)
            source_ports = self._node_output_ports(previous_tail)
            if target_ports and source_ports:
                self._workflow_map.connect(
                    previous_tail, source_ports[0], node_id, target_ports[0]
                )

        self._ui_state.editor_center_node_id = node_id
        self._refresh_all("Node added")

    def _find_linear_tail(self) -> Optional[str]:
        nodes = self._workflow_map.get_all_node_data()
        if not nodes:
            return None
        start_id = self._workflow_map.find_start_node_id()
        current = start_id or next(iter(nodes))
        visited = set()
        while current and current in nodes and current not in visited:
            visited.add(current)
            next_id = self._workflow_map.find_next_node_id(current, "default")
            if not next_id:
                return current
            current = next_id
        return current if current in nodes else None

    def _node_input_ports(self, node_type: str):
        for metadata in self._factory.get_node_types_metadata():
            if metadata["type"] == node_type:
                return metadata["input_ports"]
        return []

    def _node_output_ports(self, node_id: str):
        node_data = self._workflow_map.get_node_data(node_id)
        if not node_data:
            return []
        for metadata in self._factory.get_node_types_metadata():
            if metadata["type"] == node_data["type"]:
                return metadata["output_ports"]
        return []

    def _open_node_config(self, node_id: str) -> None:
        node_data = self._workflow_map.get_node_data(node_id)
        if node_data is None:
            return
        NodeConfigModal(
            self,
            node_id,
            node_data,
            self._factory,
            self._save_node_config,
            workflow_map=self._workflow_map,
        )

    def _delete_node(self, node_id: str) -> None:
        node_data = self._workflow_map.get_node_data(node_id)
        if node_data is None:
            return
        label = node_data.get("alias") or node_data.get("type") or node_id
        confirmed = messagebox.askyesno(
            "Delete Node",
            f"Delete node '{label}'?",
            parent=self,
        )
        if not confirmed:
            return
        if self._workflow_map.delete_node(node_id):
            self._ui_state.node_statuses.pop(node_id, None)
            self._refresh_all("Node deleted")

    def _save_node_config(self, node_id: str, alias: str, config) -> None:
        self._workflow_map.update_node_alias(node_id, alias)
        self._workflow_map.update_node_config(node_id, config)
        self._refresh_all("Node updated")

    def _validate_workflow(self) -> None:
        result = validate_workflow(self._workflow_map, self._factory)
        self._ui_state.validation_status = result
        self._editor_panel.set_validation_status(result)
        if result["success"]:
            message = f"Valid. Warnings: {len(result['warnings'])}"
        else:
            message = f"Invalid. Errors: {len(result['errors'])}"
        self._refresh_all(message)
        if not result["success"]:
            details = "\n".join(error["message"] for error in result["errors"])
            messagebox.showerror("Validation", details, parent=self)

    def _run_workflow(self) -> None:
        result = validate_workflow(self._workflow_map, self._factory)
        self._ui_state.validation_status = result
        self._editor_panel.set_validation_status(result)
        if not result["success"]:
            details = "\n".join(error["message"] for error in result["errors"])
            messagebox.showerror("Validation", details, parent=self)
            self._refresh_all(f"Invalid. Errors: {len(result['errors'])}")
            return

        self._ui_state.node_statuses.clear()
        self._ui_state.supervisor_nodes.clear()
        self._ui_state.active_supervisors.clear()
        self._ui_state.selected_supervisor_id = None
        self._controls_panel.set_status("Running")
        self._running_task = self._async_pump.create_task(
            self._master_state.start_workflow()
        )

    def _pause_resume_workflow(self) -> None:
        if self._master_state.state.value == "PAUSED":
            self._master_state.resume()
            self._controls_panel.set_status("Running")
        else:
            self._master_state.pause()
            self._controls_panel.set_status("Paused")

    def _stop_workflow(self) -> None:
        self._master_state.stop()
        self._controls_panel.set_status("Stopping")

    def _select_supervisor(self, branch_id: str) -> None:
        if not branch_id:
            return
        self._ui_state.selected_supervisor_id = branch_id
        self._execution_panel.refresh()

    def _open_memory_viewer(self) -> None:
        MemoryViewerModal(self, self._memory_bank, self._event_bus, MEMORY_UPDATE)

    def _open_output_viewer(self) -> None:
        outputs = list(self._master_state.run_outputs)
        if not outputs:
            outputs = list(self._memory_bank.read_persistent("output_log", default=[]))
        OutputViewerModal(self, outputs)

    def _open_run_history(self) -> None:
        RunHistoryModal(self, self._master_state.run_history.list_runs())

    def _get_jump_targets(self, filter_name: str):
        nodes = self._workflow_map.get_nodes_by_filter(filter_name)
        return [
            {"id": node_id, **data}
            for node_id, data in nodes.items()
        ]

    def _jump_to_node(self, node_id: str) -> None:
        self._ui_state.editor_center_node_id = node_id
        self._editor_panel.scroll_to_node(node_id)
        self._controls_panel.set_status(f"Jumped to {node_id}")

    def _open_settings(self) -> None:
        if self._configuration_manager is None:
            messagebox.showinfo("Settings", "Settings manager is not available.", parent=self)
            return
        SettingsModal(self, self._configuration_manager)

    def _open_help(self) -> None:
        HelpModal(self, self._factory)

    def _open_about(self) -> None:
        AboutModal(self)

    def _open_workflow_settings(self) -> None:
        if self._save_manager is None:
            messagebox.showinfo("Workflow Settings", "Save manager is not available.", parent=self)
            return
        WorkflowSettingsModal(
            self,
            self._workflow_map,
            self._save_manager,
            self._refresh_all,
            self._after_active_workflow_deleted,
        )

    def _open_current_errors(self) -> None:
        run_id = self._master_state.current_run_id
        errors = self._master_state.error_handler.get_errors_for_run(run_id) if run_id else []
        if errors:
            payload = {
                "branch_id": errors[-1].get("branch_id") or "",
                "node_id": errors[-1].get("node_id") or "",
                "category": errors[-1].get("category") or "UNKNOWN",
                "error_message": errors[-1].get("message") or "",
                "traceback": errors[-1].get("traceback") or "",
                "options": [],
            }
            ErrorDetailsModal(self, payload, self._submit_recovery_action)
        else:
            messagebox.showinfo("Errors", "No errors for the current run.", parent=self)

    def _save_workflow(self) -> None:
        if self._save_manager is not None:
            self._save_manager.save_current_workflow()
        else:
            self._workflow_map.save()
        self._refresh_all("Workflow saved")

    def _open_load_modal(self) -> None:
        LoadWorkflowModal(
            self,
            self._load_workflow,
            on_new=self._create_named_workflow,
            on_delete=self._delete_workflow_from_library,
            on_duplicate=self._duplicate_workflow_from_library,
            on_export=self._export_workflow_from_library,
            on_import=self._import_workflow_from_library,
            get_open_workflows=self._workflow_map.get_open_workflows,
            on_switch_open=self._switch_open_workflow,
        )

    def _load_workflow(self, workflow_id: str) -> bool:
        if workflow_id == self._workflow_map.workflow_id and self._workflow_map.is_dirty:
            if not self._confirm_discard_dirty():
                return False
        if self._save_manager is not None:
            loaded = self._save_manager.load_workflow(workflow_id)
        else:
            loaded = self._workflow_map.load(workflow_id)
        if loaded:
            self._ui_state.editor_center_node_id = self._workflow_map.find_start_node_id()
            self._refresh_all("Workflow loaded")
        return loaded

    def _switch_open_workflow(self, workflow_id: str) -> bool:
        switched = self._workflow_map.switch_active_workflow(workflow_id)
        if switched and self._configuration_manager is not None:
            self._configuration_manager.set("last_active_workflow_id", workflow_id)
        if switched:
            self._ui_state.editor_center_node_id = self._workflow_map.find_start_node_id()
            self._refresh_all("Workflow switched")
        return switched

    def _delete_workflow_from_library(self, workflow_id: str) -> bool:
        was_active = workflow_id == self._workflow_map.workflow_id
        if self._save_manager is not None:
            deleted = self._save_manager.delete_workflow(workflow_id)
        else:
            from backend.persistence import delete_workflow

            deleted = delete_workflow(workflow_id)
        if was_active:
            self._after_active_workflow_deleted()
        return deleted

    def _duplicate_workflow_from_library(self, workflow_id: str):
        if self._save_manager is None:
            return None
        return self._save_manager.duplicate_workflow(workflow_id)

    def _export_workflow_from_library(self, workflow_id: str, path: str) -> bool:
        if self._save_manager is None:
            return False
        return self._save_manager.export_workflow(workflow_id, path)

    def _import_workflow_from_library(self, path: str):
        if self._save_manager is None:
            return None
        return self._save_manager.import_workflow(path)

    def _after_active_workflow_deleted(self) -> None:
        if not self._workflow_map.is_loaded:
            self._workflow_map.create_new("Untitled Workflow")
            start_id = self._workflow_map.add_node("start_node", alias="Start")
            self._ui_state.editor_center_node_id = start_id
        self._refresh_all("Workflow deleted")

    def _on_dirty_changed(self, is_dirty: bool) -> None:
        self._ui_state.set_dirty(bool(is_dirty))
        self._refresh_toolbar()
        self._editor_panel.refresh()
        self._execution_panel.refresh()
        self._controls_panel.set_dirty(self._ui_state.is_dirty)

    def _on_workflow_state_update(self, payload) -> None:
        state = payload.get("state", "IDLE") if payload else "IDLE"
        self._ui_state.set_run_state(state)
        if state == "FINISHED":
            self._controls_panel.set_status("Run finished")
        elif state == "ERROR":
            self._controls_panel.set_status("Run errored")
        elif state == "WAITING_FOR_INPUT":
            self._controls_panel.set_status("Waiting for input")
        self._refresh_panel_mode()
        self._controls_panel.set_mode(self._ui_state.mode, state)
        self._controls_panel.set_workflow_state(state)
        self._execution_panel.refresh()

    def _on_ui_state_changed(self, _payload) -> None:
        self._refresh_toolbar()

    def _on_supervisor_register(self, payload) -> None:
        branch_id = payload["branch_id"]
        if branch_id not in [item["branch_id"] for item in self._ui_state.active_supervisors]:
            self._ui_state.active_supervisors.append(
                {
                    "branch_id": branch_id,
                    "state": "IDLE",
                    "current_node_id": "",
                    "depth": str(payload.get("depth", 0)),
                }
            )
        if self._ui_state.selected_supervisor_id is None:
            self._ui_state.selected_supervisor_id = branch_id
        self._refresh_supervisor_controls()

    def _on_supervisor_state_update(self, payload) -> None:
        branch_id = payload["branch_id"]
        new_node = payload.get("current_node_id")
        previous_node = self._ui_state.supervisor_nodes.get(branch_id)
        if previous_node and previous_node != new_node:
            self._ui_state.node_statuses[previous_node] = "done"
        if new_node:
            status = "waiting" if payload["state"] == "WAITING_FOR_INPUT" else "running"
            if payload["state"] == "TERMINATED":
                status = "done"
            self._ui_state.node_statuses[new_node] = status
            self._ui_state.supervisor_nodes[branch_id] = new_node

        for item in self._ui_state.active_supervisors:
            if item["branch_id"] == branch_id:
                item["state"] = payload["state"]
                item["current_node_id"] = new_node or ""
                break
        self._refresh_supervisor_controls()
        self._execution_panel.refresh()

    def _on_supervisor_terminating(self, payload) -> None:
        branch_id = payload["branch_id"]
        node_id = self._ui_state.supervisor_nodes.get(branch_id)
        if node_id:
            self._ui_state.node_statuses[node_id] = (
                "error" if payload.get("final_state") == "ERROR" else "done"
            )
        self._ui_state.active_supervisors = [
            item
            for item in self._ui_state.active_supervisors
            if item["branch_id"] != branch_id
        ]
        if self._ui_state.selected_supervisor_id == branch_id:
            self._ui_state.selected_supervisor_id = (
                self._ui_state.active_supervisors[0]["branch_id"]
                if self._ui_state.active_supervisors
                else None
            )
        self._refresh_supervisor_controls()
        self._execution_panel.refresh()

    def _on_user_input_needed(self, payload) -> None:
        self._pending_input_queue.append(dict(payload))
        self._show_next_user_input()

    def _show_next_user_input(self) -> None:
        if self._input_modal_open or not self._pending_input_queue:
            return
        payload = self._pending_input_queue.pop(0)
        self._input_modal_open = True
        UserInputModal(
            self,
            payload["branch_id"],
            payload.get("node_id", ""),
            payload.get("prompt", "Input required"),
            self._submit_user_input,
        )

    def _submit_user_input(self, branch_id: str, value: str) -> None:
        self._master_state.submit_user_input(branch_id, value)
        self._input_modal_open = False
        self.after(0, self._show_next_user_input)

    def _on_recovery_options_available(self, payload) -> None:
        ErrorDetailsModal(self, payload, self._submit_recovery_action)

    def _submit_recovery_action(self, branch_id: str, action: str) -> None:
        if branch_id:
            self._master_state.submit_recovery_action(branch_id, action)

    def _on_error_logged(self, payload) -> None:
        self._toolbar.set_error_count(int(payload.get("error_count", 0)))

    def _on_error_occurred(self, payload) -> None:
        node_id = payload.get("node_id")
        if node_id:
            self._ui_state.node_statuses[node_id] = "error"
        messagebox.showerror("Execution Error", payload.get("error", "Unknown error"), parent=self)
        self._execution_panel.refresh()

    def _refresh_supervisor_controls(self) -> None:
        supervisors = [item["branch_id"] for item in self._ui_state.active_supervisors]
        self._controls_panel.set_supervisors(
            supervisors, self._ui_state.selected_supervisor_id
        )

    def _refresh_all(self, status: str = "") -> None:
        self._ui_state.set_workflow_identity(
            self._workflow_map.workflow_id, self._workflow_map.workflow_name
        )
        self._ui_state.set_dirty(self._workflow_map.is_dirty)
        self._refresh_toolbar()
        self._refresh_panel_mode()
        self._editor_panel.refresh()
        self._execution_panel.refresh()
        self._controls_panel.set_dirty(self._ui_state.is_dirty)
        self._controls_panel.set_mode(
            self._ui_state.mode, self._ui_state.workflow_run_state
        )
        self._controls_panel.refresh_jump_targets()
        if status:
            self._controls_panel.set_status(status)

    def _refresh_toolbar(self) -> None:
        self._toolbar.update_state(
            self._workflow_map.workflow_name or "No Workflow",
            self._workflow_map.workflow_id or "",
            self._workflow_map.is_dirty,
            self._ui_state.mode,
        )

    def _refresh_panel_mode(self) -> None:
        if self._ui_state.mode == "execution":
            self._editor_panel.pack_forget()
            self._execution_panel.pack(fill="both", expand=True)
        else:
            self._execution_panel.pack_forget()
            self._editor_panel.pack(fill="both", expand=True)

    def _schedule_auto_save(self) -> None:
        interval_seconds = 60
        if self._configuration_manager is not None:
            interval_seconds = int(
                self._configuration_manager.get("auto_save_interval_seconds") or 60
            )
        self.after(max(1, interval_seconds) * 1000, self._auto_save_tick)

    def _auto_save_tick(self) -> None:
        if (
            self._save_manager is not None
            and self._configuration_manager is not None
            and self._configuration_manager.get("auto_save_enabled")
            and self._workflow_map.is_dirty
        ):
            self._save_manager.save_current_workflow()
            self._refresh_all("Auto-saved")
        self._schedule_auto_save()

    def _on_close(self) -> None:
        if self._workflow_map.is_dirty:
            choice = messagebox.askyesnocancel(
                "Unsaved Changes",
                "Save the current workflow before closing?",
                parent=self,
            )
            if choice is None:
                return
            if choice:
                self._save_workflow()
        self._master_state.stop()
        self._async_pump.stop()
        self.destroy()

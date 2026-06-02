"""Textual application root for the AttackOfTheNodes TUI."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App as TextualApp, ScreenStackError
from textual.binding import Binding
from textual.css.query import NoMatches

from backend.events import (
    ERROR_OCCURRED,
    ERROR_LOGGED,
    MEMORY_UPDATE,
    NODE_TIMING_UPDATE,
    RECOVERY_OPTIONS_AVAILABLE,
    SUPERVISOR_REGISTER,
    SUPERVISOR_STATE_UPDATE,
    SUPERVISOR_TERMINATING,
    USER_INPUT_NEEDED,
    WORKFLOW_DIRTY,
    WORKFLOW_STATE_UPDATE,
)

from . import notifications
from .screens.editor import EditorScreen
from .screens.confirm import ConfirmScreen
from .screens.error_details import ErrorDetailsScreen
from .screens.execution import ExecutionScreen
from .screens.help import HelpScreen
from .screens.settings import SettingsScreen
from .screens.user_input import UserInputScreen
from .screens.workflow_library import PathPromptScreen, WorkflowLibraryScreen


class AttackOfTheNodesApp(TextualApp):
    """Main Textual app shell.

    The backend stack is injected by ``main.py`` exactly as the tkinter app was.
    This class owns frontend subscriptions and screen switching only.
    """

    CSS_PATH = "styles.tcss"
    TITLE = "AttackOfTheNodes"
    SUB_TITLE = "Textual TUI"

    BINDINGS = [
        ("ctrl+s", "save_workflow", "Save"),
        ("ctrl+r", "run_workflow", "Run"),
        ("ctrl+n", "new_workflow", "New"),
        ("ctrl+o", "workflow_library", "Open"),
        ("ctrl+e", "settings", "Settings"),
        ("?", "help", "Help"),
        ("q", "back", "Back"),
        Binding("ctrl+q", "back", "Back", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True, show=False),
    ]

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
        self.event_bus = event_bus
        self.factory = factory
        self.workflow_map = workflow_map
        self.memory_bank = memory_bank
        self.master_state = master_state
        self.save_manager = save_manager
        self.configuration_manager = (
            getattr(save_manager, "configuration_manager", None)
            if save_manager is not None
            else None
        )
        self.workflow_state = "IDLE"
        self.node_statuses = {}
        self.node_timings = {}
        self.supervisors = {}
        self._branch_current_nodes = {}
        self._user_input_modal_open = False
        self._error_modal_open = False
        self._subscribe_to_backend_events()

    async def on_mount(self) -> None:
        """Create/load a workflow and show the editor screen."""
        self._ensure_starter_workflow()
        await self.push_screen(self._build_editor_screen())

    def _build_editor_screen(self) -> EditorScreen:
        return EditorScreen(
            factory=self.factory,
            workflow_map=self.workflow_map,
            save_manager=self.save_manager,
        )

    def show_editor_screen(self) -> None:
        """Return to the editor view."""
        self.stop_active_workflow()
        self.switch_screen(self._build_editor_screen())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        from frontend.widgets.command_input import CommandInput, CommandTextArea
        if action == "back":
            focused = self.focused
            if isinstance(focused, (CommandInput, CommandTextArea)) and getattr(focused, "editing", False):
                return False
        return True

    def action_back(self) -> None:
        """Go back from secondary screens, or quit from the editor."""
        if isinstance(self.screen, EditorScreen):
            self.exit()
        else:
            self.show_editor_screen()

    def _subscribe_to_backend_events(self) -> None:
        """Attach event handlers used by current and future TUI screens."""
        subscriptions = {
            WORKFLOW_DIRTY: self._on_backend_event,
            WORKFLOW_STATE_UPDATE: self._on_workflow_state_update,
            NODE_TIMING_UPDATE: self._on_node_timing_update,
            SUPERVISOR_REGISTER: self._on_supervisor_register,
            SUPERVISOR_STATE_UPDATE: self._on_supervisor_state_update,
            SUPERVISOR_TERMINATING: self._on_supervisor_terminating,
            USER_INPUT_NEEDED: self._on_user_input_needed,
            ERROR_OCCURRED: self._on_backend_event,
            ERROR_LOGGED: self._on_backend_event,
            RECOVERY_OPTIONS_AVAILABLE: self._on_recovery_options_available,
            MEMORY_UPDATE: self._on_backend_event,
        }
        for event_name, callback in subscriptions.items():
            self.event_bus.subscribe(event_name, callback)

    def _on_backend_event(self, _payload=None) -> None:
        """Ask the active screen to refresh itself after backend changes."""
        try:
            screen = self.screen
        except ScreenStackError:
            return
        if not getattr(screen, "is_mounted", False):
            return
        refresh = getattr(screen, "refresh_from_backend", None)
        if refresh is not None:
            try:
                refresh()
            except NoMatches:
                return

    def _on_workflow_state_update(self, payload=None) -> None:
        payload = payload or {}
        previous_state = self.workflow_state
        self.workflow_state = payload.get("state", self.workflow_state)
        if self.workflow_state == "IDLE":
            self._reset_run_display_state()
        elif self.workflow_state == "RUNNING" and previous_state in {"IDLE", "FINISHED", "ERROR"}:
            self._reset_run_display_state()
        self._on_backend_event(payload)

    def _on_supervisor_register(self, payload=None) -> None:
        payload = payload or {}
        branch_id = payload.get("branch_id")
        if branch_id:
            self.supervisors[branch_id] = {
                "state": "RUNNING",
                "depth": payload.get("depth", 0),
                "current_node_id": None,
            }
        self._on_backend_event(payload)

    def _on_supervisor_state_update(self, payload=None) -> None:
        payload = payload or {}
        branch_id = payload.get("branch_id")
        state = payload.get("state", "")
        current_node_id = payload.get("current_node_id")

        previous_node_id = self._branch_current_nodes.get(branch_id)
        if previous_node_id and previous_node_id != current_node_id:
            self.node_statuses[previous_node_id] = "done"

        if current_node_id:
            if state == "WAITING_FOR_INPUT":
                self.node_statuses[current_node_id] = "waiting"
            elif state == "AWAITING_RECOVERY":
                self.node_statuses[current_node_id] = "errored"
            elif state == "ERROR":
                self.node_statuses[current_node_id] = "errored"
            elif state == "TERMINATED":
                self.node_statuses[current_node_id] = "done"
            else:
                self.node_statuses[current_node_id] = "running"

        if branch_id:
            self._branch_current_nodes[branch_id] = current_node_id
            self.supervisors.setdefault(branch_id, {})
            self.supervisors[branch_id].update(
                {"state": state, "current_node_id": current_node_id}
            )
        self._on_backend_event(payload)

    def _on_node_timing_update(self, payload=None) -> None:
        payload = payload or {}
        node_id = payload.get("node_id")
        if node_id:
            seconds = float(payload.get("seconds") or 0.0)
            self.node_timings[node_id] = self.node_timings.get(node_id, 0.0) + seconds
        self._on_backend_event(payload)

    def _on_supervisor_terminating(self, payload=None) -> None:
        payload = payload or {}
        branch_id = payload.get("branch_id")
        current_node_id = self._branch_current_nodes.get(branch_id)
        if current_node_id:
            self.node_statuses[current_node_id] = "done"
        if branch_id in self.supervisors:
            self.supervisors[branch_id]["state"] = payload.get("final_state", "TERMINATED")
        self._on_backend_event(payload)

    def _on_user_input_needed(self, payload=None) -> None:
        payload = payload or {}
        node_id = payload.get("node_id")
        if node_id:
            self.node_statuses[node_id] = "waiting"
        if not self._user_input_modal_open:
            self._user_input_modal_open = True
            self.push_screen(
                UserInputScreen(
                    branch_id=payload.get("branch_id", ""),
                    node_id=payload.get("node_id", ""),
                    prompt=payload.get("prompt", ""),
                ),
                self._submit_user_input_from_modal,
            )
        self._on_backend_event(payload)

    def _on_recovery_options_available(self, payload=None) -> None:
        payload = payload or {}
        node_id = payload.get("node_id")
        if node_id:
            self.node_statuses[node_id] = "errored"
        if not self._error_modal_open:
            self._error_modal_open = True
            self.push_screen(
                ErrorDetailsScreen(payload),
                self._submit_recovery_from_modal,
            )
        self._on_backend_event(payload)

    def _submit_user_input_from_modal(self, result) -> None:
        self._user_input_modal_open = False
        if not result:
            return
        self.master_state.submit_user_input(result["branch_id"], result["value"])

    def _submit_recovery_from_modal(self, result) -> None:
        self._error_modal_open = False
        if not result:
            return
        self.master_state.submit_recovery_action(result["branch_id"], result["action"])

    def _reset_run_display_state(self) -> None:
        self.node_statuses = {}
        self.node_timings = {}
        self.supervisors = {}
        self._branch_current_nodes = {}

    def _ensure_starter_workflow(self) -> None:
        """Load the last workflow when possible, otherwise create a starter graph."""
        if self.workflow_map.is_loaded:
            return
        if self.save_manager is not None and self.configuration_manager is not None:
            last_id = self.configuration_manager.get("last_active_workflow_id")
            if last_id and self.save_manager.load_workflow(last_id):
                return
        self.workflow_map.create_new("Untitled Workflow")
        self.workflow_map.add_node("start_node", alias="Start")

    def action_save_workflow(self) -> None:
        """Save the active workflow."""
        if self.save_manager is not None:
            self.save_manager.save_current_workflow()
        else:
            self.workflow_map.save()
        notifications.workflow_saved(self)

    def action_run_workflow(self) -> None:
        """Start workflow execution and show the execution screen."""
        if self.workflow_state in {"RUNNING", "PAUSED", "WAITING_FOR_INPUT"}:
            notifications.workflow_already_running(self)
            return
        self._reset_run_display_state()
        self.switch_screen(
            ExecutionScreen(
                workflow_map=self.workflow_map,
                memory_bank=self.memory_bank,
                master_state=self.master_state,
            )
        )
        self.set_timer(0.1, lambda: asyncio.create_task(self._start_workflow()))

    async def _start_workflow(self) -> None:
        started = await self.master_state.start_workflow()
        if not started:
            notifications.workflow_start_failed(self)

    def stop_active_workflow(self) -> None:
        """Stop a run when leaving execution-oriented screens."""
        if self.workflow_state in {"RUNNING", "PAUSED", "WAITING_FOR_INPUT"}:
            self.master_state.stop()
            self.workflow_state = "IDLE"
            self._reset_run_display_state()
            notifications.workflow_stopped(self)

    def action_new_workflow(self) -> None:
        """Create a fresh starter workflow."""
        if self.workflow_map.is_dirty:
            self.push_screen(
                ConfirmScreen(
                    "The current workflow has unsaved changes.\n"
                    "Create a new workflow and discard them?",
                    yes_label="Discard",
                    no_label="Cancel",
                ),
                lambda confirmed: self._create_new_workflow() if confirmed else None,
            )
            return
        self._create_new_workflow()

    def _create_new_workflow(self) -> None:
        """Create a fresh starter workflow without additional confirmation."""
        self.stop_active_workflow()
        self.workflow_map.create_new("Untitled Workflow")
        self.workflow_map.add_node("start_node", alias="Start")
        self._on_backend_event()
        notifications.workflow_created(self)

    def action_workflow_library(self) -> None:
        """Open the workflow library modal."""
        self.push_screen(WorkflowLibraryScreen(), self._handle_workflow_library_action)

    def action_settings(self) -> None:
        """Open settings modal."""
        if self.configuration_manager is None:
            notifications.settings_unavailable(self)
            return
        self.push_screen(
            SettingsScreen(self.configuration_manager),
            self._handle_settings_action,
        )

    def action_help(self) -> None:
        """Open help modal."""
        self.push_screen(HelpScreen())

    def _handle_workflow_library_action(self, result) -> None:
        if not result:
            return
        action = result.get("action")
        if action == "new":
            self.action_new_workflow()
            return
        if action == "import":
            self._prompt_import_workflow()
            return
        workflow_id = result.get("workflow_id")
        if not workflow_id:
            return
        if action == "load":
            if self.workflow_map.is_dirty:
                workflow_name = result.get("workflow_name", workflow_id)
                self.push_screen(
                    ConfirmScreen(
                        "The current workflow has unsaved changes.\n"
                        f"Load '{workflow_name}' and discard them?",
                        yes_label="Discard",
                        no_label="Cancel",
                    ),
                    lambda confirmed: self._load_workflow_from_library(result)
                    if confirmed
                    else None,
                )
                return
            self._load_workflow_from_library(result)
        elif action == "duplicate":
            if self.save_manager is None:
                notifications.missing_service(self, "Duplicate")
                return
            new_id = self.save_manager.duplicate_workflow(workflow_id)
            if new_id:
                self.save_manager.load_workflow(new_id)
                self.show_editor_screen()
                notifications.workflow_duplicated(self)
        elif action == "delete":
            workflow_name = result.get("workflow_name", workflow_id)
            self.push_screen(
                ConfirmScreen(
                    f"Delete '{workflow_name}'?\nThis cannot be undone.",
                    yes_label="Delete",
                    no_label="Cancel",
                ),
                lambda confirmed: self._delete_workflow_from_library(result)
                if confirmed
                else None,
            )
        elif action == "export":
            self._prompt_export_workflow(result)

    def _load_workflow_from_library(self, result) -> None:
        workflow_id = result.get("workflow_id")
        if not workflow_id:
            return
        self.stop_active_workflow()
        loaded = (
            self.save_manager.load_workflow(workflow_id)
            if self.save_manager is not None
            else self.workflow_map.load(workflow_id)
        )
        if loaded:
            self.show_editor_screen()
            notifications.workflow_loaded(self, result.get("workflow_name", workflow_id))
        else:
            notifications.workflow_load_failed(self)

    def _delete_workflow_from_library(self, result) -> None:
        if self.save_manager is None:
            notifications.missing_service(self, "Delete")
            return
        workflow_id = result.get("workflow_id")
        if not workflow_id:
            return
        if workflow_id == self.workflow_map.workflow_id:
            self.workflow_map.create_new("Untitled Workflow")
            self.workflow_map.add_node("start_node", alias="Start")
        deleted = self.save_manager.delete_workflow(workflow_id)
        self.show_editor_screen()
        notifications.workflow_deleted(self, deleted)

    def _prompt_export_workflow(self, result) -> None:
        if self.save_manager is None:
            notifications.missing_service(self, "Export")
            return
        workflow_id = result.get("workflow_id")
        if not workflow_id:
            return
        default_path = str(Path.cwd() / f"{workflow_id}.json")
        self.push_screen(
            PathPromptScreen("Export workflow JSON", default_path),
            lambda path: self._export_workflow_to_path(result, path),
        )

    def _export_workflow_to_path(self, result, path: str | None) -> None:
        if not path or self.save_manager is None:
            return
        workflow_id = result.get("workflow_id")
        if not workflow_id:
            return
        try:
            exported = self.save_manager.export_workflow(workflow_id, path)
        except OSError as exc:
            notifications.workflow_export_failed(self, exc)
            return
        notifications.workflow_exported(self, path, exported)

    def _prompt_import_workflow(self) -> None:
        if self.save_manager is None:
            notifications.missing_service(self, "Import")
            return
        self.push_screen(
            PathPromptScreen("Import workflow JSON"),
            self._import_workflow_from_path,
        )

    def _import_workflow_from_path(self, path: str | None) -> None:
        if not path or self.save_manager is None:
            return
        try:
            workflow_id = self.save_manager.import_workflow(path)
        except (OSError, ValueError) as exc:
            notifications.workflow_import_failed(self, f"Import failed: {exc}")
            return
        if not workflow_id:
            notifications.workflow_import_failed(self)
            return
        result = {"workflow_id": workflow_id, "workflow_name": "Imported Workflow"}
        if self.workflow_map.is_dirty:
            self.push_screen(
                ConfirmScreen(
                    "The current workflow has unsaved changes.\n"
                    "Load the imported workflow and discard them?",
                    yes_label="Discard",
                    no_label="Stay",
                ),
                lambda confirmed: self._load_workflow_from_library(result)
                if confirmed
                else notifications.workflow_imported(self),
            )
            return
        self._load_workflow_from_library(result)

    def _handle_settings_action(self, result) -> None:
        if not result or result.get("action") != "save":
            return
        if self.configuration_manager is None:
            return
        for key, value in result.get("settings", {}).items():
            self.configuration_manager.set(key, value)
        notifications.settings_saved(self)


App = AttackOfTheNodesApp

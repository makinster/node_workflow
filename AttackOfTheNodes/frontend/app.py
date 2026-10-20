"""Textual application root for the AttackOfTheNodes TUI."""

from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path

from textual.app import App as TextualApp, ScreenStackError
from textual.css.query import NoMatches

from backend.events import (
    ERROR_OCCURRED,
    ERROR_LOGGED,
    FILE_VIEW_REQUESTED,
    MEMORY_UPDATE,
    NODE_EXECUTION_UPDATE,
    NODE_TIMING_UPDATE,
    RECOVERY_OPTIONS_AVAILABLE,
    SUBWORKFLOW_RUN_ENDED,
    SUBWORKFLOW_RUN_UPDATE,
    SUPERVISOR_REGISTER,
    SUPERVISOR_STATE_UPDATE,
    SUPERVISOR_TERMINATING,
    USER_INPUT_NEEDED,
    WORKFLOW_DIRTY,
    WORKFLOW_STATE_UPDATE,
)
from backend.workflow_names import DEFAULT_NAME, name_problem, unused_name

from .child_runs import ChildRuns
from .execution_state import ExecutionDisplayState
from . import file_io
from . import notifications
from .editor_workflow_adapter import EditorWorkflowAdapter
from .node_types import START_NODE_TYPE
from .widgets.cursor_state import CursorState
from frontend.keymap import APP, bindings_for
from frontend.keymap_runtime import KeymapScreenMixin
from .screens.editor import EditorScreen
from .screens.confirm import ConfirmScreen
from .screens.error_details import ErrorDetailsScreen
from .screens.execution import ExecutionScreen
from .screens.file_viewer import FileViewerScreen
from .screens.help import HelpScreen
from .screens.settings import SettingsScreen
from .screens.stash import StashScreen
from .screens.user_input import UserInputScreen
from .screens.workflow_library import NamePromptScreen, PathPromptScreen, WorkflowLibraryScreen


# Run telemetry (node/supervisor/timing/memory updates) only marks the active
# screen dirty; one refresh runs per interval instead of one per event. Events
# that need the user, or that change the run state, refresh at once.
REFRESH_COALESCE_SECONDS = 0.075


class AttackOfTheNodesApp(KeymapScreenMixin, TextualApp):
    """Main Textual app shell.

    The backend stack is injected by ``main.py`` exactly as the tkinter app was.
    This class owns frontend subscriptions and screen switching only.
    """

    CSS_PATH = "styles.tcss"
    TITLE = "AttackOfTheNodes"
    SUB_TITLE = "Textual TUI"

    KEYMAP = APP
    BINDINGS = bindings_for(KEYMAP)

    def __init__(
        self,
        event_bus,
        factory,
        workflow_map,
        memory_bank,
        master_state,
        save_manager=None,
        secrets_manager=None,
        stash_manager=None,
    ) -> None:
        super().__init__()
        self.event_bus = event_bus
        self.factory = factory
        self.workflow_map = workflow_map
        self.memory_bank = memory_bank
        self.master_state = master_state
        self.save_manager = save_manager
        self.secrets_manager = secrets_manager
        self.stash_manager = stash_manager
        self.configuration_manager = (
            getattr(save_manager, "configuration_manager", None)
            if save_manager is not None
            else None
        )
        self.workflow_state = "IDLE"
        self.execution_state = ExecutionDisplayState()
        # Step 4c-2: each running subworkflow call, shown on request.
        self.child_runs = ChildRuns()
        self._retired_display_run_id = None
        self.node_statuses = {}
        self.node_skip_reasons = {}
        self.node_timings = {}
        self.supervisors = {}
        self._branch_current_nodes = {}
        self._user_input_modal_open = False
        # C19: prompts wait here and show one at a time, in arrival order.
        self._user_input_requests = deque()
        self._error_modal_open = False
        self._file_viewer_open = False
        self._file_view_requests = deque()
        self._editor_deleted_nodes = {}
        self.cursor_state = CursorState()
        self._refresh_dirty = False
        self._refresh_timer = None
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
            secrets_manager=self.secrets_manager,
        )

    def show_editor_screen(self) -> None:
        """Return to the editor view."""
        self.stop_active_workflow()
        self.switch_screen(self._build_editor_screen())

    def action_back(self) -> None:
        """Go back from secondary screens, or quit from the editor."""
        if isinstance(self.screen, EditorScreen):
            self.exit()
        else:
            self.show_editor_screen()

    def _subscribe_to_backend_events(self) -> None:
        """Attach event handlers used by current and future TUI screens."""
        subscriptions = {
            WORKFLOW_DIRTY: self.flush_refresh,
            WORKFLOW_STATE_UPDATE: self._on_workflow_state_update,
            NODE_EXECUTION_UPDATE: self._on_node_execution_update,
            NODE_TIMING_UPDATE: self._on_node_timing_update,
            SUPERVISOR_REGISTER: self._on_supervisor_register,
            SUPERVISOR_STATE_UPDATE: self._on_supervisor_state_update,
            SUPERVISOR_TERMINATING: self._on_supervisor_terminating,
            USER_INPUT_NEEDED: self._on_user_input_needed,
            FILE_VIEW_REQUESTED: self._on_file_view_requested,
            ERROR_OCCURRED: self.flush_refresh,
            ERROR_LOGGED: self.flush_refresh,
            RECOVERY_OPTIONS_AVAILABLE: self._on_recovery_options_available,
            MEMORY_UPDATE: self.schedule_refresh,
            SUBWORKFLOW_RUN_UPDATE: self._on_subworkflow_run_update,
            SUBWORKFLOW_RUN_ENDED: self._on_subworkflow_run_ended,
        }
        for event_name, callback in subscriptions.items():
            self.event_bus.subscribe(event_name, callback)

    def schedule_refresh(self, _payload=None) -> None:
        """Mark the active screen dirty; refresh it on the coalescing timer."""
        self._refresh_dirty = True
        if self._refresh_timer is not None:
            return
        if not self.is_running:
            # No event loop driving timers (handlers called directly).
            self.flush_refresh()
            return
        self._refresh_timer = self.set_timer(
            REFRESH_COALESCE_SECONDS, self._on_refresh_timer
        )

    def _on_refresh_timer(self) -> None:
        self._refresh_timer = None
        if self._refresh_dirty:
            self.flush_refresh()

    def flush_refresh(self, _payload=None) -> None:
        """Refresh the active screen now and drop any pending coalesced refresh."""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None
        self._refresh_dirty = False
        self._on_backend_event()

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
        run_id = payload.get("run_id")
        state = payload.get("state", self.workflow_state)
        if (run_id != self.master_state.current_run_id
                or run_id == self._retired_display_run_id):
            return
        if state == "RUNNING" and run_id != self.execution_state.run_id:
            self._reset_run_display_state()
            self.execution_state.reset(run_id)
            self.supervisors = self.execution_state.branches
        self.workflow_state = state
        if state == "IDLE":
            self._reset_run_display_state()
        self.flush_refresh()

    def _on_subworkflow_run_update(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        self.child_runs.update(payload)
        self.schedule_refresh()

    def _on_subworkflow_run_ended(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        self.child_runs.ended(payload)
        self.schedule_refresh()

    def _prompt_labels(self, payload) -> tuple:
        """Who asks and from where: ("Greeter", ["Fetch report", "Greet",
        "Greeter", "Ask name"]). A subworkflow's prompt carries its call path."""
        path = [part for part in str(payload.get("call_path") or "").split(" › ") if part]
        workflow_map = self.workflow_map
        child_run_id = payload.get("child_run_id")
        tree = getattr(self.master_state, "call_tree", None)
        if child_run_id and tree is not None:
            for child in tree.live_masters():
                if child.current_run_id == child_run_id:
                    workflow_map = child.workflow_map
                    break
        if not path:
            path = [str(getattr(self.workflow_map, "workflow_name", "") or "Workflow")]
        node_id = str(payload.get("node_id") or "")
        from .node_io_display import node_display_name

        node_name = node_display_name(node_id, workflow_map.get_node_data(node_id) or {}) if node_id else ""
        return path[-1], path + ([node_name] if node_name else [])

    def _on_supervisor_register(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        self.execution_state.register(payload)
        self.schedule_refresh()

    def _on_supervisor_state_update(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        self.execution_state.supervisor(payload)
        self._branch_current_nodes[payload["branch_id"]] = payload.get("current_node_id")
        self.schedule_refresh()

    def _on_node_execution_update(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        self.execution_state.node(payload)
        self.node_statuses = self.execution_state.node_statuses()
        self.node_skip_reasons = self.execution_state.skip_reasons()
        self.schedule_refresh()

    def _on_node_timing_update(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        node_id = payload.get("node_id")
        if node_id:
            seconds = float(payload.get("seconds") or 0.0)
            self.node_timings[node_id] = self.node_timings.get(node_id, 0.0) + seconds
            self.execution_state.timing(payload)
        self.schedule_refresh()

    def _on_supervisor_terminating(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        self.execution_state.supervisor(payload, terminated=True)
        self.schedule_refresh()

    def _on_user_input_needed(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        self._user_input_requests.append(dict(payload))
        self._show_next_user_input()
        self.flush_refresh()

    def _show_next_user_input(self) -> None:
        """Show the oldest prompt whose run is current and whose branch still waits."""
        if self._user_input_modal_open:
            return
        while self._user_input_requests:
            payload = self._user_input_requests.popleft()
            if (self.execution_state.accepts(payload)
                    and self.master_state.waiting_for_input(payload.get("branch_id", ""))):
                break
        else:
            return
        self._user_input_modal_open = True
        asker, path = self._prompt_labels(payload)
        self.push_screen(
            UserInputScreen(
                branch_id=payload.get("branch_id", ""),
                node_id=payload.get("node_id", ""),
                prompt=payload.get("prompt", ""),
                asker=asker,
                path=path,
            ),
            self._submit_user_input_from_modal,
        )

    def _on_file_view_requested(self, payload=None) -> None:
        """Queue displays for the active run; execution does not wait on them."""
        payload = payload or {}
        if not self.execution_state.accepts(payload) or not payload.get("path"):
            return
        self._file_view_requests.append(dict(payload))
        self._show_next_file_viewer()

    def _show_next_file_viewer(self) -> None:
        if self._file_viewer_open or self._user_input_modal_open or self._error_modal_open:
            return
        while self._file_view_requests:
            payload = self._file_view_requests.popleft()
            if self.execution_state.accepts(payload):
                break
        else:
            return
        self._file_viewer_open = True
        self.push_screen(
            FileViewerScreen(path=str(payload["path"]), render=str(payload.get("render") or "plain")),
            self._on_file_viewer_closed,
        )

    def _on_file_viewer_closed(self, _result=None) -> None:
        self._file_viewer_open = False
        self._show_next_file_viewer()

    def _on_recovery_options_available(self, payload=None) -> None:
        payload = payload or {}
        if not self.execution_state.accepts(payload):
            return
        # EX: on the Execution screen the choice is made in its error panel.
        add_recovery = getattr(self.screen, "add_recovery", None)
        if add_recovery is not None:
            add_recovery(payload)
            self.flush_refresh()
            return
        if not self._error_modal_open:
            self._error_modal_open = True
            self.push_screen(
                ErrorDetailsScreen(payload),
                self._submit_recovery_from_modal,
            )
        self.flush_refresh()

    def _submit_user_input_from_modal(self, result) -> None:
        self._user_input_modal_open = False
        if result:
            self.master_state.submit_user_input(result["branch_id"], result["value"])
        self._show_next_user_input()
        self._show_next_file_viewer()

    def _submit_recovery_from_modal(self, result) -> None:
        self._error_modal_open = False
        if result:
            self.master_state.submit_recovery_action(result["branch_id"], result["action"])
        self._show_next_file_viewer()

    def _reset_run_display_state(self) -> None:
        self._file_view_requests.clear()
        self._user_input_requests.clear()
        if self.execution_state.run_id is not None:
            self._retired_display_run_id = self.execution_state.run_id
        self.execution_state.reset()
        self.node_statuses = {}
        self.node_skip_reasons = {}
        self.node_timings = {}
        self.supervisors = {}
        self._branch_current_nodes = {}
        self.child_runs.clear()

    def _ensure_starter_workflow(self) -> None:
        """Load the last workflow when possible, otherwise create a starter graph."""
        if self.workflow_map.is_loaded:
            return
        if self.save_manager is not None and self.configuration_manager is not None:
            last_id = self.configuration_manager.get("last_active_workflow_id")
            if last_id and self.save_manager.load_workflow(last_id):
                return
        self.workflow_map.create_new(DEFAULT_NAME)
        self.workflow_map.add_node(START_NODE_TYPE, alias="Start")

    def action_save_workflow(self) -> None:
        """Save the active workflow."""
        self._materialize_editor_deleted_nodes()
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
        self.action_save_workflow()
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
        from backend.contracts import ContractInputError

        try:
            started = await self.master_state.start_workflow()
        except ContractInputError as exc:
            # Step 4a: a required Start input with no value stops the run
            # before it starts (C10).
            notifications.notify_error(self, f"Can't start: {exc}")
            return
        if not started:
            notifications.workflow_start_failed(self)

    def stop_active_workflow(self) -> None:
        """Stop a run when leaving execution-oriented screens."""
        if self.workflow_state in {"RUNNING", "PAUSED", "WAITING_FOR_INPUT"}:
            self.master_state.stop()
            self.workflow_state = "IDLE"
            self._reset_run_display_state()
            notifications.workflow_stopped(self)

    def action_new_workflow(self, callable_: bool = False) -> None:
        """Create a fresh starter workflow (a subworkflow from tab 2)."""
        if self.workflow_map.is_dirty:
            kind = "subworkflow" if callable_ else "workflow"
            self.push_screen(
                ConfirmScreen(
                    "The current workflow has unsaved changes.\n"
                    f"Create a new {kind} and discard them?",
                    yes_label="Discard",
                    no_label="Cancel",
                ),
                lambda confirmed: self._prompt_new_workflow_name(callable_) if confirmed else None,
            )
            return
        self._prompt_new_workflow_name(callable_)

    def _prompt_new_workflow_name(self, callable_: bool = False) -> None:
        """Ask for the new workflow's name; Esc creates nothing."""
        title = "New subworkflow" if callable_ else "New workflow"
        self.push_screen(
            NamePromptScreen(title, unused_name(callable_=callable_),
                             lambda name: name_problem(name, callable_=callable_)),
            lambda name: self._create_new_workflow(name, callable_) if name else None,
        )

    def _create_new_workflow(self, name: str = DEFAULT_NAME, callable_: bool = False) -> None:
        """Create a fresh starter workflow without additional confirmation."""
        self.stop_active_workflow()
        self._reset_run_display_state()
        self._editor_deleted_nodes = {}
        self.workflow_map.create_new(name)
        self.workflow_map.add_node(START_NODE_TYPE, alias="Start")
        if callable_:
            self.workflow_map.set_callable(True)
        self._on_backend_event()
        if callable_:
            notifications.subworkflow_created(self)
        else:
            notifications.workflow_created(self)

    def action_workflow_library(self, initial_tab: str | None = None) -> None:
        """Open the workflow library modal."""
        self.push_screen(
            WorkflowLibraryScreen(self.workflow_map.workflow_id, initial_tab=initial_tab),
            self._handle_workflow_library_action,
        )

    def action_stash(self, initial_tab: str = "add", insert_into=None, callback=None) -> None:
        """Open the Stash (`p` in the editor). Node config's field insert (S3)
        opens it on Entries in insert mode; ``callback`` gets the chosen entry."""
        if self.stash_manager is None:
            from backend.stash_manager import StashManager

            self.stash_manager = StashManager()
        self.push_screen(
            StashScreen(self.stash_manager, initial_tab=initial_tab, insert_into=insert_into),
            callback,
        )

    def action_settings(self) -> None:
        """Open settings modal."""
        if self.configuration_manager is None:
            notifications.settings_unavailable(self)
            return
        self.push_screen(
            SettingsScreen(
                self.configuration_manager,
                secrets_manager=self.secrets_manager,
            ),
            self._handle_settings_action,
        )

    def action_help(self) -> None:
        """Open help modal."""
        self.push_screen(HelpScreen(self._help_context_for_screen()))

    def _help_context_for_screen(self) -> str:
        """Return the help topic for the currently active screen."""
        screen_name = type(self.screen).__name__
        if screen_name == "EditorScreen":
            return "editor"
        if screen_name == "ExecutionScreen":
            return "execution"
        if screen_name == "NodeConfigScreen":
            return "node_config"
        if screen_name in {"WorkflowLibraryScreen", "PathPromptScreen"}:
            return "workflow_library"
        if screen_name == "StashScreen":
            return "stash"
        if screen_name == "SettingsScreen":
            return "settings"
        return "general"

    def _handle_workflow_library_action(self, result) -> None:
        if not result:
            return
        action = result.get("action")
        if action == "new":
            self.action_new_workflow(bool(result.get("callable")))
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
        elif action == "rename":
            self._prompt_rename_workflow(result)
        elif action == "copy_to_subworkflows":
            self._confirm_copy_to_subworkflows(result)
        elif action == "duplicate":
            if self.save_manager is None:
                notifications.missing_service(self, "Duplicate")
                return
            new_id = self.save_manager.duplicate_workflow(workflow_id)
            if new_id:
                self.save_manager.load_workflow(new_id)
                self._reset_run_display_state()
                self._editor_deleted_nodes = {}
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

    def _confirm_copy_to_subworkflows(self, result) -> None:
        """C on the Workflows tab: copy it as a subworkflow (owner, 2026-10-18)."""
        if self.save_manager is None:
            notifications.missing_service(self, "Copy")
            return
        from backend.persistence import load_workflow

        workflow_id = result["workflow_id"]
        name = str(result.get("workflow_name") or workflow_id)
        data = load_workflow(workflow_id) or {}
        ends = sum(1 for node in (data.get("nodes") or {}).values()
                   if isinstance(node, dict) and node.get("type") == "end_node")
        message = f'Copy "{name}" as [sub]?\nThe original stays unchanged.'
        if ends > 1:
            message += f"\nIt has {ends} End nodes; pick one to send results back."
        self.push_screen(
            ConfirmScreen(message, yes_label="Copy", no_label="Cancel"),
            lambda confirmed: self._copy_to_subworkflows(workflow_id, name)
            if confirmed else self.action_workflow_library("library-tab-workflows"),
        )

    def _copy_to_subworkflows(self, workflow_id: str, name: str) -> None:
        copied = self.save_manager.copy_as_subworkflow(workflow_id)
        if copied is None:
            notifications.notify_error(self, "The workflow could not be read")
        else:
            notifications.copied_to_subworkflows(self, copied["name"], name, copied["renamed"])
        self.action_workflow_library("library-tab-workflows")

    def _prompt_rename_workflow(self, result) -> None:
        if self.save_manager is None:
            notifications.missing_service(self, "Rename")
            return
        workflow_id = result["workflow_id"]
        callable_ = bool(result.get("callable"))
        self.push_screen(
            NamePromptScreen(
                "Rename subworkflow" if callable_ else "Rename workflow",
                str(result.get("workflow_name") or ""),
                lambda name: name_problem(name, exclude_id=workflow_id, callable_=callable_),
            ),
            lambda name: self._rename_workflow(workflow_id, name, callable_),
        )

    def _rename_workflow(self, workflow_id: str, name, callable_: bool = False) -> None:
        """Apply a confirmed rename, then return to the library."""
        if name:
            problem = self.save_manager.rename_workflow(workflow_id, name)
            if problem:
                notifications.notify_info(self, problem)
            else:
                self._on_backend_event()
                notifications.workflow_renamed(self, name)
        self.action_workflow_library("library-tab-subworkflows" if callable_ else "library-tab-workflows")

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
            self._reset_run_display_state()
            self._editor_deleted_nodes = {}
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
            self._editor_deleted_nodes = {}
            self.workflow_map.create_new(DEFAULT_NAME)
            self.workflow_map.add_node(START_NODE_TYPE, alias="Start")
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
        asyncio.create_task(self._prompt_export_workflow_with_picker(result))

    async def _prompt_export_workflow_with_picker(self, result) -> None:
        workflow_id = result.get("workflow_id")
        default_name = f"{workflow_id}.json"
        try:
            path = await asyncio.to_thread(
                file_io.pick_save_file,
                "Export workflow JSON",
                default_name,
                file_io.JSON_FILE_TYPES,
            )
        except file_io.FilePickerUnavailable:
            self._prompt_export_workflow_path(result)
            return
        if path:
            self._export_workflow_to_path(result, path)
        else:
            self.action_workflow_library()

    def _prompt_export_workflow_path(self, result) -> None:
        workflow_id = result.get("workflow_id")
        default_path = str(Path.cwd() / f"{workflow_id}.json")
        self.push_screen(
            PathPromptScreen(
                "Export workflow JSON path",
                default_path,
                picker_mode="save",
                default_name=f"{workflow_id}.json",
            ),
            lambda path: self._export_workflow_to_path(result, path),
        )

    def _export_workflow_to_path(self, result, path: str | None) -> None:
        if not path or self.save_manager is None:
            if not path:
                self.action_workflow_library()
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
        asyncio.create_task(self._prompt_import_workflow_with_picker())

    async def _prompt_import_workflow_with_picker(self) -> None:
        try:
            path = await asyncio.to_thread(
                file_io.pick_open_file,
                "Import workflow JSON",
                file_io.JSON_FILE_TYPES,
            )
        except file_io.FilePickerUnavailable:
            self._prompt_import_workflow_path()
            return
        if path:
            self._import_workflow_from_path(path)
        else:
            self.action_workflow_library()

    def _prompt_import_workflow_path(self) -> None:
        self.push_screen(
            PathPromptScreen("Import workflow JSON path", picker_mode="open"),
            self._import_workflow_from_path,
        )

    def _import_workflow_from_path(self, path: str | None) -> None:
        if not path or self.save_manager is None:
            if not path:
                self.action_workflow_library()
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

    def _materialize_editor_deleted_nodes(self) -> None:
        adapter = EditorWorkflowAdapter(
            self.workflow_map,
            self.factory,
            state_owner=self,
        )
        adapter.materialize_deleted_nodes()

    def _handle_settings_action(self, result) -> None:
        if not result or result.get("action") != "save":
            return
        if self.configuration_manager is None:
            return
        for key, value in result.get("settings", {}).items():
            self.configuration_manager.set(key, value)
        notifications.settings_saved(self)


App = AttackOfTheNodesApp

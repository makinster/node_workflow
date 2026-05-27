"""
Master state for AttackOfTheNodes v0.5.

Coordinates all active supervisors, owns the run state machine, spawns branch
supervisors, and detects workflow completion.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .event_bus import EventBus
from .events import (
    ERROR_OCCURRED,
    SUPERVISOR_ERROR,
    SUPERVISOR_REGISTER,
    SUPERVISOR_REQUEST_BRANCH,
    SUPERVISOR_STATE_UPDATE,
    SUPERVISOR_TERMINATING,
    TERMINATE_WORKFLOW_REQUESTED,
    WORKFLOW_STATE_UPDATE,
    WorkflowState,
)
from .error_handler import ErrorHandler
from .memory_bank import MemoryBank
from .configuration_manager import ConfigurationManager
from .output_manager import OutputManager
from .run_history import RunHistory
from .supervisor import Supervisor
from .workflow_map import WorkflowMap


logger = logging.getLogger(__name__)


class MasterState:
    """Coordinates supervisors for one workflow run."""

    def __init__(
        self,
        workflow_map: WorkflowMap,
        memory_bank: MemoryBank,
        event_bus: EventBus,
        error_handler: Optional[ErrorHandler] = None,
        run_history: Optional[RunHistory] = None,
        output_manager: Optional[OutputManager] = None,
        configuration_manager: Optional[ConfigurationManager] = None,
    ) -> None:
        self._workflow_map = workflow_map
        self._memory_bank = memory_bank
        self._event_bus = event_bus
        self._error_handler = error_handler or ErrorHandler(event_bus)
        self._run_history = run_history or RunHistory(event_bus)
        self._output_manager = output_manager or OutputManager()
        self._configuration_manager = configuration_manager or ConfigurationManager()

        self.state = WorkflowState.IDLE
        self.current_run_id: Optional[str] = None
        self._started_at: Optional[str] = None
        self.run_outputs: List[str] = []

        self._supervisors: Dict[str, Supervisor] = {}
        self._supervisor_tasks: Dict[str, asyncio.Task] = {}

        self._event_bus.subscribe(SUPERVISOR_REGISTER, self._on_supervisor_register)
        self._event_bus.subscribe(
            SUPERVISOR_TERMINATING, self._on_supervisor_terminating
        )
        self._event_bus.subscribe(SUPERVISOR_REQUEST_BRANCH, self._on_request_branch)
        self._event_bus.subscribe(
            SUPERVISOR_STATE_UPDATE, self._on_supervisor_state_update
        )
        self._event_bus.subscribe(SUPERVISOR_ERROR, self._on_supervisor_error)
        self._event_bus.subscribe(
            TERMINATE_WORKFLOW_REQUESTED, self._on_terminate_workflow_requested
        )

    async def start_workflow(self) -> bool:
        """Begin executing the loaded workflow."""
        if not self._workflow_map.is_loaded:
            logger.error("Cannot start: no workflow loaded")
            return False

        start_node_id = self._workflow_map.find_start_node_id()
        if start_node_id is None:
            logger.error("Cannot start: workflow has no start node")
            return False

        self.current_run_id = f"run_{uuid.uuid4().hex[:8]}"
        self._started_at = datetime.now(timezone.utc).isoformat()
        self.run_outputs = []
        self._output_manager.clear_run(self.current_run_id)
        self._memory_bank.clear()
        self._supervisors.clear()
        self._supervisor_tasks.clear()
        self._set_state(WorkflowState.RUNNING)

        root = Supervisor(
            run_id=self.current_run_id,
            branch_id=f"branch_{uuid.uuid4().hex[:6]}",
            depth=0,
            start_node_id=start_node_id,
            workflow_map=self._workflow_map,
            memory_bank=self._memory_bank,
            event_bus=self._event_bus,
            error_handler=self._error_handler,
        )
        self._supervisor_tasks[root.branch_id] = asyncio.create_task(root.run())
        return True

    def pause(self) -> None:
        """Request all active supervisors to pause."""
        if self.state != WorkflowState.RUNNING:
            return
        for supervisor in self._supervisors.values():
            supervisor.request_pause()
        self._set_state(WorkflowState.PAUSED)

    def resume(self) -> None:
        """Resume all paused supervisors."""
        if self.state != WorkflowState.PAUSED:
            return
        for supervisor in self._supervisors.values():
            supervisor.request_resume()
        self._set_state(WorkflowState.RUNNING)

    def stop(self) -> None:
        """Request all supervisors to stop."""
        for supervisor in self._supervisors.values():
            supervisor.request_stop()

    def submit_user_input(self, branch_id: str, value: str) -> bool:
        """Forward user input to a waiting supervisor."""
        supervisor = self._supervisors.get(branch_id)
        if supervisor is None:
            logger.warning("No supervisor with branch_id %s", branch_id)
            return False
        supervisor.submit_user_input(value)
        return True

    def submit_recovery_action(self, branch_id: str, action: str) -> bool:
        """Forward a recovery action to the supervisor waiting for it."""
        supervisor = self._supervisors.get(branch_id)
        if supervisor is None:
            logger.warning("No supervisor with branch_id %s", branch_id)
            return False
        supervisor.submit_recovery_action(action)
        return True

    @property
    def error_handler(self) -> ErrorHandler:
        """Structured error handler used by this master state."""
        return self._error_handler

    @property
    def run_history(self) -> RunHistory:
        """Run history service used by this master state."""
        return self._run_history

    async def wait_for_completion(self) -> None:
        """Wait until every supervisor task, including spawned branches, ends."""
        while self._supervisor_tasks:
            tasks = list(self._supervisor_tasks.values())
            await asyncio.gather(*tasks, return_exceptions=True)

    def _on_supervisor_register(self, payload: Dict[str, Any]) -> None:
        branch_id = payload["branch_id"]
        self._supervisors[branch_id] = payload["supervisor"]
        logger.debug("Registered supervisor %s at depth %d", branch_id, payload["depth"])

    def _on_supervisor_terminating(self, payload: Dict[str, Any]) -> None:
        branch_id = payload["branch_id"]
        self._supervisors.pop(branch_id, None)
        self._supervisor_tasks.pop(branch_id, None)
        logger.debug(
            "Supervisor %s terminated (final state: %s)",
            branch_id,
            payload["final_state"],
        )
        self._check_run_completion()

    def _on_request_branch(self, payload: Dict[str, Any]) -> None:
        new_depth = payload["parent_depth"] + 1
        max_branch_depth = int(self._configuration_manager.get("max_branch_depth"))
        if new_depth > max_branch_depth:
            logger.warning(
                "Branch depth %d exceeds limit %d; not spawning",
                new_depth,
                max_branch_depth,
            )
            return

        child = Supervisor(
            run_id=payload["run_id"],
            branch_id=f"branch_{uuid.uuid4().hex[:6]}",
            depth=new_depth,
            start_node_id=payload["start_node_id"],
            workflow_map=self._workflow_map,
            memory_bank=self._memory_bank,
            event_bus=self._event_bus,
            error_handler=self._error_handler,
            initial_data=payload.get("initial_data", {}),
            parent_branch_id=payload["parent_branch_id"],
        )
        self._supervisor_tasks[child.branch_id] = asyncio.create_task(child.run())

    def _on_supervisor_state_update(self, payload: Dict[str, Any]) -> None:
        if payload["state"] == "WAITING_FOR_INPUT":
            self._set_state(WorkflowState.WAITING_FOR_INPUT)
        elif payload["state"] == "AWAITING_RECOVERY":
            self._set_state(WorkflowState.WAITING_FOR_INPUT)
        elif self.state == WorkflowState.WAITING_FOR_INPUT and payload["state"] == "RUNNING":
            self._set_state(WorkflowState.RUNNING)

    def _on_supervisor_error(self, payload: Dict[str, Any]) -> None:
        self._set_state(WorkflowState.ERROR)
        self._event_bus.publish(ERROR_OCCURRED, payload)
        self._record_run("ERROR")

    def _on_terminate_workflow_requested(self, _payload: Dict[str, Any]) -> None:
        self.stop()
        self._set_state(WorkflowState.ERROR)
        self._record_run("ERROR")

    def _check_run_completion(self) -> None:
        if self._supervisors or self._supervisor_tasks:
            return
        if self.state == WorkflowState.ERROR:
            return
        self.run_outputs = list(
            self._memory_bank.read_persistent("output_log", default=[])
        )
        self._output_manager.store_output_log(self.current_run_id, self.run_outputs)
        self.run_outputs = self._output_manager.finalize_run(self.current_run_id)
        self._set_state(WorkflowState.FINISHED)
        self._record_run("FINISHED")

    def _set_state(self, new_state: WorkflowState) -> None:
        if self.state == new_state:
            return
        self.state = new_state
        self._event_bus.publish(
            WORKFLOW_STATE_UPDATE,
            {"state": new_state.value, "run_id": self.current_run_id},
        )

    def _record_run(self, final_state: str) -> None:
        if not self.current_run_id:
            return
        errors = self._error_handler.get_errors_for_run(self.current_run_id)
        self._run_history.record_run(
            {
                "run_id": self.current_run_id,
                "workflow_id": self._workflow_map.workflow_id,
                "workflow_name": self._workflow_map.workflow_name,
                "started_at": self._started_at,
                "final_state": final_state,
                "error_count": len(errors),
                "output_count": len(self.run_outputs),
                "outputs": list(self.run_outputs),
            }
        )

    @property
    def output_manager(self) -> OutputManager:
        """Output manager used by this master state."""
        return self._output_manager

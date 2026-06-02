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
    BREAKPOINT_HIT,
    ERROR_OCCURRED,
    NODE_TIMING_UPDATE,
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
        self.node_timings: Dict[str, float] = {}
        self.completed_nodes: set[str] = set()
        self._completion_condition = asyncio.Condition()
        self._merge_condition = asyncio.Condition()
        self._branch_groups: Dict[str, str] = {}
        self._merge_groups: Dict[str, Dict[str, Any]] = {}

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
        self._event_bus.subscribe(BREAKPOINT_HIT, self._on_breakpoint_hit)
        self._event_bus.subscribe(NODE_TIMING_UPDATE, self._on_node_timing_update)
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
        self.node_timings = {}
        self.completed_nodes = set()
        self._branch_groups.clear()
        self._merge_groups.clear()
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
            mark_node_completed=self.mark_node_completed,
            wait_for_nodes=self.wait_until_nodes_completed,
            wait_for_merge=self.wait_for_merge_arrival,
            node_timeout_seconds=float(
                self._configuration_manager.get("node_timeout_seconds")
            ),
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
        self._account_for_branch_termination(branch_id)
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

        child_branch_id = f"branch_{uuid.uuid4().hex[:6]}"
        self._register_branch_group(payload["parent_branch_id"], child_branch_id)

        child = Supervisor(
            run_id=payload["run_id"],
            branch_id=child_branch_id,
            depth=new_depth,
            start_node_id=payload["start_node_id"],
            workflow_map=self._workflow_map,
            memory_bank=self._memory_bank,
            event_bus=self._event_bus,
            error_handler=self._error_handler,
            initial_data=payload.get("initial_data", {}),
            parent_branch_id=payload["parent_branch_id"],
            mark_node_completed=self.mark_node_completed,
            wait_for_nodes=self.wait_until_nodes_completed,
            wait_for_merge=self.wait_for_merge_arrival,
            node_timeout_seconds=float(
                self._configuration_manager.get("node_timeout_seconds")
            ),
        )
        self._supervisor_tasks[child.branch_id] = asyncio.create_task(child.run())

    async def mark_node_completed(self, node_id: str) -> None:
        """Record a node completion and wake wait-until nodes."""
        async with self._completion_condition:
            self.completed_nodes.add(node_id)
            self._completion_condition.notify_all()

    async def wait_until_nodes_completed(
        self, target_node_ids: List[str], timeout_seconds: Optional[float] = None
    ) -> None:
        """Wait until all target nodes have completed at least once this run."""
        targets = {node_id for node_id in target_node_ids if node_id}
        if not targets:
            return

        async def wait_for_targets() -> None:
            async with self._completion_condition:
                await self._completion_condition.wait_for(
                    lambda: targets.issubset(self.completed_nodes)
                )

        if timeout_seconds is None or timeout_seconds <= 0:
            await wait_for_targets()
            return
        await asyncio.wait_for(wait_for_targets(), timeout=timeout_seconds)

    async def wait_for_merge_arrival(
        self,
        merge_node_id: str,
        branch_id: str,
        selected_input_port: str,
        inputs: Dict[str, Any],
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Wait for sibling branches to reach/leave a merge, then elect one output."""
        group_id = self._branch_groups.get(branch_id)
        if group_id is None:
            return {
                "continue": True,
                "value": inputs.get(selected_input_port, next(iter(inputs.values()), "")),
            }

        async def wait_for_group() -> Dict[str, Any]:
            async with self._merge_condition:
                group = self._merge_groups.setdefault(
                    group_id,
                    {
                        "pending": set(),
                        "arrivals": {},
                        "merge_node_id": merge_node_id,
                        "selected_input_port": selected_input_port,
                    },
                )
                group["merge_node_id"] = merge_node_id
                group["selected_input_port"] = selected_input_port
                group.setdefault("arrivals", {})[branch_id] = dict(inputs)
                group.setdefault("pending", set()).discard(branch_id)
                self._merge_condition.notify_all()
                await self._merge_condition.wait_for(
                    lambda: not group.get("pending")
                )
                winner_branch = self._merge_winner_branch(group)
                value = self._merge_selected_value(group, selected_input_port)
                return {"continue": branch_id == winner_branch, "value": value}

        if timeout_seconds is None or timeout_seconds <= 0:
            return await wait_for_group()
        return await asyncio.wait_for(wait_for_group(), timeout=timeout_seconds)

    def _register_branch_group(self, parent_branch_id: str, child_branch_id: str) -> None:
        group_id = self._branch_groups.get(parent_branch_id, parent_branch_id)
        self._branch_groups[child_branch_id] = group_id
        group = self._merge_groups.setdefault(
            group_id,
            {
                "pending": set(),
                "arrivals": {},
                "merge_node_id": None,
                "selected_input_port": "",
            },
        )
        group.setdefault("pending", set()).add(child_branch_id)

    def _account_for_branch_termination(self, branch_id: str) -> None:
        group_id = self._branch_groups.get(branch_id)
        if group_id is None:
            return
        group = self._merge_groups.get(group_id)
        if group is None:
            return
        group.setdefault("pending", set()).discard(branch_id)
        asyncio.create_task(self._notify_merge_waiters())

    async def _notify_merge_waiters(self) -> None:
        async with self._merge_condition:
            self._merge_condition.notify_all()

    def _merge_winner_branch(self, group: Dict[str, Any]) -> Optional[str]:
        selected_port = str(group.get("selected_input_port") or "")
        arrivals = group.get("arrivals") or {}
        for branch_id, inputs in arrivals.items():
            if inputs.get(selected_port) is not None:
                return branch_id
        return next(iter(arrivals.keys()), None)

    def _merge_selected_value(
        self, group: Dict[str, Any], selected_input_port: str
    ) -> Any:
        arrivals = group.get("arrivals") or {}
        for inputs in arrivals.values():
            if inputs.get(selected_input_port) is not None:
                return inputs[selected_input_port]
        for inputs in arrivals.values():
            for value in inputs.values():
                if value is not None:
                    return value
        return ""

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

    def _on_breakpoint_hit(self, _payload: Dict[str, Any]) -> None:
        for supervisor in self._supervisors.values():
            supervisor.request_pause()
        self._set_state(WorkflowState.PAUSED)

    def _on_node_timing_update(self, payload: Dict[str, Any]) -> None:
        if payload.get("run_id") != self.current_run_id:
            return
        node_id = payload.get("node_id")
        if not node_id:
            return
        seconds = float(payload.get("seconds") or 0.0)
        self.node_timings[node_id] = self.node_timings.get(node_id, 0.0) + seconds

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
                "node_timings": dict(self.node_timings),
                # "outputs" removed — values already persisted by OutputManager
            }
        )
        self._error_handler.finalize_run(self.current_run_id)

    @property
    def output_manager(self) -> OutputManager:
        """Output manager used by this master state."""
        return self._output_manager

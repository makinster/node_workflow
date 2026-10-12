"""
Master state for AttackOfTheNodes v0.5.

Coordinates all active supervisors, owns the run state machine, spawns branch
supervisors, and detects workflow completion. Per-run state lives in a
``RunContext`` created for each run; supervisors receive callables bound to
their own run's context.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

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
from .run_context import RunContext
from .run_history import RunHistory
from .run_session import RunSession
from .secrets_manager import SecretsManager
from .supervisor import UNATTENDED_ACTIONS, Supervisor
from .wait_registry import (
    TargetUnreachableError,
    WaitStatus,
    WaitStoppedError,
    node_key,
)
from .workflow_map import WorkflowMap


logger = logging.getLogger(__name__)


class MasterState:
    """Coordinates supervisors for one workflow run at a time."""

    def __init__(
        self,
        workflow_map: WorkflowMap,
        memory_bank: MemoryBank,
        event_bus: EventBus,
        error_handler: Optional[ErrorHandler] = None,
        run_history: Optional[RunHistory] = None,
        output_manager: Optional[OutputManager] = None,
        configuration_manager: Optional[ConfigurationManager] = None,
        secrets_manager: Optional[SecretsManager] = None,
    ) -> None:
        self._workflow_map = workflow_map
        self._memory_bank = memory_bank
        self._event_bus = event_bus
        self._error_handler = error_handler or ErrorHandler(event_bus)
        self._run_history = run_history or RunHistory(event_bus)
        self._output_manager = output_manager or OutputManager()
        self._configuration_manager = configuration_manager or ConfigurationManager()
        self._secrets_manager: Optional[SecretsManager] = secrets_manager

        self.state = WorkflowState.IDLE
        self.current_run_id: Optional[str] = None
        self.run_outputs: List[str] = []
        self._run: Optional[RunContext] = None

        self._supervisors: Dict[str, Supervisor] = {}
        self._supervisor_tasks: Dict[str, asyncio.Task] = {}
        # Serializes starts: each must cancel the previous run's tasks before
        # creating its own, or an overlapping start would lose track of them.
        self._start_lock = asyncio.Lock()

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

    # -- current-run views (kept for existing callers) -------------------------

    @property
    def run_context(self) -> Optional[RunContext]:
        """The current (or most recent) run's context."""
        return self._run

    @property
    def completed_nodes(self) -> Set[str]:
        return self._run.completed_nodes if self._run else set()

    @property
    def node_timings(self) -> Dict[str, float]:
        return self._run.node_timings if self._run else {}

    @property
    def _run_session(self) -> Optional[RunSession]:
        return self._run.run_session if self._run else None

    @property
    def _started_at(self) -> Optional[str]:
        return self._run.started_at if self._run else None

    # -- run control -----------------------------------------------------------

    async def start_workflow(self, unattended: Optional[str] = None) -> bool:
        """Begin executing the loaded workflow.

        ``unattended`` is ``None`` (a client answers recovery and input
        requests), ``"terminate_branch"`` or ``"terminate_workflow"``. When set,
        errors and input requests follow that policy without waiting, and
        breakpoints are skipped.
        """
        if unattended is not None and unattended not in UNATTENDED_ACTIONS:
            raise ValueError(f"Unknown unattended policy: {unattended!r}")
        async with self._start_lock:
            return await self._start_workflow_locked(unattended)

    async def _start_workflow_locked(self, unattended: Optional[str]) -> bool:
        if not self._workflow_map.is_loaded:
            logger.error("Cannot start: no workflow loaded")
            return False

        start_node_id = self._workflow_map.find_start_node_id()
        if start_node_id is None:
            logger.error("Cannot start: workflow has no start node")
            return False

        # Leftover tasks would otherwise wake inside the new run and write
        # into its memory, so they are cancelled before any state is reset.
        await self._cancel_leftover_tasks()

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        self.current_run_id = run_id
        self.run_outputs = []
        self._output_manager.clear_run(run_id)
        self._memory_bank.clear()
        self._supervisors.clear()
        self._supervisor_tasks.clear()
        if self._run is not None:
            self._run.run_session.close_all()
        self._run = RunContext(
            run_id=run_id,
            memory_bank=self._memory_bank,
            run_session=RunSession(run_id),
            unattended=unattended,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._set_state(WorkflowState.RUNNING)

        root = self._new_supervisor(
            self._run,
            branch_id=f"branch_{uuid.uuid4().hex[:6]}",
            depth=0,
            start_node_id=start_node_id,
        )
        self._track_task(root.branch_id, asyncio.create_task(root.run()))
        return True

    def _new_supervisor(self, run: RunContext, **kwargs: Any) -> Supervisor:
        """Create a supervisor whose callbacks are bound to ``run``."""

        async def mark_completed(node_id: str) -> None:
            if run is self._run:
                await self.mark_node_completed(node_id)
            else:
                # A stale supervisor only ever touches its own run.
                run.mark_completed(node_id)

        async def wait_for_nodes(
            target_node_ids: List[str], timeout_seconds: Optional[float] = None
        ) -> None:
            await self._wait_for_nodes_in_run(run, target_node_ids, timeout_seconds)

        async def wait_for_merge(
            merge_node_id: str,
            branch_id: str,
            selected_input_port: str,
            inputs: Dict[str, Any],
            timeout_seconds: Optional[float] = None,
        ) -> Dict[str, Any]:
            return await self._wait_for_merge_in_run(
                run, merge_node_id, branch_id, selected_input_port, inputs, timeout_seconds
            )

        def report_outcome(node_id: str, state: str, delivered_to: List[str]) -> None:
            run.record_outcome(node_id, state, delivered_to)
            self._evaluate_waits(run)

        supervisor = Supervisor(
            run_id=run.run_id,
            workflow_map=self._workflow_map,
            memory_bank=run.memory_bank,
            event_bus=self._event_bus,
            error_handler=self._error_handler,
            mark_node_completed=mark_completed,
            wait_for_nodes=wait_for_nodes,
            wait_for_merge=wait_for_merge,
            node_timeout_seconds=float(
                self._configuration_manager.get("node_timeout_seconds")
            ),
            run_session=run.run_session,
            secrets_manager=self._secrets_manager,
            unattended=run.unattended,
            report_node_outcome=report_outcome,
            **kwargs,
        )
        run.live_supervisors[supervisor.branch_id] = supervisor
        return supervisor

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
        """Request all supervisors to stop, then cancel their tasks.

        Waiters get a ``stopped`` result from the run's WaitRegistry, and
        cancelling releases any other wait a stop request alone cannot reach.
        """
        if self._run is not None:
            self._run.wait_registry.stop()
        for supervisor in list(self._supervisors.values()):
            supervisor.request_stop()
        current = asyncio.current_task()
        for task in list(self._supervisor_tasks.values()):
            # A supervisor that asked to terminate the workflow is already
            # returning; cancelling itself would only obscure that.
            if task is not current and not task.done():
                task.cancel()

    async def _cancel_leftover_tasks(self) -> None:
        """Cancel and await supervisor tasks left over from a previous run."""
        tasks = [task for task in self._supervisor_tasks.values() if not task.done()]
        if self._run is not None:
            self._run.wait_registry.stop()
        for supervisor in list(self._supervisors.values()):
            supervisor.request_stop()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

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
            # Yield so done-callbacks can prune tasks that ended without
            # publishing SUPERVISOR_TERMINATING (cancelled before they ran).
            await asyncio.sleep(0)

    def _track_task(self, branch_id: str, task: asyncio.Task) -> None:
        self._supervisor_tasks[branch_id] = task
        task.add_done_callback(
            lambda done, branch_id=branch_id: self._on_task_done(branch_id, done)
        )

    def _on_task_done(self, branch_id: str, task: asyncio.Task) -> None:
        """Forget a task that ended without its supervisor reporting it.

        A task cancelled before its first step never runs ``Supervisor.run``,
        so it never publishes ``SUPERVISOR_TERMINATING``. Tasks that did report
        are already gone, and tasks of an earlier run are never tracked here.
        """
        if self._supervisor_tasks.get(branch_id) is not task:
            return
        self._supervisor_tasks.pop(branch_id, None)
        self._supervisors.pop(branch_id, None)
        self._forget_live_supervisor(self._run, branch_id)
        self._check_run_completion()

    def _on_supervisor_register(self, payload: Dict[str, Any]) -> None:
        branch_id = payload["branch_id"]
        self._supervisors[branch_id] = payload["supervisor"]
        logger.debug("Registered supervisor %s at depth %d", branch_id, payload["depth"])

    def _on_supervisor_terminating(self, payload: Dict[str, Any]) -> None:
        branch_id = payload["branch_id"]
        self._supervisors.pop(branch_id, None)
        self._supervisor_tasks.pop(branch_id, None)
        run = self._run if self._run and self._run.run_id == payload.get("run_id") else None
        self._forget_live_supervisor(run, branch_id)
        logger.debug(
            "Supervisor %s terminated (final state: %s)",
            branch_id,
            payload["final_state"],
        )
        self._check_run_completion()

    def _forget_live_supervisor(self, run: Optional[RunContext], branch_id: str) -> None:
        if run is None:
            return
        run.live_supervisors.pop(branch_id, None)
        self._account_for_branch_termination(run, branch_id)
        self._evaluate_waits(run)

    def _on_request_branch(self, payload: Dict[str, Any]) -> None:
        run = self._run
        if run is None or payload.get("run_id") != run.run_id:
            logger.warning("Ignoring branch request from inactive run %s", payload.get("run_id"))
            return
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
        self._register_branch_group(run, payload["parent_branch_id"], child_branch_id)

        # Delivery is recorded only for a child that actually exists, so a
        # branch refused by the depth limit never looks delivered.
        run.record_delivery(payload.get("source_node_id") or "", payload["start_node_id"])
        child = self._new_supervisor(
            run,
            branch_id=child_branch_id,
            depth=new_depth,
            start_node_id=payload["start_node_id"],
            initial_data=payload.get("initial_data", {}),
            parent_branch_id=payload["parent_branch_id"],
        )
        self._track_task(child.branch_id, asyncio.create_task(child.run()))

    # -- completion registry ---------------------------------------------------

    async def mark_node_completed(self, node_id: str) -> None:
        """Record a node completion in the current run and wake waiters."""
        if self._run is not None:
            self._run.mark_completed(node_id)

    async def wait_until_nodes_completed(
        self, target_node_ids: List[str], timeout_seconds: Optional[float] = None
    ) -> None:
        """Wait until all target nodes have completed at least once this run."""
        if self._run is None:
            return
        await self._wait_for_nodes_in_run(self._run, target_node_ids, timeout_seconds)

    async def _wait_for_nodes_in_run(
        self,
        run: RunContext,
        target_node_ids: List[str],
        timeout_seconds: Optional[float] = None,
    ) -> None:
        """Wait on ``run``'s registry; fail when a target can no longer complete.

        Raises ``TargetUnreachableError`` (structural rule, never a timeout),
        ``WaitStoppedError`` when the run is stopped, or ``asyncio.TimeoutError``
        when a positive ``timeout_seconds`` elapses.
        """
        targets = [node_id for node_id in target_node_ids if node_id]
        if not targets:
            return
        outcome = await run.wait_registry.wait_for_all(
            [node_key(node_id) for node_id in targets],
            timeout=timeout_seconds,
            on_registered=lambda: self._evaluate_waits(run),
        )
        if outcome.status == WaitStatus.COMPLETED:
            return
        if outcome.status == WaitStatus.STOPPED:
            raise WaitStoppedError("Run stopped while waiting")
        target_id = str(outcome.key[1]) if outcome.key else ""
        raise TargetUnreachableError(
            f"Wait target {self._describe_node(target_id)} can no longer "
            f"complete in this run: {outcome.reason}",
            key=outcome.key,
        )

    def _evaluate_waits(self, run: RunContext) -> None:
        """Apply the structural unreachable rule (D5) to every pending key."""
        pending = run.wait_registry.pending_keys()
        if not pending:
            return
        reach = run.live_reach(self._workflow_map)
        for key in pending:
            if len(key) != 2 or key[0] != "node":
                continue
            reason = run.unreachable_reason(str(key[1]), self._workflow_map, reach)
            if reason:
                run.wait_registry.mark_unreachable(key, reason)

    def _describe_node(self, node_id: str) -> str:
        data = self._workflow_map.get_node_data(node_id) or {}
        alias = str(data.get("alias") or "").strip()
        return f"'{alias}' ({node_id})" if alias else node_id

    # -- merge barrier -----------------------------------------------------------

    async def wait_for_merge_arrival(
        self,
        merge_node_id: str,
        branch_id: str,
        selected_input_port: str,
        inputs: Dict[str, Any],
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Wait for sibling branches to reach/leave a merge, then elect one output."""
        if self._run is None:
            return {"continue": True, "value": next(iter(inputs.values()), "")}
        return await self._wait_for_merge_in_run(
            self._run, merge_node_id, branch_id, selected_input_port, inputs, timeout_seconds
        )

    async def _wait_for_merge_in_run(
        self,
        run: RunContext,
        merge_node_id: str,
        branch_id: str,
        selected_input_port: str,
        inputs: Dict[str, Any],
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        group_id = run.branch_groups.get(branch_id)
        if group_id is None:
            return {
                "continue": True,
                "value": inputs.get(selected_input_port, next(iter(inputs.values()), "")),
            }

        async def wait_for_group() -> Dict[str, Any]:
            async with run.merge_condition:
                group = run.merge_groups.setdefault(
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
                run.merge_condition.notify_all()
                await run.merge_condition.wait_for(lambda: not group.get("pending"))
                winner_branch = self._merge_winner_branch(group)
                value = self._merge_selected_value(group, selected_input_port)
                return {"continue": branch_id == winner_branch, "value": value}

        if timeout_seconds is None or timeout_seconds <= 0:
            return await wait_for_group()
        return await asyncio.wait_for(wait_for_group(), timeout=timeout_seconds)

    def _register_branch_group(
        self, run: RunContext, parent_branch_id: str, child_branch_id: str
    ) -> None:
        group_id = run.branch_groups.get(parent_branch_id, parent_branch_id)
        run.branch_groups[child_branch_id] = group_id
        group = run.merge_groups.setdefault(
            group_id,
            {
                "pending": set(),
                "arrivals": {},
                "merge_node_id": None,
                "selected_input_port": "",
            },
        )
        group.setdefault("pending", set()).add(child_branch_id)

    def _account_for_branch_termination(self, run: RunContext, branch_id: str) -> None:
        group_id = run.branch_groups.get(branch_id)
        if group_id is None:
            return
        group = run.merge_groups.get(group_id)
        if group is None:
            return
        group.setdefault("pending", set()).discard(branch_id)
        asyncio.create_task(self._notify_merge_waiters(run))

    async def _notify_merge_waiters(self, run: RunContext) -> None:
        async with run.merge_condition:
            run.merge_condition.notify_all()

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

    # -- bus handlers --------------------------------------------------------------

    def _on_supervisor_state_update(self, payload: Dict[str, Any]) -> None:
        if payload.get("run_id") != self.current_run_id:
            return
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
        if self._run is None or payload.get("run_id") != self._run.run_id:
            return
        node_id = payload.get("node_id")
        if not node_id:
            return
        seconds = float(payload.get("seconds") or 0.0)
        timings = self._run.node_timings
        timings[node_id] = timings.get(node_id, 0.0) + seconds

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
        # Run is over on every path that records it; release runtime resources.
        if self._run is not None:
            self._run.run_session.close_all()
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

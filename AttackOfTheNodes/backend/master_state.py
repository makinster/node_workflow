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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from .event_bus import EventBus
from .agent_usage import usage_summary
from .events import (
    BREAKPOINT_HIT,
    ERROR_OCCURRED,
    NODE_EXECUTION_UPDATE,
    NODE_TIMING_UPDATE,
    AGENT_USAGE_UPDATE,
    SUPERVISOR_ERROR,
    SUPERVISOR_REGISTER,
    SUPERVISOR_REQUEST_BRANCH,
    SUPERVISOR_STATE_UPDATE,
    SUPERVISOR_TERMINATING,
    TERMINATE_WORKFLOW_REQUESTED,
    WORKFLOW_STATE_UPDATE,
    WorkflowState,
)
from .contracts import ContractError, resolve_inputs, return_rows, start_rows, workflow_revision
from .error_handler import ErrorHandler, unhandled_errors
from .memory_bank import MemoryBank
from .configuration_manager import ConfigurationManager
from .output_manager import OutputManager
from .run_context import (RunContext, Delivery, MergePlan, MergeBarrier,
                          MergeArrival, BranchGroup, GroupMember, BranchLaunch)
from .node_errors import NodeError
from .flow_behaviors import analyze_flow, merge_plans_from_analysis
from .branch_paths import path_index, path_port
from .run_history import RunHistory
from .run_session import RunSession
from .secrets_manager import SecretsManager
from .run_policies import (
    UNATTENDED_ACTIONS,
    InputProvider,
    RecoveryPolicy,
    unattended_policies,
)
from .supervisor import Supervisor
from .wait_registry import (
    TargetUnreachableError,
    WaitStatus,
    WaitStoppedError,
    node_key,
)
from .workflow_map import WorkflowMap

if TYPE_CHECKING:
    from .subworkflow_calls import CallTree


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
        *,
        call_tree: Optional["CallTree"] = None,
        call_depth: int = 0,
        call_info: Optional[Dict[str, Any]] = None,
        call_path: Optional[List[str]] = None,
    ) -> None:
        self._workflow_map = workflow_map
        self._memory_bank = memory_bank
        self._event_bus = event_bus
        self._error_handler = error_handler or ErrorHandler(event_bus)
        self._run_history = run_history or RunHistory(event_bus)
        self._output_manager = output_manager or OutputManager()
        self._configuration_manager = configuration_manager or ConfigurationManager()
        self._secrets_manager: Optional[SecretsManager] = secrets_manager
        # Step 4b: a child run shares its root's call tree; a root makes a new
        # one per run. ``call_info`` is the child's run record (C22).
        self._call_tree = call_tree
        self._owns_call_tree = call_tree is None
        self.call_depth = call_depth
        self._call_info = dict(call_info or {})
        self._call_path = list(call_path or [])
        self._children: Set["MasterState"] = set()
        self._finalize_hook: Optional[Any] = None

        self.state = WorkflowState.IDLE
        self.current_run_id: Optional[str] = None
        self.run_outputs: List[str] = []
        self._run: Optional[RunContext] = None

        self._supervisors: Dict[str, Supervisor] = {}
        self._supervisor_tasks: Dict[str, asyncio.Task] = {}
        # Serializes starts: each must cancel the previous run's tasks before
        # creating its own, or an overlapping start would lose track of them.
        self._start_lock = asyncio.Lock()

        self._event_bus.subscribe(AGENT_USAGE_UPDATE, self._on_agent_usage_update)
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
    def agent_usage(self) -> List[Dict[str, Any]]:
        return list(self._run.agent_usage) if self._run else []

    def _on_agent_usage_update(self, payload: Dict[str, Any]) -> None:
        if self._run is None or payload.get("run_id") != self.current_run_id:
            return
        # A terminal receipt can be updated if persisting its event failed.
        key = payload.get("invocation_id")
        self._run.agent_usage[:] = [item for item in self._run.agent_usage
                                   if item.get("invocation_id") != key]
        self._run.agent_usage.append(dict(payload))

    @property
    def node_timings(self) -> Dict[str, float]:
        return self._run.node_timings if self._run else {}

    @property
    def _run_session(self) -> Optional[RunSession]:
        return self._run.run_session if self._run else None

    @property
    def _started_at(self) -> Optional[str]:
        return self._run.started_at if self._run else None

    # -- subworkflow calls (Step 4b) -------------------------------------------

    @property
    def factory(self) -> Any:
        return self._workflow_map._factory

    @property
    def workflow_map(self) -> WorkflowMap:
        return self._workflow_map

    @property
    def memory_bank(self) -> MemoryBank:
        """This run's Vault (4c-2: a frontend shows a running call's writes)."""
        return self._memory_bank

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def configuration_manager(self) -> ConfigurationManager:
        return self._configuration_manager

    @property
    def secrets_manager(self) -> Optional[SecretsManager]:
        return self._secrets_manager

    @property
    def is_paused(self) -> bool:
        return self.state == WorkflowState.PAUSED

    @property
    def call_path(self) -> List[str]:
        """Readable names from the root to this run ("Main › Extract › Helper")."""
        return self._call_path or [self._workflow_map.workflow_name or "Workflow"]

    @property
    def call_tree(self) -> Optional["CallTree"]:
        return self._call_tree

    def call_tree_for(self, run: RunContext) -> "CallTree":
        """The tree this run's calls count against (C16 limits from Settings)."""
        if self._call_tree is None:
            from .subworkflow_calls import CallTree

            self._call_tree = CallTree(
                self,
                max_depth=int(self._configuration_manager.get("max_subworkflow_depth")),
                max_live=int(self._configuration_manager.get("max_live_subworkflow_runs")),
            )
        return self._call_tree

    def owns_branch(self, branch_id: str) -> bool:
        return branch_id in self._supervisors

    def add_child(self, child: "MasterState") -> None:
        self._children.add(child)

    def remove_child(self, child: "MasterState") -> None:
        self._children.discard(child)

    def set_finalize_hook(self, hook: Any) -> None:
        """Called as ``hook(run, final_state, errors)`` when the run is
        recorded, before its resources close (C13 file hand-over)."""
        self._finalize_hook = hook

    # -- run control -----------------------------------------------------------

    async def start_workflow(
        self,
        unattended: Optional[str] = None,
        *,
        recovery_policy: Optional[RecoveryPolicy] = None,
        input_provider: Optional[InputProvider] = None,
        inputs: Optional[Dict[str, Any]] = None,
        merge_plans: Optional[Dict[str, MergePlan]] = None,
    ) -> bool:
        """Begin executing the loaded workflow.

        With no policy the run is attended: a client answers recovery and
        input requests through this object. ``recovery_policy`` and
        ``input_provider`` (D1) answer them instead; a policy that does not
        pause at breakpoints also skips them. ``unattended`` is shorthand for
        ``TerminatePolicy(unattended)`` plus ``NoInputProvider``.
        """
        if unattended is not None:
            if unattended not in UNATTENDED_ACTIONS:
                raise ValueError(f"Unknown unattended policy: {unattended!r}")
            default_policy, default_provider = unattended_policies(unattended)
            recovery_policy = recovery_policy or default_policy
            input_provider = input_provider or default_provider
        async with self._start_lock:
            return await self._start_workflow_locked(
                unattended, recovery_policy, input_provider, dict(inputs or {}), None if merge_plans is None else dict(merge_plans)
            )

    async def _start_workflow_locked(
        self,
        unattended: Optional[str],
        recovery_policy: Optional[RecoveryPolicy],
        input_provider: Optional[InputProvider],
        inputs: Dict[str, Any],
        merge_plans: Optional[Dict[str, MergePlan]],
    ) -> bool:
        if not self._workflow_map.is_loaded:
            logger.error("Cannot start: no workflow loaded")
            return False

        start_node_id = self._workflow_map.find_start_node_id()
        if start_node_id is None:
            logger.error("Cannot start: workflow has no start node")
            return False

        # Contract inputs (Step 4a) are filled before anything is reset, so
        # a run with missing or invalid inputs never starts (C10).
        workflow = self._workflow_map.get_workflow_data_for_save()
        if merge_plans is None:
            merge_plans = merge_plans_from_analysis(analyze_flow(workflow["nodes"], self.factory))
        start_data = workflow["nodes"].get(start_node_id) or {}
        resolved_inputs = resolve_inputs(
            start_rows(start_data.get("config") or {}), inputs,
            strict=self._workflow_map.callable,
        )

        # Leftover tasks would otherwise wake inside the new run and write
        # into its memory, so they are cancelled before any state is reset.
        await self._cancel_leftover_tasks()

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        self.current_run_id = run_id
        if self._owns_call_tree:
            self._call_tree = None
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
            recovery_policy=recovery_policy,
            input_provider=input_provider,
            inputs=inputs,
            resolved_inputs=resolved_inputs,
            revision=workflow_revision(workflow),
            started_at=datetime.now(timezone.utc).isoformat(),
            merge_plans=merge_plans,
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

    def _new_supervisor(self, run: RunContext, *, register=True, **kwargs: Any) -> Supervisor:
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
            delivery: Optional[Delivery],
            visit: int,
            timeout_seconds: Optional[float] = None,
        ) -> Dict[str, Any]:
            return await self._wait_for_merge_in_run(
                run, merge_node_id, branch_id, delivery, visit, timeout_seconds
            )

        branch_id = str(kwargs.get("branch_id") or "")

        async def call_subworkflow_here(
            node_id: str, workflow_id: str, inputs: Dict[str, Any], text_inputs: Any = (),
            visit: int = 0, attempt: int = 0,
        ) -> Dict[str, Any]:
            from .subworkflow_calls import call_subworkflow

            return await call_subworkflow(
                self, run, branch_id, node_id, workflow_id, inputs, text_inputs, visit, attempt)

        def report_outcome(
            node_id: str,
            state: str,
            delivered_to: List[str],
            reason: Optional[str] = None,
        ) -> None:
            run.record_outcome(node_id, state, delivered_to, reason)
            if (
                state == "completed"
                and self._workflow_map.successor_ids(node_id) <= set(delivered_to)
            ):
                # Delivered to every successor: nothing can newly become
                # unreachable, so skip the whole-graph scan (keeps long linear
                # runs linear). Waits still re-evaluate.
                self._evaluate_waits(run)
                return
            self._after_outcome(run, branch_id)

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
            run_started_at=run.started_at,
            secrets_manager=self._secrets_manager,
            recovery_policy=run.recovery_policy,
            input_provider=run.input_provider,
            report_node_outcome=report_outcome,
            run_inputs=run.resolved_inputs,
            # Only a callable workflow returns results; elsewhere a Return
            # End is ignored, as the validator warns (C27).
            publish_result=(lambda values: self._publish_result(run, values))
            if self._workflow_map.callable else None,
            call_subworkflow=call_subworkflow_here,
            get_setting=self._configuration_manager.get,
            **kwargs,
        )
        # Children are prepared before their tasks publish registration. Inherit
        # a pause even when an in-flight Branch hands off after pause().
        if self.state == WorkflowState.PAUSED:
            supervisor.request_pause()
        if register:
            run.live_supervisors[supervisor.branch_id] = supervisor
        return supervisor

    def pause(self) -> None:
        """Request all active supervisors to pause (a supervisor waiting for
        input pauses before its next node)."""
        if self.state not in (WorkflowState.RUNNING, WorkflowState.WAITING_FOR_INPUT):
            return
        for supervisor in self._run.live_supervisors.values() if self._run else ():
            supervisor.request_pause()
        self._set_state(WorkflowState.PAUSED)
        for child in list(self._children):
            child.pause()

    def resume(self) -> None:
        """Resume all paused supervisors."""
        if self.state != WorkflowState.PAUSED:
            return
        for supervisor in self._run.live_supervisors.values() if self._run else ():
            supervisor.request_resume()
        self._set_state(WorkflowState.RUNNING)
        for child in list(self._children):
            child.resume()

    def stop(self) -> None:
        """Stop the run on request: unfinished nodes are stopped, not skipped."""
        if self._run is not None:
            self._run.stop_requested = True
        self._halt()

    def _halt(self) -> None:
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
            self._run.stop_requested = True
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
            if self._owns_call_tree and self._call_tree is not None:
                return self._call_tree.submit_user_input(branch_id, value)
            logger.warning("No supervisor with branch_id %s", branch_id)
            return False
        supervisor.submit_user_input(value)
        return True

    def waiting_for_input(self, branch_id: str) -> bool:
        """Whether this branch (or a subworkflow's) still waits for an answer."""
        supervisor = self._supervisors.get(branch_id)
        if supervisor is None:
            if self._owns_call_tree and self._call_tree is not None:
                return self._call_tree.waiting_for_input(branch_id)
            return False
        return supervisor.waiting_for_input

    def submit_recovery_action(self, branch_id: str, action: str) -> bool:
        """Forward a recovery action to the supervisor waiting for it."""
        supervisor = self._supervisors.get(branch_id)
        if supervisor is None:
            if self._owns_call_tree and self._call_tree is not None:
                return self._call_tree.submit_recovery_action(branch_id, action)
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
        if payload.get('run_id') != self.current_run_id:
            return
        branch_id = payload["branch_id"]
        self._supervisors[branch_id] = payload["supervisor"]
        logger.debug("Registered supervisor %s at depth %d", branch_id, payload["depth"])

    def _on_supervisor_terminating(self, payload: Dict[str, Any]) -> None:
        if payload.get('run_id') != self.current_run_id:
            return
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
        supervisor = run.live_supervisors.pop(branch_id, None)
        self._account_for_branch_termination(run, branch_id, supervisor)
        self._after_outcome(run, branch_id)

    def _on_request_branch(self, payload: Dict[str, Any]) -> None:
        """Preflight and register the entire handoff before scheduling children."""
        response = payload.get('response')
        if not isinstance(response, BranchLaunch):
            return
        run = self._run
        if run is None or payload.get('run_id') != run.run_id or run.stop_requested:
            response.error = NodeError('node_error', 'The Branch request belongs to an inactive run.')
            return
        depth = payload['parent_depth'] + 1
        limit = int(self._configuration_manager.get('max_branch_depth'))
        if payload['branches'] and depth > limit:
            response.error = NodeError('branch_depth_exceeded',
                f'Branch depth {depth} exceeds the limit {limit}; no paths were launched.',
                details=dict(depth=depth, limit=limit), retryable=False)
            return
        parent = payload['parent_branch_id']
        lineage = tuple(payload.get('parent_lineage', ()))
        children = []
        try:
            for chosen in payload['branches']:
                child = self._new_supervisor(run, register=False,
                    branch_id=f'branch_{uuid.uuid4().hex[:6]}', depth=depth,
                    start_node_id=chosen['start_node_id'], initial_data=chosen.get('initial_data', {}),
                    parent_branch_id=parent, delivery=chosen.get('delivery'),
                    lineage=lineage + (chosen['path_index'],))
                children.append(child)
        except Exception as exc:
            response.error = NodeError('node_error', f'Branch could not prepare its paths: {exc}')
            return
        # No await or publication between replacing the parent and registering
        # every child. A waiter can never observe an empty handoff window.
        group_key = run.branch_groups.get(parent)
        if group_key is None and children:
            group_key = (run.run_id, f'group_{uuid.uuid4().hex}', 1)
            run.merge_groups[group_key] = BranchGroup(group_key, payload['source_node_id'], lineage, payload['parent_depth'])
        if group_key is not None:
            group = run.merge_groups[group_key]
            if parent in group.members:
                group.members[parent].state = 'handoff'
            for child in children:
                run.branch_groups[child.branch_id] = group_key
                group.members[child.branch_id] = GroupMember(child.lineage, child.depth)
            for merge_id, plan in run.merge_plans.items():
                if plan.fork_node_id == group.fork_node_id:
                    self._merge_barrier(run, group, merge_id)
        for child in children:
            run.live_supervisors[child.branch_id] = child
            run.record_delivery(payload.get('source_node_id') or '', child.position)
        response.accepted = True
        if group_key is not None:
            self._update_merge_barriers(run, run.merge_groups[group_key])
        for child in children:
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

    def _after_outcome(self, run: RunContext, branch_id: str) -> None:
        """Spread skips (D9), then re-evaluate pending waits (D5)."""
        self._spread_skips(run, branch_id)
        self._evaluate_waits(run)

    def _spread_skips(self, run: RunContext, branch_id: str) -> None:
        """Mark nodes no path can reach as skipped, spreading downstream."""
        if run.stop_requested:
            # A stopped run's unfinished nodes are stopped, not skipped.
            return
        reach = run.live_reach(self._workflow_map)
        while True:
            candidates = run.skip_candidates(self._workflow_map, reach)
            if not candidates:
                return
            for node_id, reason in candidates:
                run.record_outcome(node_id, "skipped", (), reason)
                logger.info("Node %s skipped (%s) in run %s", node_id, reason, run.run_id)
                self._event_bus.publish(
                    NODE_EXECUTION_UPDATE,
                    {
                        "run_id": run.run_id,
                        "branch_id": branch_id,
                        "node_id": node_id,
                        "visit_index": 0,
                        "attempt_index": 0,
                        "status": "skipped",
                        "reason": reason,
                    },
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

    # -- actual-arrival merge barriers -----------------------------------------

    def _merge_barrier(self, run, group, merge_node_id):
        key = (run.run_id, group.key[1], merge_node_id, 1)
        if key not in run.merge_barriers:
            plan = run.merge_plans.get(merge_node_id)
            if plan is not None and plan.fork_node_id != group.fork_node_id:
                plan = None
            run.merge_barriers[key] = MergeBarrier(key, plan)
        return run.merge_barriers[key]

    async def wait_for_merge_arrival(self, merge_node_id, branch_id, delivery, visit=1,
                                     timeout_seconds=None):
        if self._run is None:
            return dict(arrival_outcome='cancelled')
        return await self._wait_for_merge_in_run(self._run, merge_node_id, branch_id,
                                                  delivery, visit, timeout_seconds)

    async def _wait_for_merge_in_run(self, run, merge_node_id, branch_id, delivery, visit,
                                     timeout_seconds=None):
        if run.stop_requested or run is not self._run:
            return dict(arrival_outcome='cancelled')
        # A repeated notification after the winner detached from its group
        # is still the same arrival, never a new pass-through invocation.
        if delivery is not None and any(key[2:] == (merge_node_id, 1, branch_id, visit, delivery.identity)
                                        for key in run.arrival_outcomes):
            return dict(arrival_outcome='absorbed')
        group_key = run.branch_groups.get(branch_id)
        if group_key is None:
            result = {'continue': True, 'present': bool(delivery and delivery.present)}
            if result['present']:
                result['value'] = delivery.value
            return result
        group = run.merge_groups[group_key]
        barrier = self._merge_barrier(run, group, merge_node_id)
        member = group.members[branch_id]
        if delivery is None or delivery.run_id != run.run_id or delivery.target_node_id != merge_node_id:
            raise NodeError('merge_delivery_missing', 'Merge needs the actual incoming delivery, not a wire snapshot.')
        identity = (run.run_id, group.key[1], merge_node_id, 1, branch_id, visit, delivery.identity)
        if identity not in barrier.arrivals and barrier.state == 'open':
            run.arrival_sequence += 1
            barrier.arrivals[identity] = MergeArrival(run.run_id, group.key[1], merge_node_id,
                branch_id, member.lineage, member.depth, run.arrival_sequence, visit, delivery)
            member.state, member.merge_node_id = 'waiting', merge_node_id
        self._update_merge_barriers(run, group)
        if timeout_seconds is not None and timeout_seconds > 0:
            await asyncio.wait_for(barrier.event.wait(), timeout_seconds)
        else:
            await barrier.event.wait()
        barrier.observed.add(branch_id)
        if barrier.state == 'cancelled':
            outcome = dict(arrival_outcome='cancelled')
        elif barrier.state == 'failed':
            if not barrier.failure_claimed:
                barrier.failure_claimed = True
                run.arrival_outcomes[identity] = 'failed'
                raise barrier.failure
            outcome = dict(arrival_outcome='absorbed')
        elif barrier.winner == branch_id and not barrier.continuation_claimed:
            barrier.continuation_claimed = True
            run.branch_groups.pop(branch_id, None)
            member.state = 'joined'
            outcome = {'continue': True, 'present': True, 'value': barrier.value,
                       'continuation_depth': group.opening_depth}
        else:
            outcome = dict(arrival_outcome='absorbed')
        name = outcome.get('arrival_outcome', 'continuing')
        run.arrival_outcomes.setdefault(identity, name)
        if name == 'absorbed':
            member.state = 'absorbed'
        self._retire_merge_group(run, group)
        return outcome

    def _update_merge_barriers(self, run, group):
        for barrier in list(run.merge_barriers.values()):
            if barrier.key[1] != group.key[1]:
                continue
            if barrier.state == 'failed' and not barrier.arrivals and not barrier.failure_claimed:
                participants = [m for m in group.members.values() if m.state != 'handoff'
                    and barrier.plan and barrier.plan.slots_for(m.lineage[len(group.root_lineage):])]
                if not any(m.state in ('running', 'waiting') for m in participants):
                    self._record_merge_failure(run, barrier, next(iter(group.members), ''))
            if barrier.state != 'open':
                continue
            if run.stop_requested:
                barrier.state = 'cancelled'
                barrier.event.set()
                continue
            if barrier.plan is None:
                if barrier.arrivals:
                    self._fail_merge_barrier(barrier, NodeError('merge_shape_unknown',
                        'Merge slot shape is not declared. Supply the reviewed graph plan (one or many per slot).'))
                continue
            participants = [(branch, m) for branch, m in group.members.items()
                if m.state != 'handoff' and barrier.plan.slots_for(m.lineage[len(group.root_lineage):])]
            failed = next(((branch, m) for branch, m in participants if m.state == 'failed'), None)
            if failed:
                branch, member = failed
                slots = barrier.plan.slots_for(member.lineage[len(group.root_lineage):])
                path = '/'.join(path_port(i) for i in member.lineage) or branch
                self._fail_merge_barrier(barrier, NodeError('merge_member_failed',
                    f'Path {path}, slot {", ".join(slots)}, failed at '
                    f'{self._describe_node(member.failed_node_id or "")}: {member.failure_message}',
                    details=dict(branch_id=branch, slots=slots, node_id=member.failed_node_id)))
                run.wait_registry.mark_unreachable(node_key(barrier.key[2]), str(barrier.failure))
                if not barrier.arrivals and not any(m.state in ('running', 'waiting') for _, m in participants):
                    self._record_merge_failure(run, barrier, branch)
                continue
            if any(m.state == 'cancelled' for _, m in participants):
                barrier.state = 'cancelled'
                barrier.event.set()
                continue
            if any(m.state == 'running' or (m.state == 'waiting' and m.merge_node_id != barrier.key[2])
                   for _, m in participants):
                continue
            if not barrier.arrivals:
                continue
            arrivals = sorted(barrier.arrivals.values(), key=lambda a: (a.lineage, a.sequence))
            values = {}
            unknown = {a.delivery.target_port for a in arrivals} - set(barrier.plan.slots)
            if unknown:
                self._fail_merge_barrier(barrier, NodeError('merge_shape_unknown',
                    'Merge received undeclared slots: ' + ', '.join(sorted(unknown))))
                continue
            for slot in sorted(barrier.plan.slots, key=lambda s: path_index(s) if path_index(s) is not None else 1000):
                rows = [a for a in arrivals if a.delivery.target_port == slot]
                shape = barrier.plan.slots[slot]
                if shape.cardinality == 'one' and len(rows) > 1:
                    self._fail_merge_barrier(barrier, NodeError('merge_shape_invalid',
                        f'Merge slot {slot} is declared scalar but received concurrent paths.'))
                    break
                present = [a.delivery.value for a in rows if a.delivery.present]
                if present:
                    values[slot] = present if shape.cardinality == 'many' else present[0]
            else:
                winner = min(arrivals, key=lambda a: (a.depth, a.sequence))
                barrier.winner, barrier.value, barrier.state = winner.branch_id, values, 'sealed'
                barrier.event.set()

    @staticmethod
    def _fail_merge_barrier(barrier, error):
        if barrier.state == 'open':
            barrier.failure, barrier.state = error, 'failed'
            barrier.event.set()

    def _record_merge_failure(self, run, barrier, branch_id):
        """No arrival can own the normal error pipeline (or the run is aborting)."""
        if barrier.failure_claimed:
            return
        barrier.failure_claimed = True
        merge_id = barrier.key[2]
        self._error_handler.log_error(barrier.failure,
            dict(run_id=run.run_id, node_id=merge_id, branch_id=branch_id),
            code=barrier.failure.code)
        run.record_outcome(merge_id, 'failed')
        self._event_bus.publish(NODE_EXECUTION_UPDATE, dict(run_id=run.run_id,
            node_id=merge_id, branch_id=branch_id, visit_index=0,
            attempt_index=0, status='errored', reason=barrier.failure.code))
        for supervisor in run.live_supervisors.values():
            if supervisor.position == merge_id:
                supervisor.suppress_terminal_status = True
                supervisor.settled_arrival_node_id = merge_id

    def _account_for_branch_termination(self, run, branch_id, supervisor=None):
        key = run.branch_groups.pop(branch_id, None)
        if key is None or key not in run.merge_groups:
            return
        group = run.merge_groups[key]
        member = group.members[branch_id]
        reason = getattr(supervisor, 'termination_reason', 'cancelled')
        if member.state not in ('handoff', 'absorbed', 'joined'):
            member.state = 'cancelled' if run.stop_requested else reason
            member.failed_node_id = getattr(supervisor, 'current_node_id', None)
            member.failure_message = getattr(supervisor, 'terminal_error', '')
        self._update_merge_barriers(run, group)
        self._retire_merge_group(run, group)

    def _retire_merge_group(self, run, group):
        if any(m.state in ('running', 'waiting') for m in group.members.values()):
            return
        barriers = [b for b in run.merge_barriers.values() if b.key[1] == group.key[1]]
        if any(len(b.observed) < len({a.branch_id for a in b.arrivals.values()}) for b in barriers):
            return
        for barrier in barriers:
            run.merge_barriers.pop(barrier.key, None)
        run.merge_groups.pop(group.key, None)

    # -- bus handlers --------------------------------------------------------------

    def _on_supervisor_state_update(self, payload: Dict[str, Any]) -> None:
        if payload.get("run_id") != self.current_run_id:
            return
        if self.state == WorkflowState.PAUSED:
            return  # An in-flight node can begin waiting without resuming the run.
        if payload["state"] == "WAITING_FOR_INPUT":
            self._set_state(WorkflowState.WAITING_FOR_INPUT)
        elif payload["state"] == "AWAITING_RECOVERY":
            self._set_state(WorkflowState.WAITING_FOR_INPUT)
        elif self.state == WorkflowState.WAITING_FOR_INPUT and payload["state"] == "RUNNING":
            self._set_state(WorkflowState.RUNNING)
        # (A PAUSED run stays paused when a prompt is answered.)

    def _on_supervisor_error(self, payload: Dict[str, Any]) -> None:
        if payload.get('run_id') != self.current_run_id:
            return
        self._set_state(WorkflowState.ERROR)
        self._event_bus.publish(ERROR_OCCURRED, payload)
        self._capture_outputs()
        self._record_run("ERROR")

    def _on_breakpoint_hit(self, _payload: Dict[str, Any]) -> None:
        for supervisor in self._run.live_supervisors.values() if self._run else ():
            supervisor.request_pause()
        self._set_state(WorkflowState.PAUSED)
        # The whole call tree pauses (C20): from a child, through the root.
        if not self._owns_call_tree and self._call_tree is not None:
            self._call_tree.pause_all()
        for child in list(self._children):
            child.pause()

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
        if _payload.get('run_id') != self.current_run_id:
            return
        run = self._run
        key = run.branch_groups.get(_payload.get('branch_id')) if run else None
        if key in (run.merge_groups if run else {}):
            group = run.merge_groups[key]
            member = group.members[_payload['branch_id']]
            member.state, member.failed_node_id = 'failed', _payload.get('node_id')
            member.failure_message = _payload.get('error', '')
            self._update_merge_barriers(run, group)
            # An explicit whole-workflow abort must still leave the join's
            # failure evidence. Its parked arrivals are about to be cancelled,
            # so they cannot own the normal Merge error/recovery pipeline.
            for barrier in run.merge_barriers.values():
                if barrier.key[1] != group.key[1] or barrier.state != 'failed' or barrier.failure_claimed:
                    continue
                self._record_merge_failure(run, barrier, _payload['branch_id'])
        # A failure ended the run: paths it cut off are still skipped (D9).
        self._halt()
        self._set_state(WorkflowState.ERROR)
        self._capture_outputs()
        self._record_run("ERROR")

    def _publish_result(self, run: RunContext, values: Dict[str, Any]) -> bool:
        """The Return End hands back the result once per run (C4)."""
        if run.return_values is not None:
            return False
        run.return_values = dict(values)
        return True

    def _check_required_results(self) -> None:
        """A callable workflow whose Return End never ran (a path without
        it finished) has not produced its required results (C4)."""
        run = self._run
        if run is None or run.return_values is not None or not self._workflow_map.callable:
            return
        required = [
            row["name"]
            for data in self._workflow_map.get_all_node_data().values()
            if data.get("type") == "end_node"
            for row in return_rows(data.get("config") or {})
            if row["required"]
        ]
        if required:
            self._error_handler.log_error(
                ContractError("The Return End did not run; required result(s) not produced: "
                              + ", ".join(required)),
                context={"run_id": run.run_id},
                code="result_missing",
            )

    def _check_run_completion(self) -> None:
        if self._supervisors or self._supervisor_tasks:
            return
        if self._run is not None:
            self._run.clear_flow_state()
        if self.state == WorkflowState.ERROR:
            self._capture_outputs()
            self._record_run('ERROR')
            return
        self._check_required_results()
        self._capture_outputs()
        self._set_state(WorkflowState.FINISHED)
        self._record_run("FINISHED")

    def _capture_outputs(self) -> None:
        """Store the outputs produced so far, whether the run finished or failed."""
        if not self.current_run_id:
            return
        self.run_outputs = list(
            self._memory_bank.read_persistent("output_log", default=[])
        )
        self._output_manager.store_output_log(self.current_run_id, self.run_outputs)
        self.run_outputs = self._output_manager.finalize_run(self.current_run_id)

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
        unhandled = unhandled_errors(errors)
        # Run is over on every path that records it; release runtime resources.
        # R4: run-owned files are deleted only when the run succeeded (finished,
        # no unhandled errors, not stopped); otherwise they are kept for
        # debugging. Errors routed along an error path count as handled.
        if self._run is not None:
            if self._finalize_hook is not None:
                try:
                    self._finalize_hook(self._run, final_state, errors)
                except Exception:
                    logger.exception("Subworkflow finalization failed (run %s)", self.current_run_id)
            succeeded = (
                final_state == "FINISHED"
                and not unhandled
                and not self._run.stop_requested
            )
            self._run.run_session.close_all(delete_run_files=succeeded)
        self._run_history.record_run(
            {
                "run_id": self.current_run_id,
                "workflow_id": self._workflow_map.workflow_id,
                "workflow_name": self._workflow_map.workflow_name,
                "workflow_revision": self._run.revision if self._run is not None else None,
                "started_at": self._started_at,
                "final_state": final_state,
                "error_count": len(errors),
                "unhandled_error_count": len(unhandled),
                "output_count": len(self.run_outputs),
                "node_timings": dict(self.node_timings),
                "agent_usage": self.agent_usage,
                "agent_usage_summary": usage_summary(self.agent_usage),
                "skipped_nodes": dict(self._run.skip_reasons) if self._run else {},
                # Step 4b (C22): where a child run was called from.
                **self._call_info,
                # "outputs" removed — values already persisted by OutputManager
            }
        )
        self._error_handler.finalize_run(self.current_run_id)

    @property
    def output_manager(self) -> OutputManager:
        """Output manager used by this master state."""
        return self._output_manager

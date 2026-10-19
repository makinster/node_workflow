"""
Supervisor for AttackOfTheNodes v0.5.

One supervisor walks one branch of the workflow. Branching creates additional
supervisors at incremented depth; each walks independently.
"""

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .event_bus import EventBus
from .events import (
    BREAKPOINT_HIT,
    NODE_EXECUTION_UPDATE,
    NODE_TIMING_UPDATE,
    RECOVERY_OPTIONS_AVAILABLE,
    SUPERVISOR_ERROR,
    SUPERVISOR_REGISTER,
    SUPERVISOR_REQUEST_BRANCH,
    SUPERVISOR_STATE_UPDATE,
    SUPERVISOR_TERMINATING,
    TERMINATE_WORKFLOW_REQUESTED,
    USER_INPUT_NEEDED,
    SupervisorState,
)
from .error_handler import ErrorHandler
from .memory_bank import MemoryBank
from .node_base import Node, NodeContext
from .node_errors import (
    MUX_INPUT_PORT,
    DEFAULT_ERROR_CODE,
    ENGINE_ERROR_DEFINITIONS,
    ENGINE_UNATTENDED_INPUT,
    ENGINE_UPSTREAM_UNREACHABLE,
    ERROR_PORT,
    FAILED_INPUT,
    NodeError,
    build_error_payload,
    definitions_with_default,
    json_safe,
)
from .run_policies import (
    UNATTENDED_ACTIONS,
    InputProvider,
    InputRequest,
    RecoveryPolicy,
    RecoveryRequest,
    RECOVERY_ACTIONS,
    TERMINATE_BRANCH,
    UnattendedInputError,
    unattended_policies,
)
from .run_session import RunSession
from .secrets_manager import SecretsManager
from .wait_registry import TargetUnreachableError
from .workflow_map import WorkflowMap


logger = logging.getLogger(__name__)


def _task_is_cancelling() -> bool:
    """True when the running task itself has been asked to cancel."""
    task = asyncio.current_task()
    return bool(task is not None and task.cancelling())


@dataclass
class _Failure:
    """A node failure described by its code (D7)."""

    code: str
    message: str
    exception: BaseException
    details: Dict[str, Any]
    retryable: bool
    stage: str = "execute"


@dataclass
class _NodeResult:
    """Mutable holder written by node signal callbacks."""

    completed: bool = False
    payload: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None


class Supervisor:
    """Walks one path through the workflow graph asynchronously."""

    def __init__(
        self,
        run_id: str,
        branch_id: str,
        depth: int,
        start_node_id: str,
        workflow_map: WorkflowMap,
        memory_bank: MemoryBank,
        event_bus: EventBus,
        error_handler: Optional[ErrorHandler] = None,
        initial_data: Optional[Dict[str, Any]] = None,
        parent_branch_id: Optional[str] = None,
        mark_node_completed: Optional[Callable[[str], Awaitable[None]]] = None,
        wait_for_nodes: Optional[
            Callable[[List[str], Optional[float]], Awaitable[None]]
        ] = None,
        wait_for_merge: Optional[
            Callable[[str, str, str, Dict[str, Any], Optional[float]], Awaitable[Dict[str, Any]]]
        ] = None,
        node_timeout_seconds: float = 30.0,
        run_session: Optional[RunSession] = None,
        secrets_manager: Optional[SecretsManager] = None,
        unattended: Optional[str] = None,
        report_node_outcome: Optional[
            Callable[[str, str, List[str], Optional[str]], None]
        ] = None,
        recovery_policy: Optional[RecoveryPolicy] = None,
        input_provider: Optional[InputProvider] = None,
        run_inputs: Optional[Dict[str, Any]] = None,
        publish_result: Optional[Callable[[Dict[str, Any]], bool]] = None,
        call_subworkflow: Optional[Callable[..., Any]] = None,
    ) -> None:
        if unattended is not None:
            if unattended not in UNATTENDED_ACTIONS:
                raise ValueError(f"Unknown unattended policy: {unattended!r}")
            default_policy, default_provider = unattended_policies(unattended)
            recovery_policy = recovery_policy or default_policy
            input_provider = input_provider or default_provider
        self.run_id = run_id
        self.branch_id = branch_id
        self.depth = depth
        self.parent_branch_id = parent_branch_id

        self._start_node_id = start_node_id
        self._initial_data = dict(initial_data) if initial_data else {}
        # (node_id, port) that routed this supervisor to its current node, so
        # an input port fed by several connections reads the one that fired.
        self._arrived_from: Optional[tuple] = None
        # The failed node's input, kept while a failure is routed along
        # `error` (offered to nodes with ``receives_failed_input``).
        self._failed_input: Any = None
        self._workflow_map = workflow_map
        self._memory_bank = memory_bank
        self._event_bus = event_bus
        self._error_handler = error_handler or ErrorHandler(event_bus)

        self.state = SupervisorState.IDLE
        self.current_node_id: Optional[str] = None

        self._stop_requested = False
        self._pause_requested = False
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._pending_input_future: Optional[asyncio.Future] = None
        self._pending_recovery_future: Optional[asyncio.Future] = None
        self._skip_breakpoint_once_for: Optional[str] = None
        self._mark_node_completed = mark_node_completed
        self._wait_for_nodes = wait_for_nodes
        self._wait_for_merge = wait_for_merge
        self._node_timeout_seconds = float(node_timeout_seconds)
        self._run_session = run_session
        self._secrets_manager = secrets_manager
        # None means attended: a client answers through MasterState.
        self._recovery_policy = recovery_policy
        self._input_provider = input_provider
        self._report_node_outcome = report_node_outcome
        self._run_inputs = run_inputs
        self._publish_result = publish_result
        self._call_subworkflow = call_subworkflow
        self._last_delivered: List[str] = []
        self._visit_index = 0
        self._attempt_index = 0
        self._input_interrupted = False
        self._last_node_status: Optional[str] = None
        self._node_phase = "queued"

    def _call_for(self, node_id: str):
        """The subworkflow call bound to the node being executed (Step 4b)."""
        if self._call_subworkflow is None:
            return None
        call = self._call_subworkflow

        async def call_here(workflow_id, inputs, text_inputs=()):
            return await call(node_id, workflow_id, inputs, text_inputs,
                              self._visit_index, self._attempt_index)
        return call_here

    async def run(self) -> None:
        """Run this supervisor until its path ends or errors."""
        self._event_bus.publish(
            SUPERVISOR_REGISTER,
            {
                "branch_id": self.branch_id,
                "supervisor": self,
                "depth": self.depth,
                "run_id": self.run_id,
                "parent_branch_id": self.parent_branch_id,
                "start_node_id": self._start_node_id,
            },
        )

        try:
            await self._run_loop()
        except asyncio.CancelledError:
            if self._last_node_status in {"running", "waiting"}:
                self._publish_node_execution("stopped")
            self.state = SupervisorState.TERMINATED
            raise
        except Exception as exc:
            logger.exception("Unhandled error in supervisor %s", self.branch_id)
            self._fail(exc)
        finally:
            self._publish_terminating()

    @property
    def position(self) -> Optional[str]:
        """Node this supervisor is at or about to run; ``None`` once ended."""
        if self.state == SupervisorState.IDLE:
            # Created but not started yet: it will begin at its start node.
            return self._start_node_id
        if self.state in (SupervisorState.TERMINATED, SupervisorState.ERROR):
            return None
        return self.current_node_id

    def _report_outcome(
        self,
        node_id: Optional[str],
        state: str,
        delivered_to: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Tell the run which final state a node reached and where it routed."""
        if node_id and self._report_node_outcome is not None:
            self._report_node_outcome(node_id, state, list(delivered_to or []), reason)

    def request_pause(self) -> None:
        """Pause between node executions."""
        self._pause_requested = True
        self._resume_event.clear()

    def request_resume(self) -> None:
        """Resume execution after a pause."""
        self._pause_requested = False
        self._resume_event.set()

    def request_stop(self) -> None:
        """Stop after the current safe point."""
        self._stop_requested = True
        self._resume_event.set()
        if self._pending_input_future and not self._pending_input_future.done():
            self._input_interrupted = True
            # A stop is not an empty answer: prevent the node from publishing
            # outputs or satisfying completion gates after the interrupted wait.
            self._pending_input_future.cancel()
        if self._pending_recovery_future and not self._pending_recovery_future.done():
            self._pending_recovery_future.set_result("TERMINATE_BRANCH")

    def submit_user_input(self, value: str) -> None:
        """Resolve a pending user-input request."""
        if self._pending_input_future and not self._pending_input_future.done():
            self._pending_input_future.set_result(value)

    def submit_recovery_action(self, action: str) -> None:
        """Resolve a pending recovery decision."""
        if self._pending_recovery_future and not self._pending_recovery_future.done():
            self._pending_recovery_future.set_result(action)

    async def _run_loop(self) -> None:
        self.state = SupervisorState.RUNNING
        self.current_node_id = self._start_node_id
        self._publish_state_update()

        while self.current_node_id is not None:
            if self._stop_requested:
                break

            if self._pause_requested:
                await self._resume_event.wait()
                if self._stop_requested:
                    break

            if await self._pause_for_breakpoint_if_needed():
                if self._stop_requested:
                    break

            self._visit_index += 1
            self._attempt_index = 0
            self._input_interrupted = False
            self._last_node_status = None
            node = self._workflow_map.get_node_instance(self.current_node_id)
            if node is None:
                self._fail(f"Node {self.current_node_id} not found in workflow map")
                return

            inputs = self._prepare_inputs(node)
            result = await self._execute_node(node, inputs)
            if self._stop_requested:
                break

            routed = False
            while result.error is not None:
                failure = self._describe_failure(node, result.error)
                target = self._error_route(failure.code)
                # A failure an error path handles is shown as recovered, not
                # as an error (D10); otherwise it is errored as before.
                self._publish_node_execution(
                    "recovered" if target is not None else "errored",
                    reason=failure.code if target is not None else None,
                )
                record = self._log_failure(failure, inputs, handled=target is not None)
                failed_node_id = self.current_node_id
                if target is not None:
                    # A matching error path exists: route the coded payload
                    # along `error` instead of asking for recovery (D7).
                    self._memory_bank.store_transient(
                        failed_node_id or "",
                        ERROR_PORT,
                        self._error_payload(failure, record),
                    )
                    self._report_outcome(failed_node_id, "failed", [target])
                    self._arrived_from = (failed_node_id, ERROR_PORT)
                    ports = node.get_input_ports()
                    self._failed_input = (
                        inputs.get(ports[0]) if len(ports) == 1 else dict(inputs)
                    )
                    self.current_node_id = target
                    self._node_phase = "queued"
                    self._publish_state_update()
                    routed = True
                    break
                action = await self._request_recovery(record, failure)
                if action == "RETRY":
                    result = await self._execute_node(node, inputs)
                    if self._stop_requested:
                        break
                    continue
                if action == "SKIP":
                    # D9: the node is skipped and its branch ends; downstream
                    # nodes are skipped until the path rejoins something live.
                    self._publish_node_execution("skipped", reason="recovery_skip")
                    self._report_outcome(failed_node_id, "skipped", [], "recovery_skip")
                    self.state = SupervisorState.TERMINATED
                    self._publish_state_update()
                    return
                self._report_outcome(failed_node_id, "failed")
                if action == "TERMINATE_WORKFLOW":
                    self._event_bus.publish(
                        TERMINATE_WORKFLOW_REQUESTED,
                        {"branch_id": self.branch_id, "run_id": self.run_id},
                    )
                    self._stop_requested = True
                    return
                self.state = SupervisorState.TERMINATED
                self._publish_state_update()
                return

            if self._stop_requested:
                break
            if routed:
                continue

            if not result.completed or result.payload is None:
                self._fail(f"Node {self.current_node_id} returned without signaling")
                return

            completed_node_id = self.current_node_id
            self._last_delivered = []
            if result.payload:
                self.current_node_id = self._handle_payload(result.payload)

            if completed_node_id and self._mark_node_completed is not None:
                await self._mark_node_completed(completed_node_id)
            self._report_outcome(completed_node_id, "completed", self._last_delivered)

            if result.payload:
                self._node_phase = "queued"
                self._publish_state_update()

        if self.state != SupervisorState.ERROR:
            self.state = SupervisorState.TERMINATED
            self._publish_state_update()

    async def _pause_for_breakpoint_if_needed(self) -> bool:
        """Pause before executing the current node when its breakpoint is set."""
        current_node_id = self.current_node_id
        if current_node_id is None:
            return False
        node_data = self._workflow_map.get_node_data(current_node_id) or {}
        if not node_data.get("breakpoint"):
            return False
        if (
            self._recovery_policy is not None
            and not self._recovery_policy.pause_at_breakpoints
        ):
            # No one can resume this run, so breakpoints are skipped.
            return False
        if self._skip_breakpoint_once_for == current_node_id:
            self._skip_breakpoint_once_for = None
            return False

        self._event_bus.publish(
            BREAKPOINT_HIT,
            {
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "node_id": current_node_id,
                "depth": self.depth,
            },
        )
        if not self._pause_requested:
            self.request_pause()
        self._publish_state_update()
        await self._resume_event.wait()
        self._skip_breakpoint_once_for = current_node_id
        return True

    def _prepare_inputs(self, node: Node) -> Dict[str, Any]:
        """Build node inputs from connected upstream transient outputs."""
        inputs: Dict[str, Any] = {}
        for input_port in node.get_input_ports():
            source = self._input_source(input_port)
            if source is None:
                if input_port in self._initial_data:
                    inputs[input_port] = self._initial_data[input_port]
                continue
            inputs[input_port] = self._memory_bank.read_transient(
                source["source_node_id"], source["source_port"]
            )

        if not inputs and not node.get_input_ports():
            inputs = dict(self._initial_data)
        if getattr(node, "receives_failed_input", False):
            if self._arrived_from is not None and self._arrived_from[1] == ERROR_PORT:
                # The failure that routed here: its payload and its input.
                inputs[ERROR_PORT] = self._memory_bank.read_transient(
                    self._arrived_from[0], ERROR_PORT
                )
                inputs[FAILED_INPUT] = self._failed_input
            else:
                # Reached on the normal path: no failure to report, even if a
                # stale error payload is still in memory from an earlier visit.
                inputs.pop(ERROR_PORT, None)
        return inputs

    def _input_source(self, input_port: str) -> Optional[Dict[str, str]]:
        """The connection feeding ``input_port``; the one that fired wins."""
        sources = self._workflow_map.find_input_sources(
            self.current_node_id or "", input_port
        )
        if not sources:
            return None
        if self._arrived_from is not None:
            arrived_node, arrived_port = self._arrived_from
            for source in sources:
                if source["source_node_id"] == arrived_node and (
                    arrived_port is None or source["source_port"] == arrived_port
                ):
                    return source
        return sources[0]

    async def _execute_node(self, node: Node, inputs: Dict[str, Any]) -> _NodeResult:
        """Execute a node and capture its context signal result."""
        self._attempt_index += 1
        self._node_phase = "executing"
        self._publish_state_update()
        self._publish_node_execution("running")
        result = _NodeResult()

        def signal_done(payload: Dict[str, Any]) -> None:
            result.completed = True
            result.payload = payload

        def signal_error(exc: Exception) -> None:
            result.completed = True
            result.error = exc

        async def signal_waiting_for_input(prompt: str) -> str:
            if self._input_provider is not None:
                # Raising here fails the node; it then follows recovery.
                self._publish_node_execution("waiting")
                try:
                    value = await self._input_provider.provide(
                        InputRequest(
                            run_id=self.run_id,
                            branch_id=self.branch_id,
                            node_id=self.current_node_id,
                            prompt=prompt,
                        )
                    )
                except asyncio.CancelledError:
                    if _task_is_cancelling():
                        raise
                    # A provider's own cancelled future is a failure, not a
                    # stop of this run.
                    raise RuntimeError("Input provider was cancelled") from None
                self._publish_node_execution("running")
                return value
            future: asyncio.Future = asyncio.get_running_loop().create_future()
            self._pending_input_future = future
            self.state = SupervisorState.WAITING_FOR_INPUT
            self._publish_node_execution("waiting")
            self._publish_state_update()
            self._event_bus.publish(
                USER_INPUT_NEEDED,
                {
                    "branch_id": self.branch_id,
                    "node_id": self.current_node_id,
                    "prompt": prompt,
                    "run_id": self.run_id,
                },
            )
            value = await future
            self._pending_input_future = None
            self._publish_node_execution("stopped" if self._input_interrupted else "running")
            self.state = SupervisorState.RUNNING
            self._publish_state_update()
            return value

        async def wait_for_nodes(
            target_node_ids: List[str], timeout_seconds: Optional[float] = None
        ) -> None:
            if self._wait_for_nodes is None:
                raise RuntimeError("Completion registry is not available")
            timeout = (
                self._node_timeout_seconds
                if timeout_seconds is None
                else timeout_seconds
            )
            await self._wait_for_nodes(target_node_ids, timeout)

        async def wait_for_merge(
            merge_node_id: str,
            branch_id: str,
            selected_input_port: str,
            inputs: Dict[str, Any],
            timeout_seconds: Optional[float] = None,
        ) -> Dict[str, Any]:
            if self._wait_for_merge is None:
                raise RuntimeError("Merge barrier is not available")
            timeout = (
                self._node_timeout_seconds
                if timeout_seconds is None
                else timeout_seconds
            )
            return await self._wait_for_merge(
                merge_node_id,
                branch_id,
                selected_input_port,
                inputs,
                timeout,
            )

        def publish_event(event_name: str, payload: Dict[str, Any]) -> None:
            # Node-emitted events always carry run/branch/node identity so
            # subscribers can attribute them (EventBus payload standing rule).
            body: Dict[str, Any] = {
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "node_id": self.current_node_id,
            }
            body.update(payload or {})
            self._event_bus.publish(event_name, body)

        context = NodeContext(
            node_id=self.current_node_id or "",
            branch_id=self.branch_id,
            run_id=self.run_id,
            inputs=inputs,
            memory_bank=self._memory_bank,
            signal_done=signal_done,
            signal_error=signal_error,
            signal_waiting_for_input=signal_waiting_for_input,
            wait_for_nodes=wait_for_nodes,
            wait_for_merge=wait_for_merge,
            run_session=self._run_session,
            secrets_manager=self._secrets_manager,
            publish_event=publish_event,
            run_inputs=self._run_inputs,
            publish_result=self._publish_result,
            call_subworkflow=self._call_for(self.current_node_id or ""),
            node_alias=str((self._workflow_map.get_node_data(self.current_node_id or "") or {}).get("alias") or ""),
        )

        started_at = perf_counter()
        try:
            await node.execute(context)
        except Exception as exc:
            result.completed = True
            result.error = exc
        finally:
            self._event_bus.publish(
                NODE_TIMING_UPDATE,
                {
                    "run_id": self.run_id,
                    "branch_id": self.branch_id,
                    "node_id": self.current_node_id,
                    "seconds": perf_counter() - started_at,
                    "visit_index": self._visit_index,
                    "attempt_index": self._attempt_index,
                },
            )

        if result.error is None and result.payload is not None:
            result.error = self._error_port_signal(result.payload)

        if self._input_interrupted or self._stop_requested:
            self._publish_node_execution("stopped")
        elif result.error is not None:
            pass  # the failure pipeline reports errored or recovered
        elif not result.completed or result.payload is None:
            self._publish_node_execution("errored")
        else:
            self._publish_node_execution("done")
        return result

    def _error_port_signal(self, payload: Dict[str, Any]) -> Optional[Exception]:
        """A payload signaled on the ``error`` port is a failure (D7).

        The node's ``data`` may carry ``error`` (message), ``code``,
        ``details`` and ``retryable``. Whether it routes along a connected
        ``error`` path or goes to recovery is decided by the failure pipeline.
        """
        if payload.get("output_port") != ERROR_PORT:
            return None
        data = payload.get("data") or {}
        message = str(data.get(ERROR_PORT) or "Node signaled failure on its error port")
        details = data.get("details") if isinstance(data.get("details"), dict) else {}
        retryable = data.get("retryable")
        return NodeError(
            str(data.get("code") or DEFAULT_ERROR_CODE),
            message,
            details=details,
            retryable=retryable if isinstance(retryable, bool) else None,
        )

    def _describe_failure(self, node: Node, error: BaseException) -> _Failure:
        """Give a failure its code: declared, engine, or the default generic."""
        definitions = definitions_with_default(getattr(node, "error_definitions", []))
        by_code = {item["code"]: item for item in definitions}
        details: Dict[str, Any] = {}
        retryable: Optional[bool] = None
        if isinstance(error, NodeError):
            code = error.code
            # Details are persisted and published; keep them JSON-safe.
            details = json_safe(dict(error.details))
            retryable = error.retryable
            if code not in by_code and code not in ENGINE_ERROR_DEFINITIONS:
                logger.warning(
                    "Node %s raised undeclared error code %r; using %r",
                    self.current_node_id, code, DEFAULT_ERROR_CODE,
                )
                details["undeclared_code"] = code
                code = DEFAULT_ERROR_CODE
        elif isinstance(error, TargetUnreachableError):
            code = ENGINE_UPSTREAM_UNREACHABLE
        elif isinstance(error, UnattendedInputError):
            code = ENGINE_UNATTENDED_INPUT
        else:
            code = DEFAULT_ERROR_CODE
        if retryable is None:
            definition = by_code.get(code) or ENGINE_ERROR_DEFINITIONS.get(code) or {}
            retryable = bool(definition.get("retryable", False))
        return _Failure(
            code=code,
            message=str(error) or type(error).__name__,
            exception=error,
            details=details,
            retryable=retryable,
        )

    def _log_failure(
        self, failure: _Failure, inputs: Dict[str, Any], handled: bool = False
    ) -> Dict[str, Any]:
        """Log and persist every failure once, routed (handled) or not."""
        error = failure.exception
        return self._error_handler.log_error(
            error if isinstance(error, Exception) else Exception(str(error)),
            {
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "node_id": self.current_node_id,
                "depth": self.depth,
                "inputs": json_safe(inputs),
                "stage": failure.stage,
                "details": failure.details,
                "retryable": failure.retryable,
            },
            code=failure.code,
            handled=handled,
        )

    def _error_payload(self, failure: _Failure, record: Dict[str, Any]) -> Dict[str, Any]:
        return build_error_payload(
            code=failure.code,
            message=failure.message,
            node_id=self.current_node_id,
            run_id=self.run_id,
            stage=failure.stage,
            details=failure.details,
            retryable=failure.retryable,
            error_id=record.get("id"),
        )

    def _error_route(self, code: str) -> Optional[str]:
        """The node to route this failure to, or None to request recovery.

        A connected ``error`` port leading to a node that matches codes (an
        error mux) routes only matching codes; a mux with no matching code
        falls through to recovery or the run's policy. Any other node
        connected to ``error`` receives every failure.
        """
        target = self._workflow_map.find_next_node_id(
            self.current_node_id or "", output_port=ERROR_PORT
        )
        if target is not None:
            instance = self._workflow_map.get_node_instance(target)
            accepts = getattr(instance, "accepts_error_code", None)
            if not callable(accepts) or accepts(code):
                return target
        return self._inline_error_route(code)

    def _inline_error_route(self, code: str) -> Optional[str]:
        """An Error Mux placed inline after the failed node catches the codes
        it selects: the node's normal output feeds the mux's ``input``."""
        node = self._workflow_map.get_node_data(self.current_node_id or "") or {}
        for conn in (node.get("connections") or {}).get("outputs", []):
            if conn.get("target_port") != MUX_INPUT_PORT:
                continue
            target = str(conn.get("target_node_id") or "")
            instance = self._workflow_map.get_node_instance(target)
            if not getattr(instance, "catches_upstream_errors", False):
                continue
            if instance.accepts_error_code(code):
                return target
        return None

    async def _request_recovery(
        self, error_record: Dict[str, Any], failure: _Failure
    ) -> str:
        """Publish recovery options for a logged error and await a decision."""
        if self._recovery_policy is not None:
            # The error is logged and persisted above; the run's policy decides.
            try:
                action = await self._recovery_policy.decide(
                    RecoveryRequest(
                        run_id=self.run_id,
                        branch_id=self.branch_id,
                        node_id=self.current_node_id,
                        error=error_record,
                    )
                )
            except asyncio.CancelledError:
                if _task_is_cancelling():
                    raise
                action = self._policy_failed(RuntimeError("Recovery policy was cancelled"))
            except Exception as exc:
                action = self._policy_failed(exc)
            if action not in RECOVERY_ACTIONS:
                logger.warning(
                    "Recovery policy returned %r; terminating the branch", action
                )
                action = TERMINATE_BRANCH
            return action
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending_recovery_future = future
        self.state = SupervisorState.AWAITING_RECOVERY
        self._publish_state_update()
        self._event_bus.publish(
            RECOVERY_OPTIONS_AVAILABLE,
            {
                "branch_id": self.branch_id,
                "node_id": self.current_node_id,
                "run_id": self.run_id,
                "error": error_record,
                "error_message": error_record["message"],
                "code": failure.code,
                "category": error_record["category"],
                "traceback": error_record["traceback"],
                "options": [
                    "RETRY",
                    "SKIP",
                    "TERMINATE_BRANCH",
                    "TERMINATE_WORKFLOW",
                ],
            },
        )
        action = await future
        self._pending_recovery_future = None
        self.state = SupervisorState.RUNNING
        self._publish_state_update()
        return action

    def _policy_failed(self, exc: BaseException) -> str:
        """Log a broken recovery policy like any error, then end the branch."""
        self._error_handler.log_error(
            exc if isinstance(exc, Exception) else RuntimeError(str(exc)),
            {
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "node_id": self.current_node_id,
                "depth": self.depth,
                "stage": "recovery_policy",
            },
        )
        return TERMINATE_BRANCH

    def _handle_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        """Write outputs, spawn branches, and determine next node.

        Records the node ids it routes to in ``_last_delivered``.
        """
        self._last_delivered = []
        data = payload.get("data", {})
        if data:
            for port_name, value in data.items():
                self._memory_bank.store_transient(
                    self.current_node_id or "", port_name, value
                )

        if payload.get("terminate_branch"):
            return None

        branches = payload.get("branches")
        if branches:
            self._spawn_branches(branches)
            return None

        explicit_next = payload.get("next_node_id")
        if explicit_next:
            self._last_delivered.append(explicit_next)
            self._arrived_from = (self.current_node_id, None)
            return explicit_next

        # Port routing hint embedded in data (used by RandomBranchNode and similar)
        route_port = (payload.get("data") or {}).get("_route_via_port")
        output_port = route_port or payload.get("output_port", "default")
        next_node_id = self._workflow_map.find_next_node_id(
            self.current_node_id or "", output_port=output_port
        )
        if next_node_id:
            self._last_delivered.append(next_node_id)
            self._arrived_from = (self.current_node_id, output_port)
        return next_node_id

    def _spawn_branches(self, branches: List[Dict[str, Any]]) -> None:
        """Publish one branch request per requested output path."""
        for branch in branches:
            output_port = branch.get("output_port", "default")
            start_node_id = self._workflow_map.find_next_node_id(
                self.current_node_id or "", output_port=output_port
            )
            if start_node_id is None:
                logger.warning(
                    "Branch on port %s has no downstream connection; skipping",
                    output_port,
                )
                continue
            self._event_bus.publish(
                SUPERVISOR_REQUEST_BRANCH,
                {
                    "parent_branch_id": self.branch_id,
                    "parent_depth": self.depth,
                    "run_id": self.run_id,
                    "source_node_id": self.current_node_id,
                    "start_node_id": start_node_id,
                    "initial_data": branch.get("initial_data", {}),
                },
            )

    def _fail(self, error: Any) -> None:
        """Transition to error and publish a supervisor error event."""
        self._report_outcome(self.current_node_id, "failed")
        self.state = SupervisorState.ERROR
        self._publish_node_execution("errored")
        message = str(error) if isinstance(error, Exception) else error
        self._event_bus.publish(
            SUPERVISOR_ERROR,
            {
                "branch_id": self.branch_id,
                "node_id": self.current_node_id,
                "error": message,
                "run_id": self.run_id,
            },
        )

    def _publish_node_execution(self, status: str, reason: Optional[str] = None) -> None:
        """Report an attempt outcome independently of supervisor termination."""
        if self.current_node_id is None:
            return
        self._last_node_status = status
        payload: Dict[str, Any] = {
            "run_id": self.run_id,
            "branch_id": self.branch_id,
            "node_id": self.current_node_id,
            "visit_index": self._visit_index,
            "attempt_index": self._attempt_index,
            "status": status,
        }
        if reason:
            payload["reason"] = reason
        self._event_bus.publish(NODE_EXECUTION_UPDATE, payload)

    def _publish_state_update(self) -> None:
        self._event_bus.publish(
            SUPERVISOR_STATE_UPDATE,
            {
                "branch_id": self.branch_id,
                "state": self.state.value,
                "current_node_id": self.current_node_id,
                "run_id": self.run_id,
                "node_phase": self._node_phase,
            },
        )

    def _publish_terminating(self) -> None:
        self._event_bus.publish(
            SUPERVISOR_TERMINATING,
            {
                "branch_id": self.branch_id,
                "final_state": self.state.value,
                "run_id": self.run_id,
                "current_node_id": self.current_node_id,
                "stop_requested": self._stop_requested,
            },
        )

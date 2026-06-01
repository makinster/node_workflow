"""
Supervisor for AttackOfTheNodes v0.5.

One supervisor walks one branch of the workflow. Branching creates additional
supervisors at incremented depth; each walks independently.
"""

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, List, Optional

from .event_bus import EventBus
from .events import (
    BREAKPOINT_HIT,
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
from .workflow_map import WorkflowMap


logger = logging.getLogger(__name__)


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
    ) -> None:
        self.run_id = run_id
        self.branch_id = branch_id
        self.depth = depth
        self.parent_branch_id = parent_branch_id

        self._start_node_id = start_node_id
        self._initial_data = dict(initial_data) if initial_data else {}
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

    async def run(self) -> None:
        """Run this supervisor until its path ends or errors."""
        self._event_bus.publish(
            SUPERVISOR_REGISTER,
            {
                "branch_id": self.branch_id,
                "supervisor": self,
                "depth": self.depth,
                "run_id": self.run_id,
            },
        )

        try:
            await self._run_loop()
        except Exception:
            logger.exception("Unhandled error in supervisor %s", self.branch_id)
            self.state = SupervisorState.ERROR
        finally:
            self._publish_terminating()

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
            self._pending_input_future.set_result("")
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

            node = self._workflow_map.get_node_instance(self.current_node_id)
            if node is None:
                self._fail(f"Node {self.current_node_id} not found in workflow map")
                return

            inputs = self._prepare_inputs(node)
            result = await self._execute_node(node, inputs)

            while result.error is not None:
                action = await self._request_recovery(result.error, inputs)
                if action == "RETRY":
                    result = await self._execute_node(node, inputs)
                    continue
                if action == "SKIP":
                    self.current_node_id = self._workflow_map.find_next_node_id(
                        self.current_node_id or "", output_port="default"
                    )
                    result = _NodeResult(completed=True, payload={})
                    break
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

            if not result.completed or result.payload is None:
                self._fail(f"Node {self.current_node_id} returned without signaling")
                return

            if result.payload:
                self.current_node_id = self._handle_payload(result.payload)

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
            source = self._workflow_map.find_input_source(
                self.current_node_id or "", input_port
            )
            if source is None:
                if input_port in self._initial_data:
                    inputs[input_port] = self._initial_data[input_port]
                continue
            inputs[input_port] = self._memory_bank.read_transient(
                source["source_node_id"], source["source_port"]
            )

        if not inputs and not node.get_input_ports():
            inputs = dict(self._initial_data)
        return inputs

    async def _execute_node(self, node: Node, inputs: Dict[str, Any]) -> _NodeResult:
        """Execute a node and capture its context signal result."""
        result = _NodeResult()

        def signal_done(payload: Dict[str, Any]) -> None:
            result.completed = True
            result.payload = payload

        def signal_error(exc: Exception) -> None:
            result.completed = True
            result.error = exc

        async def signal_waiting_for_input(prompt: str) -> str:
            future: asyncio.Future = asyncio.get_running_loop().create_future()
            self._pending_input_future = future
            self.state = SupervisorState.WAITING_FOR_INPUT
            self._publish_state_update()
            self._event_bus.publish(
                USER_INPUT_NEEDED,
                {
                    "branch_id": self.branch_id,
                    "node_id": self.current_node_id,
                    "prompt": prompt,
                },
            )
            value = await future
            self._pending_input_future = None
            self.state = SupervisorState.RUNNING
            self._publish_state_update()
            return value

        context = NodeContext(
            node_id=self.current_node_id or "",
            branch_id=self.branch_id,
            run_id=self.run_id,
            inputs=inputs,
            memory_bank=self._memory_bank,
            signal_done=signal_done,
            signal_error=signal_error,
            signal_waiting_for_input=signal_waiting_for_input,
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
                },
            )

        return result

    async def _request_recovery(
        self, error: BaseException, inputs: Dict[str, Any]
    ) -> str:
        """Log an error, publish recovery options, and await a decision."""
        error_record = self._error_handler.log_error(
            error if isinstance(error, BaseException) else Exception(str(error)),
            {
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "node_id": self.current_node_id,
                "depth": self.depth,
                "inputs": inputs,
            },
        )
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

    def _handle_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        """Write outputs, spawn branches, and determine next node."""
        data = payload.get("data", {})
        if data:
            for port_name, value in data.items():
                self._memory_bank.store_transient(
                    self.current_node_id or "", port_name, value
                )

        branches = payload.get("branches")
        if branches:
            self._spawn_branches(branches)
            return None

        explicit_next = payload.get("next_node_id")
        if explicit_next:
            return explicit_next

        # Port routing hint embedded in data (used by RandomBranchNode and similar)
        route_port = (payload.get("data") or {}).get("_route_via_port")
        if route_port:
            return self._workflow_map.find_next_node_id(
                self.current_node_id or "", output_port=route_port
            )

        output_port = payload.get("output_port", "default")
        return self._workflow_map.find_next_node_id(
            self.current_node_id or "", output_port=output_port
        )

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
                    "start_node_id": start_node_id,
                    "initial_data": branch.get("initial_data", {}),
                },
            )

    def _fail(self, error: Any) -> None:
        """Transition to error and publish a supervisor error event."""
        self.state = SupervisorState.ERROR
        message = str(error) if isinstance(error, Exception) else error
        self._event_bus.publish(
            SUPERVISOR_ERROR,
            {
                "branch_id": self.branch_id,
                "node_id": self.current_node_id,
                "error": message,
            },
        )

    def _publish_state_update(self) -> None:
        self._event_bus.publish(
            SUPERVISOR_STATE_UPDATE,
            {
                "branch_id": self.branch_id,
                "state": self.state.value,
                "current_node_id": self.current_node_id,
            },
        )

    def _publish_terminating(self) -> None:
        self._event_bus.publish(
            SUPERVISOR_TERMINATING,
            {"branch_id": self.branch_id, "final_state": self.state.value},
        )

"""What the TUI knows about each running subworkflow call (Step 4c-2).

The backend forwards a child run's events to the root run's bus wrapped in
``SUBWORKFLOW_RUN_UPDATE`` (``backend.subworkflow_calls.WATCHED_EVENTS``).
``ChildRuns`` keeps one ``ChildRun`` per live call, built the same way the app
builds the root run's display state, so an Execution screen can show a call
exactly as it shows the root run. A call's record is dropped when it ends
(owner, 2026-10-20: finished calls are not opened; their results show on the
calling node).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.events import (
    NODE_EXECUTION_UPDATE,
    NODE_TIMING_UPDATE,
    SUPERVISOR_REGISTER,
    SUPERVISOR_STATE_UPDATE,
    SUPERVISOR_TERMINATING,
    WORKFLOW_STATE_UPDATE,
)
from frontend.execution_state import ExecutionDisplayState


class ChildRun:
    """One live call: the same fields the app keeps for the root run."""

    def __init__(self, invocation_id: str, parent_run_id: str, call_site_node_id: str,
                 call_path: List[str]) -> None:
        self.invocation_id = invocation_id
        self.parent_run_id = parent_run_id
        self.call_site_node_id = call_site_node_id
        self.call_path = list(call_path)
        self.run_id: Optional[str] = None
        self.workflow_state = "RUNNING"
        self.execution_state = ExecutionDisplayState()
        self.node_statuses: Dict[str, str] = {}
        self.node_skip_reasons: Dict[str, str] = {}
        self.node_timings: Dict[str, float] = {}

    def apply(self, event: str, payload: Dict[str, Any]) -> None:
        if event == WORKFLOW_STATE_UPDATE:
            run_id = payload.get("run_id")
            if run_id and run_id != self.run_id:
                self.run_id = run_id
                self.execution_state.reset(run_id)
            self.workflow_state = str(payload.get("state") or self.workflow_state)
            return
        if not self.execution_state.accepts(payload):
            return
        state = self.execution_state
        if event == SUPERVISOR_REGISTER:
            state.register(payload)
        elif event == SUPERVISOR_STATE_UPDATE:
            state.supervisor(payload)
        elif event == SUPERVISOR_TERMINATING:
            state.supervisor(payload, terminated=True)
        elif event == NODE_EXECUTION_UPDATE:
            state.node(payload)
            self.node_statuses = state.node_statuses()
            self.node_skip_reasons = state.skip_reasons()
        elif event == NODE_TIMING_UPDATE and payload.get("node_id"):
            node_id = payload["node_id"]
            self.node_timings[node_id] = self.node_timings.get(node_id, 0.0) + float(payload.get("seconds") or 0.0)
            state.timing(payload)

    @property
    def waiting(self) -> bool:
        """Some path of this call waits for an answer or a recovery choice."""
        return any(branch.get("state") in {"WAITING_FOR_INPUT", "AWAITING_RECOVERY"}
                   for branch in self.execution_state.branches.values())


class ChildRuns:
    """Live calls of the current root run, by invocation id."""

    def __init__(self) -> None:
        self.calls: Dict[str, ChildRun] = {}

    def clear(self) -> None:
        self.calls.clear()

    def update(self, payload: Dict[str, Any]) -> None:
        invocation_id = str(payload.get("invocation_id") or "")
        if not invocation_id:
            return
        call = self.calls.get(invocation_id)
        if call is None:
            call = self.calls[invocation_id] = ChildRun(
                invocation_id, str(payload.get("parent_run_id") or ""),
                str(payload.get("call_site_node_id") or ""), list(payload.get("call_path") or []))
        call.apply(str(payload.get("event") or ""), dict(payload.get("payload") or {}))

    def ended(self, payload: Dict[str, Any]) -> None:
        self.calls.pop(str(payload.get("invocation_id") or ""), None)

    def children_of(self, run_id: Optional[str]) -> List[ChildRun]:
        """The live calls the run ``run_id`` made directly."""
        return [call for call in self.calls.values() if run_id and call.parent_run_id == run_id]

    def waiting_inside(self, call: ChildRun, _seen: Optional[set] = None) -> Optional[ChildRun]:
        """The call that waits for you, at or below ``call`` (followed by run
        ids, never by display names), or None."""
        if call.waiting:
            return call
        seen = _seen if _seen is not None else set()
        if call.invocation_id in seen:
            return None
        seen.add(call.invocation_id)
        for child in self.children_of(call.run_id):
            found = self.waiting_inside(child, seen)
            if found is not None:
                return found
        return None

    def at(self, parent_run_id: Optional[str], node_id: str) -> List[ChildRun]:
        """The live calls a node of the run ``parent_run_id`` started."""
        return [call for call in self.calls.values()
                if call.call_site_node_id == node_id and call.parent_run_id == parent_run_id]

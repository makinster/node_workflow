"""Child runs: one workflow calling a subworkflow and waiting (Step 4b).

Design: ``docs/SUBWORKFLOWS_PROPOSAL.md`` C11–C20, C22. Each call builds a
small stack of its own (bus, workflow map, memory, master state) and shares
the process's read-only parts: the node factory, settings, secrets and the
run-history writer (C18). A ``CallTree`` belongs to the root run; it holds
the limits (C16), counts live children, routes prompts and answers between
the root's client and any descendant (C19), and spreads pause (C20).

Cancellation needs no extra machinery: stopping a run, or terminating one
branch, cancels the calling supervisor's task, and the call stops its child
and waits until it has stopped before letting the cancellation through
(C20: "requesting cancellation is not the same as having stopped").
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional

from .contracts import (
    ContractError,
    ContractInputError,
    parse_text,
    return_rows,
    start_rows,
)
from .error_handler import unhandled_errors
from .event_bus import EventBus
from .events import RECOVERY_OPTIONS_AVAILABLE, USER_INPUT_NEEDED
from .file_refs import is_file_reference
from .node_errors import NodeError
from .persistence import load_workflow

if TYPE_CHECKING:
    from .master_state import MasterState
    from .run_context import RunContext

logger = logging.getLogger(__name__)

#: Error codes a Subworkflow node can fail with (routable on ``error``).
CALL_ERROR_DEFINITIONS: List[Dict[str, Any]] = [
    {"code": "child_not_found", "description": "The subworkflow is missing or is not a subworkflow.", "retryable": False},
    {"code": "child_input_missing", "description": "A required input of the subworkflow has no value.", "retryable": False},
    {"code": "child_input_invalid", "description": "An input does not match the subworkflow's input type.", "retryable": False},
    {"code": "child_failed", "description": "The subworkflow failed or ended with unhandled errors.", "retryable": True},
    {"code": "child_output_conflict", "description": "The subworkflow sent its results back more than once.", "retryable": False},
    {"code": "depth_limit", "description": "The call is deeper than the subworkflow depth limit.", "retryable": False},
    {"code": "capacity_limit", "description": "Too many subworkflows are running at once.", "retryable": True},
]

BRIDGED_EVENTS = (USER_INPUT_NEEDED, RECOVERY_OPTIONS_AVAILABLE)


class CallTree:
    """Everything one root run shares with its descendants."""

    def __init__(self, root: "MasterState", max_depth: int, max_live: int) -> None:
        self.root = root
        self.max_depth = max_depth
        self.max_live = max_live
        self.live = 0
        self.peak_live = 0
        self._masters: Dict[str, "MasterState"] = {}

    # -- children ------------------------------------------------------------

    def register(self, invocation_id: str, master: "MasterState") -> None:
        self._masters[invocation_id] = master
        self.live += 1
        self.peak_live = max(self.peak_live, self.live)

    def unregister(self, invocation_id: str) -> None:
        if self._masters.pop(invocation_id, None) is not None:
            self.live -= 1

    def live_masters(self) -> List["MasterState"]:
        return list(self._masters.values())

    # -- prompts and answers (C19) ---------------------------------------------

    def submit_user_input(self, branch_id: str, value: str) -> bool:
        for master in self.live_masters():
            if master.owns_branch(branch_id):
                return master.submit_user_input(branch_id, value)
        return False

    def submit_recovery_action(self, branch_id: str, action: str) -> bool:
        for master in self.live_masters():
            if master.owns_branch(branch_id):
                return master.submit_recovery_action(branch_id, action)
        return False

    # -- pause (C20: the whole tree) ---------------------------------------------

    def pause_all(self) -> None:
        self.root.pause()

    def resume_all(self) -> None:
        self.root.resume()


def _copy(value: Any) -> Any:
    """A JSON-shaped copy: the two sides never share a mutable value."""
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError):
        return deepcopy(value)


def _typed_inputs(rows: List[Dict[str, Any]], inputs: Dict[str, Any], text_names: Iterable[str]) -> Dict[str, Any]:
    """The caller's values for the child's rows: configured text is parsed by
    the row's type (C6); values that arrive typed are checked by the child."""
    by_name = {row["name"]: row for row in rows if not row.get("_legacy")}
    text_names = set(text_names)
    typed: Dict[str, Any] = {}
    for name, value in inputs.items():
        row = by_name.get(name)
        if row is not None and name in text_names and isinstance(value, str):
            if value == "":
                continue  # a blank configured value means "not supplied"
            try:
                value = parse_text(row["type"], value)
            except ContractError as exc:
                raise NodeError("child_input_invalid", f"Input '{name}': {exc}",
                                details={"input": name}) from None
        typed[name] = _copy(value)
    return typed


async def call_subworkflow(
    parent: "MasterState",
    run: "RunContext",
    branch_id: str,
    node_id: str,
    workflow_id: str,
    inputs: Dict[str, Any],
    text_inputs: Iterable[str] = (),
) -> Dict[str, Any]:
    """Run ``workflow_id`` as a child of ``run`` and return its results.

    Raises ``NodeError`` with one of ``CALL_ERROR_DEFINITIONS``' codes. A
    cancellation stops the child and waits for it before propagating.
    """
    from .master_state import MasterState
    from .memory_bank import MemoryBank
    from .workflow_map import WorkflowMap

    tree = parent.call_tree_for(run)
    depth = parent.call_depth + 1
    if depth > tree.max_depth:
        raise NodeError("depth_limit", f"Subworkflow calls are limited to {tree.max_depth} levels",
                        details={"depth": depth, "limit": tree.max_depth})
    if tree.live >= tree.max_live:
        raise NodeError("capacity_limit", f"{tree.max_live} subworkflows are already running",
                        details={"live": tree.live, "limit": tree.max_live})
    data = load_workflow(str(workflow_id or ""))
    if data is None:
        raise NodeError("child_not_found", f"No saved subworkflow with id {workflow_id!r}",
                        details={"workflow_id": workflow_id})
    if not data.get("callable"):
        raise NodeError("child_not_found", f"{data.get('name') or workflow_id!r} is not a subworkflow",
                        details={"workflow_id": workflow_id})

    bus = EventBus()
    child_map = WorkflowMap(parent.factory, bus)
    child_map.load_data(data)
    invocation_id = f"call_{uuid.uuid4().hex[:8]}"
    node = parent.workflow_map.get_node_data(node_id) or {}
    call_path = parent.call_path + [str(node.get("alias") or node_id), str(data.get("name") or workflow_id)]
    child = MasterState(
        child_map,
        MemoryBank(bus),
        bus,
        run_history=parent.run_history,
        configuration_manager=parent.configuration_manager,
        secrets_manager=parent.secrets_manager,
        call_tree=tree,
        call_depth=depth,
        call_info={
            "root_run_id": tree.root.current_run_id,
            "parent_run_id": run.run_id,
            "invocation_id": invocation_id,
            "call_site_node_id": node_id,
            "call_site_alias": str(node.get("alias") or ""),
            "parent_branch_id": branch_id,
            "call_number": run.count_call(node_id),
        },
        call_path=call_path,
    )
    root_bus = tree.root.event_bus

    def bridge(event_name: str) -> Callable[[Dict[str, Any]], None]:
        def forward(payload: Dict[str, Any]) -> None:
            if root_bus is bus:
                return
            root_bus.publish(event_name, {
                **dict(payload or {}),
                "child_run_id": (payload or {}).get("run_id"),
                "run_id": tree.root.current_run_id,
                "invocation_id": invocation_id,
                "call_path": " › ".join(call_path),
            })
        return forward

    forwards = {name: bridge(name) for name in BRIDGED_EVENTS}
    for name, forward in forwards.items():
        bus.subscribe(name, forward)

    outcome: Dict[str, Any] = {"cancelled": False}
    result_rows = [row for node_data in child_map.get_all_node_data().values()
                   if node_data.get("type") == "end_node"
                   for row in return_rows(node_data.get("config") or {})]
    file_results = {row["name"] for row in result_rows if row["type"] == "file"}

    def finalize(child_run: "RunContext", final_state: str, errors: List[Dict[str, Any]]) -> None:
        """C13 steps 2-3, inside the child's finalization: collect the results
        and hand returned run-owned files over before the child closes."""
        outcome["final_state"] = final_state
        outcome["errors"] = list(errors)
        values = _copy(child_run.return_values) if child_run.return_values is not None else None
        outcome["values"] = values
        if outcome["cancelled"] or not values:
            return
        for name in file_results:
            value = values.get(name)
            if not is_file_reference(value):
                continue
            lifetime = child_run.run_session.release_file(value)
            if lifetime is not None:
                run.run_session.adopt_file(value, lifetime)

    child.set_finalize_hook(finalize)
    parent.add_child(child)
    tree.register(invocation_id, child)
    try:
        rows = start_rows((child_map.get_node_data(child_map.find_start_node_id() or "") or {}).get("config") or {})
        typed = _typed_inputs(rows, inputs, text_inputs)
        try:
            started = await child.start_workflow(
                recovery_policy=run.recovery_policy,
                input_provider=run.input_provider,
                inputs=typed,
            )
        except ContractInputError as exc:
            code = "child_input_missing" if exc.missing else "child_input_invalid"
            raise NodeError(code, str(exc), details={"missing": exc.missing, "invalid": exc.invalid,
                                                     "unknown": exc.unknown}) from None
        if not started:
            raise NodeError("child_failed", "The subworkflow could not be started")
        if parent.is_paused:
            child.pause()
        try:
            await child.wait_for_completion()
        except asyncio.CancelledError:
            outcome["cancelled"] = True
            child.stop()
            # Acknowledge: the child has stopped and cleaned up before the
            # caller's cancellation goes on (C20).
            while True:
                try:
                    await asyncio.shield(child.wait_for_completion())
                    break
                except asyncio.CancelledError:
                    continue
            raise
        final_state = outcome.get("final_state") or child.state.value
        errors = outcome.get("errors") or []
        unhandled = unhandled_errors(errors)
        if final_state != "FINISHED" or unhandled:
            conflict = any(e.get("code") == "result_conflict" for e in errors)
            first = (unhandled or errors or [{}])[0]
            raise NodeError(
                "child_output_conflict" if conflict else "child_failed",
                f"Subworkflow {data.get('name') or workflow_id!r} "
                + ("sent its results back more than once" if conflict
                   else ("failed" if final_state == "FINISHED" else f"ended {final_state.lower()}")
                   + f": {first.get('message') or 'unhandled error'}"),
                details={"child_run_id": child.current_run_id, "final_state": final_state,
                         "errors": [e.get("message") for e in unhandled[:3]]},
            )
        return outcome.get("values") or {}
    finally:
        for name, forward in forwards.items():
            bus.unsubscribe(name, forward)
        tree.unregister(invocation_id)
        parent.remove_child(child)

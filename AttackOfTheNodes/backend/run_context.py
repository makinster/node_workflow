"""
Per-run state for AttackOfTheNodes.

``MasterState`` creates one ``RunContext`` per run and hands each supervisor
callables bound to that context, so a stale supervisor can never mark
completions in another run. Nothing here is process-wide.

Delivery tracking records, for each finished node, its final state and which
outgoing connections it actually routed along. It serves the structural
unreachable rule (D5) now and the skipped status (D9) later.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Set

from .run_session import RunSession
from .wait_registry import WaitRegistry, node_key
from .node_errors import NodeError

if TYPE_CHECKING:
    from .memory_bank import MemoryBank
    from .run_policies import InputProvider, RecoveryPolicy
    from .workflow_map import WorkflowMap


NODE_COMPLETED = "completed"
NODE_FAILED = "failed"
NODE_SKIPPED = "skipped"
FINAL_STATES = frozenset({NODE_COMPLETED, NODE_FAILED, NODE_SKIPPED})

# Why a node was skipped (D9).
SKIP_RECOVERY = "recovery_skip"
SKIP_UPSTREAM_SKIPPED = "upstream_skipped"
SKIP_NOT_TAKEN = "not_taken"
SKIP_UPSTREAM_FAILED = "upstream_failed"
SKIP_REASONS = frozenset(
    {SKIP_RECOVERY, SKIP_UPSTREAM_SKIPPED, SKIP_NOT_TAKEN, SKIP_UPSTREAM_FAILED}
)


@dataclass(frozen=True)
class Delivery:
    """One fired edge, with its value captured by the sending invocation."""

    run_id: str
    source_node_id: str
    source_port: str
    target_node_id: str
    target_port: str
    present: bool
    value: Any = None
    identity: tuple = ()
    pass_number: int = field(default=1, init=False)


@dataclass(frozen=True)
class MergeSlot:
    """Graph-declared shape; producer lineages are relative to the group fork.

    These are supplied facts, not an analyser or a node configuration mode.
    Empty producers means all actual members; explicit paths can exclude an
    independent side path waiting for this Merge's completion.
    """

    cardinality: str
    producers: tuple[tuple[int, ...], ...] = ()

    def __post_init__(self):
        if self.cardinality not in ('one', 'many'):
            raise ValueError('Merge slot cardinality must be one or many')


@dataclass(frozen=True)
class MergePlan:
    fork_node_id: str
    slots: Dict[str, MergeSlot]

    def slots_for(self, lineage: tuple[int, ...]) -> list[str]:
        return [slot for slot, shape in self.slots.items() if not shape.producers or any(
            lineage[:len(path)] == path or path[:len(lineage)] == lineage
            for path in shape.producers)]


@dataclass
class BranchLaunch:
    """Synchronous EventBus response; handlers return errors instead of raising."""

    accepted: bool = False
    error: Optional[NodeError] = None


@dataclass
class GroupMember:
    lineage: tuple[int, ...]
    depth: int
    state: str = 'running'
    merge_node_id: Optional[str] = None
    failed_node_id: Optional[str] = None
    failure_message: str = ''


@dataclass
class BranchGroup:
    key: tuple[str, str, int]
    fork_node_id: str
    root_lineage: tuple[int, ...]
    opening_depth: int
    members: Dict[str, GroupMember] = field(default_factory=dict)


@dataclass(frozen=True)
class MergeArrival:
    run_id: str
    group_id: str
    merge_node_id: str
    branch_id: str
    lineage: tuple[int, ...]
    depth: int
    sequence: int
    visit: int
    delivery: Delivery
    pass_number: int = field(default=1, init=False)


@dataclass
class MergeBarrier:
    key: tuple[str, str, str, int]
    plan: Optional[MergePlan]
    arrivals: Dict[tuple, MergeArrival] = field(default_factory=dict)
    state: str = 'open'
    winner: Optional[str] = None
    value: Dict[str, Any] = field(default_factory=dict)
    failure: Optional[NodeError] = None
    failure_claimed: bool = False
    observed: Set[str] = field(default_factory=set)
    event: asyncio.Event = field(default_factory=asyncio.Event)
    continuation_claimed: bool = False


@dataclass
class RunContext:
    """Everything that belongs to one run and nothing that outlives it."""

    run_id: str
    memory_bank: "MemoryBank"
    run_session: RunSession
    parent_run_id: Optional[str] = None
    unattended: Optional[str] = None
    recovery_policy: Optional["RecoveryPolicy"] = None
    input_provider: Optional["InputProvider"] = None
    # Values supplied when the run started. Recorded now; the Start contract
    # that consumes them arrives with step 4.
    inputs: Dict[str, Any] = field(default_factory=dict)
    # Step 4a: Start's rows filled from ``inputs`` and their defaults, the
    # Return End's published result (None until it runs), and the revision
    # of the workflow definition this run executes.
    resolved_inputs: Dict[str, Any] = field(default_factory=dict)
    return_values: Optional[Dict[str, Any]] = None
    revision: Optional[str] = None
    started_at: Optional[str] = None
    wait_registry: WaitRegistry = field(default_factory=WaitRegistry)
    node_timings: Dict[str, float] = field(default_factory=dict)
    agent_usage: list[dict] = field(default_factory=list)
    branch_groups: Dict[str, tuple[str, str, int]] = field(default_factory=dict)
    merge_groups: Dict[tuple[str, str, int], BranchGroup] = field(default_factory=dict)
    merge_barriers: Dict[tuple[str, str, str, int], MergeBarrier] = field(default_factory=dict)
    merge_plans: Dict[str, MergePlan] = field(default_factory=dict)
    arrival_outcomes: Dict[tuple, str] = field(default_factory=dict)
    arrival_sequence: int = 0
    node_completions: Set[tuple[str, str, int]] = field(default_factory=set)
    # Delivery tracking: node id -> final state of its latest visit, and
    # node id -> target node ids it has routed to during this run.
    node_final: Dict[str, str] = field(default_factory=dict)
    deliveries: Dict[str, Set[str]] = field(default_factory=dict)
    skip_reasons: Dict[str, str] = field(default_factory=dict)
    # Supervisors created for this run that have not terminated yet, keyed by
    # branch id. Tracked from creation, before they register on the bus.
    live_supervisors: Dict[str, Any] = field(default_factory=dict)
    # Set by a user Stop (not by a failure terminating the workflow).
    stop_requested: bool = False
    # Step 4b (C22): how many subworkflow calls each call-site node has made
    # in this run (the "visit" a child record names).
    call_counts: Dict[str, int] = field(default_factory=dict)

    # -- completions ---------------------------------------------------------

    @property
    def completed_nodes(self) -> Set[str]:
        return {
            key[1]
            for key in self.wait_registry.completed_keys
            if len(key) == 2 and key[0] == "node"
        }

    def count_call(self, node_id: str) -> int:
        """Count one more subworkflow call from ``node_id``; return its number."""
        self.call_counts[node_id] = self.call_counts.get(node_id, 0) + 1
        return self.call_counts[node_id]

    def mark_completed(self, node_id: str) -> None:
        self.node_completions.add((self.run_id, node_id, 1))
        self.wait_registry.mark_completed(node_key(node_id))

    def clear_flow_state(self) -> None:
        """Only after participants end; completion evidence remains run-scoped."""
        self.branch_groups.clear()
        self.merge_groups.clear()
        self.merge_barriers.clear()
        self.arrival_outcomes.clear()

    # -- delivery tracking ---------------------------------------------------

    def record_outcome(
        self,
        node_id: str,
        state: str,
        delivered_to: Iterable[str] = (),
        reason: Optional[str] = None,
    ) -> None:
        """Record a node visit's final state and the targets it routed to.

        Skipped nodes carry a reason (D9); they count as finished but are
        never completed.
        """
        if state not in FINAL_STATES:
            raise ValueError(f"Unknown final node state: {state!r}")
        if state == NODE_SKIPPED:
            if reason not in SKIP_REASONS:
                raise ValueError(f"Unknown skip reason: {reason!r}")
            self.skip_reasons[node_id] = str(reason)
        else:
            self.skip_reasons.pop(node_id, None)
        self.node_final[node_id] = state
        targets = {target for target in delivered_to if target}
        if targets:
            self.deliveries.setdefault(node_id, set()).update(targets)

    def record_delivery(self, source_id: str, target_id: str) -> None:
        """Record one routed connection (e.g. a branch actually spawned)."""
        if source_id and target_id:
            self.deliveries.setdefault(source_id, set()).add(target_id)

    def delivered(self, source_id: str, target_id: str) -> bool:
        return target_id in self.deliveries.get(source_id, set())

    # -- D9: skip spreading -----------------------------------------------------

    def skip_candidates(
        self,
        workflow_map: "WorkflowMap",
        reach: Set[str],
    ) -> list[tuple[str, str]]:
        """Nodes that must now be marked skipped, with their reasons.

        A node is skipped when it has incoming connections, every source is
        final, none of them routed to it, and no live supervisor is at it or
        can reach it. The caller marks them and asks again, so skips spread
        downstream until a node with a live or delivering source is reached.
        """
        completed = self.completed_nodes
        found: list[tuple[str, str]] = []
        for node_id, data in workflow_map.get_all_node_data().items():
            if node_id in completed or node_id in self.node_final or node_id in reach:
                continue
            sources = {
                conn.get("source_node_id")
                for conn in data.get("connections", {}).get("inputs", [])
                if conn.get("source_node_id")
            }
            if not sources:
                continue
            if any(
                self.node_final.get(source) not in FINAL_STATES
                or self.delivered(source, node_id)
                for source in sources
            ):
                continue
            found.append((node_id, self._skip_reason(sources)))
        return found

    def _skip_reason(self, sources: Set[str]) -> str:
        states = {source: self.node_final.get(source) for source in sources}
        if any(
            state == NODE_FAILED and not self.deliveries.get(source)
            for source, state in states.items()
        ):
            return SKIP_UPSTREAM_FAILED
        if NODE_SKIPPED in states.values():
            return SKIP_UPSTREAM_SKIPPED
        # Every source finished and routed somewhere else: a path not taken
        # (a Conditional's other port, or `default` after routing to `error`).
        return SKIP_NOT_TAKEN

    # -- D5: structural unreachable rule --------------------------------------

    def live_reach(self, workflow_map: "WorkflowMap") -> Set[str]:
        """Nodes a live supervisor is at or can still reach."""
        reach: Set[str] = set()
        for supervisor in list(self.live_supervisors.values()):
            position = getattr(supervisor, "position", None)
            if not position or position in reach:
                continue
            reach.add(position)
            reach |= workflow_map.nodes_reachable_from(position)
        return reach

    def unreachable_reason(
        self,
        node_id: str,
        workflow_map: "WorkflowMap",
        reach: Optional[Set[str]] = None,
    ) -> Optional[str]:
        """Return why ``node_id`` can no longer complete, or ``None``.

        Never based on a timeout. A node can still complete while a live
        supervisor is at it or can reach it (this covers loops). Otherwise it
        cannot when:

        - its own latest visit ended failed or skipped; or
        - (D5) every incoming connection's source is final, none of them
          routed to it, and no live supervisor can still reach those sources.
          A node with no incoming connections is therefore unreachable at once.

        A source that has not run and that no live supervisor can reach can
        never become final any other way than being skipped (D9 marks it so
        in step 3), so it is settled now: it will never route to the target.
        """
        if node_id in self.completed_nodes:
            return None
        if reach is None:
            reach = self.live_reach(workflow_map)
        if node_id in reach:
            return None

        own_state = self.node_final.get(node_id)
        if own_state in (NODE_FAILED, NODE_SKIPPED):
            return f"it {own_state} and no live path can run it again"

        node = workflow_map.get_node_data(node_id)
        if node is None:
            return "it is not in the workflow"
        sources = {
            conn.get("source_node_id")
            for conn in node.get("connections", {}).get("inputs", [])
            if conn.get("source_node_id")
        }
        if not sources:
            return "it has no incoming connections"
        for source_id in sources:
            if source_id in reach:
                return None
            if self.delivered(source_id, node_id):
                return None
        return "no upstream source routed to it and none can still run"

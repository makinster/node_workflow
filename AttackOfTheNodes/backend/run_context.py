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

if TYPE_CHECKING:
    from .memory_bank import MemoryBank
    from .workflow_map import WorkflowMap


NODE_COMPLETED = "completed"
NODE_FAILED = "failed"
NODE_SKIPPED = "skipped"
FINAL_STATES = frozenset({NODE_COMPLETED, NODE_FAILED, NODE_SKIPPED})


@dataclass
class RunContext:
    """Everything that belongs to one run and nothing that outlives it."""

    run_id: str
    memory_bank: "MemoryBank"
    run_session: RunSession
    parent_run_id: Optional[str] = None
    unattended: Optional[str] = None
    started_at: Optional[str] = None
    wait_registry: WaitRegistry = field(default_factory=WaitRegistry)
    node_timings: Dict[str, float] = field(default_factory=dict)
    branch_groups: Dict[str, str] = field(default_factory=dict)
    merge_groups: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    merge_condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    # Delivery tracking: node id -> final state of its latest visit, and
    # node id -> target node ids it has routed to during this run.
    node_final: Dict[str, str] = field(default_factory=dict)
    deliveries: Dict[str, Set[str]] = field(default_factory=dict)
    # Supervisors created for this run that have not terminated yet, keyed by
    # branch id. Tracked from creation, before they register on the bus.
    live_supervisors: Dict[str, Any] = field(default_factory=dict)

    # -- completions ---------------------------------------------------------

    @property
    def completed_nodes(self) -> Set[str]:
        return {
            key[1]
            for key in self.wait_registry.completed_keys
            if len(key) == 2 and key[0] == "node"
        }

    def mark_completed(self, node_id: str) -> None:
        self.wait_registry.mark_completed(node_key(node_id))

    # -- delivery tracking ---------------------------------------------------

    def record_outcome(
        self, node_id: str, state: str, delivered_to: Iterable[str] = ()
    ) -> None:
        """Record a node visit's final state and the targets it routed to."""
        if state not in FINAL_STATES:
            raise ValueError(f"Unknown final node state: {state!r}")
        self.node_final[node_id] = state
        targets = {target for target in delivered_to if target}
        if targets:
            self.deliveries.setdefault(node_id, set()).update(targets)

    def delivered(self, source_id: str, target_id: str) -> bool:
        return target_id in self.deliveries.get(source_id, set())

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
            if self.node_final.get(source_id) not in FINAL_STATES:
                return None
            if self.delivered(source_id, node_id):
                return None
            if source_id in reach:
                return None
        return "every upstream source finished without routing to it"

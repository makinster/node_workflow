"""
Workflow map for AttackOfTheNodes v0.5.

Holds the currently loaded workflow in memory and provides execution-time
queries: get a node instance, find the start node, and follow connections.
"""

import logging
import uuid
from copy import deepcopy
from typing import Any, Dict, List, Optional

from .event_bus import EventBus
from .events import WORKFLOW_DIRTY
from .node_base import Node
from .node_factory import NodeFactory
from .persistence import load_workflow, save_workflow


logger = logging.getLogger(__name__)


class WorkflowMap:
    """In-memory representation of loaded workflows.

    The public API still exposes an "active workflow" for existing callers,
    but the map now keeps a small cache keyed by workflow id so the UI can
    switch between open workflows without discarding unsaved edits.
    """

    def __init__(self, factory: NodeFactory, event_bus: EventBus) -> None:
        self._factory = factory
        self._event_bus = event_bus
        self._workflow_id: Optional[str] = None
        self._workflow_name = ""
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._is_dirty = False
        self._cache: Dict[str, Dict[str, Any]] = {}

    @property
    def workflow_id(self) -> Optional[str]:
        """Current workflow id."""
        return self._workflow_id

    @property
    def workflow_name(self) -> str:
        """Current workflow name."""
        return self._workflow_name

    @property
    def is_dirty(self) -> bool:
        """Whether the workflow has unsaved changes."""
        return self._is_dirty

    @property
    def is_loaded(self) -> bool:
        """Whether a workflow is currently loaded."""
        return self._workflow_id is not None

    def load(self, workflow_id: str) -> bool:
        """Load a workflow from persistence."""
        data = load_workflow(workflow_id)
        if data is None:
            logger.error("Cannot load workflow: %s not found", workflow_id)
            return False
        self.load_data(data)
        return True

    def load_data(self, data: Dict[str, Any]) -> None:
        """Load raw workflow data into memory."""
        self._sync_active_to_cache()
        self._workflow_id = data["id"]
        self._workflow_name = data.get("name", self._workflow_id)
        self._nodes = deepcopy(data.get("nodes", {}))
        self._is_dirty = False
        self._sync_active_to_cache()

    def save(self) -> None:
        """Save the current workflow and clear dirty state."""
        if not self.is_loaded:
            logger.warning("Cannot save: no workflow loaded")
            return
        save_workflow(
            self._workflow_id,
            {"id": self._workflow_id, "name": self._workflow_name, "nodes": self._nodes},
        )
        self._is_dirty = False
        self._event_bus.publish(WORKFLOW_DIRTY, False)

    def get_workflow_data_for_save(self) -> Dict[str, Any]:
        """Return the serializable current workflow structure."""
        return {
            "id": self._workflow_id,
            "name": self._workflow_name,
            "nodes": deepcopy(self._nodes),
        }

    def mark_saved(self) -> None:
        """Clear dirty state after an external save."""
        self._is_dirty = False
        self._sync_active_to_cache()
        self._event_bus.publish(WORKFLOW_DIRTY, False)

    def create_new(self, name: str) -> str:
        """Create a fresh empty workflow."""
        self._sync_active_to_cache()
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        self._workflow_id = workflow_id
        self._workflow_name = name
        self._nodes = {}
        self._mark_dirty()
        return workflow_id

    def rename_current_workflow(self, name: str) -> bool:
        """Rename the active workflow."""
        if not self.is_loaded:
            return False
        self._workflow_name = name
        self._mark_dirty()
        return True

    def get_open_workflows(self) -> List[Dict[str, Any]]:
        """Return cached workflows for a selector/list UI."""
        self._sync_active_to_cache()
        workflows = []
        for workflow_id, entry in self._cache.items():
            workflows.append(
                {
                    "id": workflow_id,
                    "name": entry.get("name", workflow_id),
                    "is_dirty": bool(entry.get("is_dirty", False)),
                    "is_active": workflow_id == self._workflow_id,
                }
            )
        return sorted(workflows, key=lambda item: item["name"])

    def switch_active_workflow(self, workflow_id: str) -> bool:
        """Switch active workflow to one already present in the cache."""
        self._sync_active_to_cache()
        entry = self._cache.get(workflow_id)
        if entry is None:
            return False
        self._workflow_id = workflow_id
        self._workflow_name = entry.get("name", workflow_id)
        self._nodes = deepcopy(entry.get("nodes", {}))
        self._is_dirty = bool(entry.get("is_dirty", False))
        self._event_bus.publish(WORKFLOW_DIRTY, self._is_dirty)
        return True

    def close_workflow(self, workflow_id: str) -> bool:
        """Remove a workflow from the in-memory cache."""
        self._sync_active_to_cache()
        if workflow_id not in self._cache:
            return False
        del self._cache[workflow_id]
        if workflow_id == self._workflow_id:
            self._workflow_id = None
            self._workflow_name = ""
            self._nodes = {}
            self._is_dirty = False
            if self._cache:
                next_id = next(iter(self._cache))
                self.switch_active_workflow(next_id)
            else:
                self._event_bus.publish(WORKFLOW_DIRTY, False)
        return True

    def get_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Return raw node data by id."""
        return self._nodes.get(node_id)

    def get_all_node_data(self) -> Dict[str, Dict[str, Any]]:
        """Return a shallow copy of all nodes."""
        return dict(self._nodes)

    def get_node_instance(self, node_id: str) -> Optional[Node]:
        """Create an executable node instance from stored node data."""
        data = self._nodes.get(node_id)
        if data is None:
            return None
        return self._factory.create_node(data["type"], node_id, data.get("config"))

    def find_start_node_id(self) -> Optional[str]:
        """Find the first start node id."""
        for node_id, data in self._nodes.items():
            if data["type"] == "start_node":
                return node_id
        return None

    def find_next_node_id(
        self, current_node_id: str, output_port: str = "default"
    ) -> Optional[str]:
        """Follow one output connection from current_node_id."""
        node = self._nodes.get(current_node_id)
        if node is None:
            return None
        for conn in node.get("connections", {}).get("outputs", []):
            if conn.get("source_port", "default") == output_port:
                return conn.get("target_node_id")
        return None

    def find_input_source(
        self, current_node_id: str, input_port: str
    ) -> Optional[Dict[str, str]]:
        """Resolve which upstream node and port feeds an input port."""
        node = self._nodes.get(current_node_id)
        if node is None:
            return None
        for conn in node.get("connections", {}).get("inputs", []):
            if conn.get("target_port") == input_port:
                return {
                    "source_node_id": conn["source_node_id"],
                    "source_port": conn.get("source_port", "default"),
                }
        return None

    def nodes_reachable_from(self, node_id: str) -> set[str]:
        """Return all node ids reachable by following output connections forward.

        The starting node is excluded from the result, even if a cycle points
        back to it. Missing connection targets are ignored here; validation owns
        reporting broken references.
        """
        if node_id not in self._nodes:
            return set()

        reachable: set[str] = set()
        seen: set[str] = {node_id}
        stack = [
            conn.get("target_node_id")
            for conn in self._nodes[node_id].get("connections", {}).get("outputs", [])
        ]

        while stack:
            current_id = stack.pop()
            if not current_id or current_id in seen or current_id not in self._nodes:
                continue
            seen.add(current_id)
            reachable.add(current_id)
            for conn in self._nodes[current_id].get("connections", {}).get("outputs", []):
                stack.append(conn.get("target_node_id"))

        return reachable

    def add_node(
        self,
        node_type: str,
        alias: str = "",
        position: Optional[Dict[str, int]] = None,
    ) -> Optional[str]:
        """Add a node and return its id."""
        if not self._factory.is_valid_node_type(node_type):
            logger.error("Cannot add node: unknown type %s", node_type)
            return None
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        config_template = self._factory.create_config_template(node_type) or {}
        default_alias = self._factory.get_default_alias(node_type) or node_type
        self._nodes[node_id] = {
            "type": node_type,
            "alias": alias or default_alias,
            "config": config_template,
            "position": position or {"x": 0, "y": 0},
            "bookmarked": False,
            "breakpoint": False,
            "connections": {"inputs": [], "outputs": []},
        }
        self._mark_dirty()
        return node_id

    def set_bookmark(self, node_id: str, is_bookmarked: bool) -> bool:
        """Set whether a node is bookmarked for quick navigation."""
        if node_id not in self._nodes:
            return False
        self._nodes[node_id]["bookmarked"] = bool(is_bookmarked)
        self._mark_dirty()
        return True

    def set_breakpoint(self, node_id: str, enabled: bool) -> bool:
        """Set whether a node should pause execution before running."""
        if node_id not in self._nodes:
            return False
        self._nodes[node_id]["breakpoint"] = bool(enabled)
        self._mark_dirty()
        return True

    def clear_all_breakpoints(self) -> int:
        """Clear every node breakpoint and return how many were changed."""
        cleared = 0
        for node in self._nodes.values():
            if node.get("breakpoint"):
                node["breakpoint"] = False
                cleared += 1
        if cleared:
            self._mark_dirty()
        return cleared

    def get_nodes_by_filter(self, filter_name: str) -> Dict[str, Dict[str, Any]]:
        """Return nodes matching a navigation filter."""
        if filter_name == "start":
            return {
                node_id: data
                for node_id, data in self._nodes.items()
                if data.get("type") == "start_node"
            }
        if filter_name == "branches":
            return {
                node_id: data
                for node_id, data in self._nodes.items()
                if len(data.get("connections", {}).get("outputs", [])) > 1
            }
        if filter_name == "bookmarks":
            return {
                node_id: data
                for node_id, data in self._nodes.items()
                if data.get("bookmarked")
            }
        if filter_name == "outputs":
            return {
                node_id: data
                for node_id, data in self._nodes.items()
                if data.get("type") == "end_node" or not data.get("connections", {}).get("outputs", [])
            }
        return dict(self._nodes)

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and remove references from neighboring nodes."""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        for other in self._nodes.values():
            conns = other.get("connections", {})
            conns["inputs"] = [
                c for c in conns.get("inputs", []) if c.get("source_node_id") != node_id
            ]
            conns["outputs"] = [
                c for c in conns.get("outputs", []) if c.get("target_node_id") != node_id
            ]
        self._mark_dirty()
        return True

    def update_node_config(self, node_id: str, new_config: Dict[str, Any]) -> bool:
        """Replace a node config dict."""
        if node_id not in self._nodes:
            return False
        self._nodes[node_id]["config"] = dict(new_config)
        self._mark_dirty()
        return True

    def update_node_alias(self, node_id: str, alias: str) -> bool:
        """Rename a node."""
        if node_id not in self._nodes:
            return False
        self._nodes[node_id]["alias"] = alias
        self._mark_dirty()
        return True

    def connect(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> bool:
        """Connect one node output port to one node input port."""
        if source_node_id not in self._nodes or target_node_id not in self._nodes:
            return False
        source = self._nodes[source_node_id]
        target = self._nodes[target_node_id]
        source.setdefault("connections", {}).setdefault("outputs", []).append(
            {
                "source_port": source_port,
                "target_node_id": target_node_id,
                "target_port": target_port,
            }
        )
        target.setdefault("connections", {}).setdefault("inputs", []).append(
            {
                "target_port": target_port,
                "source_node_id": source_node_id,
                "source_port": source_port,
            }
        )
        self._mark_dirty()
        return True

    def disconnect(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> bool:
        """Remove a connection between two node ports."""
        if source_node_id not in self._nodes or target_node_id not in self._nodes:
            return False
        source = self._nodes[source_node_id]
        target = self._nodes[target_node_id]
        source_conns = source.setdefault("connections", {}).setdefault("outputs", [])
        target_conns = target.setdefault("connections", {}).setdefault("inputs", [])

        before = len(source_conns) + len(target_conns)
        source["connections"]["outputs"] = [
            conn
            for conn in source_conns
            if not (
                conn.get("source_port", "default") == source_port
                and conn.get("target_node_id") == target_node_id
                and conn.get("target_port") == target_port
            )
        ]
        target["connections"]["inputs"] = [
            conn
            for conn in target_conns
            if not (
                conn.get("source_node_id") == source_node_id
                and conn.get("source_port", "default") == source_port
                and conn.get("target_port") == target_port
            )
        ]
        after = (
            len(source["connections"]["outputs"])
            + len(target["connections"]["inputs"])
        )
        if after != before:
            self._mark_dirty()
            return True
        return False

    def collect_downstream_subtree(self, node_id: str) -> List[str]:
        """Return all node IDs reachable from node_id's output connections (DFS).

        The starting node itself is NOT included. Useful for computing the set
        of nodes that will become orphaned when a multi-output node is deleted.
        """
        node = self._nodes.get(node_id)
        if not node:
            return []
        seed_ids = [
            c["target_node_id"]
            for c in node.get("connections", {}).get("outputs", [])
            if c.get("target_node_id") and c["target_node_id"] in self._nodes
        ]
        visited: List[str] = []
        stack = list(seed_ids)
        seen: set = set()
        while stack:
            nid = stack.pop()
            if nid in seen or nid == node_id:
                continue
            seen.add(nid)
            visited.append(nid)
            child = self._nodes.get(nid)
            if child:
                for conn in child.get("connections", {}).get("outputs", []):
                    target = conn.get("target_node_id")
                    if target and target in self._nodes and target not in seen:
                        stack.append(target)
        return visited

    def delete_subtree(self, node_ids: List[str]) -> None:
        """Delete every node in node_ids and scrub all cross-references."""
        id_set = set(node_ids)
        for nid in node_ids:
            self._nodes.pop(nid, None)
        for other in self._nodes.values():
            conns = other.get("connections", {})
            conns["inputs"] = [
                c for c in conns.get("inputs", []) if c.get("source_node_id") not in id_set
            ]
            conns["outputs"] = [
                c for c in conns.get("outputs", []) if c.get("target_node_id") not in id_set
            ]
        if node_ids:
            self._mark_dirty()

    def _mark_dirty(self) -> None:
        # The active workflow's live state is self._nodes; it is the source of
        # truth and needs no per-mutation snapshot. The cache is refreshed
        # lazily by _sync_active_to_cache() before any path that reads it
        # (switch/close/list) or replaces the active workflow (load/create/save).
        # Syncing here instead deep-copied the whole graph on every edit, making
        # building/editing an N-node workflow O(n^2).
        self._is_dirty = True
        self._event_bus.publish(WORKFLOW_DIRTY, True)

    def _sync_active_to_cache(self) -> None:
        """Persist the active workflow fields into the in-memory cache."""
        if self._workflow_id is None:
            return
        self._cache[self._workflow_id] = {
            "id": self._workflow_id,
            "name": self._workflow_name,
            "nodes": deepcopy(self._nodes),
            "is_dirty": self._is_dirty,
        }

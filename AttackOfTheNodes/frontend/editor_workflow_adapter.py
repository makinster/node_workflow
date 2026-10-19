"""Frontend-owned workflow editing helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.node_errors import ERROR_PORT, MUX_DEFAULT_PORT
from backend.validator import _declared_membank_outputs, _membank_source_id
from frontend.node_io_display import metadata_for_type
from frontend.node_types import (
    BRANCH_END_NODE_TYPE,
    BRANCH_NODE_TYPE,
    MERGE_NODE_TYPE,
    START_NODE_TYPE,
    TOMBSTONE_NODE_TYPE,
)


ERROR_MUX_TYPE = "error_mux_node"
DELETED_NODE_SYSTEM_ROLE = "deleted_node_branch_end"
DELETED_NODE_ALIAS = "Deleted node"
DELETED_NODE_STATE_ATTR = "_editor_deleted_nodes"


@dataclass
class TombstoneRestoreReport:
    """Outcome of a tombstone restore. Plain data — rendering is a UI concern.

    The node itself is restored whenever ``restored`` is True, even if some
    connections could not be re-established. Each error/warning entry carries
    enough context for the frontend alert sections described in
    BACKEND_FRONTEND_BOUNDARY.md.
    """

    node_id: str
    restored: bool
    failure_reason: str = ""
    # {"source_node_id", "source_alias", "port", "reason"} —
    # reason: "source_missing" | "source_port_missing"
    input_errors: List[Dict[str, str]] = field(default_factory=list)
    # {"target_node_id", "target_alias", "port", "reason"} —
    # reason: "target_missing" | "target_port_missing" | "target_port_occupied"
    output_errors: List[Dict[str, str]] = field(default_factory=list)
    # {"variable", "reason"} — reason: "membank_source_missing"
    membank_warnings: List[Dict[str, str]] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return self.restored and not (
            self.input_errors or self.output_errors or self.membank_warnings
        )


def tombstone_config_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Build the save-persistent tombstone config from delete-time metadata.

    Shape follows the tombstone contract in BACKEND_FRONTEND_BOUNDARY.md:
    full original node data so restore survives save/reload, plus the port
    lists the validator reads for orphaned-connection context.
    """
    return {
        **({"delete_group": deepcopy(metadata["delete_group"])} if "delete_group" in metadata else {}),
        "original_type": str(metadata.get("original_type") or ""),
        "original_display_name": str(metadata.get("original_display_name") or ""),
        "original_alias": str(metadata.get("original_alias") or ""),
        "original_config": deepcopy(metadata.get("original_config") or {}),
        "original_inputs": deepcopy(
            metadata.get("original_input_connections") or []
        ),
        "original_outputs": deepcopy(
            metadata.get("original_output_connections") or []
        ),
        "original_input_ports": list(metadata.get("original_input_ports") or []),
        "original_output_ports": list(metadata.get("original_output_ports") or []),
    }


def metadata_from_tombstone_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild delete-time metadata from a tombstone config (inverse of above)."""
    return {
        **({"delete_group": deepcopy(config["delete_group"])} if "delete_group" in config else {}),
        "original_type": str(config.get("original_type") or ""),
        "original_display_name": str(config.get("original_display_name") or ""),
        "original_alias": str(config.get("original_alias") or ""),
        "original_config": deepcopy(config.get("original_config") or {}),
        "original_input_connections": deepcopy(config.get("original_inputs") or []),
        "original_output_connections": deepcopy(config.get("original_outputs") or []),
        "original_input_ports": list(config.get("original_input_ports") or []),
        "original_output_ports": list(config.get("original_output_ports") or []),
    }


def migrate_legacy_deleted_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a legacy branch_end_node+_system_role record to tombstone_node in-place.

    Old saves write a deleted node as branch_end_node with:
        config._system_role == DELETED_NODE_SYSTEM_ROLE
        config.deleted_node == {original_type, original_display_name, ...}

    New tombstone_node stores the full original data at the config top level,
    so legacy saves keep undo-after-reload when the metadata carried it.
    Non-matching nodes are returned unchanged.
    """
    config = node.get("config") or {}
    if not (
        node.get("type") == BRANCH_END_NODE_TYPE
        and config.get("_system_role") == DELETED_NODE_SYSTEM_ROLE
    ):
        return node
    metadata = config.get("deleted_node") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    node["type"] = TOMBSTONE_NODE_TYPE
    node["alias"] = DELETED_NODE_ALIAS
    node["config"] = tombstone_config_from_metadata(metadata)
    return node


class EditorWorkflowAdapter:
    """Apply editor-only workflow transformations for the Textual UI."""

    def __init__(self, workflow_map, factory, state_owner: Optional[Any] = None) -> None:
        self.workflow_map = workflow_map
        self.factory = factory
        self._state_owner = state_owner
        self._local_deleted_nodes: Dict[str, Dict[str, Any]] = {}

    def bind_state_owner(self, state_owner: Any) -> None:
        """Use app-owned state so soft deletes survive screen recreation."""
        self._state_owner = state_owner
        if not hasattr(state_owner, DELETED_NODE_STATE_ATTR):
            setattr(state_owner, DELETED_NODE_STATE_ATTR, {})

    def is_placeholder(self, node_id: str) -> bool:
        node = self.workflow_map.get_node_data(node_id) or {}
        return node_id in self._deleted_nodes or self.is_materialized_placeholder(node)

    def is_materialized_placeholder(self, node: Dict[str, Any]) -> bool:
        if node.get("type") == TOMBSTONE_NODE_TYPE:
            return True
        # Legacy marker, recognized until migrate_workflow_on_load runs.
        config = node.get("config") or {}
        return (
            node.get("type") == BRANCH_END_NODE_TYPE
            and config.get("_system_role") == DELETED_NODE_SYSTEM_ROLE
        )

    def placeholder_metadata(self, node_id: str) -> Dict[str, Any]:
        node = self.workflow_map.get_node_data(node_id) or {}
        if node_id in self._deleted_nodes:
            return dict(self._deleted_nodes[node_id])
        config = node.get("config") or {}
        if node.get("type") == TOMBSTONE_NODE_TYPE:
            return metadata_from_tombstone_config(config)
        metadata = config.get("deleted_node") or {}
        return dict(metadata) if isinstance(metadata, dict) else {}

    def placeholder_has_restore_data(self, node_id: str) -> bool:
        metadata = self.placeholder_metadata(node_id)
        return bool(metadata.get("original_type"))

    def replace_with_placeholder(self, node_id: str) -> bool:
        node = self.workflow_map.get_node_data(node_id)
        if node is None:
            return False
        self._deleted_nodes[node_id] = self._metadata_for_node(node)
        self._mark_dirty()
        return True

    def undo_placeholder(self, node_id: str) -> bool:
        config = (self.workflow_map.get_node_data(node_id) or {}).get('config', {})
        if config.get('delete_group') or config.get('delete_recovery'):
            self.apply_plan(self.plan_restore(node_id))
            return True
        if not self.is_placeholder(node_id):
            return False
        node = self.workflow_map.get_node_data(node_id)
        if node is None:
            return False
        if self.is_materialized_placeholder(node):
            return self.restore_tombstone(node_id).restored
        metadata = self.placeholder_metadata(node_id)
        if not str(metadata.get("original_type") or ""):
            return False
        self._deleted_nodes.pop(node_id, None)
        self._mark_dirty()
        return True

    def restore_tombstone(self, node_id: str) -> TombstoneRestoreReport:
        """Restore a save-persistent tombstone with connection validation.

        Implements the restore procedure from BACKEND_FRONTEND_BOUNDARY.md:
        node identity, alias, and config always come back; each stored
        connection is re-established only if the counterparty node and port
        still exist (and the target input port is not occupied by a different
        source). A partial restore is always preferred over keeping the
        tombstone — drift is reported, never blocking.
        """
        node = self.workflow_map.get_node_data(node_id)
        if node and (node.get('config') or {}).get('delete_group'):
            plan = self.plan_restore(node_id)
            self.apply_plan(plan)
            return TombstoneRestoreReport(node_id=node_id, restored=True,
                output_errors=[{'target_node_id': node_id, 'target_alias': '', 'port': '', 'reason': message}
                               for message in plan['conflicts']])
        if node is None or not self.is_materialized_placeholder(node):
            return TombstoneRestoreReport(
                node_id=node_id, restored=False, failure_reason="not_a_tombstone"
            )
        metadata = self.placeholder_metadata(node_id)
        original_type = str(metadata.get("original_type") or "")
        if not original_type:
            return TombstoneRestoreReport(
                node_id=node_id, restored=False, failure_reason="no_restore_data"
            )
        if not self.factory.is_valid_node_type(original_type):
            return TombstoneRestoreReport(
                node_id=node_id,
                restored=False,
                failure_reason="unknown_original_type",
            )

        report = TombstoneRestoreReport(node_id=node_id, restored=True)

        # Step 1: identity/config restore is never blocked by connection drift.
        node["type"] = original_type
        node["alias"] = str(metadata.get("original_alias") or "")
        node["config"] = deepcopy(metadata.get("original_config") or {})

        # Step 2: input connections — source must exist and still declare the
        # port. Wiring the node gained while deleted (an insert placed it after
        # a new node) is kept, and an original source whose port now leads
        # elsewhere is not re-added: one output never gets a second target.
        restored_inputs: list[Dict[str, Any]] = []
        for conn in node.get("connections", {}).get("inputs", []):
            source_node = self.workflow_map.get_node_data(str(conn.get("source_node_id") or ""))
            if source_node is None:
                continue
            record = {
                "source_port": conn.get("source_port", "default"),
                "target_node_id": node_id,
                "target_port": conn.get("target_port", "input"),
            }
            source_outputs = source_node.get("connections", {}).get("outputs", [])
            if not self._declares_output_port(source_node, record["source_port"]):
                # The path is gone (a Branch lost it): drop both halves; the
                # stored-input check below reports it.
                if record in source_outputs:
                    source_outputs.remove(record)
                continue
            if record in source_outputs:
                restored_inputs.append(deepcopy(conn))
        for conn in metadata.get("original_input_connections") or []:
            source_id = str(conn.get("source_node_id") or "")
            source_port = conn.get("source_port", "default")
            source_node = self.workflow_map.get_node_data(source_id)
            if source_node is None:
                report.input_errors.append(
                    {
                        "source_node_id": source_id,
                        "source_alias": "",
                        "port": source_port,
                        "reason": "source_missing",
                    }
                )
                continue
            declared = set(self.factory.node_output_ports(source_node)) | {ERROR_PORT}
            if source_port not in declared:
                report.input_errors.append(
                    {
                        "source_node_id": source_id,
                        "source_alias": str(source_node.get("alias") or ""),
                        "port": source_port,
                        "reason": "source_port_missing",
                    }
                )
                continue
            if conn in restored_inputs:
                continue
            taken = [
                out for out in source_node.get("connections", {}).get("outputs", [])
                if out.get("source_port", "default") == source_port
                and out.get("target_node_id") != node_id
            ]
            if taken:
                if restored_inputs:
                    continue  # already back in place through its new wiring
                report.input_errors.append(
                    {
                        "source_node_id": source_id,
                        "source_alias": str(source_node.get("alias") or ""),
                        "port": source_port,
                        "reason": "source_port_taken",
                    }
                )
                continue
            restored_inputs.append(deepcopy(conn))
            source_outputs = source_node.setdefault("connections", {}).setdefault(
                "outputs",
                [],
            )
            source_record = {
                "source_port": source_port,
                "target_node_id": node_id,
                "target_port": conn.get("target_port", "input"),
            }
            if source_record not in source_outputs:
                source_outputs.append(source_record)
        node["connections"] = {"inputs": restored_inputs, "outputs": []}

        # Step 3: output connections — target must exist and declare the port.
        own_sources = {str(conn.get("source_node_id") or "") for conn in restored_inputs}
        for conn in metadata.get("original_output_connections") or []:
            target_id = str(conn.get("target_node_id") or "")
            target_port = conn.get("target_port", "input")
            source_port = conn.get("source_port", "default")
            target_node = self.workflow_map.get_node_data(target_id)
            if target_node is None:
                report.output_errors.append(
                    {
                        "target_node_id": target_id,
                        "target_alias": "",
                        "port": target_port,
                        "reason": "target_missing",
                    }
                )
                continue
            declared = set(self.factory.node_input_ports(target_node))
            if target_port not in declared:
                report.output_errors.append(
                    {
                        "target_node_id": target_id,
                        "target_alias": str(target_node.get("alias") or ""),
                        "port": target_port,
                        "reason": "target_port_missing",
                    }
                )
                continue
            target_inputs = target_node.setdefault("connections", {}).setdefault(
                "inputs",
                [],
            )
            others = [
                str(input_conn.get("source_node_id") or "")
                for input_conn in target_inputs
                if input_conn.get("target_port", "input") == target_port
                and not (
                    input_conn.get("source_node_id") == node_id
                    and input_conn.get("source_port", "default") == source_port
                )
            ]
            # Another parent may share an ordinary input (a fan-in), unless it
            # took this node's place: it is fed by one of this node's inputs,
            # or the node has no input back. A Merge slot takes one source.
            occupied = bool(others) and (
                target_node.get("type") == MERGE_NODE_TYPE
                or not restored_inputs
                or any(self._fed_by(other, own_sources) for other in others)
            )
            if occupied:
                report.output_errors.append(
                    {
                        "target_node_id": target_id,
                        "target_alias": str(target_node.get("alias") or ""),
                        "port": target_port,
                        "reason": "target_port_occupied",
                    }
                )
                continue
            node["connections"]["outputs"].append(deepcopy(conn))
            restored_input = {
                "target_port": target_port,
                "source_node_id": node_id,
                "source_port": source_port,
            }
            if restored_input not in target_inputs:
                target_inputs.append(restored_input)

        # Step 4: membank inputs come back with the config regardless; flag
        # variables whose declared source no longer exists in the workflow.
        declared_keys = _declared_membank_outputs(self.workflow_map.get_all_node_data())
        membank_inputs = node["config"].get("membank_inputs") or []
        if isinstance(membank_inputs, list):
            for entry in membank_inputs:
                key = _membank_source_id(entry)
                if key and key not in declared_keys:
                    report.membank_warnings.append(
                        {"variable": key, "reason": "membank_source_missing"}
                    )

        node.pop("_timing_invalidated", None)
        self._deleted_nodes.pop(node_id, None)
        self._mark_dirty()
        return report

    def materialize_deleted_nodes(self) -> int:
        """Replace soft-deleted editor rows with save-persistent tombstone records."""
        materialized = 0
        for node_id, metadata in list(self._deleted_nodes.items()):
            node = self.workflow_map.get_node_data(node_id)
            if node is None or self.is_materialized_placeholder(node):
                continue
            node["type"] = TOMBSTONE_NODE_TYPE
            node["alias"] = DELETED_NODE_ALIAS
            node["config"] = tombstone_config_from_metadata(metadata)
            self._drop_outgoing_connections(node_id, node)
            node.pop("_timing_invalidated", None)
            materialized += 1
        if materialized:
            self._mark_dirty()
        return materialized

    def _metadata_for_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        original_type = node.get("type", "")
        return {
            "original_type": original_type,
            "original_display_name": self._display_name_for_type(original_type),
            "original_alias": node.get("alias", ""),
            "original_config": deepcopy(node.get("config") or {}),
            "original_input_connections": deepcopy(
                node.get("connections", {}).get("inputs", [])
            ),
            "original_output_connections": deepcopy(
                node.get("connections", {}).get("outputs", [])
            ),
            "original_input_ports": list(
                {
                    conn.get("target_port", "")
                    for conn in node.get("connections", {}).get("inputs", [])
                }
            ),
            "original_output_ports": list(
                {
                    conn.get("source_port", "")
                    for conn in node.get("connections", {}).get("outputs", [])
                }
            ),
        }

    def _drop_outgoing_connections(self, node_id: str, node: Dict[str, Any]) -> None:
        outputs = list(node.get("connections", {}).get("outputs", []))
        node.setdefault("connections", {})["outputs"] = []
        for conn in outputs:
            target_id = str(conn.get("target_node_id") or "")
            target_node = self.workflow_map.get_node_data(target_id)
            if target_node is None:
                continue
            target_inputs = target_node.setdefault("connections", {}).setdefault(
                "inputs",
                [],
            )
            target_node["connections"]["inputs"] = [
                input_conn
                for input_conn in target_inputs
                if not (
                    input_conn.get("source_node_id") == node_id
                    and input_conn.get("source_port", "default")
                    == conn.get("source_port", "default")
                    and input_conn.get("target_port", "input")
                    == conn.get("target_port", "input")
                )
            ]

    def _stub_parts(self, node_id: str):
        node = self.workflow_map.get_node_data(node_id) or {}
        upstream = list(node.get("connections", {}).get("inputs", []))
        downstream = list(node.get("connections", {}).get("outputs", []))
        if self.is_materialized_placeholder(node):
            config = node.get("config") or {}
            original_type = str(config.get("original_type") or "")
            if not downstream:
                downstream = list(config.get("original_outputs") or [])
        else:
            original_type = str(node.get("type") or "")
        return original_type, upstream, downstream

    def stub_removal_plan(self, node_id: str) -> Dict[str, List[Any]]:
        """What removing a deleted node's stub reconnects and deletes.

        The gap is bridged to one target only, so no output gets two. An
        Error Resolver keeps its No error path and takes the nodes only its
        error branches reach with it (owner, 2026-10-18). Other paths of a
        multi-path node are left for the deletion review.
        """
        config = (self.workflow_map.get_node_data(node_id) or {}).get('config', {})
        if config.get('delete_group'):
            record = self._group_for(node_id)
            return {'keep': deepcopy(record.get('keep') or []), 'doomed': []}
        original_type, _, downstream = self._stub_parts(node_id)
        if original_type in {BRANCH_NODE_TYPE, START_NODE_TYPE, MERGE_NODE_TYPE}:
            return {"keep": [], "doomed": []}
        live = [
            conn for conn in downstream
            if self.workflow_map.get_node_data(str(conn.get("target_node_id") or ""))
        ]
        if original_type == ERROR_MUX_TYPE:
            keep_port = MUX_DEFAULT_PORT
        else:
            ports = self.factory.output_ports_for(
                original_type, self.placeholder_metadata(node_id).get("original_config") or {})
            used = [str(conn.get("source_port") or "default") for conn in live
                    if conn.get("source_port") != ERROR_PORT]
            keep_port = next((port for port in ports if port in used), used[0] if used else None)
        keep = [conn for conn in live if str(conn.get("source_port") or "default") == keep_port][:1]
        doomed: List[str] = []
        if original_type == ERROR_MUX_TYPE:
            from frontend.error_mux_ui import nodes_only_reached_from

            heads = [str(conn.get("target_node_id")) for conn in live
                     if str(conn.get("source_port") or "default") != MUX_DEFAULT_PORT]
            doomed = nodes_only_reached_from(
                self.workflow_map, heads, node_id,
                extra_roots=[str(conn.get("target_node_id")) for conn in keep])
        return {"keep": keep, "doomed": doomed}

    def remove_placeholder(self, node_id: str, reconnect_gap: bool = True) -> bool:
        node = self.workflow_map.get_node_data(node_id) or {}
        if (node.get('config') or {}).get('delete_group') and reconnect_gap:
            self.apply_plan(self.plan_remove_group(node_id))
            return True
        if not self.is_placeholder(node_id):
            return False
        node = self.workflow_map.get_node_data(node_id)
        if node is None:
            self._deleted_nodes.pop(node_id, None)
            return False

        original_type, upstream_connections, downstream_connections = self._stub_parts(node_id)
        plan = self.stub_removal_plan(node_id) if reconnect_gap else {"keep": [], "doomed": []}

        self._deleted_nodes.pop(node_id, None)
        result = self.workflow_map.delete_node(node_id)

        if result and reconnect_gap and original_type == MERGE_NODE_TYPE:
            self._reconnect_merge_gap(upstream_connections, downstream_connections)
        if result:
            for doomed in plan["doomed"]:
                if self.is_placeholder(doomed):
                    self.remove_placeholder(doomed, reconnect_gap=False)
                else:
                    self.workflow_map.delete_node(doomed)
            for in_conn in upstream_connections:
                source_id = str(in_conn.get("source_node_id") or "")
                source_port = str(in_conn.get("source_port") or "default")
                if not source_id or self.workflow_map.get_node_data(source_id) is None:
                    continue
                for out_conn in plan["keep"]:
                    target_id = str(out_conn.get("target_node_id") or "")
                    target_port = str(out_conn.get("target_port") or "input")
                    if self.workflow_map.get_node_data(target_id) is None:
                        continue
                    self.workflow_map.connect(source_id, source_port, target_id, target_port)

        return result

    def _reconnect_merge_gap(
        self,
        upstream_connections: List[Dict[str, Any]],
        downstream_connections: List[Dict[str, Any]],
    ) -> bool:
        """Bridge the local path across a deleted merge node when possible."""
        upstream = self._merge_home_input_connection(upstream_connections)
        downstream = self._merge_downstream_connection(downstream_connections)
        if upstream is None or downstream is None:
            return False
        source_id = str(upstream.get("source_node_id") or "")
        source_port = str(upstream.get("source_port") or "default")
        target_id = str(downstream.get("target_node_id") or "")
        target_port = str(downstream.get("target_port") or "input")
        if not source_id or not target_id:
            return False
        source_node = self.workflow_map.get_node_data(source_id)
        target_node = self.workflow_map.get_node_data(target_id)
        if source_node is None or target_node is None:
            return False
        if not self._declares_output_port(source_node, source_port):
            return False
        if not self._declares_input_port(target_node, target_port):
            return False
        if self._output_port_has_target(source_node, source_port):
            return False
        if self._input_port_has_source(target_node, target_port):
            return False
        return self.workflow_map.connect(source_id, source_port, target_id, target_port)

    def _merge_home_input_connection(
        self,
        upstream_connections: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        for conn in upstream_connections:
            source_id = str(conn.get("source_node_id") or "")
            source_node = self.workflow_map.get_node_data(source_id)
            if source_node is None:
                continue
            if source_node.get("type") != BRANCH_END_NODE_TYPE:
                return conn
        return None

    def _merge_downstream_connection(
        self,
        downstream_connections: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        for conn in downstream_connections:
            if str(conn.get("source_port") or "default") == "default":
                return conn
        return downstream_connections[0] if downstream_connections else None

    def _fed_by(self, node_id: str, sources: set) -> bool:
        node = self.workflow_map.get_node_data(node_id) or {}
        return any(
            str(conn.get("source_node_id") or "") in sources
            for conn in node.get("connections", {}).get("inputs", [])
        )

    def _declares_output_port(self, node: Dict[str, Any], port: str) -> bool:
        # `error` is the engine-level failure port every node has (D7).
        return port == ERROR_PORT or port in self.factory.node_output_ports(node)

    def _declares_input_port(self, node: Dict[str, Any], port: str) -> bool:
        return port in self.factory.node_input_ports(node)

    def _output_port_has_target(self, node: Dict[str, Any], port: str) -> bool:
        return any(
            str(conn.get("source_port") or "default") == port
            for conn in node.get("connections", {}).get("outputs", [])
        )

    def _input_port_has_source(self, node: Dict[str, Any], port: str) -> bool:
        return any(
            str(conn.get("target_port") or "input") == port
            for conn in node.get("connections", {}).get("inputs", [])
        )

    def _is_branch_prune_terminal(self, node: Dict[str, Any]) -> bool:
        """A node that ends its path: a Merge Beacon, or a type that declares
        ``terminates_branch`` (End). Output-family nodes (Text Output, File
        Manager, File Write, ...) continue along their connections
        (file_io_continuation_v1), so they are not path ends."""
        node_type = str(node.get("type") or "")
        if node_type == BRANCH_END_NODE_TYPE:
            return True
        metadata = metadata_for_type(self.factory, node_type) or {}
        return bool(metadata.get("terminates_branch"))

    def prune_branch_tombstone(self, node_id: str, kept_port: str) -> int:
        """Keep one branch path when permanently deleting a branch-node tombstone.

        Walks every output port other than ``kept_port`` downstream (BFS) and
        deletes all reachable non-structural nodes. Then wires the branch node's
        upstream input directly to the head of the kept branch and removes the
        tombstone itself.

        ``start_node`` is always a hard stop — it is never pruned. Terminal
        branch nodes (Merge Beacons and types that declare
        ``terminates_branch``, i.e. ``end_node``) are inclusive prune
        boundaries: the terminal on a non-kept branch is deleted, but traversal
        does not continue past it. Output-family nodes are not terminals; they
        continue along their connections, so pruning continues past them.
        Merge Beacons also register their connected merge_node for orphan
        cleanup. A node still reachable from Start through a surviving route
        (the kept path or anything else) is never pruned.

        ``merge_node`` is a *conditional* stop: traversal halts there only
        while another surviving (non-pruned) branch still feeds it. If the
        branch being pruned was its only live input, the merge_node has
        nothing left to merge and would otherwise be left behind as a
        disconnected, unreachable orphan — so it is pruned too, and pruning
        cascades through its own downstream nodes (re-checking the same rule
        for any further merge_node reached that way).

        Returns the number of downstream nodes pruned, or -1 on precondition
        failure (not a placeholder, not a branch_node tombstone).
        """
        if not self.is_placeholder(node_id):
            return -1
        metadata = self.placeholder_metadata(node_id)
        if metadata.get("original_type") != BRANCH_NODE_TYPE:
            return -1

        original_outputs: List[Dict[str, Any]] = metadata.get(
            "original_output_connections"
        ) or []
        original_inputs: List[Dict[str, Any]] = metadata.get(
            "original_input_connections"
        ) or []

        _HARD_STOP_TYPES = {START_NODE_TYPE}

        # Resolve kept branch head.
        kept_target_id: Optional[str] = None
        kept_target_port: str = "input"
        for conn in original_outputs:
            if conn.get("source_port") == kept_port:
                candidate = str(conn.get("target_node_id") or "")
                if candidate and self.workflow_map.get_node_data(candidate) is not None:
                    kept_target_id = candidate
                    kept_target_port = str(conn.get("target_port") or "input")
                break
        self._disconnect_kept_branch_terminal_outputs(kept_target_id)

        # BFS to collect nodes to prune from non-kept ports. merge_node is a
        # conditional stop: record it as pending and resolve afterward.
        to_prune: set = set()
        pending_merges: set = set()
        # Computed below, before any pruning: nodes still reachable from Start
        # once the branch is gone and its upstream feeds the kept head. Such a
        # node is shared with a surviving route and is never pruned.
        protected: set = set()

        def _enqueue(start_ids: List[str]) -> None:
            queue = list(start_ids)
            while queue:
                current = queue.pop(0)
                if current in to_prune or current == kept_target_id or current in protected:
                    continue
                current_node = self.workflow_map.get_node_data(current)
                if current_node is None:
                    continue
                node_type = current_node.get("type", "")
                if node_type in _HARD_STOP_TYPES:
                    continue
                if node_type == MERGE_NODE_TYPE:
                    pending_merges.add(current)
                    continue
                to_prune.add(current)
                if node_type == BRANCH_END_NODE_TYPE:
                    for out_conn in current_node.get("connections", {}).get("outputs", []):
                        next_id = str(out_conn.get("target_node_id") or "")
                        next_node = self.workflow_map.get_node_data(next_id)
                        if next_node and next_node.get("type") == MERGE_NODE_TYPE:
                            pending_merges.add(next_id)
                    continue
                if self._is_branch_prune_terminal(current_node):
                    continue
                for out_conn in current_node.get("connections", {}).get("outputs", []):
                    next_id = str(out_conn.get("target_node_id") or "")
                    if next_id and next_id not in to_prune:
                        queue.append(next_id)

        def _future_reachable(excluded: set) -> set:
            """Reachability after branch removal and kept-path rewiring."""
            all_nodes = self.workflow_map.get_all_node_data()
            start_ids = [
                candidate_id
                for candidate_id, candidate in all_nodes.items()
                if candidate.get("type") == START_NODE_TYPE and candidate_id not in excluded
            ]
            reachable: set = set()
            queue = list(start_ids)
            while queue:
                current = queue.pop(0)
                if current in reachable or current in excluded:
                    continue
                current_node = self.workflow_map.get_node_data(current)
                if current_node is None:
                    continue
                reachable.add(current)
                if self._is_branch_prune_terminal(current_node):
                    continue
                for out_conn in current_node.get("connections", {}).get("outputs", []):
                    next_id = str(out_conn.get("target_node_id") or "")
                    if next_id and next_id not in excluded and next_id not in reachable:
                        queue.append(next_id)
                for in_conn in original_inputs:
                    if current != str(in_conn.get("source_node_id") or ""):
                        continue
                    if kept_target_id and kept_target_id not in excluded:
                        queue.append(kept_target_id)
            return reachable

        protected = {
            candidate
            for candidate in _future_reachable({node_id})
            if (self.workflow_map.get_node_data(candidate) or {}).get("type") != MERGE_NODE_TYPE
        }
        initial_starts = []
        for conn in original_outputs:
            if conn.get("source_port") == kept_port:
                continue
            start_id = str(conn.get("target_node_id") or "")
            if start_id and self.workflow_map.get_node_data(start_id) is not None:
                initial_starts.append(start_id)
        _enqueue(initial_starts)

        # Resolve pending merge_nodes: a merge_node only survives if at least
        # one of its current inputs comes from a node outside the pruned set.
        changed = True
        while changed:
            changed = False
            for merge_id in list(pending_merges):
                merge_node = self.workflow_map.get_node_data(merge_id)
                if merge_node is None:
                    pending_merges.discard(merge_id)
                    continue
                reachable_after_prune = _future_reachable(to_prune | {node_id})
                input_sources = [
                    str(conn.get("source_node_id") or "")
                    for conn in merge_node.get("connections", {}).get("inputs", [])
                ]
                live_sources = [
                    s
                    for s in input_sources
                    if s
                    and s != node_id
                    and s not in to_prune
                    and s in reachable_after_prune
                ]
                merge_is_kept_head = (
                    merge_id == kept_target_id and merge_id in reachable_after_prune
                )
                if not live_sources and not merge_is_kept_head:
                    to_prune.add(merge_id)
                    pending_merges.discard(merge_id)
                    changed = True
                    downstream_ids = [
                        str(conn.get("target_node_id") or "")
                        for conn in merge_node.get("connections", {}).get("outputs", [])
                    ]
                    _enqueue([d for d in downstream_ids if d])

        # Reconnect upstream to the kept branch head.
        if kept_target_id:
            for conn in original_inputs:
                upstream_id = str(conn.get("source_node_id") or "")
                upstream_port = str(conn.get("source_port") or "output")
                if upstream_id and self.workflow_map.get_node_data(upstream_id) is not None:
                    self.workflow_map.connect(
                        upstream_id, upstream_port,
                        kept_target_id, kept_target_port,
                    )

        # Prune downstream nodes then remove the tombstone.
        for prune_id in to_prune:
            self.workflow_map.delete_node(prune_id)

        self.remove_placeholder(node_id, reconnect_gap=False)
        return len(to_prune)

    def _disconnect_kept_branch_terminal_outputs(self, node_id: Optional[str]) -> None:
        if not node_id:
            return
        node = self.workflow_map.get_node_data(node_id)
        if node is None or not self._is_branch_prune_terminal(node):
            return
        for conn in list(node.get("connections", {}).get("outputs", [])):
            self.workflow_map.disconnect(
                node_id,
                str(conn.get("source_port") or "default"),
                str(conn.get("target_node_id") or ""),
                str(conn.get("target_port") or "input"),
            )

    def replace_placeholder(self, node_id: str, new_type: str) -> Dict[str, Any]:
        node = self.workflow_map.get_node_data(node_id)
        if node is None or not self.is_placeholder(node_id):
            return {"replaced": False, "restored_original": False}
        metadata = self.placeholder_metadata(node_id)
        original_type = metadata.get("original_type")
        restored_original = new_type == original_type
        if metadata.get('delete_group') and not restored_original:
            raise ValueError('Confirm discarding the stored group before replacing this node.')
        if restored_original and self.is_materialized_placeholder(node):
            report = self.restore_tombstone(node_id)
            return {
                "replaced": report.restored,
                "restored_original": report.restored,
                "original_type": original_type,
                "restore_report": report,
            }
        node["type"] = new_type
        node["config"] = (
            deepcopy(metadata.get("original_config") or {})
            if restored_original
            else (self.factory.create_config_template(new_type) or {})
        )
        node["alias"] = (
            metadata.get("original_alias", "")
            if restored_original
            else ""
        )
        node.pop("_timing_invalidated", None)
        self._deleted_nodes.pop(node_id, None)
        self._mark_dirty()
        return {
            "replaced": True,
            "restored_original": restored_original,
            "original_type": original_type,
        }

    def migrate_workflow_on_load(self, all_nodes: Dict[str, Dict[str, Any]]) -> int:
        """Migrate legacy deleted-node records to tombstone_node format in-place.

        Returns the count of nodes migrated. Call this after loading a workflow
        and before the editor renders the node list. The actual call-site wiring
        in app.py is deferred (UI concern); this method is testable standalone.
        """
        count = 0
        for node in all_nodes.values():
            config = node.get("config") or {}
            if (
                node.get("type") == BRANCH_END_NODE_TYPE
                and config.get("_system_role") == DELETED_NODE_SYSTEM_ROLE
            ):
                migrate_legacy_deleted_node(node)
                count += 1
        return count

    def _display_name_for_type(self, node_type: str) -> str:
        for metadata in self.factory.get_node_types_metadata():
            if metadata.get("type") == node_type:
                return metadata.get("display_name", node_type)
        return node_type

    # -- Versioned grouped deletion and saved Branch paths --------------------

    def _graph(self):
        return deepcopy(self.workflow_map.get_all_node_data())

    @staticmethod
    def _edges(nodes):
        edges = set()
        for nid, node in nodes.items():
            if node is None:
                continue
            for c in node.get('connections', {}).get('outputs', []):
                edges.add((nid, c.get('source_port', 'default'), c.get('target_node_id'), c.get('target_port', 'input')))
            for c in node.get('connections', {}).get('inputs', []):
                edges.add((c.get('source_node_id'), c.get('source_port', 'default'), nid, c.get('target_port', 'input')))
        return edges

    @staticmethod
    def _wire_graph(nodes, edges, preferred=None, removed=()):
        edges = {e for e in edges if e[0] not in removed and e[2] not in removed}
        # Connection order matters: an ordinary output follows its first edge.
        for nid, node in nodes.items():
            current = node.get('connections', {})
            reference = ((preferred or {}).get(nid) or {}).get('connections', current)
            outputs = [{'source_port': p, 'target_node_id': t, 'target_port': slot}
                       for source, p, t, slot in sorted(edges, key=lambda edge: tuple(str(value) for value in edge)) if source == nid]
            inputs = [{'target_port': slot, 'source_node_id': source, 'source_port': p}
                      for source, p, t, slot in sorted(edges, key=lambda edge: tuple(str(value) for value in edge)) if t == nid]
            def ordered(values, key):
                previous = reference.get(key, []) + current.get(key, [])
                return sorted(values, key=lambda value: previous.index(value) if value in previous else len(previous))
            node['connections'] = {'inputs': ordered(inputs, 'inputs'), 'outputs': ordered(outputs, 'outputs')}

    def _plan(self, kind, root, nodes, **details):
        return {'kind': kind, 'root': root, 'basis': self._graph(),
                'overlays': deepcopy(self._deleted_nodes), 'nodes': nodes, 'conflicts': [], **details}

    def apply_single_delete(self, plan):
        """Keep the ordinary single-node overlay until Save/Validate, as before."""
        if self._graph() != plan['basis'] or self._deleted_nodes != plan.get('overlays', {}):
            raise ValueError('The workflow changed. Review the deletion again.')
        root = plan['root']
        self._deleted_nodes[root] = {**self._metadata_for_node(self.workflow_map.get_node_data(root)),
                                     'delete_group': deepcopy(plan['record'])}
        self._mark_dirty()

    def apply_plan(self, plan):
        """Commit a checked preview through WorkflowMap, with one dirty signal.

        load_data is the public graph loader, including cache synchronization.
        Keep the workflow envelope and unrelated nodes; never write _nodes.
        """
        if self._graph() != plan['basis'] or self._deleted_nodes != plan.get('overlays', {}):
            raise ValueError('The workflow changed. Review the operation again.')
        payload = self.workflow_map.get_workflow_data_for_save()
        old_dirty = self.workflow_map.is_dirty
        try:
            self.workflow_map.load_data({**payload, 'nodes': plan['nodes']})
        except Exception:
            self.workflow_map.load_data(payload)
            if old_dirty:
                self._mark_dirty()
            raise
        for nid in set(plan.get('removed', [])) | {plan['root']}:
            self._deleted_nodes.pop(nid, None)
        self._mark_dirty()

    def _record(self, kind, root, before, after, **extra):
        import uuid
        before, after = deepcopy(before), deepcopy(after)
        if kind == 'reduction':
            for graph in (before, after):
                graph[root].get('config', {}).pop('branch_recovery', None)
        changed = {nid for nid in before.keys() | after.keys() if before.get(nid) != after.get(nid)}
        return {'version': 1, 'id': uuid.uuid4().hex, 'kind': kind, 'root': root,
                'before': {nid: deepcopy(before.get(nid)) for nid in sorted(changed)},
                'after': {nid: deepcopy(after.get(nid)) for nid in sorted(changed)}, **extra}

    @staticmethod
    def _check_record(record):
        if not isinstance(record, dict) or record.get('version') != 1:
            raise ValueError('Unsupported recovery version. The stored data was kept.')

    def _clone(self):
        from backend.event_bus import EventBus
        from backend.workflow_map import WorkflowMap
        wm = WorkflowMap(self.factory, EventBus())
        wm.load_data(self.workflow_map.get_workflow_data_for_save())
        adapter = EditorWorkflowAdapter(wm, self.factory)
        adapter._local_deleted_nodes = deepcopy(self._deleted_nodes)
        return adapter

    def _branch_keys(self, nodes, target):
        keys, seen, stack = set(), set(), [target]
        while stack:
            nid = stack.pop()
            if nid in seen or nid not in nodes:
                continue
            seen.add(nid)
            for c in nodes[nid].get('connections', {}).get('inputs', []):
                source = c.get('source_node_id')
                if (nodes.get(source) or {}).get('type') == BRANCH_NODE_TYPE:
                    keys.add(f"{source}:{c.get('source_port')}")
                else:
                    stack.append(source)
        return keys

    @staticmethod
    def _merge_keys(nodes, mapping, removed):
        for node in nodes.values():
            if node.get('type') != MERGE_NODE_TYPE:
                continue
            config = node.get('config', {})
            config['branches_to_close'] = [mapping.get(key, key) for key in config.get('branches_to_close', [])
                                           if key not in removed]
            for field in ('carry_forward_branch_id', 'selected_branch_id'):
                if config.get(field) in removed:
                    config[field] = ''
                    config['selected_input_port'] = ''
                elif config.get(field) in mapping:
                    config[field] = mapping[config[field]]

    def _clean_beacons(self, before, after, removed, reset=()):
        keys = set()
        for nid in removed | set(reset):
            if (before.get(nid) or {}).get('type') == BRANCH_END_NODE_TYPE:
                keys.update(self._branch_keys(before, nid))
        edges = self._edges(after)
        for source, port, target, slot in list(edges):
            if source in reset and (before.get(target) or {}).get('type') == MERGE_NODE_TYPE:
                edges.discard((source, port, target, slot))
                if target in after and after[target].get('config', {}).get('selected_input_port') == slot:
                    after[target]['config']['selected_input_port'] = ''
        self._wire_graph(after, edges, removed=set(before) - set(after))
        self._merge_keys(after, {}, keys)

    def _archive_nodes(self, before, removed):
        """An already deleted nested member stays deleted when its group returns."""
        for nid in removed:
            if nid not in self._deleted_nodes or nid not in before:
                continue
            metadata = self.placeholder_metadata(nid)
            before[nid].update(type=TOMBSTONE_NODE_TYPE, alias=DELETED_NODE_ALIAS,
                               config=tombstone_config_from_metadata(metadata))
            edges = {e for e in self._edges(before) if e[0] != nid}
            self._wire_graph(before, edges)

    def plan_deletion(self, node_id, kept_port=None):
        from frontend.error_mux_ui import deletion_members, guarded_node_ids
        before = self._graph()
        root = before.get(node_id)
        if not root or root.get('type') == START_NODE_TYPE or self.is_placeholder(node_id):
            raise ValueError('Select a live node other than Start.')
        adapter = self._clone()
        adapter.replace_with_placeholder(node_id)
        ordinary = adapter.stub_removal_plan(node_id)
        outputs = root.get('connections', {}).get('outputs', [])
        ports = [p for p in self.factory.node_output_ports(root) if p != ERROR_PORT]
        if root['type'] in (BRANCH_NODE_TYPE, 'conditional_node'):
            if kept_port not in ports:
                raise ValueError('Pick one path to keep.')
            keep = [c for c in outputs if c.get('source_port') == kept_port][:1]
        elif root['type'] == BRANCH_END_NODE_TYPE:
            keep = []
        elif root['type'] == MERGE_NODE_TYPE:
            homes = [c for c in root.get('connections', {}).get('inputs', [])
                     if (before.get(c.get('source_node_id')) or {}).get('type') != BRANCH_END_NODE_TYPE]
            if len(homes) > 1:
                raise ValueError('This Merge has more than one home path. Reconnect it before deleting.')
            keep = [c for c in outputs if c.get('source_port', 'default') == 'default'][:1]
        else:
            keep = ordinary['keep']
        owners = {node_id}
        shared_handlers = []
        for c in outputs:
            nid = c.get('target_node_id')
            if (before.get(nid) or {}).get('type') != ERROR_MUX_TYPE:
                continue
            other_guards = [other for other in guarded_node_ids(self.workflow_map, nid)
                            if other != node_id and not self.is_placeholder(other)]
            if other_guards:
                shared_handlers.append(nid)
            else:
                owners.add(nid)
        # A selected node's exclusive inline Resolver goes with it; No error stays.
        while keep and keep[0].get('target_node_id') in owners - {node_id}:
            handler = before[keep[0]['target_node_id']]
            keep = [c for c in handler.get('connections', {}).get('outputs', [])
                    if c.get('source_port', 'default') == MUX_DEFAULT_PORT][:1]
        kept_heads = [c['target_node_id'] for c in keep]
        heads = []
        for owner in owners:
            for c in before[owner].get('connections', {}).get('outputs', []):
                if owner == node_id and c in keep:
                    continue
                if c.get('target_node_id') in kept_heads or c.get('target_node_id') in owners:
                    continue
                if owner != node_id and c.get('source_port', 'default') == MUX_DEFAULT_PORT:
                    continue
                if root['type'] in (MERGE_NODE_TYPE, BRANCH_END_NODE_TYPE) and owner == node_id:
                    continue
                heads.append(c.get('target_node_id'))
        kept_beacons, seen, stack = set(), set(), list(kept_heads)
        if root['type'] in (BRANCH_NODE_TYPE, 'conditional_node'):
            while stack:
                nid = stack.pop()
                if nid in seen or nid not in before:
                    continue
                seen.add(nid)
                if before[nid].get('type') == BRANCH_END_NODE_TYPE:
                    kept_beacons.add(nid)
                elif not self._is_branch_prune_terminal(before[nid]):
                    stack.extend(c.get('target_node_id') for c in before[nid].get('connections', {}).get('outputs', []))
        removed = set(deletion_members(self.workflow_map, heads, owners, kept_heads, self._is_branch_prune_terminal, kept_beacons))
        removed.update(owners - {node_id})
        after = {nid: deepcopy(n) for nid, n in before.items() if nid not in removed}
        edges = {e for e in self._edges(after) if e[0] != node_id}
        reset = set()
        if root['type'] == MERGE_NODE_TYPE:
            reset = {c['source_node_id'] for c in root['connections']['inputs']
                     if (before.get(c['source_node_id']) or {}).get('type') == BRANCH_END_NODE_TYPE}
            edges = {e for e in edges if not (e[2] == node_id and e[0] in reset)}
        reset.update(kept_beacons)
        metadata = self._metadata_for_node(root)
        after[node_id].update(type=TOMBSTONE_NODE_TYPE, alias=DELETED_NODE_ALIAS,
                              config=tombstone_config_from_metadata(metadata))
        self._wire_graph(after, edges, removed=removed)
        self._clean_beacons(before, after, removed | {node_id}, reset)
        self._archive_nodes(before, removed)
        record = self._record('delete', node_id, before, after, keep=deepcopy(keep), kept_port=kept_port)
        after[node_id]['config']['delete_group'] = record
        return self._plan('delete', node_id, after, removed=sorted(removed), keep=keep,
                          record=record, shared_handlers=shared_handlers)

    def _group_for(self, node_id):
        node = self.workflow_map.get_node_data(node_id) or {}
        config = node.get('config') or {}
        record = config.get('delete_group') or config.get('delete_recovery') or self.placeholder_metadata(node_id).get('delete_group')
        self._check_record(record)
        return deepcopy(record)

    @staticmethod
    def _without_recovery(node):
        result = deepcopy(node)
        if result:
            config = result.get('config', {})
            config.pop('delete_group', None)
            config.pop('delete_recovery', None)
        return result

    def _restore_record(self, record, current, subset=None):
        """Three-way restore: only undo our fields/edges; newer work wins."""
        self._check_record(record)
        nodes = deepcopy(current)
        before, after = record['before'], record['after']
        conflicts = []
        restored, blocked = set(), set()
        allowed = set(before) if subset is None else set(subset)
        for nid in sorted(allowed):
            old, expected = before.get(nid), after.get(nid)
            if old is None:
                continue
            now = self._without_recovery(nodes.get(nid))
            if not self.factory.is_valid_node_type(str(old.get('type') or '')):
                conflicts.append(f"{old.get('alias') or nid}: its node type is unavailable")
                blocked.add(nid)
                continue
            if expected is None:
                if now is None:
                    nodes[nid] = {**deepcopy(old), 'connections': {'inputs': [], 'outputs': []}}
                    restored.add(nid)
                elif nid not in record.get('restored', []):
                    conflicts.append(f"{old.get('alias') or nid}: its id is now in use")
                    blocked.add(nid)
                continue
            if now is None:
                conflicts.append(f"{old.get('alias') or nid}: it no longer exists")
                continue
            for key in old.keys() | expected.keys():
                if key == 'connections' or old.get(key) == expected.get(key):
                    continue
                if key == 'config' and old.get('type') == expected.get('type'):
                    config = nodes[nid].setdefault('config', {})
                    for field in (old.get('config') or {}).keys() | (expected.get('config') or {}).keys():
                        wanted = old.get('config', {}).get(field)
                        baseline = expected.get('config', {}).get(field)
                        if wanted == baseline or config.get(field) == wanted:
                            continue
                        if config.get(field) == baseline:
                            if field in old.get('config', {}):
                                config[field] = deepcopy(wanted)
                            else:
                                config.pop(field, None)
                        else:
                            conflicts.append(f"{old.get('alias') or nid}: {field} changed")
                elif now.get(key) == expected.get(key) or now.get(key) == old.get(key):
                    if key in old:
                        nodes[nid][key] = deepcopy(old[key])
                    else:
                        nodes[nid].pop(key, None)
                else:
                    conflicts.append(f"{old.get('alias') or nid}: {key} changed")
        edges = self._edges(current)
        old_edges, new_edges = self._edges(before), self._edges(after)
        for edge in new_edges - old_edges:
            if subset is None:
                edges.discard(edge)
        original_members = {nid for nid in before if after.get(nid) is None} | {record['root']}
        desired = (old_edges - new_edges) | {e for e in old_edges if e[0] in original_members or e[2] in original_members}
        if subset is not None:
            desired = {e for e in desired if (e[0] in allowed or e[2] in allowed)
                       and record['root'] != e[0]}
        for edge in sorted(desired, key=lambda edge: tuple(str(value) for value in edge)):
            source, port, target, slot = edge
            if edge in edges:
                continue
            problem = ''
            if source in blocked or target in blocked:
                problem = 'its saved node id is in use'
            elif source not in nodes or target not in nodes:
                problem = 'a node is unavailable'
            elif not self._declares_output_port(nodes[source], port) or not self._declares_input_port(nodes[target], slot):
                problem = 'a port is unavailable'
            elif any(e[0] == source and e[1] == port and e != edge for e in edges) and not (
                    nodes[source].get('type') == BRANCH_END_NODE_TYPE
                    and all(e in old_edges for e in edges if e[0] == source and e[1] == port)):
                # A newly inserted Resolver feeding this root keeps its input.
                incoming = [e[0] for e in edges if e[2] == target]
                if target == record['root'] and any(
                        any(e[0] == source and e[2] == parent for e in edges) for parent in incoming):
                    continue
                problem = 'its output changed'
            elif nodes[target].get('type') == MERGE_NODE_TYPE and any(e[2:] == (target, slot) for e in edges):
                problem = 'its Merge input changed'
            if problem:
                conflicts.append(f"{(before.get(source) or nodes.get(source) or {}).get('alias') or source}: {problem}")
            else:
                edges.add(edge)
        # Check affected retained wires, while preserving unrelated draft diagnostics.
        checked_edges = set()
        for edge in edges:
            source, port, target, slot = edge
            if source not in allowed and target not in allowed:
                checked_edges.add(edge)
            elif source in nodes and target in nodes and self._declares_output_port(nodes[source], port) and self._declares_input_port(nodes[target], slot):
                checked_edges.add(edge)
            else:
                conflicts.append(f'{source}: a retained connection has an unavailable node or port')
        edges = checked_edges
        self._wire_graph(nodes, edges, preferred=before)
        return nodes, list(dict.fromkeys(conflicts)), restored

    def plan_restore(self, node_id):
        record = self._group_for(node_id)
        nodes, conflicts, restored = self._restore_record(record, self._graph())
        # A retry must recognize nodes restored by the previous partial undo.
        # Keep their committed baseline so later edits still win three-way.
        for restored_id in restored:
            record['after'][restored_id] = deepcopy(nodes[restored_id])
        config = nodes[node_id].setdefault('config', {})
        config.pop('delete_group', None)
        config.pop('delete_recovery', None)
        if conflicts:
            config['delete_recovery'] = record
        return self._plan('restore', node_id, nodes, conflicts=conflicts,
                          preferred_port=record.get('kept_port'), editor_state=record.get('editor_state', {}))

    def plan_replace_group(self, node_id, new_type):
        if not self.factory.is_valid_node_type(new_type) or new_type == START_NODE_TYPE:
            raise ValueError('Pick a valid replacement other than Start.')
        record = self._group_for(node_id)
        # Finalization preflights the stored route, without discovering nodes.
        self.plan_remove_group(node_id)
        nodes = self._graph()
        node = nodes[node_id]
        node.update(type=new_type, alias=self.factory.get_default_alias(new_type) or new_type,
                    config=self.factory.create_config_template(new_type) or {})
        edges = {e for e in self._edges(nodes) if e[0] != node_id}
        ports = self.factory.node_output_ports(node)
        if ports and record.get('keep'):
            out = record['keep'][0]
            edges.add((node_id, ports[0], out['target_node_id'], out.get('target_port', 'input')))
        self._wire_graph(nodes, edges)
        return self._plan('replace', node_id, nodes)

    def plan_remove_group(self, node_id):
        record = self._group_for(node_id)
        nodes = self._graph()
        root = nodes[node_id]
        if root.get('type') != TOMBSTONE_NODE_TYPE and not self.is_placeholder(node_id):
            raise ValueError('Restore this node or discard its saved recovery data.')
        incoming = list(root.get('connections', {}).get('inputs', []))
        keep = record.get('keep') or []
        edges = {e for e in self._edges(nodes) if node_id not in (e[0], e[2])}
        nodes.pop(node_id)
        conflicts = []
        for c in incoming:
            for out in keep[:1]:
                edge = (c['source_node_id'], c.get('source_port', 'default'),
                        out['target_node_id'], out.get('target_port', 'input'))
                source, port, target, slot = edge
                if source not in nodes or target not in nodes:
                    raise ValueError('The kept route changed. Restore the group to repair it.')
                if not self._declares_output_port(nodes[source], port) or not self._declares_input_port(nodes[target], slot):
                    raise ValueError('The kept route changed. Restore the group to repair it.')
                if any(e[0] == source and e[1] == port for e in edges):
                    raise ValueError('The parent output changed. Restore the group to repair it.')
                if nodes[target].get('type') == MERGE_NODE_TYPE and any(e[2:] == (target, slot) for e in edges):
                    raise ValueError('The Merge input changed. Restore the group to repair it.')
                edges.add(edge)
        self._wire_graph(nodes, edges)
        return self._plan('remove', node_id, nodes, removed=[node_id], conflicts=conflicts)

    def saved_paths(self, node_id):
        data = (self.workflow_map.get_node_data(node_id) or {}).get('config', {}).get('branch_recovery')
        if not data:
            return []
        self._check_record(data)
        return deepcopy(data.get('entries', []))

    def plan_branch_count(self, node_id, result, kept_ports):
        import uuid
        from frontend.error_mux_ui import deletion_members
        before = self._graph()
        root = before[node_id]
        ports = [p for p in self.factory.node_output_ports(root) if p != ERROR_PORT]
        config = deepcopy(result['config'])
        new_ports = [p for p in self.factory.output_ports_for(BRANCH_NODE_TYPE, config) if p != ERROR_PORT]
        selected = [p for p in ports if p in kept_ports]
        if len(selected) != len(new_ports) or len(kept_ports) != len(selected) or len(new_ports) >= len(ports):
            raise ValueError('Pick exactly the new number of paths.')
        outputs = root['connections']['outputs']
        kept_heads = [c['target_node_id'] for c in outputs if c.get('source_port') in selected]
        heads = [c['target_node_id'] for c in outputs if c.get('source_port') not in selected and c.get('source_port') != ERROR_PORT]
        removed = set(deletion_members(self.workflow_map, heads, {node_id}, kept_heads, self._is_branch_prune_terminal))
        after = {nid: deepcopy(n) for nid, n in before.items() if nid not in removed}
        remap = dict(zip(selected, new_ports))
        sources = root['config'].get('branch_payload_sources') or {}
        drafts = result.get('path_drafts') or {}
        draft_sources = {port: drafts.get(port, {}).get('source',
            (result['config'].get('branch_payload_sources') or {}).get(port, sources.get(port, 'dead_drop:input')))
            for port in ports}
        draft_labels = {port: drafts.get(port, {}).get('label',
            result['config'].get(f'{port}_label', root['config'].get(f'{port}_label', port))) for port in ports}
        config['branch_payload_sources'] = {new: deepcopy(draft_sources[old]) for old, new in remap.items()}
        for old, new in remap.items():
            config[f'{new}_label'] = draft_labels[old]
        after[node_id]['config'] = config
        after[node_id]['alias'] = str(result.get('alias', root.get('alias', ''))).strip()
        edges = set()
        for source, port, target, slot in self._edges(before):
            if source == node_id and port != ERROR_PORT:
                if port not in remap:
                    continue
                port = remap[port]
            edges.add((source, port, target, slot))
        self._wire_graph(after, edges, removed=removed)
        self._clean_beacons(before, after, removed)
        mapping = {f'{node_id}:{old}': f'{node_id}:{new}' for old, new in remap.items()}
        dropped = {f'{node_id}:{p}' for p in ports if p not in selected}
        self._merge_keys(after, mapping, dropped)
        self._archive_nodes(before, removed)
        record = self._record('reduction', node_id, before, after)
        archive = deepcopy(root['config'].get('branch_recovery') or {'version': 1, 'entries': [], 'groups': {}})
        self._check_record(archive)
        for port in ports:
            if port in selected:
                continue
            head = next((deepcopy(c) for c in outputs if c.get('source_port') == port), None)
            members, seen, stack = set(), set(), [head['target_node_id']] if head else []
            while stack:
                nid = stack.pop()
                if nid in seen or nid not in before:
                    continue
                seen.add(nid)
                if nid in removed:
                    members.add(nid)
                if self._is_branch_prune_terminal(before[nid]):
                    continue
                stack.extend(c.get('target_node_id') for c in before[nid].get('connections', {}).get('outputs', []))
            archive['entries'].append({'id': uuid.uuid4().hex, 'group': record['id'], 'port': port,
                'label': str(draft_labels[port]),
                'payload_source': deepcopy(draft_sources[port]), 'head': head, 'members': sorted(members)})
        archive['groups'][record['id']] = record
        after[node_id]['config']['branch_recovery'] = archive
        return self._plan('reduction', node_id, after, removed=sorted(removed), record=record, port_mapping=remap)

    def plan_recover_paths(self, node_id, result, selected_ids):
        before = self._graph()
        root = before[node_id]
        config = deepcopy(result['config'])
        old_ports = self.factory.node_output_ports(root)
        new_ports = [p for p in self.factory.output_ports_for(BRANCH_NODE_TYPE, config) if p not in old_ports and p != ERROR_PORT]
        archive = deepcopy(root['config'].get('branch_recovery') or {'version': 1, 'entries': [], 'groups': {}})
        self._check_record(archive)
        selected = [e for e in archive['entries'] if e['id'] in selected_ids]
        if len(selected) != len(selected_ids) or len(selected) > len(new_ports):
            raise ValueError('Pick no more than the number of new paths.')
        nodes = deepcopy(before)
        nodes[node_id]['config'] = config
        nodes[node_id]['alias'] = str(result.get('alias', root.get('alias', ''))).strip()
        conflicts, consumed = [], set()
        for entry, port in zip(selected, new_ports):
            record = archive['groups'][entry['group']]
            self._check_record(record)
            nodes, problems, restored = self._restore_record(record, nodes, subset=entry['members'])
            conflicts.extend(problems)
            record['restored'] = sorted(set(record.get('restored', [])) | restored)
            head = entry.get('head')
            if head and (head['target_node_id'] not in nodes or (head['target_node_id'] in entry['members']
                    and head['target_node_id'] not in restored and head['target_node_id'] not in record.get('restored', []))):
                conflicts.append(f"{entry['label']}: its first node is unavailable")
                continue
            if head:
                edge = (node_id, port, head['target_node_id'], head.get('target_port', 'input'))
                if not self._declares_input_port(nodes[edge[2]], edge[3]):
                    conflicts.append(f"{entry['label']}: its input is unavailable")
                    continue
                edges = self._edges(nodes)
                edges.add(edge)
                self._wire_graph(nodes, edges)
            nodes[node_id]['config'][f'{port}_label'] = entry['label']
            nodes[node_id]['config'].setdefault('branch_payload_sources', {})[port] = entry['payload_source']
            old_key, new_key = f"{node_id}:{entry['port']}", f'{node_id}:{port}'
            for merge_id, original in record['before'].items():
                if not original or original.get('type') != MERGE_NODE_TYPE or merge_id not in nodes:
                    continue
                old_config = original.get('config', {})
                live_config = nodes[merge_id].setdefault('config', {})
                if old_key in old_config.get('branches_to_close', []):
                    values = live_config.setdefault('branches_to_close', [])
                    if new_key not in values:
                        values.append(new_key)
                for field in ('carry_forward_branch_id', 'selected_branch_id'):
                    if old_config.get(field) == old_key and not live_config.get(field):
                        live_config[field] = new_key
                        if not live_config.get('selected_input_port'):
                            live_config['selected_input_port'] = old_config.get('selected_input_port', '')

            consumed.add(entry['id'])
            if problems:
                # The path head has returned. Keep only its unresolved work as
                # a repair record, never offer the same executable path again.
                pending = deepcopy(record)
                members = set(entry['members'])
                for nid in pending['before'].keys() | pending['after'].keys():
                    if nid not in members:
                        pending['before'][nid] = deepcopy(nodes.get(nid))
                        pending['after'][nid] = deepcopy(nodes.get(nid))
                for graph in (pending['before'], pending['after']):
                    if graph.get(node_id):
                        for field in ('branch_recovery', 'delete_recovery', 'delete_group'):
                            graph[node_id].get('config', {}).pop(field, None)
                if head and pending['before'].get(head['target_node_id']):
                    for connection in pending['before'][head['target_node_id']]['connections']['inputs']:
                        if connection.get('source_node_id') == node_id:
                            connection['source_port'] = port
                previous = nodes[node_id]['config'].get('delete_recovery')
                if previous:
                    self._check_record(previous)
                    for nid, original in previous['before'].items():
                        if nid != node_id and original != previous['after'].get(nid):
                            pending['before'][nid] = deepcopy(original)
                            pending['after'][nid] = deepcopy(previous['after'].get(nid))
                    pending['restored'] = sorted(set(pending.get('restored', [])) | set(previous.get('restored', [])))
                nodes[node_id]['config']['delete_recovery'] = pending
        archive['entries'] = [e for e in archive['entries'] if e['id'] not in consumed]
        archive['groups'] = {key: value for key, value in archive['groups'].items()
                             if any(e['group'] == key for e in archive['entries'])}
        if archive['entries']:
            nodes[node_id]['config']['branch_recovery'] = archive
        else:
            nodes[node_id]['config'].pop('branch_recovery', None)
        return self._plan('recover', node_id, nodes, conflicts=list(dict.fromkeys(conflicts)))

    def _mark_dirty(self) -> None:
        mark_dirty = getattr(self.workflow_map, "_mark_dirty", None)
        if callable(mark_dirty):
            mark_dirty()

    @property
    def _deleted_nodes(self) -> Dict[str, Dict[str, Any]]:
        if self._state_owner is None:
            return self._local_deleted_nodes
        state = getattr(self._state_owner, DELETED_NODE_STATE_ATTR, None)
        if not isinstance(state, dict):
            state = {}
            setattr(self._state_owner, DELETED_NODE_STATE_ATTR, state)
        return state

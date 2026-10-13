"""Rows for the node config Connections tab (UX5).

Each row describes one connection in plain words: the node at the other end,
the port names on both ends and what flows along it (a payload's name,
"No payload" when the source publishes nothing on that port, or the error
details an ``error`` port carries when the node fails). Vault reads are
listed separately, one row per key and writer, using the shared read/write
model in ``backend.vault_declarations``. A row with a ``target`` jumps to
that node's editor; ``key`` identifies the connection across refreshes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.node_errors import ERROR_PORT
from backend.vault_declarations import active_vault_reads, active_vault_writes
from frontend.node_io_display import (
    input_display_name,
    metadata_for_type,
    node_label,
    output_display_name,
    trace_transient_producer,
)

NO_PAYLOAD = "No payload"
ERROR_PAYLOAD = "Error details on failure"
NO_WRITER = "no writer found"
UNPICKED_NOTE = "branch unpicked: removed on save"
_NO_INCOMING = "No connected incoming payload"


def _publishes_default(node: Dict[str, Any]) -> bool:
    """Whether the node puts its result on ``default``. The Publish toggle
    only controls that port; other ports always carry their data."""
    config = node.get("config") or {}
    return config.get("transient_output", True) is not False or bool(config.get("dead_drop_passthrough"))


def payload_text(workflow_map, factory, source_id: str, source_port: str) -> str:
    """What flows out of ``source_id``'s ``source_port``."""
    source = workflow_map.get_node_data(source_id) or {}
    if not source:
        return NO_PAYLOAD
    if source_port == ERROR_PORT:
        # The supervisor publishes a structured error here when the node
        # fails, whatever the normal-output toggle says.
        return ERROR_PAYLOAD
    if source_port == "default" and not _publishes_default(source):
        return NO_PAYLOAD
    producer = trace_transient_producer(workflow_map, factory, source_id, source_port)
    name = str(producer.get("name") or "").strip()
    return name if name and name != _NO_INCOMING else NO_PAYLOAD


def _node_vault(factory, node: Dict[str, Any], reads: bool) -> list[str]:
    node_type = str(node.get("type") or "")
    config = node.get("config") or {}
    metadata = metadata_for_type(factory, node_type) or {}
    if reads:
        return active_vault_reads(node_type, config, metadata)
    return active_vault_writes(node_type, config, metadata)


def vault_writers(workflow_map, factory) -> Dict[str, list[str]]:
    """Vault key -> ids of the nodes that write it (each node once)."""
    writers: Dict[str, list[str]] = {}
    for node_id, node in workflow_map.get_all_node_data().items():
        for key in _node_vault(factory, node, reads=False):
            writers.setdefault(key, []).append(node_id)
    return writers


def connection_rows(
    workflow_map,
    factory,
    node_id: str,
    mux_ports: Optional[set[str]] = None,
) -> Dict[str, list[Dict[str, Any]]]:
    """Incoming, outgoing and Vault-read rows for one node.

    ``mux_ports`` (Error Mux only) are the ports picked on screen right now;
    an outgoing connection from any other port is marked as removed on save.
    """
    node = workflow_map.get_node_data(node_id) or {}
    connections = node.get("connections") or {}
    incoming = []
    for conn in connections.get("inputs") or []:
        source_id = str(conn.get("source_node_id") or "")
        source = workflow_map.get_node_data(source_id) or {}
        source_port = str(conn.get("source_port") or "default")
        target_port = str(conn.get("target_port") or "input")
        incoming.append({
            "key": ("in", source_id, source_port, target_port),
            "target": source_id if source else None,
            "text": (f"{node_label(source_id, source)}: "
                     f"{output_display_name(factory, source, source_port)} → "
                     f"{input_display_name(factory, node, target_port)}"
                     f" ({payload_text(workflow_map, factory, source_id, source_port)})"),
        })
    outgoing = []
    for conn in connections.get("outputs") or []:
        target_id = str(conn.get("target_node_id") or "")
        target = workflow_map.get_node_data(target_id) or {}
        source_port = str(conn.get("source_port") or "default")
        target_port = str(conn.get("target_port") or "input")
        note = ""
        if mux_ports is not None and source_port not in mux_ports:
            note = f"  ({UNPICKED_NOTE})"
        outgoing.append({
            "key": ("out", source_port, target_id, target_port),
            "target": target_id if target else None,
            "text": (f"{output_display_name(factory, node, source_port)} → "
                     f"{node_label(target_id, target)}: "
                     f"{input_display_name(factory, target, target_port)}"
                     f" ({payload_text(workflow_map, factory, node_id, source_port)}){note}"),
        })
    vault = []
    keys = _node_vault(factory, node, reads=True)
    writers_by_key = vault_writers(workflow_map, factory) if keys else {}
    for key in keys:
        writers = [w for w in writers_by_key.get(key, []) if w != node_id]
        if not writers:
            # Not proof that nothing writes it: only declared writers are known.
            vault.append({"key": ("vault", key, ""), "target": None,
                          "text": f"{key}: {NO_WRITER}"})
        for writer in writers:
            writer_node = workflow_map.get_node_data(writer) or {}
            vault.append({"key": ("vault", key, writer), "target": writer,
                          "text": f"{key}: written by {node_label(writer, writer_node)}"})
    return {"incoming": incoming, "outgoing": outgoing, "vault": vault}

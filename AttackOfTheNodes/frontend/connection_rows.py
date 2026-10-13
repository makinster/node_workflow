"""Rows for the node config Connections tab (UX5).

Each row describes one connection in plain words: the node at the other end,
the port names on both ends and what flows along it (a payload's name, or
"No payload" when the source publishes nothing). Vault reads are listed
separately, one row per key and writer. A row with a ``target`` jumps to
that node's editor.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from frontend.node_io_display import (
    input_display_name,
    memory_registry,
    node_label,
    normalize_membank_inputs,
    output_display_name,
    trace_transient_producer,
)

NO_PAYLOAD = "No payload"
UNPICKED_NOTE = "branch unpicked: removed on save"
_NO_INCOMING = "No connected incoming payload"


def _publishes(node: Dict[str, Any]) -> bool:
    """Whether the node puts a payload on its outputs (the editor's rule)."""
    config = node.get("config") or {}
    return config.get("transient_output", True) is not False or bool(config.get("dead_drop_passthrough"))


def payload_text(workflow_map, factory, source_id: str, source_port: str) -> str:
    """What flows out of ``source_id``'s ``source_port``."""
    source = workflow_map.get_node_data(source_id) or {}
    if not source or not _publishes(source):
        return NO_PAYLOAD
    producer = trace_transient_producer(workflow_map, factory, source_id, source_port)
    name = str(producer.get("name") or "").strip()
    return name if name and name != _NO_INCOMING else NO_PAYLOAD


def vault_read_keys(config: Dict[str, Any]) -> list[str]:
    """Vault keys the node reads: declared reads and inputs sourced from the Vault."""
    keys = list(normalize_membank_inputs(config))
    for field, value in config.items():
        if not field.endswith("_source") or value != "Vault":
            continue
        key = str(config.get(f"{field[:-len('_source')]}_vault_key") or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


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
            "target": target_id if target else None,
            "text": (f"{output_display_name(factory, node, source_port)} → "
                     f"{node_label(target_id, target)}: "
                     f"{input_display_name(factory, target, target_port)}"
                     f" ({payload_text(workflow_map, factory, node_id, source_port)}){note}"),
        })
    vault = []
    keys = vault_read_keys(node.get("config") or {})
    registry = memory_registry(workflow_map) if keys else {}
    for key in keys:
        writers = [w for w in (registry.get(key) or {}).get("writers", []) if w != node_id]
        if not writers:
            vault.append({"target": None, "text": f"{key}: no node writes it"})
        for writer in writers:
            writer_node = workflow_map.get_node_data(writer) or {}
            vault.append({"target": writer, "text": f"{key}: written by {node_label(writer, writer_node)}"})
    return {"incoming": incoming, "outgoing": outgoing, "vault": vault}

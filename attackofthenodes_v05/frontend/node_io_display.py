"""Frontend helpers for explaining node inputs and outputs."""

from __future__ import annotations

from typing import Any, Dict, Optional


def normalize_membank_outputs(config: Dict[str, Any]) -> list[Dict[str, str]]:
    """Return valid membank output declarations from node config."""
    outputs = config.get("membank_outputs") or []
    if not isinstance(outputs, list):
        return []
    normalized: list[Dict[str, str]] = []
    for entry in outputs:
        if not isinstance(entry, dict):
            continue
        output_id = str(entry.get("output") or entry.get("id") or "").strip()
        if not output_id:
            continue
        normalized.append(
            {
                "id": output_id,
                "output": output_id,
                "description": str(entry.get("description") or "").strip(),
            }
        )
    return normalized


def normalize_membank_inputs(config: Dict[str, Any]) -> list[str]:
    """Return membank input ids from node config."""
    inputs = config.get("membank_inputs") or []
    if not isinstance(inputs, list):
        return []
    normalized: list[str] = []
    for entry in inputs:
        value = ""
        if isinstance(entry, str):
            value = entry
        elif isinstance(entry, dict):
            value = str(entry.get("source_id") or entry.get("id") or "")
        value = value.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def metadata_for_type(factory, node_type: str) -> Optional[Dict[str, Any]]:
    """Return factory metadata for a node type."""
    for item in factory.get_node_types_metadata():
        if item["type"] == node_type:
            return item
    return None


def node_label(node_id: str, node: Dict[str, Any]) -> str:
    """Return the editor-facing node label."""
    name = node.get("alias") or node.get("type") or node_id
    return f"{name} ({node_id})"


def node_display_name(node_id: str, node: Dict[str, Any]) -> str:
    """Return the friendly node name without generated ids."""
    return str(node.get("alias") or node.get("type") or node_id)


def output_display_name(factory, node: Dict[str, Any], port: str) -> str:
    """Return a friendly name for a node output port."""
    config = node.get("config") or {}
    configured = str(config.get(f"{port}_label") or "").strip()
    if configured:
        return configured
    if port == "default":
        return "Output"
    return port.replace("_", " ").title()


def input_display_name(port: str) -> str:
    """Return a friendly name for an input port."""
    if port == "input":
        return "Input"
    if port == "default":
        return "Input"
    return port.replace("_", " ").title()


def memory_display_text(output_id: str, description: str = "") -> str:
    """Return compact memory key display text."""
    output_id = str(output_id).strip()
    description = str(description or "").strip()
    if output_id and description:
        return f"{output_id} - {description}"
    return output_id or "unnamed"


def memory_registry(workflow_map) -> Dict[str, Dict[str, Any]]:
    """Scan workflow nodes for declared memory outputs."""
    registry: Dict[str, Dict[str, Any]] = {}
    for node_id, node in workflow_map.get_all_node_data().items():
        for output in normalize_membank_outputs(node.get("config") or {}):
            entry = registry.setdefault(
                output["id"],
                {
                    "id": output["id"],
                    "description": output["description"],
                    "writers": [],
                },
            )
            if output["description"] and not entry.get("description"):
                entry["description"] = output["description"]
            entry["writers"].append(node_id)
    return registry


def is_pass_through_node(factory, node: Dict[str, Any]) -> bool:
    """Return whether this node should be treated as display pass-through."""
    metadata = metadata_for_type(factory, node.get("type", ""))
    if metadata and (metadata.get("ui_hints") or {}).get("pass_through"):
        return True
    config = node.get("config") or {}
    return config.get("pass_through") is True


def transient_output_details(
    factory,
    node: Dict[str, Any],
    port: str,
) -> Dict[str, str]:
    """Return friendly output name and optional description for a node port."""
    for output in normalize_membank_outputs(node.get("config") or {}):
        output_id = output.get("id") or output.get("output") or ""
        if output_id == port:
            return {
                "name": output_id,
                "description": output.get("description") or "No output description configured.",
            }
    outputs = normalize_membank_outputs(node.get("config") or {})
    if len(outputs) == 1:
        output = outputs[0]
        return {
            "name": output.get("id") or output.get("output") or output_display_name(factory, node, port),
            "description": output.get("description") or "No output description configured.",
        }
    return {
        "name": output_display_name(factory, node, port),
        "description": "No output description configured.",
    }


def trace_transient_producer(
    workflow_map,
    factory,
    source_node_id: str,
    source_port: str,
) -> Dict[str, Any]:
    """Trace pass-through outputs back to the node that produced the data."""
    current_id = source_node_id
    current_port = source_port or "default"
    visited: set[str] = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        node = workflow_map.get_node_data(current_id) or {}
        if not node or not is_pass_through_node(factory, node):
            break
        inputs = node.get("connections", {}).get("inputs", [])
        if not inputs:
            break
        upstream = inputs[0]
        next_id = str(upstream.get("source_node_id") or "")
        next_port = str(upstream.get("source_port") or "default")
        if not next_id:
            break
        current_id = next_id
        current_port = next_port

    node = workflow_map.get_node_data(current_id) or {}
    details = transient_output_details(factory, node, current_port)
    return {
        "node_id": current_id,
        "node": node,
        "port": current_port,
        "name": details["name"],
        "description": details["description"],
    }

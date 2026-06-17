"""Frontend helpers for explaining node inputs and outputs."""

from __future__ import annotations

from typing import Any, Dict, Optional

from frontend.node_types import (
    BRANCH_END_NODE_TYPE,
    BRANCH_NODE_TYPE,
    TOMBSTONE_NODE_TYPE,
)


# Plain-language fallback shown when an output port has no configured
# description, e.g. "Output: not configured yet" in the editor quick view.
OUTPUT_NOT_CONFIGURED = "not configured yet"


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
    name = node_display_name(node_id, node)
    return f"{name} ({node_id})"


def node_display_name(node_id: str, node: Dict[str, Any]) -> str:
    """Return the friendly node name without generated ids."""
    if node.get("type") == BRANCH_END_NODE_TYPE:
        alias = str(node.get("alias") or "").strip()
        if not alias or alias in {"Branch End", BRANCH_END_NODE_TYPE}:
            return "Merge Beacon"
        return alias
    if node.get("type") == TOMBSTONE_NODE_TYPE:
        config = node.get("config") or {}
        original = (
            config.get("original_alias")
            or config.get("original_display_name")
            or config.get("original_type")
            or "node"
        )
        return f"Deleted: {original}"
    return str(node.get("alias") or node.get("type") or node_id)


def _port_metadata(
    factory,
    node: Dict[str, Any],
    port: str,
    direction: str,
) -> Dict[str, str]:
    metadata = metadata_for_type(factory, node.get("type", ""))
    if not metadata:
        return {}
    key = "output_port_metadata" if direction == "output" else "input_port_metadata"
    value = (metadata.get(key) or {}).get(port) or {}
    return value if isinstance(value, dict) else {}


def normalize_transient_outputs(config: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Return transient output display overrides keyed by port."""
    outputs = config.get("transient_outputs") or {}
    normalized: Dict[str, Dict[str, str]] = {}
    if isinstance(outputs, dict):
        iterable = [
            {"port": port, **value} if isinstance(value, dict) else {"port": port, "name": value}
            for port, value in outputs.items()
        ]
    elif isinstance(outputs, list):
        iterable = outputs
    else:
        iterable = []
    for entry in iterable:
        if not isinstance(entry, dict):
            continue
        port = str(entry.get("port") or "").strip()
        if not port:
            continue
        normalized[port] = {
            "port": port,
            "name": str(entry.get("name") or "").strip(),
            "description": str(entry.get("description") or "").strip(),
        }
    return normalized


def output_display_name(factory, node: Dict[str, Any], port: str) -> str:
    """Return a friendly name for a node output port."""
    config = node.get("config") or {}
    override = normalize_transient_outputs(config).get(port) or {}
    if override.get("name"):
        return override["name"]
    configured = str(config.get(f"{port}_label") or "").strip()
    if configured:
        return configured
    metadata = _port_metadata(factory, node, port, "output")
    if metadata.get("name"):
        return str(metadata["name"])
    if port == "default":
        return "Output"
    return port.replace("_", " ").title()


def input_display_name(factory, node: Dict[str, Any], port: str) -> str:
    """Return a friendly name for an input port."""
    metadata = _port_metadata(factory, node, port, "input")
    if metadata.get("name"):
        return str(metadata["name"])
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


def output_display_description(factory, node: Dict[str, Any], port: str) -> str:
    """Return friendly output description for a node output port."""
    override = normalize_transient_outputs(node.get("config") or {}).get(port) or {}
    if override.get("description"):
        return override["description"]
    metadata = _port_metadata(factory, node, port, "output")
    if metadata.get("description"):
        return str(metadata["description"])
    return OUTPUT_NOT_CONFIGURED


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
                "description": output.get("description") or OUTPUT_NOT_CONFIGURED,
            }
    outputs = normalize_membank_outputs(node.get("config") or {})
    if len(outputs) == 1:
        output = outputs[0]
        return {
            "name": output.get("id") or output.get("output") or output_display_name(factory, node, port),
            "description": output.get("description") or OUTPUT_NOT_CONFIGURED,
        }
    return {
        "name": output_display_name(factory, node, port),
        "description": output_display_description(factory, node, port),
    }


def trace_transient_producer(
    workflow_map,
    factory,
    source_node_id: str,
    source_port: str,
) -> Dict[str, Any]:
    """Trace pass-through outputs back to the node that produced the data."""
    return _trace_transient_producer(
        workflow_map,
        factory,
        source_node_id,
        source_port,
        set(),
    )


def _trace_transient_producer(
    workflow_map,
    factory,
    source_node_id: str,
    source_port: str,
    visited: set[tuple[str, str]],
) -> Dict[str, Any]:
    current_id = source_node_id
    current_port = source_port or "default"

    while current_id and (current_id, current_port) not in visited:
        visited.add((current_id, current_port))
        node = workflow_map.get_node_data(current_id) or {}
        if node.get("type") == BRANCH_NODE_TYPE and current_port != "input":
            branch_result = _trace_branch_payload_producer(
                workflow_map,
                factory,
                current_id,
                node,
                current_port,
                visited,
            )
            if branch_result:
                return branch_result
        if not node or not is_pass_through_node(factory, node):
            break
        upstream = _first_input_connection(node)
        if not upstream:
            break
        next_id = str(upstream.get("source_node_id") or "")
        next_port = str(upstream.get("source_port") or "default")
        if not next_id:
            break
        upstream_result = _trace_transient_producer(
            workflow_map,
            factory,
            next_id,
            next_port,
            visited,
        )
        upstream_result["chain_node_ids"] = _append_chain_node(
            upstream_result.get("chain_node_ids"),
            current_id,
        )
        return upstream_result

    node = workflow_map.get_node_data(current_id) or {}
    details = transient_output_details(factory, node, current_port)
    return {
        "node_id": current_id,
        "node": node,
        "port": current_port,
        "name": details["name"],
        "description": details["description"],
        "chain_node_ids": [current_id] if current_id else [],
    }


def _trace_branch_payload_producer(
    workflow_map,
    factory,
    branch_node_id: str,
    branch_node: Dict[str, Any],
    branch_port: str,
    visited: set[tuple[str, str]],
) -> Optional[Dict[str, Any]]:
    """Trace the selected seed payload for a branch output port."""
    config = branch_node.get("config") or {}
    sources = config.get("branch_payload_sources") or {}
    source = ""
    if isinstance(sources, dict):
        source = str(sources.get(branch_port) or "").strip()

    if source.startswith("vault:"):
        vault_key = source.removeprefix("vault:").strip()
        if not vault_key:
            return None
        registry = memory_registry(workflow_map)
        entry = registry.get(vault_key) or {}
        writer_id = next(
            (
                str(writer)
                for writer in entry.get("writers", [])
                if str(writer) and str(writer) != branch_node_id
            ),
            "",
        )
        writer_node = workflow_map.get_node_data(writer_id) or {}
        chain = [writer_id, branch_node_id] if writer_id else [branch_node_id]
        return {
            "node_id": writer_id or branch_node_id,
            "node": writer_node or branch_node,
            "port": vault_key,
            "name": vault_key,
            "description": str(entry.get("description") or "").strip()
            or OUTPUT_NOT_CONFIGURED,
            "chain_node_ids": chain,
        }

    upstream = _first_input_connection(branch_node, "input") or _first_input_connection(branch_node)
    if not upstream:
        details = transient_output_details(factory, branch_node, branch_port)
        return {
            "node_id": branch_node_id,
            "node": branch_node,
            "port": branch_port,
            "name": details["name"],
            "description": details["description"],
            "chain_node_ids": [branch_node_id],
        }

    upstream_id = str(upstream.get("source_node_id") or "")
    upstream_port = str(upstream.get("source_port") or "default")
    if not upstream_id:
        return None
    upstream_result = _trace_transient_producer(
        workflow_map,
        factory,
        upstream_id,
        upstream_port,
        visited,
    )
    upstream_result["chain_node_ids"] = _append_chain_node(
        upstream_result.get("chain_node_ids"),
        branch_node_id,
    )
    return upstream_result


def _first_input_connection(
    node: Dict[str, Any],
    target_port: str | None = None,
) -> Optional[Dict[str, Any]]:
    inputs = node.get("connections", {}).get("inputs", [])
    if target_port is not None:
        for conn in inputs:
            if str(conn.get("target_port") or "") == target_port:
                return conn
    return inputs[0] if inputs else None


def _append_chain_node(chain: Any, node_id: str) -> list[str]:
    node_ids = [str(item) for item in chain or [] if str(item)]
    if node_id and (not node_ids or node_ids[-1] != node_id):
        node_ids.append(node_id)
    return node_ids

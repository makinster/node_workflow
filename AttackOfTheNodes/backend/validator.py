"""
Validator for AttackOfTheNodes v0.5.

Runs static checks on a loaded workflow. Errors block execution; warnings are
informational, such as loose nodes unreachable from the start node.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from .branch_health import ENDED_UNMERGED, derive_branch_health, output_types_from_factory
from .node_factory import NodeFactory
from .workflow_map import WorkflowMap

if TYPE_CHECKING:
    from .secrets_manager import SecretsManager


def derive_input_sources(
    all_nodes: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, str]]]:
    """Derive node and membank input sources from workflow structure."""
    input_sources: Dict[str, List[Dict[str, str]]] = {}
    for node_id, data in all_nodes.items():
        sources: List[Dict[str, str]] = []
        for conn in data.get("connections", {}).get("inputs", []):
            source_id = conn.get("source_node_id")
            if source_id:
                sources.append(
                    {
                        "type": "node",
                        "source_id": source_id,
                        "port": conn.get("source_port", "default"),
                    }
                )

        config = data.get("config") or {}
        membank_inputs = config.get("membank_inputs") or []
        if isinstance(membank_inputs, list):
            for entry in membank_inputs:
                source_id = _membank_source_id(entry)
                if source_id:
                    sources.append({"type": "membank", "source_id": source_id})
        input_sources[node_id] = sources
    return input_sources


def validate_workflow(
    workflow_map: WorkflowMap,
    factory: NodeFactory,
    secrets_manager: Optional["SecretsManager"] = None,
) -> Dict[str, Any]:
    """Validate the loaded workflow structure."""
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    all_nodes = workflow_map.get_all_node_data()

    start_ids = [
        node_id for node_id, data in all_nodes.items() if data["type"] == "start_node"
    ]
    if len(start_ids) == 0:
        errors.append({"node_id": "", "message": "Workflow has no start node"})
    elif len(start_ids) > 1:
        errors.append(
            {
                "node_id": "",
                "message": f"Workflow has {len(start_ids)} start nodes; expected exactly 1",
            }
        )

    for node_id, data in all_nodes.items():
        if not factory.is_valid_node_type(data["type"]):
            errors.append(
                {"node_id": node_id, "message": f"Unknown node type: {data['type']}"}
            )

    node_ids = set(all_nodes.keys())
    for node_id, data in all_nodes.items():
        for conn in data.get("connections", {}).get("outputs", []):
            target = conn.get("target_node_id")
            if target and target not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Output connection targets missing node: {target}",
                    }
                )
        for conn in data.get("connections", {}).get("inputs", []):
            source = conn.get("source_node_id")
            if source and source not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Input connection from missing node: {source}",
                    }
                )

    # Tombstone nodes (deleted-node stubs) are always errors
    for node_id, data in all_nodes.items():
        if data.get("type") == "tombstone_node":
            cfg = data.get("config") or {}
            original = cfg.get("original_display_name") or cfg.get("original_type") or "unknown"
            in_ports = cfg.get("original_input_ports") or []
            out_ports = cfg.get("original_output_ports") or []
            port_context = ""
            if in_ports or out_ports:
                parts = []
                if in_ports:
                    parts.append(f"orphaned inputs: {', '.join(in_ports)}")
                if out_ports:
                    parts.append(f"orphaned outputs: {', '.join(out_ports)}")
                port_context = f" ({'; '.join(parts)})"
            errors.append(
                {
                    "node_id": node_id,
                    "message": (
                        f"Deleted node stub (was: {original}) — replace with a valid node type"
                        f"{port_context}"
                    ),
                }
            )

    # Port-name validity: every connection must reference a port the node type declares
    _type_meta_cache: Dict[str, Any] = {}
    for meta in factory.get_node_types_metadata():
        _type_meta_cache[meta["type"]] = meta

    for node_id, data in all_nodes.items():
        node_type = data.get("type", "")
        meta = _type_meta_cache.get(node_type)
        if meta is None:
            continue  # unknown type already flagged above
        declared_out = set(meta.get("output_ports") or [])
        declared_in = set(meta.get("input_ports") or [])
        for conn in data.get("connections", {}).get("outputs", []):
            port = conn.get("source_port", "default")
            if port not in declared_out:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"Orphaned output connection on undeclared port '{port}' "
                            f"(node type '{node_type}' has no such output)"
                        ),
                    }
                )
        for conn in data.get("connections", {}).get("inputs", []):
            port = conn.get("target_port", "default")
            if port not in declared_in:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"Orphaned input connection on undeclared port '{port}' "
                            f"(node type '{node_type}' has no such input)"
                        ),
                    }
                )

    # File-path fields: schema fields hinted with path_hint == "file".
    # An empty required path is an error; a path missing on disk is only a
    # warning because an earlier node may create the file during the run.
    for node_id, data in all_nodes.items():
        meta = _type_meta_cache.get(data.get("type", ""))
        if meta is None:
            continue
        config = data.get("config") or {}
        for field_name, field_info in (meta.get("config_schema") or {}).items():
            if field_info.get("path_hint") != "file":
                continue
            raw_path = str(config.get(field_name, "") or "").strip()
            if not raw_path:
                if field_info.get("required", False):
                    errors.append(
                        {
                            "node_id": node_id,
                            "message": f"Missing file path in field '{field_name}'",
                        }
                    )
                continue
            if not Path(raw_path).expanduser().exists():
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"File for field '{field_name}' was not found at "
                            f"validation time: {raw_path}"
                        ),
                    }
                )

    # Secret-ref fields: schema fields annotated with "secret": True.
    # An empty required key is an error; a configured key absent from the store
    # is a warning (key might be added before the run).
    # When secrets_manager is None the existence check is skipped.
    for node_id, data in all_nodes.items():
        meta = _type_meta_cache.get(data.get("type", ""))
        if meta is None:
            continue
        config = data.get("config") or {}
        for field_name, field_info in (meta.get("config_schema") or {}).items():
            if not field_info.get("secret"):
                continue
            key_name = str(config.get(field_name, "") or "").strip()
            if not key_name:
                if field_info.get("required", False):
                    errors.append(
                        {
                            "node_id": node_id,
                            "message": (
                                f"Secret key for field '{field_name}' is required but not configured"
                            ),
                        }
                    )
                continue
            if secrets_manager is not None and not secrets_manager.has_key(key_name):
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"Secret key '{key_name}' (field '{field_name}') "
                            f"is not present in the secrets store"
                        ),
                    }
                )

    declared_membank_outputs = _declared_membank_outputs(all_nodes)
    for node_id, sources in derive_input_sources(all_nodes).items():
        for source in sources:
            source_type = source.get("type")
            source_id = source.get("source_id", "")
            if source_type == "node" and source_id not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Input source missing node: {source_id}",
                    }
                )
            elif source_type == "membank" and source_id not in declared_membank_outputs:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Membank input source not declared: {source_id}",
                    }
                )

    # Typed vault: warn when a node reads a key typed "ai_session" but the writer
    # declared a different (or null) type_tag.  Error (key absent) is already above.
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        membank_inputs = config.get("membank_inputs") or []
        if not isinstance(membank_inputs, list):
            continue
        for entry in membank_inputs:
            if not isinstance(entry, dict):
                continue
            if entry.get("type_tag") != "ai_session":
                continue
            key = _membank_source_id(entry)
            if not key or key not in declared_membank_outputs:
                continue
            writer_tag = declared_membank_outputs[key]
            if writer_tag != "ai_session":
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"vault key '{key}' is read as ai_session but writer "
                            f"does not declare ai_session type tag"
                        ),
                    }
                )

    # Parallel-branch vault race: warn when all writers for a vault key are on
    # parallel branches (not ancestors of the reader).  This is a warning, not
    # an error — the validator must not infer timing from node count or type.
    # The correct ceiling is: suggest a Wait Until node.
    if declared_membank_outputs:
        reverse_adj = _build_reverse_adjacency(all_nodes)
        # Map each vault key to the set of node_ids that write it
        key_writers: Dict[str, Set[str]] = {}
        for w_id, w_data in all_nodes.items():
            w_config = w_data.get("config") or {}
            for entry in w_config.get("membank_outputs") or []:
                k = _membank_source_id(entry)
                if k:
                    key_writers.setdefault(k, set()).add(w_id)

        for node_id, data in all_nodes.items():
            config = data.get("config") or {}
            membank_inputs = config.get("membank_inputs") or []
            if not isinstance(membank_inputs, list):
                continue
            for entry in membank_inputs:
                key = _membank_source_id(entry)
                if not key:
                    continue
                writers = key_writers.get(key)
                if not writers:
                    continue  # already caught by the error check above
                ancestors = _build_ancestor_set(node_id, all_nodes, reverse_adj)
                if not any(w in ancestors or w == node_id for w in writers):
                    warnings.append(
                        {
                            "node_id": node_id,
                            "message": (
                                f"Node reads vault key '{key}' but all writers are on "
                                f"parallel branches; consider adding a Wait Until node "
                                f"before this reader"
                            ),
                        }
                    )

    # Chat session: warn when use_chat_session is enabled but session_key is empty
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        if config.get("use_chat_session") and not str(config.get("session_key") or "").strip():
            warnings.append(
                {
                    "node_id": node_id,
                    "message": "Node has use_chat_session enabled but no session_key configured",
                }
            )

    if len(start_ids) == 1:
        reachable: Set[str] = set()
        _dfs_reachable(start_ids[0], all_nodes, reachable)
        for node_id in node_ids:
            if node_id not in reachable:
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": "Node is not reachable from the start node",
                    }
                )

    for health in derive_branch_health(all_nodes, output_types_from_factory(factory)):
        if health.state != ENDED_UNMERGED:
            continue
        warnings.append(
            {
                "node_id": health.terminus_node_id or health.branch_node_id,
                "message": (
                    "Merge Beacon is not connected to a merge node "
                    f"for branch port '{health.port}'"
                ),
            }
        )

    return {"success": not errors, "errors": errors, "warnings": warnings}


def _dfs_reachable(
    node_id: str, all_nodes: Dict[str, Dict[str, Any]], visited: Set[str]
) -> None:
    """Record every node reachable from node_id."""
    if node_id in visited:
        return
    visited.add(node_id)
    data = all_nodes.get(node_id)
    if data is None:
        return
    for conn in data.get("connections", {}).get("outputs", []):
        target = conn.get("target_node_id")
        if target and target in all_nodes:
            _dfs_reachable(target, all_nodes, visited)


def _declared_membank_outputs(
    all_nodes: Dict[str, Dict[str, Any]]
) -> Dict[str, Optional[str]]:
    """Collect declared memory-bank output ids mapped to their type_tag (or None)."""
    declared: Dict[str, Optional[str]] = {}
    for data in all_nodes.values():
        config = data.get("config") or {}
        membank_outputs = config.get("membank_outputs") or []
        if not isinstance(membank_outputs, list):
            continue
        for entry in membank_outputs:
            source_id = _membank_source_id(entry)
            if source_id:
                type_tag = entry.get("type_tag") if isinstance(entry, dict) else None
                declared[source_id] = type_tag
    return declared


def _membank_source_id(entry: Any) -> str:
    """Normalize a membank input/output entry to an id string."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return str(entry.get("source_id") or entry.get("output") or entry.get("id") or "")
    return ""


def _build_reverse_adjacency(all_nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Set[str]]:
    """Build a map of node_id → set of nodes that have a direct output edge to it."""
    reverse: Dict[str, Set[str]] = {nid: set() for nid in all_nodes}
    for node_id, data in all_nodes.items():
        for conn in data.get("connections", {}).get("outputs", []):
            target = conn.get("target_node_id")
            if target and target in reverse:
                reverse[target].add(node_id)
    return reverse


def _build_ancestor_set(
    node_id: str,
    all_nodes: Dict[str, Dict[str, Any]],
    reverse_adj: Optional[Dict[str, Set[str]]] = None,
) -> Set[str]:
    """Return the set of all nodes that can reach node_id via forward edges.

    Uses the reverse adjacency map for an efficient backward BFS.
    Does not include node_id itself.
    """
    if reverse_adj is None:
        reverse_adj = _build_reverse_adjacency(all_nodes)
    ancestors: Set[str] = set()
    queue = list(reverse_adj.get(node_id, set()))
    while queue:
        candidate = queue.pop()
        if candidate in ancestors:
            continue
        ancestors.add(candidate)
        queue.extend(reverse_adj.get(candidate, set()) - ancestors)
    return ancestors

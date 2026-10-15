"""
Validator for AttackOfTheNodes v0.5.

Runs static checks on a loaded workflow. Errors block execution; warnings are
informational, such as loose nodes unreachable from the start node.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from .branch_health import ENDED_UNMERGED, derive_branch_health, output_types_from_factory
from .branch_paths import path_index
from .data_types import DataType, types_compatible
from .port_types import input_port_type, metadata_for_type, port_metadata, trace_producer
from .vault_declarations import (
    config_vault_read_entries,
    continuation_selected as _continuation_selected,
    repeatable_slot_active as _repeatable_slot_active,
    standard_vault_reads,
    typed_vault_writes,
)
from .file_paths import normalize_local_path
from .node_errors import (
    ENGINE_ERROR_DEFINITIONS,
    ERROR_PORT,
    MUX_INPUT_PORT,
    UNMATCHED_ROUTE,
    mux_has_unmatched_route,
    mux_route_problems,
    mux_routes,
)
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
        config = data.get("config") or {}
        for conn in data.get("connections", {}).get("inputs", []):
            source_id = conn.get("source_node_id")
            target_port = str(conn.get("target_port") or "default")
            if source_id and _standard_source_active(
                config, target_port, "Upstream payload"
            ):
                sources.append(
                    {
                        "type": "node",
                        "source_id": source_id,
                        "port": conn.get("source_port", "default"),
                    }
                )

        membank_inputs = config.get("membank_inputs") or []
        if isinstance(membank_inputs, list):
            for entry in membank_inputs:
                source_id = _membank_source_id(entry)
                if source_id:
                    sources.append({"type": "membank", "source_id": source_id})
        # Standard-model vault reads: `<port>_source == "Vault"` paired with a
        # `<port>_vault_key`, plus the AI-session continuation input. These are
        # the helper-generated field names (NODE_HELPER.md input_sources).
        for entry in standard_vault_reads(config, {}):
            sources.append({"type": "membank", "source_id": entry["source_id"]})
        input_sources[node_id] = sources
    return input_sources


ERROR_MUX_NODE_TYPE = "error_mux_node"


def _validate_error_muxes(
    all_nodes: Dict[str, Dict[str, Any]],
    type_meta: Dict[str, Any],
    errors: List[Dict[str, str]],
    warnings: List[Dict[str, str]],
) -> None:
    """D7: an Error Mux may only list codes its upstream node can raise."""
    for node_id, data in all_nodes.items():
        if data.get("type") != ERROR_MUX_NODE_TYPE:
            continue
        config = data.get("config") or {}
        routes = {route["id"]: route["codes"] for route in mux_routes(config)}
        labels = {route["id"]: route["label"] for route in mux_routes(config)}
        for problem in mux_route_problems(config):
            warnings.append({"node_id": node_id, "message": f"Error Mux {problem}"})
        if not any(routes.values()) and not mux_has_unmatched_route(config):
            warnings.append({"node_id": node_id,
                             "message": "Error Mux lists no codes, so it never routes anything"})
        # Inline (the node's output into `input`) or wired from its `error` port.
        sources = [
            conn for conn in data.get("connections", {}).get("inputs", [])
            if conn.get("target_port") in {ERROR_PORT, MUX_INPUT_PORT}
        ]
        if not sources:
            warnings.append({"node_id": node_id,
                             "message": "Error Mux has no incoming connection"})
        for conn in sources:
            source_id = conn.get("source_node_id")
            if conn.get("target_port") == ERROR_PORT and conn.get("source_port") != ERROR_PORT:
                errors.append({
                    "node_id": node_id,
                    "message": (
                        f"Error Mux input comes from port '{conn.get('source_port')}' "
                        f"of {source_id}; connect a node's '{ERROR_PORT}' port"
                    ),
                })
                continue
            source = all_nodes.get(source_id) or {}
            source_meta = type_meta.get(source.get("type", "")) or {}
            known = {item.get("code") for item in source_meta.get("errors") or []}
            known |= set(ENGINE_ERROR_DEFINITIONS)
            for port, codes in routes.items():
                for code in codes:
                    if code not in known:
                        errors.append({
                            "node_id": node_id,
                            "message": (
                                f"Error Mux route '{labels[port]}' lists code '{code}', which "
                                f"{source.get('alias') or source_id} never raises "
                                f"(declared: {', '.join(sorted(c for c in known if c))})"
                            ),
                        })
        connected = {
            conn.get("source_port")
            for conn in data.get("connections", {}).get("outputs", [])
        }
        for port, codes in routes.items():
            if codes and port not in connected:
                warnings.append({
                    "node_id": node_id,
                    "message": f"Error Mux route '{labels[port]}' lists codes but has no connection",
                })
        if mux_has_unmatched_route(config) and UNMATCHED_ROUTE not in connected:
            warnings.append({
                "node_id": node_id,
                "message": "Error Mux unmatched route is on but has no connection",
            })


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
        type_out = set(meta.get("output_ports") or [])
        declared_out = set(factory.node_output_ports(data))
        type_in = set(meta.get("input_ports") or [])
        declared_in = set(factory.node_input_ports(data))
        for conn in data.get("connections", {}).get("outputs", []):
            port = conn.get("source_port", "default")
            if port in type_out and port not in declared_out:
                # The type has this port but this node's config hides it (for
                # example a Branch path above its count): it can never fire.
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"Connection on hidden output '{port}' never runs "
                            f"(this node's settings do not use that output)"
                        ),
                    }
                )
            # `error` is the one engine-level failure port every node has.
            if port not in declared_out and port not in type_out and port != ERROR_PORT:
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
            if port in type_in and port not in declared_in:
                # A Merge slot above this node's input_slots is never read.
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"Connection into hidden input '{port}' is never read "
                            f"(this node's settings do not use that input)"
                        ),
                    }
                )
            if port not in declared_in and port not in type_in:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"Orphaned input connection on undeclared port '{port}' "
                            f"(node type '{node_type}' has no such input)"
                        ),
                    }
                )

    _validate_error_muxes(all_nodes, _type_meta_cache, errors, warnings)

    # File-path fields: schema fields hinted with path_hint == "file".
    # An empty required path is an error; a path missing on disk is only a
    # warning because an earlier node may create the file during the run.
    # Source-gated fields (visible_when) are skipped while hidden — a
    # required Configured path is irrelevant when the input reads from
    # Upstream/Vault (standard input source model).
    for node_id, data in all_nodes.items():
        meta = _type_meta_cache.get(data.get("type", ""))
        if meta is None:
            continue
        config = data.get("config") or {}
        defaults = meta.get("default_config") or {}
        for field_name, field_info in (meta.get("config_schema") or {}).items():
            if field_info.get("path_hint") != "file":
                continue
            if not _field_visible(config, defaults, field_info):
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
            try:
                path = (normalize_local_path(raw_path)
                        if field_info.get("normalize_local_path")
                        else Path(raw_path).expanduser())
            except ValueError as exc:
                errors.append({"node_id": node_id, "message": str(exc)})
                continue
            if (field_info.get("path_mode") != "write"
                    and not path.exists()):
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": (
                            f"File for field '{field_name}' was not found at "
                            f"validation time: {path}"
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
        defaults = meta.get("default_config") or {}
        for field_name, field_info in (meta.get("config_schema") or {}).items():
            if not field_info.get("secret"):
                continue
            if not _field_visible(config, defaults, field_info):
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

    metadata_by_type = {
        str(item.get("type") or ""): item for item in factory.get_node_types_metadata()
    }
    vault_writes = _standard_model_vault_writes(all_nodes, metadata_by_type)
    standard_vault_reads = _standard_model_vault_reads(all_nodes, metadata_by_type)

    # Source selectors must name a real key; missing selections cannot fall
    # through to a connected input. Use node metadata to avoid unrelated keys.
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        metadata = metadata_by_type.get(data.get("type", "")) or {}
        for port in (metadata.get("input_port_metadata") or {}):
            if (config.get(f"{port}_source") == "Vault"
                    and _repeatable_slot_active(config, port)
                    and not str(config.get(f"{port}_vault_key") or "").strip()):
                errors.append({"node_id": node_id, "message": f"Vault source for '{port}' requires a key"})
        if config.get("vault_write") and not str(config.get("vault_write_key") or "").strip():
            errors.append({"node_id": node_id, "message": "Vault output requires a key"})

    for duplicate in _duplicate_input_source_errors(all_nodes, standard_vault_reads):
        errors.append(duplicate)

    declared_membank_outputs = _declared_membank_outputs(all_nodes)
    for node_writes in vault_writes.values():
        for key, type_tag in node_writes.items():
            # Prefer a concrete tag over an untyped legacy declaration.
            if type_tag is not None or key not in declared_membank_outputs:
                declared_membank_outputs[key] = type_tag
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

    # Node-specific reads (Get Variable, Variable Reader, Conditional,
    # Counter, Branch seeds) carry a required/optional flag in the shared
    # model. Optional reads have a runtime fallback, so a key nobody writes is
    # a warning; a required read without a writer blocks the run.
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        for entry in config_vault_read_entries(str(data.get("type") or ""), config):
            key = entry["source_id"]
            if key in declared_membank_outputs:
                continue
            if entry["required"]:
                errors.append({"node_id": node_id,
                               "message": f"Membank input source not declared: {key}"})
            else:
                warnings.append({"node_id": node_id,
                                 "message": _unwritten_read_message(config, entry)})

    # C2: an active Upstream edge whose producer type the receiving port does
    # not accept (port_types / data_types.types_compatible, the rule the
    # editor's connector choice and Source dropdowns use). A warning for now;
    # `any` on either side never warns.
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        for conn in data.get("connections", {}).get("inputs", []):
            source_id = str(conn.get("source_node_id") or "")
            target_port = str(conn.get("target_port") or "default")
            if source_id not in all_nodes or not _standard_source_active(
                config, target_port, "Upstream payload"
            ):
                continue
            wanted = input_port_type(factory, data, target_port)
            producer_id, actual = trace_producer(
                all_nodes, factory, source_id, str(conn.get("source_port") or "default"))
            if types_compatible(actual, wanted):
                continue
            port_name = str(port_metadata(factory, data, target_port, "input").get("name") or target_port)
            producer = all_nodes.get(producer_id) or all_nodes[source_id]
            warnings.append({
                "node_id": node_id,
                "message": (
                    f"Input '{port_name}' expects {wanted} but "
                    f"{_node_name(factory, producer)} sends {actual}"
                ),
            })

    # Typed vault: warn when a node reads a key typed "ai_session" but the writer
    # declared a different (or null) type_tag.  Error (key absent) is already above.
    # Type identities come from backend.data_types (the single canonical source
    # shared with node port data types) — not free strings.
    ai_session = DataType.AI_SESSION.value
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        membank_inputs = config.get("membank_inputs") or []
        entries = list(membank_inputs) if isinstance(membank_inputs, list) else []
        entries.extend(standard_vault_reads.get(node_id, []))
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            reader_tag = entry.get("type_tag")
            if not reader_tag or reader_tag == "any":
                continue
            key = _membank_source_id(entry)
            if not key or key not in declared_membank_outputs:
                continue
            writer_tag = declared_membank_outputs[key]
            if reader_tag != ai_session:
                if writer_tag and writer_tag != "any" and writer_tag != reader_tag:
                    warnings.append({"node_id": node_id, "message": f"Vault key '{key}' has type {writer_tag}, incompatible with {reader_tag} input"})
                continue
            if writer_tag != ai_session:
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
        for w_id, node_writes in vault_writes.items():
            for k in node_writes:
                key_writers.setdefault(k, set()).add(w_id)

        for node_id, data in all_nodes.items():
            config = data.get("config") or {}
            membank_inputs = config.get("membank_inputs") or []
            entries = list(membank_inputs) if isinstance(membank_inputs, list) else []
            entries.extend(standard_vault_reads.get(node_id, []))
            entries.extend(config_vault_read_entries(str(data.get("type") or ""), config))
            for entry in entries:
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

    # OS window choreography (D5): warn — never error — when a node
    # configures open/placement/close the current platform's window manager
    # cannot deliver. The workflow still runs; the capability degrades.
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        if not config.get("open_after_write"):
            continue
        capabilities = _window_capabilities()
        placement = str(config.get("window_placement") or "OS default")
        if placement != "OS default" and "place" not in capabilities:
            warnings.append(
                {
                    "node_id": node_id,
                    "message": (
                        f"Window placement '{placement}' is not supported on "
                        f"this platform; the file will open unplaced"
                    ),
                }
            )
        if config.get("close_on_run_end") and "close" not in capabilities:
            warnings.append(
                {
                    "node_id": node_id,
                    "message": (
                        "'Close when run ends' is not supported on this "
                        "platform; the window will stay open"
                    ),
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


def _node_name(factory, node: Dict[str, Any]) -> str:
    """Alias, else the type's display name (as the editor shows nodes)."""
    alias = str(node.get("alias") or "").strip()
    if alias:
        return alias
    metadata = metadata_for_type(factory, str(node.get("type") or "")) or {}
    return str(metadata.get("display_name") or node.get("type") or "node")


def _unwritten_read_message(config: Dict[str, Any], entry: Dict[str, Any]) -> str:
    """Warning for an optional node-specific Vault read with no writer."""
    key = entry["source_id"]
    port = str(entry.get("target_port") or "")
    if path_index(port) is not None:
        label = str(config.get(f"{port}_label") or port)
        return (f"Path '{label}' seeds from Vault key '{key}' but no node writes it; "
                f"the path gets the input payload")
    return f"Reads Vault key '{key}' but no node writes it; the node uses its fallback value"


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


def _duplicate_input_source_errors(
    all_nodes: Dict[str, Dict[str, Any]],
    standard_vault_reads: Dict[str, List[Dict[str, Optional[str]]]],
) -> List[Dict[str, str]]:
    """Errors for repeated input-source declarations on one node."""
    errors: List[Dict[str, str]] = []
    for node_id, data in all_nodes.items():
        seen: Dict[tuple[str, str, str], str] = {}

        def add(source_key: tuple[str, str, str], label: str, description: str) -> None:
            previous = seen.get(source_key)
            if previous is None:
                seen[source_key] = label
                return
            errors.append(
                {
                    "node_id": node_id,
                    "message": (
                        f"Duplicate input source {description} used by "
                        f"'{previous}' and '{label}'"
                    ),
                }
            )

        config = data.get("config") or {}
        for conn in data.get("connections", {}).get("inputs", []):
            source_id = str(conn.get("source_node_id") or "").strip()
            if not source_id:
                continue
            source_port = str(conn.get("source_port") or "default")
            target_port = str(conn.get("target_port") or "default")
            if not _standard_source_active(config, target_port, "Upstream payload"):
                continue
            add(
                ("node", source_id, source_port),
                target_port,
                f"upstream payload '{source_id}:{source_port}'",
            )

        config = data.get("config") or {}
        membank_inputs = config.get("membank_inputs") or []
        if isinstance(membank_inputs, list):
            for entry in membank_inputs:
                source_id = _membank_source_id(entry).strip()
                if source_id:
                    add(
                        ("membank", source_id, ""),
                        "membank_inputs",
                        f"vault key '{source_id}'",
                    )

        for entry in standard_vault_reads.get(node_id, []):
            source_id = _membank_source_id(entry).strip()
            if not source_id:
                continue
            target_port = str(entry.get("target_port") or source_id)
            add(
                ("membank", source_id, ""),
                target_port,
                f"vault key '{source_id}'",
            )
    return errors


def _standard_model_vault_writes(
    all_nodes: Dict[str, Dict[str, Any]],
    metadata_by_type: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Optional[str]]]:
    """Vault writes implied by config, node_id -> {key: tag}.

    Standard result routing (``vault_write`` + ``vault_write_key``) declares a
    write tagged with the node's default output data type; an enabled AI
    session (``use_chat_session`` + ``session_key``) declares an ``ai_session``
    write; node-specific writers (Set Variable, Variable Setter, Counter)
    declare their key with an unknown (None) tag. This keeps the
    existence/type/race checks working for nodes whose config UI does not edit
    ``membank_outputs`` directly, and matches the editor's Connections tab
    and Vault pickers (``vault_declarations.typed_vault_writes``).
    """
    writes: Dict[str, Dict[str, Optional[str]]] = {}
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        node_type = str(data.get("type") or "")
        node_writes = typed_vault_writes(node_type, config, metadata_by_type.get(node_type) or {})
        if node_writes:
            writes[node_id] = node_writes
    return writes


def _standard_model_vault_reads(
    all_nodes: Dict[str, Dict[str, Any]],
    metadata_by_type: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Optional[str]]]]:
    """Vault reads implied by standard-model config, node_id -> entries.

    ``<port>_source == "Vault"`` with a ``<port>_vault_key`` reads the key as
    the port's declared data type; ``continue_session_key`` reads an
    ``ai_session`` entry. Entries use the membank-inputs dict shape
    (``source_id`` + ``type_tag``) so the shared checks treat them uniformly.
    """
    reads: Dict[str, List[Dict[str, Optional[str]]]] = {}
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        metadata = metadata_by_type.get(str(data.get("type") or "")) or {}
        entries = standard_vault_reads(config, metadata)
        if entries:
            reads[node_id] = entries
    return reads


def _window_capabilities() -> Set[str]:
    """Current platform's window-manager capabilities (D5 warning support)."""
    from .window_manager import get_window_manager

    return get_window_manager().capabilities()


def _field_visible(
    config: Dict[str, Any],
    defaults: Dict[str, Any],
    field_info: Dict[str, Any],
) -> bool:
    """Whether a schema field's visible_when condition currently holds.

    Mirrors the form generator's rule semantics: every entry must match
    (AND); a list value matches any listed entry (OR within one field).
    Unset config keys fall back to the node type's default_config, the same
    value the config screen renders. Fields with no visible_when are always
    visible.
    """
    condition = field_info.get("visible_when")
    if not isinstance(condition, dict):
        return True
    for key, expected in condition.items():
        actual = config.get(key, defaults.get(key))
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _standard_source_active(
    config: Dict[str, Any], target_port: str, expected_source: str
) -> bool:
    """True when a standard source selector actively reads the target source."""
    if not _repeatable_slot_active(config, target_port):
        return False
    source_key = f"{target_port}_source"
    if source_key not in config:
        return True
    return config.get(source_key) == expected_source


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

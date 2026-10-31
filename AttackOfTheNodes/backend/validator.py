"""
Validator for AttackOfTheNodes v0.5.

Runs static checks on a loaded workflow. Errors block execution; warnings are
informational, such as loose nodes unreachable from the start node.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from .branch_health import ENDED_UNMERGED, derive_branch_health, output_types_from_factory
from .flow_behaviors import analyze_flow, reached_with_open_family
from .branch_paths import path_index
from .data_types import DataType, types_compatible
from .port_types import (
    input_port_type, metadata_for_type, port_metadata, resolved_metadata, trace_producers,
)
from .vault_declarations import (
    vault_output_fields,
    config_vault_read_entries,
    continuation_selected as _continuation_selected,
    repeatable_slot_active as _repeatable_slot_active,
    standard_vault_reads,
    typed_vault_writes,
    supports_standard_vault_write,
    concat_template_keys,
)
from .field_types import check_number, field_visible as _field_visible, number_fields, object_list_problems
from .file_paths import normalize_local_path
from .node_errors import (
    ENGINE_ERROR_DEFINITIONS,
    ERROR_PORT,
    MUX_DEFAULT_PORT,
    MUX_INPUT_PORT,
    UNMATCHED_ROUTE,
    mux_has_unmatched_route,
    mux_route_problems,
    mux_routes,
)
from .node_factory import NodeFactory
from .contracts import return_rows, row_problems, start_rows, sends_downstream
from .workflow_map import WorkflowMap

if TYPE_CHECKING:
    from .secrets_manager import SecretsManager


# Stable issue adapters, not flow rules. Literal codes retain the validator's
# static registration contract; all semantics belong to flow_behaviors.
_FLOW_ISSUE_TEMPLATES = {issue["code"]: issue for issue in (
    {"code": "merge_outside_split", "message": ""},
    {"code": "merge_required_path_escape", "message": ""},
    {"code": "merge_required_child_omitted", "message": ""},
    {"code": "impossible_wait", "message": ""},
    {"code": "wait_target_missing", "message": ""},
    {"code": "wait_target_needs_review", "message": ""},
    {"code": "flow_loop", "message": ""},
    {"code": "flow_needs_review", "message": ""},
    {"code": "repeated_join_unsupported", "message": ""},
)}


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
            warnings.append({"node_id": node_id, "code": "mux_route_problem", "message": f"Error Mux {problem}"})
        if not any(routes.values()) and not mux_has_unmatched_route(config):
            warnings.append({"node_id": node_id,
                             "code": "mux_no_codes", "message": "Error Mux lists no codes, so it never routes anything"})
        # Inline (the node's output into `input`) or wired from its `error` port.
        sources = [
            conn for conn in data.get("connections", {}).get("inputs", [])
            if conn.get("target_port") in {ERROR_PORT, MUX_INPUT_PORT}
        ]
        if not sources:
            warnings.append({"node_id": node_id,
                             "code": "mux_no_input", "message": "Error Mux has no incoming connection"})
        for conn in sources:
            source_id = conn.get("source_node_id")
            if conn.get("target_port") == ERROR_PORT and conn.get("source_port") != ERROR_PORT:
                errors.append({
                    "node_id": node_id,
                    "code": "mux_wrong_source_port", "message": (
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
                            "code": "mux_unknown_code", "message": (
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
                    "code": "mux_route_unconnected", "message": f"Error Mux route '{labels[port]}' lists codes but has no connection",
                })
        if mux_has_unmatched_route(config) and UNMATCHED_ROUTE not in connected:
            warnings.append({
                "node_id": node_id,
                "code": "mux_unmatched_unconnected", "message": "Error Mux unmatched route is on but has no connection",
            })


def validate_workflow(
    workflow_map: WorkflowMap,
    factory: NodeFactory,
    secrets_manager: Optional["SecretsManager"] = None,
    *, draft: bool = False,
) -> Dict[str, Any]:
    """Validate the loaded workflow structure."""
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    all_nodes = workflow_map.get_all_node_data()

    start_ids = [
        node_id for node_id, data in all_nodes.items() if data["type"] == "start_node"
    ]
    if len(start_ids) == 0:
        errors.append({"node_id": "", "code": "no_start_node", "message": "Workflow has no start node"})
    elif len(start_ids) > 1:
        errors.append(
            {
                "node_id": "",
                "code": "multiple_start_nodes", "message": f"Workflow has {len(start_ids)} start nodes; expected exactly 1",
            }
        )

    for node_id, data in all_nodes.items():
        if not factory.is_valid_node_type(data["type"]):
            errors.append(
                {"node_id": node_id, "code": "unknown_node_type", "message": f"Unknown node type: {data['type']}"}
            )

    node_ids = set(all_nodes.keys())
    for node_id, data in all_nodes.items():
        for conn in data.get("connections", {}).get("outputs", []):
            target = conn.get("target_node_id")
            if target and target not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "code": "missing_node", "message": f"Output connection targets missing node: {target}",
                    }
                )
        for conn in data.get("connections", {}).get("inputs", []):
            source = conn.get("source_node_id")
            if source and source not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "code": "missing_node", "message": f"Input connection from missing node: {source}",
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
                    "code": "deleted_node_stub", "message": (
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
        config = data.get("config") or {}
        default_meta = (meta.get("output_port_metadata") or {}).get("default") or {}
        # Only diagnose switches the runtime actually implements. Legacy nodes
        # without standard output routing may ignore retained shared keys.
        disabled = ("vault" in (default_meta.get("to") or [])
                    and config.get("transient_output") is False
                    and not (default_meta.get("pass_through") and config.get("dead_drop_passthrough")))
        if node_type == "start_node" and (config.get("rows") or config.get("no_inputs")):
            disabled = not any(sends_downstream(row) for row in start_rows(config))
        if disabled and any(c.get("source_port", "default") == "default"
                            for c in data.get("connections", {}).get("outputs", [])):
            warnings.append({"node_id": node_id, "code": "disabled_output_connection",
                             "message": "Connected default output publishes no payload with these settings "
                                        "(transient_output=false or no downstream Start rows); "
                                        "the next node receives no value from this connection"})
        for conn in data.get("connections", {}).get("outputs", []):
            port = conn.get("source_port", "default")
            routing = (factory.node_output_port_metadata(data).get(port) or {}).get("to")
            if routing is not None and "downstream" not in routing:
                errors.append({"node_id": node_id, "code": "vault_only_connection",
                               "message": f"Output '{port}' can only be sent to the Vault"})
            if port in type_out and port not in declared_out:
                # The type has this port but this node's config hides it (for
                # example a Branch path above its count): it can never fire.
                warnings.append(
                    {
                        "node_id": node_id,
                        "code": "hidden_output_connection", "message": (
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
                        "code": "undeclared_port", "message": (
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
                        "code": "hidden_input_connection", "message": (
                            f"Connection into hidden input '{port}' is never read "
                            f"(this node's settings do not use that input)"
                        ),
                    }
                )
            if port not in declared_in and port not in type_in:
                errors.append(
                    {
                        "node_id": node_id,
                        "code": "undeclared_port", "message": (
                            f"Orphaned input connection on undeclared port '{port}' "
                            f"(node type '{node_type}' has no such input)"
                        ),
                    }
                )

    _validate_error_muxes(all_nodes, _type_meta_cache, errors, warnings)

    # An ordinary output follows its first connection only
    # (WorkflowMap.find_next_node_id). The `error` port routes by code and an
    # inline Error Mux on a normal output is a catch, not a second path,
    # unless the mux has a No error path too: that path then never runs.
    for node_id, data in all_nodes.items():
        by_port: Dict[str, List[str]] = {}
        for conn in data.get("connections", {}).get("outputs", []):
            port = str(conn.get("source_port") or "default")
            target = str(conn.get("target_node_id") or "")
            target_data = all_nodes.get(target) or {}
            catch_only = (
                target_data.get("type") == ERROR_MUX_NODE_TYPE
                and conn.get("target_port") == MUX_INPUT_PORT
                and not any(
                    out.get("source_port") == MUX_DEFAULT_PORT
                    for out in target_data.get("connections", {}).get("outputs", [])
                )
            )
            if port == ERROR_PORT or catch_only:
                continue
            by_port.setdefault(port, []).append(target)
        for port, targets in by_port.items():
            if len(targets) < 2:
                continue
            names = [_node_name(factory, all_nodes[t]) if t in all_nodes else t for t in targets]
            warnings.append({
                "node_id": node_id,
                "port": port,
                "code": "ignored_fan_out", "message": (
                    f"Output '{port}' has {len(targets)} connections; only the first "
                    f"({names[0]}) runs. Use a Parallel Branch to run {', '.join(names[1:])} too"
                ),
            })

    # C5: number fields hold a finite number inside the field's declared range
    # (field_types.check_number, the rule the node editor enforces on save).
    # A saved value that breaks it blocks the run; nothing is coerced.
    for node_id, data in all_nodes.items():
        meta = _type_meta_cache.get(data.get("type", ""))
        if meta is None:
            continue
        config = data.get("config") or {}
        defaults = meta.get("default_config") or {}
        for field_name, field_info in number_fields(meta.get("config_schema") or {}):
            if not _field_visible(config, defaults, field_info):
                continue
            raw = config.get(field_name, defaults.get(field_name))
            _, problem = check_number(field_info, raw, defaults.get(field_name))
            if problem:
                label = str(field_info.get("label") or field_name)
                errors.append({
                    "node_id": node_id,
                    "port": field_name,
                    "code": "invalid_number", "message": f"{label}: {problem} (saved value {raw!r})",
                })

    # Saved values (C2): Remember, Recall and If changed need a name.
    for node_id, data in all_nodes.items():
        if data.get("type") in ("remember_node", "recall_node", "if_changed_node") and \
                not str((data.get("config") or {}).get("name") or "").strip():
            errors.append({
                "node_id": node_id, "port": "name", "code": "saved_name_missing",
                "message": "Saved as is blank: give the value a name, like last_version",
            })

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
                            "code": "missing_file_path", "message": f"Missing file path in field '{field_name}'",
                        }
                    )
                continue
            try:
                path = (normalize_local_path(raw_path)
                        if field_info.get("normalize_local_path")
                        else Path(raw_path).expanduser())
            except ValueError as exc:
                errors.append({"node_id": node_id, "code": "invalid_file_path", "message": str(exc)})
                continue
            if (field_info.get("path_mode") != "write"
                    and not path.exists()):
                warnings.append(
                    {
                        "node_id": node_id,
                        "code": "file_not_found", "message": (
                            f"File for field '{field_name}' was not found at "
                            f"validation time: {path}"
                        ),
                    }
                )

    # Opted-in row lists share exact uniqueness/count rules with the form.
    for node_id, data in all_nodes.items():
        meta = _type_meta_cache.get(data.get("type", "")) or {}
        config = {**(meta.get("default_config") or {}), **(data.get("config") or {})}
        for problem in object_list_problems(meta.get("config_schema") or {}, config):
            errors.append({"node_id": node_id, "code": "invalid_rows", "message": problem})
        for port, (enabled, key_field, _) in list(vault_output_fields(meta).items())[1:]:
            if config.get(enabled) and not str(config.get(key_field) or "").strip():
                errors.append({"node_id": node_id, "code": "vault_output_key_missing",
                               "message": f"{port}: enter a Vault output key"})

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
                            "code": "secret_not_configured", "message": (
                                f"Secret key for field '{field_name}' is required but not configured"
                            ),
                        }
                    )
                continue
            if secrets_manager is not None and not secrets_manager.has_key(key_name):
                warnings.append(
                    {
                        "node_id": node_id,
                        "code": "secret_missing", "message": (
                            f"Secret key '{key_name}' (field '{field_name}') "
                            f"is not present in the secrets store"
                        ),
                    }
                )

    metadata_by_type = {
        str(item.get("type") or ""): item for item in factory.get_node_types_metadata()
    }
    vault_writes = _standard_model_vault_writes(all_nodes, factory)
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
                errors.append({"node_id": node_id, "code": "vault_source_key_missing", "message": f"Vault source for '{port}' requires a key"})
        if config.get("vault_write") and not str(config.get("vault_write_key") or "").strip():
            errors.append({"node_id": node_id, "code": "vault_output_key_missing", "message": "Vault output requires a key"})
        if config.get("vault_write") and not supports_standard_vault_write(str(data.get("type") or ""), config, metadata):
            warnings.append({"node_id": node_id, "code": "vault_write_unsupported",
                             "message": "vault_write is ignored by this node's output routing; "
                                        "it does not publish vault_write_key. Use a supported Vault output or row."})

    for duplicate in _duplicate_input_source_errors(all_nodes, standard_vault_reads):
        errors.append(duplicate)

    declared_membank_outputs = _declared_membank_outputs(all_nodes)
    for node_writes in vault_writes.values():
        for key, type_tag in node_writes.items():
            # Prefer a concrete tag over an untyped legacy declaration.
            if type_tag is not None or key not in declared_membank_outputs:
                declared_membank_outputs[key] = type_tag
    reverse_adj = _build_reverse_adjacency(all_nodes)
    for node_id, data in all_nodes.items():
        if data.get("type") != "concat_node":
            continue
        config = data.get("config") or {}
        ancestors = _build_ancestor_set(node_id, all_nodes, reverse_adj) - {node_id}
        earlier_keys = set()
        for ancestor in ancestors:
            earlier_keys.update(vault_writes.get(ancestor, {}))
            for entry in (all_nodes[ancestor].get("config") or {}).get("membank_outputs") or []:
                earlier_keys.add(_membank_source_id(entry))
        for key in concat_template_keys(config, metadata_by_type.get("concat_node") or {}):
            if key not in earlier_keys:
                warnings.append({"node_id": node_id, "code": "template_vault_key_unwritten",
                                 "message": f"Concat template reads Vault key '{key}' but no earlier node "
                                            "on an incoming path declares a write. Missing keys error at runtime; "
                                            "parallel writers need ordering before this reader."})
    for node_id, sources in derive_input_sources(all_nodes).items():
        for source in sources:
            source_type = source.get("type")
            source_id = source.get("source_id", "")
            if source_type == "node" and source_id not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "code": "missing_node", "message": f"Input source missing node: {source_id}",
                    }
                )
            elif source_type == "membank" and source_id not in declared_membank_outputs:
                errors.append(
                    {
                        "node_id": node_id,
                        "code": "undeclared_vault_key", "message": f"Membank input source not declared: {source_id}",
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
                               "code": "undeclared_vault_key", "message": f"Membank input source not declared: {key}"})
            else:
                warnings.append({"node_id": node_id, "port": entry["target_port"],
                                 "code": "unwritten_vault_key", "message": _unwritten_read_message(config, entry)})

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
            # Every producer a pass-through chain can forward, not only the
            # first connection into it (PR 56 review).
            for producer_id, actual in trace_producers(
                all_nodes, factory, source_id, str(conn.get("source_port") or "default")
            ):
                if types_compatible(actual, wanted):
                    continue
                port_name = str(port_metadata(factory, data, target_port, "input").get("name") or target_port)
                producer = all_nodes.get(producer_id) or all_nodes[source_id]
                warnings.append({
                    "node_id": node_id,
                    "port": target_port,
                    "source_node_id": producer_id,
                    "code": "type_mismatch", "message": (
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
                    warnings.append({"node_id": node_id, "code": "vault_type_mismatch", "message": f"Vault key '{key}' has type {writer_tag}, incompatible with {reader_tag} input"})
                continue
            if writer_tag != ai_session:
                warnings.append(
                    {
                        "node_id": node_id,
                        "code": "ai_session_tag_missing", "message": (
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
                            "code": "vault_race", "message": (
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
                    "code": "chat_session_key_missing", "message": "Node has use_chat_session enabled but no session_key configured",
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
                    "code": "window_placement_unsupported", "message": (
                        f"Window placement '{placement}' is not supported on "
                        f"this platform; the file will open unplaced"
                    ),
                }
            )
        if config.get("close_on_run_end") and "close" not in capabilities:
            warnings.append(
                {
                    "node_id": node_id,
                    "code": "window_close_unsupported", "message": (
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
                        "code": "unreachable", "message": "Node is not reachable from the start node",
                    }
                )

    for health in derive_branch_health(all_nodes, output_types_from_factory(factory)):
        if health.state != ENDED_UNMERGED:
            continue
        warnings.append(
            {
                "node_id": health.terminus_node_id or health.branch_node_id,
                "code": "merge_beacon_unconnected", "message": (
                    "Merge Beacon is not connected to a merge node "
                    f"for branch port '{health.port}'"
                ),
            }
        )

    # A stand-in map (tests, previews) without the flag is a standard workflow.
    _check_subworkflow_calls(all_nodes, str(getattr(workflow_map, "workflow_id", "") or ""),
                             errors, warnings)
    _check_contract(all_nodes, factory, bool(getattr(workflow_map, "callable", False)),
                    errors, warnings)

    flow = analyze_flow(all_nodes, factory, draft=draft)
    for finding in flow.findings:
        # An ignored ordinary fan-out already explains an ambiguous hand-built
        # fragment. Preserve that diagnostic rather than adding a speculative
        # standalone-Merge warning for the surviving wire order.
        if not draft and finding.code == "merge_outside_split" and any(
            warning["code"] == "ignored_fan_out"
            and warning["node_id"] in _build_ancestor_set(finding.node_id, all_nodes)
            for warning in warnings
        ):
            continue
        issue = dict(_FLOW_ISSUE_TEMPLATES[finding.code], node_id=finding.node_id,
                     message=finding.message, path=list(finding.path), slot=finding.slot,
                     route=finding.route, repair=finding.repair)
        (errors if finding.level == "error" else warnings).append(issue)
    return {"success": not errors, "errors": errors, "warnings": warnings,
            "flow_analysis": flow.to_dict()}


SUBWORKFLOW_NODE_TYPE = "subworkflow_node"


def _check_subworkflow_calls(all_nodes, workflow_id, errors, warnings) -> None:
    """Step 4b: each Subworkflow node's child exists and is a subworkflow
    (C12); its input and result mappings fit the child's contract, matched by
    exact name and type as a run matches them; and no chain of calls reachable
    from here loops (C17: recursion is rejected in v1). Children are read
    fresh on every pass, once each."""
    from .contracts import ContractError, check, parse_text
    from .persistence import load_workflow
    from .stash_manager import StashManager, input_value

    stash = StashManager()  # read once per pass, only if a row uses it
    cache: Dict[str, Optional[Dict[str, Any]]] = {}

    def load(child_id: str) -> Optional[Dict[str, Any]]:
        if child_id not in cache:
            cache[child_id] = load_workflow(child_id) if child_id else None
        return cache[child_id]

    def callees(data: Optional[Dict[str, Any]]) -> List[str]:
        return [str((node.get("config") or {}).get("workflow_id") or "").strip()
                for node in ((data or {}).get("nodes") or {}).values()
                if isinstance(node, dict) and node.get("type") == SUBWORKFLOW_NODE_TYPE]

    # One traversal of the reachable call graph finds every loop, including
    # one that starts below this workflow (Root → A → B → A).
    looping: Set[str] = set()
    state: Dict[str, str] = {}

    def visit(current: str, path: List[str]) -> None:
        if state.get(current) == "done":
            return
        if state.get(current) == "open":
            looping.update(path[path.index(current):])
            return
        state[current] = "open"
        data = all_nodes_data if current == workflow_id else load(current)
        for callee in callees(data):
            if callee:
                visit(callee, path + [callee])
        state[current] = "done"

    all_nodes_data = {"nodes": all_nodes}
    root = workflow_id or "<this workflow>"
    if not workflow_id:
        workflow_id = root
    visit(root, [root])

    def leads_to_loop(child_id: str) -> bool:
        seen, stack = set(), [child_id]
        while stack:
            current = stack.pop()
            if current in looping:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(callees(all_nodes_data if current == workflow_id else load(current)))
        return False

    for node_id, data in all_nodes.items():
        if data.get("type") != SUBWORKFLOW_NODE_TYPE:
            continue
        config = data.get("config") or {}
        child_id = str(config.get("workflow_id") or "").strip()
        child = load(child_id)
        if not child_id or child is None:
            errors.append({"node_id": node_id, "code": "subworkflow_not_found",
                           "message": "Pick a saved subworkflow to call" if not child_id
                           else f"The subworkflow {child_id!r} no longer exists"})
            continue
        name = str(child.get("name") or child_id)
        if not child.get("callable"):
            errors.append({"node_id": node_id, "code": "subworkflow_not_callable",
                           "message": f"{name!r} is a standard workflow, not a subworkflow"})
            continue
        if leads_to_loop(child_id):
            errors.append({"node_id": node_id, "code": "subworkflow_recursion",
                           "message": f"Calling {name!r} leads into a loop of subworkflow calls; "
                                      "a workflow can't call itself"})
        child_nodes = [node for node in (child.get("nodes") or {}).values() if isinstance(node, dict)]
        starts = [node for node in child_nodes if node.get("type") == "start_node"]
        rows = [row for row in start_rows((starts[0].get("config") or {}) if starts else {})
                if not row.get("_legacy")]
        by_name = {row["name"]: row for row in rows}
        mappings = [row for row in config.get("inputs") or [] if isinstance(row, dict)
                    and str(row.get("name") or "").strip()]
        mapped = {str(row["name"]).strip() for row in mappings}
        for key in sorted(mapped - set(by_name)):
            errors.append({"node_id": node_id, "code": "subworkflow_input_unknown",
                           "message": f"{name!r} has no input named {key!r}"})
        for mapping in mappings:
            target = by_name.get(str(mapping["name"]).strip())
            if target is not None and mapping.get("source") == "Stash":
                entry_name = str(mapping.get("stash_entry") or "").strip()
                entry = stash.get_by_name(entry_name) if entry_name else None
                if entry is None:
                    errors.append({"node_id": node_id, "code": "subworkflow_stash_missing",
                                   "message": f"Input {target['name']!r} of {name!r}: "
                                   + (f"no Stash entry {entry_name!r}" if entry_name
                                      else "pick a Stash entry")})
                    continue
                # As the call does it: a file entry is checked as a typed
                # value, text is parsed by the input's type (blank = unset).
                stashed = input_value(entry)
                try:
                    if entry["type"] == "file":
                        check(target["type"], stashed)
                    elif stashed != "":
                        parse_text(target["type"], stashed)
                except ContractError as exc:
                    errors.append({"node_id": node_id, "code": "subworkflow_input_invalid",
                                   "message": f"Input {target['name']!r} of {name!r} "
                                   f"(Stash entry {entry['name']!r}): {exc}"})
                continue
            value = mapping.get("value", "")
            if (target is None or (mapping.get("source") or "Configured") != "Configured"
                    or not isinstance(value, str) or value == ""):
                continue
            try:
                parse_text(target["type"], value)
            except ContractError as exc:
                errors.append({"node_id": node_id, "code": "subworkflow_input_invalid",
                               "message": f"Input {target['name']!r} of {name!r}: {exc}"})
        for row in rows:
            filled = any(str(m["name"]).strip() == row["name"]
                         and not ((m.get("source") or "Configured") == "Configured"
                                  and m.get("value", "") == "")
                         for m in mappings)
            if filled:
                continue
            if row["required"] and (row.get("value") is None or row.get("value") == ""):
                errors.append({"node_id": node_id, "code": "subworkflow_input_missing",
                               "message": f"{name!r} needs input {row['name']!r} and nothing fills it"})
            else:
                warnings.append({"node_id": node_id, "code": "subworkflow_input_unmapped",
                                 "message": f"{name!r} input {row['name']!r} uses its own default"})
        results = {row["name"] for node in child_nodes if node.get("type") == "end_node"
                   for row in return_rows(node.get("config") or {})}
        for route in config.get("results") or []:
            route_name = str((route or {}).get("name") or "").strip() if isinstance(route, dict) else ""
            if route_name and route_name not in results:
                errors.append({"node_id": node_id, "code": "subworkflow_result_unknown",
                               "message": f"{name!r} sends back no result named {route_name!r}"})


def _check_contract(all_nodes, factory, callable_workflow: bool, errors, warnings) -> None:
    """Step 4a: Start rows and the Return End (SUBWORKFLOWS_PROPOSAL C1-C7)."""
    for node_id, data in all_nodes.items():
        config = data.get("config") or {}
        if data.get("type") == "start_node":
            rows = start_rows(config)
            for problem in row_problems(rows, "Input"):
                errors.append({"node_id": node_id, "code": "contract_row_invalid", "message": problem})
            for row in rows:
                raw = row.get("value")
                no_value = raw is None or raw == ""
                if row["required"] and no_value:
                    warnings.append({
                        "node_id": node_id, "code": "input_required_no_value",
                        "message": f"Input '{row['name']}' is required and has no value: a direct run "
                                   "stops before starting unless it is supplied (--input)",
                    })
        if data.get("type") == "end_node":
            rows = return_rows(config)
            for problem in row_problems(rows, "Result"):
                errors.append({"node_id": node_id, "code": "contract_row_invalid", "message": problem})
            if config.get("return_end") and not callable_workflow:
                warnings.append({
                    "node_id": node_id, "code": "return_end_not_callable",
                    "message": f"{_node_name(factory, data)} is a Return End, but the workflow isn't "
                               "callable; its results are ignored",
                })
    if not callable_workflow:
        return
    returns = [node_id for node_id, data in all_nodes.items()
               if data.get("type") == "end_node" and (data.get("config") or {}).get("return_end")]
    if len(returns) > 1:
        for node_id in returns:
            errors.append({
                "node_id": node_id, "code": "multiple_return_ends",
                "message": f"{len(returns)} Ends are Return Ends; a callable workflow returns from exactly one",
            })
        return
    if returns and _reached_with_open_branch(all_nodes, returns[0]):
        errors.append({
            "node_id": returns[0], "code": "return_end_unmerged",
            "message": f"{_node_name(factory, all_nodes[returns[0]])} can be reached inside a Parallel "
                       "Branch that hasn't merged; merge the branches before the Return End",
        })


def _reached_with_open_branch(all_nodes, target: str) -> bool:
    """Compatibility hook; inherited-family semantics live in the flow owner."""
    return reached_with_open_family(all_nodes, target)


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
                    "code": "duplicate_input_source", "message": (
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
    factory: NodeFactory,
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
        node_writes = typed_vault_writes(node_type, config, resolved_metadata(factory, node_type, config))
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

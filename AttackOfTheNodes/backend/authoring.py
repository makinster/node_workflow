"""Workflow authoring: discover node types, describe them, build workflows.

A small JSON spec in, an ordinary saved workflow out, through the same
services the app uses (NodeFactory, WorkflowMap, the validator, SaveManager).
The ``aotn`` CLI (``aotn_author.py``) is one adapter; a future server or AI
tool interface wraps the same three functions.

Spec format ``aotn-workflow/1``::

    {
      "format": "aotn-workflow/1",
      "name": "Summarise a file",
      "nodes": {
        "start": {"type": "start_node", "config": {"greeting": "hello"}},
        "read":  {"type": "file_reader_node", "alias": "Read notes",
                  "config": {"input_source": "Configured", "file_path": "/tmp/n.txt"}}
      },
      "connections": [{"from": "start.default", "to": "read.input"}]
    }

- Node handles (``start``, ``read``) are local to the spec; real node ids are
  generated and reported back. Fields declared as node references (Wait
  Until's ``target_node_ids``) take handles and are translated.
- ``config`` holds real config keys, merged over the type's defaults.
  Unknown keys and bad numbers are errors; keys a type uses but does not
  describe in its schema are reported as unchecked by ``describe``.
- Every connection names both ports explicitly; both must exist for the
  node's config.

A build checks the spec, creates the workflow in memory, runs the validator,
saves through SaveManager (atomic write, never over an existing workflow or
name), reloads the saved file into a fresh map and checks it again. Any error
means nothing is written. A passing build means these checks passed, not that
external services or runtime behaviour were exercised (run it with
``aotn run``).
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from .event_bus import EventBus
from .field_types import check_number, field_visible, number_fields
from .node_errors import ERROR_PORT
from .node_factory import NodeFactory
from . import persistence
from .port_types import (
    _vault_writers, metadata_for_type, port_metadata, resolved_metadata, trace_producers,
)
from .save_manager import SaveManager
from .data_types import types_compatible
from .validator import _build_ancestor_set, _build_reverse_adjacency, validate_workflow
from .vault_declarations import typed_vault_writes, vault_read_entries
from .workflow_map import WorkflowMap
from .workflow_names import name_problem, name_taken

FORMAT = "aotn-workflow/1"
HANDLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")

#: Types an author never places directly.
HIDDEN_TYPES = frozenset({"tombstone_node"})

#: Config keys the shared output-routing and Vault models give every node,
#: whether or not a type lists them in its defaults.
STANDARD_KEYS = frozenset({
    "transient_output", "transient_outputs", "dead_drop_passthrough",
    "vault_write", "vault_write_key", "vault_write_description",
    "membank_inputs", "membank_outputs", "show_error_path",
})

#: Config fields that hold node ids; a spec gives handles, the build
#: translates them. Moves into node declarations with C10.
NODE_REFERENCE_FIELDS: Dict[str, Tuple[str, ...]] = {
    "wait_until_node": ("target_node_ids",),
}

#: Validator warnings that fail a build (an authored spec should not
#: produce them on purpose).
BUILD_ERROR_CODES = frozenset({"ignored_fan_out"})

#: Build diagnostic codes (validator issues keep their own codes).
AUTHORING_CODES: Dict[str, str] = {
    "spec_invalid": "The spec is not shaped like aotn-workflow/1.",
    "bad_handle": "A node handle is not a lowercase identifier.",
    "unknown_node_type": "A node's type is not registered (or is internal).",
    "unknown_config_key": "A config key is not one the node type knows.",
    "invalid_number": "A number field is not a finite number in its allowed range.",
    "unknown_reference": "A node-reference field names a handle the spec does not define.",
    "unknown_port": "A connection uses a port the node does not have with this config.",
    "duplicate_connection": "The same connection is listed twice.",
    "duplicate_name": "A saved workflow already has this name.",
    "name_invalid": "The name breaks the shared name rule (blank, or ends with [sub]).",
    "reload_mismatch": "The saved file does not reload to the workflow that was built.",
}


class AuthoringError(ValueError):
    """A request ``describe`` cannot answer (unknown type)."""


# --- discover -----------------------------------------------------------------------


def list_node_types(factory: NodeFactory) -> List[Dict[str, Any]]:
    """Every type an author can place, sorted by family then name."""
    rows = []
    for meta in factory.get_node_types_metadata():
        if meta["type"] in HIDDEN_TYPES:
            continue
        rows.append({
            "type": meta["type"],
            "name": str(meta.get("display_name") or meta["type"]),
            "family": str(meta.get("primary_family") or ""),
            "group": str(meta.get("group") or ""),
            "description": str(meta.get("description") or ""),
        })
    return sorted(rows, key=lambda row: (row["family"], row["name"]))


# --- describe ------------------------------------------------------------------------


def describe_node_type(
    factory: NodeFactory, node_type: str, overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """What a node of ``node_type`` takes, does and produces with ``overrides``
    applied over its defaults: config fields (with visibility for this config),
    resolved input/output ports and types, Vault reads/writes, declared errors,
    node-reference fields and config keys the schema cannot check."""
    meta = metadata_for_type(factory, node_type)
    if meta is None or node_type in HIDDEN_TYPES:
        raise AuthoringError(f"Unknown node type: {node_type}")
    defaults = dict(meta.get("default_config") or {})
    schema = dict(meta.get("config_schema") or {})
    config = {**deepcopy(defaults), **(overrides or {})}
    node = {"type": node_type, "config": config}
    resolved = resolved_metadata(factory, node_type, config)

    fields = []
    for key, info in schema.items():
        if not isinstance(info, dict):
            continue
        field = {
            "key": key,
            "type": str(info.get("type") or "string"),
            "label": str(info.get("label") or key),
            "default": defaults.get(key),
            "required": bool(info.get("required")),
            "visible": field_visible(config, defaults, info),
        }
        for extra in ("options", "min", "max", "min_exclusive", "description", "visible_when"):
            if extra in info:
                field[extra] = info[extra]
        fields.append(field)

    inputs = []
    for port in factory.node_input_ports(node):
        info = port_metadata(factory, node, port, "input")
        source = schema.get(f"{port}_source") or {}
        inputs.append({
            "port": port,
            "name": str(info.get("name") or port),
            "data_type": str(info.get("data_type") or "any"),
            "required": bool(info.get("required")),
            "description": str(info.get("description") or ""),
            "source_field": f"{port}_source" if source else None,
            "source_options": list(source.get("options") or []),
        })
    outputs = []
    for port in factory.node_output_ports(node):
        info = (resolved.get("output_port_metadata") or {}).get(port) or {}
        outputs.append({
            "port": port,
            "name": str(info.get("name") or port),
            "data_type": str(info.get("data_type") or "any"),
            "description": str(info.get("description") or ""),
        })
    if ERROR_PORT not in {port["port"] for port in outputs}:
        outputs.append({"port": ERROR_PORT, "name": "Error", "data_type": "any",
                        "description": "Engine-level failure path every node has"})

    return {
        "type": node_type,
        "name": str(meta.get("display_name") or node_type),
        "family": str(meta.get("primary_family") or ""),
        "description": str(meta.get("description") or ""),
        "config": config,
        "fields": fields,
        "unchecked_keys": sorted((set(defaults) - set(schema)) | set(meta.get("custom_config_keys") or {})),
        "custom_keys": dict(meta.get("custom_config_keys") or {}),
        "standard_keys": sorted(STANDARD_KEYS),
        "node_reference_fields": list(NODE_REFERENCE_FIELDS.get(node_type, ())),
        "inputs": inputs,
        "outputs": outputs,
        "vault_reads": vault_read_entries(node_type, config, resolved),
        "vault_writes": [
            {"key": key, "data_type": tag or "any"}
            for key, tag in typed_vault_writes(node_type, config, resolved).items()
        ],
        "errors": list(meta.get("errors") or []),
    }


# --- build -----------------------------------------------------------------------------


def build_workflow(factory: NodeFactory, spec: Any, *, write: bool = True) -> Dict[str, Any]:
    """Build (and, with ``write``, save) the workflow ``spec`` describes.

    Returns a report: ``ok``, ``workflow_id``, ``name``, ``path`` (when
    written), ``nodes`` (handle -> generated id) and ``diagnostics`` (each
    ``{level, code, node, message}``; ``node`` is a handle or None). Nothing
    is written unless every check passes.
    """
    diagnostics: List[Dict[str, Any]] = []

    def report(ok: bool, **extra: Any) -> Dict[str, Any]:
        return {"ok": ok, "format": FORMAT, "diagnostics": diagnostics, **extra}

    def add(level: str, code: str, message: str, node: Optional[str] = None) -> None:
        diagnostics.append({"level": level, "code": code, "node": node, "message": message})

    nodes_spec, connections, name = _read_spec(spec, add)
    # Only a spec that cannot be walked stops here; otherwise every problem
    # is collected so one build lists them all.
    if not nodes_spec:
        return report(False)
    nodes_spec = {handle: node for handle, node in nodes_spec.items()
                  if isinstance(node, dict) and isinstance(node.get("type"), str)}

    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new(name)
    if "callable" in spec:
        # Step 4 (C27): a callable workflow can be run as a subworkflow.
        if isinstance(spec["callable"], bool):
            workflow_map.set_callable(spec["callable"])
        else:
            add("error", "spec_invalid", "\"callable\" must be true or false")
    ids: Dict[str, str] = {}
    configs: Dict[str, Dict[str, Any]] = {}
    for handle, node_spec in nodes_spec.items():
        node_type = node_spec["type"]
        meta = metadata_for_type(factory, node_type)
        if meta is None or node_type in HIDDEN_TYPES:
            add("error", "unknown_node_type", f"Unknown node type: {node_type}", handle)
            continue
        overrides = node_spec.get("config") if isinstance(node_spec.get("config"), dict) else {}
        configs[handle] = _checked_config(meta, overrides, handle, add)
        alias = node_spec.get("alias") if isinstance(node_spec.get("alias"), str) else ""
        node_id = workflow_map.add_node(node_type, alias=alias)
        ids[handle] = node_id
    for handle, config in configs.items():
        node_type = nodes_spec[handle]["type"]
        for field in NODE_REFERENCE_FIELDS.get(node_type, ()):
            if field in config:
                config[field] = _translated_references(config[field], ids, handle, field, add)
        workflow_map.update_node_config(ids[handle], config)

    seen = set()
    for index, connection in enumerate(connections):
        if len(connection) != 2:
            continue  # malformed, already reported
        (source, source_port), (target, target_port) = connection
        where = f"connection {index + 1} ({source}.{source_port} -> {target}.{target_port})"
        if (source, source_port, target, target_port) in seen:
            add("error", "duplicate_connection", f"{where} is listed twice")
            continue
        seen.add((source, source_port, target, target_port))
        if source not in ids or target not in ids:
            continue  # unknown_node_type already reported
        source_node = workflow_map.get_node_data(ids[source])
        target_node = workflow_map.get_node_data(ids[target])
        outputs = list(factory.node_output_ports(source_node)) + [ERROR_PORT]
        inputs = list(factory.node_input_ports(target_node))
        if source_port not in outputs:
            add("error", "unknown_port",
                f"{where}: {source} has no output '{source_port}' (has: {', '.join(outputs)})", source)
            continue
        if target_port not in inputs:
            add("error", "unknown_port",
                f"{where}: {target} has no input '{target_port}' (has: {', '.join(inputs) or 'none'})", target)
            continue
        workflow_map.connect(ids[source], source_port, ids[target], target_port)

    handles = {node_id: handle for handle, node_id in ids.items()}
    _add_validation(workflow_map, factory, handles, add, diagnostics)
    if any(d["level"] == "error" for d in diagnostics):
        return report(False)
    if not write:
        return report(True, workflow_id=workflow_map.workflow_id, name=name, nodes=ids)

    # Case-insensitive, like `aotn run <name>` resolves names; the library's
    # rename and New use the same rule (workflow_names).
    callable_ = bool(workflow_map.callable)
    if name_taken(name, callable_=callable_):
        add("error", "duplicate_name", f"A saved workflow is already named {name!r}; choose another name")
        return report(False)
    problem = name_problem(name, callable_=callable_)
    if problem:
        add("error", "name_invalid", problem)
        return report(False)
    workflow_id = workflow_map.workflow_id
    SaveManager(workflow_map).save_current_workflow()
    problem = _reload_problem(factory, workflow_id, workflow_map)
    if problem:
        persistence.delete_workflow(workflow_id)
        add("error", "reload_mismatch", problem)
        return report(False)
    return report(True, workflow_id=workflow_id, name=name, nodes=ids,
                  path=str(persistence.WORKFLOWS_DIR / f"{workflow_id}.json"))


def _read_spec(spec: Any, add) -> Tuple[Dict[str, Dict[str, Any]], List[Any], str]:
    """Shape checks; returns (nodes, connections as ((src, port), (dst, port)), name)."""
    if not isinstance(spec, dict):
        add("error", "spec_invalid", "The spec must be a JSON object")
        return {}, [], ""
    if spec.get("format") != FORMAT:
        add("error", "spec_invalid", f"\"format\" must be {FORMAT!r}")
    name = spec.get("name")
    if not isinstance(name, str) or not name.strip():
        add("error", "spec_invalid", "\"name\" must be a non-empty string")
        name = ""
    nodes = spec.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        add("error", "spec_invalid", "\"nodes\" must be a non-empty object of handle -> node")
        nodes = {}
    for handle, node in nodes.items():
        if not HANDLE_PATTERN.match(str(handle)):
            add("error", "bad_handle",
                f"Handle {handle!r}: use lowercase letters, digits and _, starting with a letter", str(handle))
        if not isinstance(node, dict) or not isinstance(node.get("type"), str):
            add("error", "spec_invalid", f"Node {handle!r} needs a \"type\"", str(handle))
            continue
        if "config" in node and not isinstance(node["config"], dict):
            add("error", "spec_invalid", f"Node {handle!r}: \"config\" must be an object", str(handle))
        if "alias" in node and not isinstance(node["alias"], str):
            add("error", "spec_invalid", f"Node {handle!r}: \"alias\" must be a string", str(handle))
        unknown = sorted(set(node) - {"type", "alias", "config"})
        if unknown:
            add("error", "spec_invalid", f"Node {handle!r}: unknown keys {unknown}", str(handle))
    connections = []
    raw_connections = spec.get("connections", [])
    if not isinstance(raw_connections, list):
        add("error", "spec_invalid", "\"connections\" must be a list")
        raw_connections = []
    for index, raw in enumerate(raw_connections):
        ends = []
        for side in ("from", "to"):
            value = raw.get(side) if isinstance(raw, dict) else None
            handle, _, port = str(value or "").partition(".")
            if not handle or not port:
                add("error", "spec_invalid",
                    f"Connection {index + 1}: \"{side}\" must be \"handle.port\" (got {value!r})")
            elif handle not in nodes:
                add("error", "spec_invalid", f"Connection {index + 1}: no node with handle {handle!r}")
            ends.append((handle, port))
        connections.append(tuple(ends))
    return nodes, connections, str(name).strip()


def _checked_config(meta: Dict[str, Any], overrides: Dict[str, Any], handle: str, add) -> Dict[str, Any]:
    """Defaults with ``overrides`` merged in; unknown keys and bad numbers reported."""
    defaults = dict(meta.get("default_config") or {})
    schema = dict(meta.get("config_schema") or {})
    known = set(defaults) | set(schema) | STANDARD_KEYS | set(meta.get("custom_config_keys") or {})
    for key in sorted(set(overrides) - known):
        add("error", "unknown_config_key",
            f"{handle}: unknown config key {key!r} for {meta['type']} (see: aotn describe {meta['type']})",
            handle)
    config = {**deepcopy(defaults), **deepcopy(overrides)}
    for key, info in number_fields(schema):
        if key in overrides:
            value, problem = check_number(info, overrides[key], defaults.get(key))
            if problem:
                add("error", "invalid_number", f"{handle}.{key}: {problem} (got {overrides[key]!r})", handle)
            else:
                config[key] = value
    return config


def _translated_references(value: Any, ids: Dict[str, str], handle: str, field: str, add) -> str:
    """Handles (list or comma-separated) to generated node ids."""
    items = value if isinstance(value, list) else str(value or "").replace("\n", ",").split(",")
    translated = []
    for item in (str(item).strip() for item in items):
        if not item:
            continue
        if item not in ids:
            add("error", "unknown_reference", f"{handle}.{field}: no node with handle {item!r}", handle)
            continue
        translated.append(ids[item])
    return ", ".join(translated)


def _add_validation(workflow_map: WorkflowMap, factory: NodeFactory, handles: Dict[str, str],
                    add, diagnostics: List[Dict[str, Any]]) -> None:
    """Validator issues as diagnostics (a bad number the spec check already
    reported for a node is not repeated)."""
    reported = {(d["code"], d["node"]) for d in diagnostics if d["code"] == "invalid_number"}
    result = validate_workflow(workflow_map, factory)
    for level, issues in (("error", result["errors"]), ("warning", result["warnings"])):
        for issue in issues:
            code = str(issue.get("code") or "validation")
            handle = handles.get(str(issue.get("node_id") or ""))
            if (code, handle) in reported:
                continue
            # A spec that wires one output twice is a mistake, not a choice.
            if code in BUILD_ERROR_CODES:
                level = "error"
            add(level, code, str(issue.get("message") or ""), handle)


def _reload_problem(factory: NodeFactory, workflow_id: str, built: WorkflowMap) -> str:
    """Reload the saved file into a fresh map; "" when it matches the build."""
    data = persistence.load_workflow(workflow_id)
    if data is None:
        return "The saved file could not be read back"
    fresh = WorkflowMap(factory, EventBus())
    fresh.load_data(data)
    before = built.get_all_node_data()
    after = fresh.get_all_node_data()
    if set(before) != set(after):
        return "Reloaded node ids differ from the built workflow"
    for node_id, node in before.items():
        other = after[node_id]
        for key in ("type", "alias", "config", "connections"):
            if node.get(key) != other.get(key):
                return f"Reloaded {key} of {node_id} differs from the built workflow"
    issues = lambda result: sorted(  # noqa: E731
        (str(i.get("code")), str(i.get("node_id"))) for i in result["errors"] + result["warnings"])
    if issues(validate_workflow(fresh, factory)) != issues(validate_workflow(built, factory)):
        return "The reloaded workflow validates differently from the built one"
    return ""


# --- inspect ------------------------------------------------------------------------------

#: The most nodes the readable execution outline walks before stopping.
OUTLINE_LIMIT = 400


def inspect_workflow(factory: NodeFactory, workflow_map: WorkflowMap) -> Dict[str, Any]:
    """Explain a loaded workflow the way the engine will run it.

    - ``execution``: an outline from Start. An ordinary output follows its
      first connection; a branching node (Parallel Branch) splits into parallel
      paths; a node with several used outputs (Conditional, Error Mux routes)
      takes one of them at run time; ``error`` connections run on failure.
    - ``vault``: per key, its writers and readers, and for each reader
      "before" only when every path from Start to it passes a writer;
      otherwise "not guaranteed" (a path skips every writer, or writers run
      on a parallel path), "no writer", "its own key" or "not reached".
      Wait Until synchronisation is not counted as a guarantee.
    - ``data_flow``: each Upstream connection, the types its producers can
      send, and "ok", "ok (accepts any)", "mismatch", or "unchecked"
      (the port wants a specific type but a sender's type is undeclared).
    - ``unchecked``: config keys the contract cannot check (no schema).
    - ``nodes``: id, name, type and the config keys changed from defaults.
    - ``validation``: the validator's issues with their codes.
    """
    nodes = workflow_map.get_all_node_data()
    meta_by_type = {m["type"]: m for m in factory.get_node_types_metadata()}

    def plain_name(node_id: str) -> str:
        node = nodes.get(node_id) or {}
        meta = meta_by_type.get(str(node.get("type") or "")) or {}
        alias = str(node.get("alias") or "").strip()
        type_name = str(meta.get("display_name") or node.get("type") or "?")
        return f"{alias} ({type_name})" if alias and alias != type_name else type_name

    counts: Dict[str, int] = {}
    for node_id in nodes:
        counts[plain_name(node_id)] = counts.get(plain_name(node_id), 0) + 1

    def name(node_id: str) -> str:
        """Display name; nodes sharing one get their id's tail (#a3f2)."""
        plain = plain_name(node_id)
        return f"{plain} #{node_id[-4:]}" if counts.get(plain, 0) > 1 else plain

    summary = []
    unchecked = []
    for node_id, node in nodes.items():
        meta = meta_by_type.get(str(node.get("type") or "")) or {}
        defaults = meta.get("default_config") or {}
        schema = meta.get("config_schema") or {}
        config = node.get("config") or {}
        summary.append({
            "id": node_id, "name": name(node_id), "type": node.get("type"),
            "changed": {k: v for k, v in config.items() if defaults.get(k, object()) != v},
        })
        loose = sorted(k for k in config if k not in schema and k not in STANDARD_KEYS
                       and (k in defaults or k in (meta.get("custom_config_keys") or {})))
        if loose:
            unchecked.append({"node": node_id, "name": name(node_id), "keys": loose})

    execution = _execution_outline(factory, nodes, meta_by_type, name)
    vault = _vault_report(factory, nodes, meta_by_type, name)
    data_flow = _data_flow_report(factory, nodes, name)
    result = validate_workflow(workflow_map, factory)
    validation = [
        {"level": level, "code": issue.get("code"), "node": issue.get("node_id"),
         "name": name(str(issue.get("node_id") or "")) if issue.get("node_id") in nodes else None,
         "message": issue.get("message")}
        for level, issues in (("error", result["errors"]), ("warning", result["warnings"]))
        for issue in issues
    ]
    return {
        "workflow_id": workflow_map.workflow_id, "name": workflow_map.workflow_name,
        "nodes": summary, "execution": execution, "vault": vault,
        "data_flow": data_flow, "unchecked": unchecked, "validation": validation,
    }


def _execution_outline(factory, nodes, meta_by_type, name) -> List[str]:
    starts = [node_id for node_id, node in nodes.items() if node.get("type") == "start_node"]
    if not starts:
        return ["No Start node: nothing runs."]
    lines: List[str] = []
    printed: set = set()

    def outputs_by_port(node_id):
        """Connections grouped by output port, active ports in port order."""
        node = nodes.get(node_id) or {}
        # Some types list `error` themselves (HTTP Request): keep it once.
        order = list(dict.fromkeys(list(factory.node_output_ports(node)) + [ERROR_PORT]))
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for conn in node.get("connections", {}).get("outputs", []):
            grouped.setdefault(str(conn.get("source_port") or "default"), []).append(conn)
        return [(port, grouped[port]) for port in order if port in grouped]

    def hidden_connections(node_id):
        """Connections on outputs this node's config does not have."""
        node = nodes.get(node_id) or {}
        active = set(factory.node_output_ports(node)) | {ERROR_PORT}
        return [c for c in node.get("connections", {}).get("outputs", [])
                if str(c.get("source_port") or "default") not in active]

    def walk(node_id: str, indent: str, on_path: tuple) -> None:
        while node_id:
            if len(printed) >= OUTLINE_LIMIT:
                lines.append(f"{indent}... (outline stops at {OUTLINE_LIMIT} nodes)")
                return
            if node_id in on_path:
                lines.append(f"{indent}-> back to {name(node_id)} (loop)")
                return
            if node_id in printed:
                lines.append(f"{indent}-> {name(node_id)} (continues as shown above)")
                return
            printed.add(node_id)
            on_path = on_path + (node_id,)
            node = nodes.get(node_id) or {}
            node_type = str(node.get("type") or "")
            extra = ""
            if node_type == "wait_until_node":
                targets = _wait_targets((node.get("config") or {}).get("target_node_ids"))
                extra = f"; waits for {', '.join(name(t) for t in targets) or 'nothing'}"
            lines.append(f"{indent}{name(node_id)}{extra}")
            for conn in hidden_connections(node_id):
                lines.append(f"{indent}  ({conn.get('source_port')} -> {name(str(conn.get('target_node_id')))}: "
                             f"hidden output, never runs)")
            ports = outputs_by_port(node_id)
            errors = [c for p, conns in ports if p == ERROR_PORT for c in conns]
            normal = [(p, conns) for p, conns in ports if p != ERROR_PORT]
            for conn in errors:
                lines.append(f"{indent}  on error ->")
                walk(str(conn.get("target_node_id") or ""), indent + "    ", on_path)
            for port, conns in normal:
                for ignored in conns[1:]:
                    lines.append(f"{indent}  ({port} -> {name(str(ignored.get('target_node_id')))}: never runs; only the first connection does)")
            if not normal:
                return
            if factory.spawns_branches(node_type) and len(normal) > 1:
                lines.append(f"{indent}  splits into {len(normal)} parallel paths:")
                for port, conns in normal:
                    lines.append(f"{indent}    [{port}]")
                    walk(str(conns[0].get("target_node_id") or ""), indent + "      ", on_path)
                return
            if len(normal) > 1:
                lines.append(f"{indent}  takes one of:")
                for port, conns in normal:
                    lines.append(f"{indent}    [{port}]")
                    walk(str(conns[0].get("target_node_id") or ""), indent + "      ", on_path)
                return
            port, conns = normal[0]
            node_id = str(conns[0].get("target_node_id") or "")
            if port != "default":
                lines.append(f"{indent}  [{port}]")

    for start in starts:
        walk(start, "", ())
    loose = [node_id for node_id in nodes if node_id not in printed]
    if loose:
        lines.append("Not reached from Start: " + ", ".join(name(n) for n in loose))
    return lines


def _wait_targets(raw: Any) -> List[str]:
    """Wait Until targets, saved as a list (the editor) or a comma string."""
    items = raw if isinstance(raw, list) else str(raw or "").replace("\n", ",").split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def _reachable(factory, nodes, starts, blocked=frozenset()) -> set:
    """Nodes reachable from ``starts`` over active outputs (any port may
    fire), never continuing past a node in ``blocked``."""
    seen: set = set()
    stack = list(starts)
    while stack:
        node_id = stack.pop()
        if node_id in seen or node_id not in nodes:
            continue
        seen.add(node_id)
        if node_id in blocked:
            continue
        node = nodes[node_id]
        active = set(factory.node_output_ports(node)) | {ERROR_PORT}
        for conn in node.get("connections", {}).get("outputs", []):
            if str(conn.get("source_port") or "default") in active:
                stack.append(str(conn.get("target_node_id") or ""))
    return seen


def _vault_report(factory, nodes, meta_by_type, name) -> List[Dict[str, Any]]:
    reverse = _build_reverse_adjacency(nodes)
    starts = [node_id for node_id, node in nodes.items() if node.get("type") == "start_node"]
    reached = _reachable(factory, nodes, starts)
    readers: Dict[str, List[Dict[str, Any]]] = {}
    for node_id, node in nodes.items():
        node_type = str(node.get("type") or "")
        config = node.get("config") or {}
        for entry in vault_read_entries(node_type, config, resolved_metadata(factory, node_type, config)):
            readers.setdefault(entry["source_id"], []).append({"node": node_id, "required": entry["required"]})
    keys = set(readers)
    for node_id, node in nodes.items():
        node_type = str(node.get("type") or "")
        config = node.get("config") or {}
        keys |= set(typed_vault_writes(node_type, config, resolved_metadata(factory, node_type, config)))
        for entry in config.get("membank_outputs") or []:
            key = entry if isinstance(entry, str) else (entry.get("source_id") or entry.get("id") or entry.get("output")
                                                         if isinstance(entry, dict) else None)
            if key:
                keys.add(str(key))
    report = []
    for key in sorted(keys):
        writers = _vault_writers(nodes, factory, key)
        writer_ids = {w for w, _ in writers}
        reads = []
        # "before" only when proven: every path from Start to the reader
        # passes a writer (PR 63 review). Anything else is uncertain.
        around_writers = _reachable(factory, nodes, starts, frozenset(writer_ids))
        for reader in readers.get(key, []):
            ancestors = _build_ancestor_set(reader["node"], nodes, reverse)
            if not writer_ids:
                order = "no writer"
            elif reader["node"] in writer_ids:
                order = "its own key (the first visit reads the fallback)"
            elif reader["node"] not in reached:
                order = "not reached from Start"
            elif reader["node"] not in around_writers:
                order = "before"
            elif writer_ids & ancestors:
                order = "not guaranteed (a path reaches it without passing a writer)"
            else:
                order = "not guaranteed (writers on a parallel path)"
            reads.append({"node": reader["node"], "name": name(reader["node"]),
                          "required": reader["required"], "order": order})
        report.append({
            "key": key,
            "writers": [{"node": w, "name": name(w), "data_type": t} for w, t in writers],
            "readers": reads,
        })
    return report


def _data_flow_report(factory, nodes, name) -> List[Dict[str, Any]]:
    from .port_types import input_port_type
    from .validator import _standard_source_active

    report = []
    for node_id, node in nodes.items():
        config = node.get("config") or {}
        for conn in node.get("connections", {}).get("inputs", []):
            source = str(conn.get("source_node_id") or "")
            port = str(conn.get("target_port") or "default")
            if source not in nodes:
                continue
            active = _standard_source_active(config, port, "Upstream payload")
            wanted = input_port_type(factory, node, port)
            producers = trace_producers(nodes, factory, source, str(conn.get("source_port") or "default"))
            types = sorted({t for _, t in producers}) or ["any"]
            if not active:
                status = "not used (source is not Upstream payload)"
            elif wanted == "any":
                status = "ok (accepts any)"
            elif any(not types_compatible(t, wanted) for t in types if t != "any"):
                status = "mismatch"
            elif "any" in types:
                # The port wants a specific type; the sender's is not declared.
                status = "unchecked"
            else:
                status = "ok"
            report.append({"from": source, "from_name": name(source), "to": node_id, "to_name": name(node_id),
                           "port": port, "expects": wanted, "sends": types, "status": status})
    return report

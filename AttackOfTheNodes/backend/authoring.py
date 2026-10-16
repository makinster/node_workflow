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
from .port_types import metadata_for_type, port_metadata, resolved_metadata
from .save_manager import SaveManager
from .validator import validate_workflow
from .vault_declarations import typed_vault_writes, vault_read_entries
from .workflow_map import WorkflowMap

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
        "unchecked_keys": sorted(set(defaults) - set(schema)),
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

    # Case-insensitive, like `aotn run <name>` resolves names.
    if any(str(entry.get("name") or "").casefold() == name.casefold()
           for entry in persistence.list_workflows()):
        add("error", "duplicate_name", f"A saved workflow is already named {name!r}; choose another name")
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
    known = set(defaults) | set(schema) | STANDARD_KEYS
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

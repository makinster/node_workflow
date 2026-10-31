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
from .flow_behaviors import parse_targets
from .vault_declarations import typed_vault_writes, vault_read_entries
from .node_capabilities import STANDARD_FLAGS, supported_standard_flags
from .workflow_map import WorkflowMap
from .workflow_names import name_problem, name_taken

FORMAT = "aotn-workflow/1"
INPUT_ARRIVAL_NOTE = (
    "Ordinary inputs may have several incoming connections. Each arriving path runs the node "
    "separately with that path’s payload; this is not a join/wait. Shared End is normal. "
    "Special join nodes have their own rules."
)
HANDLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")

# Fixed format guidance shared by CLI diagnostics and the persistence-safe node
# report. Keys and type names are selected internally, never from spec values.
SPEC_SHAPE_MESSAGES = {
    "spec": 'spec: expected a JSON object. Example: {"format": "aotn-workflow/1", "name": "Example", "nodes": {...}}.',
    "format": 'format: expected "aotn-workflow/1". Example: {"format": "aotn-workflow/1"}.',
    "name": 'name: expected a non-empty string. Example: {"name": "Example"}.',
    "nodes": 'nodes: expected a non-empty object keyed by handle or a list of objects with id (or handle). Example: {"read": {"type": "<type>"}}.',
    "node": 'node: expected an object with a string type. Example: {"type": "<type>"}.',
    "type": 'type: expected a string naming a registered type. Example: {"type": "<type>"}.',
    "config": 'config: expected an object of configuration fields. Example: {"config": {}}.',
    "alias": 'alias: expected a string. Example: {"alias": "Read"}.',
    "node_fields": 'node: expected only type, alias and config (plus id or handle in list form). Example: {"type": "<type>", "config": {}}.',
    "handle": 'handle: expected 1–40 lowercase letters, digits or underscores, starting with a letter. Example: "read_notes".',
    "id_missing": 'nodes: id is required on each list item (handle also works). Example: {"id": "read", "type": "<type>"}.',
    "id_invalid": 'nodes: id must be a handle of 1–40 lowercase letters, digits or underscores, starting with a letter (handle also works as the key). Example: {"id": "read_notes", "type": "<type>"}.',
    "id_duplicate": 'nodes: duplicate id; give every list item a unique id. Example: [{"id": "first", "type": "<type>"}, {"id": "second", "type": "<type>"}].',
    "id_conflict": 'nodes: a list item has different id and handle; give one name. Example: {"id": "read", "type": "<type>"}.',
    "list_mixed": 'nodes: mixed keyed entries and list items are not allowed; each list item needs id and type. Example: [{"id": "read", "type": "<type>"}].',
    "list_item": 'nodes: each item must be an object with id and type. Example: [{"id": "read", "type": "<type>"}].',
    "connections": 'connections: expected a list of connection objects. Example: [{"from": "first.default", "to": "second.input"}].',
    "connection": 'connection: expected an object with from and to. Example: {"from": "first.default", "to": "second.input"}.',
    "endpoint": 'connection endpoint: expected a string "handle.port". Example: {"from": "first.default", "to": "second.input"}.',
    "endpoint_handle": 'connection endpoint: expected a handle declared in nodes. Example: nodes {"first": {...}} with "from": "first.default".',
    "callable": 'callable: expected true or false. Example: {"callable": false}.',
}
_JSON_TYPES = ("null", "a boolean", "a string", "an object", "a list", "a number", "an unsupported value")
ID_KEYS = ("id", "handle")
# The value's type says nothing useful when the problem is a repeat or clash.
_NO_GOT = frozenset({"id_duplicate", "id_conflict"})


def _json_type(value):
    if value is None:
        return "null"
    for cls, name in ((bool, "a boolean"), (str, "a string"), (dict, "an object"),
                      (list, "a list"), ((int, float), "a number")):
        if isinstance(value, cls):
            return name
    return "an unsupported value"


def spec_shape_message(diagnostic):
    """Render only whitelisted templates and JSON type names, never raw values."""
    message = SPEC_SHAPE_MESSAGES.get(diagnostic.get("hint"), SPEC_SHAPE_MESSAGES["spec"])
    got = diagnostic.get("got")
    if got in _JSON_TYPES and diagnostic.get("hint") not in _NO_GOT:
        message = message.replace(". Example:", "; got " + got + ". Example:", 1)
    return message


def _shape_error(add, hint, value, *, field=None, node=None, code="spec_invalid"):
    diagnostic = dict(hint=hint, got=_json_type(value))
    add("error", code, spec_shape_message(diagnostic), node=node, field=field, **diagnostic)


def normalize_spec(spec):
    """Losslessly convert list nodes to keyed nodes; never mutate the input.

    Reject the entire list on ambiguous identity, before any graph checks.
    The id is list syntax, not a node field; all other fields are preserved so
    ordinary shape/metadata validation can reject unsupported fields itself.
    """
    if not isinstance(spec, dict) or not isinstance(spec.get("nodes"), list):
        return spec, []
    diagnostics = []

    def add(level, code, message, **location):
        diagnostics.append(dict(level=level, code=code, message=message, **location))

    nodes = {}
    for index, item in enumerate(spec["nodes"]):
        field = f"nodes[{index}]"
        if not isinstance(item, dict):
            _shape_error(add, "list_item", item, field=field)
            continue
        # Drafts name list items with "handle" as often as "id"; both mean the
        # keyed handle. Two different names for one node are ambiguous.
        names = [key for key in ID_KEYS if key in item]
        if not names:
            keyed = any(key not in {"type", "alias", "config"} and isinstance(value, dict)
                        for key, value in item.items())
            _shape_error(add, "list_mixed" if keyed else "id_missing", item, field=field)
            continue
        if len(names) > 1 and item["id"] != item["handle"]:
            _shape_error(add, "id_conflict", item, field=field)
            continue
        key = names[0]
        handle = item[key]
        if not isinstance(handle, str) or not HANDLE_PATTERN.fullmatch(handle):
            _shape_error(add, "id_invalid", handle, field=f"{field}.{key}")
            continue
        if handle in nodes:
            _shape_error(add, "id_duplicate", handle, field=f"{field}.{key}")
            continue
        nodes[handle] = {k: value for k, value in item.items() if k not in ID_KEYS}
    if diagnostics:
        return spec, diagnostics
    return {**spec, "nodes": nodes}, []


#: Types an author never places directly.
HIDDEN_TYPES = frozenset({"tombstone_node"})

#: Retained shared config keys; acceptance alone is not runtime support.
#: Validation warns for unsupported Vault result writes.
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
    "unsupported_standard_flag": "An explicit standard flag has no supported runtime behavior on this node.",
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
        "execution_contract": deepcopy(meta.get("execution_contract") or {}),
        "node_metadata": deepcopy(meta.get("node_metadata")),
        "config": config,
        "fields": fields,
        "unchecked_keys": sorted((set(defaults) - set(schema)) | set(meta.get("custom_config_keys") or {})),
        "custom_keys": dict(meta.get("custom_config_keys") or {}),
        "standard_keys": sorted((STANDARD_KEYS - STANDARD_FLAGS) | supported_standard_flags(meta, config)),
        "standard_flags": sorted(supported_standard_flags(meta, config)),
        "standard_key_docs": deepcopy(meta.get("standard_key_docs") or {}),
        "node_reference_fields": list(NODE_REFERENCE_FIELDS.get(node_type, ())),
        "inputs": inputs,
        "input_routing": INPUT_ARRIVAL_NOTE,
        "outputs": outputs,
        "vault_reads": vault_read_entries(node_type, config, resolved),
        "vault_writes": [
            {"key": key, "data_type": tag or "any"}
            for key, tag in typed_vault_writes(node_type, config, resolved).items()
        ],
        "errors": list(meta.get("errors") or []),
    }


# --- build -----------------------------------------------------------------------------


def check_workflow_spec(factory: NodeFactory, spec: Any) -> Dict[str, Any]:
    """The authoring verdict only: no saves, execution or active-map edits.

    Ephemeral ids in this low-level report are check internals, not library ids.
    The workflow node returns the parsed input spec instead of these internals.
    """
    report, _ = _checked_graph(factory, spec)
    return report


def build_workflow(factory: NodeFactory, spec: Any, *, write: bool = True) -> Dict[str, Any]:
    """Shared check, then optionally save/reload a new workflow. Never execute."""
    report, workflow_map = _checked_graph(factory, spec)
    if not report["ok"] or not write:
        return report
    name = report["name"]
    diagnostics = report["diagnostics"]

    def failed(code, message):
        diagnostics.append(dict(level="error", code=code, node=None, field=None, message=message))
        return dict(ok=False, format=FORMAT, diagnostics=diagnostics)

    callable_ = bool(workflow_map.callable)
    if name_taken(name, callable_=callable_):
        return failed("duplicate_name", f"A saved workflow is already named {name!r}; choose another name")
    problem = name_problem(name, callable_=callable_)
    if problem:
        return failed("name_invalid", problem)
    workflow_id = workflow_map.workflow_id
    SaveManager(workflow_map).save_current_workflow()
    problem = _reload_problem(factory, workflow_id, workflow_map)
    if problem:
        persistence.delete_workflow(workflow_id)
        return failed("reload_mismatch", problem)
    return {**report, "path": str(persistence.WORKFLOWS_DIR / f"{workflow_id}.json")}


def _checked_graph(factory: NodeFactory, spec: Any):
    """One validation path shared by CLI checks, saving builds and the node."""
    diagnostics: List[Dict[str, Any]] = []

    def report(ok: bool, **extra: Any) -> Dict[str, Any]:
        return {"ok": ok, "format": FORMAT, "diagnostics": diagnostics, **extra}

    def add(level: str, code: str, message: str, node: Optional[str] = None, field: Optional[str] = None, **guidance) -> None:
        diagnostics.append({"level": level, "code": code, "node": node, "field": field, "message": message, **guidance})

    spec, normalization_errors = normalize_spec(spec)
    if normalization_errors:
        diagnostics.extend(normalization_errors)
        return report(False), None
    nodes_spec, connections, name = _read_spec(spec, add)
    # Only a spec that cannot be walked stops here; otherwise every problem
    # is collected so one build lists them all.
    if not nodes_spec:
        return report(False), None
    nodes_spec = {handle: node for handle, node in nodes_spec.items()
                  if isinstance(node, dict) and isinstance(node.get("type"), str)}

    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new(name)
    if "callable" in spec:
        # Step 4 (C27): a callable workflow can be run as a subworkflow.
        if isinstance(spec["callable"], bool):
            workflow_map.set_callable(spec["callable"])
        else:
            _shape_error(add, "callable", spec["callable"], field="callable")
    ids: Dict[str, str] = {}
    configs: Dict[str, Dict[str, Any]] = {}
    for handle, node_spec in nodes_spec.items():
        node_type = node_spec["type"]
        meta = metadata_for_type(factory, node_type)
        if meta is None or node_type in HIDDEN_TYPES:
            add("error", "unknown_node_type", f"Unknown node type: {node_type}", handle, "type")
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
            add("error", "duplicate_connection", f"{where} is listed twice", field=f"connections[{index}]")
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
                f"{where}: {source} has no output '{source_port}' (has: {', '.join(outputs)})", source, f"connections[{index}].from")
            continue
        if target_port not in inputs:
            add("error", "unknown_port",
                f"{where}: {target} has no input '{target_port}' (has: {', '.join(inputs) or 'none'})", target, f"connections[{index}].to")
            continue
        workflow_map.connect(ids[source], source_port, ids[target], target_port)

    handles = {node_id: handle for handle, node_id in ids.items()}
    _add_validation(workflow_map, factory, handles, add, diagnostics)
    if any(d["level"] == "error" for d in diagnostics):
        return report(False), None
    return report(True, workflow_id=workflow_map.workflow_id, name=name, nodes=ids), workflow_map


def _read_spec(spec: Any, add) -> Tuple[Dict[str, Dict[str, Any]], List[Any], str]:
    """Format checks only; node knowledge stays in factory metadata."""
    if not isinstance(spec, dict):
        _shape_error(add, "spec", spec)
        return {}, [], ""
    if spec.get("format") != FORMAT:
        _shape_error(add, "format", spec.get("format"), field="format")
    name = spec.get("name")
    if not isinstance(name, str) or not name.strip():
        _shape_error(add, "name", name, field="name")
        name = ""
    nodes = spec.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        _shape_error(add, "nodes", nodes, field="nodes")
        # Endpoints cannot be resolved without a usable node table.
        return {}, [], name.strip()
    for handle, node in nodes.items():
        if not isinstance(handle, str) or not HANDLE_PATTERN.fullmatch(handle):
            _shape_error(add, "handle", handle, node=str(handle), field="handle", code="bad_handle")
        if not isinstance(node, dict):
            _shape_error(add, "node", node, node=str(handle), field="node")
            continue
        if not isinstance(node.get("type"), str):
            _shape_error(add, "type", node.get("type"), node=str(handle), field="type")
            continue
        if "config" in node and not isinstance(node["config"], dict):
            _shape_error(add, "config", node["config"], node=str(handle), field="config")
        if "alias" in node and not isinstance(node["alias"], str):
            _shape_error(add, "alias", node["alias"], node=str(handle), field="alias")
        if set(node) - {"type", "alias", "config"}:
            _shape_error(add, "node_fields", node, node=str(handle), field="node")
    connections = []
    raw_connections = spec.get("connections", [])
    if not isinstance(raw_connections, list):
        _shape_error(add, "connections", raw_connections, field="connections")
        raw_connections = []
    for index, raw in enumerate(raw_connections):
        if not isinstance(raw, dict):
            _shape_error(add, "connection", raw, field=f"connections[{index}]")
            continue
        ends = []
        for side in ("from", "to"):
            value = raw.get(side)
            handle, _, port = value.partition(".") if isinstance(value, str) else ("", "", "")
            if not handle or not port:
                _shape_error(add, "endpoint", value, field=f"connections[{index}].{side}")
            elif handle not in nodes:
                _shape_error(add, "endpoint_handle", value, field=f"connections[{index}].{side}")
            ends.append((handle, port))
        connections.append(tuple(ends))
    return nodes, connections, name.strip()


def _checked_config(meta: Dict[str, Any], overrides: Dict[str, Any], handle: str, add) -> Dict[str, Any]:
    """Defaults with ``overrides`` merged in; unknown keys and bad numbers reported."""
    defaults = dict(meta.get("default_config") or {})
    schema = dict(meta.get("config_schema") or {})
    known = set(defaults) | set(schema) | STANDARD_KEYS | set(meta.get("custom_config_keys") or {})
    for key in sorted(set(overrides) - known):
        add("error", "unknown_config_key",
            f"{handle}: unknown config key {key!r} for {meta['type']} (see: aotn describe {meta['type']})",
            handle, f"config.{key}")
    config = {**deepcopy(defaults), **deepcopy(overrides)}
    supported = supported_standard_flags(meta, config)
    for flag in sorted((set(overrides) & STANDARD_FLAGS) - supported):
        add("error", "unsupported_standard_flag",
            f"{handle}: {meta['type']} cannot honour {flag}; remove this unsupported option "
            "(explicit false/empty values are also rejected)", handle, f"config.{flag}")
    for key, info in number_fields(schema):
        if key in overrides:
            value, problem = check_number(info, overrides[key], defaults.get(key))
            if problem:
                add("error", "invalid_number", f"{handle}.{key}: {problem} (got {overrides[key]!r})", handle, f"config.{key}")
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
            add("error", "unknown_reference", f"{handle}.{field}: no node with handle {item!r}", handle, f"config.{field}")
            continue
        translated.append(ids[item])
    return ", ".join(translated)


def _add_validation(workflow_map: WorkflowMap, factory: NodeFactory, handles: Dict[str, str],
                    add, diagnostics: List[Dict[str, Any]]) -> None:
    """Validator issues as diagnostics (a bad number the spec check already
    reported for a node is not repeated)."""
    reported = {(d["code"], d["node"]) for d in diagnostics if d["code"] == "invalid_number"}
    result = validate_workflow(workflow_map, factory, draft=True)
    for level, issues in (("error", result["errors"]), ("warning", result["warnings"])):
        for issue in issues:
            code = str(issue.get("code") or "validation")
            handle = handles.get(str(issue.get("node_id") or ""))
            if (code, handle) in reported:
                continue
            # A spec that wires one output twice is a mistake, not a choice.
            if code in BUILD_ERROR_CODES:
                level = "error"
            guidance = {key: issue[key] for key in ("slot", "route", "repair") if issue.get(key)}
            if issue.get("path"):
                guidance["path"] = [handles.get(nid, nid) for nid in issue["path"]]
            add(level, code, str(issue.get("message") or ""), handle, issue.get("field"), **guidance)


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
    return list(parse_targets(raw))


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

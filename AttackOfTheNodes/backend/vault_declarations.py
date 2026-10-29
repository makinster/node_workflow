"""Portable declarations for the Vault values nodes actually publish and read.

One model for "which Vault keys does this node read / write, given its
config", shared by the validator and the editor's Connections tab so they
cannot drift apart. Activation rules (a hidden repeatable slot, a stale
continuation key) are applied here.
"""

from typing import Any
from string import Formatter

from .branch_paths import branch_count_from_config, path_ports

# Prompt-source label that resumes an AI session; mirrors
# backend/nodes/chat_completion_node.CONTINUE_SESSION_SOURCE.
CONTINUE_SESSION_SOURCE = "Continue AI session"


def supports_standard_vault_write(node_type: str, config: dict[str, Any], metadata: dict[str, Any]) -> bool:
    """Standard result routing exists only on outputs declaring Vault support.

    Start's explicit rows route individually; its legacy result switch is ignored
    in row/no-input mode. Legacy named writes remain separate below.
    """
    if node_type == "start_node" and (config.get("rows") or config.get("no_inputs")):
        return False
    output = (metadata.get("output_port_metadata") or {}).get("default") or {}
    return "vault" in (output.get("to") or [])


def concat_template_keys(config: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    """Bare format roots read from the Vault, excluding prepared input names.

    Invalid templates belong to the runtime formatter. Inspect nested format
    specs too, up to Python's own two-level formatting limit.
    """
    fields: list[str] = []
    def collect(template: str, depth: int = 0) -> None:
        for _, name, spec, _ in Formatter().parse(template):
            if name is not None:
                root = name.split("[", 1)[0].split(".", 1)[0]
                if root:
                    fields.append(root)
            if spec and depth < 2:
                collect(spec, depth + 1)
    try:
        collect(str(config.get("template", "{input}")))
    except ValueError:
        return []
    inputs = set(metadata.get("input_ports") or []) | {"input"}
    return _unique([key for key in fields if key not in inputs])


def vault_output_fields(metadata: dict[str, Any]) -> dict[str, tuple[str, str, str]]:
    """Config fields for each Vault output; keep the first port's legacy keys."""
    ports = [port for port, info in (metadata.get("output_port_metadata") or {}).items()
             if "vault" in (info.get("to") or [])]
    return {port: (("vault_write", "vault_write_key", "vault_write_description") if index == 0
                   else (f"{port}_vault_write", f"{port}_vault_key", f"{port}_vault_description"))
            for index, port in enumerate(ports)}


def standard_vault_writes(node_type: str, config: dict[str, Any], metadata: dict[str, Any]) -> dict[str, str | None]:
    """Return declared result/session keys without inspecting runtime resources."""
    writes: dict[str, str | None] = {}
    if node_type in {"user_text_input_node", "start_node", "text_output_node"}:
        for key in legacy_output_keys(config):
            writes[key] = "string"
    if node_type == "start_node":
        # Step 4a: each Start row sent to the Vault writes its key, typed.
        from .contracts import sends_to_vault, start_rows, vault_key_for

        for row in start_rows(config):
            if not row.get("_legacy") and sends_to_vault(row) and row["name"]:
                writes[vault_key_for(row)] = row["type"]
    if node_type == "subworkflow_node":
        # The child types belong to its saved contract, not this node's port
        # metadata. Unknown is explicit any; never pretend it is string.
        for row in config.get("results") or []:
            if not isinstance(row, dict) or row.get("to") not in ("Vault", "Both"):
                continue
            name = str(row.get("name") or "").strip()
            if name:
                writes[str(row.get("vault_key") or "").strip() or name] = "any"
    if config.get("vault_write") and supports_standard_vault_write(node_type, config, metadata):
        key = str(config.get("vault_write_key") or "").strip()
        if key:
            output = (metadata.get("output_port_metadata") or {}).get("default") or {}
            writes[key] = str(output.get("data_type") or "") or None
    for port, (enabled, key_field, _) in list(vault_output_fields(metadata).items())[1:]:
        key = str(config.get(key_field) or "").strip()
        if config.get(enabled) and key:
            writes[key] = str(metadata["output_port_metadata"][port].get("data_type") or "") or None
    if node_type == "file_view_node":
        for row in config.get("additional_files") or []:
            if isinstance(row, dict):
                key = str(row.get("vault_key") or "").strip()
                if key:
                    writes[key] = "file"
    if config.get("use_chat_session"):
        key = str(config.get("session_key") or "").strip()
        if key:
            writes[key] = "ai_session"
    return writes


def continuation_selected(config: dict[str, Any]) -> bool:
    """True when the node's continuation key is active.

    Nodes with a prompt-source selector only read the continuation key while
    the Continue AI session mode is selected; a stale hidden value must not
    produce validation noise. Nodes without the selector read it whenever set.
    """
    prompt_source = config.get("prompt_source")
    return prompt_source is None or prompt_source == CONTINUE_SESSION_SOURCE


def repeatable_slot_active(config: dict[str, Any], target_port: str) -> bool:
    """False for numbered repeatable slots hidden by their count selector."""
    group, separator, suffix = str(target_port).rpartition("_")
    if not separator or not suffix.isdigit():
        return True
    count_key = f"{group}_input_count"
    if count_key not in config:
        return True
    try:
        count = int(config.get(count_key) or 0)
    except (TypeError, ValueError):
        count = 0
    return int(suffix) <= count


def standard_vault_reads(config: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Standard-model reads: ``<port>_source == "Vault"`` with a
    ``<port>_vault_key`` (as the port's declared data type), then an active
    ``continue_session_key`` (an ``ai_session``). Entries are
    ``{"source_id", "type_tag", "target_port"}``."""
    port_meta = metadata.get("input_port_metadata") or {}
    entries: list[dict[str, Any]] = []
    for key, value in config.items():
        if not str(key).endswith("_source") or value != "Vault":
            continue
        port = str(key)[: -len("_source")]
        if not repeatable_slot_active(config, port):
            continue
        vault_key = str(config.get(f"{port}_vault_key") or "").strip()
        if not vault_key:
            continue
        data_type = str((port_meta.get(port) or {}).get("data_type") or "") or None
        entries.append({"source_id": vault_key, "type_tag": data_type, "target_port": port})
    # Ordered source rows use the same source/vault_key convention as ports.
    # Their values are declared inputs, never inferred from arbitrary JSON paths.
    for field_name, rows in config.items():
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or row.get("source") != "Vault":
                continue
            key = str(row.get("vault_key") or "").strip()
            if key:
                entries.append({"source_id": key, "type_tag": "any",
                                "target_port": f"{field_name}[{index}]"})
    if continuation_selected(config):
        continue_key = str(config.get("continue_session_key") or "").strip()
        if continue_key:
            entries.append({"source_id": continue_key, "type_tag": "ai_session",
                            "target_port": "continue_session_key"})
    return entries


def config_vault_read_entries(node_type: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Reads named by node-specific config fields (not the standard model).

    Entries are ``{"source_id", "target_port", "required"}``; ``target_port``
    is the config field (or Branch path) that names the key. Every
    node-specific read has a runtime fallback today (Get Variable and Variable
    Reader return their ``default``, Conditional compares against "", Counter
    starts at 0, a Branch seed falls back to the input payload), so each is
    optional: preflight warns when no node writes the key. A read without a
    fallback declares ``required=True`` and is checked like a standard read.
    """
    entries: list[dict[str, Any]] = []

    def add(key: Any, target_port: str, required: bool = False) -> None:
        key = str(key).strip()
        if key:
            entries.append({"source_id": key, "target_port": target_port, "required": required})

    if node_type == "get_variable_node":
        add(config.get("variable_name", "value"), "variable_name")
    elif node_type == "variable_reader_node":
        add(config.get("variable_name") or "", "variable_name")
    elif node_type == "conditional_node" and config.get("left_value_source") == "variable":
        add(config.get("variable_name") or "", "variable_name")
    elif node_type == "counter_node":
        add(config.get("counter_name") or "counter", "counter_name")
    elif node_type == "branch_node":
        sources = config.get("branch_payload_sources") or {}
        if isinstance(sources, dict):
            for port in path_ports(branch_count_from_config(config)):
                source = str(sources.get(port) or "").strip()
                if source.startswith("vault:"):
                    add(source.removeprefix("vault:"), port)
    return entries


def config_vault_reads(node_type: str, config: dict[str, Any]) -> list[str]:
    """Keys of :func:`config_vault_read_entries`."""
    return _unique([entry["source_id"] for entry in config_vault_read_entries(node_type, config)])


def vault_read_entries(node_type: str, config: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Every Vault read with its required/optional flag, in the
    ``{"source_id", "target_port", "required"}`` shape: declared
    ``membank_inputs`` and standard-model reads are required (no fallback;
    a missing writer blocks the run), node-specific reads carry their own
    flag (see :func:`config_vault_read_entries`)."""
    inputs = config.get("membank_inputs") or []
    entries = [
        {"source_id": key, "target_port": "membank_inputs", "required": True}
        for key in (_entry_key(entry).strip() for entry in (inputs if isinstance(inputs, list) else []))
        if key
    ]
    entries += [
        {"source_id": entry["source_id"], "target_port": entry["target_port"], "required": True}
        for entry in standard_vault_reads(config, metadata)
    ]
    entries += config_vault_read_entries(node_type, config)
    return entries


def config_vault_writes(node_type: str, config: dict[str, Any]) -> list[str]:
    """Writes named by node-specific config fields (not in standard_vault_writes)."""
    if node_type == "set_variable_node":
        return _unique([str(config.get("variable_name", "value"))])
    if node_type == "variable_setter_node":
        return _unique([str(config.get("variable_name") or "")])
    if node_type == "counter_node":
        return _unique([str(config.get("counter_name") or "counter")])
    return []


def active_vault_reads(node_type: str, config: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    """Every Vault key the node reads with this config: declared
    ``membank_inputs``, standard-model reads and node-specific fields."""
    return _unique([entry["source_id"] for entry in vault_read_entries(node_type, config, metadata)])


def typed_vault_writes(node_type: str, config: dict[str, Any], metadata: dict[str, Any]) -> dict[str, str | None]:
    """Standard writes with their type tags, plus node-specific writes whose
    type is not known statically (None: unknown, treated as ``any``; a valid
    writer is never dropped because its type is dynamic)."""
    writes = dict(standard_vault_writes(node_type, config, metadata))
    for key in config_vault_writes(node_type, config):
        writes.setdefault(key, None)
    return writes


def active_vault_writes(node_type: str, config: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    """Every Vault key the node writes with this config: declared
    ``membank_outputs``, standard writes and node-specific fields."""
    outputs = config.get("membank_outputs") or []
    keys = [_entry_key(entry) for entry in outputs] if isinstance(outputs, list) else []
    keys += list(typed_vault_writes(node_type, config, metadata))
    return _unique(keys)


def _entry_key(entry: Any) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return str(entry.get("source_id") or entry.get("id") or entry.get("output") or "")
    return ""


def _unique(keys: list[str]) -> list[str]:
    result: list[str] = []
    for key in keys:
        key = str(key).strip()
        if key and key not in result:
            result.append(key)
    return result


def legacy_output_keys(config: dict[str, Any]) -> list[str]:
    """Preserve explicitly named legacy outputs when upgrading a real writer."""
    entries = config.get("membank_outputs") or []
    if not isinstance(entries, list):
        return []
    keys = []
    for entry in entries:
        value = entry if isinstance(entry, str) else (
            entry.get("source_id") or entry.get("output") or entry.get("id") or ""
        ) if isinstance(entry, dict) else ""
        key = str(value).strip()
        if key and key not in keys:
            keys.append(key)
    return keys

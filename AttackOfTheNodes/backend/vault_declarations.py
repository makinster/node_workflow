"""Portable declarations for the Vault values nodes actually publish and read.

One model for "which Vault keys does this node read / write, given its
config", shared by the validator and the editor's Connections tab so they
cannot drift apart. Activation rules (a hidden repeatable slot, a stale
continuation key) are applied here.
"""

from typing import Any

from .branch_paths import branch_count_from_config, path_ports

# Prompt-source label that resumes an AI session; mirrors
# backend/nodes/chat_completion_node.CONTINUE_SESSION_SOURCE.
CONTINUE_SESSION_SOURCE = "Continue AI session"


def standard_vault_writes(node_type: str, config: dict[str, Any], metadata: dict[str, Any]) -> dict[str, str | None]:
    """Return declared result/session keys without inspecting runtime resources."""
    writes: dict[str, str | None] = {}
    if node_type in {"user_text_input_node", "start_node", "text_output_node"}:
        for key in legacy_output_keys(config):
            writes[key] = "string"
    if config.get("vault_write"):
        key = str(config.get("vault_write_key") or "").strip()
        if key:
            output = (metadata.get("output_port_metadata") or {}).get("default") or {}
            writes[key] = str(output.get("data_type") or "") or None
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
    if continuation_selected(config):
        continue_key = str(config.get("continue_session_key") or "").strip()
        if continue_key:
            entries.append({"source_id": continue_key, "type_tag": "ai_session",
                            "target_port": "continue_session_key"})
    return entries


def config_vault_reads(node_type: str, config: dict[str, Any]) -> list[str]:
    """Reads named by node-specific config fields (not the standard model)."""
    keys: list[str] = []
    if node_type == "get_variable_node":
        keys.append(str(config.get("variable_name", "value")))
    elif node_type == "variable_reader_node":
        keys.append(str(config.get("variable_name") or ""))
    elif node_type == "conditional_node" and config.get("left_value_source") == "variable":
        keys.append(str(config.get("variable_name") or ""))
    elif node_type == "counter_node":
        keys.append(str(config.get("counter_name") or "counter"))
    elif node_type == "branch_node":
        sources = config.get("branch_payload_sources") or {}
        if isinstance(sources, dict):
            for port in path_ports(branch_count_from_config(config)):
                source = str(sources.get(port) or "").strip()
                if source.startswith("vault:"):
                    keys.append(source.removeprefix("vault:"))
    return _unique(keys)


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
    inputs = config.get("membank_inputs") or []
    keys = [_entry_key(entry) for entry in inputs] if isinstance(inputs, list) else []
    keys += [entry["source_id"] for entry in standard_vault_reads(config, metadata)]
    keys += config_vault_reads(node_type, config)
    return _unique(keys)


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

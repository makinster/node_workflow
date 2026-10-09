"""Portable declarations for the Vault values nodes actually publish."""

from typing import Any


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

"""Portable, non-destructive upgrades for saved node configurations."""

from copy import deepcopy
from typing import Any


def normalize_node_config(node_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """Return upgraded config, retaining unknown keys and migration evidence.

    File I/O now always continues along its connections. The retired optional
    termination flag is archived, never secretly honored after its UI disappears.
    End nodes explicitly stop paths; unconnected outputs end naturally.
    """
    result = deepcopy(config)
    if node_type in {"file_output_node", "file_view_node"} and "terminate_branch" in result:
        old_value = result.pop("terminate_branch")
        history = result.get("_config_migrations")
        history = dict(history) if isinstance(history, dict) else {}
        history.setdefault("file_io_continuation_v1", {"terminate_branch": old_value})
        result["_config_migrations"] = history

    if node_type == "text_output_node" and "membank_inputs" in result:
        keys = []
        inputs = result.get("membank_inputs")
        for entry in inputs if isinstance(inputs, list) else []:
            key = entry if isinstance(entry, str) else (
                entry.get("source_id") or entry.get("id") or ""
            ) if isinstance(entry, dict) else ""
            key = str(key).strip()
            if key and key not in keys:
                keys.append(key)
        if keys:
            if "input_source" not in result:
                result["input_source"] = "Vault"
                result["input_vault_key"] = keys[0] if len(keys) == 1 else ""
            history = result.get("_config_migrations")
            history = dict(history) if isinstance(history, dict) else {}
            history["text_output_source_v1"] = {"membank_inputs": result.pop("membank_inputs")}
            result["_config_migrations"] = history

    if node_type == "start_node" and "vault_write" not in result:
        outputs = result.get("membank_outputs") or []
        outputs = outputs if isinstance(outputs, list) else []
        valid = [entry for entry in outputs if isinstance(entry, dict)
                 and str(entry.get("output") or entry.get("id") or "").strip()]
        if len(valid) == 1:
            entry = valid[0]
            result["vault_write"] = True
            result["vault_write_key"] = str(entry.get("output") or entry.get("id")).strip()
            result["vault_write_description"] = str(entry.get("description") or "")
            history = result.get("_config_migrations")
            history = dict(history) if isinstance(history, dict) else {}
            history["start_vault_output_v1"] = {"membank_outputs": result.pop("membank_outputs")}
            result["_config_migrations"] = history

    if node_type == "file_reader_node" and "input_source" not in result:
        result["input_source"] = "Configured"

    return result

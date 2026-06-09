"""Frontend helpers for displaying run outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def normalize_outputs(outputs: Iterable[Any]) -> List[Dict[str, Any]]:
    """Return display-ready output records sorted by timestamp/order."""
    records: List[Dict[str, Any]] = []
    for index, item in enumerate(outputs):
        if isinstance(item, dict):
            timestamp = item.get("timestamp") or item.get("time") or ""
            branch_id = item.get("branch_id") or item.get("branch") or "unassigned"
            node_id = item.get("node_id") or item.get("node") or ""
            value = item.get("value", item.get("message", item))
        else:
            timestamp = getattr(item, "timestamp", "")
            branch_id = getattr(item, "branch_id", "unassigned")
            node_id = getattr(item, "node_id", "")
            value = item
        records.append(
            {
                "order": index,
                "timestamp": timestamp,
                "branch_id": branch_id,
                "node_id": node_id,
                "value": value,
            }
        )
    return sorted(records, key=_sort_key)


def format_output_record(record: Dict[str, Any]) -> str:
    """Format one normalized output for terminal display."""
    timestamp = record.get("timestamp") or f"#{record.get('order', 0) + 1}"
    branch = record.get("branch_id") or "unassigned"
    node = f" {record['node_id']}" if record.get("node_id") else ""
    return f"{timestamp} [{branch}{node}] {record.get('value', '')}"


def branch_names(records: Iterable[Dict[str, Any]]) -> list[str]:
    """Return branch names present in normalized records."""
    names = {record.get("branch_id") or "unassigned" for record in records}
    return ["all"] + sorted(names)


def current_timestamp() -> str:
    """Return a stable UTC timestamp string for future structured outputs."""
    return datetime.now(timezone.utc).isoformat()


def _sort_key(record: Dict[str, Any]) -> tuple:
    timestamp = record.get("timestamp") or ""
    return (timestamp == "", timestamp, record.get("order", 0))

"""Output log entry helpers."""

from __future__ import annotations

from datetime import datetime, timezone


class OutputLogEntry(str):
    """String-compatible output entry with display metadata."""

    def __new__(
        cls,
        value: str,
        *,
        branch_id: str = "unassigned",
        node_id: str = "",
        timestamp: str | None = None,
    ):
        obj = str.__new__(cls, value)
        obj.branch_id = branch_id
        obj.node_id = node_id
        obj.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        return obj

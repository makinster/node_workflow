"""
Structured error handling for AttackOfTheNodes.

Errors are cached in memory by run and persisted as JSON records for later
inspection. The handler also publishes count updates for UI badges.
"""

import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .event_bus import EventBus
from .events import ERROR_LOGGED, ERRORS_CLEARED
from .persistence import RUN_ERRORS_DIR, load_json_record, save_json_record


def unhandled_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The records in ``errors`` that no error path handled."""
    return [error for error in errors if not error.get("handled")]


class ErrorHandler:
    """Central structured error logger."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._errors_by_run: Dict[str, List[Dict[str, Any]]] = {}

    def log_error(
        self,
        error: BaseException,
        context: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        code: Optional[str] = None,
        handled: bool = False,
    ) -> Dict[str, Any]:
        """Record, persist, and broadcast a structured error.

        ``handled`` is True when the failure was routed along an error path
        (D7); a run whose errors were all handled still counts as succeeded.
        """
        context = dict(context or {})
        run_id = context.get("run_id") or "unknown_run"
        error_record = {
            "id": f"err_{uuid.uuid4().hex[:10]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category or self.categorize_exception(error),
            "message": str(error),
            "type": type(error).__name__,
            "traceback": "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
            "context": context,
            "run_id": run_id,
            "node_id": context.get("node_id"),
            "branch_id": context.get("branch_id"),
            "code": code,
            "handled": bool(handled),
        }
        errors = self._errors_by_run.setdefault(run_id, self.get_errors_for_run(run_id))
        errors.append(error_record)
        save_json_record(RUN_ERRORS_DIR, run_id, {"run_id": run_id, "errors": errors})
        self._event_bus.publish(
            ERROR_LOGGED,
            {
                "run_id": run_id,
                "error": error_record,
                "error_count": len(errors),
            },
        )
        return error_record

    def get_errors_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Return errors for a run, loading persisted data if needed."""
        if run_id in self._errors_by_run:
            return list(self._errors_by_run[run_id])
        record = load_json_record(RUN_ERRORS_DIR, run_id) or {}
        errors = list(record.get("errors", []))
        self._errors_by_run[run_id] = errors
        return list(errors)

    def snapshot(self, run_id: str, started_at: str):
        """Latest five cached errors only: never lazy-load another run/file."""
        from .run_snapshot import RunErrorSummary, RunSnapshot
        errors = self._errors_by_run.get(run_id, ())
        recent = tuple(RunErrorSummary(
            time=str(record.get("timestamp") or ""),
            node_name=str((record.get("context") or {}).get("node_alias") or record.get("node_id") or ""),
            code=str(record.get("code") or "node_error"),
            handled=bool(record.get("handled")),
            message=str(record.get("message") or ""),
        ) for record in errors[-5:])
        return RunSnapshot(started_at, recent, max(0, len(errors) - 5))

    def get_unhandled_errors_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Errors for a run that were not routed along an error path."""
        return unhandled_errors(self.get_errors_for_run(run_id))

    def finalize_run(self, run_id: str) -> None:
        """Evict in-memory errors for a completed run.

        Call after get_errors_for_run() has already captured errors for the
        history record. Subsequent calls to get_errors_for_run() lazy-load
        from disk.
        """
        self._errors_by_run.pop(run_id, None)

    def clear_errors_for_run(self, run_id: str) -> None:
        """Clear cached/persisted errors for a run."""
        self._errors_by_run[run_id] = []
        save_json_record(RUN_ERRORS_DIR, run_id, {"run_id": run_id, "errors": []})
        self._event_bus.publish(ERRORS_CLEARED, {"run_id": run_id})

    def categorize_exception(self, error: BaseException) -> str:
        """Map exception types to coarse error categories."""
        if isinstance(error, (ConnectionError, TimeoutError)):
            return "NETWORK"
        if isinstance(error, (ValueError, KeyError, TypeError)):
            return "NODE_LOGIC"
        return "UNKNOWN"

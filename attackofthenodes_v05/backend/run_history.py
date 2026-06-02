"""Run history persistence for AttackOfTheNodes."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from .event_bus import EventBus
from .events import RUN_HISTORY_UPDATED
from .persistence import RUN_HISTORY_DIR, list_json_records, save_json_record


class RunHistory:
    """Stores summaries of completed or errored runs."""

    _MAX_IN_MEMORY: int = 500

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        all_runs = sorted(
            list_json_records(RUN_HISTORY_DIR),
            key=lambda item: item.get("started_at", ""),
            reverse=True,
        )
        # Cap in-memory list; full history remains on disk.
        self._runs: List[Dict[str, Any]] = all_runs[:self._MAX_IN_MEMORY]

    def record_run(self, summary: Dict[str, Any]) -> None:
        """Persist a run summary and broadcast history update."""
        run_id = summary["run_id"]
        record = {
            "ended_at": datetime.now(timezone.utc).isoformat(),
            **summary,
        }
        save_json_record(RUN_HISTORY_DIR, run_id, record)
        self._runs = [run for run in self._runs if run.get("run_id") != run_id]
        self._runs.insert(0, record)
        if len(self._runs) > self._MAX_IN_MEMORY:
            self._runs = self._runs[:self._MAX_IN_MEMORY]
        self._event_bus.publish(RUN_HISTORY_UPDATED, {"runs": self.list_runs()})

    def list_runs(self) -> List[Dict[str, Any]]:
        """Return run summaries newest first."""
        return list(self._runs)

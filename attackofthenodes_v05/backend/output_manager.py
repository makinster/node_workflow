"""
Output manager for AttackOfTheNodes.

Collects run outputs in memory and persists finalized outputs by run id. v0.9
keeps compatibility with the existing output_log memory convention while
centralizing output persistence for future output-type nodes.
"""

from typing import Any, Dict, List

from .persistence import RUN_OUTPUTS_DIR, load_json_record, save_json_record


class OutputManager:
    """Collects and persists workflow outputs keyed by run id."""

    def __init__(self) -> None:
        self._outputs_by_run: Dict[str, List[Dict[str, Any]]] = {}

    def clear_run(self, run_id: str) -> None:
        """Clear in-memory outputs for a run."""
        self._outputs_by_run[run_id] = []

    def store_output(self, run_id: str, node_id: str, value: Any) -> None:
        """Store one output item for a run."""
        self._outputs_by_run.setdefault(run_id, []).append(
            {"run_id": run_id, "node_id": node_id, "value": value}
        )

    def store_output_log(self, run_id: str, values: List[Any]) -> None:
        """Store legacy output_log entries as output items."""
        self._outputs_by_run[run_id] = [
            {"run_id": run_id, "node_id": "output_log", "value": value}
            for value in values
        ]

    def finalize_run(self, run_id: str) -> List[Any]:
        """Persist outputs, evict from memory, and return their values."""
        outputs = self._outputs_by_run.pop(run_id, [])
        save_json_record(RUN_OUTPUTS_DIR, run_id, {"run_id": run_id, "outputs": outputs})
        return [item["value"] for item in outputs]

    def get_outputs_for_run(self, run_id: str) -> List[Any]:
        """Return output values for a run from memory or disk."""
        if run_id not in self._outputs_by_run:
            record = load_json_record(RUN_OUTPUTS_DIR, run_id) or {}
            self._outputs_by_run[run_id] = list(record.get("outputs", []))
        return [item["value"] for item in self._outputs_by_run.get(run_id, [])]

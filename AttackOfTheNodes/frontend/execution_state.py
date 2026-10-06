"""Run-scoped execution facts, independent of Textual widgets/navigation."""
from __future__ import annotations

from typing import Any


class ExecutionDisplayState:
    """Retain branches and visits for the current run, including ended paths."""

    def __init__(self) -> None:
        self.reset()

    def reset(self, run_id: str | None = None) -> None:
        self.run_id = run_id
        self.branches: dict[str, dict[str, Any]] = {}

    def accepts(self, payload: dict[str, Any]) -> bool:
        return self.run_id is not None and payload.get("run_id") == self.run_id

    def branch(self, branch_id: str) -> dict[str, Any]:
        return self.branches.setdefault(branch_id, {
            "state": "RUNNING", "depth": 0, "current_node_id": None,
            "parent_branch_id": None, "start_node_id": None, "visits": {},
            "node_statuses": {}, "latest_visits": {},
        })

    def register(self, payload: dict[str, Any]) -> None:
        branch = self.branch(payload["branch_id"])
        for key in ("depth", "parent_branch_id", "start_node_id"):
            branch[key] = payload.get(key)

    def supervisor(self, payload: dict[str, Any], terminated: bool = False) -> None:
        branch = self.branch(payload["branch_id"])
        branch["state"] = payload.get("final_state" if terminated else "state", "")
        branch["current_node_id"] = payload.get("current_node_id")
        branch["node_phase"] = "ended" if terminated else payload.get("node_phase", "queued")
        if terminated:
            branch["stop_requested"] = bool(payload.get("stop_requested"))

    def visit(self, payload: dict[str, Any]) -> dict[str, Any]:
        visits = self.branch(payload["branch_id"])["visits"]
        return visits.setdefault(payload["visit_index"], {
            "node_id": payload["node_id"], "attempts": {}, "seconds": 0.0,
        })

    def node(self, payload: dict[str, Any]) -> None:
        visit = self.visit(payload)
        attempt = visit["attempts"].setdefault(payload["attempt_index"], {})
        attempt["status"] = payload["status"]
        branch = self.branch(payload["branch_id"])
        node_id = payload["node_id"]
        position = (payload["visit_index"], payload["attempt_index"])
        if position >= branch["latest_visits"].get(node_id, (-1, -1)):
            branch["latest_visits"][node_id] = position
            branch["node_statuses"][node_id] = payload["status"]

    def timing(self, payload: dict[str, Any]) -> None:
        if "visit_index" not in payload:
            return
        visit = self.visit(payload)
        seconds = float(payload.get("seconds") or 0.0)
        visit["seconds"] += seconds
        attempt = visit["attempts"].setdefault(payload["attempt_index"], {})
        attempt["seconds"] = attempt.get("seconds", 0.0) + seconds

    def node_statuses(self, branch_id: str | None = None) -> dict[str, str]:
        """Latest visit per branch; active visits win across parallel branches.

        Retried attempts are retained, but only the latest attempt is displayed.
        Terminal precedence across branches: error, stopped, skipped, success.
        """
        by_node: dict[str, list[str]] = {}
        if branch_id is None:
            branches = self.branches.values()
        else:
            branch = self.branches.get(branch_id)
            branches = [branch] if branch is not None else []
        for branch in branches:
            for node_id, status in branch["node_statuses"].items():
                by_node.setdefault(node_id, []).append(status)
        priority = ("running", "waiting", "errored", "stopped", "skipped", "done")
        return {node: next(status for status in priority if status in statuses)
                for node, statuses in by_node.items()}

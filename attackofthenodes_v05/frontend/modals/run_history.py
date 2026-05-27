"""Run history modal."""

import tkinter as tk
from tkinter import ttk
from typing import List

from .common import center_window


class RunHistoryModal(tk.Toplevel):
    """Displays persisted run summaries and outputs."""

    def __init__(self, parent, runs: List[dict]) -> None:
        super().__init__(parent)
        self.title("Run History")
        self.transient(parent)
        self.geometry("760x420")
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(
            frame,
            columns=("workflow", "state", "errors", "outputs"),
            show="headings",
            height=9,
        )
        self._tree.heading("workflow", text="Workflow")
        self._tree.heading("state", text="State")
        self._tree.heading("errors", text="Errors")
        self._tree.heading("outputs", text="Outputs")
        self._tree.pack(fill="x")

        self._runs_by_item = {}
        for run in runs:
            item = self._tree.insert(
                "",
                "end",
                values=(
                    run.get("workflow_name") or run.get("workflow_id"),
                    run.get("final_state"),
                    run.get("error_count", 0),
                    run.get("output_count", 0),
                ),
            )
            self._runs_by_item[item] = run
        self._tree.bind("<<TreeviewSelect>>", self._show_selected)

        self._details = tk.Text(frame, wrap="word", height=10)
        self._details.pack(fill="both", expand=True, pady=(10, 0))
        self._details.configure(state="disabled")
        center_window(self, parent)

    def _show_selected(self, _event=None) -> None:
        selected = self._tree.selection()
        if not selected:
            return
        run = self._runs_by_item[selected[0]]
        lines = [
            f"Run: {run.get('run_id')}",
            f"Started: {run.get('started_at')}",
            f"Ended: {run.get('ended_at')}",
            "",
            "Outputs:",
        ]
        lines.extend(str(item) for item in run.get("outputs", []))
        self._details.configure(state="normal")
        self._details.delete("1.0", "end")
        self._details.insert("1.0", "\n".join(lines))
        self._details.configure(state="disabled")

"""Error details and recovery modal."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List

from .common import center_window, safe_grab


class ErrorDetailsModal(tk.Toplevel):
    """Shows one recoverable error and recovery action buttons."""

    def __init__(
        self,
        parent,
        payload: Dict[str, object],
        on_recovery_action: Callable[[str, str], None],
    ) -> None:
        super().__init__(parent)
        self.title("Execution Error")
        self.transient(parent)
        self.geometry("620x420")
        self._payload = payload
        self._on_recovery_action = on_recovery_action
        self._trace_visible = False

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Recoverable Error", font=("Segoe UI", 12, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            frame,
            text=f"Node: {payload.get('node_id')}   Branch: {payload.get('branch_id')}",
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(frame, text=f"Category: {payload.get('category')}").pack(anchor="w")
        ttk.Label(
            frame,
            text=str(payload.get("error_message", "")),
            wraplength=560,
            foreground="#991b1b",
        ).pack(anchor="w", pady=(8, 10))

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(0, 8))
        for action in payload.get("options", []):
            ttk.Button(
                actions,
                text=str(action).replace("_", " ").title(),
                command=lambda selected=str(action): self._choose(selected),
            ).pack(side="left", padx=(0, 6))

        ttk.Button(frame, text="View Full Trace", command=self._toggle_trace).pack(
            anchor="w", pady=(0, 6)
        )
        self._trace = tk.Text(frame, wrap="none", height=10)
        self._trace.insert("1.0", str(payload.get("traceback", "")))
        self._trace.configure(state="disabled")

        center_window(self, parent)
        safe_grab(self)

    def _choose(self, action: str) -> None:
        self._on_recovery_action(str(self._payload["branch_id"]), action)
        self.destroy()

    def _toggle_trace(self) -> None:
        if self._trace_visible:
            self._trace.pack_forget()
        else:
            self._trace.pack(fill="both", expand=True)
        self._trace_visible = not self._trace_visible

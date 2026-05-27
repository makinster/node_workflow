"""User input modal."""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .common import center_window, safe_grab


class UserInputModal(tk.Toplevel):
    """Dialog shown when a supervisor pauses for user input."""

    def __init__(
        self,
        parent,
        branch_id: str,
        node_id: str,
        prompt: str,
        on_submit: Callable[[str, str], None],
    ) -> None:
        super().__init__(parent)
        self.title("User Input")
        self.transient(parent)
        self.resizable(False, False)
        self._branch_id = branch_id
        self._on_submit = on_submit

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"Node: {node_id}", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(0, 8)
        )
        ttk.Label(frame, text=prompt, wraplength=360).pack(anchor="w", pady=(0, 8))
        self._value_var = tk.StringVar(value="")
        entry = ttk.Entry(frame, textvariable=self._value_var, width=44)
        entry.pack(fill="x", pady=(0, 12))
        entry.focus_set()

        actions = ttk.Frame(frame)
        actions.pack(anchor="e")
        ttk.Button(actions, text="Cancel", command=self._submit_empty).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(actions, text="Submit", command=self._submit).pack(side="right")
        self.bind("<Return>", lambda _event: self._submit())
        self.protocol("WM_DELETE_WINDOW", self._submit_empty)
        center_window(self, parent)
        safe_grab(self)

    def _submit(self) -> None:
        self._on_submit(self._branch_id, self._value_var.get())
        self.destroy()

    def _submit_empty(self) -> None:
        self._on_submit(self._branch_id, "")
        self.destroy()

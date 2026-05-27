"""Top toolbar widget for AttackOfTheNodes."""

import tkinter as tk
from tkinter import ttk
from typing import Callable


class Toolbar(tk.Frame):
    """Persistent top toolbar with workflow and common actions."""

    def __init__(
        self,
        parent,
        on_workflow_library: Callable[[], None],
        on_save: Callable[[], None],
        on_run: Callable[[], None],
        on_new: Callable[[], None],
        on_errors: Callable[[], None],
        on_settings: Callable[[], None],
        on_workflow_settings: Callable[[], None],
        on_help: Callable[[], None],
        on_about: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg="#0f172a", height=48)
        self.pack_propagate(False)
        self._workflow_id = ""

        self._name_label = tk.Label(
            self,
            text="",
            bg="#0f172a",
            fg="#f8fafc",
            font=("Segoe UI", 12, "bold"),
        )
        self._name_label.pack(side="left", padx=(16, 10))
        self._name_label.bind("<Button-1>", self._show_workflow_id)

        ttk.Button(self, text="Workflow", command=on_workflow_library).pack(
            side="left", padx=4, pady=8
        )
        ttk.Button(self, text="Workflow Settings", command=on_workflow_settings).pack(
            side="left", padx=4, pady=8
        )
        self._save_button = ttk.Button(self, text="Save", command=on_save)
        self._save_button.pack(side="left", padx=4, pady=8)
        self._run_button = ttk.Button(self, text="Run", command=on_run)
        self._run_button.pack(side="left", padx=4, pady=8)
        self._error_button = ttk.Button(self, text="Errors: 0", command=on_errors)
        self._error_button.pack(side="left", padx=4, pady=8)
        ttk.Button(self, text="Settings", command=on_settings).pack(
            side="left", padx=4, pady=8
        )
        ttk.Button(self, text="Help", command=on_help).pack(
            side="left", padx=4, pady=8
        )
        ttk.Button(self, text="About", command=on_about).pack(
            side="left", padx=4, pady=8
        )
        ttk.Button(self, text="New", command=on_new).pack(
            side="right", padx=(4, 16), pady=8
        )

        self._id_label = tk.Label(
            self,
            text="",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Consolas", 8),
        )
        self._id_label.pack(side="left", padx=(10, 0))

    def update_state(
        self,
        workflow_name: str,
        workflow_id: str,
        is_dirty: bool,
        mode: str,
    ) -> None:
        """Refresh toolbar labels and button states from UI state."""
        self._workflow_id = workflow_id or ""
        dirty = " *" if is_dirty else ""
        self._name_label.configure(text=f"{workflow_name or 'No Workflow'}{dirty}")
        self._save_button.configure(state=("normal" if is_dirty else "disabled"))
        self._run_button.configure(state=("normal" if mode == "editor" else "disabled"))

    def set_error_count(self, count: int) -> None:
        """Update the current run error badge."""
        self._error_button.configure(text=f"Errors: {count}")

    def _show_workflow_id(self, _event=None) -> None:
        self._id_label.configure(text=self._workflow_id)

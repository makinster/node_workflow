"""Global settings modal."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict

from backend.configuration_manager import DEFAULT_SETTINGS

from .common import center_window, safe_grab


class SettingsModal(tk.Toplevel):
    """Form for editing ConfigurationManager settings."""

    def __init__(self, parent, configuration_manager) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.transient(parent)
        self.resizable(False, False)
        self._configuration_manager = configuration_manager
        self._vars: Dict[str, Any] = {}

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Global Settings", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        settings = configuration_manager.get_all()
        for row, key in enumerate(DEFAULT_SETTINGS, start=1):
            value = settings.get(key, DEFAULT_SETTINGS[key])
            ttk.Label(frame, text=key.replace("_", " ").title()).grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=4
            )
            self._vars[key] = self._make_editor(frame, row, key, value)

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(DEFAULT_SETTINGS) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        ttk.Button(buttons, text="Save", command=self._save).pack(side="right")

        center_window(self, parent)
        safe_grab(self)

    def _make_editor(self, parent, row: int, key: str, value: Any):
        if isinstance(DEFAULT_SETTINGS[key], bool):
            var = tk.BooleanVar(value=bool(value))
            ttk.Checkbutton(parent, variable=var).grid(row=row, column=1, sticky="w", pady=4)
            return var
        if isinstance(DEFAULT_SETTINGS[key], int):
            var = tk.StringVar(value=str(value))
            ttk.Spinbox(parent, from_=0, to=9999, textvariable=var, width=12).grid(
                row=row, column=1, sticky="w", pady=4
            )
            return var
        var = tk.StringVar(value=str(value))
        ttk.Entry(parent, textvariable=var, width=34).grid(row=row, column=1, sticky="we", pady=4)
        return var

    def _save(self) -> None:
        values: Dict[str, Any] = {}
        try:
            for key, var in self._vars.items():
                default = DEFAULT_SETTINGS[key]
                value = var.get()
                if isinstance(default, bool):
                    values[key] = bool(value)
                elif isinstance(default, int):
                    values[key] = int(value)
                else:
                    values[key] = str(value)
        except ValueError as exc:
            messagebox.showerror("Settings", f"Invalid numeric value: {exc}", parent=self)
            return

        for key, value in values.items():
            self._configuration_manager.set(key, value)
        self.destroy()

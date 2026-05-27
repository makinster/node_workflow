"""Output viewer modal."""

import tkinter as tk
from tkinter import ttk

from .common import center_window


class OutputViewerModal(tk.Toplevel):
    """Shows output lines collected by MasterState after a run."""

    def __init__(self, parent, outputs) -> None:
        super().__init__(parent)
        self.title("Output")
        self.transient(parent)
        self.geometry("560x360")

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Run Output", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )
        self._text = tk.Text(frame, wrap="word", height=14, width=64)
        self._text.pack(fill="both", expand=True)
        if outputs:
            self._text.insert("1.0", "\n".join(str(item) for item in outputs))
        else:
            self._text.insert("1.0", "No output has been collected yet.")
        self._text.configure(state="disabled")
        ttk.Button(frame, text="Close", command=self.destroy).pack(anchor="e", pady=(8, 0))
        center_window(self, parent)

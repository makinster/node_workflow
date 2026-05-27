"""Memory viewer modal."""

import json
import tkinter as tk
from tkinter import ttk

from .common import center_window


class MemoryViewerModal(tk.Toplevel):
    """Live view of MemoryBank persistent and transient stores."""

    def __init__(self, parent, memory_bank, event_bus, memory_update_event: str) -> None:
        super().__init__(parent)
        self.title("Memory")
        self.transient(parent)
        self.geometry("620x420")
        self._memory_bank = memory_bank
        self._event_bus = event_bus
        self._memory_update_event = memory_update_event
        self._event_bus.subscribe(self._memory_update_event, self._on_memory_update)

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Memory State", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )
        self._text = tk.Text(frame, wrap="none", height=18, width=72)
        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=self._text.yview)
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self._text.xview)
        self._text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self._text.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._render(self._memory_bank.get_state())
        center_window(self, parent)

    def destroy(self) -> None:
        self._event_bus.unsubscribe(self._memory_update_event, self._on_memory_update)
        super().destroy()

    def _on_memory_update(self, state) -> None:
        self._render(state)

    def _render(self, state) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", json.dumps(state, indent=2, sort_keys=True))
        self._text.configure(state="disabled")

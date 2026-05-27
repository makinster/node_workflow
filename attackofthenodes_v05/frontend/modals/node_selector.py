"""Node selector modal."""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .common import center_window, safe_grab


class NodeSelectorModal(tk.Toplevel):
    """Dialog for choosing a node type to add."""

    def __init__(self, parent, factory, on_select: Callable[[str], None]) -> None:
        super().__init__(parent)
        self.title("Add Node")
        self.transient(parent)
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Choose Node Type", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        for metadata in factory.get_node_types_metadata():
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=3)
            ttk.Label(
                row,
                text=f"{metadata['display_name']} - {metadata['description']}",
                width=54,
            ).pack(side="left", fill="x", expand=True)
            ttk.Button(
                row,
                text="Add",
                command=lambda node_type=metadata["type"]: self._select(
                    node_type, on_select
                ),
            ).pack(side="right")

        center_window(self, parent)
        safe_grab(self)

    def _select(self, node_type: str, on_select: Callable[[str], None]) -> None:
        on_select(node_type)
        self.destroy()

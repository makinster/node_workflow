"""Help and about modals."""

import tkinter as tk
from tkinter import ttk

from .common import center_window, safe_grab


class HelpModal(tk.Toplevel):
    """Tabbed in-app help."""

    def __init__(self, parent, factory) -> None:
        super().__init__(parent)
        self.title("Help")
        self.transient(parent)
        self.geometry("620x440")
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self._add_tab(tabs, "Getting Started", (
            "Create or load a workflow from the Workflow button.\n\n"
            "Add nodes, open each node config, set fields, and connect output ports "
            "to downstream nodes. Validate before running. Use the branch dropdown "
            "under branch nodes to inspect alternate paths."
        ))
        node_lines = [
            f"{item['display_name']} ({item['type']}): {item['description']}"
            for item in factory.get_node_types_metadata()
        ]
        self._add_tab(tabs, "Node Types", "\n".join(node_lines))
        self._add_tab(tabs, "Shortcuts", (
            "Ctrl+S: Save current workflow\n"
            "Ctrl+R: Run workflow\n"
            "Ctrl+Shift+R: Stop workflow\n"
            "Ctrl+N: New workflow\n"
            "Ctrl+O / Ctrl+L: Workflow library\n"
            "Escape: Close the active modal or window"
        ))
        self._add_tab(tabs, "Troubleshooting", (
            "Validation errors usually mean a missing start node, an invalid node type, "
            "or a connection pointing at a deleted node.\n\n"
            "Yellow validation warnings mean nodes are disconnected from the start path. "
            "They are saved, but they will not execute."
        ))
        center_window(self, parent)
        safe_grab(self)

    def _add_tab(self, tabs, title: str, text: str) -> None:
        frame = ttk.Frame(tabs, padding=10)
        box = tk.Text(frame, wrap="word", height=18, width=70)
        box.insert("1.0", text)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True)
        tabs.add(frame, text=title)


class AboutModal(tk.Toplevel):
    """Small about window."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("About AttackOfTheNodes")
        self.transient(parent)
        self.resizable(False, False)
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="AttackOfTheNodes", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Local Python workflow engine and node editor.").pack(anchor="w", pady=(8, 0))
        ttk.Label(frame, text="Prototype track: v0.99 readiness surface. v1.0 swaps placeholder AI nodes for real API calls.").pack(anchor="w", pady=(8, 0))
        ttk.Button(frame, text="Close", command=self.destroy).pack(anchor="e", pady=(16, 0))
        center_window(self, parent)
        safe_grab(self)

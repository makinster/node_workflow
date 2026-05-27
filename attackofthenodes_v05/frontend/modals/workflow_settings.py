"""Current workflow settings modal."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .common import center_window, safe_grab


class WorkflowSettingsModal(tk.Toplevel):
    """Actions for the active workflow: rename, duplicate, export, delete."""

    def __init__(
        self,
        parent,
        workflow_map,
        save_manager,
        on_refresh,
        on_deleted,
    ) -> None:
        super().__init__(parent)
        self.title("Workflow Settings")
        self.transient(parent)
        self.resizable(False, False)
        self._workflow_map = workflow_map
        self._save_manager = save_manager
        self._on_refresh = on_refresh
        self._on_deleted = on_deleted

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=workflow_map.workflow_name or "No Workflow", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(frame, text=workflow_map.workflow_id or "", foreground="#64748b").pack(anchor="w", pady=(0, 10))

        ttk.Button(frame, text="Rename", command=self._rename).pack(fill="x", pady=3)
        ttk.Button(frame, text="Duplicate", command=self._duplicate).pack(fill="x", pady=3)
        ttk.Button(frame, text="Export...", command=self._export).pack(fill="x", pady=3)
        ttk.Button(frame, text="Delete", command=self._delete).pack(fill="x", pady=3)
        ttk.Button(frame, text="Close", command=self.destroy).pack(anchor="e", pady=(12, 0))

        center_window(self, parent)
        safe_grab(self)

    def _rename(self) -> None:
        current = self._workflow_map.workflow_name or ""
        name = simpledialog.askstring("Rename Workflow", "New workflow name:", initialvalue=current, parent=self)
        if not name:
            return
        self._save_manager.rename_current_workflow(name)
        self._on_refresh("Workflow renamed")
        self.destroy()

    def _duplicate(self) -> None:
        new_id = self._save_manager.duplicate_workflow()
        if new_id:
            self._save_manager.load_workflow(new_id)
            self._on_refresh("Workflow duplicated")
            self.destroy()
        else:
            messagebox.showerror("Duplicate Workflow", "Could not duplicate workflow.", parent=self)

    def _export(self) -> None:
        workflow_id = self._workflow_map.workflow_id
        if not workflow_id:
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Workflow",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        if self._save_manager.export_workflow(workflow_id, path):
            messagebox.showinfo("Export Workflow", "Workflow exported.", parent=self)
        else:
            messagebox.showerror("Export Workflow", "Could not export workflow.", parent=self)

    def _delete(self) -> None:
        workflow_id = self._workflow_map.workflow_id
        if not workflow_id:
            return
        confirmed = messagebox.askyesno(
            "Delete Workflow",
            f"Delete workflow '{self._workflow_map.workflow_name}'?",
            parent=self,
        )
        if not confirmed:
            return
        self._save_manager.delete_workflow(workflow_id)
        self._on_deleted()
        self.destroy()

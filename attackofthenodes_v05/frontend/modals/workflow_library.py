"""Workflow library modal."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable, Optional

from backend.persistence import delete_workflow, list_workflows

from .common import center_window, safe_grab


class WorkflowLibraryModal(tk.Toplevel):
    """Dialog listing saved workflows with load/delete/new actions."""

    def __init__(
        self,
        parent,
        on_load: Callable[[str], bool],
        on_new: Callable[[str], None] = None,
        on_delete: Optional[Callable[[str], bool]] = None,
        on_duplicate: Optional[Callable[[str], Optional[str]]] = None,
        on_export: Optional[Callable[[str, str], bool]] = None,
        on_import: Optional[Callable[[str], Optional[str]]] = None,
        get_open_workflows: Optional[Callable[[], list]] = None,
        on_switch_open: Optional[Callable[[str], bool]] = None,
    ) -> None:
        super().__init__(parent)
        self.title("Workflow Library")
        self.transient(parent)
        self.resizable(False, False)
        self._on_load = on_load
        self._on_new = on_new
        self._on_delete = on_delete
        self._on_duplicate = on_duplicate
        self._on_export = on_export
        self._on_import = on_import
        self._get_open_workflows = get_open_workflows
        self._on_switch_open = on_switch_open

        self._frame = ttk.Frame(self, padding=12)
        self._frame.pack(fill="both", expand=True)
        self._render()
        center_window(self, parent)
        safe_grab(self)

    def _render(self) -> None:
        for child in self._frame.winfo_children():
            child.destroy()
        top = ttk.Frame(self._frame)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Saved Workflows", font=("Segoe UI", 11, "bold")).pack(
            side="left"
        )
        if self._on_import is not None:
            ttk.Button(top, text="Import...", command=self._import_workflow).pack(
                side="right", padx=(4, 0)
            )
        if self._on_new is not None:
            ttk.Button(top, text="New Workflow", command=self._new_workflow).pack(
                side="right"
            )

        self._render_open_workflows()

        workflows = list_workflows()
        if not workflows:
            ttk.Label(self._frame, text="No saved workflows yet.").pack(anchor="w")
        for workflow in workflows:
            row = ttk.Frame(self._frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=workflow["name"], width=34).pack(side="left")
            ttk.Button(
                row,
                text="Load",
                command=lambda workflow_id=workflow["id"]: self._load(workflow_id),
            ).pack(side="left", padx=3)
            if self._on_duplicate is not None:
                ttk.Button(
                    row,
                    text="Duplicate",
                    command=lambda workflow_id=workflow["id"]: self._duplicate(workflow_id),
                ).pack(side="left", padx=3)
            if self._on_export is not None:
                ttk.Button(
                    row,
                    text="Export",
                    command=lambda workflow_id=workflow["id"]: self._export(workflow_id),
                ).pack(side="left", padx=3)
            ttk.Button(
                row,
                text="Delete",
                command=lambda workflow_id=workflow["id"]: self._delete(workflow_id),
            ).pack(side="left", padx=3)

        ttk.Button(self._frame, text="Close", command=self.destroy).pack(
            anchor="e", pady=(12, 0)
        )

    def _new_workflow(self) -> None:
        name = simpledialog.askstring("New Workflow", "Workflow name:", parent=self)
        if name:
            self._on_new(name)
            self.destroy()

    def _render_open_workflows(self) -> None:
        if self._get_open_workflows is None or self._on_switch_open is None:
            return
        open_workflows = self._get_open_workflows()
        if not open_workflows:
            return
        box = ttk.LabelFrame(self._frame, text="Open In This Session", padding=8)
        box.pack(fill="x", pady=(0, 10))
        for workflow in open_workflows:
            row = ttk.Frame(box)
            row.pack(fill="x", pady=2)
            marker = "current" if workflow.get("is_active") else "open"
            dirty = " *" if workflow.get("is_dirty") else ""
            ttk.Label(row, text=f"{workflow['name']}{dirty} ({marker})", width=34).pack(side="left")
            ttk.Button(
                row,
                text="Switch",
                command=lambda workflow_id=workflow["id"]: self._switch_open(workflow_id),
            ).pack(side="left", padx=3)

    def _load(self, workflow_id: str) -> None:
        if self._on_load(workflow_id):
            self.destroy()
        else:
            messagebox.showerror("Load Workflow", f"Could not load {workflow_id}")

    def _delete(self, workflow_id: str) -> None:
        confirmed = messagebox.askyesno(
            "Delete Workflow", f"Delete workflow '{workflow_id}'?", parent=self
        )
        if confirmed:
            if self._on_delete is not None:
                self._on_delete(workflow_id)
            else:
                delete_workflow(workflow_id)
            self._render()

    def _duplicate(self, workflow_id: str) -> None:
        if self._on_duplicate is None:
            return
        new_id = self._on_duplicate(workflow_id)
        if new_id:
            self._render()
        else:
            messagebox.showerror("Duplicate Workflow", "Could not duplicate workflow.", parent=self)

    def _export(self, workflow_id: str) -> None:
        if self._on_export is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Workflow",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        if self._on_export(workflow_id, path):
            messagebox.showinfo("Export Workflow", "Workflow exported.", parent=self)
        else:
            messagebox.showerror("Export Workflow", "Could not export workflow.", parent=self)

    def _import_workflow(self) -> None:
        if self._on_import is None:
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="Import Workflow",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        new_id = self._on_import(path)
        if new_id:
            self._on_load(new_id)
            self.destroy()
        else:
            messagebox.showerror("Import Workflow", "Could not import workflow.", parent=self)

    def _switch_open(self, workflow_id: str) -> None:
        if self._on_switch_open and self._on_switch_open(workflow_id):
            self.destroy()

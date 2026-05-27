"""Controls panel for AttackOfTheNodes v0.5."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional


class ControlsPanel(tk.Frame):
    """Right-side controls for editor mode."""

    def __init__(
        self,
        parent,
        on_validate: Callable[[], None],
        on_save: Callable[[], None],
        on_load: Callable[[], None],
        on_add_node: Callable[[], None],
        on_run: Callable[[], None],
        on_pause_resume: Callable[[], None],
        on_stop: Callable[[], None],
        on_select_supervisor: Callable[[str], None],
        on_view_memory: Callable[[], None],
        on_view_output: Callable[[], None],
        on_view_history: Callable[[], None],
        on_jump_to_node: Callable[[str], None],
        get_jump_targets: Callable[[str], List[dict]],
    ) -> None:
        super().__init__(parent, bg="#f8fafc", padx=14, pady=14)
        self._on_validate = on_validate
        self._on_save = on_save
        self._on_load = on_load
        self._on_add_node = on_add_node
        self._on_run = on_run
        self._on_pause_resume = on_pause_resume
        self._on_stop = on_stop
        self._on_select_supervisor = on_select_supervisor
        self._on_view_memory = on_view_memory
        self._on_view_output = on_view_output
        self._on_view_history = on_view_history
        self._on_jump_to_node = on_jump_to_node
        self._get_jump_targets = get_jump_targets
        self._mode = "editor"
        self._run_state = "IDLE"
        self._is_dirty = False

        self._title = tk.Label(
            self,
            text="Editor Controls",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 11, "bold"),
        )
        self._title.pack(anchor="w", pady=(0, 12))
        self._state_label = tk.Label(
            self,
            text="IDLE",
            bg="#e2e8f0",
            fg="#475569",
            padx=8,
            pady=4,
            font=("Segoe UI", 9, "bold"),
        )
        self._state_label.pack(fill="x", pady=(0, 10))

        self._validate_button = ttk.Button(
            self, text="Validate", command=self._on_validate
        )
        self._save_button = ttk.Button(self, text="Save", command=self._on_save)
        self._load_button = ttk.Button(self, text="Load", command=self._on_load)
        self._add_button = ttk.Button(self, text="Add Node", command=self._on_add_node)
        self._run_button = ttk.Button(self, text="Run", command=self._on_run)
        self._pause_resume_button = ttk.Button(
            self, text="Pause", command=self._on_pause_resume
        )
        self._stop_button = ttk.Button(self, text="Stop", command=self._on_stop)
        self._memory_button = ttk.Button(
            self, text="View Memory", command=self._on_view_memory
        )
        self._output_button = ttk.Button(
            self, text="View Output", command=self._on_view_output
        )
        self._history_button = ttk.Button(
            self, text="Run History", command=self._on_view_history
        )

        self._supervisor_var = tk.StringVar(value="")
        self._supervisor_combo = ttk.Combobox(
            self,
            textvariable=self._supervisor_var,
            state="readonly",
            width=20,
        )
        self._supervisor_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._on_select_supervisor(self._supervisor_var.get()),
        )
        self._jump_filter_var = tk.StringVar(value="all")
        self._jump_node_var = tk.StringVar(value="")
        self._jump_targets = {}
        self._jump_filter_combo = ttk.Combobox(
            self,
            textvariable=self._jump_filter_var,
            values=["all", "start", "branches", "bookmarks", "outputs"],
            state="readonly",
            width=20,
        )
        self._jump_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_jump_targets())
        self._jump_combo = ttk.Combobox(self, textvariable=self._jump_node_var, state="readonly", width=20)
        self._jump_button = ttk.Button(self, text="Jump To Node", command=self._jump_to_selected)

        for button in (
            self._validate_button,
            self._save_button,
            self._load_button,
            self._add_button,
            self._run_button,
            self._pause_resume_button,
            self._stop_button,
            self._memory_button,
            self._output_button,
            self._history_button,
        ):
            button.pack(fill="x", pady=4)
        self._supervisor_combo.pack(fill="x", pady=(12, 4))
        self._jump_filter_combo.pack(fill="x", pady=(12, 4))
        self._jump_combo.pack(fill="x", pady=4)
        self._jump_button.pack(fill="x", pady=4)

        self._status_label = tk.Label(
            self,
            text="Ready",
            bg="#f8fafc",
            fg="#475569",
            justify="left",
            wraplength=190,
            font=("Segoe UI", 9),
        )
        self._status_label.pack(anchor="w", pady=(16, 0))
        self.set_mode("editor", "IDLE")

    def set_dirty(self, is_dirty: bool) -> None:
        """Enable save button only when there are unsaved changes."""
        self._is_dirty = is_dirty
        if self._mode == "editor":
            self._save_button.configure(state=("normal" if is_dirty else "disabled"))

    def set_status(self, text: str) -> None:
        """Show a short status message."""
        self._status_label.configure(text=text)

    def set_mode(self, mode: str, run_state: str) -> None:
        """Switch visible controls between editor and execution mode."""
        self._mode = mode
        self._run_state = run_state
        is_editor = mode == "editor"
        editor_state = "normal" if is_editor else "disabled"
        execution_state = "normal" if not is_editor else "disabled"

        self._title.configure(
            text="Editor Controls" if is_editor else "Execution Controls"
        )
        for button in (
            self._validate_button,
            self._load_button,
            self._add_button,
            self._run_button,
        ):
            button.configure(state=editor_state)
        self._save_button.configure(
            state=("normal" if is_editor and self._is_dirty else "disabled")
        )
        self._pause_resume_button.configure(state=execution_state)
        self._stop_button.configure(state=execution_state)
        self._memory_button.configure(state="normal")
        self._output_button.configure(state="normal")
        self._history_button.configure(state="normal")
        self._supervisor_combo.configure(state=("readonly" if not is_editor else "disabled"))
        jump_state = "readonly" if is_editor else "disabled"
        self._jump_filter_combo.configure(state=jump_state)
        self._jump_combo.configure(state=jump_state)
        self._jump_button.configure(state=("normal" if is_editor else "disabled"))
        self._pause_resume_button.configure(
            text="Resume" if run_state == "PAUSED" else "Pause"
        )
        self.set_workflow_state(run_state)

    def set_workflow_state(self, run_state: str) -> None:
        """Display the current workflow state with a simple color cue."""
        colors = {
            "IDLE": ("#e2e8f0", "#475569"),
            "RUNNING": ("#dbeafe", "#1d4ed8"),
            "PAUSED": ("#fef3c7", "#92400e"),
            "WAITING_FOR_INPUT": ("#fef3c7", "#92400e"),
            "FINISHED": ("#dcfce7", "#166534"),
            "ERROR": ("#fee2e2", "#991b1b"),
        }
        bg, fg = colors.get(run_state, ("#e2e8f0", "#475569"))
        self._state_label.configure(text=run_state, bg=bg, fg=fg)

    def set_supervisors(
        self, supervisors: List[str], selected_supervisor_id: Optional[str]
    ) -> None:
        """Update the supervisor selector."""
        self._supervisor_combo.configure(values=supervisors)
        if selected_supervisor_id:
            self._supervisor_var.set(selected_supervisor_id)
        elif supervisors:
            self._supervisor_var.set(supervisors[0])
        else:
            self._supervisor_var.set("")

    def refresh_jump_targets(self) -> None:
        """Refresh Jump To dropdown values from the selected filter."""
        targets = self._get_jump_targets(self._jump_filter_var.get())
        self._jump_targets = {
            f"{item.get('alias') or item.get('type')} ({item['id']})": item["id"]
            for item in targets
        }
        labels = list(self._jump_targets.keys())
        self._jump_combo.configure(values=labels)
        self._jump_node_var.set(labels[0] if labels else "")

    def _jump_to_selected(self) -> None:
        node_id = self._jump_targets.get(self._jump_node_var.get())
        if node_id:
            self._on_jump_to_node(node_id)

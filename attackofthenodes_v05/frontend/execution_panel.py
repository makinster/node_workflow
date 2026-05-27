"""Execution panel for AttackOfTheNodes v0.5."""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .node_card import CARD_HEIGHT, CARD_WIDTH, draw_node_card


class ExecutionPanel(tk.Frame):
    """Shows workflow nodes with execution-time highlighting."""

    def __init__(
        self,
        parent,
        workflow_map,
        ui_state,
        on_select_supervisor: Callable[[str], None],
    ) -> None:
        super().__init__(parent, bg="#ffffff")
        self._workflow_map = workflow_map
        self._ui_state = ui_state
        self._on_select_supervisor = on_select_supervisor

        header = tk.Frame(self, bg="#ffffff")
        header.pack(fill="x", padx=18, pady=(14, 4))
        self._label = tk.Label(
            header, text="", bg="#ffffff", fg="#0f172a", font=("Segoe UI", 11, "bold")
        )
        self._label.pack(side="left")
        self._supervisor_var = tk.StringVar(value="")
        self._supervisor_combo = ttk.Combobox(
            header,
            textvariable=self._supervisor_var,
            state="readonly",
            width=34,
        )
        self._supervisor_combo.pack(side="right")
        self._supervisor_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._select_supervisor_from_combo(),
        )
        self._canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)
        self._scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

    def refresh(self) -> None:
        """Redraw nodes with current execution statuses."""
        self._canvas.delete("all")
        selected = self._ui_state.selected_supervisor_id or "none"
        self._label.configure(
            text=f"Run: {self._ui_state.workflow_run_state}   Supervisor: {selected}"
        )
        self._refresh_supervisor_combo()
        nodes = self._workflow_map.get_all_node_data()
        if not nodes:
            self._canvas.configure(scrollregion=(0, 0, 520, 320))
            return

        ordered = self._ordered_node_ids(nodes)
        x = 32
        y = 28
        center_x = x + CARD_WIDTH // 2
        for index, node_id in enumerate(ordered):
            status = self._ui_state.node_statuses.get(node_id, "idle")
            draw_node_card(self._canvas, node_id, nodes[node_id], x, y, status=status)
            if index < len(ordered) - 1:
                self._canvas.create_line(
                    center_x,
                    y + CARD_HEIGHT,
                    center_x,
                    y + CARD_HEIGHT + 24,
                    fill="#94a3b8",
                    width=2,
                    arrow="last",
                )
            y += CARD_HEIGHT + 34
        self._canvas.configure(scrollregion=(0, 0, 520, max(360, y + 40)))

    def _refresh_supervisor_combo(self) -> None:
        labels = []
        for supervisor in self._ui_state.active_supervisors:
            branch_id = supervisor["branch_id"]
            current_node = supervisor.get("current_node_id") or "idle"
            labels.append(f"{branch_id} @ {current_node}")
        self._supervisor_combo.configure(values=labels)
        selected = self._ui_state.selected_supervisor_id
        if selected:
            for label in labels:
                if label.startswith(selected):
                    self._supervisor_var.set(label)
                    return
        self._supervisor_var.set(labels[0] if labels else "")

    def _select_supervisor_from_combo(self) -> None:
        value = self._supervisor_var.get()
        branch_id = value.split(" @ ", 1)[0] if value else ""
        if branch_id:
            self._on_select_supervisor(branch_id)

    def _ordered_node_ids(self, nodes):
        start_id = self._workflow_map.find_start_node_id()
        if start_id is None:
            return list(nodes.keys())
        ordered = []
        visited = set()
        stack = [start_id]
        while stack:
            node_id = stack.pop(0)
            if node_id in visited or node_id not in nodes:
                continue
            ordered.append(node_id)
            visited.add(node_id)
            outputs = nodes[node_id].get("connections", {}).get("outputs", [])
            for conn in outputs:
                target = conn.get("target_node_id")
                if target and target not in visited:
                    stack.append(target)
        for node_id in nodes.keys():
            if node_id not in visited:
                ordered.append(node_id)
        return ordered

"""
Editor panel for AttackOfTheNodes v0.5.

Displays the current workflow as a vertical list of node cards. Clicking a
card opens the node configuration modal.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Set

from .node_card import CARD_HEIGHT, CARD_WIDTH, draw_node_card


class EditorPanel(tk.Frame):
    """Scrollable workflow editor panel."""

    def __init__(
        self,
        parent,
        workflow_map,
        on_node_selected: Callable[[str], None],
        on_node_deleted: Callable[[str], None],
    ) -> None:
        super().__init__(parent, bg="#ffffff")
        self._workflow_map = workflow_map
        self._on_node_selected = on_node_selected
        self._on_node_deleted = on_node_deleted
        self._selected_branch_ports: Dict[str, str] = {}
        self._branch_controls = []
        self._validation_status = None
        self._last_positions: Dict[str, int] = {}

        self._canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)
        self._scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

    def refresh(self) -> None:
        """Redraw all loaded workflow nodes."""
        self._canvas.delete("all")
        self._branch_controls.clear()
        self._last_positions.clear()
        nodes = self._workflow_map.get_all_node_data()
        if not nodes:
            self._canvas.create_text(
                32,
                32,
                anchor="nw",
                text="No nodes yet. Use Add Node to begin.",
                fill="#475569",
                font=("Segoe UI", 11),
            )
            self._canvas.configure(scrollregion=(0, 0, 520, 320))
            return

        ordered_ids = self._ordered_node_ids(nodes)
        x = 32
        y = 28
        center_x = x + CARD_WIDTH // 2

        for index, node_id in enumerate(ordered_ids):
            node = nodes[node_id]
            status = self._validation_node_status(node_id)
            draw_node_card(
                self._canvas,
                node_id,
                node,
                x,
                y,
                status=status,
                on_click=self._on_node_selected,
                on_delete=self._on_node_deleted,
            )
            self._last_positions[node_id] = y
            self._draw_validation_badge(node_id, x, y)
            branch_extra_height = self._draw_branch_selector_if_needed(node_id, node, x, y)
            if index < len(ordered_ids) - 1:
                self._canvas.create_line(
                    center_x,
                    y + CARD_HEIGHT + branch_extra_height,
                    center_x,
                    y + CARD_HEIGHT + branch_extra_height + 24,
                    fill="#94a3b8",
                    width=2,
                    arrow="last",
                )
            y += CARD_HEIGHT + branch_extra_height + 34

        self._canvas.configure(scrollregion=(0, 0, 520, max(360, y + 40)))

    def set_validation_status(self, validation_status) -> None:
        """Store latest validation result for error/warning badges."""
        self._validation_status = validation_status
        self.refresh()

    def scroll_to_node(self, node_id: str) -> None:
        """Scroll near a node if it is currently rendered."""
        if node_id not in self._last_positions:
            return
        _, top, _, bottom = self._canvas.bbox("all") or (0, 0, 1, 1)
        height = max(1, bottom - top)
        self._canvas.yview_moveto(max(0.0, self._last_positions[node_id] / height))

    def _validation_node_status(self, node_id: str) -> str:
        if not self._validation_status:
            return "idle"
        if any(item.get("node_id") == node_id for item in self._validation_status.get("errors", [])):
            return "error"
        if any(item.get("node_id") == node_id for item in self._validation_status.get("warnings", [])):
            return "warning"
        return "idle"

    def _draw_validation_badge(self, node_id: str, x: int, y: int) -> None:
        if not self._validation_status:
            return
        messages = [
            item.get("message", "")
            for item in self._validation_status.get("errors", []) + self._validation_status.get("warnings", [])
            if item.get("node_id") == node_id
        ]
        if not messages:
            return
        self._canvas.create_text(
            x + CARD_WIDTH - 120,
            y + 60,
            anchor="w",
            text="; ".join(messages)[:34],
            fill="#991b1b" if self._validation_node_status(node_id) == "error" else "#92400e",
            font=("Segoe UI", 8, "bold"),
        )

    def _draw_branch_selector_if_needed(
        self,
        node_id: str,
        node_data: Dict[str, object],
        x: int,
        y: int,
    ) -> int:
        """Draw a branch-port selector below nodes with multiple outputs."""
        outputs = node_data.get("connections", {}).get("outputs", [])
        ports = []
        for conn in outputs:
            port = conn.get("source_port", "default")
            if port not in ports:
                ports.append(port)
        if len(ports) <= 1:
            self._selected_branch_ports.pop(node_id, None)
            return 0

        current = self._selected_branch_ports.get(node_id)
        if current not in ports:
            current = ports[0]
            self._selected_branch_ports[node_id] = current

        frame = tk.Frame(self._canvas, bg="#ffffff")
        label = tk.Label(
            frame,
            text="View branch",
            bg="#ffffff",
            fg="#475569",
            font=("Segoe UI", 9),
        )
        label.pack(side="left", padx=(0, 8))
        selected = tk.StringVar(value=current)
        combo = ttk.Combobox(
            frame,
            textvariable=selected,
            values=ports,
            state="readonly",
            width=18,
        )
        combo.pack(side="left")
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event, nid=node_id, var=selected: self._select_branch(nid, var.get()),
        )
        self._branch_controls.append(frame)
        self._canvas.create_window(x + 14, y + CARD_HEIGHT + 8, anchor="nw", window=frame)
        return 38

    def _select_branch(self, node_id: str, port: str) -> None:
        self._selected_branch_ports[node_id] = port
        self.refresh()

    def _ordered_node_ids(self, nodes: Dict[str, Dict[str, object]]) -> List[str]:
        """Return a stable mostly-execution-order node list."""
        start_id = self._workflow_map.find_start_node_id()
        if start_id is None:
            return list(nodes.keys())

        ordered: List[str] = []
        visited: Set[str] = set()
        hidden_nodes = self._hidden_nodes_for_unselected_branches(nodes)
        current: Optional[str] = start_id
        while current and current in nodes and current not in visited:
            ordered.append(current)
            visited.add(current)
            current = self._next_node_for_editor_view(current, nodes[current])

        for node_id in nodes.keys():
            if node_id not in visited and node_id not in hidden_nodes:
                ordered.append(node_id)
        return ordered

    def _hidden_nodes_for_unselected_branches(
        self, nodes: Dict[str, Dict[str, object]]
    ) -> Set[str]:
        """Return nodes that belong to currently unselected branch paths."""
        hidden: Set[str] = set()
        for node_id, node_data in nodes.items():
            outputs = node_data.get("connections", {}).get("outputs", [])
            ports = []
            for conn in outputs:
                port = conn.get("source_port", "default")
                if port not in ports:
                    ports.append(port)
            if len(ports) <= 1:
                continue
            selected = self._selected_branch_ports.get(node_id) or ports[0]
            for conn in outputs:
                if conn.get("source_port", "default") != selected:
                    self._collect_reachable(conn.get("target_node_id"), nodes, hidden)
        return hidden

    def _collect_reachable(
        self,
        node_id: Optional[str],
        nodes: Dict[str, Dict[str, object]],
        collected: Set[str],
    ) -> None:
        if not node_id or node_id not in nodes or node_id in collected:
            return
        collected.add(node_id)
        for conn in nodes[node_id].get("connections", {}).get("outputs", []):
            self._collect_reachable(conn.get("target_node_id"), nodes, collected)

    def _next_node_for_editor_view(self, node_id: str, node_data: Dict[str, object]) -> Optional[str]:
        """Follow default output or the selected branch output for branch nodes."""
        outputs = node_data.get("connections", {}).get("outputs", [])
        if not outputs:
            return None

        selected_port = self._selected_branch_ports.get(node_id)
        if selected_port:
            for conn in outputs:
                if conn.get("source_port", "default") == selected_port:
                    return conn.get("target_node_id")

        default_next = self._workflow_map.find_next_node_id(node_id, "default")
        if default_next:
            return default_next

        if len(outputs) == 1:
            return outputs[0].get("target_node_id")

        first_port = outputs[0].get("source_port", "default")
        self._selected_branch_ports[node_id] = first_port
        return outputs[0].get("target_node_id")

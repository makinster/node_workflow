"""Node configuration modal with simple connection editing."""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict

from .common import center_window, safe_grab


class NodeConfigModal(tk.Toplevel):
    """Dialog for editing node alias, config fields, and connections."""

    def __init__(
        self,
        parent,
        node_id: str,
        node_data: Dict[str, Any],
        factory,
        on_save: Callable[[str, str, Dict[str, Any]], None],
        workflow_map=None,
    ) -> None:
        super().__init__(parent)
        self.title("Node Config")
        self.transient(parent)
        self.resizable(False, False)

        self._node_id = node_id
        self._node_data = node_data
        self._factory = factory
        self._workflow_map = workflow_map
        self._on_save = on_save
        self._fields: Dict[str, tk.Variable] = {}

        metadata_by_type = {
            item["type"]: item for item in factory.get_node_types_metadata()
        }
        self._metadata = metadata_by_type.get(node_data["type"], {})
        schema = self._metadata.get("config_schema", {})
        config = dict(node_data.get("config", {}))

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=node_data["type"], font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        ttk.Label(frame, text="Alias").grid(row=1, column=0, sticky="w", pady=4)
        self._alias_var = tk.StringVar(value=node_data.get("alias", ""))
        ttk.Entry(frame, textvariable=self._alias_var, width=38).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=4
        )
        self._bookmark_var = tk.BooleanVar(value=bool(node_data.get("bookmarked", False)))
        ttk.Checkbutton(frame, text="Bookmark this node", variable=self._bookmark_var).grid(
            row=2, column=1, columnspan=2, sticky="w", pady=(0, 6)
        )

        row = 3
        for field_name, field_info in schema.items():
            ttk.Label(frame, text=field_name).grid(row=row, column=0, sticky="w", pady=4)
            field_type = field_info.get("type", "string")
            options = field_info.get("options", [])
            current = config.get(field_name, "")
            if field_type == "boolean":
                var = tk.BooleanVar(value=bool(current))
                ttk.Checkbutton(frame, variable=var).grid(row=row, column=1, sticky="w")
            elif options:
                var = tk.StringVar(value=str(current or options[0]))
                ttk.Combobox(
                    frame,
                    textvariable=var,
                    values=options,
                    state="readonly",
                    width=36,
                ).grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
            elif field_type == "multiline":
                var = tk.StringVar(value=str(current))
                text = tk.Text(frame, height=4, width=36)
                text.insert("1.0", str(current))
                text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
                var._text_widget = text
            else:
                var = tk.StringVar(value=str(current))
                ttk.Entry(frame, textvariable=var, width=38).grid(
                    row=row, column=1, columnspan=2, sticky="ew", pady=4
                )
            self._fields[field_name] = var
            row += 1

        if self._workflow_map is not None:
            row = self._build_connection_section(frame, row)

        actions = ttk.Frame(frame)
        actions.grid(row=row, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Save", command=self._save).pack(
            side="right", padx=(0, 8)
        )

        center_window(self, parent)
        safe_grab(self)

    def _build_connection_section(self, frame, row: int) -> int:
        ttk.Separator(frame).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1
        ttk.Label(frame, text="Connections", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w"
        )
        row += 1

        nodes = self._workflow_map.get_all_node_data()
        target_labels = {
            node_id: f"{data.get('alias') or data.get('type')} ({node_id})"
            for node_id, data in nodes.items()
            if node_id != self._node_id
        }
        reverse_labels = {label: node_id for node_id, label in target_labels.items()}

        output_ports = self._metadata.get("output_ports", [])
        for port in output_ports:
            ttk.Label(frame, text=f"Output: {port}").grid(
                row=row, column=0, sticky="w", pady=4
            )
            selected = tk.StringVar(value="")
            combo = ttk.Combobox(
                frame,
                textvariable=selected,
                values=list(target_labels.values()),
                state="readonly",
                width=34,
            )
            combo.grid(row=row, column=1, sticky="ew", pady=4)
            ttk.Button(
                frame,
                text="Connect",
                command=lambda p=port, s=selected, labels=reverse_labels: self._connect(
                    p, s, labels
                ),
            ).grid(row=row, column=2, padx=(6, 0), pady=4)
            row += 1

        for conn in self._node_data.get("connections", {}).get("outputs", []):
            label = (
                f"{conn.get('source_port', 'default')} -> "
                f"{conn.get('target_node_id')}:{conn.get('target_port')}"
            )
            ttk.Label(frame, text=label).grid(row=row, column=0, columnspan=2, sticky="w")
            ttk.Button(
                frame,
                text="Disconnect",
                command=lambda c=dict(conn): self._disconnect(c),
            ).grid(row=row, column=2, padx=(6, 0), pady=2)
            row += 1
        return row

    def _connect(self, source_port: str, selected, labels: Dict[str, str]) -> None:
        target_node_id = labels.get(selected.get())
        if not target_node_id:
            return
        target_data = self._workflow_map.get_node_data(target_node_id)
        if not target_data:
            return
        target_port = self._first_input_port(target_data["type"])
        if not target_port:
            return
        self._workflow_map.connect(self._node_id, source_port, target_node_id, target_port)
        self.destroy()

    def _disconnect(self, conn: Dict[str, Any]) -> None:
        self._workflow_map.disconnect(
            self._node_id,
            conn.get("source_port", "default"),
            conn.get("target_node_id"),
            conn.get("target_port"),
        )
        self.destroy()

    def _first_input_port(self, node_type: str) -> str:
        for metadata in self._factory.get_node_types_metadata():
            if metadata["type"] == node_type:
                ports = metadata.get("input_ports", [])
                return ports[0] if ports else ""
        return ""

    def _save(self) -> None:
        new_config = {}
        for field_name, variable in self._fields.items():
            text_widget = getattr(variable, "_text_widget", None)
            if text_widget is not None:
                new_config[field_name] = text_widget.get("1.0", "end-1c")
            else:
                new_config[field_name] = variable.get()
        self._on_save(self._node_id, self._alias_var.get(), new_config)
        if self._workflow_map is not None:
            self._workflow_map.set_bookmark(self._node_id, self._bookmark_var.get())
        self.destroy()

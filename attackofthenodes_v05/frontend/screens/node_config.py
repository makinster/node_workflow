"""Node configuration modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, SelectionList, Static

from frontend.widgets.form_generator import WidgetGetter, build_form


MAX_MEMBANK_OUTPUT_ROWS = 5


def normalize_membank_outputs(config: Dict[str, Any]) -> list[Dict[str, str]]:
    """Return valid membank output declarations from node config."""
    outputs = config.get("membank_outputs") or []
    if not isinstance(outputs, list):
        return []
    normalized: list[Dict[str, str]] = []
    for entry in outputs:
        if not isinstance(entry, dict):
            continue
        output_id = str(entry.get("id") or "").strip()
        if not output_id:
            continue
        normalized.append(
            {
                "id": output_id,
                "description": str(entry.get("description") or "").strip(),
            }
        )
    return normalized


def normalize_membank_inputs(config: Dict[str, Any]) -> list[str]:
    """Return membank input ids from node config."""
    inputs = config.get("membank_inputs") or []
    if not isinstance(inputs, list):
        return []
    normalized: list[str] = []
    for entry in inputs:
        value = ""
        if isinstance(entry, str):
            value = entry
        elif isinstance(entry, dict):
            value = str(entry.get("source_id") or entry.get("id") or "")
        value = value.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def build_membank_registry(workflow_map) -> Dict[str, Dict[str, Any]]:
    """Scan workflow nodes for declared membank outputs."""
    registry: Dict[str, Dict[str, Any]] = {}
    for node_id, node in workflow_map.get_all_node_data().items():
        for output in normalize_membank_outputs(node.get("config") or {}):
            entry = registry.setdefault(
                output["id"],
                {
                    "id": output["id"],
                    "description": output["description"],
                    "writers": [],
                },
            )
            if output["description"] and not entry.get("description"):
                entry["description"] = output["description"]
            entry["writers"].append(node_id)
    return registry


def membank_input_options(workflow_map, current_node_id: str) -> list[tuple[str, str]]:
    """Return selectable membank inputs, excluding downstream-only writers."""
    downstream = workflow_map.nodes_reachable_from(current_node_id)
    options: list[tuple[str, str]] = []
    for output_id, entry in sorted(build_membank_registry(workflow_map).items()):
        writers = set(entry.get("writers") or [])
        if writers and writers.issubset(downstream):
            continue
        description = entry.get("description") or "No description"
        options.append((f"{output_id} - {description}", output_id))
    return options


def normalize_wait_target_ids(config: Dict[str, Any]) -> list[str]:
    """Return wait-until target node ids from config."""
    configured = config.get("target_node_ids") or []
    if isinstance(configured, list):
        raw_values = configured
    else:
        raw_values = str(configured).replace("\n", ",").split(",")
    normalized: list[str] = []
    for value in raw_values:
        node_id = str(value).strip()
        if node_id and node_id not in normalized:
            normalized.append(node_id)
    return normalized


def wait_target_options(workflow_map, current_node_id: str) -> list[tuple[str, str]]:
    """Return wait targets, excluding self and downstream nodes."""
    downstream = workflow_map.nodes_reachable_from(current_node_id)
    options: list[tuple[str, str]] = []
    for node_id, node in sorted(workflow_map.get_all_node_data().items()):
        if node_id == current_node_id or node_id in downstream:
            continue
        label = node.get("alias") or node.get("type") or node_id
        options.append((f"{label} ({node_id})", node_id))
    return options


class NodeConfigScreen(ModalScreen):
    """Edit-node modal powered by the schema form generator."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+enter", "save", "Save"),
    ]

    def __init__(
        self,
        factory,
        workflow_map,
        node_id: str,
        node_data: Dict[str, Any],
    ) -> None:
        super().__init__()
        self.factory = factory
        self.workflow_map = workflow_map
        self.node_id = node_id
        self.node_data = node_data
        self._get_form_values: Optional[WidgetGetter] = None

    def compose(self) -> ComposeResult:
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        schema = metadata.get("config_schema", {}) if metadata else {}
        config = self.node_data.get("config") or {}
        excluded_config_keys = {"membank_outputs", "membank_inputs"}
        if self.node_data.get("type") == "wait_until_node":
            excluded_config_keys.add("target_node_ids")
        schema = {
            key: value
            for key, value in schema.items()
            if key not in excluded_config_keys
        }
        core_config = {
            key: value
            for key, value in config.items()
            if key not in excluded_config_keys
        }
        form, getter = build_form(schema, core_config)
        self._get_form_values = getter

        with Vertical(id="modal-card", classes="node-config-modal"):
            yield Label(f"Edit Node: {self.node_data.get('alias') or self.node_id}", classes="modal-title")
            yield Static("Ctrl+S save  Ctrl+Enter save  Esc close  Tab moves focus", classes="modal-help")
            yield Label("Alias", classes="form-label")
            yield Input(value=self.node_data.get("alias", ""), id="alias-input")
            yield Static(self._format_metadata(metadata), id="node-config-summary")
            yield Label("Memory Bank Inputs", classes="form-label")
            yield from self._compose_membank_inputs(config)
            if self.node_data.get("type") == "wait_until_node":
                yield Label("Wait Targets", classes="form-label")
                yield from self._compose_wait_targets(config)
            yield Label("Node Settings", classes="form-label")
            yield form
            yield Label("Connections", classes="form-label")
            yield Static("Connection editing lives in the editor path tools.", classes="form-description")
            yield Static(self._format_connections(), id="connection-summary")
            yield Label("Memory Bank Outputs", classes="form-label")
            yield from self._compose_membank_outputs(config)
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save-node-config", variant="primary")
                yield Button("Cancel", id="cancel-node-config", variant="default")

    def on_mount(self) -> None:
        self.query_one("#alias-input", Input).focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-node-config":
            self.action_save()
        elif event.button.id == "cancel-node-config":
            self.action_cancel()

    def action_save(self) -> None:
        alias = self.query_one("#alias-input", Input).value
        config = self._get_form_values() if self._get_form_values else {}
        config.update(self._membank_config_values())
        config.update(self._wait_config_values())
        self.dismiss({"alias": alias, "config": config})

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _metadata_for_type(self, node_type: str) -> Optional[Dict[str, Any]]:
        for item in self.factory.get_node_types_metadata():
            if item["type"] == node_type:
                return item
        return None

    def _format_metadata(self, metadata: Optional[Dict[str, Any]]) -> str:
        if metadata is None:
            return "Unknown node type"
        inputs = ", ".join(metadata.get("input_ports") or []) or "-"
        outputs = ", ".join(metadata.get("output_ports") or []) or "-"
        return "\n".join(
            [
                f"Type: {metadata['type']}",
                f"Description: {metadata.get('description', '')}",
                f"Inputs: {inputs}",
                f"Outputs: {outputs}",
            ]
        )

    def _format_connections(self) -> str:
        self._refresh_node_data()
        connections = self.node_data.get("connections", {})
        outputs = connections.get("outputs", [])
        inputs = connections.get("inputs", [])
        lines = []
        if inputs:
            lines.append("  inputs:")
            for conn in inputs:
                source = conn.get("source_node_id", "?")
                source_node = self.workflow_map.get_node_data(source) or {}
                source_port = conn.get("source_port", "default")
                target_port = conn.get("target_port", "default")
                lines.append(
                    f"    {self._node_label(source, source_node)}.{source_port} -> {target_port}"
                )
        if outputs:
            lines.append("  outputs:")
            for conn in outputs:
                target = conn.get("target_node_id", "?")
                target_node = self.workflow_map.get_node_data(target) or {}
                source_port = conn.get("source_port", "default")
                target_port = conn.get("target_port", "default")
                lines.append(
                    f"    {source_port} -> {self._node_label(target, target_node)}.{target_port}"
                )
        if not inputs and not outputs:
            lines.append("  -")
        return "\n".join(lines)

    def _compose_membank_outputs(self, config: Dict[str, Any]):
        outputs = normalize_membank_outputs(config)
        enabled = bool(outputs)
        yield Checkbox("Writes to memory bank", value=enabled, id="membank-writes")
        yield Label("Number of outputs", classes="form-description")
        yield Input(
            value=str(len(outputs) if outputs else 0),
            type="integer",
            id="membank-output-count",
        )
        for index in range(MAX_MEMBANK_OUTPUT_ROWS):
            current = outputs[index] if index < len(outputs) else {}
            yield Label(f"Output {index + 1}", classes="form-description")
            with Horizontal(classes="connection-row"):
                yield Input(
                    value=current.get("id", ""),
                    id=f"membank-output-id-{index}",
                    placeholder="memory id",
                )
                yield Input(
                    value=current.get("description", ""),
                    id=f"membank-output-desc-{index}",
                    placeholder="description",
                )

    def _compose_membank_inputs(self, config: Dict[str, Any]):
        selected = set(normalize_membank_inputs(config))
        options = membank_input_options(self.workflow_map, self.node_id)
        enabled = bool(selected)
        yield Checkbox("Read from memory bank", value=enabled, id="membank-reads")
        if options:
            selection_options = [
                (label, value, value in selected)
                for label, value in options
            ]
            yield SelectionList(*selection_options, id="membank-inputs")
        else:
            yield Static("No upstream memory-bank outputs are available.", classes="form-description")

    def _compose_wait_targets(self, config: Dict[str, Any]):
        selected = set(normalize_wait_target_ids(config))
        options = wait_target_options(self.workflow_map, self.node_id)
        if options:
            selection_options = [
                (label, value, value in selected)
                for label, value in options
            ]
            yield SelectionList(*selection_options, id="wait-targets")
        else:
            yield Static("No non-downstream wait targets are available.", classes="form-description")

    def _membank_config_values(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {"membank_outputs": [], "membank_inputs": []}

        writes_enabled = self.query_one("#membank-writes", Checkbox).value
        try:
            count = int(self.query_one("#membank-output-count", Input).value)
        except ValueError:
            count = 0
        if writes_enabled and count > 0:
            for index in range(min(count, MAX_MEMBANK_OUTPUT_ROWS)):
                output_id = self.query_one(f"#membank-output-id-{index}", Input).value.strip()
                description = self.query_one(f"#membank-output-desc-{index}", Input).value.strip()
                if output_id:
                    values["membank_outputs"].append(
                        {"id": output_id, "description": description}
                    )

        reads_enabled = self.query_one("#membank-reads", Checkbox).value
        if reads_enabled:
            selection_lists = self.query("#membank-inputs")
            if selection_lists:
                values["membank_inputs"] = list(selection_lists.first().selected)
        return values

    def _wait_config_values(self) -> Dict[str, Any]:
        if self.node_data.get("type") != "wait_until_node":
            return {}
        selection_lists = self.query("#wait-targets")
        if not selection_lists:
            return {"target_node_ids": []}
        return {"target_node_ids": list(selection_lists.first().selected)}

    def _node_label(self, node_id: str, node: Dict[str, Any]) -> str:
        name = node.get("alias") or node.get("type") or node_id
        return f"{name} ({node_id})"

    def _refresh_node_data(self) -> None:
        self.node_data = self.workflow_map.get_node_data(self.node_id) or self.node_data

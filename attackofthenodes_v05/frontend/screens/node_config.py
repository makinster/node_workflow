"""Node configuration modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, SelectionList, Static, TabbedContent, TabPane, TextArea

from frontend.widgets.command_input import CommandInput, CommandTextArea
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
        output_id = str(entry.get("output") or entry.get("id") or "").strip()
        if not output_id:
            continue
        normalized.append(
            {
                "id": output_id,
                "output": output_id,
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
        options.append((f"Output Description: {description} | Output: {output_id}", output_id))
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


def merge_input_options(workflow_map, current_node_id: str) -> list[Dict[str, str]]:
    """Return current incoming merge inputs with human-readable descriptions."""
    node = workflow_map.get_node_data(current_node_id) or {}
    options: list[Dict[str, str]] = []
    for index, conn in enumerate(node.get("connections", {}).get("inputs", [])):
        source_id = conn.get("source_node_id", "?")
        source_node = workflow_map.get_node_data(source_id) or {}
        source_name = source_node.get("alias") or source_node.get("type") or source_id
        source_port = conn.get("source_port", "default")
        target_port = conn.get("target_port", "input")
        options.append(
            {
                "id": f"merge-input-choice-{index}",
                "port": str(target_port),
                "description": (
                    f"{source_name} ({source_id}).{source_port} -> {target_port}"
                ),
            }
        )
    return options


class NodeConfigScreen(ModalScreen):
    """Edit-node modal powered by the schema form generator."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+enter", "save", "Save"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        Binding("e", "activate_focused", "Activate", priority=True),
        Binding("enter", "activate_focused", "Activate", priority=True),
    ]

    def __init__(
        self,
        factory,
        workflow_map,
        node_id: str,
        node_data: Dict[str, Any],
        memory_bank=None,
    ) -> None:
        super().__init__()
        self.factory = factory
        self.workflow_map = workflow_map
        self.node_id = node_id
        self.node_data = node_data
        self.memory_bank = memory_bank
        self._get_form_values: Optional[WidgetGetter] = None
        self._nav_widget: Any = None
        self._initial_membank_outputs = normalize_membank_outputs(
            node_data.get("config") or {}
        )
        self._refreshing_membank_outputs = False

    def compose(self) -> ComposeResult:
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        schema = metadata.get("config_schema", {}) if metadata else {}
        schema = self._schema_with_generated_branch_labels(metadata, schema)
        config = self.node_data.get("config") or {}
        excluded_config_keys = {"membank_outputs", "membank_inputs"}
        if self.node_data.get("type") == "wait_until_node":
            excluded_config_keys.add("target_node_ids")
        if self.node_data.get("type") == "merge_node":
            excluded_config_keys.add("selected_input_port")
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
            yield Static("w = up, s = down    e = edit/select    esc = cancel/close", classes="modal-help")
            with VerticalScroll(id="node-config-scroll"):
                yield Label("Alias", classes="form-label nav-section")
                yield CommandInput(value=self.node_data.get("alias", ""), id="alias-input")
                yield Static(self._format_metadata(metadata), id="node-config-summary")
                pass_through_note = self._pass_through_note(metadata)
                if pass_through_note:
                    yield Static(pass_through_note, classes="form-description pass-through-note")
                yield Label("Previous Node Output", classes="form-label nav-section")
                yield Checkbox(
                    "Show previous node output",
                    value=False,
                    id="show-previous-output",
                )
                yield Static("", id="previous-output-preview", classes="form-description")
                yield Label("Memory Bank Inputs", classes="form-label nav-section")
                yield from self._compose_membank_inputs(config)
                if self.node_data.get("type") == "wait_until_node":
                    yield Label("Wait Targets", classes="form-label nav-section")
                    yield from self._compose_wait_targets(config)
                if self.node_data.get("type") == "merge_node":
                    yield Label("Merge Output Input", classes="form-label nav-section")
                    yield from self._compose_merge_inputs(config)
                yield form
                yield Label("Connections", classes="form-label nav-section")
                yield Static("Connection editing lives in the editor path tools.", classes="form-description")
                yield Static(self._format_connections(), id="connection-summary")
                if self._supports_membank_outputs(metadata):
                    yield Label("Memory Bank Outputs", classes="form-label nav-section")
                    yield from self._compose_membank_outputs(config)
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save-node-config", variant="primary")
                yield Button("Cancel", id="cancel-node-config", variant="default")

    def on_mount(self) -> None:
        self.query_one("#node-config-scroll").can_focus = False
        self.app.set_focus(self.query_one("#alias-input", CommandInput))
        self._sync_membank_output_controls()
        self._sync_previous_output_preview()
        self.call_after_refresh(
            lambda: self.app.set_focus(self.query_one("#alias-input", CommandInput))
        )
        self.set_timer(
            0.01,
            lambda: self.app.set_focus(self.query_one("#alias-input", CommandInput)),
        )

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        focused = self.app.focused
        if isinstance(focused, (CommandInput, CommandTextArea)) and focused.editing:
            if action in {"cursor_up", "cursor_down", "activate_focused", "cancel"}:
                return False
        return True

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "membank-writes":
            await self._refresh_membank_output_rows()
        elif event.checkbox.id == "show-previous-output":
            self._sync_previous_output_preview()
        elif str(event.checkbox.id or "").startswith("merge-input-choice-"):
            self._sync_merge_input_choices(event.checkbox)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "membank-output-count":
            await self._refresh_membank_output_rows()

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
        config.update(self._merge_config_values())
        self.dismiss({"alias": alias, "config": config})

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        self._move_keyboard_focus(-1)

    def action_cursor_down(self) -> None:
        self._move_keyboard_focus(1)

    def action_activate_focused(self) -> None:
        focused = self.app.focused
        if isinstance(focused, (CommandInput, CommandTextArea)):
            focused.begin_edit()
        elif isinstance(focused, Checkbox):
            focused.value = not focused.value
        elif isinstance(focused, Button):
            focused.press()

    def _move_keyboard_focus(self, direction: int) -> None:
        widgets = self._keyboard_focus_widgets()
        if not widgets:
            return
        current = self._nav_widget if self._nav_widget is not None else self.app.focused
        try:
            current_index = widgets.index(current)
        except ValueError:
            current_index = 0 if direction > 0 else len(widgets) - 1
        next_index = max(0, min(len(widgets) - 1, current_index + direction))
        target = widgets[next_index]

        if self._nav_widget is not None:
            try:
                self._nav_widget.remove_class("nav-highlight")
            except Exception:
                pass
            self._nav_widget = None

        interactive = (CommandInput, CommandTextArea, Checkbox, SelectionList, Select, TextArea, Button)
        if isinstance(target, interactive):
            if isinstance(target, (CommandInput, CommandTextArea)):
                target.end_edit()
            self.app.set_focus(target)
        else:
            self._nav_widget = target
            target.add_class("nav-highlight")
            self.app.set_focus(None)
        try:
            self.query_one("#node-config-scroll").scroll_to_widget(target, animate=False)
        except Exception:
            target.scroll_visible(animate=False)

    def _keyboard_focus_widgets(self) -> list[Any]:
        interactive = (
            CommandInput,
            CommandTextArea,
            Checkbox,
            SelectionList,
            Select,
            TextArea,
            Button,
        )
        inactive_pane_ids: set[str] = {
            pane.id
            for tc in self.query(TabbedContent)
            for pane in tc.query(TabPane)
            if pane.id and pane.id != tc.active
        }
        result = []
        for widget in self.query("*"):
            if self._in_inactive_tab(widget, inactive_pane_ids):
                continue
            if getattr(widget, "disabled", False):
                continue
            if not self._ancestor_visible(widget):
                continue
            if isinstance(widget, interactive):
                result.append(widget)
            elif isinstance(widget, Label) and "nav-section" in widget.classes:
                result.append(widget)
            elif isinstance(widget, Static) and widget.id in {
                "node-config-summary", "connection-summary"
            }:
                result.append(widget)
        return result

    def _in_inactive_tab(self, widget, inactive_pane_ids: set[str]) -> bool:
        if not inactive_pane_ids:
            return False
        node = widget.parent
        while node is not None and node is not self:
            if isinstance(node, TabPane) and node.id in inactive_pane_ids:
                return True
            node = node.parent
        return False

    def _ancestor_visible(self, widget) -> bool:
        """Return False if any ancestor up to self has display=False."""
        node = widget.parent
        while node is not None and node is not self:
            if not getattr(node, "display", True):
                return False
            node = node.parent
        return True

    def _metadata_for_type(self, node_type: str) -> Optional[Dict[str, Any]]:
        for item in self.factory.get_node_types_metadata():
            if item["type"] == node_type:
                return item
        return None

    def _schema_with_generated_branch_labels(
        self,
        metadata: Optional[Dict[str, Any]],
        schema: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        if metadata is None:
            return dict(schema)
        output_ports = list(metadata.get("output_ports") or [])
        if len(output_ports) <= 1:
            return dict(schema)

        # Strip any "Branch Names" group so all fields land in the default group
        # and no TabbedContent is created.
        enhanced = {
            key: ({k: v for k, v in field.items() if k != "group"} if field.get("group") == "Branch Names" else field)
            for key, field in schema.items()
        }
        for port in output_ports:
            key = f"{port}_label"
            enhanced.setdefault(
                key,
                {
                    "type": "string",
                    "label": f"{port} branch name",
                    "description": f"Editor display name for {port}",
                    "required": False,
                },
            )
        return enhanced

    def _supports_membank_outputs(self, metadata: Optional[Dict[str, Any]]) -> bool:
        if metadata is None:
            return True
        return len(metadata.get("output_ports") or []) <= 1

    def _pass_through_note(self, metadata: Optional[Dict[str, Any]]) -> str:
        if metadata is None:
            return ""
        hint = (metadata.get("ui_hints") or {}).get("pass_through")
        if hint:
            return f"Pass-through: {hint}"
        description = str(metadata.get("description") or "").lower()
        if "passes input through" in description or "passes it through" in description:
            return "Pass-through: forwards the previous node output to its own output."
        return ""

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

    def _previous_output_text(self) -> str:
        self._refresh_node_data()
        inputs = self.node_data.get("connections", {}).get("inputs", [])
        if not inputs:
            return "No upstream connection."
        connection = inputs[0]
        source_id = connection.get("source_node_id")
        source_port = connection.get("source_port", "default")
        source_node = self.workflow_map.get_node_data(source_id) if source_id else {}
        source_label = self._node_label(source_id or "?", source_node or {})
        prefix = f"Source: {source_label}.{source_port}"
        if self.memory_bank is None:
            return f"{prefix}\nNo captured run output is available yet."
        value = self.memory_bank.read_transient(source_id, source_port, default=None)
        if value is None:
            return f"{prefix}\nNo captured output yet. Run the workflow to populate it."
        rendered = repr(value)
        if len(rendered) > 800:
            rendered = f"{rendered[:797]}..."
        return f"{prefix}\n{rendered}"

    def _sync_previous_output_preview(self) -> None:
        checkbox_query = self.query("#show-previous-output")
        preview_query = self.query("#previous-output-preview")
        if not checkbox_query or not preview_query:
            return
        enabled = checkbox_query.first().value
        preview = preview_query.first()
        preview.display = enabled
        preview.update(self._previous_output_text() if enabled else "")

    def _compose_membank_outputs(self, config: Dict[str, Any]):
        outputs = normalize_membank_outputs(config)
        enabled = bool(outputs)
        count = len(outputs) if outputs else 0
        count_input = Input(
            value=str(count),
            id="membank-output-count",
            classes="compact-number-field",
        )
        count_input.disabled = not enabled
        yield Checkbox("Writes to memory bank", value=enabled, id="membank-writes")
        yield Label("Number of outputs", classes="form-description")
        yield count_input
        yield Vertical(id="membank-output-rows")

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

    def _compose_merge_inputs(self, config: Dict[str, Any]):
        selected = str(config.get("selected_input_port") or "").strip()
        options = merge_input_options(self.workflow_map, self.node_id)
        if not options:
            yield Static("No branch inputs are connected to this merge yet.", classes="form-description")
            return
        if not selected:
            selected = options[0]["port"]
        for option in options:
            yield Static(option["description"], classes="form-description")
            yield Checkbox(
                "Use this input as merge output",
                value=option["port"] == selected,
                id=option["id"],
            )

    def _sync_merge_input_choices(self, changed: Checkbox) -> None:
        if not changed.value:
            return
        for checkbox in self.query(Checkbox):
            checkbox_id = str(checkbox.id or "")
            if checkbox_id.startswith("merge-input-choice-") and checkbox is not changed:
                checkbox.value = False

    def _membank_config_values(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {"membank_outputs": [], "membank_inputs": []}

        writes_query = self.query("#membank-writes")
        if not writes_query:
            reads_enabled = self.query_one("#membank-reads", Checkbox).value
            if reads_enabled:
                selection_lists = self.query("#membank-inputs")
                if selection_lists:
                    values["membank_inputs"] = list(selection_lists.first().selected)
            return values

        writes_enabled = self.query_one("#membank-writes", Checkbox).value
        if writes_enabled:
            for output in self._current_membank_output_row_values():
                output_id = str(output.get("id") or "").strip()
                if not output_id:
                    continue
                values["membank_outputs"].append(
                    {
                        "id": output_id,
                        "output": output_id,
                        "description": str(output.get("description") or "").strip(),
                    }
                )

        reads_enabled = self.query_one("#membank-reads", Checkbox).value
        if reads_enabled:
            selection_lists = self.query("#membank-inputs")
            if selection_lists:
                values["membank_inputs"] = list(selection_lists.first().selected)
        return values

    def _sync_membank_output_controls(self) -> None:
        if not self.query("#membank-writes"):
            return
        writes_enabled = self.query_one("#membank-writes", Checkbox).value
        count_query = self.query("#membank-output-count")
        if not count_query:
            return
        count_input = count_query.first()
        count_input.disabled = not writes_enabled
        if writes_enabled and self._membank_output_count() <= 0:
            count_input.value = "1"

    async def _refresh_membank_output_rows(self) -> None:
        if self._refreshing_membank_outputs or not self.query("#membank-output-rows"):
            return
        self._refreshing_membank_outputs = True
        try:
            self._sync_membank_output_controls()
            container = self.query_one("#membank-output-rows", Vertical)
            values = self._current_membank_output_row_values()
            count = self._membank_output_count()
            writes_enabled = self.query_one("#membank-writes", Checkbox).value
            if not writes_enabled:
                count = 0
            await container.remove_children()
            await container.mount(*self._membank_output_row_widgets(values[:count]))
        finally:
            self._refreshing_membank_outputs = False

    def _current_membank_output_row_values(self) -> list[Dict[str, str]]:
        values: list[Dict[str, str]] = []
        row_count = max(self._membank_output_count(), len(self._initial_membank_outputs))
        for index in range(min(row_count, MAX_MEMBANK_OUTPUT_ROWS)):
            id_query = self.query(f"#membank-output-id-{index}")
            desc_query = self.query(f"#membank-output-desc-{index}")
            if id_query and desc_query:
                values.append(
                    {
                        "id": self._widget_text_value(id_query.first()),
                        "description": self._widget_text_value(desc_query.first()),
                    }
                )
            elif index < len(self._initial_membank_outputs):
                values.append(dict(self._initial_membank_outputs[index]))
            else:
                values.append({"id": "", "description": ""})
        return values

    def _membank_output_count(self) -> int:
        count_query = self.query("#membank-output-count")
        if not count_query:
            return 0
        try:
            count = int(count_query.first().value)
        except ValueError:
            count = 0
        return max(0, min(count, MAX_MEMBANK_OUTPUT_ROWS))

    def _membank_output_row_widgets(self, outputs: list[Dict[str, str]]) -> list[Any]:
        widgets: list[Any] = []
        for index, current in enumerate(outputs[:MAX_MEMBANK_OUTPUT_ROWS]):
            output_number = index + 1
            desc_input = CommandInput(
                value=current.get("description", ""),
                id=f"membank-output-desc-{index}",
                placeholder="Describe what this output contains",
                classes="membank-output-description-field",
            )
            output_input = CommandTextArea(
                current.get("id", ""),
                id=f"membank-output-id-{index}",
                classes="membank-output-field membank-output-textarea",
            )
            output_input.placeholder = "Memory-bank output key or output value"
            desc_input.styles.height = 3
            desc_input.styles.width = "100%"
            output_input.styles.height = 6
            output_input.styles.width = "100%"
            widgets.extend(
                [
                    Label(f"Output {output_number} Description:", classes="form-description"),
                    desc_input,
                    Label(f"Output {output_number}:", classes="form-description"),
                    output_input,
                    Static("", classes="membank-output-spacer"),
                ]
            )
        return widgets

    def _text_widget_value(self, selector: str) -> str:
        return self._widget_text_value(self.query_one(selector))

    def _widget_text_value(self, widget) -> str:
        if isinstance(widget, TextArea):
            return widget.text.strip()
        return str(getattr(widget, "value", "")).strip()

    def _wait_config_values(self) -> Dict[str, Any]:
        if self.node_data.get("type") != "wait_until_node":
            return {}
        selection_lists = self.query("#wait-targets")
        if not selection_lists:
            return {"target_node_ids": []}
        return {"target_node_ids": list(selection_lists.first().selected)}

    def _merge_config_values(self) -> Dict[str, Any]:
        if self.node_data.get("type") != "merge_node":
            return {}
        options = merge_input_options(self.workflow_map, self.node_id)
        for option in options:
            checkbox_query = self.query(f"#{option['id']}")
            if checkbox_query and checkbox_query.first().value:
                return {"selected_input_port": option["port"]}
        return {"selected_input_port": ""}

    def _node_label(self, node_id: str, node: Dict[str, Any]) -> str:
        name = node.get("alias") or node.get("type") or node_id
        return f"{name} ({node_id})"

    def _refresh_node_data(self) -> None:
        self.node_data = self.workflow_map.get_node_data(self.node_id) or self.node_data

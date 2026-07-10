"""Node configuration modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, SelectionList, Static, TabbedContent, TabPane, TextArea

from frontend.io_contract import TYPE_COLOR
from frontend.node_types import (
    BRANCH_END_NODE_TYPE,
    BRANCH_NODE_TYPE,
    END_NODE_TYPE,
    MERGE_NODE_TYPE,
    TEXT_OUTPUT_NODE_TYPE,
    WAIT_UNTIL_NODE_TYPE,
)
from frontend.node_io_display import (
    OUTPUT_NOT_CONFIGURED,
    metadata_for_type,
    normalize_membank_inputs,
    normalize_membank_outputs,
    node_display_name,
    normalize_transient_outputs,
    output_display_description,
    output_display_name,
    trace_transient_producer,
)
from frontend.widgets.command_navigation import (
    activate_command_widget,
    focus_command_widget,
    is_editing_text,
    move_select_overlay,
)
from frontend.widgets.command_input import CommandInput, CommandTextArea
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.dynamic_sections import (
    clamp_dynamic_row_count,
    dynamic_selection_rows,
    preserved_dynamic_rows,
    selected_values_from_widget,
)
from frontend.widgets.form_generator import (
    WidgetGetter,
    apply_field_rules,
    build_form,
    mutual_exclusion_targets,
    schema_has_field_rules,
)
from frontend.widgets.status_bar import StatusBar


MAX_MEMBANK_OUTPUT_ROWS = 5
BRANCH_PORTS = ["path_a", "path_b", "path_c", "path_d", "path_e"]
MIN_BRANCH_COUNT = 2
MAX_BRANCH_COUNT = 5
LEGACY_BRANCH_CONFIG_KEYS = {
    "condition",
    "match_value",
    "match_mode",
    "case_sensitive",
    "on_match",
    "on_no_match",
}


class PayloadPreview(Static):
    """Read-only payload preview that participates in command navigation."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.can_focus = True
        self.add_class("payload-preview")


def _branch_count_from_config(config: Dict[str, Any]) -> int:
    try:
        count = int(config.get("branch_count", MIN_BRANCH_COUNT))
    except (TypeError, ValueError):
        count = MIN_BRANCH_COUNT
    return max(MIN_BRANCH_COUNT, min(MAX_BRANCH_COUNT, count))


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
        writers.discard(current_node_id)
        if not writers:
            continue
        if writers and writers.issubset(downstream):
            continue
        description = entry.get("description") or "No description"
        options.append((f"Vault: {output_id} - {description}", output_id))
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
    """Return Merge Beacon branches that this merge may close."""
    merge_input_ports = ["path_a", "path_b", "path_c", "path_d", "path_e"]
    options: list[Dict[str, str]] = []
    branch_contexts = _branch_contexts_by_node(workflow_map)
    merge_branch_keys = {
        (context["branch_id"], context["branch_port"])
        for context in branch_contexts.get(current_node_id, [])
    }
    used_merge_ports = _reserved_merge_input_ports(workflow_map, current_node_id)
    downstream_ids = _descendant_node_ids(workflow_map, current_node_id)
    seen_beacons: set[str] = set()

    for beacon_id, beacon_node in workflow_map.get_all_node_data().items():
        if beacon_node.get("type") != BRANCH_END_NODE_TYPE or beacon_id in seen_beacons:
            continue
        context = _select_beacon_branch_context(
            branch_contexts.get(beacon_id, []),
            merge_branch_keys,
        )
        if context is None:
            continue
        if context["branch_id"] in downstream_ids:
            # This branch only starts after passing through the merge node
            # being configured (it's downstream of it) — it cannot close here.
            continue
        seen_beacons.add(beacon_id)
        branch_id = context["branch_id"]
        branch_port = context["branch_port"]
        target_port = _connected_merge_target_port(beacon_node, current_node_id)
        if not target_port:
            target_port = _available_merge_input_port(
                branch_port,
                len(options),
                merge_input_ports,
                used_merge_ports,
            )
        used_merge_ports.add(str(target_port))
        output = _beacon_output_details(workflow_map, beacon_node)
        beacon_name = beacon_node.get("alias") or "Merge Beacon"
        branch_label = context["branch_label"]
        branch_path = context.get("branch_path") or branch_label
        options.append(
            {
                "id": f"merge-input-choice-{len(options)}",
                "port": str(target_port),
                "branch_id": branch_id,
                "branch_port": branch_port,
                "branch_label": branch_label,
                "branch_path": branch_path,
                "branch_end_id": beacon_id,
                "branch_end": f"{beacon_name} ({beacon_id})",
                "last_node": f"{beacon_name} ({beacon_id})",
                "source_port": "default",
                "description": f"Branch: {branch_path}",
                "output_name": output["name"],
                "output_description": output["description"],
            }
        )
    return options


def _descendant_node_ids(workflow_map, source_id: str) -> set[str]:
    """Return every node id reachable forward from source_id."""
    descendants: set[str] = set()
    queue = [source_id]
    while queue:
        candidate = queue.pop()
        node = workflow_map.get_node_data(candidate)
        if node is None:
            continue
        for conn in node.get("connections", {}).get("outputs", []):
            dest = str(conn.get("target_node_id") or "")
            if dest and dest not in descendants:
                descendants.add(dest)
                queue.append(dest)
    return descendants


def _branch_contexts_by_node(workflow_map) -> Dict[str, list[Dict[str, str]]]:
    """Map nodes to the branch path contexts that can reach them."""
    contexts: Dict[str, list[Dict[str, str]]] = {}
    start_id = workflow_map.find_start_node_id()
    if not start_id:
        return contexts

    def add_context(node_id: str, context: Optional[Dict[str, str]]) -> None:
        if not context:
            return
        existing = contexts.setdefault(node_id, [])
        key = (context["branch_id"], context["branch_port"])
        if all((item["branch_id"], item["branch_port"]) != key for item in existing):
            existing.append(context)

    def follow(node_id: str, context: Optional[Dict[str, str]], seen: set[tuple[str, str, str]]) -> None:
        node = workflow_map.get_node_data(node_id) or {}
        if not node:
            return
        state = (
            node_id,
            context["branch_id"] if context else "",
            context["branch_port"] if context else "",
        )
        if state in seen:
            return
        seen.add(state)
        add_context(node_id, context)
        if node.get("type") == BRANCH_END_NODE_TYPE:
            return
        output_ports = _node_output_ports(workflow_map, node)
        outputs = node.get("connections", {}).get("outputs", [])
        if len(output_ports) > 1:
            for output_port in output_ports:
                target_id = _target_for_output(node, output_port)
                if not target_id:
                    continue
                next_context = {
                    "branch_id": node_id,
                    "branch_port": output_port,
                    "branch_label": _branch_label(node, output_port),
                }
                next_context["branch_path"] = _branch_path_label(
                    context,
                    next_context["branch_label"],
                )
                follow(target_id, next_context, set(seen))
            return
        for conn in outputs:
            target_id = str(conn.get("target_node_id") or "")
            if target_id:
                follow(target_id, context, set(seen))

    follow(start_id, None, set())
    return contexts


def _select_beacon_branch_context(
    contexts: list[Dict[str, str]],
    merge_branch_keys: set[tuple[str, str]],
) -> Optional[Dict[str, str]]:
    for context in reversed(contexts):
        if (context["branch_id"], context["branch_port"]) not in merge_branch_keys:
            return context
    return None


def _branch_label(branch_node: Dict[str, Any], branch_port: str) -> str:
    config = branch_node.get("config") or {}
    label = str(config.get(f"{branch_port}_label") or "").strip()
    return label or branch_port.replace("_", " ").title()


def _branch_path_label(context: Optional[Dict[str, str]], branch_label: str) -> str:
    if context and context.get("branch_path"):
        return f"{context['branch_path']} -> {branch_label}"
    return branch_label


def _target_for_output(node: Dict[str, Any], source_port: str) -> str:
    for conn in node.get("connections", {}).get("outputs", []):
        if str(conn.get("source_port", "default")) == source_port:
            return str(conn.get("target_node_id") or "")
    return ""


def _connected_merge_target_port(beacon_node: Dict[str, Any], merge_node_id: str) -> str:
    for conn in beacon_node.get("connections", {}).get("outputs", []):
        if str(conn.get("target_node_id") or "") == merge_node_id:
            return str(conn.get("target_port") or "")
    return ""


def _beacon_output_details(workflow_map, beacon_node: Dict[str, Any]) -> Dict[str, str]:
    inputs = beacon_node.get("connections", {}).get("inputs", [])
    if inputs:
        source_id = str(inputs[0].get("source_node_id") or "")
        source_port = str(inputs[0].get("source_port") or "default")
        source_node = workflow_map.get_node_data(source_id) or {}
        if source_node:
            return _source_output_details(source_node, source_port)
    return _source_output_details(beacon_node, "default")


def _node_output_ports(workflow_map, node: Dict[str, Any]) -> list[str]:
    factory = getattr(workflow_map, "_factory", None)
    node_type = node.get("type")
    if factory is not None:
        for metadata in factory.get_node_types_metadata():
            if metadata.get("type") == node_type:
                ports = [str(port) for port in metadata.get("output_ports") or []]
                if node_type == BRANCH_NODE_TYPE:
                    return ports[: _branch_count_from_config(node.get("config") or {})]
                return ports
    outputs = node.get("connections", {}).get("outputs", [])
    return sorted({str(conn.get("source_port", "default")) for conn in outputs})


def _trace_branch_path(
    workflow_map,
    branch_id: str,
    branch_port: str,
    current_merge_id: str,
) -> Dict[str, Any]:
    node = workflow_map.get_node_data(branch_id) or {}
    current_id = branch_id
    current_port = branch_port
    last_node_id = branch_id
    last_node = node
    last_port = branch_port
    seen: set[str] = set()

    while True:
        if current_id in seen:
            return {
                "status": "open",
                "target_port": "",
                "last_node_id": last_node_id,
                "last_node": last_node,
                "last_port": last_port,
            }
        seen.add(current_id)
        current_node = workflow_map.get_node_data(current_id) or {}
        outputs = current_node.get("connections", {}).get("outputs", [])
        next_conn = next(
            (
                conn
                for conn in outputs
                if str(conn.get("source_port", "default")) == current_port
            ),
            None,
        )
        if next_conn is None and current_port != "default":
            next_conn = next(
                (
                    conn
                    for conn in outputs
                    if str(conn.get("source_port", "default")) == "default"
                ),
                None,
            )
        if next_conn is None:
            status = "closed" if _node_closes_branch(current_node) else "open"
            return {
                "status": status,
                "target_port": "",
                "last_node_id": current_id,
                "last_node": current_node,
                "last_port": current_port,
            }
        target_id = str(next_conn.get("target_node_id") or "")
        target_port = str(next_conn.get("target_port") or "")
        source_port = str(next_conn.get("source_port", "default"))
        target_node = workflow_map.get_node_data(target_id) or {}
        if target_id == current_merge_id:
            return {
                "status": "current_merge",
                "target_port": target_port,
                "last_node_id": current_id,
                "last_node": current_node,
                "last_port": source_port,
            }
        if target_node.get("type") == MERGE_NODE_TYPE:
            return {
                "status": "closed",
                "target_port": target_port,
                "last_node_id": current_id,
                "last_node": current_node,
                "last_port": source_port,
            }
        current_id = target_id
        current_port = "default"
        last_node_id = current_id
        last_node = target_node
        last_port = source_port


def _node_closes_branch(node: Dict[str, Any]) -> bool:
    return node.get("type") in {END_NODE_TYPE, TEXT_OUTPUT_NODE_TYPE}


def _default_merge_input_port(
    branch_port: str,
    option_index: int,
    merge_input_ports: list[str],
) -> str:
    if branch_port in merge_input_ports:
        return branch_port
    if option_index < len(merge_input_ports):
        return merge_input_ports[option_index]
    return merge_input_ports[-1]


def _available_merge_input_port(
    branch_port: str,
    option_index: int,
    merge_input_ports: list[str],
    used_ports: set[str],
) -> str:
    preferred = _default_merge_input_port(branch_port, option_index, merge_input_ports)
    if preferred not in used_ports:
        return preferred
    for port in merge_input_ports:
        if port not in used_ports:
            return port
    return preferred


def _reserved_merge_input_ports(workflow_map, merge_node_id: str) -> set[str]:
    merge_node = workflow_map.get_node_data(merge_node_id) or {}
    reserved: set[str] = set()
    for conn in merge_node.get("connections", {}).get("inputs", []):
        source_id = str(conn.get("source_node_id") or "")
        source_node = workflow_map.get_node_data(source_id) or {}
        if source_node.get("type") == BRANCH_END_NODE_TYPE:
            continue
        target_port = str(conn.get("target_port") or "")
        if target_port:
            reserved.add(target_port)
    return reserved


def _source_output_details(source_node: Dict[str, Any], source_port: str) -> Dict[str, str]:
    outputs = normalize_membank_outputs(source_node.get("config") or {})
    for output in outputs:
        output_id = output.get("id") or output.get("output") or ""
        if output_id == source_port:
            return {
                "name": output_id,
                "description": output.get("description") or "No description",
            }
    if len(outputs) == 1:
        output = outputs[0]
        return {
            "name": output.get("id") or output.get("output") or source_port,
            "description": output.get("description") or "No description",
        }
    return {"name": source_port, "description": OUTPUT_NOT_CONFIGURED}


def _upstream_branch_label(
    workflow_map,
    source_node_id: str,
    merge_node_id: str,
    target_port: str,
) -> str:
    label, _ = upstream_branch_info(
        workflow_map,
        source_node_id,
        merge_node_id,
        target_port,
    )
    return label


def upstream_branch_info(
    workflow_map,
    source_node_id: str,
    merge_node_id: str,
    target_port: str,
) -> tuple[str, str]:
    visited: set[str] = set()
    stack = [source_node_id]
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        node = workflow_map.get_node_data(node_id) or {}
        for input_conn in node.get("connections", {}).get("inputs", []):
            upstream_id = input_conn.get("source_node_id")
            upstream_node = workflow_map.get_node_data(upstream_id) if upstream_id else {}
            upstream_outputs = _node_output_ports(workflow_map, upstream_node) if upstream_node else []
            output_count = len(upstream_outputs)
            source_port = str(input_conn.get("source_port", "default"))
            if output_count > 1:
                config = upstream_node.get("config") or {}
                label = str(config.get(f"{source_port}_label") or "").strip()
                if label:
                    return label, f"{upstream_id}:{source_port}"
                return source_port.replace("_", " ").title(), f"{upstream_id}:{source_port}"
            if upstream_id:
                stack.append(upstream_id)
    return target_port.replace("_", " ").title(), target_port


class NodeConfigScreen(CommandScreenMixin, ModalScreen):
    """Edit-node modal powered by the schema form generator."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+enter", "save", "Save"),
        # Tabs switch by number key (1-5). A/D are within-row navigation,
        # supplied by CommandScreenMixin.
        Binding("1", "jump_config_tab(1)", "Tab 1", priority=True),
        Binding("2", "jump_config_tab(2)", "Tab 2", priority=True),
        Binding("3", "jump_config_tab(3)", "Tab 3", priority=True),
        Binding("4", "jump_config_tab(4)", "Tab 4", priority=True),
        Binding("5", "jump_config_tab(5)", "Tab 5", priority=True),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
    ]

    def __init__(
        self,
        factory,
        workflow_map,
        node_id: str,
        node_data: Dict[str, Any],
        memory_bank=None,
        secrets_manager=None,
    ) -> None:
        super().__init__()
        self.factory = factory
        self.workflow_map = workflow_map
        self.node_id = node_id
        self.node_data = node_data
        self.memory_bank = memory_bank
        self.secrets_manager = secrets_manager
        self._get_form_values: Optional[WidgetGetter] = None
        self._nav_widget: Any = None
        self._initial_membank_outputs = normalize_membank_outputs(
            node_data.get("config") or {}
        )
        self._initial_transient_outputs = normalize_transient_outputs(
            node_data.get("config") or {}
        )
        self._refreshing_membank_outputs = False
        self._rule_schema: Dict[str, Dict[str, Any]] = {}
        self._generated_config_schema: Dict[str, Dict[str, Any]] = {}
        self._source_select_base_options: Dict[str, list[tuple[Any, Any]]] = {}
        self._vault_select_base_options: Dict[str, list[tuple[Any, Any]]] = {}

    def compose(self) -> ComposeResult:
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        schema = metadata.get("config_schema", {}) if metadata else {}
        if self.node_data.get("type") != BRANCH_NODE_TYPE:
            schema = self._schema_with_generated_branch_labels(metadata, schema)
        config = self.node_data.get("config") or {}
        excluded_config_keys = {"membank_outputs", "membank_inputs", "transient_outputs"}
        if self._uses_standard_source_model(metadata):
            # Routing state renders through the composed Downstream/Vault
            # payload controls; stale schema checkbox fields (pre-2026-07-08
            # generated nodes) must not double-render.
            excluded_config_keys.update(
                {
                    "transient_output",
                    "dead_drop_passthrough",
                    "vault_write",
                    "vault_write_key",
                    "vault_write_description",
                }
            )
        if self.node_data.get("type") == BRANCH_NODE_TYPE:
            excluded_config_keys.update(
                {
                    "branch_count",
                    "branch_payload_sources",
                    *LEGACY_BRANCH_CONFIG_KEYS,
                    *(f"{port}_label" for port in BRANCH_PORTS),
                }
            )
        if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
            excluded_config_keys.add("target_node_ids")
        if self.node_data.get("type") == MERGE_NODE_TYPE:
            excluded_config_keys.update(
                {
                    "branches_to_close",
                    "carry_forward_branch_id",
                    "selected_branch_id",
                    "selected_input_port",
                    "branch_output_name",
                    "branch_output_description",
                }
            )
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
        forms, getter = self._build_standard_config_forms(schema, core_config)
        self._get_form_values = getter
        self._rule_schema = (
            self._generated_config_schema
            if schema_has_field_rules(self._generated_config_schema)
            else {}
        )

        with Vertical(id="modal-card", classes="node-config-modal"):
            title = f"{self.node_data.get('alias') or self.node_id} ({self.node_id})"
            yield Label(f"Edit Node: {title}", classes="modal-title")
            help_text = "w/s move | a/d tabs | e interact | ctrl+s save | esc cancel | ctrl+q revert"
            yield Static(
                help_text,
                classes="modal-help",
            )
            if self.node_data.get("type") == MERGE_NODE_TYPE:
                with VerticalScroll(id="node-config-scroll"):
                    yield Label("Branches To Close", classes="form-label nav-section")
                    yield from self._compose_merge_inputs(config)
            elif self.node_data.get("type") == BRANCH_END_NODE_TYPE:
                with VerticalScroll(id="node-config-scroll"):
                    yield Static(
                        self._branch_end_status_text(),
                        classes="form-description",
                    )
            elif self.node_data.get("type") == BRANCH_NODE_TYPE:
                yield from self._compose_branch_config_tabs(metadata, config)
            else:
                yield from self._compose_standard_config_tabs(
                    metadata,
                    config,
                    forms,
                )
            with Vertical(classes="button-row"):
                yield Button("Save", id="save-node-config", variant="primary")
                yield Button("Cancel", id="cancel-node-config", variant="default")
            yield StatusBar(help_text)

    def _compose_standard_config_tabs(
        self,
        metadata: Optional[Dict[str, Any]],
        config: Dict[str, Any],
        forms: Dict[str, Any],
    ):
        standard_model = self._uses_standard_source_model(metadata)
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 - Source", id="node-config-tab-core"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Horizontal(
                        Label("Alias:", classes="form-label-inline"),
                        CommandInput(value=self._alias_default_value(), id="alias-input"),
                        classes="form-inline-row",
                        id="alias-row",
                    )
                    yield Static(self._format_metadata(metadata), id="node-config-summary")
                    if standard_model:
                        # Standard-model nodes show the incoming payload up
                        # front; the reveal checkboxes and the legacy vault
                        # selection list are replaced by per-input source
                        # selectors with typed vault dropdowns.
                        yield from self._compose_incoming_payload_summary(metadata)
                    if forms.get("source") is not None:
                        yield forms["source"]
                    pass_through_note = self._pass_through_note(metadata)
                    if pass_through_note:
                        yield Static(pass_through_note, classes="form-description pass-through-note")
                    if not standard_model:
                        yield Label("Upstream Payload", classes="form-label nav-section")
                        yield Checkbox(
                            "Reveal upstream payload",
                            value=False,
                            id="show-previous-output",
                        )
                        yield PayloadPreview("", id="previous-output-preview", classes="form-description")
                        yield from self._compose_membank_inputs(config)
                        yield from self._compose_vault_payload_preview("source")
                    if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
                        yield Label("Wait Targets", classes="form-label nav-section")
                        yield from self._compose_wait_targets(config)

            with TabPane("2 - Parameters", id="node-config-tab-parameters"):
                with VerticalScroll(classes="tab-scroll"):
                    if forms.get("parameters") is not None:
                        yield forms["parameters"]
                    else:
                        yield Static("No parameters.", classes="form-description")

            with TabPane("3 - Payloads", id="node-config-tab-outputs"):
                with VerticalScroll(classes="tab-scroll"):
                    if standard_model:
                        # New output model: one designated Downstream node
                        # payload, optional Vault payloads, then the schema
                        # Payloads fields (AI Session) at the bottom.
                        yield from self._compose_standard_payloads(metadata, config)
                        if forms.get("payloads") is not None:
                            yield forms["payloads"]
                    else:
                        yield Label("Incoming Payloads", classes="form-label nav-section")
                        yield Checkbox(
                            "Reveal upstream payload",
                            value=False,
                            id="show-payload-upstream-payload",
                        )
                        yield PayloadPreview("", id="payload-upstream-payload-preview", classes="form-description")
                        yield from self._compose_vault_payload_preview("payload")
                        if forms.get("payloads") is not None:
                            yield forms["payloads"]
                        yield Label("Dead Drop Payloads", classes="form-label nav-section")
                        yield from self._compose_transient_outputs(metadata, config)
                        if self._supports_membank_outputs(metadata):
                            yield Label("Vault Payloads", classes="form-label nav-section")
                            yield from self._compose_membank_outputs(config)

            with TabPane("4 - Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Connections", classes="form-label nav-section")
                    yield Static(
                        "Edit connections from the editor.",
                        classes="form-description",
                    )
                    yield Static(self._format_connections(), id="connection-summary")

    def _compose_branch_config_tabs(
        self,
        metadata: Optional[Dict[str, Any]],
        config: Dict[str, Any],
    ):
        branch_count = _branch_count_from_config(config)
        source_options = self._branch_payload_source_options(config)
        payload_sources = config.get("branch_payload_sources") or {}
        if not isinstance(payload_sources, dict):
            payload_sources = {}
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 - Source", id="node-config-tab-core"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Horizontal(
                        Label("Alias:", classes="form-label-inline"),
                        CommandInput(value=self._alias_default_value(), id="alias-input"),
                        classes="form-inline-row",
                        id="alias-row",
                    )
                    yield Static(
                        "\n".join(
                            [
                                "Node type: Parallel Branch",
                                "- Duplicates the incoming payload across branch paths.",
                                "- Parallel paths run independently",
                                "- Conditional branching hidden for a later node pass",
                            ]
                        ),
                        id="node-config-summary",
                        classes="form-description",
                    )
                    yield Checkbox(
                        "Reveal upstream payload",
                        value=False,
                        id="show-previous-output",
                    )
                    yield PayloadPreview("", id="previous-output-preview", classes="form-description")
                    yield from self._compose_membank_inputs(config)
                    yield from self._compose_vault_payload_preview("source")

            with TabPane("2 - Parameters", id="node-config-tab-parameters"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Branches", classes="form-label nav-section")
                    yield CommandInput(
                        value=str(branch_count),
                        type="integer",
                        id="branch-count",
                        classes="compact-number-field",
                    )
                    yield Static("Choose 2 to 5 spawn points.", classes="form-description")

            with TabPane("3 - Payloads", id="node-config-tab-outputs"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Incoming Payloads", classes="form-label nav-section")
                    yield Checkbox(
                        "Reveal upstream payload",
                        value=False,
                        id="show-payload-upstream-payload",
                    )
                    yield PayloadPreview("", id="payload-upstream-payload-preview", classes="form-description")
                    yield from self._compose_vault_payload_preview("payload")
                    yield Vertical(
                        *self._branch_payload_row_widgets(
                            branch_count,
                            source_options,
                            payload_sources,
                            config,
                        ),
                        id="branch-payload-rows",
                    )

            with TabPane("4 - Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Connections", classes="form-label nav-section")
                    yield Static(
                        "Edit connections from the editor.",
                        classes="form-description",
                    )
                    yield Static(self._format_connections(), id="connection-summary")

    def _build_standard_config_forms(
        self,
        schema: Dict[str, Dict[str, Any]],
        values: Dict[str, Any],
    ) -> tuple[Dict[str, Any], WidgetGetter]:
        vault_keys_by_type = self._vault_key_options(schema)
        schema = self._prune_unavailable_source_options(
            schema, vault_keys_by_type, values
        )
        self._generated_config_schema = schema
        self._source_select_base_options = {
            field_name: [
                (str(option), option) for option in field_schema.get("options", [])
            ]
            for field_name, field_schema in schema.items()
            if field_name.endswith("_source") and field_schema.get("type") == "select"
        }
        self._vault_select_base_options = {}
        schemas = self._schema_by_top_level_config_tab(schema)
        forms: Dict[str, Any] = {}
        getters: list[WidgetGetter] = []
        for tab_name, tab_schema in schemas.items():
            if not tab_schema:
                forms[tab_name] = None
                continue
            form, getter = build_form(
                tab_schema,
                values,
                secret_keys=self._secret_key_options(),
                vault_keys_by_type=vault_keys_by_type,
            )
            forms[tab_name] = form
            getters.append(getter)

        def get_values() -> Dict[str, Any]:
            merged: Dict[str, Any] = {}
            for getter in getters:
                merged.update(getter())
            return merged

        return forms, get_values

    def _secret_key_options(self) -> list[str] | None:
        if self.secrets_manager is None:
            return None
        try:
            return list(self.secrets_manager.list_keys())
        except Exception:
            return []

    def _vault_key_options(
        self,
        schema: Dict[str, Dict[str, Any]],
    ) -> Dict[str, list[tuple[str, str]]] | None:
        """Selectable `(label, key)` vault options per type tag.

        Fields declaring a ``vault_type`` schema key render as a dropdown over
        these options (IO_CONTRACT_UI_DESIGN.md §3). Keys come from persisted
        vault entries of a compatible tag plus keys declared by workflow-node
        writers, so wiring works before the first run. Compatibility: exact
        tag match always; untagged (legacy) entries also satisfy ``string``;
        ``any`` accepts everything. Labels render as ``key [type]``.
        """
        tags = sorted(
            {
                str(field_schema.get("vault_type"))
                for field_schema in schema.values()
                if isinstance(field_schema, dict) and field_schema.get("vault_type")
            }
        )
        if not tags:
            return None

        # Eligibility (applied to EVERY candidate, persisted or declared): a
        # key is offered only if some writer other than this node — and not
        # solely downstream of it on the same branch — declares it. A key whose
        # only declared writer is this node (e.g. a session it created, which
        # persists in the store after a run) must NOT be offered back to
        # itself. Parallel-branch writers stay eligible (static analysis cannot
        # rank branch timing; the validator's race warning covers that).
        declared = self._declared_vault_writer_keys()
        try:
            downstream = set(self.workflow_map.nodes_reachable_from(self.node_id) or set())
        except Exception:
            downstream = set()

        def eligible(key: str) -> bool:
            info = declared.get(key)
            if info is None:
                # No workflow node declares it — external/legacy vault entry,
                # not attributable to this node, so it is fair game.
                return True
            writers = set(info.get("writers") or set()) - {self.node_id}
            return bool(writers) and not (writers <= downstream)

        # (key -> tag) from persisted vault entries; "" marks untagged/legacy.
        candidates: Dict[str, str] = {}
        if self.memory_bank is not None:
            try:
                state = self.memory_bank.get_state()
                entry_tags = state.get("persistent_type_tags") or {}
                for key in state.get("persistent") or {}:
                    if eligible(str(key)):
                        candidates[str(key)] = str(entry_tags.get(key) or "")
            except Exception:
                pass
        # Declared writers win the more specific tag; same eligibility gate.
        for key, info in declared.items():
            if not eligible(key):
                continue
            tag = str(info.get("tag") or "")
            if tag or key not in candidates:
                candidates[key] = tag

        def compatible(entry_tag: str, wanted: str) -> bool:
            if wanted == "any" or entry_tag == wanted:
                return True
            return entry_tag == "" and wanted == "string"

        options: Dict[str, list[tuple[str, str]]] = {}
        for wanted in tags:
            rows = [
                (f"{key} [{entry_tag}]" if entry_tag else key, key)
                for key, entry_tag in sorted(candidates.items())
                if compatible(entry_tag, wanted)
            ]
            options[wanted] = rows
        return options

    def _declared_vault_writer_keys(self) -> Dict[str, Dict[str, Any]]:
        """Vault keys declared by workflow nodes: key -> {tag, writers}.

        Covers legacy ``membank_outputs`` declarations (untagged), standard
        result routing (``vault_write_key`` — tagged with the writer's default
        output type), and AI session keys (``ai_session``). Writer node ids
        power the same-branch eligibility filter in ``_vault_key_options``.
        """
        declared: Dict[str, Dict[str, Any]] = {}

        def add(key: str, tag: str, writer_id: str) -> None:
            entry = declared.setdefault(key, {"tag": "", "writers": set()})
            if tag:
                entry["tag"] = tag
            if writer_id:
                entry["writers"].add(str(writer_id))

        for output_id, registry_entry in build_membank_registry(self.workflow_map).items():
            for writer in registry_entry.get("writers") or []:
                add(str(output_id), "", str(writer))
        try:
            all_nodes = self.workflow_map.get_all_node_data()
        except Exception:
            return declared
        for node_id, node_data in all_nodes.items():
            config = node_data.get("config") or {}
            if config.get("vault_write"):
                key = str(config.get("vault_write_key") or "").strip()
                if key:
                    meta = self._metadata_for_type(node_data.get("type", "")) or {}
                    out_meta = (meta.get("output_port_metadata") or {}).get("default") or {}
                    add(key, str(out_meta.get("data_type") or ""), str(node_id))
            if config.get("use_chat_session"):
                session_key = str(config.get("session_key") or "").strip()
                if session_key:
                    add(session_key, "ai_session", str(node_id))
        return declared

    def _prune_unavailable_source_options(
        self,
        schema: Dict[str, Dict[str, Any]],
        vault_keys_by_type: Dict[str, list[tuple[str, str]]] | None,
        values: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Hide source options whose revealed vault dropdown has no entries.

        A select option that only reveals an empty typed vault dropdown (e.g.
        "Continue AI session" with no eligible sessions, or "Vault" with no
        compatible vault keys) is dropped from the selector. A saved value is
        kept selectable so existing configs still display faithfully.
        """
        if vault_keys_by_type is None:
            return schema
        removals: Dict[str, set] = {}
        for field_schema in schema.values():
            if not isinstance(field_schema, dict) or not field_schema.get("vault_type"):
                continue
            condition = field_schema.get("visible_when")
            if not isinstance(condition, dict) or len(condition) != 1:
                continue
            (select_name, option_value), = condition.items()
            select_schema = schema.get(select_name) or {}
            if select_schema.get("type") != "select" or not isinstance(option_value, str):
                continue
            if not vault_keys_by_type.get(str(field_schema["vault_type"])):
                removals.setdefault(select_name, set()).add(option_value)
        if not removals:
            return schema
        adjusted = dict(schema)
        for select_name, gone in removals.items():
            select_schema = dict(adjusted[select_name])
            options = [
                option
                for option in select_schema.get("options", [])
                if option not in gone
            ]
            current = values.get(select_name, select_schema.get("default"))
            if current in gone and current not in options:
                options.append(current)
            select_schema["options"] = options
            adjusted[select_name] = select_schema
        return adjusted

    def _schema_by_top_level_config_tab(
        self,
        schema: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        tabs: Dict[str, Dict[str, Dict[str, Any]]] = {
            "source": {},
            "parameters": {},
            "payloads": {},
        }
        for field_name, field_schema in schema.items():
            tab_name = self._normalize_config_tab_name(field_schema.get("tab"))
            tabs[tab_name][field_name] = field_schema
        return tabs

    def _normalize_config_tab_name(self, tab_name: Any) -> str:
        value = str(tab_name or "parameters").strip().lower()
        if value in {"source", "core"}:
            return "source"
        if value in {"payload", "payloads", "output", "outputs"}:
            return "payloads"
        return "parameters"

    def _branch_payload_source_options(
        self,
        config: Optional[Dict[str, Any]] = None,
    ) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = [("Upstream payload", "dead_drop:input")]
        selected_vault = self._selected_vault_inputs(config)
        registry = build_membank_registry(self.workflow_map)
        for output_id in selected_vault:
            description = str((registry.get(output_id) or {}).get("description") or "").strip()
            label = f"Vault: {output_id}"
            if description:
                label = f"{label} - {description}"
            options.append((label, f"vault:{output_id}"))
        return options

    def _selected_vault_inputs(self, config: Optional[Dict[str, Any]] = None) -> list[str]:
        if config is not None:
            return normalize_membank_inputs(config)
        reads_query = self.query("#membank-reads")
        if reads_query and not reads_query.first().value:
            return []
        selection_query = self.query("#membank-inputs")
        if selection_query:
            return list(selected_values_from_widget(selection_query.first()))
        return normalize_membank_inputs(config or self.node_data.get("config") or {})

    def _branch_payload_row_widgets(
        self,
        branch_count: int,
        source_options: list[tuple[str, str]],
        payload_sources: Dict[str, Any],
        config: Dict[str, Any],
    ) -> list[Any]:
        widgets: list[Any] = []
        for index, port in enumerate(BRANCH_PORTS):
            label = str(
                config.get(f"{port}_label") or f"Branch {index + 1}"
            )
            selected_source = str(payload_sources.get(port) or "dead_drop:input")
            valid_values = {value for _, value in source_options}
            if selected_source not in valid_values:
                selected_source = "dead_drop:input"
            row = Vertical(
                Label("Spawn Point:", classes="form-description"),
                CommandInput(
                    value=label,
                    id=f"branch-label-{port}",
                    placeholder=f"Branch {index + 1}",
                ),
                Label("Start with:", classes="form-description"),
                Select(
                    source_options,
                    value=selected_source,
                    id=f"branch-payload-source-{port}",
                    allow_blank=False,
                ),
                id=f"branch-payload-row-{port}",
                classes="branch-payload-row",
            )
            row.display = index < branch_count
            widgets.append(row)
        return widgets

    def on_mount(self) -> None:
        for scroll in self.query("#node-config-scroll"):
            scroll.can_focus = False
        for scroll in self.query(".tab-scroll"):
            scroll.can_focus = False
        self._sync_merge_input_details()
        if self.query("#alias-input"):
            self.app.set_focus(self.query_one("#alias-input", CommandInput))
        else:
            focusable = self._keyboard_focus_widgets()
            if focusable:
                self.app.set_focus(focusable[0])
        self._sync_membank_output_controls()
        self._sync_membank_input_controls()
        self._sync_branch_payload_rows()
        self._sync_payload_previews()
        self._sync_standard_payload_controls()
        self._apply_generated_field_rules()
        self._sync_duplicate_input_source_options()
        if self.query("#alias-input"):
            self.call_after_refresh(
                lambda: self.app.set_focus(self.query_one("#alias-input", CommandInput))
            )
            self.set_timer(
                0.01,
                lambda: self.app.set_focus(self.query_one("#alias-input", CommandInput)),
            )

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        expanded_select = self._expanded_select()
        if expanded_select is not None and action in {"back", "cancel"}:
            expanded_select.expanded = False
            expanded_select.focus()
            return False
        if action == "jump_config_tab":
            # Digits type normally while editing a field or with a Select
            # overlay open; only switch tabs in nav mode.
            active_text = getattr(self, "_active_command_text_widget", None)
            if (
                is_editing_text(self.app.focused)
                or is_editing_text(active_text)
                or expanded_select is not None
            ):
                return False
        return super().check_action(action, parameters)

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "membank-writes":
            await self._refresh_membank_output_rows()
        elif event.checkbox.id == "membank-reads":
            self._sync_membank_input_controls()
            self._sync_branch_payload_rows()
            self._sync_payload_previews()
        elif event.checkbox.id in {
            "show-previous-output",
            "show-payload-upstream-payload",
            "show-source-vault-payload",
            "show-payload-vault-payload",
        }:
            self._sync_payload_previews()
        elif event.checkbox.id == "field-pass_through":
            await self._refresh_membank_output_rows()
        elif event.checkbox.id == "dead-drop-passthrough" or (
            event.checkbox.id or ""
        ).startswith("vault-output-disabled-"):
            self._sync_standard_payload_controls()
        if event.checkbox.id and event.checkbox.id.startswith("field-"):
            if event.value:
                self._uncheck_mutually_exclusive_fields(
                    event.checkbox.id.removeprefix("field-")
                )
            self._apply_generated_field_rules()
        self._scroll_changed_widget_with_peek(event.checkbox)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "membank-output-count":
            await self._refresh_membank_output_rows()
        elif event.input.id == "branch-count":
            self._sync_branch_payload_rows()
        elif event.input.id and event.input.id.startswith("field-"):
            self._apply_generated_field_rules()
        self._scroll_changed_widget_with_peek(event.input)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "merge-carry-forward-selector":
            self._sync_merge_input_details()
        elif event.select.id and event.select.id.startswith("field-"):
            self._apply_generated_field_rules()
            self._sync_duplicate_input_source_options()
        self._scroll_changed_widget_with_peek(event.select)

    def _apply_generated_field_rules(self) -> None:
        if not self._rule_schema or self._get_form_values is None:
            return
        # force_value_when may set a widget value, which re-fires Select.Changed
        # and re-enters here; guard so the pass runs once to a fixed point.
        if getattr(self, "_applying_field_rules", False):
            return
        self._applying_field_rules = True
        try:
            apply_field_rules(self, self._rule_schema, self._get_form_values())
        finally:
            self._applying_field_rules = False

    def _uncheck_mutually_exclusive_fields(self, field_name: str) -> None:
        if not self._rule_schema:
            return
        for partner in mutual_exclusion_targets(field_name, self._rule_schema):
            for widget in self.query(f"#field-{partner}"):
                if isinstance(widget, Checkbox) and widget.value:
                    widget.value = False

    def _sync_duplicate_input_source_options(self) -> None:
        """Prevent selecting the same upstream/vault source for two inputs."""
        if self._get_form_values is None or not self._generated_config_schema:
            return
        if getattr(self, "_syncing_duplicate_input_sources", False):
            return
        self._syncing_duplicate_input_sources = True
        try:
            values = self._get_form_values()
            source_fields = self._standard_source_fields()
            vault_fields = self._standard_vault_key_fields(source_fields)
            self._capture_vault_select_base_options(vault_fields)
            changed = self._sync_duplicate_source_select_options(
                values, source_fields, vault_fields
            )
            if changed:
                self._apply_generated_field_rules()
                values = self._get_form_values()
            self._sync_duplicate_vault_key_options(values, source_fields, vault_fields)
        finally:
            self._syncing_duplicate_input_sources = False

    def _standard_source_fields(self) -> list[str]:
        fields: list[str] = []
        for field_name, field_schema in self._generated_config_schema.items():
            if (
                not field_name.endswith("_source")
                or field_schema.get("type") != "select"
            ):
                continue
            query = self.query(f"#field-{field_name}")
            if query and getattr(query.first(), "display", True) is False:
                continue
            fields.append(field_name)
        return fields

    def _standard_vault_key_fields(self, source_fields: list[str]) -> Dict[str, str]:
        fields: Dict[str, str] = {}
        for source_field in source_fields:
            port = source_field[: -len("_source")]
            vault_field = f"{port}_vault_key"
            field_schema = self._generated_config_schema.get(vault_field)
            if isinstance(field_schema, dict) and field_schema.get("vault_type"):
                fields[source_field] = vault_field
        return fields

    def _capture_vault_select_base_options(self, vault_fields: Dict[str, str]) -> None:
        for vault_field in vault_fields.values():
            if vault_field in self._vault_select_base_options:
                continue
            query = self.query(f"#field-{vault_field}")
            if query and isinstance(query.first(), Select):
                self._vault_select_base_options[vault_field] = (
                    self._select_options_without_blank(query.first()._options)
                )

    def _sync_duplicate_source_select_options(
        self,
        values: Dict[str, Any],
        source_fields: list[str],
        vault_fields: Dict[str, str],
    ) -> bool:
        upstream_refs = self._upstream_refs_by_source_field(source_fields)
        first_upstream_field_by_ref: Dict[tuple[str, str], str] = {}
        duplicate_upstream_fields: set[str] = set()
        for field in source_fields:
            source_ref = upstream_refs.get(field)
            if values.get(field) != "Upstream payload" or source_ref is None:
                continue
            if source_ref in first_upstream_field_by_ref:
                duplicate_upstream_fields.add(field)
            else:
                first_upstream_field_by_ref[source_ref] = field
        changed = False
        for source_field in source_fields:
            query = self.query(f"#field-{source_field}")
            if not query or not isinstance(query.first(), Select):
                continue
            widget = query.first()
            current = widget.value
            options = list(
                self._source_select_base_options.get(source_field) or widget._options
            )
            source_ref = upstream_refs.get(source_field)
            upstream_owned_elsewhere = (
                source_ref is not None
                and source_ref in first_upstream_field_by_ref
                and first_upstream_field_by_ref.get(source_ref) != source_field
            )
            if (
                current == "Upstream payload"
                and source_field in duplicate_upstream_fields
            ):
                fallback = self._fallback_source_value(options, "Upstream payload")
                if fallback is not None and fallback != current:
                    widget.value = fallback
                    values[source_field] = fallback
                    current = fallback
                    changed = True
            if current != "Upstream payload" and upstream_owned_elsewhere:
                options = [
                    option for option in options if option[1] != "Upstream payload"
                ]
            vault_field = vault_fields.get(source_field)
            if vault_field and current != "Vault":
                if not self._has_available_vault_key(values, source_field, vault_fields):
                    options = [option for option in options if option[1] != "Vault"]
            self._set_select_options_preserving_value(widget, options, current)
        return changed

    @staticmethod
    def _fallback_source_value(
        options: list[tuple[Any, Any]], excluded: Any
    ) -> Any | None:
        preferred = ("Configured", "Vault")
        available = [value for _label, value in options if value != excluded]
        for value in preferred:
            if value in available:
                return value
        return available[0] if available else None

    def _upstream_refs_by_source_field(
        self, source_fields: list[str]
    ) -> Dict[str, tuple[str, str]]:
        refs: Dict[str, tuple[str, str]] = {}
        connections = self.node_data.get("connections", {}).get("inputs", [])
        for source_field in source_fields:
            port = source_field[: -len("_source")]
            for conn in connections:
                if str(conn.get("target_port") or "default") != port:
                    continue
                source_id = str(conn.get("source_node_id") or "").strip()
                if source_id:
                    refs[source_field] = (
                        source_id,
                        str(conn.get("source_port") or "default"),
                    )
                    break
        return refs

    def _has_available_vault_key(
        self,
        values: Dict[str, Any],
        source_field: str,
        vault_fields: Dict[str, str],
    ) -> bool:
        return any(
            value not in (None, "", Select.NULL)
            for _label, value in self._available_vault_options_for(
                values, source_field, vault_fields
            )
        )

    def _sync_duplicate_vault_key_options(
        self,
        values: Dict[str, Any],
        source_fields: list[str],
        vault_fields: Dict[str, str],
    ) -> None:
        for source_field, vault_field in vault_fields.items():
            query = self.query(f"#field-{vault_field}")
            if not query or not isinstance(query.first(), Select):
                continue
            widget = query.first()
            current = widget.value
            options = self._available_vault_options_for(
                values, source_field, vault_fields, include_current=True
            )
            self._set_select_options_preserving_value(widget, options, current)

    def _available_vault_options_for(
        self,
        values: Dict[str, Any],
        source_field: str,
        vault_fields: Dict[str, str],
        include_current: bool = False,
    ) -> list[tuple[Any, Any]]:
        vault_field = vault_fields.get(source_field)
        if not vault_field:
            return []
        current = values.get(vault_field)
        used_elsewhere = {
            values.get(other_vault_field)
            for other_source, other_vault_field in vault_fields.items()
            if other_source != source_field
            and values.get(other_source) == "Vault"
            and values.get(other_vault_field) not in (None, "")
        }
        options = []
        for label, value in self._vault_select_base_options.get(vault_field, []):
            if value in used_elsewhere and not (include_current and value == current):
                continue
            options.append((label, value))
        return options

    def _set_select_options_preserving_value(
        self, widget: Select, options: list[tuple[Any, Any]], current: Any
    ) -> None:
        options = self._select_options_without_blank(options)
        existing = self._select_options_without_blank(widget._options)
        if existing == options:
            return
        widget.set_options(options)
        legal_values = {value for _label, value in options}
        if current in legal_values:
            widget.value = current

    @staticmethod
    def _select_options_without_blank(
        options: list[tuple[Any, Any]],
    ) -> list[tuple[Any, Any]]:
        """Return real Select options, excluding Textual's synthetic blank row."""
        return [
            (label, value)
            for label, value in options
            if value not in (None, "", Select.NULL)
        ]

    def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        if event.selection_list.id == "merge-branches-to-close":
            self._sync_merge_carry_forward_selector()
            self._sync_merge_input_details()
        elif event.selection_list.id == "membank-inputs":
            self._sync_branch_payload_rows()
            self._sync_payload_previews()
        self._scroll_changed_widget_with_peek(event.selection_list)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-node-config":
            self.action_save()
        elif event.button.id == "cancel-node-config":
            self.action_cancel()

    def on_key(self, event: Key) -> None:
        if self._expanded_select() is None:
            # A/D within-row navigation is handled by CommandScreenMixin
            # bindings; tab switching is via number keys.
            return
        if event.key in {"up", "w"}:
            self.action_cursor_up()
            event.stop()
            event.prevent_default()
        elif event.key in {"down", "s"}:
            self.action_cursor_down()
            event.stop()
            event.prevent_default()
        elif event.key in {"e", "enter"}:
            self.action_activate_focused()
            event.stop()
            event.prevent_default()
        elif event.key == "ctrl+q":
            self._expanded_select().expanded = False
            event.stop()
            event.prevent_default()

    def action_save(self) -> None:
        alias_query = self.query("#alias-input")
        alias = alias_query.first().value if alias_query else self.node_data.get("alias", "")
        config = self._get_form_values() if self._get_form_values else {}
        config.update(self._transient_config_values())
        config.update(self._membank_config_values())
        config.update(self._standard_payload_config_values())
        config.update(self._wait_config_values())
        config.update(self._branch_config_values())
        config.update(self._merge_config_values())
        self.dismiss({"alias": alias, "config": config})

    def action_cancel(self) -> None:
        expanded_select = self._expanded_select()
        if expanded_select is not None:
            expanded_select.expanded = False
            expanded_select.focus()
            return
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        focused = self.app.focused
        active_text = getattr(self, "_active_command_text_widget", None)
        if is_editing_text(active_text):
            self.app.set_focus(active_text)
            return
        if is_editing_text(focused):
            return
        expanded_select = self._expanded_select()
        if expanded_select is not None:
            move_select_overlay(expanded_select, -1)
            return
        if isinstance(focused, SelectionList):
            if self._selection_list_at_top(focused):
                self._move_keyboard_focus(-1)
            else:
                focused.action_cursor_up()
            self._sync_cursor_mode()
            return
        self._move_keyboard_focus(-1)
        self._sync_cursor_mode()

    def action_cursor_down(self) -> None:
        focused = self.app.focused
        active_text = getattr(self, "_active_command_text_widget", None)
        if is_editing_text(active_text):
            self.app.set_focus(active_text)
            return
        if is_editing_text(focused):
            return
        expanded_select = self._expanded_select()
        if expanded_select is not None:
            move_select_overlay(expanded_select, 1)
            return
        if isinstance(focused, SelectionList):
            if self._selection_list_at_bottom(focused):
                self._move_keyboard_focus(1)
            else:
                focused.action_cursor_down()
            self._sync_cursor_mode()
            return
        self._move_keyboard_focus(1)
        self._sync_cursor_mode()

    def _selection_list_at_bottom(self, selection_list: SelectionList) -> bool:
        highlighted = getattr(selection_list, "highlighted", None)
        if highlighted is None:
            return False
        try:
            option_count = len(selection_list._options)
        except Exception:
            option_count = 0
        return option_count > 0 and highlighted >= option_count - 1

    def _selection_list_at_top(self, selection_list: SelectionList) -> bool:
        highlighted = getattr(selection_list, "highlighted", None)
        if highlighted is None:
            return False
        try:
            option_count = len(selection_list._options)
        except Exception:
            option_count = 0
        return option_count > 0 and highlighted <= 0

    def action_activate_focused(self) -> None:
        activate_command_widget(
            self._expanded_select()
            or self.app.focused
            or self._nav_widget
        )
        self._sync_cursor_mode()

    def action_previous_config_tab(self) -> None:
        self._move_config_tab(-1)

    def action_next_config_tab(self) -> None:
        self._move_config_tab(1)

    def action_jump_config_tab(self, tab_number: int) -> None:
        """Jump directly to the Nth config tab (1-based). No-op past the end."""
        tabbed_query = self.query("#node-config-tabs")
        if not tabbed_query:
            return
        tabs = tabbed_query.first()
        panes = [pane for pane in tabs.query(TabPane) if pane.id]
        index = tab_number - 1
        if index < 0 or index >= len(panes):
            return
        target_tab_id = str(panes[index].id)
        tabs.active = target_tab_id
        self.call_after_refresh(
            lambda tab_id=target_tab_id: self._focus_first_config_tab_widget(tab_id)
        )
        self.set_timer(
            0.01,
            lambda tab_id=target_tab_id: self._focus_first_config_tab_widget(tab_id),
        )

    def _move_config_tab(self, direction: int, *, wrap: bool = True) -> bool:
        tabbed_query = self.query("#node-config-tabs")
        if not tabbed_query:
            return False
        tabs = tabbed_query.first()
        panes = [pane for pane in tabs.query(TabPane) if pane.id]
        if len(panes) <= 1:
            return False
        active = tabs.active
        try:
            current_index = next(
                index for index, pane in enumerate(panes) if pane.id == active
            )
        except StopIteration:
            current_index = 0
        next_index = current_index + direction
        if wrap:
            next_index %= len(panes)
        elif next_index < 0 or next_index >= len(panes):
            return False
        target_tab_id = str(panes[next_index].id)
        tabs.active = target_tab_id
        self.call_after_refresh(
            lambda tab_id=target_tab_id: self._focus_first_config_tab_widget(tab_id)
        )
        self.set_timer(
            0.01,
            lambda tab_id=target_tab_id: self._focus_first_config_tab_widget(tab_id),
        )
        return True

    def _focus_first_config_tab_widget(self, tab_id: str) -> None:
        tabbed_query = self.query("#node-config-tabs")
        if tabbed_query:
            tabs = tabbed_query.first()
            if tabs.active != tab_id:
                tabs.active = tab_id
        try:
            active_pane = self.query_one(f"#{tab_id}", TabPane)
            widgets = [
                widget
                for widget in self._keyboard_focus_widgets()
                if self._is_descendant_of(widget, active_pane)
            ]
        except Exception:
            widgets = []
        if widgets:
            try:
                scroll = self._scroll_container()
                peek = widgets[1] if len(widgets) > 1 else None
                focus_command_widget(self, widgets[0], scroll, peek_widget=peek)
                self.call_after_refresh(
                    lambda target=widgets[0], peek=peek: self._scroll_config_widget_into_view(
                        target, peek
                    )
                )
                self._sync_cursor_mode()
                return
            except Exception:
                pass
        save_query = self.query("#save-node-config")
        if save_query:
            self.app.set_focus(save_query.first())
            self._sync_cursor_mode()

    def _is_descendant_of(self, widget: Any, ancestor: Any) -> bool:
        node = widget
        while node is not None and node is not self:
            if node is ancestor:
                return True
            node = getattr(node, "parent", None)
        return False

    def _expanded_select(self) -> Select | None:
        for select in self.query(Select):
            if select.expanded:
                return select
        return None

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

        try:
            scroll = self._scroll_container()
            peek = (
                widgets[next_index + direction]
                if 0 <= next_index + direction < len(widgets)
                else None
            )
            focus_command_widget(self, target, scroll, peek_widget=peek)
            self.call_after_refresh(
                lambda target=target, peek=peek: self._scroll_config_widget_into_view(
                    target, peek
                )
            )
        except Exception:
            focus_command_widget(self, target)

    def _scroll_config_widget_into_view(
        self, target: Any, peek_widget: Any | None = None
    ) -> None:
        try:
            scroll = self._scroll_container()
            if scroll is None:
                return
            scroll.scroll_to_widget(target, animate=False)
            target.scroll_visible(animate=False)
            if peek_widget is not None and peek_widget is not target:
                peek_widget.scroll_visible(animate=False)
        except Exception:
            pass

    def _scroll_changed_widget_with_peek(self, changed_widget: Any) -> None:
        """After a user change, reveal the changed widget and next field."""
        self.call_after_refresh(
            lambda widget=changed_widget: self._scroll_changed_widget_now(widget)
        )

    def _scroll_changed_widget_now(self, changed_widget: Any) -> None:
        widgets = self._keyboard_focus_widgets()
        if not widgets:
            return
        target = changed_widget if changed_widget in widgets else self.app.focused
        if target not in widgets:
            return
        index = widgets.index(target)
        peek = widgets[index + 1] if index + 1 < len(widgets) else None
        self._scroll_config_widget_into_view(target, peek)

    def _is_first_active_tab_widget(self, target: Any) -> bool:
        tabbed_query = self.query("#node-config-tabs")
        if not tabbed_query:
            return False
        tabs = tabbed_query.first()
        try:
            active_pane = self.query_one(f"#{tabs.active}", TabPane)
        except Exception:
            return False
        widgets = [
            widget
            for widget in self._keyboard_focus_widgets()
            if self._is_descendant_of(widget, active_pane)
        ]
        return bool(widgets and widgets[0] is target)

    def _nav_widgets(self) -> list[Any]:
        return self._keyboard_focus_widgets()

    def _scroll_container(self):
        """Return the active scroll: tab-inner scroll in tabbed mode, flat scroll otherwise."""
        try:
            tabbed = self.query_one("#node-config-tabs", TabbedContent)
            active_id = tabbed.active
            if active_id:
                pane = self.query_one(f"#{active_id}", TabPane)
                scrolls = list(pane.query(".tab-scroll"))
                if scrolls:
                    return scrolls[0]
        except Exception:
            pass
        try:
            return self.query_one("#node-config-scroll")
        except Exception:
            return None

    def _keyboard_focus_widgets(self) -> list[Any]:
        interactive = (
            CommandInput,
            CommandTextArea,
            PayloadPreview,
            Checkbox,
            SelectionList,
            Select,
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
            # Skip widgets hidden on their own (e.g. collapsed payload
            # previews). A hidden widget shows no highlight, so focusing it
            # looks like the cursor vanished and needs a second key press.
            if not getattr(widget, "display", True):
                continue
            if not self._ancestor_visible(widget):
                continue
            if isinstance(widget, interactive):
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
        return metadata_for_type(self.factory, node_type)

    def _alias_default_value(self) -> str:
        """Pre-fill the alias box with the friendly node name from the node file.

        Uses the saved alias when present; otherwise falls back to the node's
        ``display_name`` metadata (a user-friendly label with no underscores),
        and finally to a humanized node type. This keeps the alias field
        populated from the node definition rather than blank.
        """
        alias = str(self.node_data.get("alias") or "").strip()
        if alias:
            return alias
        metadata = self._metadata_for_type(self.node_data.get("type", "")) or {}
        display_name = str(metadata.get("display_name") or "").strip()
        if display_name:
            return display_name
        return node_display_name(self.node_id, self.node_data).replace("_", " ").title()

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

    def _uses_standard_source_model(self, metadata: Optional[Dict[str, Any]]) -> bool:
        """True when any input port declares the standard source model.

        Standard-model nodes get the redesigned config layout: auto incoming
        payload summary, per-input typed vault dropdowns, and no legacy
        membank/reveal sections. Legacy nodes keep the old flat layout
        (IO_CONTRACT_UI_DESIGN.md fallback rule).
        """
        if metadata is None:
            return False
        port_meta = metadata.get("input_port_metadata") or {}
        return any(
            (port_meta.get(str(port)) or {}).get("sources")
            for port in metadata.get("input_ports") or []
        )

    def _compose_incoming_payload_summary(self, metadata: Optional[Dict[str, Any]]):
        """Auto-revealed incoming payload block for standard-model nodes.

        One compact entry per connected input: the producing node, the payload
        name and data type, its description when declared, and the last
        captured value when the memory bank holds one. Deliberately portless —
        the dead-drop payload arrives whether or not an input consumes it.
        """
        self._refresh_node_data()
        inputs = self.node_data.get("connections", {}).get("inputs", [])
        if not inputs:
            return
        yield Label("Incoming Payload", classes="form-label nav-section")
        for connection in inputs:
            source_id = str(connection.get("source_node_id") or "")
            source_port = str(connection.get("source_port") or "default")
            target_port = str(connection.get("target_port") or "default")
            producer = trace_transient_producer(
                self.workflow_map, self.factory, source_id, source_port
            )
            chain_ids = producer.get("chain_node_ids") or []
            source_label = (
                self._dead_drop_chain_text_from_ids(chain_ids)
                if chain_ids
                else self._dead_drop_chain_text(
                    source_id, str(producer.get("node_id") or source_id)
                )
            )
            if "->" not in source_label:
                source_label = f"{source_label} node"
            payload_name = str(producer.get("name") or source_port)
            description = str(producer.get("description") or "").strip()
            producer_node = producer.get("node") or {}
            producer_meta = (
                self._metadata_for_type(str(producer_node.get("type") or "")) or {}
            )
            producer_out = (producer_meta.get("output_port_metadata") or {}).get(
                str(producer.get("port") or "")
            ) or {}
            data_type = str(producer_out.get("data_type") or "any")

            lines = []
            if len(inputs) > 1:
                lines.append(f"Input: {target_port.replace('_', ' ')}")
            lines.append(f"Node source: {source_label}")
            lines.append(f"Payload: {payload_name} ({data_type})")
            if description and description != OUTPUT_NOT_CONFIGURED:
                lines.append(f"Payload desc: {description}")
            if self.memory_bank is not None:
                value = self.memory_bank.read_transient(
                    source_id, source_port, default=None
                )
                if value is not None:
                    lines.append(f"Value: {self._short_value_text(value)}")
            # Read-only summary: plain Static so keyboard navigation skips it.
            yield Static(
                "\n".join(lines),
                classes="form-description incoming-payload-summary",
                id=f"incoming-payload-{target_port}",
            )

    def _sync_standard_payload_controls(self) -> None:
        """Grey downstream fields when forwarding, and vault fields when
        an output is disabled."""
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        if not self._uses_standard_source_model(metadata):
            return
        dead_drop_query = self.query("#dead-drop-passthrough")
        forwarding = bool(dead_drop_query.first().value) if dead_drop_query else False
        for port in self._downstream_output_ports(metadata):
            for suffix in (f"transient-output-name-{port}", f"transient-output-desc-{port}"):
                for widget in self.query(f"#{suffix}"):
                    widget.disabled = forwarding
        for port in self._vault_output_ports(metadata):
            disable_query = self.query(f"#vault-output-disabled-{port}")
            disabled = bool(disable_query.first().value) if disable_query else False
            for suffix in (f"vault-output-key-{port}", f"vault-output-desc-{port}"):
                for widget in self.query(f"#{suffix}"):
                    widget.disabled = disabled

    def _standard_payload_config_values(self) -> Dict[str, Any]:
        """Collect the redesigned Payloads controls into config keys."""
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        if not self._uses_standard_source_model(metadata):
            return {}
        dead_drop_query = self.query("#dead-drop-passthrough")
        # No forwarding checkbox (no pass_through port): result always flows.
        dead_drop = bool(dead_drop_query.first().value) if dead_drop_query else False
        values: Dict[str, Any] = {
            "dead_drop_passthrough": dead_drop,
            "transient_output": not dead_drop,
        }
        # A single vault output maps to the vault_write* keys the backend and
        # validator read; the first vault port wins (multi-vault is a future
        # extension — see NODE_STANDARDS.md).
        for port in self._vault_output_ports(metadata):
            disable_query = self.query(f"#vault-output-disabled-{port}")
            disabled = bool(disable_query.first().value) if disable_query else False
            key_query = self.query(f"#vault-output-key-{port}")
            desc_query = self.query(f"#vault-output-desc-{port}")
            values["vault_write"] = not disabled
            values["vault_write_key"] = (
                self._widget_text_value(key_query.first()) if key_query else ""
            )
            values["vault_write_description"] = (
                self._widget_text_value(desc_query.first()) if desc_query else ""
            )
            break
        return values

    def _short_value_text(self, value: Any) -> str:
        """One-line captured-value preview, truncated for the summary block."""
        if isinstance(value, (list, tuple, set, dict)):
            return f"({type(value).__name__}, {len(value)} items)"
        rendered = str(value)
        if len(rendered) > 400:
            rendered = f"{rendered[:397]}..."
        return rendered

    def _downstream_output_ports(self, metadata: Optional[Dict[str, Any]]) -> list[str]:
        """Output ports routed downstream (the designated node payload)."""
        port_meta = (metadata or {}).get("output_port_metadata") or {}
        ports = []
        for port in (metadata or {}).get("output_ports") or []:
            routing = (port_meta.get(str(port)) or {}).get("to")
            if routing is None or "downstream" in routing:
                ports.append(str(port))
        return ports

    def _vault_output_ports(self, metadata: Optional[Dict[str, Any]]) -> list[str]:
        """Output ports that may be keyed to the Vault."""
        port_meta = (metadata or {}).get("output_port_metadata") or {}
        return [
            str(port)
            for port in (metadata or {}).get("output_ports") or []
            if "vault" in ((port_meta.get(str(port)) or {}).get("to") or [])
        ]

    def _output_header(self, metadata: Optional[Dict[str, Any]], port: str) -> Text:
        """Rich `Name [type]` header for an output port."""
        info = ((metadata or {}).get("output_port_metadata") or {}).get(port) or {}
        name = output_display_name(self.factory, self.node_data, port)
        data_type = str(info.get("data_type") or "any")
        return Text.assemble(
            (name, "bold"),
            "  [",
            (data_type, f"bold {TYPE_COLOR}"),
            "]",
        )

    def _compose_standard_payloads(
        self,
        metadata: Optional[Dict[str, Any]],
        config: Dict[str, Any],
    ):
        """Compose the redesigned standard-model Payloads controls.

        Layout: the designated Downstream node payload (editable name +
        description, known before routing is chosen), the single
        "Forward incoming payload unchanged" checkbox beneath it (greys the
        downstream fields), then optional Vault payloads (each an editable key
        + description with a "Disable output" checkbox for optional outputs).
        Model per NODE_STANDARDS.md: one downstream output, the rest vault.
        """
        downstream_ports = self._downstream_output_ports(metadata)
        vault_ports = self._vault_output_ports(metadata)

        yield Label("Downstream node payload", classes="form-label nav-section")
        for port in downstream_ports:
            name = output_display_name(self.factory, self.node_data, port)
            description = output_display_description(self.factory, self.node_data, port)
            yield Static(
                self._output_header(metadata, port),
                classes="payload-header",
                id=f"downstream-header-{port}",
            )
            yield Horizontal(
                Label("Payload name:", classes="form-label-inline"),
                CommandInput(value=name, id=f"transient-output-name-{port}"),
                classes="form-inline-row",
                id=f"downstream-name-row-{port}",
            )
            yield Horizontal(
                Label("Description:", classes="form-label-inline"),
                CommandInput(
                    value="" if description == OUTPUT_NOT_CONFIGURED else description,
                    id=f"transient-output-desc-{port}",
                ),
                classes="form-inline-row",
                id=f"downstream-desc-row-{port}",
            )
        # The forwarding option renders only when a downstream port advertises
        # the dead-drop capability (`pass_through: true` in its metadata).
        port_meta = (metadata or {}).get("output_port_metadata") or {}
        supports_forwarding = any(
            (port_meta.get(port) or {}).get("pass_through")
            for port in downstream_ports
        )
        if supports_forwarding:
            yield Checkbox(
                "Forward incoming payload unchanged",
                value=bool(config.get("dead_drop_passthrough")),
                id="dead-drop-passthrough",
            )

        if vault_ports:
            plural = "s" if len(vault_ports) > 1 else ""
            yield Label(f"Vault Payload{plural}", classes="form-label nav-section")
            for port in vault_ports:
                info = (
                    (metadata or {}).get("output_port_metadata") or {}
                ).get(port) or {}
                optional = not bool(info.get("vault_required"))
                yield Static(
                    self._output_header(metadata, port),
                    classes="payload-header",
                    id=f"vault-header-{port}",
                )
                if optional:
                    yield Checkbox(
                        "Disable output",
                        value=not bool(config.get("vault_write", True)),
                        id=f"vault-output-disabled-{port}",
                    )
                default_key = str(config.get("vault_write_key") or "").strip()
                default_desc = str(config.get("vault_write_description") or "").strip()
                if not default_desc:
                    default_desc = "" if (
                        str(info.get("description") or "").strip() == OUTPUT_NOT_CONFIGURED
                    ) else str(info.get("description") or "").strip()
                yield Horizontal(
                    Label("Vault key:", classes="form-label-inline"),
                    CommandInput(value=default_key, id=f"vault-output-key-{port}"),
                    classes="form-inline-row",
                    id=f"vault-key-row-{port}",
                )
                yield Horizontal(
                    Label("Description:", classes="form-label-inline"),
                    CommandInput(value=default_desc, id=f"vault-output-desc-{port}"),
                    classes="form-inline-row",
                    id=f"vault-desc-row-{port}",
                )

    def _pass_through_note(self, metadata: Optional[Dict[str, Any]]) -> str:
        if metadata is None:
            return ""
        hint = (metadata.get("ui_hints") or {}).get("pass_through")
        if hint:
            return f"Dead drop payload: {hint}"
        description = str(metadata.get("description") or "").lower()
        if "passes input through" in description or "passes it through" in description:
            return "Dead drop payload: forwards the upstream payload unchanged."
        return ""

    def _format_metadata(self, metadata: Optional[Dict[str, Any]]) -> str:
        if metadata is None:
            return "Unknown node type"
        display_name = str(metadata.get("display_name") or metadata.get("type") or "Node")
        return "\n".join(
            [
                f"Node type: {display_name}",
                str(metadata.get("description", "")),
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
        producer = trace_transient_producer(
            self.workflow_map,
            self.factory,
            str(source_id or ""),
            str(source_port or "default"),
        )
        producer_id = producer.get("node_id") or source_id or "?"
        chain_node_ids = producer.get("chain_node_ids") or []
        source_label = (
            self._dead_drop_chain_text_from_ids(chain_node_ids)
            if chain_node_ids
            else self._dead_drop_chain_text(str(source_id or ""), str(producer_id))
        )
        payload_name = str(producer.get("name") or source_port)
        description = str(producer.get("description") or "").strip()
        value = None
        has_value = False
        if self.memory_bank is not None:
            value = self.memory_bank.read_transient(source_id, source_port, default=None)
            has_value = value is not None
        return self._payload_preview_text(
            source_label,
            payload_name,
            description,
            value,
            has_value=has_value,
        )

    def _vault_payload_text(self) -> str:
        selected = self._selected_vault_inputs()
        if not selected:
            return "No Vault payload selected."
        registry = build_membank_registry(self.workflow_map)
        lines: list[str] = []
        for output_id in selected:
            entry = registry.get(output_id) or {}
            writer_id = next(
                (
                    str(writer)
                    for writer in entry.get("writers", [])
                    if str(writer) and str(writer) != self.node_id
                ),
                "",
            )
            writer_node = self.workflow_map.get_node_data(writer_id) or {}
            source_label = (
                self._node_display_name(writer_id, writer_node)
                if writer_id
                else "Vault"
            )
            value = None
            has_value = False
            if self.memory_bank is not None:
                value = self.memory_bank.read_persistent(output_id, default=None)
                has_value = value is not None
            if lines:
                lines.append("")
            lines.append(
                self._payload_preview_text(
                    source_label,
                    output_id,
                    str(entry.get("description") or "").strip(),
                    value,
                    has_value=has_value,
                )
            )
        return "\n".join(lines)

    def _payload_preview_text(
        self,
        source_label: str,
        payload_name: str,
        description: str,
        value: Any,
        *,
        has_value: bool,
    ) -> str:
        lines = [f"Source: {source_label}"]
        if has_value:
            rendered = self._payload_value_preview(payload_name, value)
            if len(rendered) > 800:
                rendered = f"{rendered[:797]}..."
            lines.append(rendered)
        else:
            lines.append(f"Payload: {payload_name}")
        description = str(description or "").strip()
        if description and description != OUTPUT_NOT_CONFIGURED:
            lines.append(f"Description: {description}")
        return "\n".join(lines)

    def _compose_vault_payload_preview(self, location: str):
        yield Checkbox(
            "Reveal Vault payload",
            value=False,
            id=f"show-{location}-vault-payload",
        )
        yield PayloadPreview(
            "",
            id=f"{location}-vault-payload-preview",
            classes="form-description",
        )

    def _sync_payload_previews(self) -> None:
        self._sync_previous_output_preview()
        for location in ("source", "payload"):
            checkbox_query = self.query(f"#show-{location}-vault-payload")
            preview_query = self.query(f"#{location}-vault-payload-preview")
            if not checkbox_query or not preview_query:
                continue
            enabled = checkbox_query.first().value
            preview = preview_query.first()
            preview.display = enabled
            preview.update(self._vault_payload_text() if enabled else "")

        checkbox_query = self.query("#show-payload-upstream-payload")
        preview_query = self.query("#payload-upstream-payload-preview")
        if checkbox_query and preview_query:
            enabled = checkbox_query.first().value
            preview = preview_query.first()
            preview.display = enabled
            preview.update(self._previous_output_text() if enabled else "")

    def _dead_drop_chain_text_from_ids(self, node_ids: list[str]) -> str:
        chain = [
            self._node_display_name(node_id, self.workflow_map.get_node_data(node_id) or {})
            for node_id in node_ids
            if node_id
        ]
        if len(chain) > 4:
            chain = [chain[0], "(...)", chain[-1]]
        return " -> ".join(chain) if chain else "-"

    def _dead_drop_chain_text(self, source_id: str, producer_id: str) -> str:
        chain: list[str] = []
        current_id = source_id
        visited: set[str] = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            node = self.workflow_map.get_node_data(current_id) or {}
            if not node:
                break
            chain.append(self._node_display_name(current_id, node))
            if current_id == producer_id:
                break
            inputs = node.get("connections", {}).get("inputs", [])
            if not inputs:
                break
            current_id = str(inputs[0].get("source_node_id") or "")
        chain.reverse()
        if not chain:
            node = self.workflow_map.get_node_data(producer_id) or {}
            return self._node_display_name(producer_id, node)
        if len(chain) > 4:
            chain = [chain[0], "(...)", chain[-1]]
        return " -> ".join(chain)

    def _payload_value_preview(self, payload_name: str, value: Any) -> str:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return f"Payload: {payload_name} ({type(value).__name__}): {value}"
        if isinstance(value, (list, tuple, set, dict)):
            return f"Payload: {payload_name} ({type(value).__name__}, {len(value)} items)"
        return f"Payload: {payload_name} ({type(value).__name__})"

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
        count_input = CommandInput(
            value=str(count),
            type="integer",
            id="membank-output-count",
            classes="compact-number-field",
        )
        count_input.disabled = not enabled
        yield Checkbox("Write to Vault", value=enabled, id="membank-writes")
        yield Label("Payload count", classes="form-description")
        yield count_input
        yield Vertical(id="membank-output-rows")

    def _compose_membank_inputs(self, config: Dict[str, Any]):
        selected = set(normalize_membank_inputs(config))
        options = membank_input_options(self.workflow_map, self.node_id)
        enabled = bool(selected)
        yield Checkbox("Vault", value=enabled, id="membank-reads")
        if options:
            selection_list = SelectionList(
                *dynamic_selection_rows(options, selected),
                id="membank-inputs",
            )
            selection_list.disabled = not enabled
            yield selection_list
        else:
            yield Static("The vault is empty", classes="form-description")

    def _compose_transient_outputs(
        self,
        metadata: Optional[Dict[str, Any]],
        config: Dict[str, Any],
    ):
        ports = list(metadata.get("output_ports") or []) if metadata else []
        if not ports:
            yield Static("No dead drop payloads.", classes="form-description")
            return
        for port in ports:
            port = str(port)
            yield Label(port.replace("_", " ").title(), classes="form-description")
            name = output_display_name(self.factory, self.node_data, port)
            description = output_display_description(self.factory, self.node_data, port)
            yield CommandInput(
                value=name,
                id=f"transient-output-name-{port}",
                placeholder="Payload name",
            )
            yield CommandInput(
                value="" if description == OUTPUT_NOT_CONFIGURED else description,
                id=f"transient-output-desc-{port}",
                placeholder="Payload description",
            )

    def _compose_wait_targets(self, config: Dict[str, Any]):
        selected = set(normalize_wait_target_ids(config))
        options = wait_target_options(self.workflow_map, self.node_id)
        if options:
            yield SelectionList(
                *dynamic_selection_rows(options, selected),
                id="wait-targets",
            )
        else:
            yield Static("No non-downstream wait targets are available.", classes="form-description")

    def _compose_merge_inputs(self, config: Dict[str, Any]):
        options = merge_input_options(self.workflow_map, self.node_id)
        if not options:
            yield Static("No open branches are available to close.", classes="form-description")
            return
        selected_values = self._selected_merge_close_values(options, config)
        yield SelectionList(
            *dynamic_selection_rows(
                [
                    (option["description"], self._merge_option_value(option))
                    for option in options
                ],
                selected_values,
                select_all_when_empty=False,
            ),
            id="merge-branches-to-close",
        )
        yield Label("Carry Forward Output", classes="form-label nav-section")
        carry_options = self._merge_carry_forward_options(options, selected_values)
        carry_value = self._selected_merge_carry_value(carry_options, config)
        yield Select(
            carry_options or [("Select branches to close first", "")],
            value=carry_value if carry_options else "",
            id="merge-carry-forward-selector",
            disabled=not bool(carry_options),
        )
        yield Static("", id="merge-selected-output-details", classes="form-description merge-branch-output-details")

    def _selected_merge_close_values(
        self, options: list[Dict[str, str]], config: Dict[str, Any]
    ) -> set[str]:
        valid_values = {self._merge_option_value(option) for option in options}
        configured = config.get("branches_to_close")
        if isinstance(configured, list):
            values = {str(value) for value in configured if str(value) in valid_values}
            if values:
                return values
        legacy_branch = str(config.get("selected_branch_id") or "").strip()
        if legacy_branch in valid_values:
            return {legacy_branch}
        return set()

    def _merge_carry_forward_options(
        self, options: list[Dict[str, str]], selected_values: set[str]
    ) -> list[tuple[str, str]]:
        return [
            (
                f"{option['branch_label']} | Output: {option['output_name']}",
                self._merge_option_value(option),
            )
            for option in options
            if self._merge_option_value(option) in selected_values
        ]

    def _selected_merge_carry_value(
        self, carry_options: list[tuple[str, str]], config: Dict[str, Any]
    ) -> str:
        valid_values = {value for _, value in carry_options}
        for key in ("carry_forward_branch_id", "selected_branch_id"):
            value = str(config.get(key) or "").strip()
            if value in valid_values:
                return value
        if carry_options:
            return carry_options[0][1]
        return ""

    def _merge_option_value(self, option: Dict[str, str]) -> str:
        return f"{option['branch_id']}:{option['branch_port']}"

    def _merge_option_by_value(self, value: str) -> Optional[Dict[str, str]]:
        for option in merge_input_options(self.workflow_map, self.node_id):
            if self._merge_option_value(option) == value:
                return option
        return None

    def _selected_merge_close_values_from_widget(self) -> set[str]:
        selection_query = self.query("#merge-branches-to-close")
        if not selection_query:
            return set()
        return selected_values_from_widget(selection_query.first())

    def _sync_merge_carry_forward_selector(self) -> None:
        selector_query = self.query("#merge-carry-forward-selector")
        if not selector_query:
            return
        selector = selector_query.first()
        options = merge_input_options(self.workflow_map, self.node_id)
        selected_values = self._selected_merge_close_values_from_widget()
        carry_options = self._merge_carry_forward_options(options, selected_values)
        previous_value = str(selector.value or "")
        selector.set_options(carry_options or [("Select branches to close first", "")])
        selector.disabled = not bool(carry_options)
        valid_values = {value for _, value in carry_options}
        selector.value = (
            previous_value
            if previous_value in valid_values
            else (carry_options[0][1] if carry_options else "")
        )

    def _sync_merge_input_details(self) -> None:
        detail_query = self.query("#merge-selected-output-details")
        if not detail_query:
            return
        detail = detail_query.first()
        selector_query = self.query("#merge-carry-forward-selector")
        selected_value = selector_query.first().value if selector_query else ""
        selected_closures = self._selected_merge_close_values_from_widget()
        option = self._merge_option_by_value(str(selected_value or ""))
        if option is not None:
            detail.update(
                "\n".join(
                    [
                        f"Branches selected: {len(selected_closures)}",
                        f"Carry forward: {option['branch_label']}",
                        f"Branch path: {option.get('branch_path') or option['branch_label']}",
                        f"Last node: {option['last_node']}",
                        f"Output: {option['output_name']}",
                        f"Output Description: {option['output_description']}",
                    ]
                )
            )
            detail.display = True
            return
        detail.update("No branch selected.")
        detail.display = True

    def _membank_config_values(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {"membank_outputs": [], "membank_inputs": []}

        writes_query = self.query("#membank-writes")
        if not writes_query:
            if not self.query("#membank-reads"):
                return values
            reads_enabled = self.query_one("#membank-reads", Checkbox).value
            if reads_enabled:
                selection_lists = self.query("#membank-inputs")
                if selection_lists:
                    values["membank_inputs"] = list(selection_lists.first().selected)
            return values

        writes_enabled = self.query_one("#membank-writes", Checkbox).value
        if self._pass_through_selected():
            writes_enabled = False
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

    def _transient_config_values(self) -> Dict[str, Any]:
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        ports = list(metadata.get("output_ports") or []) if metadata else []
        outputs = []
        for port in ports:
            port = str(port)
            name_query = self.query(f"#transient-output-name-{port}")
            desc_query = self.query(f"#transient-output-desc-{port}")
            if not name_query and not desc_query:
                continue
            name = self._widget_text_value(name_query.first()) if name_query else ""
            description = (
                self._widget_text_value(desc_query.first()) if desc_query else ""
            )
            if name or description:
                outputs.append(
                    {
                        "port": port,
                        "name": name,
                        "description": description,
                    }
                )
        return {"transient_outputs": outputs}

    def _branch_config_values(self) -> Dict[str, Any]:
        if self.node_data.get("type") != BRANCH_NODE_TYPE:
            return {}
        existing_config = self.node_data.get("config") or {}
        branch_count = self._branch_count_value()
        values: Dict[str, Any] = {
            "branch_count": branch_count,
            "branch_payload_sources": {},
        }
        for key in LEGACY_BRANCH_CONFIG_KEYS:
            if key in existing_config:
                values[key] = existing_config[key]
        for index, port in enumerate(BRANCH_PORTS):
            label_query = self.query(f"#branch-label-{port}")
            if label_query:
                label = self._widget_text_value(label_query.first())
            else:
                label = str(existing_config.get(f"{port}_label") or f"Branch {index + 1}")
            values[f"{port}_label"] = label or f"Branch {index + 1}"
            source_query = self.query(f"#branch-payload-source-{port}")
            if index < branch_count and source_query:
                source = str(source_query.first().value or "dead_drop:input")
                values["branch_payload_sources"][port] = source
        return values

    def _branch_count_value(self) -> int:
        count_query = self.query("#branch-count")
        if not count_query:
            return _branch_count_from_config(self.node_data.get("config") or {})
        return _branch_count_from_config({"branch_count": count_query.first().value})

    def _sync_branch_payload_rows(self) -> None:
        if self.node_data.get("type") != BRANCH_NODE_TYPE or not self.query("#branch-payload-rows"):
            return
        branch_count = self._branch_count_value()
        source_options = self._branch_payload_source_options()
        valid_values = {value for _, value in source_options}
        for index, port in enumerate(BRANCH_PORTS):
            row_query = self.query(f"#branch-payload-row-{port}")
            if row_query:
                row_query.first().display = index < branch_count
            select_query = self.query(f"#branch-payload-source-{port}")
            if select_query:
                selector = select_query.first()
                current_value = str(selector.value or "dead_drop:input")
                selector.set_options(source_options)
                selector.value = current_value if current_value in valid_values else "dead_drop:input"

    def _sync_membank_input_controls(self) -> None:
        reads_query = self.query("#membank-reads")
        if not reads_query:
            return
        reads_enabled = bool(reads_query.first().value)
        selection_query = self.query("#membank-inputs")
        if selection_query:
            selection_query.first().disabled = not reads_enabled

    def _sync_membank_output_controls(self) -> None:
        if not self.query("#membank-writes"):
            return
        writes_enabled = self.query_one("#membank-writes", Checkbox).value
        pass_through_selected = self._pass_through_selected()
        if pass_through_selected:
            writes_enabled = False
        count_query = self.query("#membank-output-count")
        if not count_query:
            return
        writes_checkbox = self.query_one("#membank-writes", Checkbox)
        writes_checkbox.disabled = pass_through_selected
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
            if self._pass_through_selected():
                writes_enabled = False
            if not writes_enabled:
                count = 0
            await container.remove_children()
            await container.mount(*self._membank_output_row_widgets(values[:count]))
        finally:
            self._refreshing_membank_outputs = False

    def _current_membank_output_row_values(self) -> list[Dict[str, str]]:
        def read_row(index: int) -> Dict[str, str] | None:
            id_query = self.query(f"#membank-output-id-{index}")
            desc_query = self.query(f"#membank-output-desc-{index}")
            if id_query and desc_query:
                return {
                    "id": self._widget_text_value(id_query.first()),
                    "description": self._widget_text_value(desc_query.first()),
                }
            return None

        return preserved_dynamic_rows(
            self._membank_output_count(),
            MAX_MEMBANK_OUTPUT_ROWS,
            read_row,
            self._initial_membank_outputs,
            {"id": "", "description": ""},
        )

    def _membank_output_count(self) -> int:
        count_query = self.query("#membank-output-count")
        if not count_query:
            return 0
        return clamp_dynamic_row_count(
            count_query.first().value,
            MAX_MEMBANK_OUTPUT_ROWS,
        )

    def _membank_output_row_widgets(self, outputs: list[Dict[str, str]]) -> list[Any]:
        widgets: list[Any] = []
        for index, current in enumerate(outputs[:MAX_MEMBANK_OUTPUT_ROWS]):
            output_number = index + 1
            desc_input = CommandInput(
                value=current.get("description", ""),
                id=f"membank-output-desc-{index}",
                placeholder="Describe this Vault payload",
                classes="membank-output-description-field",
            )
            output_input = CommandTextArea(
                current.get("id", ""),
                id=f"membank-output-id-{index}",
                classes="membank-output-field membank-output-textarea",
            )
            output_input.placeholder = "Vault payload key or value"
            desc_input.styles.height = 3
            desc_input.styles.width = "100%"
            output_input.styles.height = 6
            output_input.styles.width = "100%"
            widgets.extend(
                [
                    Label(f"Vault Payload {output_number} Description:", classes="form-description"),
                    desc_input,
                    Label(f"Vault Payload {output_number}:", classes="form-description"),
                    output_input,
                    Static("", classes="membank-output-spacer"),
                ]
            )
        return widgets

    def _pass_through_selected(self) -> bool:
        query = self.query("#field-pass_through")
        if not query:
            return False
        widget = query.first()
        return bool(getattr(widget, "value", False))

    def _text_widget_value(self, selector: str) -> str:
        return self._widget_text_value(self.query_one(selector))

    def _widget_text_value(self, widget) -> str:
        if isinstance(widget, TextArea):
            return widget.text.strip()
        return str(getattr(widget, "value", "")).strip()

    def _wait_config_values(self) -> Dict[str, Any]:
        if self.node_data.get("type") != WAIT_UNTIL_NODE_TYPE:
            return {}
        selection_lists = self.query("#wait-targets")
        if not selection_lists:
            return {"target_node_ids": []}
        return {"target_node_ids": list(selection_lists.first().selected)}

    def _merge_config_values(self) -> Dict[str, Any]:
        if self.node_data.get("type") != MERGE_NODE_TYPE:
            return {}
        options = merge_input_options(self.workflow_map, self.node_id)
        branches_to_close = sorted(self._selected_merge_close_values_from_widget())
        carry_value = ""
        selector_query = self.query("#merge-carry-forward-selector")
        if selector_query:
            carry_value = str(selector_query.first().value or "")
        for option in options:
            if self._merge_option_value(option) == carry_value:
                return {
                    "branches_to_close": branches_to_close,
                    "carry_forward_branch_id": carry_value,
                    "selected_branch_id": carry_value,
                    "selected_input_port": option["port"],
                }
        return {
            "branches_to_close": branches_to_close,
            "carry_forward_branch_id": "",
            "selected_branch_id": "",
            "selected_input_port": "",
        }

    def _branch_end_status_text(self) -> str:
        self._refresh_node_data()
        outputs = self.node_data.get("connections", {}).get("outputs", [])
        for conn in outputs:
            target_id = str(conn.get("target_node_id") or "")
            target_node = self.workflow_map.get_node_data(target_id) or {}
            if target_node.get("type") != MERGE_NODE_TYPE:
                continue
            target_port = str(conn.get("target_port") or "default")
            branch_label, branch_id = upstream_branch_info(
                self.workflow_map,
                self.node_id,
                target_id,
                target_port,
            )
            return "\n".join(
                [
                    "Merge Beacon has no editable fields.",
                    f"Merges To Branch: {branch_label} ({branch_id})",
                    f"Merge Node: {self._node_label(target_id, target_node)}",
                ]
            )
        return "Merge Beacon has no editable fields.\nStatus: open until connected to a Merge node."

    def _node_label(self, node_id: str, node: Dict[str, Any]) -> str:
        name = node.get("alias") or node.get("type") or node_id
        return f"{name} ({node_id})"

    def _node_display_name(self, node_id: str, node: Dict[str, Any]) -> str:
        return str(node.get("alias") or node.get("type") or node_id)

    def _refresh_node_data(self) -> None:
        self.node_data = self.workflow_map.get_node_data(self.node_id) or self.node_data

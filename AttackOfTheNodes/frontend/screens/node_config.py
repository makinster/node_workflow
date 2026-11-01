"""Node configuration modal."""

from __future__ import annotations

import uuid
from copy import deepcopy


from typing import Any, Callable, Dict, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, SelectionList, Static, TabbedContent, TabPane, TextArea

from backend.output_entry import text_output_prefix
from backend.branch_paths import ALL_PATH_PORTS, path_port, path_ports
from backend.configuration_manager import DEFAULT_SETTINGS
from backend.nodes.branch_node import (
    MAX_BRANCH_COUNT,
    MIN_BRANCH_COUNT,
    branch_count_from_config as _branch_count_from_config,
)
from backend.data_types import types_compatible
from backend.field_types import check_number, field_visible, number_fields, object_list_problems

# Number fields drawn by custom controls instead of the generated form.
CUSTOM_NUMBER_CONTROLS = {"branch_count": "#branch-count"}
from backend.port_types import resolved_metadata, trace_producers
from backend.vault_declarations import typed_vault_writes, vault_output_fields
from frontend.keymap import NODE_CONFIG, bindings_for

from frontend.error_paths import editor_output_ports
from backend.node_errors import UNMATCHED_ROUTE
from frontend.error_mux_ui import (
    ANY_OTHER_ERROR,
    ERROR_MUX_NODE_TYPE,
    FORWARD_CHOICES,
    caught_error_count,
    friendly_error_name,
    guarded_node_ids,
    inline_mux_for,
    recovery_choices,
    MuxRouteDraft,
    branch_nodes_for_port,
    selected_values,
    unmatched_route,
    upstream_error_definitions,
)
from frontend import notifications, colors
from frontend.editor_workflow_adapter import EditorWorkflowAdapter
from frontend.screens.recovery_branch_unpick import DELETE_BRANCH, RecoveryBranchUnpickScreen
from frontend.screens.unsaved_changes import DISCARD, SAVE, UnsavedChangesScreen
from frontend.connection_rows import connection_rows
from frontend.node_labels import friendly_label, friendly_labels
from frontend.node_types import (
    BRANCH_END_NODE_TYPE,
    BRANCH_NODE_TYPE,
    END_NODE_TYPE,
    MERGE_NODE_TYPE,
    START_NODE_TYPE,
    TEXT_OUTPUT_NODE_TYPE,
    WAIT_UNTIL_NODE_TYPE,
)
from frontend.node_io_display import (
    OUTPUT_NOT_CONFIGURED,
    metadata_for_type,
    memory_registry,
    normalize_membank_inputs,
    normalize_membank_outputs,
    node_display_name,
    normalize_transient_outputs,
    output_display_description,
    output_display_name,
    trace_transient_producer,
)
from frontend.widgets.command_navigation import (
    group_widgets_into_rows,
    row_move_target,
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
from frontend.widgets.contract_rows import INPUT, RESULT, ContractRowsField, next_node_summary, row_line
from frontend import subworkflow_info
from frontend.widgets.subworkflow_rows import (
    SubworkflowInputsField,
    SubworkflowPayloadsField,
    SubworkflowPicker,
    ask_warning,
)


_MISSING_PAYLOAD = object()

MAX_MEMBANK_OUTPUT_ROWS = 5
# Branch config rows are composed for at least this many paths; more are
# mounted when the count grows.
COMPOSED_BRANCH_ROWS = 5
# Pause after the last keystroke in the Branch count before rows sync.
BRANCH_COUNT_DEBOUNCE_SECONDS = 0.15
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


def build_membank_registry(workflow_map) -> Dict[str, Dict[str, Any]]:
    """Scan workflow nodes for declared membank outputs."""
    return memory_registry(workflow_map)


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
    labels = friendly_labels(workflow_map)
    options: list[tuple[str, str]] = []
    for node_id, node in sorted(workflow_map.get_all_node_data().items()):
        if node_id == current_node_id or node_id in downstream:
            continue
        options.append((labels.get(node_id) or node_id, node_id))
    return options


def merge_input_options(workflow_map, current_node_id: str) -> list[Dict[str, str]]:
    """Return Merge Beacon branches that this merge may close."""
    merge_input_ports = list(ALL_PATH_PORTS)
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
                "branch_end": beacon_name,
                "last_node": beacon_name,
                "source_port": "default",
                "description": f"Branch: {branch_path}",
                "output_name": output["name"],
                "output_description": output["description"],
            }
        )
    return options


def unmatched_merge_values(
    options: list[Dict[str, str]],
    config: Dict[str, Any],
    reserved_ports: Optional[set[str]] = None,
) -> tuple[list[str], str]:
    """Saved Merge values that match no current option: (closures, carry).

    A Merge save keeps these unchanged instead of dropping them, so a change
    in how the editor identifies a branch can never silently undo a closure
    or disconnect its beacon. ``reserved_ports`` are the Merge's home inputs;
    when it is None a ``home:`` carry-forward is not judged.
    """
    valid = {f"{option['branch_id']}:{option['branch_port']}" for option in options}
    legacy = str(config.get("selected_branch_id") or "").strip()
    configured = config.get("branches_to_close")
    if isinstance(configured, list) and configured:
        closures = [str(value) for value in configured if str(value)]
    elif legacy and not legacy.startswith("home:"):
        closures = [legacy]
    else:
        closures = []
    kept_close = sorted({value for value in closures if value not in valid})
    carry = str(config.get("carry_forward_branch_id") or "").strip() or legacy
    if not carry:
        kept_carry = ""
    elif carry.startswith("home:"):
        # Home inputs are only judged when the caller knows them.
        matched = reserved_ports is None or carry.removeprefix("home:") in reserved_ports
        kept_carry = "" if matched else carry
    else:
        kept_carry = "" if carry in valid else carry
    return kept_close, kept_carry


def merge_unmatched_warning(kept_close: list[str], kept_carry: str) -> str:
    lines = ["Warning: saved settings no longer match a branch here. They are kept unchanged:"]
    lines.extend(f"  closes {value}" for value in kept_close)
    if kept_carry:
        lines.append(f"  carries forward {kept_carry}")
    lines.append("Uncheck or reselect them to change them.")
    return "\n".join(lines)


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
    """Map nodes to the branch path contexts that can reach them.

    One depth-first scan with a single visited set keyed by (node,
    branch_id, branch_port), so each fork/rejoin pair costs a constant
    amount instead of doubling the work (UX3). A node reached by several
    routes in the same context keeps the ``branch_path`` display text of the
    first route found; which contexts reach a node is unchanged.
    """
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

    seen: set[tuple[str, str, str]] = set()
    # Depth-first with an explicit stack (no recursion limit on long
    # workflows). Children are pushed in reverse so the visit order, and so
    # each node's first branch_path, matches the recursive scan.
    stack: list[tuple[str, Optional[Dict[str, str]]]] = [(start_id, None)]
    while stack:
        node_id, context = stack.pop()
        node = workflow_map.get_node_data(node_id) or {}
        if not node:
            continue
        state = (
            node_id,
            context["branch_id"] if context else "",
            context["branch_port"] if context else "",
        )
        if state in seen:
            continue
        seen.add(state)
        add_context(node_id, context)
        if node.get("type") == BRANCH_END_NODE_TYPE:
            continue
        outputs = node.get("connections", {}).get("outputs", [])
        children: list[tuple[str, Optional[Dict[str, str]]]] = []
        # Only nodes that spawn branch supervisors start new branch contexts
        # (as the engine does). Any other node, whatever its output count
        # (an error path, an inline Error Mux, a Conditional), passes the
        # current context to every connected target.
        if _node_spawns_branches(workflow_map, node):
            for output_port in _node_output_ports(workflow_map, node):
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
                children.append((target_id, next_context))
        else:
            for conn in outputs:
                target_id = str(conn.get("target_node_id") or "")
                if target_id:
                    children.append((target_id, context))
        stack.extend(reversed(children))
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


def _is_empty_config_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _node_spawns_branches(workflow_map, node: Dict[str, Any]) -> bool:
    node_type = str(node.get("type") or "")
    factory = getattr(workflow_map, "_factory", None)
    spawns = getattr(factory, "spawns_branches", None)
    if callable(spawns) and factory.is_valid_node_type(node_type):
        return bool(spawns(node_type))
    return node_type == BRANCH_NODE_TYPE


def _node_output_ports(workflow_map, node: Dict[str, Any]) -> list[str]:
    factory = getattr(workflow_map, "_factory", None)
    if factory is not None and factory.is_valid_node_type(str(node.get("type") or "")):
        # The backend resolves ports from the node's config (port model).
        return editor_output_ports(factory, node)
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


def selected_merge_ports(workflow_map, node_id, options, selected):
    """Allocate the finite input capacity only to branches actually selected."""
    used = _reserved_merge_input_ports(workflow_map, node_id)
    assignments = {}
    for option in options:
        key = f"{option['branch_id']}:{option['branch_port']}"
        if key not in selected:
            continue
        preferred = option.get("port")
        port = preferred if preferred in ALL_PATH_PORTS and preferred not in used else next((port for port in ALL_PATH_PORTS if port not in used), None)
        if port is None:
            raise ValueError(f"Merge has capacity for {len(ALL_PATH_PORTS) - len(_reserved_merge_input_ports(workflow_map, node_id))} closing branches; reduce the selection.")
        assignments[key] = port
        used.add(port)
    return assignments


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


def merge_home_port(workflow_map, merge_node_id: str) -> str:
    """The directly wired slot whose path lists Merge and the steps after it."""
    merge_node = workflow_map.get_node_data(merge_node_id) or {}
    if merge_node.get("type") != MERGE_NODE_TYPE:
        return ""
    reserved = _reserved_merge_input_ports(workflow_map, merge_node_id)
    carry = str((merge_node.get("config") or {}).get("carry_forward_branch_id") or "")
    if carry.startswith("home:") and carry.removeprefix("home:") in reserved:
        return carry.removeprefix("home:")
    return next((port for port in ALL_PATH_PORTS if port in reserved), "")


def merge_slot_label(port: str) -> str:
    return port.replace("_", " ").title()


def merge_slot_lines(workflow_map, merge_node_id: str) -> list[str]:
    """One line per connected slot: what arrives there and how to read it."""
    merge_node = workflow_map.get_node_data(merge_node_id) or {}
    home = merge_home_port(workflow_map, merge_node_id)
    sources: Dict[str, list[str]] = {}
    for conn in merge_node.get("connections", {}).get("inputs", []):
        port = str(conn.get("target_port") or "")
        source_id = str(conn.get("source_node_id") or "")
        if port and source_id:
            sources.setdefault(port, []).append(friendly_label(workflow_map, source_id))
    return [
        f"{merge_slot_label(port)}: {', '.join(sources[port])}. Read later as {{input[{port}]}}."
        + (" Next steps are listed on this path." if port == home else "")
        for port in ALL_PATH_PORTS
        if port in sources
    ]


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


SUBWORKFLOW_NODE_TYPE = "subworkflow_node"


class NodeConfigScreen(CommandScreenMixin, ModalScreen):
    """Edit-node modal powered by the schema form generator."""

    KEYMAP = NODE_CONFIG
    BINDINGS = bindings_for(KEYMAP)

    def __init__(
        self,
        factory,
        workflow_map,
        node_id: str,
        node_data: Dict[str, Any],
        memory_bank=None,
        secrets_manager=None,
        workflow_adapter=None,
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        super().__init__()
        # Save and stay: ``on_save`` applies a save while the screen stays
        # open. Without it the last saved result is returned on close.
        self._on_save = on_save
        self._saved_result: Optional[Dict[str, Any]] = None
        self._opened_alias: Optional[str] = None
        self._connection_targets: Dict[str, str] = {}
        self._connection_keys: Dict[str, tuple] = {}
        self.factory = factory
        self.workflow_map = workflow_map
        self.node_id = node_id
        self.node_data = node_data
        self.memory_bank = memory_bank
        self.secrets_manager = secrets_manager
        self.workflow_adapter = workflow_adapter or EditorWorkflowAdapter(workflow_map, factory)
        self._get_form_values: Optional[WidgetGetter] = None
        self._nav_widget: Any = None
        # No-edit invariant (UX2): the stored config as opened, and what the
        # screen's widgets produce before any edit (taken after mount).
        self._original_config = deepcopy(node_data.get("config") or {})
        self._opened_config: Optional[Dict[str, Any]] = None
        # Branch rows by port: (row, label input, source select), filled as
        # rows are built so syncing never searches the whole screen (UX3).
        self._branch_rows: Dict[str, tuple[Any, Any, Any]] = {}
        self._branch_count_timer: Any = None
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
                    *(f"{port}_label" for port in ALL_PATH_PORTS),
                }
            )
        if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
            excluded_config_keys.add("target_node_ids")
        if self.node_data.get("type") == START_NODE_TYPE:
            # Step 4a-2: the rows (the old greeting is shown as one) replace
            # the greeting field and its routing.
            excluded_config_keys.update({"greeting", "rows", "no_inputs", "transient_output", "transient_outputs",
                                         "vault_write", "vault_write_key", "vault_write_description"})
        if self.node_data.get("type") == END_NODE_TYPE:
            excluded_config_keys.update({"return_end", "results"})
        if self.node_data.get("type") == SUBWORKFLOW_NODE_TYPE:
            excluded_config_keys.update({"workflow_id", "inputs", "results"})
        if self.node_data.get("type") == MERGE_NODE_TYPE:
            excluded_config_keys.update(
                {
                    "branches_to_close",
                    "carry_forward_branch_id",
                    "selected_branch_id",
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
            title = self.node_data.get("alias") or self.node_id
            sub_mark = "   \\[sub]" if self._is_subworkflow() else ""
            yield Label(f"Edit Node: {title}{sub_mark}", classes="modal-title")
            # The node ID on its own line (owner, 2026-10-14), not in labels.
            yield Static(f"Node ID: {self.node_id}", id="node-config-id",
                         classes="form-description")
            help_text = "1-5 tabs | w/s move | e edit | p stash | ctrl+s save | esc close | ctrl+q revert"
            if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
                help_text = "1/2 tabs | w/s move | e edit | p stash | ctrl+s save | esc close | ctrl+q revert"
            # UX6: the key hints show once, in the status bar at the bottom.
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
            elif self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
                yield from self._compose_wait_config_tabs(config, forms)
            elif self.node_data.get("type") == ERROR_MUX_NODE_TYPE:
                yield from self._compose_error_mux_config_tabs(metadata, config)
            elif self.node_data.get("type") == START_NODE_TYPE:
                help_text = ("1-3 tabs" if self._is_subworkflow() else "1/2 tabs") + \
                    " | w/s move | e edit | ctrl+s save | esc close | ctrl+q revert"
                yield from self._compose_start_config_tabs(config)
            elif self.node_data.get("type") == END_NODE_TYPE and self._is_subworkflow():
                help_text = "1-3 tabs | w/s move | e edit | ctrl+s save | esc close | ctrl+q revert"
                yield from self._compose_end_config_tabs(config, forms)
            elif self.node_data.get("type") == SUBWORKFLOW_NODE_TYPE:
                help_text = "1-3 tabs | w/s move | e edit | ctrl+s save | esc close | ctrl+q revert"
                yield from self._compose_subworkflow_config_tabs(config)
            else:
                yield from self._compose_standard_config_tabs(
                    metadata,
                    config,
                    forms,
                )
            with Vertical(classes="button-row"):
                # UX6: compact one-row buttons; Close asks before discarding edits.
                yield Button("Save", id="save-node-config", variant="primary", compact=True)
                yield Button("Close", id="cancel-node-config", variant="default", compact=True)
                # Last, so W/S from the fields still reaches Save first.
                yield Button("Insert from Stash", id="stash-insert-node-config", variant="default", compact=True)
            yield StatusBar(help_text)

    def _compose_standard_config_tabs(
        self,
        metadata: Optional[Dict[str, Any]],
        config: Dict[str, Any],
        forms: Dict[str, Any],
    ):
        standard_model = self._uses_standard_source_model(metadata)
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 Source", id="node-config-tab-core"):
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

            with TabPane("2 Parameters", id="node-config-tab-parameters"):
                with VerticalScroll(classes="tab-scroll"):
                    if forms.get("parameters") is not None:
                        yield forms["parameters"]
                    else:
                        yield Static("No parameters.", classes="form-description")

            with TabPane("3 Payloads", id="node-config-tab-outputs"):
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

            with TabPane("4 Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Connections", classes="form-label nav-section")
                    yield Static(
                        "Edit connections from the editor.",
                        classes="form-description",
                    )
                    yield from self._compose_connection_rows()
                    yield from self._compose_errors_section()

    # -- Step 4a-2: Start inputs, Return End results (owner samples, 2026-10-18) --

    def _is_subworkflow(self) -> bool:
        return bool(getattr(self.workflow_map, "callable", False))

    def _return_end(self) -> Optional[tuple[str, Dict[str, Any]]]:
        """The End that sends results back (the first one ticked), if any."""
        for node_id, node in self.workflow_map.get_all_node_data().items():
            if node.get("type") == END_NODE_TYPE and (node.get("config") or {}).get("return_end"):
                return node_id, node
        return None

    def _alias_row(self):
        return Horizontal(
            Label("Alias:", classes="form-label-inline"),
            CommandInput(value=self._alias_default_value(), id="alias-input"),
            classes="form-inline-row", id="alias-row",
        )

    def _compose_start_config_tabs(self, config: Dict[str, Any]):
        from backend.contracts import start_rows

        rows = config.get("rows") if isinstance(config.get("rows"), list) and config.get("rows") else start_rows(config)
        sub = self._is_subworkflow()
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 Inputs", id="node-config-tab-core"):
                with VerticalScroll(classes="tab-scroll"):
                    yield self._alias_row()
                    text = "Values the workflow starts with."
                    if sub:
                        text += " A calling workflow can fill them in."
                    yield Static(text, classes="form-description")
                    yield ContractRowsField(INPUT, rows, id="start-inputs")
                    yield Static(next_node_summary(rows), id="start-next-summary",
                                 classes="form-description", markup=False)
            if sub:
                with TabPane("2 Results", id="node-config-tab-results"):
                    with VerticalScroll(classes="tab-scroll"):
                        yield from self._compose_start_results()
            with TabPane("3 Connections" if sub else "2 Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Static("Edit connections from the editor.", classes="form-description")
                    yield from self._compose_connection_rows()
                    yield from self._compose_errors_section()

    def _compose_start_results(self):
        from backend.contracts import return_rows

        found = self._return_end()
        if found is None:
            yield Static('Nothing sent back yet. Tick "Send results back" on an End node.',
                         classes="form-description", markup=False)
            return
        end_id, end = found
        name = friendly_label(self.workflow_map, end_id)
        rows = return_rows(end.get("config") or {})
        if not rows:
            yield Static(f'Nothing sent back yet. Add results on End "{name}".',
                         classes="form-description", markup=False)
            return
        yield Static(f'Sent back when called. Edit on End "{name}".', classes="form-description", markup=False)
        yield Static("\n".join(row_line(RESULT, row) for row in rows), id="start-results",
                     classes="form-description", markup=False)

    def _compose_end_config_tabs(self, config: Dict[str, Any], forms: Dict[str, Any]):
        returning = bool(config.get("return_end"))
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 Results", id="node-config-tab-results"):
                with VerticalScroll(classes="tab-scroll"):
                    yield self._alias_row()
                    yield Checkbox("Send results back", value=returning, id="return-end")
                    yield Static("Only one End can do this, after branches merge.",
                                 classes="form-description", markup=False)
                    rows = config.get("results") if isinstance(config.get("results"), list) else []
                    field = ContractRowsField(RESULT, rows, id="end-results")
                    field.display = returning
                    yield field
            with TabPane("2 Parameters", id="node-config-tab-parameters"):
                with VerticalScroll(classes="tab-scroll"):
                    if forms.get("parameters") is not None:
                        yield forms["parameters"]
            with TabPane("3 Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Static("Edit connections from the editor.", classes="form-description")
                    yield from self._compose_connection_rows()
                    yield from self._compose_errors_section()

    # -- Step 4c: the Subworkflow node (owner samples, 2026-10-19, revision 2) --

    def _compose_subworkflow_config_tabs(self, config: Dict[str, Any]):
        child = subworkflow_info.describe(str(config.get("workflow_id") or ""))
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 Inputs", id="node-config-tab-core"):
                with VerticalScroll(classes="tab-scroll"):
                    yield self._alias_row()
                    yield Horizontal(
                        Label("Subworkflow:", classes="form-label-inline"),
                        Static(self._sub_name_text(config, child), id="sub-name", markup=False),
                        Button("Change", id="sub-change", compact=True),
                        classes="form-inline-row", id="sub-name-row",
                    )
                    yield Static(ask_warning(child["name"], child["asks"]) if child else "", id="sub-asks")
                    yield Static(self._sub_inputs_intro(child), id="sub-inputs-intro",
                                 classes="form-description", markup=False)
                    yield SubworkflowInputsField(child, list(config.get("inputs") or []), id="sub-inputs")
            with TabPane("2 Payloads", id="node-config-tab-outputs"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Static(self._sub_payloads_intro(child), id="sub-payloads-intro",
                                 classes="form-description", markup=False)
                    payloads = SubworkflowPayloadsField(child, list(config.get("results") or []), id="sub-payloads")
                    yield payloads
                    yield Static(payloads.next_node_text() if child else "", id="sub-next",
                                 classes="form-description", markup=False)
            with TabPane("3 Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Static("Edit connections from the editor.", classes="form-description")
                    yield from self._compose_connection_rows()
                    yield from self._compose_errors_section()

    @staticmethod
    def _sub_name_text(config: Dict[str, Any], child: Optional[Dict[str, Any]]) -> str:
        if child is not None:
            return f"{child['name']} [sub]"
        workflow_id = str(config.get("workflow_id") or "")
        return f"Not found: {workflow_id}" if workflow_id else "None chosen yet"

    @staticmethod
    def _sub_inputs_intro(child: Optional[Dict[str, Any]]) -> str:
        return f"Fill in the values {child['name']} starts with:" if child and child["inputs"] else ""

    @staticmethod
    def _sub_payloads_intro(child: Optional[Dict[str, Any]]) -> str:
        if not child or not child["results"]:
            return ""
        return f"Payloads {child['name']} sends back, and where each one goes:"

    def _open_subworkflow_picker(self) -> None:
        current = self._sub_workflow_id()
        entries = subworkflow_info.subworkflows(exclude=str(getattr(self.workflow_map, "workflow_id", "") or ""))

        async def chosen(workflow_id: Optional[str]) -> None:
            if not workflow_id or workflow_id == current:
                return
            child = subworkflow_info.describe(workflow_id)
            self._sub_chosen_id = workflow_id
            await self.query_one("#sub-inputs", SubworkflowInputsField).set_child(child)
            await self.query_one("#sub-payloads", SubworkflowPayloadsField).set_child(child)
            self.query_one("#sub-name", Static).update(self._sub_name_text({"workflow_id": workflow_id}, child))
            self.query_one("#sub-asks", Static).update(ask_warning(child["name"], child["asks"]) if child else "")
            self.query_one("#sub-inputs-intro", Static).update(self._sub_inputs_intro(child))
            self.query_one("#sub-payloads-intro", Static).update(self._sub_payloads_intro(child))
            self._refresh_sub_next()

        self.app.push_screen(SubworkflowPicker(entries, current), chosen)

    def _sub_workflow_id(self) -> str:
        chosen = getattr(self, "_sub_chosen_id", None)
        return chosen or str((self.node_data.get("config") or {}).get("workflow_id") or "")

    def _refresh_sub_next(self) -> None:
        payloads = self.query_one("#sub-payloads", SubworkflowPayloadsField)
        self.query_one("#sub-next", Static).update(payloads.next_node_text() if payloads.child else "")

    def on_subworkflow_payloads_field_changed(self, _event) -> None:
        self._refresh_sub_next()

    def on_contract_rows_field_changed(self, event: ContractRowsField.Changed) -> None:
        for summary in self.query("#start-next-summary"):
            summary.update(next_node_summary(self.query_one("#start-inputs", ContractRowsField).rows))

    def _contract_config_values(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        start = self.query("#start-inputs")
        if start and not start.first().untouched_legacy:
            values["rows"] = start.first().value
            # rows=[] alone still means the old greeting (saved files rely on it).
            values["no_inputs"] = not values["rows"]
        if self.query("#return-end"):
            values["return_end"] = bool(self.query_one("#return-end", Checkbox).value)
            values["results"] = self.query_one("#end-results", ContractRowsField).value
        if self.query("#sub-inputs"):
            values["workflow_id"] = self._sub_workflow_id()
            values["inputs"] = self.query_one("#sub-inputs", SubworkflowInputsField).value
            values["results"] = self.query_one("#sub-payloads", SubworkflowPayloadsField).value
        return values

    # "Send back to calling workflow" on a Vault payload (C26).

    def _send_back_key(self, port: str) -> str:
        key_query = self.query(f"#vault-output-key-{port}")
        return self._widget_text_value(key_query.first()).strip() if key_query else ""

    def _sent_back_keys(self) -> set:
        from backend.contracts import return_rows

        found = self._return_end()
        if found is None:
            return set()
        return {row["vault_key"] or row["name"] for row in return_rows(found[1].get("config") or {})
                if row["source"] == "Vault key"}

    def _send_back_choices(self) -> Dict[str, tuple]:
        """``{port: (sent back, Vault key)}`` for the checkboxes on screen."""
        return {port: (bool(box.first().value), self._send_back_key(port))
                for port in self._vault_output_ports(self._metadata_for_type(self.node_data.get("type", "")))
                for box in [self.query(f"#send-back-{port}")] if box}

    def _send_back_plan(self) -> tuple[Optional[list], str]:
        """The Return End's new results for the checkboxes, and a problem
        that blocks the save ("" when there is none). A renamed key moves
        its result; a name another result already uses is refused."""
        choices = self._send_back_choices()
        opened = getattr(self, "_send_back_opened", {})
        found = self._return_end()
        if not choices or found is None or choices == opened:
            return None, ""
        end_id, end = found
        results = [dict(row) for row in (end.get("config") or {}).get("results") or [] if isinstance(row, dict)]
        metadata = self._metadata_for_type(self.node_data.get("type", "")) or {}

        def reads(row, key):
            return (row.get("source") or "Vault key") == "Vault key" and (row.get("vault_key") or row.get("name")) == key

        for port, (wanted, key) in choices.items():
            was_sent, old_key = opened.get(port, (False, ""))
            if (wanted, key) == (was_sent, old_key):
                continue
            if was_sent and old_key:
                results = [row for row in results if not reads(row, old_key)]
            if not wanted or not key or any(reads(row, key) for row in results):
                continue
            if any(str(row.get("name") or "").strip().casefold() == key.casefold() for row in results):
                name = friendly_label(self.workflow_map, end_id)
                return None, f'End "{name}" already has a result named "{key}"'
            from backend.contracts import ROW_TYPES

            data_type = str(((metadata.get("output_port_metadata") or {}).get(port) or {}).get("data_type") or "var")
            results.append({"id": f"out_{uuid.uuid4().hex[:8]}", "name": key,
                            "type": data_type if data_type in ROW_TYPES else "var",
                            "required": True, "source": "Vault key", "vault_key": key,
                            "description": ""})
        return results, ""

    def _apply_send_back(self, results: Optional[list]) -> None:
        """Write the planned results to the Return End (C26)."""
        found = self._return_end()
        if results is not None and found is not None:
            end_id, end = found
            self.workflow_map.update_node_config(end_id, {**deepcopy(end.get("config") or {}), "results": results})
        self._send_back_opened = self._send_back_choices()

    def _compose_wait_config_tabs(self, config: Dict[str, Any], forms: Dict[str, Any]):
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 Wait", id="node-config-tab-core"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Horizontal(
                        Label("Alias:", classes="form-label-inline"),
                        CommandInput(value=self._alias_default_value(), id="alias-input"),
                        classes="form-inline-row", id="alias-row",
                    )
                    yield Static(
                        "Wait for all selected nodes to complete, then forward the "
                        "incoming dead-drop payload unchanged. The next node can read the Vault.",
                        classes="form-description",
                    )
                    yield Label("Wait for these nodes", classes="form-label nav-section")
                    yield from self._compose_wait_targets(config)
                    yield Static(self._wait_target_summary(normalize_wait_target_ids(config)),
                                 id="wait-target-summary", classes="form-description")
                    yield Static(
                        "Targets must complete at least once in this run. "
                        "A target that never executes can wait forever at zero timeout.",
                        classes="form-description",
                    )
                    if forms.get("parameters") is not None:
                        yield forms["parameters"]
                    yield Static("", id="wait-config-error", classes="form-description")
                    yield Static(self._wait_route_summary(), classes="form-description")
            with TabPane("2 Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Static("Edit connections from the editor.", classes="form-description")
                    yield from self._compose_connection_rows()
                    yield from self._compose_errors_section()

    def _wait_route_summary(self) -> str:
        connections = self.node_data.get("connections") or {}
        incoming = connections.get("inputs") or []
        outgoing = connections.get("outputs") or []
        def label(node_id):
            data = self.workflow_map.get_node_data(node_id) or {}
            return data.get("alias") or data.get("type") or node_id
        source = next((c for c in incoming if c.get("target_port") == "input"), None)
        target = next((c for c in outgoing if c.get("source_port") == "default"), None)
        before = (f"{label(source['source_node_id'])}.{source.get('source_port', 'default')}"
                  if source else "Not connected")
        after = (f"{label(target['target_node_id'])}.{target.get('target_port', 'input')}"
                 if target else "Not connected")
        return f"Incoming: {before}\nForward unchanged\nNext: {after}"

    def _wait_target_summary(self, selected) -> str:
        if not selected:
            return "No targets selected: this node will continue immediately."
        return f"{len(selected)} target(s) selected; wait for all."

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
            with TabPane("1 Source", id="node-config-tab-core"):
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

            with TabPane("2 Parameters", id="node-config-tab-parameters"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Branches", classes="form-label nav-section")
                    yield CommandInput(
                        value=str(branch_count),
                        type="integer",
                        id="branch-count",
                        classes="compact-number-field",
                    )
                    yield Static(
                        f"Choose {MIN_BRANCH_COUNT} to {MAX_BRANCH_COUNT} spawn points.",
                        classes="form-description",
                    )

            with TabPane("3 Payloads", id="node-config-tab-outputs"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Incoming Payloads", classes="form-label nav-section")
                    yield Checkbox(
                        "Reveal upstream payload",
                        value=False,
                        id="show-payload-upstream-payload",
                    )
                    yield PayloadPreview("", id="payload-upstream-payload-preview", classes="form-description")
                    yield from self._compose_vault_payload_preview("payload")
                    # Column headings for the one-line path rows below (owner).
                    yield Horizontal(
                        Label("Branch ID", classes="form-label branch-heading-id"),
                        Label("Start Payload", classes="form-label branch-heading-source"),
                        classes="branch-payload-headings",
                    )
                    yield Vertical(
                        *self._branch_payload_row_widgets(
                            branch_count,
                            source_options,
                            payload_sources,
                            config,
                        ),
                        id="branch-payload-rows",
                    )

            with TabPane("4 Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Connections", classes="form-label nav-section")
                    yield Static(
                        "Edit connections from the editor.",
                        classes="form-description",
                    )
                    yield from self._compose_connection_rows()
                    yield from self._compose_errors_section()

    def _build_standard_config_forms(
        self,
        schema: Dict[str, Dict[str, Any]],
        values: Dict[str, Any],
    ) -> tuple[Dict[str, Any], WidgetGetter]:
        schema = {key: dict(field) for key, field in schema.items()}
        for name, field in schema.items():
            if field.get("options_from_setting"):
                field["options"] = self._options_from_setting(field, values.get(name))
            source = field.get("options_from")
            if source:
                options = list(field.get("options_include") or [])
                options.extend((str(row.get("path") or row.get("id")), row["id"]) for row in values.get(source, []) if isinstance(row, dict) and row.get("id"))
                field["options"] = options
        vault_keys_by_type = self._vault_key_options(schema)
        schema = self._prune_unavailable_source_options(
            schema, vault_keys_by_type, values
        )
        self._generated_config_schema = schema
        self._source_select_base_options = {
            field_name: [
                (f"{option} (unavailable)" if option in field_schema.get("unavailable_options", []) else str(option), option) for option in field_schema.get("options", [])
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
        these options (docs/archive/IO_CONTRACT_UI_DESIGN.md §3). Keys come from persisted
        vault entries of a compatible tag plus keys declared by workflow-node
        writers, so wiring works before the first run. Compatibility: exact
        tag match always; untagged (legacy) entries also satisfy ``string``;
        ``any`` accepts everything. Labels render as ``key [type]``.
        Persisted file entries require a current workflow declaration. Deleted
        declarations are retained for filtering, with no active writer ids.
        """
        fields = list(schema.values())
        fields += [child for spec in schema.values() if isinstance(spec, dict)
                   for child in (spec.get("item_schema") or {}).values()]
        tags = sorted({str(spec["vault_type"]) for spec in fields
                       if isinstance(spec, dict) and spec.get("vault_type")})
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

        # (key -> possible tags) from persisted vault entries; "" marks untagged/legacy.
        candidates: Dict[str, set[str]] = {}
        if self.memory_bank is not None:
            try:
                state = self.memory_bank.get_state()
                entry_tags = state.get("persistent_type_tags") or {}
                for key in state.get("persistent") or {}:
                    # File references are run outputs: a leftover value alone
                    # does not make a removed producer available in this graph.
                    if entry_tags.get(key) == "file" and str(key) not in declared:
                        continue
                    if eligible(str(key)):
                        candidates[str(key)] = {str(entry_tags.get(key) or "")}
            except Exception:
                pass
        # Declared writers describe future runs; apply the same eligibility gate.
        for key, info in declared.items():
            if not eligible(key):
                continue
            # Every eligible writer matters; another branch may write a
            # different compatible value under the same key.
            writer_tags = info.get("writer_tags") or {}
            candidates[key] = {tag for writer, tags in writer_tags.items()
                               if writer and writer != self.node_id and writer not in downstream
                               for tag in tags} or {"any"}

        def compatible(entry_tag: str, wanted: str) -> bool:
            # Untagged legacy entries hold text.
            return types_compatible(entry_tag or "string", wanted)

        options: Dict[str, list[tuple[str, str]]] = {}
        for wanted in tags:
            rows = [
                (f"{key} [{', '.join(sorted(tag or 'legacy text' for tag in entry_tags))}]", key)
                for key, entry_tags in sorted(candidates.items())
                if any(compatible(tag, wanted) for tag in entry_tags)
            ]
            options[wanted] = rows
        return options

    def _declared_vault_writer_keys(self) -> Dict[str, Dict[str, Any]]:
        """Vault keys declared by workflow nodes, with types grouped by writer.

        Covers legacy ``membank_outputs`` declarations (unknown), standard
        result routing (``vault_write_key`` — tagged with the writer's default
        output type), and AI session keys (``ai_session``). Writer node ids
        power the same-branch eligibility filter in ``_vault_key_options``.
        Deleted nodes retain keys but contribute no writer ids, including
        when their original configuration lives inside a saved tombstone.
        """
        declared: Dict[str, Dict[str, Any]] = {}

        def add(key: str, tag: str, writer_id: str) -> None:
            entry = declared.setdefault(key, {"tag": "", "tags": set(), "writers": set(), "writer_tags": {}})
            if tag:
                entry["tag"] = tag
            entry["writer_tags"].setdefault(writer_id, set()).add(tag or "any")
            entry["tags"].add(tag or "any")
            if writer_id:
                entry["writers"].add(str(writer_id))

        try:
            all_nodes = self.workflow_map.get_all_node_data()
        except Exception:
            return declared
        for node_id, node_data in all_nodes.items():
            deleted = self.workflow_adapter.is_placeholder(node_id)
            if deleted:
                original = self.workflow_adapter.placeholder_metadata(node_id)
                config = original.get("original_config") or {}
                node_type = original.get("original_type", "")
            else:
                config = node_data.get("config") or {}
                node_type = node_data.get("type", "")
            # Keep deleted declarations with no eligible writer. Otherwise a
            # persisted value would be mistaken for an external Vault entry.
            writer_id = "" if deleted else str(node_id)
            meta = resolved_metadata(self.factory, node_type, config)
            typed = typed_vault_writes(node_type, config, meta)
            for output in normalize_membank_outputs(config):
                if str(output["id"]) not in typed:
                    add(str(output["id"]), "any", writer_id)
            for key, tag in typed.items():
                add(key, tag or "any", writer_id)
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
        vault_keys_by_type = vault_keys_by_type or {}
        removals: Dict[str, set] = {}
        metadata = self._metadata_for_type(self.node_data.get("type", "")) or {}
        ports = metadata.get("input_port_metadata") or {}
        connections = self.node_data.get("connections", {}).get("inputs", [])
        for port, info in ports.items():
            field = f"{port}_source"
            if field not in schema:
                continue
            wanted = info.get("data_type", "any")
            available = False
            for connection in connections:
                if connection.get("target_port") != port:
                    continue
                source_node = self.workflow_map.get_node_data(connection.get("source_node_id", "")) or {}
                source_config = source_node.get("config") or {}
                publishes = source_config.get("transient_output", True) is not False or bool(source_config.get("dead_drop_passthrough"))
                producers = trace_producers(
                    self.workflow_map.get_all_node_data(), self.factory,
                    connection.get("source_node_id", ""), connection.get("source_port", "default"),
                )
                if publishes and (not producers or any(types_compatible(actual, wanted) for _, actual in producers)):
                    available = True
                    break
            if not available:
                removals.setdefault(field, set()).add("Upstream payload")
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
            if select_name in values and current in gone and current not in options:
                options.append(current)
                select_schema["unavailable_options"] = [current]
            if select_schema.get("default") not in options and options:
                select_schema["default"] = options[0]
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
        for index in range(max(branch_count, COMPOSED_BRANCH_ROWS)):
            row = self._branch_payload_row(index, source_options, payload_sources, config)
            row.display = index < branch_count
            widgets.append(row)
        return widgets

    def _branch_payload_row(
        self,
        index: int,
        source_options: list[tuple[str, str]],
        payload_sources: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Horizontal:
        port = path_port(index)
        label = str(config.get(f"{port}_label") or f"Branch {index + 1}")
        selected_source = str(payload_sources.get(port) or "dead_drop:input")
        valid_values = {value for _, value in source_options}
        if selected_source not in valid_values:
            selected_source = "dead_drop:input"
        label_input = CommandInput(
            value=label,
            id=f"branch-label-{port}",
            placeholder=f"Branch {index + 1}",
        )
        source_select = Select(
            source_options,
            value=selected_source,
            id=f"branch-payload-source-{port}",
            allow_blank=False,
        )
        # UX6: one line per path (name, then what it starts with); the column
        # meaning is stated once above the rows. Fewer widgets per row keeps a
        # 64-path Branch quick to open.
        row = Horizontal(
            label_input,
            source_select,
            id=f"branch-payload-row-{port}",
            classes="branch-payload-row",
        )
        self._branch_rows[port] = (row, label_input, source_select)
        return row

    def on_mount(self) -> None:
        for scroll in self.query("#node-config-scroll"):
            scroll.can_focus = False
        for scroll in self.query(".tab-scroll"):
            scroll.can_focus = False
        self._sync_merge_input_details()
        if self.query("#alias-input"):
            self.app.set_focus(self.query_one("#alias-input", CommandInput), scroll_visible=False)
        else:
            focusable = self._keyboard_focus_widgets()
            if focusable:
                self.app.set_focus(focusable[0], scroll_visible=False)
        self._sync_membank_output_controls()
        self._sync_membank_input_controls()
        self._sync_branch_payload_rows()
        self._sync_payload_previews()
        self._sync_standard_payload_controls()
        self._apply_generated_field_rules()
        self._sync_duplicate_input_source_options()
        self.call_after_refresh(self._take_opened_snapshot)
        if self.query("#alias-input"):
            self.call_after_refresh(
                lambda: self.app.set_focus(self.query_one("#alias-input", CommandInput), scroll_visible=False)
            )
            self.set_timer(
                0.01,
                lambda: self.app.set_focus(self.query_one("#alias-input", CommandInput), scroll_visible=False),
            )

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "return-end":
            self.query_one("#end-results", ContractRowsField).display = bool(event.checkbox.value)
            return
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
        self._scroll_changed_widget(event.checkbox)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "membank-output-count":
            await self._refresh_membank_output_rows()
        elif event.input.id == "branch-count":
            # Debounced: typing "64" should not sync for "6" first.
            if self._branch_count_timer is not None:
                self._branch_count_timer.stop()
            self._branch_count_timer = self.set_timer(
                BRANCH_COUNT_DEBOUNCE_SECONDS, self._sync_branch_payload_rows
            )
        elif event.input.id and event.input.id.startswith("field-"):
            self._apply_generated_field_rules()
        self._scroll_changed_widget(event.input)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "merge-carry-forward-selector":
            self._sync_merge_input_details()
        elif event.select.id and event.select.id.startswith("field-"):
            self._apply_generated_field_rules()
            self._sync_duplicate_input_source_options()
        self._scroll_changed_widget(event.select)

    def on_long_text_preview_changed(self, event):
        self._apply_generated_field_rules()

    def on_object_list_field_changed(self, event):
        self._sync_dynamic_options()

    # -- Error Mux: Source picks errors, Parameters names branches, Payloads
    # chooses what each branch passes along (frontend-only entry) ----------

    def _compose_error_mux_config_tabs(self, metadata, config: Dict[str, Any]):
        definitions = upstream_error_definitions(self.factory, self.workflow_map, self.node_id)
        self._mux_config = deepcopy(config)
        self._mux_choices = recovery_choices(definitions, config)
        self._mux_draft = MuxRouteDraft(config)
        # U1: what to do with each unpicked branch that has nodes, by port.
        self._mux_unpick_choices: Dict[str, str] = {}
        picked = set(selected_values(config))
        self._mux_rows = self._mux_rows_for(
            [value for _, value in self._mux_choices if value in picked])
        guarded = [
            str((self.workflow_map.get_node_data(node_id) or {}).get("alias") or node_id)
            for node_id in guarded_node_ids(self.workflow_map, self.node_id)
        ]
        with TabbedContent(id="node-config-tabs", classes="node-config-tabs"):
            with TabPane("1 Source", id="node-config-tab-core"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Horizontal(
                        Label("Alias:", classes="form-label-inline"),
                        CommandInput(value=self._alias_default_value(), id="alias-input"),
                        classes="form-inline-row",
                        id="alias-row",
                    )
                    yield Static(
                        "Place this right after a node. When that node succeeds, its "
                        "output continues on No error. Pick the errors to catch: each "
                        "gets its own recovery branch, and the run carries on there "
                        "instead of stopping with an error.",
                        classes="form-description",
                    )
                    yield Static(
                        f"Catching errors from: {', '.join(guarded)}" if guarded
                        else "Connect a node into this mux to see the errors it can raise.",
                        id="mux-guarded", classes="form-description",
                    )
                    yield Label("Catch these errors", classes="form-label nav-section")
                    yield SelectionList(
                        # Plain text: "[code]" must not be read as markup.
                        *[(Text(text), value, value in picked) for text, value in self._mux_choices],
                        id="mux-recover-from",
                    )
            with TabPane("2 Parameters", id="node-config-tab-parameters"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Recovery branches", classes="form-label nav-section")
                    yield Static("No error: the node's normal output (always present).",
                                 classes="form-description")
                    yield Vertical(*self._mux_parameter_rows(), id="mux-branch-rows")
            with TabPane("3 Payloads", id="node-config-tab-outputs"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("No error", classes="form-label nav-section")
                    yield Static("Passes the node's normal output on unchanged.",
                                 classes="form-description")
                    yield Vertical(*self._mux_forward_rows(), id="mux-forward-rows")
            with TabPane("4 Connections", id="node-config-tab-connections"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Label("Connections", classes="form-label nav-section")
                    yield Static("Edit connections from the editor.", classes="form-description")
                    yield from self._compose_connection_rows()
                    yield from self._compose_errors_section()

    def _mux_rows_for(self, selected: list[str]) -> list[Dict[str, Any]]:
        rows = self._mux_draft.rows(selected)
        if ANY_OTHER_ERROR in selected:
            rows.append(unmatched_route(self._mux_config))
        return rows

    def _mux_branch_title(self, row: Dict[str, Any]) -> str:
        if row["id"] == UNMATCHED_ROUTE:
            return "When: any other error"
        return "When: " + ", ".join(friendly_error_name(code) for code in row["codes"])

    def _mux_parameter_rows(self) -> list[Any]:
        if not self._mux_rows:
            return [Static("Pick errors on the Source tab to add recovery branches.",
                           classes="form-description")]
        return [
            Vertical(
                Label(self._mux_branch_title(row), classes="form-label"),
                Label("Branch name", classes="form-description"),
                CommandInput(value=row["label"], id=f"mux-route-label-{row['id']}"),
                id=f"mux-param-{row['id']}", classes="mux-branch-row",
            )
            for row in self._mux_rows
        ]

    def _mux_forward_rows(self) -> list[Any]:
        return [
            Vertical(
                Label(f"Branch for: {self._mux_branch_title(row)[6:]}",
                      classes="form-label nav-section"),
                Label("Pass along", classes="form-description"),
                Select(FORWARD_CHOICES, value=row["forward"], allow_blank=False,
                       id=f"mux-route-forward-{row['id']}"),
                id=f"mux-out-{row['id']}", classes="mux-forward-row",
            )
            for row in self._mux_rows
        ]

    def _mux_capture_edits(self) -> None:
        """Copy typed names and pass-along choices back into the row data."""
        for row in self._mux_rows:
            label_query = self.query(f"#mux-route-label-{row['id']}")
            if label_query:
                row["label"] = self._widget_text_value(label_query.first()).strip() or row["label"]
            forward_query = self.query(f"#mux-route-forward-{row['id']}")
            if forward_query and forward_query.first().value in {v for _, v in FORWARD_CHOICES}:
                row["forward"] = str(forward_query.first().value)

    async def _sync_error_mux_rows(self) -> None:
        """Rebuild the Parameters and Payloads rows from the Source picks."""
        self._mux_capture_edits()
        picked = set(self.query_one("#mux-recover-from", SelectionList).selected)
        # The draft remembers every branch, so re-picking restores it.
        self._mux_draft.record([r for r in self._mux_rows if r["id"] != UNMATCHED_ROUTE])
        for row in self._mux_rows:
            if row["id"] == UNMATCHED_ROUTE:
                self._mux_config.update(unmatched_label=row["label"],
                                        unmatched_forward=row["forward"])
        before = {row["id"]: row for row in self._mux_rows}
        self._mux_rows = self._mux_rows_for(
            [value for _, value in self._mux_choices if value in picked])
        current = {row["id"] for row in self._mux_rows}
        for port in current:
            self._mux_unpick_choices.pop(port, None)
        for port, row in before.items():
            if port not in current:
                self._confirm_unpicked_branch(port, row)
        await self._refresh_connection_rows()
        for container_id, build in (("#mux-branch-rows", self._mux_parameter_rows),
                                    ("#mux-forward-rows", self._mux_forward_rows)):
            container = self.query_one(container_id)
            await container.remove_children()
            await container.mount(*build())

    def _confirm_unpicked_branch(self, port: str, row: Dict[str, Any]) -> None:
        """U1: the last error of a branch with a downstream connection was
        unpicked; ask whether to leave its nodes unlinked or delete them."""
        outputs = (self.workflow_map.get_node_data(self.node_id) or {}).get(
            "connections", {}).get("outputs", [])
        if not any(conn.get("source_port") == port for conn in outputs):
            return
        names = friendly_labels(self.workflow_map)
        labels = [names.get(node_id) or node_id
                  for node_id in branch_nodes_for_port(self.workflow_map, self.node_id, port)]
        self.app.push_screen(
            RecoveryBranchUnpickScreen(row["label"], labels),
            lambda choice: self._on_unpick_choice(port, row, choice),
        )

    def _on_unpick_choice(self, port: str, row: Dict[str, Any], choice: Optional[str]) -> None:
        if choice is None:
            # Cancel: pick the error(s) again; the branch comes back as it was.
            picker = self.query_one("#mux-recover-from", SelectionList)
            for code in ([ANY_OTHER_ERROR] if port == UNMATCHED_ROUTE else row["codes"]):
                picker.select(code)
            return
        self._mux_unpick_choices[port] = choice

    def _mux_branch_nodes_to_delete(self) -> list[str]:
        """Nodes of unpicked branches the user chose to delete (applied on save)."""
        if self.node_data.get("type") != ERROR_MUX_NODE_TYPE or not hasattr(self, "_mux_rows"):
            return []
        current = {row["id"] for row in self._mux_rows}
        doomed: list[str] = []
        for port, choice in self._mux_unpick_choices.items():
            if choice != DELETE_BRANCH or port in current:
                continue
            for node_id in branch_nodes_for_port(self.workflow_map, self.node_id, port):
                if node_id not in doomed:
                    doomed.append(node_id)
        return doomed

    def _error_mux_config_values(self) -> Dict[str, Any]:
        if self.node_data.get("type") != ERROR_MUX_NODE_TYPE or not self.query("#mux-recover-from"):
            return {}
        self._mux_capture_edits()
        routes = [
            {"id": row["id"], "label": row["label"], "codes": list(row["codes"]),
             "forward": row["forward"]}
            for row in self._mux_rows if row["id"] != UNMATCHED_ROUTE
        ]
        values: Dict[str, Any] = {"routes": routes, "unmatched_route": False}
        for row in self._mux_rows:
            if row["id"] == UNMATCHED_ROUTE:
                values.update(unmatched_route=True, unmatched_label=row["label"],
                              unmatched_forward=row["forward"])
        return values

    def _options_from_setting(self, field: Dict[str, Any], current: Any) -> list:
        """Select options listed in Options, separated by ";" (Notify me's
        Send to names), each labelled "name · summary"."""
        key = field["options_from_setting"]
        manager = getattr(self.app, "configuration_manager", None)
        try:
            raw = manager.get(key) if manager is not None else DEFAULT_SETTINGS.get(key, "")
        except KeyError:
            raw = ""
        summary = field.get("option_summary")
        names = [part.strip() for part in str(raw or "").split(";") if part.strip()]
        options = [(f"{name} · {summary}" if summary else name, name) for name in names]
        if current not in (None, "") and current not in names:
            options.append((f"{current} (unavailable)", current))
        return options

    def _sync_dynamic_options(self):
        if self._get_form_values is None:
            return
        values = self._get_form_values()
        for name, field in self._generated_config_schema.items():
            source = field.get("options_from")
            if not source:
                continue
            query = self.query(f"#field-{name}")
            if not query or not isinstance(query.first(), Select):
                continue
            options = list(field.get("options_include") or [])
            options.extend((str(row.get("path") or row.get("id")), row["id"]) for row in values.get(source, []) if isinstance(row, dict) and row.get("id"))
            widget = query.first()
            current = widget.value
            if current not in {value for _, value in options} and current not in (None, "", Select.NULL):
                options.append((f"{current} (unavailable)", current))
            self._set_select_options_preserving_value(widget, options, current)

    def _apply_generated_field_rules(self) -> None:
        self._sync_dynamic_options()
        self._sync_routing_previews()
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
        first_source_field_by_ref: Dict[tuple[str, str], str] = {}
        first_upstream_field_by_ref: Dict[tuple[str, str], str] = {}
        duplicate_upstream_fields: set[str] = set()
        for field in source_fields:
            source_ref = upstream_refs.get(field)
            if source_ref is None:
                continue
            base_options = self._source_select_base_options.get(field)
            if base_options is None:
                query = self.query(f"#field-{field}")
                if query and isinstance(query.first(), Select):
                    base_options = list(query.first()._options)
            if not any(
                value == "Upstream payload" for _label, value in (base_options or [])
            ):
                continue
            first_source_field_by_ref.setdefault(source_ref, field)
            if values.get(field) != "Upstream payload":
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
            upstream_reserved_elsewhere = (
                source_ref is not None
                and first_source_field_by_ref.get(source_ref) != source_field
            )
            if (
                current == "Upstream payload"
                and (
                    source_field in duplicate_upstream_fields
                    or upstream_reserved_elsewhere
                )
            ):
                fallback = self._fallback_source_value(options, "Upstream payload")
                if fallback is not None and fallback != current:
                    widget.value = fallback
                    values[source_field] = fallback
                    current = fallback
                    changed = True
            if current != "Upstream payload" and upstream_reserved_elsewhere:
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

    async def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        if event.selection_list.id == "mux-recover-from":
            await self._sync_error_mux_rows()
        elif event.selection_list.id == "merge-branches-to-close":
            self._sync_merge_carry_forward_selector()
            self._sync_merge_input_details()
        elif event.selection_list.id == "wait-targets":
            self.query_one("#wait-target-summary", Static).update(
                self._wait_target_summary(event.selection_list.selected))
        elif event.selection_list.id == "membank-inputs":
            self._sync_branch_payload_rows()
            self._sync_payload_previews()
        self._scroll_changed_widget(event.selection_list)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "stash-insert-node-config":
            self.action_stash_insert()
            return
        if event.button.id == "save-node-config":
            self.action_save()
        elif event.button.id == "cancel-node-config":
            self.action_cancel()
        elif event.button.id == "catch-errors":
            self.action_catch_errors()
        elif event.button.id == "sub-change":
            self._open_subworkflow_picker()
        elif event.button.id in self._connection_targets:
            self._leave(jump_to=self._connection_targets[event.button.id])

    def action_catch_errors(self) -> None:
        """Save this node, then let the editor spawn or open its Error Mux."""
        self.action_save(then="catch_errors")

    def action_save(self, then: Optional[str] = None) -> None:
        """Save and close (the Save button, the catch-errors button)."""
        self._commit_text_edit()
        result = self._save_result(then)
        if result is not None:
            self.dismiss(result)

    async def action_save_and_stay(self) -> None:
        """Ctrl+S / Ctrl+Enter: save and keep the editor open (owner,
        2026-10-13). A text field being edited is committed first."""
        expanded_select = self._expanded_select()
        if expanded_select is not None:
            expanded_select.expanded = False
            expanded_select.focus()
        self._commit_text_edit()
        result = self._save_result()
        if result is None:
            return
        # Taken before the save: the editor's refresh behind this screen can
        # move focus, and the row refresh replaces the row widgets.
        focused = self.focused
        focus_key = self._focused_connection_key()
        scroll = self._connection_scroll()
        scroll_y = scroll.scroll_y if scroll is not None else None
        if self._on_save is not None:
            self._on_save(result)
            self._refresh_node_data()
            self._original_config = deepcopy(self.node_data.get("config") or {})
            if hasattr(self, "_mux_unpick_choices"):
                self._mux_unpick_choices.clear()  # applied by the save
        else:
            self._saved_result = result
            self._original_config = deepcopy(result["config"])
        # What is on screen now is the saved state.
        self._opened_config = None
        self._take_opened_snapshot()
        await self._refresh_connection_rows(focus_key=focus_key, scroll_y=scroll_y)
        if focus_key is not None:
            return  # the row refresh restored focus by connection
        if focused is not None and focused.is_attached and focused.screen is self:
            self.app.set_focus(focused, scroll_visible=False)
        else:
            self._focus_first()

    # -- Stash S3: insert an entry into a field ---------------------------------

    def _focused_stash_widget(self, focused):
        """Resolve the exact generated text field, including composite owners.

        A nested Select/model input belongs to its outer field; it must not
        reuse the previous text field or assign through a picker container.
        """
        if focused is None:
            return None
        for widget in focused.ancestors_with_self:
            if widget is self:
                break
            widget_id = str(widget.id or "")
            if widget_id.startswith("field-"):
                if isinstance(widget, (CommandInput, CommandTextArea)):
                    return widget
                from frontend.widgets.long_text import LongTextPreview
                return widget if isinstance(widget, LongTextPreview) else None
        return None

    def action_stash_insert(self) -> None:
        """Insert into the focused text/file field; selectors never redirect."""
        from backend.field_types import stash_insert_target

        origin = self.focused
        widget = self._focused_stash_widget(origin)
        field = widget.id.removeprefix("field-") if widget is not None else None
        metadata = self.factory.metadata_for_type(self.node_data.get("type", "")) or {}
        target = stash_insert_target(metadata.get("config_schema") or {}, field) if field else None
        if target is None or target["field"] != field:
            notifications.notify_info(self.app, "Stash text can't go into this field")
            return
        self.app.action_stash(
            "entries",
            insert_into={"label": target["label"], "accepts": target["accepts"]},
            callback=lambda entry: self._insert_stash_entry(target, entry, widget, origin),
        )

    def _insert_stash_entry(self, target, entry, widget, origin) -> None:
        if not entry:
            return
        # Capture the actual field, not a name resolved after an async picker.
        # Removed/replaced widgets or a changed focus cancel the assignment.
        if (not widget.is_attached or widget.screen is not self or widget.disabled
                or not widget.visible or self.focused is not origin):
            notifications.notify_info(self.app, "Stash text can't go into this field")
            return
        from backend.file_refs import reference_path
        from frontend.widgets.long_text import LongTextPreview

        value = reference_path(entry["value"]) if entry["type"] == "file" else str(entry["value"])
        if isinstance(widget, LongTextPreview):
            widget.replace_from_stash(value, self._apply_generated_field_rules)
            return
        if isinstance(widget, CommandTextArea):
            widget.text = value
        else:
            widget.value = value
        self._apply_generated_field_rules()
        notifications.notify_info(self.app, f"Inserted '{entry['name']}' into {target['label']}")

    def _commit_text_edit(self) -> None:
        for widget in (getattr(self, "_active_command_text_widget", None), self.app.focused):
            if is_editing_text(widget):
                widget.end_edit()

    def _alias_value(self) -> str:
        alias_query = self.query("#alias-input")
        return alias_query.first().value if alias_query else self.node_data.get("alias", "")

    def _is_dirty(self) -> bool:
        """Edits since opening or the last save (U9; relies on UX2's no-edit invariant)."""
        if self._opened_config is None:
            return False
        try:
            collected = self._collected_config()
        except ValueError:
            return True
        return (collected != self._opened_config or self._alias_value() != self._opened_alias
                or self._send_back_choices() != getattr(self, "_send_back_opened", {}))

    def _leave(self, jump_to: Optional[str] = None) -> None:
        """Close, or jump to another node's editor; ask Save / Discard / Stay
        first when there are unsaved edits (U9)."""
        if not self._is_dirty():
            self._close(None, jump_to)
            return

        def answered(choice: Optional[str]) -> None:
            if choice == SAVE:
                result = self._save_result()
                if result is not None:
                    self._close(result, jump_to)
            elif choice == DISCARD:
                self._close(None, jump_to)

        name = friendly_label(self.workflow_map, self.node_id)
        self.app.push_screen(UnsavedChangesScreen(name), answered)

    def _close(self, result: Optional[Dict[str, Any]], jump_to: Optional[str]) -> None:
        if result is None and self._on_save is None:
            # Nothing applied the saves made while staying open: return the last.
            result = self._saved_result
        if jump_to:
            result = {**(result or {}), "then": "jump", "jump_to": jump_to}
        self.dismiss(result)

    def _save_result(self, then: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """The save the screen describes now, or None when it cannot be saved."""
        alias = self._alias_value()
        if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
            selected = self._wait_config_values()["target_node_ids"]
            eligible = {value for _, value in wait_target_options(self.workflow_map, self.node_id)}
            message = ""
            if any(target not in eligible for target in selected):
                message = "Remove unavailable wait targets before saving."
            if message:
                self.query_one("#wait-config-error", Static).update(message)
                notifications.notify_error(self.app, message)
                return None
        try:
            config = self._collected_config()
        except ValueError as error:
            notifications.notify_error(self.app, str(error))
            return None
        send_back, send_back_problem = self._send_back_plan()
        if send_back_problem:
            notifications.notify_error(self.app, send_back_problem)
            return None
        numbers, problems = self._checked_numbers(config)
        if problems:
            count = len(problems)
            notifications.notify_error(
                self.app, f"Fix {count} number field{'s' if count > 1 else ''} before saving")
            return None
        metadata = self._metadata_for_type(self.node_data.get("type", "")) or {}
        row_problems = object_list_problems(metadata.get("config_schema") or {}, config)
        if row_problems:
            notifications.notify_error(self.app, row_problems[0])
            return None
        # The no-edit comparison runs on what the widgets showed; checked
        # numbers then replace only the keys that are being written.
        saved = self._without_untouched_defaults(config)
        saved.update({key: value for key, value in numbers.items() if key in saved})
        result = {"alias": alias, "config": saved}
        if then:
            result["then"] = then
        doomed = self._mux_branch_nodes_to_delete()
        if doomed:
            result["delete_branch_nodes"] = doomed
        self._apply_send_back(send_back)
        return result

    def _checked_numbers(self, config: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, str]]:
        """C5: check every visible number field (``field_types.check_number``,
        the validator's rule). Returns the parsed values (blank becomes the
        default) and ``{field: problem}``; each problem is shown under its
        field, the typed text stays, and the first bad field gets focus."""
        metadata = self._metadata_for_type(self.node_data.get("type", "")) or {}
        defaults = metadata.get("default_config") or {}
        # The type's whole schema: custom controls (Branch count) count too.
        schema = metadata.get("config_schema") or {}
        numbers: Dict[str, Any] = {}
        problems: Dict[str, str] = {}
        first_bad = None
        for name, info in number_fields(schema):
            widgets = list(self.query(f"#field-{name}")) or list(
                self.query(CUSTOM_NUMBER_CONTROLS.get(name, "#none")))
            if not widgets or not field_visible(config, defaults, info):
                continue
            raw = getattr(widgets[0], "value", config.get(name))
            value, problem = check_number(info, raw, defaults.get(name))
            self._show_field_error(widgets[0], name, problem)
            if problem:
                problems[name] = problem
                first_bad = first_bad or widgets[0]
            else:
                numbers[name] = value
        if first_bad is not None:
            self.set_focus(first_bad)
        return numbers, problems

    def _show_field_error(self, widget: Any, name: str, problem: str) -> None:
        """Show (or clear) a one-line problem under a field."""
        existing = list(self.query(f"#field-error-{name}"))
        if not problem:
            for item in existing:
                item.remove()
            return
        if existing:
            existing[0].update(problem)
            return
        # Under the whole row when the input shares a line with its label.
        anchor = widget.parent if widget.parent.has_class("form-inline-row") else widget
        anchor.parent.mount(
            Static(problem, id=f"field-error-{name}", classes="field-error", markup=False),
            after=anchor,
        )

    def _wait_timeout_value(self) -> Optional[float]:
        """Wait Until's timeout under the C5 policy (blank = default 0)."""
        metadata = self._metadata_for_type(self.node_data.get("type", "")) or {}
        info = (metadata.get("config_schema") or {}).get("timeout_seconds") or {}
        default = (metadata.get("default_config") or {}).get("timeout_seconds")
        value, problem = check_number(
            info, self.query_one("#field-timeout_seconds", Input).value, default)
        return None if problem else value

    def _collected_config(self) -> Dict[str, Any]:
        """The config the widgets describe now (raises ValueError on Merge overflow)."""
        config = dict(self.node_data.get("config") or {})
        if self._get_form_values:
            config.update(self._get_form_values())
        if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
            # Keep unrelated config, but retire declarations that falsely claim
            # this coordination node reads/writes Vault or configures outputs.
            config = dict(self.node_data.get("config") or {})
            timeout = self._wait_timeout_value()
            config.update(target_node_ids=self._wait_config_values()["target_node_ids"],
                          timeout_seconds=timeout if timeout is not None
                          else self.query_one("#field-timeout_seconds", Input).value,
                          membank_inputs=[], membank_outputs=[], transient_outputs=[])
            config.update(self._error_path_config_values())
            return config
        if self.query("#start-inputs") or self.query("#return-end") or self.query("#sub-inputs"):
            # Start and a subworkflow's End have no Payloads tab: their
            # routing lives in the rows, so nothing else is collected.
            config.update(self._error_path_config_values())
            config.update(self._contract_config_values())
            return config
        config.update(self._transient_config_values())
        config.update(self._membank_config_values())
        config.update(self._standard_payload_config_values())
        config.update(self._wait_config_values())
        config.update(self._branch_config_values())
        config.update(self._error_path_config_values())
        config.update(self._error_mux_config_values())
        config.update(self._merge_config_values())
        config.update(self._contract_config_values())
        return config

    def _take_opened_snapshot(self) -> None:
        if self._opened_config is not None:
            return
        self._opened_alias = self._alias_value()
        try:
            self._opened_config = deepcopy(self._collected_config())
        except Exception:
            # A screen that cannot describe itself yet keeps every value.
            self._opened_config = {}

    def _without_untouched_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """No-edit invariant: a save without edits keeps the stored config.

        When the widgets still describe exactly what the screen showed on
        opening, a key the stored config lacked stays absent (the node keeps
        its own fallback) and a stored empty value ("", None, [], {}) is kept.
        Non-empty values the save corrects (migrations, retired declarations)
        are written as collected. A save with any edit is written as
        collected, as before, so defaults shown in widgets are materialised.
        """
        opened = self._opened_config
        if opened is None:
            # Saved before the first refresh: nothing can have been edited.
            opened = config
        if opened != config:
            return config
        original = self._original_config
        result = dict(config)
        for key, value in config.items():
            if key not in original:
                result.pop(key)
            elif _is_empty_config_value(original[key]) and original[key] != value:
                result[key] = deepcopy(original[key])
        return result

    def action_cancel(self) -> None:
        expanded_select = self._expanded_select()
        if expanded_select is not None:
            expanded_select.expanded = False
            expanded_select.focus()
            return
        self._leave()

    def action_cursor_up(self) -> None:
        focused = self.app.focused
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
        # An empty list has no row to move to, so the cursor moves past it.
        if selection_list.option_count == 0:
            return True
        highlighted = getattr(selection_list, "highlighted", None)
        if highlighted is None:
            return False
        return highlighted >= selection_list.option_count - 1

    def _selection_list_at_top(self, selection_list: SelectionList) -> bool:
        if selection_list.option_count == 0:
            return True
        highlighted = getattr(selection_list, "highlighted", None)
        if highlighted is None:
            return False
        return highlighted <= 0

    def _reply_fields_at_focus(self):
        from frontend.widgets.reply_fields import ReplyFields
        focused = self.app.focused
        while focused is not None:
            if isinstance(focused, ReplyFields):
                return focused
            focused = focused.parent
        return None

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "remove_field":
            return self._reply_fields_at_focus() is not None
        return super().check_action(action, parameters)

    async def action_remove_field(self) -> None:
        field = self._reply_fields_at_focus()
        if field is not None:
            await field.remove_selected()

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
        if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
            views = getattr(self, "_wait_tab_views", {})
            scroll = self._scroll_container()
            focused = self.app.focused
            if focused is not None and self._is_descendant_of(focused, self.query_one(f"#{tabs.active}", TabPane)):
                views[tabs.active] = (focused.id, float(scroll.scroll_y) if scroll else 0)
            self._wait_tab_views = views
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
        if self.node_data.get("type") == WAIT_UNTIL_NODE_TYPE:
            saved = getattr(self, "_wait_tab_views", {}).get(tab_id)
            if saved and saved[0]:
                widget = self.query(f"#{saved[0]}")
                if widget:
                    self.app.set_focus(widget.first(), scroll_visible=False)
                    scroll = self._scroll_container()
                    if scroll:
                        scroll.scroll_to(y=saved[1], animate=False)
                    self._sync_cursor_mode()
                    return
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
                focus_command_widget(self, widgets[0], scroll, scroll_on_focus=False)
                self.call_after_refresh(
                    lambda target=widgets[0]: self._scroll_config_widget_into_view(target)
                )
                self._sync_cursor_mode()
                return
            except Exception:
                pass
        save_query = self.query("#save-node-config")
        if save_query:
            self.app.set_focus(save_query.first(), scroll_visible=False)
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
        rows = group_widgets_into_rows(widgets)
        if current in widgets and any(len(row) > 1 for row in rows):
            # Widgets side by side (Branch path rows) are one line: W/S move a
            # whole row and keep the column (UI_QUICK_REFERENCE command rules).
            target, _at_boundary = row_move_target(rows, current, direction)
        else:
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
            focus_command_widget(self, target, scroll, scroll_on_focus=False)
            self.call_after_refresh(
                lambda target=target: self._scroll_config_widget_into_view(target)
            )
        except Exception:
            focus_command_widget(self, target, scroll_on_focus=False)

    def _scroll_config_widget_into_view(self, target: Any) -> None:
        try:
            if target is not self.app.focused:
                return
            scroll = self._scroll_container()
            if scroll is None:
                return
            if self._is_descendant_of(target, scroll):
                scroll.scroll_to_widget(target, animate=False, immediate=True)
        except Exception:
            pass

    def _scroll_changed_widget(self, changed_widget: Any) -> None:
        """Keep the active field visible; initialization must not move the view."""
        if changed_widget is not self.app.focused:
            return
        self.call_after_refresh(
            lambda widget=changed_widget: self._scroll_changed_widget_now(widget)
        )

    def _scroll_changed_widget_now(self, changed_widget: Any) -> None:
        if changed_widget is not self.app.focused:
            return
        widgets = self._keyboard_focus_widgets()
        if not widgets:
            return
        if changed_widget not in widgets:
            return
        self._scroll_config_widget_into_view(changed_widget)

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
        # Only the type's declared ports get generated name fields;
        # config-driven ports (Error Mux routes) are named in their own config.
        declared = set(self.factory.declared_output_ports(str(self.node_data.get("type") or "")))
        output_ports = [port for port in self._downstream_output_ports(metadata) if port in declared]
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
        return bool((metadata or {}).get("ui_hints", {}).get("legacy_vault_outputs"))

    def _uses_standard_source_model(self, metadata: Optional[Dict[str, Any]]) -> bool:
        """True when any input port declares the standard source model.

        Standard-model nodes get the redesigned config layout: auto incoming
        payload summary, per-input typed vault dropdowns, and no legacy
        membank/reveal sections. Legacy nodes keep the old flat layout
        (docs/archive/IO_CONTRACT_UI_DESIGN.md fallback rule).
        """
        if metadata is None:
            return False
        port_meta = metadata.get("input_port_metadata") or {}
        return bool((metadata.get("ui_hints") or {}).get("standard_output")) or any(
            (port_meta.get(str(port)) or {}).get("sources")
            for port in self.factory.node_input_ports(self.node_data)
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
        target_counts: Dict[str, int] = {}
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
            data_type = str(producer.get("data_type") or producer_out.get("data_type") or "any")

            lines = []
            if len(inputs) > 1:
                lines.append(f"Input: {target_port.replace('_', ' ')}")
            lines.append(f"Node source: {source_label}")
            lines.append(f"Payload: {payload_name} ({data_type})")
            if description and description != OUTPUT_NOT_CONFIGURED:
                lines.append(f"Payload desc: {description}")
            if self.memory_bank is not None:
                value = self.memory_bank.read_transient(
                    source_id, source_port, default=_MISSING_PAYLOAD
                )
                if value is not _MISSING_PAYLOAD:
                    lines.append(f"Value: {self._short_value_text(value)}")
            # Read-only summary: plain Static so keyboard navigation skips it.
            index = target_counts.get(target_port, 0)
            target_counts[target_port] = index + 1
            suffix = f"-{index}" if index else ""
            yield Static(
                "\n".join(lines),
                classes="form-description incoming-payload-summary",
                id=f"incoming-payload-{target_port}{suffix}",
            )

    def _sync_standard_payload_controls(self) -> None:
        """Hide controls whose routing toggle makes them inapplicable."""
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        if not self._uses_standard_source_model(metadata):
            return
        dead_drop_query = self.query("#dead-drop-passthrough")
        forwarding = bool(dead_drop_query.first().value) if dead_drop_query else False
        for port in self._downstream_output_ports(metadata):
            for row in (f"downstream-name-row-{port}", f"downstream-desc-row-{port}"):
                for widget in self.query(f"#{row}"):
                    widget.display = not forwarding
            for suffix in (f"transient-output-name-{port}", f"transient-output-desc-{port}"):
                for widget in self.query(f"#{suffix}"):
                    widget.disabled = forwarding
        for port in self._vault_output_ports(metadata):
            disable_query = self.query(f"#vault-output-disabled-{port}")
            disabled = bool(disable_query.first().value) if disable_query else False
            for row in (f"vault-key-row-{port}", f"vault-desc-row-{port}"):
                for widget in self.query(f"#{row}"):
                    widget.display = not disabled
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
            "transient_output": bool(self.query_one("#publish-downstream", Checkbox).value) if self.query("#publish-downstream") else not dead_drop,
        }
        # Each Vault port has independent routing state. The first keeps the
        # established vault_write* keys for compatibility with existing nodes.
        fields = vault_output_fields(metadata or {})
        for port in self._vault_output_ports(metadata):
            enabled_field, key_field, desc_field = fields[port]
            disable_query = self.query(f"#vault-output-disabled-{port}")
            disabled = bool(disable_query.first().value) if disable_query else False
            key_query = self.query(f"#vault-output-key-{port}")
            desc_query = self.query(f"#vault-output-desc-{port}")
            values[enabled_field] = not disabled
            values[key_field] = (
                self._widget_text_value(key_query.first()) if key_query else ""
            )
            values[desc_field] = (
                self._widget_text_value(desc_query.first()) if desc_query else ""
            )
        return values

    def _sync_routing_previews(self) -> None:
        metadata = self._metadata_for_type(self.node_data.get("type", "")) or {}
        hints = metadata.get("ui_hints") or {}
        values = dict(self.node_data.get("config") or {})
        if self._get_form_values:
            values.update(self._get_form_values())
        for port, field in (hints.get("output_value_fields") or {}).items():
            for widget in self.query(f"#configured-output-preview-{port}"):
                widget.update(f"Configured in Parameters: {self._short_value_text(values.get(field, ''))}\nEdit the value in Parameters; choose its destinations here.")
        for widget in self.query("#formatted-output-preview"):
            value = _MISSING_PAYLOAD
            if values.get("input_source") == "Vault":
                key = str(values.get("input_vault_key") or "")
                source = f"Vault: {key or '(no key selected)'}"
                if self.memory_bank is not None and key:
                    value = self.memory_bank.read_persistent(key, default=_MISSING_PAYLOAD)
            else:
                source = "Upstream payload"
                connection = next((c for c in self.node_data.get("connections", {}).get("inputs", []) if c.get("target_port") == "input"), None)
                if connection and self.memory_bank is not None:
                    value = self.memory_bank.read_transient(connection["source_node_id"], connection.get("source_port", "default"), default=_MISSING_PAYLOAD)
            label = values.get("label", "Output")
            template = values.get("template", "{input}")
            lines = [f"Source: {source}", f"Output format: {text_output_prefix(label)}{template}"]
            if values.get("request_user_input"):
                lines.append("The prompted user response replaces the selected input at execution.")
            elif value is _MISSING_PAYLOAD:
                lines.append("Preview available after the selected source produces a value.")
            else:
                try:
                    lines.append("Preview (captured value): " + self._short_value_text(text_output_prefix(label) + template.format(input=value)))
                except (KeyError, IndexError, ValueError) as error:
                    lines.append(f"Invalid template: {error}")
            connected = bool(self.node_data.get("connections", {}).get("outputs"))
            lines.append("Routing: " + ("Continues along its connection after recording output." if connected and not metadata.get("terminates_branch") else "Ends here after recording output."))
            widget.update("\n".join(lines))

    def _short_value_text(self, value: Any) -> str:
        """One-line captured-value preview, truncated for the summary block."""
        if isinstance(value, (list, tuple, set, dict)):
            return f"({type(value).__name__}, {len(value)} items)"
        rendered = str(value)
        if len(rendered) > 400:
            rendered = f"{rendered[:397]}..."
        return rendered

    def _own_output_ports(self, metadata: Optional[Dict[str, Any]]) -> list[str]:
        """This node's output ports, resolved by the backend from its config."""
        if not metadata:
            return []
        return self.factory.node_output_ports(self.node_data)

    def _downstream_output_ports(self, metadata: Optional[Dict[str, Any]]) -> list[str]:
        """Output ports routed downstream (the designated node payload)."""
        port_meta = (metadata or {}).get("output_port_metadata") or {}
        ports = []
        for port in self._own_output_ports(metadata):
            routing = (port_meta.get(str(port)) or {}).get("to")
            if routing is None or "downstream" in routing:
                ports.append(str(port))
        return ports

    def _vault_output_ports(self, metadata: Optional[Dict[str, Any]]) -> list[str]:
        """Output ports that may be keyed to the Vault."""
        port_meta = (metadata or {}).get("output_port_metadata") or {}
        return [
            str(port)
            for port in self._own_output_ports(metadata)
            if "vault" in ((port_meta.get(str(port)) or {}).get("to") or [])
        ]

    def _output_header(self, metadata: Optional[Dict[str, Any]], port: str) -> Text:
        """Rich `Name [type]` header for an output port."""
        info = ((metadata or {}).get("output_port_metadata") or {}).get(port) or {}
        # A config-driven type (Recall's Type) wins over the class default.
        info = {**info, **(self.factory.node_output_port_metadata(self.node_data).get(port) or {})}
        name = output_display_name(self.factory, self.node_data, port)
        data_type = str(info.get("data_type") or "any")
        return Text.assemble(
            (name, f"bold {colors.PAYLOAD}"),
            "  [",
            (data_type, f"bold {colors.TYPE}"),
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
        "Forward incoming payload unchanged" checkbox beneath it (hides the
        downstream fields), then optional Vault payloads (each an editable key
        + description with a "Disable output" checkbox for optional outputs).
        Model per NODE_STANDARDS.md: one downstream output, the rest vault.
        """
        downstream_ports = self._downstream_output_ports(metadata)
        vault_ports = self._vault_output_ports(metadata)
        port_meta = (metadata or {}).get("output_port_metadata") or {}

        hints = (metadata or {}).get("ui_hints") or {}
        if hints.get("formatted_output_preview"):
            yield Label("Output log", classes="form-label nav-section")
            yield Static("Any selected payload is formatted as text. File references print as references; use File Reader for contents.", classes="form-description")
            yield Static("", id="formatted-output-preview", classes="form-description", markup=False)
        if downstream_ports:
            yield Label("Downstream node payload", classes="form-label nav-section")
        if any((port_meta.get(port) or {}).get("data_type") == "file"
               for port in downstream_ports + vault_ports):
            yield Static(
                "The same file keeps the same reference. Display names and Vault keys "
                "label that reference; they do not create copies or versions of the file. "
                "Creating a different file produces a different reference.",
                classes="form-description",
                id="file-reference-output-note",
            )
        for port in downstream_ports:
            name = output_display_name(self.factory, self.node_data, port)
            description = output_display_description(self.factory, self.node_data, port)
            yield Static(
                self._output_header(metadata, port),
                classes="payload-header",
                id=f"downstream-header-{port}",
            )
            if hints.get("formatted_output_preview"):
                continue
            if port in (hints.get("output_value_fields") or {}):
                yield Static("", id=f"configured-output-preview-{port}", classes="form-description", markup=False)
                continue
            yield Horizontal(
                Label("Display name:" if (port_meta.get(port) or {}).get("data_type") == "file"
                      else "Payload name:", classes="form-label-inline"),
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
        supports_forwarding = any(
            (port_meta.get(port) or {}).get("pass_through")
            for port in downstream_ports
        )
        if downstream_ports and not supports_forwarding and vault_ports:
            yield Checkbox("Publish downstream payload", value=bool(config.get("transient_output", True)), id="publish-downstream")
        if supports_forwarding:
            forwarded_port = ((metadata or {}).get("ui_hints") or {}).get("forwarded_input_port")
            if ((metadata or {}).get("ui_hints") or {}).get("forwarded_input_fallbacks"):
                connected = {c.get("target_port") for c in self.node_data.get("connections", {}).get("inputs", [])}
                forwarded_port = next((p for p in [forwarded_port] + (metadata["ui_hints"]["forwarded_input_fallbacks"]) if p in connected), None)
            forwarded_name = (((metadata or {}).get("input_port_metadata") or {}).get(forwarded_port) or {}).get("name")
            yield Checkbox(
                f"Forward incoming {forwarded_name} payload unchanged" if forwarded_name
                else "Forward incoming payload unchanged",
                value=bool(config.get("dead_drop_passthrough")),
                id="dead-drop-passthrough",
            )

        if vault_ports:
            plural = "s" if len(vault_ports) > 1 else ""
            yield Label(f"Vault Payload{plural}", classes="form-label nav-section")
            fields = vault_output_fields(metadata or {})
            for port in vault_ports:
                enabled_field, key_field, desc_field = fields[port]
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
                        value=not bool(config.get(enabled_field, enabled_field == "vault_write")),
                        id=f"vault-output-disabled-{port}",
                    )
                default_key = str(config.get(key_field) or "").strip()
                default_desc = str(config.get(desc_field) or "").strip()
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
                if self._is_subworkflow():
                    if self._return_end() is None:
                        yield Static('To send it back, tick "Send results back" on an End node.',
                                     classes="form-description", markup=False)
                    else:
                        sent = (default_key or "") in self._sent_back_keys() if default_key else False
                        self._send_back_opened = {**getattr(self, "_send_back_opened", {}),
                                                  port: (sent, default_key or "")}
                        yield Checkbox("Send back to calling workflow", value=sent, id=f"send-back-{port}")

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

    def _compose_errors_section(self):
        """D8/U4: the node's errors in plain words, and one widget that spawns
        or opens the Error Mux catching them. Picking which errors to catch
        happens in the mux editor (U6); this shows status and an action."""
        yield Label("Errors", classes="form-label nav-section")
        # The catch widget sits under the header, above the list (owner, Q5).
        if self.node_data.get("type") != ERROR_MUX_NODE_TYPE:
            yield from self._compose_catch_widget()
        yield Static(
            self._format_error_definitions(),
            id="error-definitions",
            classes="form-description",
        )

    def _compose_catch_widget(self):
        if not self.factory.node_output_ports(self.node_data):
            return  # nothing to place an inline Error Mux after (End, Beacon)
        mux_id = inline_mux_for(self.workflow_map, self.node_id)
        if mux_id:
            count = caught_error_count(self.workflow_map, mux_id)
            label = f"Open Error Resolver Node ({count} caught)"
        else:
            label = "Add Error Resolver Node"
        # Kept plain on purpose (owner): one solid button, no status line.
        yield Button(label, id="catch-errors", variant="primary", compact=True,
                     classes="catch-errors-button")

    def _error_path_config_values(self) -> Dict[str, Any]:
        # U4/U10: no editable error-path control any more; a stored
        # show_error_path stays in the config unchanged and keeps its path.
        return {}

    def _format_error_definitions(self) -> Text:
        metadata = self._metadata_for_type(str(self.node_data.get("type") or "")) or {}
        text = Text()
        for error in metadata.get("errors") or []:
            if text:
                text.append("\n")
            # One plain line per error, code first (owner, Q5).
            description = str(error.get("description") or "").strip()
            text.append(f"  • [{error.get('code')}] {description}".rstrip())
        return text if text else Text("  (none)")

    def _compose_connection_rows(self):
        yield Vertical(*self._connection_row_widgets(), id="connection-rows")

    def _connection_row_widgets(self) -> list[Any]:
        """UX5: one row per connection and Vault read; Enter on a row jumps
        to the node at the other end."""
        self._refresh_node_data()
        # Error Mux: ports of the branches picked right now (before save).
        mux_ports = None
        if self.node_data.get("type") == ERROR_MUX_NODE_TYPE and hasattr(self, "_mux_rows"):
            mux_ports = {"default"} | {row["id"] for row in self._mux_rows}
        rows = connection_rows(self.workflow_map, self.factory, self.node_id, mux_ports)
        self._connection_targets = {}
        self._connection_keys = {}
        widgets: list[Any] = []
        for section, title in (("incoming", "Incoming"), ("outgoing", "Outgoing"),
                               ("vault", "Vault reads")):
            if section == "vault" and not rows["vault"]:
                continue
            widgets.append(Label(title, classes="form-label connection-heading"))
            if not rows[section]:
                widgets.append(Static("  (none)", classes="form-description"))
            for index, row in enumerate(rows[section]):
                widget_id = f"connection-{section}-{index}"
                self._connection_keys[widget_id] = row["key"]
                if row["target"]:
                    self._connection_targets[widget_id] = row["target"]
                    widgets.append(Button(Text(row["text"]), id=widget_id, compact=True,
                                          classes="connection-row"))
                else:
                    widgets.append(Static(f"  {row['text']}", id=widget_id,
                                          classes="form-description", markup=False))
        return widgets

    def _focused_connection_key(self) -> Optional[tuple]:
        focused = self.focused
        if focused is None or not focused.id:
            return None
        return self._connection_keys.get(focused.id)

    def _connection_scroll(self) -> Any:
        rows = self.query("#connection-rows")
        return rows.first().parent if rows else None

    async def _refresh_connection_rows(
        self,
        focus_key: Optional[tuple] = None,
        scroll_y: Optional[float] = None,
    ) -> None:
        """Rebuild the rows. A focused row keeps focus by its connection (its
        direction and both node/port ends, or Vault key and writer), not its
        position; if that connection is gone the first row takes focus. The
        tab keeps its scroll position."""
        if focus_key is None:
            focus_key = self._focused_connection_key()
        scroll = self._connection_scroll()
        if scroll_y is None and scroll is not None:
            scroll_y = scroll.scroll_y
        for container in self.query("#connection-rows"):
            await container.remove_children()
            await container.mount(*self._connection_row_widgets())
        if scroll is not None and scroll_y is not None:
            scroll.scroll_to(y=scroll_y, animate=False)
            self.call_after_refresh(scroll.scroll_to, y=scroll_y, animate=False)
        if focus_key is None:
            return
        match = next((widget_id for widget_id, key in self._connection_keys.items()
                      if key == focus_key and widget_id in self._connection_targets), None)
        rows = list(self.query(".connection-row"))
        target = self.query_one(f"#{match}") if match else (rows[0] if rows else None)
        if target is not None:
            self.app.set_focus(target, scroll_visible=False)
        else:
            self._focus_first()

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
            value = self.memory_bank.read_transient(source_id, source_port, default=_MISSING_PAYLOAD)
            has_value = value is not _MISSING_PAYLOAD
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
                value = self.memory_bank.read_persistent(output_id, default=_MISSING_PAYLOAD)
                has_value = value is not _MISSING_PAYLOAD
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
        if self.node_data.get("type") != BRANCH_NODE_TYPE:
            return
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
        self._sync_routing_previews()
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
        yield Label("Payload count", classes="form-description", id="membank-output-count-label")
        yield count_input
        yield Vertical(id="membank-output-rows")

    def _compose_membank_inputs(self, config: Dict[str, Any]):
        if self.node_data.get("type") != BRANCH_NODE_TYPE:
            return
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
            yield Static("The vault is empty", classes="form-description", id="membank-inputs-empty")

    def _compose_transient_outputs(
        self,
        metadata: Optional[Dict[str, Any]],
        config: Dict[str, Any],
    ):
        ports = self._own_output_ports(metadata)
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
        options.sort(key=lambda row: (row[0].casefold(), row[1]))
        eligible = {value for _, value in options}
        downstream = self.workflow_map.nodes_reachable_from(self.node_id)
        for node_id in sorted(selected - eligible):
            node = self.workflow_map.get_node_data(node_id)
            reason = ("self" if node_id == self.node_id else
                      "downstream" if node_id in downstream else "missing")
            label = (node or {}).get("alias") or node_id
            options.append((f"Unavailable target: {label} ({reason}; {node_id})", node_id))
        if options:
            targets = SelectionList(*dynamic_selection_rows(options, selected), id="wait-targets")
            targets.styles.height = min(6, len(options) + 2)
            yield targets
        else:
            yield Static("No non-downstream wait targets are available.", classes="form-description")

    def _compose_merge_inputs(self, config: Dict[str, Any]):
        options = merge_input_options(self.workflow_map, self.node_id)
        # Backstop: saved values that match no current option are kept as
        # they are (and shown), never dropped silently on save.
        self._merge_kept_close, self._merge_kept_carry = unmatched_merge_values(
            options, config, _reserved_merge_input_ports(self.workflow_map, self.node_id)
        )
        self._merge_kept_carry_config = {
            key: config.get(key, "")
            for key in ("carry_forward_branch_id", "selected_branch_id")
        }
        yield Label("Paths joined here", classes="form-label nav-section", id="merge-slots-label")
        slot_lines = merge_slot_lines(self.workflow_map, self.node_id)
        yield Static(
            "\n".join(slot_lines) or "Nothing is connected to this Merge yet.",
            id="merge-slots",
            classes="form-description",
            markup=False,
        )
        reserved = _reserved_merge_input_ports(self.workflow_map, self.node_id)
        if not options:
            if not reserved:
                yield Static("No open branches are available to close.", classes="form-description")
            if not reserved and not (self._merge_kept_close or self._merge_kept_carry):
                return
        selected_values = self._selected_merge_close_values(options, config)
        selected_values |= set(self._merge_kept_close)
        capacity = len(ALL_PATH_PORTS) - len(_reserved_merge_input_ports(self.workflow_map, self.node_id))
        if options or self._merge_kept_close:
            yield Static(f"Select up to {capacity} branches to close; home inputs reserve the remaining ports.", classes="form-description")
        if self._merge_kept_close or self._merge_kept_carry:
            yield Static(
                merge_unmatched_warning(self._merge_kept_close, self._merge_kept_carry),
                id="merge-unmatched-warning",
                classes="form-description merge-unmatched-warning",
            )
        rows = [
            (option["description"], self._merge_option_value(option))
            for option in options
        ] + [
            (f"Kept, no longer matches a branch: {value}", value)
            for value in self._merge_kept_close
        ]
        if rows:
            yield SelectionList(
                *dynamic_selection_rows(
                    rows,
                    selected_values,
                    select_all_when_empty=False,
                ),
                id="merge-branches-to-close",
            )
        yield Label("Merge home path (wiring)", classes="form-label nav-section", id="merge-carry-forward-label")
        carry_options = self._merge_carry_forward_options(options, selected_values)
        carry_value = self._selected_merge_carry_value(carry_options, config)
        yield Select(
            carry_options or [("Select branches to close first", "")],
            value=carry_value if carry_options else "",
            id="merge-carry-forward-selector",
            disabled=not bool(carry_options),
        )
        yield Static("Merge collects delivered slot values. The shallowest arriving path continues; ties use first arrival. This selector controls wiring only.", classes="form-description")
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
        return [(f"Home branch | Input: {port}", f"home:{port}") for port in sorted(_reserved_merge_input_ports(self.workflow_map, self.node_id))] + [
            (
                f"{option['branch_label']} | Output: {option['output_name']}",
                self._merge_option_value(option),
            )
            for option in options
            if self._merge_option_value(option) in selected_values
        ] + (
            [(f"Kept, no longer matches a branch: {kept}", kept)]
            if (kept := getattr(self, "_merge_kept_carry", ""))
            else []
        )

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
        kept_carry = getattr(self, "_merge_kept_carry", "")
        if kept_carry and str(selected_value) == kept_carry:
            detail.update(f"Editor home path: kept unchanged ({kept_carry}); it no longer matches a branch.")
            detail.display = True
            return
        if str(selected_value).startswith("home:"):
            detail.update("Editor home path: home branch")
            detail.display = True
            selector_query.first().display = True
            for label in self.query("#merge-carry-forward-label"):
                label.display = True
            return
        if selector_query:
            selector_query.first().display = option is not None
        for label in self.query("#merge-carry-forward-label"):
            label.display = option is not None
        if option is not None:
            detail.update(
                "\n".join(
                    [
                        f"Branches selected: {len(selected_closures)}",
                        f"Editor home path: {option['branch_label']}",
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
        detail.display = False

    def _membank_config_values(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        if self.query("#membank-reads"):
            values["membank_inputs"] = []
        if self.query("#membank-writes"):
            values["membank_outputs"] = []

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

        reads_enabled = bool(self.query("#membank-reads") and self.query_one("#membank-reads", Checkbox).value)
        if reads_enabled:
            selection_lists = self.query("#membank-inputs")
            if selection_lists:
                values["membank_inputs"] = list(selection_lists.first().selected)
        return values

    def _transient_config_values(self) -> Dict[str, Any]:
        metadata = self._metadata_for_type(self.node_data.get("type", ""))
        ports = self._own_output_ports(metadata)
        # Keep overrides for ports this config hides (a lowered Branch count),
        # so raising the count again brings their names back.
        outputs = [
            dict(entry)
            for port, entry in normalize_transient_outputs(
                self.node_data.get("config") or {}
            ).items()
            if port not in ports and (entry.get("name") or entry.get("description"))
        ]
        # One walk of the screen, not two id searches per port (UX3).
        fields = {
            widget.id: widget
            for widget in self.query("*")
            if widget.id and widget.id.startswith("transient-output-")
        }
        for port in ports:
            port = str(port)
            name_widget = fields.get(f"transient-output-name-{port}")
            desc_widget = fields.get(f"transient-output-desc-{port}")
            if name_widget is None and desc_widget is None:
                continue
            name = self._widget_text_value(name_widget) if name_widget is not None else ""
            description = (
                self._widget_text_value(desc_widget) if desc_widget is not None else ""
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
        composed = len(self._branch_rows)
        for index, port in enumerate(path_ports(max(branch_count, composed))):
            widgets = self._branch_rows.get(port)
            if widgets is not None:
                label = self._widget_text_value(widgets[1])
            else:
                label = str(existing_config.get(f"{port}_label") or f"Branch {index + 1}")
            values[f"{port}_label"] = label or f"Branch {index + 1}"
            if index < branch_count and widgets is not None:
                source = str(widgets[2].value or "dead_drop:input")
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
        rows = self.query_one("#branch-payload-rows")
        config = self.node_data.get("config") or {}
        payload_sources = config.get("branch_payload_sources") or {}
        if not isinstance(payload_sources, dict):
            payload_sources = {}
        composed = len(self._branch_rows)
        # A raised count gets its rows on demand (up to MAX_BRANCH_COUNT),
        # mounted in one batch.
        new_rows = [
            self._branch_payload_row(index, source_options, payload_sources, config)
            for index in range(composed, branch_count)
        ]
        if new_rows:
            rows.mount(*new_rows)
        for index, port in enumerate(path_ports(max(branch_count, composed))):
            widgets = self._branch_rows.get(port)
            if widgets is None:
                continue
            row, _label_input, selector = widgets
            row.display = index < branch_count
            current_value = str(selector.value or "dead_drop:input")
            self._set_select_options_preserving_value(selector, source_options, current_value)
            if current_value not in valid_values:
                selector.value = "dead_drop:input"

    def _sync_membank_input_controls(self) -> None:
        reads_query = self.query("#membank-reads")
        if not reads_query:
            return
        reads_enabled = bool(reads_query.first().value)
        selection_query = self.query("#membank-inputs")
        if selection_query:
            selection_query.first().disabled = not reads_enabled
            selection_query.first().display = reads_enabled
        for widget in self.query("#membank-inputs-empty"):
            widget.display = reads_enabled

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
        writes_checkbox.display = not pass_through_selected
        count_input = count_query.first()
        count_input.disabled = not writes_enabled
        count_input.display = writes_enabled
        for widget in self.query("#membank-output-count-label, #membank-output-rows"):
            widget.display = writes_enabled
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
                # Keep edited rows mounted while hidden so re-enabling restores them.
                return
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
        selection_query = self.query("#merge-branches-to-close")
        kept_close = list(getattr(self, "_merge_kept_close", []))
        if selection_query:
            branches_to_close = sorted(self._selected_merge_close_values_from_widget())
        else:
            branches_to_close = sorted(kept_close)
        carry_value = ""
        selector_query = self.query("#merge-carry-forward-selector")
        kept_carry = getattr(self, "_merge_kept_carry", "")
        if selector_query:
            carry_value = str(selector_query.first().value or "")
        elif kept_carry:
            carry_value = kept_carry
        if kept_carry and carry_value == kept_carry:
            # Backstop: an unmatched carry-forward stays exactly as saved.
            kept = dict(getattr(self, "_merge_kept_carry_config", {}))
            return {
                "branches_to_close": branches_to_close,
                "carry_forward_branch_id": kept.get("carry_forward_branch_id", ""),
                "selected_branch_id": kept.get("selected_branch_id", ""),
            }
        if carry_value.startswith("home:"):
            port = carry_value.removeprefix("home:")
            if port in _reserved_merge_input_ports(self.workflow_map, self.node_id):
                return {"branches_to_close": branches_to_close, "carry_forward_branch_id": carry_value, "selected_branch_id": ""}
        for option in options:
            if self._merge_option_value(option) == carry_value:
                return {
                    "branches_to_close": branches_to_close,
                    "carry_forward_branch_id": carry_value,
                    "selected_branch_id": carry_value,
                }
        return {
            "branches_to_close": branches_to_close,
            "carry_forward_branch_id": "",
            "selected_branch_id": "",
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
            branch_label, _branch_id = upstream_branch_info(
                self.workflow_map,
                self.node_id,
                target_id,
                target_port,
            )
            return "\n".join(
                [
                    "Merge Beacon has no editable fields.",
                    f"Merges To Branch: {branch_label}",
                    f"Merge Node: {self._node_label(target_id, target_node)}",
                ]
            )
        return "Merge Beacon has no editable fields.\nStatus: open until connected to a Merge node."

    def _node_label(self, node_id: str, node: Dict[str, Any]) -> str:
        return str(node.get("alias") or node.get("type") or node_id)

    def _node_display_name(self, node_id: str, node: Dict[str, Any]) -> str:
        return str(node.get("alias") or node.get("type") or node_id)

    def _refresh_node_data(self) -> None:
        self.node_data = self.workflow_map.get_node_data(self.node_id) or self.node_data

"""Error details modal."""

from __future__ import annotations

from typing import Any, Dict

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from frontend.keymap import ERROR_DETAILS, bindings_for
from frontend.node_location import node_heading
from frontend.widgets.command_screen_mixin import CommandScreenMixin

#: Validation Details label per validator issue code
#: (``backend/validation_codes.ISSUE_CODES``). The one place to change how a
#: kind of issue is named; an unknown code falls back to "Validation issue".
VALIDATION_LABELS: Dict[str, str] = {
    "no_start_node": "No Start node",
    "multiple_start_nodes": "Several Start nodes",
    "unknown_node_type": "Unknown node type",
    "deleted_node_stub": "Deleted node stub",
    "missing_node": "Missing node",
    "unreachable": "Unreachable node",
    "merge_outside_split": "Merge outside split",
    "merge_required_path_escape": "Merge path escapes",
    "merge_required_child_omitted": "Merge path may not launch",
    "impossible_wait": "Impossible wait",
    "wait_target_missing": "Wait target missing",
    "wait_target_needs_review": "Wait target needs review",
    "flow_loop": "Loop needs review",
    "flow_needs_review": "Flow needs review",
    "repeated_join_unsupported": "Repeated join needs review",
    "merge_beacon_unconnected": "Unmerged branch",
    "undeclared_port": "Invalid port",
    "hidden_output_connection": "Unused output",
    "disabled_output_connection": "Disabled output",
    "vault_write_unsupported": "Unsupported Vault write",
    "template_vault_key_unwritten": "Unwritten template key",
    "hidden_input_connection": "Unused input",
    "duplicate_input_source": "Duplicate source",
    "ignored_fan_out": "Ignored connection",
    "type_mismatch": "Type mismatch",
    "contract_row_invalid": "Contract row",
    "input_required_no_value": "Required input",
    "return_end_not_callable": "Return End unused",
    "multiple_return_ends": "Several Return Ends",
    "return_end_unmerged": "Return End inside branch",
    "subworkflow_not_found": "Subworkflow missing",
    "subworkflow_not_callable": "Not a subworkflow",
    "subworkflow_recursion": "Calls itself",
    "subworkflow_input_unknown": "Unknown input",
    "subworkflow_input_invalid": "Input type mismatch",
    "subworkflow_result_unknown": "Unknown result",
    "subworkflow_input_missing": "Input not filled",
    "subworkflow_stash_missing": "No such Stash entry",
    "subworkflow_input_unmapped": "Input uses default",
    "undeclared_vault_key": "Missing Vault key",
    "unwritten_vault_key": "Unwritten Vault key",
    "vault_source_key_missing": "Vault key not set",
    "vault_output_key_missing": "Vault key not set",
    "vault_type_mismatch": "Vault type mismatch",
    "ai_session_tag_missing": "Vault type mismatch",
    "vault_race": "Vault timing",
    "chat_session_key_missing": "Session key not set",
    "saved_name_missing": "Saved as not set",
    "missing_file_path": "File path not set",
    "invalid_file_path": "Invalid file path",
    "invalid_number": "Invalid number",
    "invalid_rows": "Invalid answer rows",
    "vault_only_connection": "Vault-only output",
    "file_not_found": "File not found",
    "secret_not_configured": "Secret not set",
    "secret_missing": "Secret missing",
    "window_placement_unsupported": "Not supported here",
    "window_close_unsupported": "Not supported here",
    "mux_route_problem": "Error Mux",
    "mux_no_codes": "Error Mux",
    "mux_no_input": "Error Mux",
    "mux_wrong_source_port": "Error Mux",
    "mux_unknown_code": "Error Mux",
    "mux_route_unconnected": "Error Mux",
    "mux_unmatched_unconnected": "Error Mux",
}


class ErrorDetailsScreen(CommandScreenMixin, ModalScreen):
    """Show structured errors and recovery choices."""

    KEYMAP = ERROR_DETAILS
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, payload: Dict[str, Any]) -> None:
        super().__init__()
        self.payload = payload

    def compose(self) -> ComposeResult:
        if "validation" in self.payload:
            yield from self._compose_validation()
            return

        options = self.payload.get("options", [])
        with VerticalScroll(id="modal-card"):
            yield Label("Error Details", classes="modal-title")
            yield Static(self._format_error(), id="error-details", markup=False)
            yield Label("W/S or arrows: move · E/Enter: select · Esc: close", classes="modal-help")
            for option in options:
                yield Button(option.replace("_", " ").title(), id=f"recovery-{option}", variant="default")
            yield Button("Close", id="close-error", variant="default")

    def on_mount(self) -> None:
        # Long tracebacks need layout before the first button can be revealed.
        self.call_after_refresh(self._focus_first)

    def _scroll_container(self) -> VerticalScroll:
        return self.query_one("#modal-card", VerticalScroll)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id or "")
        if button_id.startswith("recovery-"):
            self.dismiss(
                {
                    "branch_id": self.payload.get("branch_id"),
                    "action": button_id.removeprefix("recovery-"),
                }
            )
        elif button_id.startswith("jump-validation-"):
            node_id = self.payload.get("_jump_targets", {}).get(button_id)
            self.dismiss({"action": "jump", "node_id": node_id})
        elif button_id == "close-error":
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)

    def _heading(self, node_id: str) -> str:
        """Plain first line: name, type, depth and branch (owner, 2026-10-14)."""
        workflow_map = getattr(self.app, "workflow_map", None)
        if not node_id or workflow_map is None:
            return f"Node {node_id or '-'}"
        return node_heading(workflow_map, getattr(self.app, "factory", None), node_id)

    def _format_error(self) -> str:
        error = self.payload.get("error", {})
        node_id = str(self.payload.get("node_id") or error.get("node_id") or "")
        return "\n".join(
            [
                self._heading(node_id),
                f"Node ID: {node_id or '-'}",
                f"Run branch: {self.payload.get('branch_id', '-')}",
                f"Category: {self.payload.get('category', error.get('category', '-'))}",
                f"Message: {self.payload.get('error_message', error.get('message', '-'))}",
                "",
                "Traceback:",
                str(self.payload.get("traceback", error.get("traceback", "-"))),
            ]
        )

    def _compose_validation(self) -> ComposeResult:
        validation = self.payload.get("validation", {})
        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])
        self.payload["_jump_targets"] = {}
        with VerticalScroll(id="modal-card"):
            yield Label("Validation Details", classes="modal-title")
            if not errors and not warnings:
                yield Static("Workflow is valid.", classes="validation-card")
            for label, items in (("Error", errors), ("Warning", warnings)):
                for index, item in enumerate(items):
                    node_id = item.get("node_id") or ""
                    message = item.get("message") or "-"
                    error_type = self._validation_type(item)
                    yield Static(
                        "\n".join(
                            [
                                f"{label}: {self._heading(node_id) if node_id else 'Workflow'}",
                                *([f"Node ID: {node_id}"] if node_id else []),
                                f"{error_type}: {message}",
                            ]
                        ),
                        classes="validation-card",
                        markup=False,
                    )
                    if node_id:
                        button_id = f"jump-validation-{label.lower()}-{index}"
                        self.payload["_jump_targets"][button_id] = node_id
                        yield Button("Jump to node", id=button_id, variant="default")
            yield Button("Close", id="close-error", variant="default")

    def _validation_type(self, item: Dict[str, Any]) -> str:
        """Label for one validator issue, from its ``code``."""
        return VALIDATION_LABELS.get(str(item.get("code") or ""), "Validation issue")

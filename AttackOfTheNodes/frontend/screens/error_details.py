"""Error details modal."""

from __future__ import annotations

from typing import Any, Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ErrorDetailsScreen(ModalScreen):
    """Show structured errors and recovery choices."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        Binding("ctrl+q", "close", "Close", priority=True),
    ]

    def __init__(self, payload: Dict[str, Any]) -> None:
        super().__init__()
        self.payload = payload

    def compose(self) -> ComposeResult:
        if "validation" in self.payload:
            yield from self._compose_validation()
            return

        options = self.payload.get("options", [])
        with Vertical(id="modal-card"):
            yield Label("Error Details", classes="modal-title")
            yield Static(self._format_error(), id="error-details")
            with Horizontal(classes="button-row"):
                for option in options:
                    yield Button(option, id=f"recovery-{option}", variant="default")
                yield Button("Close", id="close-error", variant="default")

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

    def _format_error(self) -> str:
        error = self.payload.get("error", {})
        return "\n".join(
            [
                f"Branch: {self.payload.get('branch_id', '-')}",
                f"Node: {self.payload.get('node_id', '-')}",
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
        with Vertical(id="modal-card"):
            yield Label("Validation Details", classes="modal-title")
            if not errors and not warnings:
                yield Static("Workflow is valid.", classes="validation-card")
            for label, items in (("Error", errors), ("Warning", warnings)):
                for index, item in enumerate(items):
                    node_id = item.get("node_id") or ""
                    message = item.get("message") or "-"
                    error_type = self._validation_type(message)
                    yield Static(
                        "\n".join(
                            [
                                f"{label}: {error_type}",
                                f"Node: {node_id or '-'}",
                                f"Description: {message}",
                            ]
                        ),
                        classes="validation-card",
                    )
                    if node_id:
                        button_id = f"jump-validation-{label.lower()}-{index}"
                        self.payload["_jump_targets"][button_id] = node_id
                        yield Button("Jump to node", id=button_id, variant="default")
            with Horizontal(classes="button-row"):
                yield Button("Close", id="close-error", variant="default")

    def _validation_type(self, message: str) -> str:
        text = message.lower()
        if "deleted node stub" in text:
            return "Deleted node stub"
        if "not reachable" in text:
            return "Unreachable node"
        if "unknown node type" in text:
            return "Unknown node type"
        if "missing node" in text:
            return "Missing connection target"
        if "undeclared port" in text:
            return "Invalid port"
        if "start node" in text:
            return "Start node"
        return "Validation issue"

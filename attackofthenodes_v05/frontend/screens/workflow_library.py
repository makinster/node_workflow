"""Workflow library modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from backend.persistence import list_workflows
from frontend.widgets.command_navigation import (
    activate_command_widget,
    blocks_command_action,
    focus_command_widget,
)
from frontend.widgets.command_input import CommandInput
from frontend.widgets.list_navigation import focus_list, move_list_highlight


class WorkflowLibraryScreen(ModalScreen):
    """Open, duplicate, export, and delete saved workflows."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("q", "cancel", "Cancel"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("w", "cursor_up", "Up", priority=True),
        Binding("s", "cursor_down", "Down", priority=True),
        ("enter", "load_selected", "Load"),
        ("n", "new_workflow", "New"),
        ("d", "duplicate_selected", "Duplicate"),
        ("e", "export_selected", "Export"),
        ("i", "import_workflow", "Import"),
        ("x", "delete_selected", "Delete"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.workflows: list[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Workflow Library", classes="modal-title")
            yield ListView(id="workflow-list")
            yield Static(
                "ENTER load  N new  D duplicate  E export  I import  X delete  ESC close",
                classes="modal-help",
            )
            with Horizontal(classes="button-row"):
                yield Button("Load", id="load-workflow", variant="primary")
                yield Button("New", id="new-workflow", variant="default")
                yield Button("Duplicate", id="duplicate-workflow", variant="default")
                yield Button("Export", id="export-workflow", variant="default")
                yield Button("Import", id="import-workflow", variant="default")
                yield Button("Delete", id="delete-workflow", variant="error")
                yield Button("Cancel", id="cancel-workflow-library", variant="default")

    def on_mount(self) -> None:
        self._refresh_workflows()
        self._focus_workflow_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_action("load", event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "load-workflow":
            self.action_load_selected()
        elif button_id == "new-workflow":
            self.action_new_workflow()
        elif button_id == "duplicate-workflow":
            self.action_duplicate_selected()
        elif button_id == "export-workflow":
            self.action_export_selected()
        elif button_id == "import-workflow":
            self.action_import_workflow()
        elif button_id == "delete-workflow":
            self.action_delete_selected()
        elif button_id == "cancel-workflow-library":
            self.action_cancel()

    def action_load_selected(self) -> None:
        index = self.query_one("#workflow-list", ListView).index
        self._dismiss_action("load", index)

    def action_new_workflow(self) -> None:
        self.dismiss({"action": "new"})

    def action_duplicate_selected(self) -> None:
        index = self.query_one("#workflow-list", ListView).index
        self._dismiss_action("duplicate", index)

    def action_export_selected(self) -> None:
        index = self.query_one("#workflow-list", ListView).index
        self._dismiss_action("export", index)

    def action_import_workflow(self) -> None:
        self.dismiss({"action": "import"})

    def action_delete_selected(self) -> None:
        index = self.query_one("#workflow-list", ListView).index
        self._dismiss_action("delete", index)

    def action_cursor_up(self) -> None:
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._move_selection(1)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _refresh_workflows(self) -> None:
        self.workflows = list_workflows()
        list_view = self.query_one("#workflow-list", ListView)
        list_view.clear()
        for workflow in self.workflows:
            list_view.append(
                ListItem(Static(f"{workflow['name']}  ({workflow['id']})"))
            )
        if not self.workflows:
            list_view.append(ListItem(Static("No saved workflows")))
        else:
            list_view.index = 0

    def _focus_workflow_list(self) -> None:
        list_view = self.query_one("#workflow-list", ListView)
        focus_list(self.app, list_view, len(self.workflows))

    def _move_selection(self, delta: int) -> None:
        list_view = self.query_one("#workflow-list", ListView)
        move_list_highlight(self.app, list_view, len(self.workflows), delta)

    def _dismiss_action(self, action: str, index: Optional[int]) -> None:
        if index is None or index < 0 or index >= len(self.workflows):
            if action == "new":
                self.dismiss({"action": "new"})
            return
        workflow = self.workflows[index]
        self.dismiss(
            {
                "action": action,
                "workflow_id": workflow["id"],
                "workflow_name": workflow["name"],
            }
        )


class PathPromptScreen(ModalScreen):
    """Ask for an import/export filesystem path."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "submit", "Submit"),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
        Binding("e", "activate_focused", "Activate", priority=True),
        Binding("enter", "activate_focused", "Activate", priority=True),
    ]

    def __init__(self, title: str, default_path: str = "") -> None:
        super().__init__()
        self.title_text = title
        self.default_path = default_path

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="path-prompt-modal"):
            yield Label(self.title_text, classes="modal-title")
            yield CommandInput(
                value=self.default_path,
                id="path-input",
                auto_edit_on_focus=True,
            )
            yield Static("Type path  Ctrl+Enter confirm  Esc leaves edit/cancels", classes="modal-help")
            with Horizontal(classes="button-row"):
                yield Button("Confirm", id="confirm-path", variant="primary")
                yield Button("Cancel", id="cancel-path", variant="default")

    def on_mount(self) -> None:
        focus_command_widget(self, self.query_one("#path-input", CommandInput))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if blocks_command_action(self.app.focused, action):
            return False
        return True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-path":
            self.action_submit()
        elif event.button.id == "cancel-path":
            self.action_cancel()

    def action_submit(self) -> None:
        path = self.query_one("#path-input", Input).value.strip()
        self.dismiss(path or None)

    def action_activate_focused(self) -> None:
        activate_command_widget(self.app.focused)

    def action_cancel(self) -> None:
        self.dismiss(None)

"""Workflow library modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from backend.persistence import list_workflows
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.list_navigation import focus_list, move_list_highlight
from frontend.widgets.status_bar import StatusBar


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

    def __init__(self, current_workflow_id: str | None = None) -> None:
        super().__init__()
        self.workflows: list[Dict[str, Any]] = []
        self.current_workflow_id = current_workflow_id

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card"):
            yield Label("Workflow Library", classes="modal-title")
            yield ListView(id="workflow-list")
            yield Static(
                "Enter load | N new | D duplicate | X delete\nE export | I import | Esc cancel",
                classes="modal-help",
            )
            yield Button("Cancel", id="cancel-workflow-library", variant="default")

    def on_mount(self) -> None:
        self._refresh_workflows()
        self._focus_workflow_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_action("load", event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "cancel-workflow-library":
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
        display_names = self._display_names(self.workflows)
        for workflow, display_name in zip(self.workflows, display_names):
            loaded = (
                " <-- Loaded Workflow"
                if workflow.get("id") == self.current_workflow_id
                else ""
            )
            text = f"{display_name}{loaded}"
            row = Static(text)
            setattr(row, "display_text", text)
            list_view.append(ListItem(row))
        if not self.workflows:
            list_view.append(ListItem(Static("No saved workflows")))
        else:
            list_view.index = 0

    def _focus_workflow_list(self) -> None:
        list_view = self.query_one("#workflow-list", ListView)
        focus_list(self.app, list_view, len(self.workflows))

    def _move_selection(self, delta: int) -> None:
        list_view = self.query_one("#workflow-list", ListView)
        cancel = self.query_one("#cancel-workflow-library", Button)
        if self.app.focused is cancel and delta < 0:
            if self.workflows:
                list_view.index = len(self.workflows) - 1
                focus_list(self.app, list_view, len(self.workflows))
            return
        if self.app.focused is list_view:
            current = list_view.index if list_view.index is not None else 0
            if delta > 0 and current >= len(self.workflows) - 1:
                self.app.set_focus(cancel)
                return
        if not self.workflows and delta > 0:
            self.app.set_focus(cancel)
            return
        move_list_highlight(self.app, list_view, len(self.workflows), delta)

    def _display_names(self, workflows: list[Dict[str, Any]]) -> list[str]:
        totals: Dict[str, int] = {}
        seen: Dict[str, int] = {}
        for workflow in workflows:
            name = str(workflow.get("name") or "Untitled Workflow")
            totals[name] = totals.get(name, 0) + 1
        names = []
        for workflow in workflows:
            name = str(workflow.get("name") or "Untitled Workflow")
            seen[name] = seen.get(name, 0) + 1
            names.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
        return names

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


class PathPromptScreen(CommandScreenMixin, ModalScreen):
    """Ask for an import/export filesystem path."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "submit", "Submit"),
        Binding("tab", "tab_out", "Next", priority=True),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
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
            yield Static("E edit path | Tab next | Ctrl+Enter confirm | Esc cancel", classes="modal-help")
            with Vertical(classes="button-row"):
                yield Button("Confirm", id="confirm-path", variant="primary")
                yield Button("Cancel", id="cancel-path", variant="default")
            yield StatusBar("E edit path | Tab next | Ctrl+Enter confirm | Esc cancel")

    def on_mount(self) -> None:
        self._focus_first()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-path":
            self.action_submit()
        elif event.button.id == "cancel-path":
            self.action_cancel()

    def action_submit(self) -> None:
        path = self.query_one("#path-input", Input).value.strip()
        self.dismiss(path or None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_tab_out(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            focused.end_edit()
        self._move_cursor(1)

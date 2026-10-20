"""Workflow library modal."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static, TabbedContent, TabPane

from backend.persistence import list_workflows
from frontend import file_io, notifications
from frontend.keymap import NAME_INPUT, WORKFLOW_LIBRARY, NAME_PROMPT, PATH_PROMPT, bindings_for
from frontend.keymap_runtime import KeymapScreenMixin

from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.list_navigation import focus_list, move_list_highlight
from frontend.widgets.status_bar import StatusBar


STANDARD_TAB = "library-tab-workflows"
SUB_TAB = "library-tab-subworkflows"
_LISTS = {STANDARD_TAB: "workflow-list", SUB_TAB: "subworkflow-list"}
_HELP = {
    STANDARD_TAB: "1-2 tabs | e open | n new | c copy to subworkflows | x delete | ? more",
    SUB_TAB: "1-2 tabs | e open | n new | x delete | ? more",
}


class WorkflowLibraryScreen(KeymapScreenMixin, ModalScreen):
    """Open, create, copy, rename, duplicate, export and delete saved
    workflows. Tab 1 lists workflows, tab 2 subworkflows (owner, 2026-10-18)."""

    KEYMAP = WORKFLOW_LIBRARY
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, current_workflow_id: str | None = None, initial_tab: str | None = None) -> None:
        super().__init__()
        self.current_workflow_id = current_workflow_id
        self._initial_tab = initial_tab
        self._by_tab: Dict[str, list[Dict[str, Any]]] = {STANDARD_TAB: [], SUB_TAB: []}

    @property
    def workflows(self) -> list[Dict[str, Any]]:
        """The workflows on the active tab."""
        return self._by_tab[self._active_tab()]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="library-modal"):
            yield Label("Workflow Library", classes="modal-title")
            with TabbedContent(id="library-tabs", classes="node-config-tabs"):
                with TabPane("1 Workflows", id=STANDARD_TAB):
                    yield ListView(id="workflow-list")
                with TabPane("2 Subworkflows", id=SUB_TAB):
                    yield Static("Can run inside other workflows.", classes="form-description")
                    yield ListView(id="subworkflow-list")
            with Horizontal(classes="button-row"):
                yield Button("Open", id="load-workflow-library", variant="primary")
                yield Button("Close", id="cancel-workflow-library", variant="default")
            yield StatusBar(_HELP[STANDARD_TAB])

    def on_mount(self) -> None:
        self._refresh_workflows()
        tab = self._initial_tab
        if tab is None:
            current = next((w for w in list_workflows() if w.get("id") == self.current_workflow_id), None)
            tab = SUB_TAB if current and current.get("callable") else STANDARD_TAB
        self.action_show_tab("sub" if tab == SUB_TAB else "workflows")

    def _active_tab(self) -> str:
        try:
            active = self.query_one("#library-tabs", TabbedContent).active
        except Exception:
            active = ""
        return active if active in _LISTS else STANDARD_TAB

    def _list(self) -> ListView:
        return self.query_one(f"#{_LISTS[self._active_tab()]}", ListView)

    def action_show_tab(self, tab: str) -> None:
        tab_id = SUB_TAB if tab == "sub" else STANDARD_TAB
        self.query_one("#library-tabs", TabbedContent).active = tab_id
        self.query_one(StatusBar).set_bindings_text(_HELP[tab_id])
        self._focus_workflow_list()

    def on_tabbed_content_tab_activated(self, _event: TabbedContent.TabActivated) -> None:
        self.query_one(StatusBar).set_bindings_text(_HELP[self._active_tab()])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._dismiss_action("load", event.list_view.index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "cancel-workflow-library":
            self.action_cancel()
        elif button_id == "load-workflow-library":
            self.action_load_selected()

    def action_load_selected(self) -> None:
        self._dismiss_action("load", self._list().index)

    def action_choose(self) -> None:
        if self.app.focused is self.query_one("#cancel-workflow-library", Button):
            self.action_cancel()
            return
        self.action_load_selected()

    def action_new_workflow(self) -> None:
        if self._active_tab() == SUB_TAB:
            self.dismiss({"action": "new", "callable": True})
        else:
            self.dismiss({"action": "new"})

    def action_copy_to_subworkflows(self) -> None:
        if self._active_tab() == STANDARD_TAB:
            self._dismiss_action("copy_to_subworkflows", self._list().index)

    def action_rename_selected(self) -> None:
        self._dismiss_action("rename", self._list().index)

    def action_duplicate_selected(self) -> None:
        self._dismiss_action("duplicate", self._list().index)

    def action_export_selected(self) -> None:
        self._dismiss_action("export", self._list().index)

    def action_import_workflow(self) -> None:
        self.dismiss({"action": "import"})

    def action_delete_selected(self) -> None:
        self._dismiss_action("delete", self._list().index)

    def action_cursor_up(self) -> None:
        self._move_selection(-1)

    def action_cursor_down(self) -> None:
        self._move_selection(1)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _refresh_workflows(self) -> None:
        saved = list_workflows()
        self._by_tab = {
            STANDARD_TAB: [w for w in saved if not w.get("callable")],
            SUB_TAB: [w for w in saved if w.get("callable")],
        }
        for tab_id, list_id in _LISTS.items():
            workflows = self._by_tab[tab_id]
            list_view = self.query_one(f"#{list_id}", ListView)
            list_view.clear()
            for workflow, display_name in zip(workflows, self._display_names(workflows)):
                loaded = (
                    " <-- Loaded Workflow"
                    if workflow.get("id") == self.current_workflow_id
                    else ""
                )
                text = f"{display_name}{loaded}"
                row = Static(text, markup=False)
                setattr(row, "display_text", text)
                list_view.append(ListItem(row))
            if not workflows:
                empty = "No saved subworkflows" if tab_id == SUB_TAB else "No saved workflows"
                list_view.append(ListItem(Static(empty)))
            else:
                list_view.index = 0

    def _focus_workflow_list(self) -> None:
        focus_list(self.app, self._list(), len(self.workflows))

    def _move_selection(self, delta: int) -> None:
        list_view = self._list()
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
        seen: Dict[str, int] = {}
        names = []
        for workflow in workflows:
            name = str(workflow.get("name") or "Untitled Workflow")
            seen[name] = seen.get(name, 0) + 1
            names.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
        return names

    def _dismiss_action(self, action: str, index: Optional[int]) -> None:
        if index is None or index < 0 or index >= len(self.workflows):
            if action == "new":
                self.action_new_workflow()
            return
        workflow = self.workflows[index]
        result = {
            "action": action,
            "workflow_id": workflow["id"],
            "workflow_name": workflow["name"],
        }
        if workflow.get("callable"):
            result["callable"] = True
        self.dismiss(result)


class _NameInput(CommandInput):
    """A one-field prompt: Enter confirms, in edit mode or not.

    Plain CommandInputs end the edit on Enter and need Ctrl+Enter to submit,
    which many terminals (and tmux) don't send distinctly.
    """

    KEYMAP = NAME_INPUT
    BINDINGS = bindings_for(KEYMAP)

    def action_submit_name(self) -> None:
        if self.editing:
            self.end_edit()
        self.post_message(self.Submitted(self, self.value))


class NamePromptScreen(CommandScreenMixin, ModalScreen):
    """Ask for a workflow name; ``check`` returns why a name can't be used.

    A rejected name keeps the prompt open with the reason under the field.
    Dismisses with the trimmed name, or None on Esc.
    """

    KEYMAP = NAME_PROMPT
    BINDINGS = bindings_for(KEYMAP)

    def __init__(
        self,
        title: str,
        default_name: str,
        check: Callable[[str], Optional[str]],
    ) -> None:
        super().__init__()
        self.title_text = title
        self.default_name = default_name
        self.check = check

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="name-prompt-modal"):
            yield Label(self.title_text, classes="modal-title")
            yield _NameInput(value=self.default_name, id="name-input")
            yield Static("", id="name-error", classes="field-error")
            with Horizontal(classes="button-row"):
                yield Button("Confirm", id="confirm-name", variant="primary")
                yield Button("Cancel", id="cancel-name", variant="default")
            yield StatusBar("Type a name | Enter or Ctrl+S confirm | Esc cancel")

    def on_mount(self) -> None:
        self.query_one("#name-error", Static).display = False
        self._focus_first()
        # Typing starts at once; W/S are letters of the name here.
        self.query_one("#name-input", CommandInput).begin_edit()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self.action_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-name":
            self.action_submit()
        elif event.button.id == "cancel-name":
            self.action_cancel()

    def action_submit(self) -> None:
        name = self.query_one("#name-input", Input).value
        problem = self.check(name)
        error = self.query_one("#name-error", Static)
        if problem:
            error.update(problem)
            error.display = True
            name_input = self.query_one("#name-input", CommandInput)
            if not name_input.editing:
                name_input.begin_edit()
            return
        self.dismiss(name.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


class PathPromptScreen(CommandScreenMixin, ModalScreen):
    """Ask for an import/export filesystem path."""

    KEYMAP = PATH_PROMPT
    BINDINGS = bindings_for(KEYMAP)

    def __init__(
        self,
        title: str,
        default_path: str = "",
        *,
        picker_mode: str | None = None,
        default_name: str = "",
    ) -> None:
        super().__init__()
        self.title_text = title
        self.default_path = default_path
        self.picker_mode = picker_mode
        self.default_name = default_name or Path(default_path).name

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-card", classes="path-prompt-modal"):
            yield Label(self.title_text, classes="modal-title")
            yield CommandInput(
                value=self.default_path,
                id="path-input",
                auto_edit_on_focus=True,
            )
            help_text = "B browse | E edit path | Tab next | Ctrl+Enter confirm | Esc cancel"
            with Vertical(classes="button-row"):
                if self.picker_mode:
                    yield Button("Browse", id="browse-path", variant="default")
                yield Button("Confirm", id="confirm-path", variant="primary")
                yield Button("Cancel", id="cancel-path", variant="default")
            yield StatusBar(help_text)

    def on_mount(self) -> None:
        self._focus_first()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-path":
            self.action_submit()
        elif event.button.id == "cancel-path":
            self.action_cancel()
        elif event.button.id == "browse-path":
            self.action_browse()

    def action_submit(self) -> None:
        path = self.query_one("#path-input", Input).value.strip()
        self.dismiss(path or None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_browse(self) -> None:
        if not self.picker_mode:
            return
        asyncio.create_task(self._browse_path())

    async def _browse_path(self) -> None:
        try:
            if self.picker_mode == "save":
                path = await asyncio.to_thread(
                    file_io.pick_save_file,
                    self.title_text,
                    self.default_name,
                    file_io.JSON_FILE_TYPES,
                )
            else:
                path = await asyncio.to_thread(
                    file_io.pick_open_file,
                    self.title_text,
                    file_io.JSON_FILE_TYPES,
                )
        except file_io.FilePickerUnavailable:
            notifications.notify_info(self.app, "File picker unavailable; type the path")
            return
        if not path:
            return
        path_input = self.query_one("#path-input", CommandInput)
        if path_input.editing:
            path_input.end_edit()
        path_input.value = path
        self.app.set_focus(self.query_one("#confirm-path", Button))

    def action_tab_out(self) -> None:
        focused = self.app.focused
        if isinstance(focused, CommandInput) and focused.editing:
            focused.end_edit()
        self._move_cursor(1)

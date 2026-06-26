"""Settings modal."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Label,
    ListItem,
    ListView,
    Static,
    TabbedContent,
    TabPane,
)

from backend.configuration_manager import DEFAULT_SETTINGS
from frontend.screens.confirm import ConfirmScreen
from frontend.widgets.command_navigation import (
    command_focus_widgets,
    focus_command_widget,
    is_editing_text,
)
from frontend.widgets.command_input import CommandInput
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.list_navigation import move_list_highlight
from frontend.widgets.status_bar import StatusBar


class SettingsScreen(CommandScreenMixin, ModalScreen):
    """Configuration and secrets management form."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        Binding("1", "settings_tab_general", "General", priority=True),
        Binding("2", "settings_tab_secrets", "Secrets", priority=True),
        Binding("x", "delete_secret", "Delete secret", priority=True),
        Binding("ctrl+q", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, configuration_manager, secrets_manager=None) -> None:
        super().__init__()
        self.configuration_manager = configuration_manager
        self.secrets_manager = secrets_manager

    def compose(self) -> ComposeResult:
        values = self.configuration_manager.get_all()
        with Vertical(id="modal-card", classes="settings-modal"):
            yield Label("Options", classes="modal-title")
            yield Static(
                "W/S move | 1 general | 2 secrets | E edit/select | X delete key | Ctrl+S save",
                classes="modal-help",
            )
            with TabbedContent(
                id="settings-tabs",
                classes="node-config-tabs settings-tabs",
            ):
                with TabPane("1 - General", id="settings-tab-general"):
                    with VerticalScroll(classes="tab-scroll"):
                        for key, default in DEFAULT_SETTINGS.items():
                            yield Label(key, classes="form-label")
                            value = values.get(key, default)
                            if isinstance(default, bool):
                                yield Checkbox(value=bool(value), id=f"setting-{key}")
                            else:
                                yield CommandInput(value=str(value), id=f"setting-{key}")
                with TabPane("2 - Secrets", id="settings-tab-secrets"):
                    with VerticalScroll(classes="tab-scroll"):
                        yield Label("Key", classes="form-label nav-section")
                        yield CommandInput(id="secret-key-input")
                        yield Label("API key", classes="form-label")
                        yield CommandInput(id="secret-value-input", password=True)
                        with Horizontal(classes="button-row secrets-action-row"):
                            yield Button("Add", id="add-secret", variant="primary")
                            yield Button("Clear", id="clear-secret", variant="default")
                        yield Label("Saved Keys", classes="form-label nav-section")
                        yield ListView(id="secret-key-list", classes="saved-key-list")
                        yield Static("", id="secrets-status", classes="form-description")
            with Vertical(classes="button-row"):
                yield Button("Save", id="save-settings", variant="primary")
                yield Button("Cancel", id="cancel-settings", variant="default")
            yield StatusBar("W/S move | 1/2 tabs | Add/Clear | X delete key | Ctrl+S save")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings":
            self.action_save()
        elif event.button.id == "cancel-settings":
            self.action_cancel()
        elif event.button.id == "add-secret":
            self.action_add_secret()
        elif event.button.id == "clear-secret":
            self.action_clear_secret()

    def on_mount(self) -> None:
        self._refresh_secret_key_list()
        self._focus_first()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        active_text = getattr(self, "_active_command_text_widget", None)
        if action in {
            "settings_tab_general",
            "settings_tab_secrets",
            "jump_settings_tab",
            "delete_secret",
        } and (
            is_editing_text(self.app.focused) or is_editing_text(active_text)
        ):
            return False
        return super().check_action(action, parameters)

    def on_key(self, event: events.Key) -> None:
        action = "settings_tab_general" if event.key == "1" else "settings_tab_secrets"
        if event.key in {"1", "2"} and self.check_action(action, ()) is not False:
            self.action_jump_settings_tab(int(event.key))
            event.stop()
            event.prevent_default()
            return
        super().on_key(event)

    def _nav_widgets(self) -> list[Any]:
        inactive_pane_ids = {
            pane.id
            for tabs in self.query(TabbedContent)
            for pane in tabs.query(TabPane)
            if pane.id and pane.id != tabs.active
        }
        widgets = command_focus_widgets(
            self,
            (CommandInput, Checkbox, ListView, Button),
        )
        return [
            widget
            for widget in widgets
            if not self._in_inactive_tab(widget, inactive_pane_ids)
            and not getattr(widget, "disabled", False)
            and getattr(widget, "display", True)
        ]

    def _scroll_container(self):
        try:
            tabs = self.query_one("#settings-tabs", TabbedContent)
            if tabs.active:
                pane = self.query_one(f"#{tabs.active}", TabPane)
                scrolls = list(pane.query(".tab-scroll"))
                if scrolls:
                    return scrolls[0]
        except Exception:
            return None
        return None

    def _in_inactive_tab(self, widget, inactive_pane_ids: set[str]) -> bool:
        node = widget.parent
        while node is not None and node is not self:
            if isinstance(node, TabPane) and node.id in inactive_pane_ids:
                return True
            node = node.parent
        return False

    def action_settings_tab_general(self) -> None:
        self.action_jump_settings_tab(1)

    def action_settings_tab_secrets(self) -> None:
        self.action_jump_settings_tab(2)

    def action_jump_settings_tab(self, tab_number: int) -> None:
        tabbed_query = self.query("#settings-tabs")
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
            lambda tab_id=target_tab_id: self._focus_first_settings_tab_widget(tab_id)
        )
        self.set_timer(
            0.01,
            lambda tab_id=target_tab_id: self._focus_first_settings_tab_widget(tab_id),
        )

    def _focus_first_settings_tab_widget(self, tab_id: str) -> None:
        try:
            pane = self.query_one(f"#{tab_id}", TabPane)
        except Exception:
            self._focus_first()
            return
        for widget in self._nav_widgets():
            if self._is_descendant_of(widget, pane):
                focus_command_widget(self, widget, self._scroll_container())
                return
        self._focus_first()

    def _is_descendant_of(self, widget: Any, ancestor: Any) -> bool:
        node = widget
        while node is not None:
            if node is ancestor:
                return True
            node = getattr(node, "parent", None)
        return False

    def action_cursor_up(self) -> None:
        if self._move_secret_key_highlight(-1):
            return
        super().action_cursor_up()

    def action_cursor_down(self) -> None:
        if self._move_secret_key_highlight(1):
            return
        super().action_cursor_down()

    def _move_secret_key_highlight(self, delta: int) -> bool:
        focused = self.app.focused
        if not isinstance(focused, ListView) or focused.id != "secret-key-list":
            return False
        keys = self._secret_key_names()
        if not keys:
            return False
        current_index = focused.index if focused.index is not None else 0
        next_index = max(0, min(len(keys) - 1, current_index + delta))
        if next_index == current_index:
            return False
        move_list_highlight(self.app, focused, len(keys), delta)
        return True

    def action_save(self) -> None:
        values: Dict[str, Any] = {}
        for key, default in DEFAULT_SETTINGS.items():
            widget = self.query_one(f"#setting-{key}")
            if isinstance(default, bool):
                values[key] = bool(widget.value)
            elif isinstance(default, int):
                try:
                    values[key] = int(widget.value)
                except ValueError:
                    values[key] = default
            else:
                values[key] = str(widget.value)
        self.dismiss({"action": "save", "settings": values})

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_add_secret(self) -> None:
        if self.secrets_manager is None:
            self._set_secret_status("Secrets manager is unavailable")
            return
        key_input = self.query_one("#secret-key-input", CommandInput)
        value_input = self.query_one("#secret-value-input", CommandInput)
        key_name = str(key_input.value or "").strip()
        secret_value = str(value_input.value or "")
        if not key_name or not secret_value:
            self._set_secret_status("Enter both a key and API key")
            return
        if key_name in set(self._secret_key_names()):
            self._set_secret_status(f"Key already exists: {key_name}")
            focus_command_widget(self, key_input, self._scroll_container())
            return
        self.secrets_manager.set_secret(key_name, secret_value)
        self._set_secret_input_values("", "")
        self._refresh_secret_key_list(key_name)
        self._set_secret_status(f"Saved key: {key_name}")
        focus_command_widget(self, key_input, self._scroll_container())

    def action_clear_secret(self) -> None:
        self._set_secret_input_values("", "")
        self._set_secret_status("Secret fields cleared")
        focus_command_widget(
            self,
            self.query_one("#secret-key-input", CommandInput),
            self._scroll_container(),
        )

    def action_delete_secret(self) -> None:
        key_name = self._selected_secret_key()
        if not key_name:
            self._set_secret_status("Select a saved key to delete")
            return
        self.app.push_screen(
            ConfirmScreen(f"Delete saved key '{key_name}'?", "Delete", "Cancel"),
            lambda confirmed, key=key_name: self._delete_secret_after_confirm(
                key,
                confirmed,
            ),
        )

    def _delete_secret_after_confirm(self, key_name: str, confirmed: bool) -> None:
        if not confirmed:
            return
        deleted = bool(
            self.secrets_manager and self.secrets_manager.delete_secret(key_name)
        )
        self._refresh_secret_key_list()
        self._set_secret_status(
            f"Deleted key: {key_name}" if deleted else f"Key not found: {key_name}"
        )
        try:
            focus_command_widget(
                self,
                self.query_one("#secret-key-list", ListView),
                self._scroll_container(),
            )
        except Exception:
            pass

    def _set_secret_input_values(self, key_name: str, secret_value: str) -> None:
        key_input = self.query_one("#secret-key-input", CommandInput)
        value_input = self.query_one("#secret-value-input", CommandInput)
        key_input.value = key_name
        value_input.value = secret_value
        key_input.end_edit()
        value_input.end_edit()

    def _selected_secret_key(self) -> Optional[str]:
        list_view = self.query_one("#secret-key-list", ListView)
        keys = self._secret_key_names()
        if list_view.index is None or list_view.index < 0 or list_view.index >= len(keys):
            return None
        return keys[list_view.index]

    def _secret_key_names(self) -> list[str]:
        if self.secrets_manager is None:
            return []
        return list(self.secrets_manager.list_keys())

    def _refresh_secret_key_list(self, preferred_key: Optional[str] = None) -> None:
        list_view = self.query_one("#secret-key-list", ListView)
        keys = self._secret_key_names()
        current_index = list_view.index
        list_view.clear()
        for key in keys:
            list_view.append(ListItem(Static(key)))
        if preferred_key and preferred_key in keys:
            list_view.index = keys.index(preferred_key)
        elif current_index is not None and 0 <= current_index < len(keys):
            list_view.index = current_index
        elif keys:
            list_view.index = 0
        else:
            list_view.index = None

    def _set_secret_status(self, message: str) -> None:
        try:
            self.query_one("#secrets-status", Static).update(message)
        except Exception:
            pass

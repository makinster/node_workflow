"""Regressions reproduced before the phase-2 keymap migration."""

import asyncio

from textual.app import App
from textual.binding import Binding, BindingsMap
from textual.widgets import Select, TabbedContent


def test_node_config_availability_does_not_close_select():
    from backend.stash_manager import StashManager
    from tests.test_stash_insert import _config_app

    async def go():
        app, open_config = _config_app(StashManager(), "file_reader_node")
        async with app.run_test(size=(100, 35)) as pilot:
            screen = await open_config(pilot)
            select = screen.query_one("#field-input_source", Select)
            select.focus()
            await pilot.press("enter")
            await pilot.pause()
            assert select.expanded
            focused = app.focused
            screen.check_action("cancel", ())
            screen.check_action("back", ())
            _ = screen.active_bindings
            assert select.expanded, "availability queries closed a Select"
            assert app.focused is focused

    asyncio.run(go())


def _move_binding(screen, old_keys, new_key, action):
    """Emulate rebinding at the native layer without depending on registry IDs."""
    rows = [binding for key, bindings in screen._bindings.key_to_bindings.items()
            if key not in old_keys for binding in bindings]
    screen._bindings = BindingsMap([*rows, Binding(new_key, action, "Remapped", priority=True)])


def test_execution_stop_has_no_raw_key_route_after_rebinding():
    from frontend.screens.execution import ExecutionScreen
    from tests.test_debug_nodes import _make_services

    master, workflow, memory, _ = _make_services()
    workflow.create_new("Stop routing")
    calls = []

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(ExecutionScreen(workflow, memory, master))

    async def go():
        app = Host()
        async with app.run_test(size=(100, 35)) as pilot:
            screen = app.screen
            screen.action_stop = lambda: calls.append("stop")
            _move_binding(screen, {"s", "S"}, "f7", "stop")
            await pilot.press("s", "S")
            assert calls == [], "old Stop key survived outside native bindings"
            await pilot.press("f7")
            assert calls == ["stop"]

    asyncio.run(go())


def test_settings_tab_has_no_raw_digit_route_after_rebinding():
    from backend.configuration_manager import DEFAULT_SETTINGS
    from frontend.screens.settings import SettingsScreen

    class Configuration:
        def get_all(self):
            return dict(DEFAULT_SETTINGS)

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(SettingsScreen(Configuration()))

    async def go():
        app = Host()
        async with app.run_test(size=(100, 35)) as pilot:
            screen = app.screen
            tabs = screen.query_one("#settings-tabs", TabbedContent)
            screen.action_settings_tab_secrets()
            app.set_focus(screen.query_one("#save-settings"))
            await pilot.pause()
            assert tabs.active == "settings-tab-secrets"
            calls = []
            original_jump = screen.action_jump_settings_tab
            def jump(number):
                calls.append(number)
                original_jump(number)
            screen.action_jump_settings_tab = jump
            _move_binding(screen, {"1"}, "f7", "jump_settings_tab(1)")
            await pilot.press("1")
            # Also exercise the screen's bubbled-event fallback independently
            # of the focused control's handling of digits.
            from textual import events
            screen.post_message(events.Key("1", "1"))
            await pilot.pause()
            assert calls == [], "old digit bypassed the binding map"
            assert tabs.active == "settings-tab-secrets"
            await pilot.press("f7")
            await pilot.pause()
            assert calls == [1]
            assert tabs.active == "settings-tab-general"

    asyncio.run(go())

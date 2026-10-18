"""Characterize actual key routes before and after registry migration."""

import asyncio

import pytest
from textual.app import App
from textual.widgets import Button, Label

from frontend.screens.confirm import ConfirmScreen


@pytest.mark.parametrize("key, expected", [
    ("y", True), ("n", False), ("escape", False), ("ctrl+q", False),
    ("e", True), ("enter", True),
])
def test_confirm_default_keys(key, expected):
    results = []

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def check_action(self, action, parameters):
            # Isolate modal routes from Textual App's default Ctrl+Q quit.
            return action != "quit"

        def on_mount(self):
            self.push_screen(ConfirmScreen("Continue?"), results.append)

    async def go():
        app = Host()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            assert str(app.screen.query_one(".modal-help", Label).render()) == (
                "Y confirm  N / Esc cancel"
            )
            await pilot.press(key)
            await pilot.pause()
            assert results == [expected]

    asyncio.run(go())


@pytest.mark.parametrize("key", ["d", "right", "tab"])
def test_confirm_navigation_activates_focused_cancel(key):
    results = []

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def check_action(self, action, parameters):
            # Isolate modal routes from Textual App's default Ctrl+Q quit.
            return action != "quit"

        def on_mount(self):
            self.push_screen(ConfirmScreen("Continue?"), results.append)

    async def go():
        app = Host()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            await pilot.press(key)
            assert app.focused is app.screen.query_one("#confirm-no", Button)
            await pilot.press("e")
            await pilot.pause()
            assert results == [False]

    asyncio.run(go())


@pytest.mark.parametrize("widget_kind", ["input", "textarea"])
def test_priority_command_yields_to_typing_and_active_editor(widget_kind):
    from textual.app import ComposeResult
    from textual.containers import Vertical
    from textual.screen import Screen
    from frontend.keymap import NAVIGATION, Command, Profile, bindings_for
    from frontend.keymap_runtime import KeymapScreenMixin
    from frontend.widgets.command_input import CommandInput, CommandTextArea
    from frontend.widgets.command_screen_mixin import CommandScreenMixin

    widget_type = CommandInput if widget_kind == "input" else CommandTextArea
    profile = Profile("typing-probe", (
        Command("probe.nav", ("y",), "probe", "Probe", priority=True),
        *NAVIGATION,
    ))

    class Probe(CommandScreenMixin, Screen):
        KEYMAP = profile
        BINDINGS = bindings_for(KEYMAP)

        def compose(self) -> ComposeResult:
            with Vertical():
                yield widget_type(id="editor")
                yield Button("Other", id="other")

        def action_probe(self):
            self.app.calls += 1

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"
        calls = 0

        def on_mount(self):
            self.push_screen(Probe())

    async def go():
        app = Host()
        async with app.run_test(size=(100, 30)) as pilot:
            editor = app.screen.query_one("#editor", widget_type)
            editor.focus()
            await pilot.press("y")
            assert app.calls == 1  # priority runs despite nonediting text focus
            editor.begin_edit()
            await pilot.press("y", "1", "2")
            assert (editor.value if widget_kind == "input" else editor.text) == "y12"
            assert app.calls == 1
            # Retained editor ownership also suppresses actions after focus drift.
            app.set_focus(app.screen.query_one("#other"))
            assert not app.screen.check_action("probe", ())
            assert editor.editing

    asyncio.run(go())


def test_select_queries_are_pure_and_own_navigation_keys():
    from textual.app import ComposeResult
    from textual.screen import Screen
    from textual.widgets import Select
    from frontend.keymap import NAVIGATION, Command, Policy, Profile, bindings_for
    from frontend.keymap_runtime import KeymapScreenMixin
    from frontend.widgets.command_screen_mixin import CommandScreenMixin

    profile = Profile("select-probe", (
        Command("probe.nav", ("y",), "probe", "Probe", priority=True),
        Command("probe.overlay", ("f6",), "overlay", "Overlay", frozenset({Policy.SELECT}), True),
        *NAVIGATION,
    ))

    class Probe(CommandScreenMixin, Screen):
        KEYMAP = profile
        BINDINGS = bindings_for(KEYMAP)

        def compose(self) -> ComposeResult:
            yield Select([("First", "first"), ("Second", "second")], allow_blank=False)

        def action_probe(self):
            self.app.calls.append("nav")

        def action_overlay(self):
            self.app.calls.append("overlay")

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def __init__(self):
            super().__init__()
            self.calls = []

        def on_mount(self):
            self.push_screen(Probe())

    async def go():
        app = Host()
        async with app.run_test(size=(100, 30)) as pilot:
            select = app.screen.query_one(Select)
            select.focus()
            await pilot.press("enter")
            await pilot.pause()
            assert select.expanded
            focused = app.focused
            for _ in range(3):
                assert not app.screen.check_action("probe", ())
                assert app.screen.check_action("overlay", ())
                _ = app.screen.active_bindings
            assert select.expanded and app.focused is focused
            await pilot.press("f6", "y")
            assert app.calls == ["overlay"]
            await pilot.press("down", "enter")
            assert select.value == "second"
            assert not select.expanded
            await pilot.press("y", "f6")
            assert app.calls == ["overlay", "nav"]

    asyncio.run(go())


def test_modal_scope_blocks_root_and_suspended_screen_commands():
    from textual.app import ComposeResult
    from textual.screen import Screen
    from frontend.keymap import Command, Profile, Scope, bindings_for
    from frontend.keymap_runtime import KeymapScreenMixin, available, context_for

    command = Command("probe.root", ("f4",), "probe", "Probe", priority=True)
    profile = Profile("scope-probe", (command,))

    class Background(KeymapScreenMixin, Screen):
        KEYMAP = profile
        BINDINGS = bindings_for(KEYMAP)

        def compose(self) -> ComposeResult:
            yield Label("Background")

        def action_probe(self):
            self.app.calls += 1

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"
        BINDINGS = bindings_for(Profile("root", (command,), Scope.APPLICATION))
        calls = 0

        def on_mount(self):
            self.push_screen(Background())

        def check_action(self, action, parameters):
            if action == "probe":
                return available(command, Scope.APPLICATION, context_for(self))
            return action != "quit"

        def action_probe(self):
            self.calls += 1

    async def go():
        app = Host()
        async with app.run_test(size=(100, 30)) as pilot:
            background = app.screen
            await pilot.press("f4")
            assert app.calls == 1
            app.push_screen(ConfirmScreen("Continue?"))
            await pilot.pause()
            assert background.check_action("probe", ()) is False
            await pilot.press("f4")
            assert app.calls == 1
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is background
            await pilot.press("f4")
            assert app.calls == 2

    asyncio.run(go())

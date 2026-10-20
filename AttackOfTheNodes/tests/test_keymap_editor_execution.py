"""Editor/Execution reference text follows the same profiles as native dispatch."""

import asyncio
from dataclasses import replace
import re

import pytest
from textual.containers import VerticalScroll
from textual.widgets import Button, Static

import frontend.keymap as keymap
from frontend.screens.execution import ExecutionScreen
from frontend.screens.help import HELP_TEXT, HelpScreen
from frontend.widgets.status_bar import StatusBar
from tests.test_execution_screen import fan_with_failure
from tests.test_execution_status import linear, make_app, until


def help_text(screen):
    return str(screen.query_one("#help-text", Static).render())


def test_execution_keys_and_routes_stay_unchanged():
    routes = {
        binding.key: binding.action for binding in keymap.bindings_for(keymap.EXECUTION)
    }
    assert routes == {
        "p": "pause_resume",
        "x": "stop",
        "X": "stop",
        "w": "cursor_up",
        "up": "cursor_up",
        "s": "cursor_down",
        "down": "cursor_down",
        "a": "branch(-1)",
        "left": "branch(-1)",
        "d": "branch(1)",
        "right": "branch(1)",
        "f": "follow",
        "v": "error_panel",
        "m": "memory",
        "o": "output",
        # 4c-2 (owner, 2026-10-20): E and Enter open a running subworkflow;
        # elsewhere E still shows the errors.
        "e": "open_or_errors",
        "enter": "open_call",
        "escape": "back_to_editor",
        "ctrl+q": "revert_or_cancel",
    }


@pytest.mark.parametrize(
    "topic,profile", [("editor", keymap.EDITOR), ("execution", keymap.EXECUTION)]
)
def test_help_lists_the_screen_profiles_and_inherited_commands(topic, profile):
    async def check():
        app, master, wm, memory, bus = make_app()
        linear(wm)
        async with app.run_test(size=(100, 30)) as pilot:
            app.push_screen(HelpScreen(topic))
            await pilot.pause()
            text = help_text(app.screen)
            for command in profile.commands:
                assert command.description in text
            assert "Ctrl+R" in text and "Run" in text
            if topic == "execution":
                assert re.search(r"X\s+Stop", text)
                assert not re.search(r"S\s+Stop", text)
                assert "Show/hide error" in text and "Follow" in text

    asyncio.run(check())


def test_reference_generation_reads_changed_profile_keys_and_descriptions():
    changed = replace(
        keymap.EXECUTION,
        commands=tuple(
            (
                replace(command, keys=("f11",), description="End run")
                if command.id == "execution.stop"
                else command
            )
            for command in keymap.EXECUTION.commands
        ),
    )
    text = "\n".join(keymap.help_for(changed))
    assert re.search(r"F11\s+End run", text)
    assert "f11 stop" in keymap.screen_hint_for(changed)
    assert "x stop" not in keymap.screen_hint_for(changed)


def test_editor_hint_and_help_follow_native_rebinding():
    async def check():
        app, master, wm, memory, bus = make_app()
        linear(wm)
        calls = []
        async with app.run_test(size=(100, 30)) as pilot:
            screen = app.screen
            screen.action_workflow_library = lambda: calls.append("file")
            app.set_keymap({"editor.workflow_library": "f7"})
            screen.refresh_from_backend()
            await pilot.pause()
            assert (
                screen.query_one(StatusBar)._binding_text
                == "f7 file | o options | h help | ctrl+q quit"
            )
            await pilot.press("f")
            assert calls == []
            await pilot.press("f7")
            assert calls == ["file"]
            await pilot.press("h")
            await pilot.pause()
            text = help_text(app.screen)
            assert re.search(r"F7\s+File", text)
            assert not re.search(r"^\s+F\s+File", text, re.MULTILINE)

    asyncio.run(check())


def test_execution_error_hint_and_help_follow_native_rebinding_without_modal_leaks():
    async def check():
        app, master, wm, memory, bus = make_app()
        fan_with_failure(wm)
        async with app.run_test(size=(110, 34)) as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            app.set_keymap({"execution.error_panel": "f6", "execution.stop": "f7"})
            await master.start_workflow()
            try:
                await until(lambda: bool(screen.pending_recoveries))
                app.flush_refresh()
                await pilot.pause()
                assert screen.query_one(StatusBar)._binding_text.startswith(
                    "f6 hide error | "
                )
                assert "f7 stop" in screen.query_one(StatusBar)._binding_text
                await pilot.press("v")
                assert not screen._panel_hidden
                await pilot.press("f6")
                assert screen._panel_hidden
                assert screen.query_one(StatusBar)._binding_text.startswith(
                    "f6 show error | "
                )
                await pilot.press("h")
                await pilot.pause()
                text = help_text(app.screen)
                assert re.search(r"F6\s+Show/hide error", text)
                assert re.search(r"F7\s+Stop", text)
                await pilot.press("f6", "f7", "x", "p")
                assert screen._panel_hidden and screen.pending_recoveries
                await pilot.press("escape")
                await pilot.pause()
                await pilot.press("x")
                assert screen.pending_recoveries
                await pilot.press("f7")
                await master.wait_for_completion()
                assert not screen.pending_recoveries
            finally:
                master.stop()
                await master.wait_for_completion()

    asyncio.run(check())


@pytest.mark.parametrize("width", [60, 100, 140])
def test_generated_help_scrolls_by_keyboard_with_close_visible(width):
    async def check():
        app, master, wm, memory, bus = make_app()
        linear(wm)
        async with app.run_test(size=(width, 24)) as pilot:
            app.push_screen(HelpScreen("editor"))
            await pilot.pause()
            screen = app.screen
            scroll = screen.query_one("#help-scroll", VerticalScroll)
            await pilot.press("s", "s", "down")
            await pilot.pause()
            assert scroll.scroll_y > 0
            assert screen.query_one("#close-help", Button).region.bottom <= 24
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is not screen

    asyncio.run(check())


def test_reference_keeps_literal_punctuation_after_native_normalization():
    text = "\n".join(keymap.help_for(keymap.EDITOR))
    assert "QUESTION_MARK" not in text
    assert re.search(r"H / \?\s+Help", text)
    changed = replace(
        keymap.EDITOR,
        commands=tuple(
            replace(command, keys=("?",)) if command.id == "editor.help" else command
            for command in keymap.EDITOR.commands
        ),
    )
    assert "? help" in keymap.screen_hint_for(changed)


@pytest.mark.parametrize(
    "profile,expected",
    [
        (keymap.EDITOR, "f file | o options | h help | ctrl+q quit"),
        (
            keymap.EXECUTION,
            "w/s move | a/d branch | f follow | m memory | o output | p pause | x stop | esc editor",
        ),
    ],
)
def test_default_compact_hints_keep_the_existing_text(profile, expected):
    assert keymap.screen_hint_for(profile) == expected
    if profile is keymap.EXECUTION:
        assert re.search(r"Esc\s+Editor", "\n".join(keymap.help_for(profile)))

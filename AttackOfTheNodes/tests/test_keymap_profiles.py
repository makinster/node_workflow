"""Contracts for real migrated owners and production keypress routes."""

import asyncio
import importlib

import pytest
from textual.widgets import Input, Select, TabbedContent

from frontend.keymap import PROFILES, WIDGET_PROFILES


OWNER_TYPES = [
    ("frontend.app", "AttackOfTheNodesApp"),
    *[("frontend.screens." + module, name) for module, name in [
        ("confirm", "ConfirmScreen"), ("editor", "EditorScreen"),
        ("execution", "ExecutionScreen"), ("node_config", "NodeConfigScreen"),
        ("node_selector", "NodeSelectorScreen"), ("settings", "SettingsScreen"),
        ("stash", "StashScreen"), ("stash", "_PasteBox"), ("stash", "_SearchInput"),
        ("workflow_library", "WorkflowLibraryScreen"), ("workflow_library", "NamePromptScreen"),
        ("workflow_library", "PathPromptScreen"), ("workflow_library", "_NameInput"),
        ("branch_selector", "BranchSelectorScreen"), ("branch_keep_selector_screen", "BranchKeepSelectorScreen"),
        ("merge_beacon_selector", "MergeBeaconSelectorScreen"), ("group_picker", "GroupPickerScreen"),
        ("unsaved_changes", "UnsavedChangesScreen"), ("user_input", "UserInputScreen"),
        ("help", "HelpScreen"), ("error_details", "ErrorDetailsScreen"),
        ("recovery_branch_unpick", "RecoveryBranchUnpickScreen"),
    ]],
    ("frontend.widgets.contract_rows", "ContractRowEditor"),
    ("frontend.widgets.long_text", "LongTextEditor"),
    ("frontend.widgets.command_input", "CommandInput"),
    ("frontend.widgets.command_input", "CommandTextArea"),
    ("frontend.widgets.select_keymap", "SelectOverlay"),
    ("textual.widgets", "Select"),
]


@pytest.mark.parametrize("module, name", OWNER_TYPES)
def test_registered_owner_native_routes_and_actions(module, name):
    if name in {"Select", "SelectOverlay"}:
        from frontend.widgets.select_keymap import install_select_keymap
        install_select_keymap()
    owner = getattr(importlib.import_module(module), name)
    profile = owner.KEYMAP
    for command in profile.commands:
        action, _ = command.action_signature
        from textual.app import App
        # Textual falls back to App for framework actions such as focus_next.
        assert callable(getattr(owner, "action_" + action, getattr(App, "action_" + action, None))), (name, command.id)
        # Framework maps normalize printable keys such as '/' and '?'.
        from textual.binding import BindingsMap
        from frontend.keymap import bindings_for
        normalized = BindingsMap(bindings_for(type(profile)("one", (command,)))).key_to_bindings
        actual = owner._merged_bindings.key_to_bindings
        for native_key in normalized:
            assert any(b.id == command.id and b.action == command.action
                       for b in actual[native_key]), (name, native_key, command.id)
    if profile.cancel_action:
        assert callable(getattr(owner, "action_" + profile.cancel_action))


def test_shared_ids_never_describe_different_commands():
    seen = {}
    owners = {getattr(importlib.import_module(module), name).KEYMAP.id for module, name in OWNER_TYPES}
    for profile in (*PROFILES, *WIDGET_PROFILES):
        assert profile.id in owners
        for command in profile.commands:
            assert command.id not in seen or seen[command.id] == command
            seen[command.id] = command


@pytest.mark.parametrize("key", ["ctrl+s", "ctrl+enter"])
@pytest.mark.parametrize("editing", [False, True])
def test_node_config_save_and_stay_in_nav_and_text(key, editing):
    from backend.stash_manager import StashManager
    from tests.test_stash_insert import _config_app

    async def go():
        app, open_config = _config_app(StashManager(), "file_reader_node", {"input_source": "Configured"})
        async with app.run_test(size=(100, 35)) as pilot:
            screen = await open_config(pilot)
            field = screen.query_one("#alias-input", Input)
            field.focus()
            if editing:
                field.begin_edit()
                await pilot.press(*" New")
            else:
                field.value = "Saved alias"
            expected = field.value
            await pilot.press(key)
            await pilot.pause()
            assert app.screen is screen
            assert not field.editing
            assert screen._saved_result["alias"] == expected

    asyncio.run(go())


def test_node_config_ctrl_q_reverts_before_leaving_and_modal_blocks_root():
    from backend.stash_manager import StashManager
    from tests.test_stash_insert import _config_app

    async def go():
        app, open_config = _config_app(StashManager(), "file_reader_node")
        async with app.run_test(size=(100, 35)) as pilot:
            screen = await open_config(pilot)
            field = screen.query_one("#alias-input", Input)
            original = field.value
            field.begin_edit()
            await pilot.press(*" temporary")
            await pilot.press("ctrl+q")
            await pilot.pause()
            assert app.screen is screen
            assert field.value == original and not field.editing
            await pilot.press("ctrl+r")
            assert app.master_state.current_run_id is None
            await pilot.press("ctrl+q")
            await pilot.pause()
            assert app.screen is not screen

    asyncio.run(go())


def test_remapped_select_overlay_has_one_native_navigation_route():
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
            from textual.widgets._select import SelectOverlay
            overlay = select.query_one(SelectOverlay)
            calls = []
            original = overlay.action_cursor_down
            def down():
                calls.append("down")
                original()
            overlay.action_cursor_down = down
            app.set_keymap({"select.down": "f7"})
            await pilot.press("s")
            assert calls == []
            await pilot.press("f7")
            assert calls == ["down"]
            await pilot.press("ctrl+q")
            assert not select.expanded and app.screen is screen

    asyncio.run(go())


def test_remapped_screen_navigation_does_not_survive_in_text_widget_fallback():
    from backend.stash_manager import StashManager
    from tests.test_stash_insert import _config_app

    async def go():
        app, open_config = _config_app(StashManager(), "file_reader_node")
        async with app.run_test(size=(100, 35)) as pilot:
            screen = await open_config(pilot)
            field = screen.query_one("#alias-input", Input)
            field.focus()
            await pilot.pause()
            calls = []
            screen.action_cursor_down = lambda: calls.append("down")
            app.set_keymap({"node_config.cursor_down": "f7"})
            await pilot.press("s", "down")
            assert calls == []
            await pilot.press("f7")
            assert calls == ["down"]
            field.begin_edit()
            await pilot.press("s", "1", "2")
            assert field.value.endswith("s12")
            assert calls == ["down"]

    asyncio.run(go())


@pytest.mark.parametrize("key", ["ctrl+s", "ctrl+enter"])
def test_node_config_multiline_save_commits_and_stays_open(key):
    from frontend.widgets.long_text import LongTextPreview
    from backend.stash_manager import StashManager
    from frontend.widgets.command_input import CommandTextArea
    from tests.test_stash_insert import _config_app

    async def go():
        app, open_config = _config_app(StashManager(), "file_output_node", {
            "file_path_source": "Configured", "content_source": "Configured",
        })
        async with app.run_test(size=(100, 35)) as pilot:
            screen = await open_config(pilot)
            await pilot.press("2")
            await pilot.pause()
            field = screen.query_one("#field-content", LongTextPreview)
            field.focus(); await pilot.press("e"); await pilot.pause()
            area = app.screen.query_one(CommandTextArea)
            await pilot.press(*"first", "enter", *"second")
            expected = area.text
            assert "\n" in expected
            await pilot.press("ctrl+s"); await pilot.pause()
            assert field.value == expected and screen._saved_result is None
            await pilot.press(key)
            await pilot.pause()
            assert app.screen is screen
            assert app.focused is field
            assert screen._saved_result["config"]["content"] == expected

    asyncio.run(go())


def test_nav_caret_alias_is_registered_and_can_be_rebound():
    from backend.stash_manager import StashManager
    from tests.test_stash_insert import _config_app

    async def go():
        app, open_config = _config_app(StashManager(), "file_reader_node")
        async with app.run_test(size=(100, 35)) as pilot:
            screen = await open_config(pilot)
            field = screen.query_one("#alias-input", Input)
            field.value = "abcd"
            field.focus()
            field.cursor_position = 4
            app.set_keymap({"text.caret_left": "f7"})
            await pilot.press("a")
            assert field.value == "abcd" and field.cursor_position == 4
            await pilot.press("f7")
            assert field.value == "abcd" and field.cursor_position == 3
            await pilot.press("e")
            assert field.editing and field.cursor_position == 3
            await pilot.press("a")
            assert field.value == "abcad"

    asyncio.run(go())

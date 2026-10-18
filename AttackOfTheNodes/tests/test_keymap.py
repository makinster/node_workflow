"""Registry and availability contracts, independently of display generation."""

from dataclasses import FrozenInstanceError

import pytest

from frontend.keymap import (
    CONFIRM, PROFILES, Command, Policy, Profile, Scope, bindings_for, hint_for,
)
from frontend.keymap_runtime import KeyContext, available
from frontend.screens.confirm import ConfirmScreen


def test_confirm_compiles_before_textual_merges_bindings():
    expected = {
        "y": ("confirm_yes", "confirm.accept"),
        "n": ("confirm_no", "confirm.reject"),
        "escape": ("confirm_no", "confirm.reject"),
        "ctrl+q": ("confirm_no", "confirm.cancel"),
        "w": ("cursor_up", "ui.focus.up"), "up": ("cursor_up", "ui.focus.up"),
        "s": ("cursor_down", "ui.focus.down"), "down": ("cursor_down", "ui.focus.down"),
        "a": ("cursor_left", "ui.focus.left"), "left": ("cursor_left", "ui.focus.left"),
        "d": ("cursor_right", "ui.focus.right"), "right": ("cursor_right", "ui.focus.right"),
        "e": ("activate_focused", "ui.activate"), "enter": ("activate_focused", "ui.activate"),
    }
    # No injected legacy aliases or ID-less override rows may replace the map.
    assert ConfirmScreen.BINDINGS == bindings_for(CONFIRM)
    actual = {key: (binding.action, binding.id)
              for key, rows in ConfirmScreen._merged_bindings.key_to_bindings.items()
              for binding in rows}
    for key, route in expected.items():
        assert actual[key] == route
    assert hint_for(CONFIRM) == "Y confirm  N / Esc cancel"


def test_ids_are_stable_and_actions_exist_on_profile_owner():
    assert CONFIRM.id == "confirm"
    seen = {}
    for profile in PROFILES:
        for command in profile.commands:
            assert command.id not in seen or seen[command.id] == command
            seen[command.id] = command
    with pytest.raises(FrozenInstanceError):
        CONFIRM.id = "changed"


@pytest.mark.parametrize("commands", [
    (Command("duplicate", ("y",), "yes", "Yes"), Command("duplicate", ("n",), "no", "No")),
    (Command("yes", ("y",), "yes", "Yes"), Command("no", ("y",), "no", "No")),
    (Command("blank", (), "yes", "Yes"),),
    (Command("combined", ("y,n",), "yes", "Yes"),),
    (Command("namespace", ("y",), "app.yes", "Yes"),),
    (Command("one", ("y",), "yes", "Yes"),
     Command("two", ("n",), "yes", "Yes", policies=frozenset({Policy.TEXT}))),
])
def test_invalid_profiles_are_rejected(commands):
    with pytest.raises(ValueError):
        Profile("invalid", commands)


@pytest.mark.parametrize("policy", list(Policy))
@pytest.mark.parametrize("scope", list(Scope))
@pytest.mark.parametrize("context, screen_policy, app_policy", [
    (KeyContext(True), Policy.NAV, Policy.NAV),
    (KeyContext(True, typing=True), Policy.TEXT, Policy.TEXT),
    (KeyContext(True, select_expanded=True), Policy.SELECT, Policy.SELECT),
    (KeyContext(True, typing=True, select_expanded=True, modal_open=True), Policy.SELECT, None),
    (KeyContext(False, modal_open=True), None, None),
    (KeyContext(True, modal_open=True), Policy.NAV, None),
])
def test_pure_mode_and_modal_policy(policy, scope, context, screen_policy, app_policy):
    command = Command("test.command", ("x",), "test", "Test", policies=frozenset({policy}))
    expected_policy = {Scope.SCREEN: screen_policy, Scope.APPLICATION: app_policy, Scope.WIDGET: screen_policy}[scope]
    before = (context.owner_active, context.typing, context.select_expanded, context.modal_open)
    assert available(command, scope, context) is (policy is expected_policy)
    assert (context.owner_active, context.typing, context.select_expanded, context.modal_open) == before


def test_command_can_work_in_nav_and_text_without_allowing_select():
    command = Command("test.save", ("ctrl+s",), "save", "Save",
                      policies=frozenset({Policy.NAV, Policy.TEXT}), priority=True)
    assert available(command, Scope.SCREEN, KeyContext(True))
    assert available(command, Scope.SCREEN, KeyContext(True, typing=True))
    assert not available(command, Scope.SCREEN, KeyContext(True, select_expanded=True))


def test_key_specific_policies_require_separate_actions():
    with pytest.raises(ValueError, match="conflicting policies"):
        Profile("save", (
            Command("test.save.nav", ("s",), "save", "Save"),
            Command("test.save.edit", ("ctrl+s",), "save", "Save",
                    policies=frozenset({Policy.NAV, Policy.TEXT})),
        ))

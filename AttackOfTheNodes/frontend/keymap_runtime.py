"""Pure keymap availability and small adapters over native Textual dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual.screen import ModalScreen, Screen
from textual.widgets import Select

from frontend.keymap import Command, Policy, Profile, Scope, priority_for


@dataclass(frozen=True)
class KeyContext:
    owner_active: bool
    typing: bool = False
    select_expanded: bool = False
    modal_open: bool = False

    @property
    def policy(self) -> Policy:
        if self.select_expanded:
            return Policy.SELECT
        return Policy.TEXT if self.typing else Policy.NAV


def available(command: Command, scope: Scope, context: KeyContext) -> bool:
    """Queries never focus controls, close Selects, commit or dispatch actions."""
    return (
        context.owner_active
        and not (scope is Scope.APPLICATION and context.modal_open)
        and context.policy in command.policies
    )


def active_editor(screen):
    """Only the currently focused text widget owns typing and edit commands."""
    widget = screen.app.focused
    return widget if getattr(widget, "editing", False) else None


def context_for(owner) -> KeyContext:
    app = owner.app
    current = app.screen
    scope = getattr(getattr(owner, "KEYMAP", None), "scope", Scope.SCREEN if isinstance(owner, Screen) else Scope.APPLICATION)
    screen = owner if isinstance(owner, Screen) else owner.screen if scope is Scope.WIDGET else current
    focused = app.focused
    # A few reusable hosts mount a Screen inside the active screen. It owns
    # actions only while focus is inside it; suspended pushed screens do not.
    embedded_active = (
        focused is not None
        and screen in focused.ancestors_with_self
        and current in screen.ancestors
    )
    owner_active = screen is current or embedded_active
    if scope is Scope.WIDGET:
        editor = active_editor(screen)
        owner_active = owner_active and (
            (app.focused is owner and (editor is None or any(select.expanded for select in screen.query(Select))))
            or editor is owner
        )
    return KeyContext(
        owner_active=owner_active,
        typing=active_editor(screen) is not None,
        select_expanded=any(select.expanded for select in screen.query(Select)),
        modal_open=isinstance(current, ModalScreen),
    )


def effective_bindings(owner):
    """Isolate Textual 8.2's keymap storage here; dispatch still stays native.

    Use this for adapters, never active_bindings (which queries guards
    and would recurse from check_consume_key). Copy before applying overrides.
    """
    bindings = owner._bindings.copy()
    overrides = owner.app._keymap
    if overrides:
        bindings.apply_keymap(overrides)
    return bindings


def commands_for_key(owner, key: str) -> tuple[Command, ...]:
    profile = getattr(owner, "KEYMAP", None)
    if profile is None:
        return ()
    ids = {binding.id for binding in effective_bindings(owner).key_to_bindings.get(key, ())}
    return tuple(command for command in profile.commands if command.id in ids)


def screen_owns_key(widget, key: str, *, priority_only: bool = False) -> bool:
    """Allow an explicitly registered screen command through a text adapter."""
    screen = widget.screen
    profile = getattr(screen, "KEYMAP", None)
    if profile is None:
        return False
    context = context_for(screen)
    return any(
        (not priority_only or priority_for(command, key))
        and available(command, profile.scope, context)
        and screen.check_action(*command.action_signature) is not False
        for command in commands_for_key(screen, key)
    )


def navigation_keys(owner, role: str | None = None) -> set[str]:
    ids = {command.id for command in owner.KEYMAP.commands
           if command.navigation and (role is None or command.navigation == role)}
    return {key for key, rows in effective_bindings(owner).key_to_bindings.items()
            if any(binding.id in ids for binding in rows)}


class KeymapScreenMixin:
    """Owner availability adapter; Textual resolves keys and runs actions."""

    KEYMAP: ClassVar[Profile]

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        commands = [command for command in self.KEYMAP.commands
                    if command.action_signature == (action, parameters)]
        if commands:
            context = context_for(self)
            if not all(available(command, self.KEYMAP.scope, context) for command in commands):
                return False
        return super().check_action(action, parameters)

    def action_revert_or_cancel(self) -> None:
        """Ctrl+Q reverts an active edit first; a second press leaves the owner."""
        screen = self if isinstance(self, Screen) else self.app.screen
        editor = active_editor(screen)
        if editor is not None:
            editor.end_edit(revert=True)
            return
        action = self.KEYMAP.cancel_action
        if action is not None:
            getattr(self, f"action_{action}")()

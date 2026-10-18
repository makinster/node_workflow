"""Pure keymap availability layered on native Textual action dispatch.

Context collection reads state only. Availability never focuses a control,
closes a Select, commits an editor or dispatches another action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual.screen import ModalScreen, Screen
from textual.widgets import Select

from frontend.keymap import Command, Policy, Profile, Scope


@dataclass(frozen=True)
class KeyContext:
    owner_active: bool
    typing: bool = False
    select_expanded: bool = False
    modal_open: bool = False

    @property
    def policy(self) -> Policy:
        # An expanded overlay owns focus even if a previous editor is retained.
        if self.select_expanded:
            return Policy.SELECT
        return Policy.TEXT if self.typing else Policy.NAV


def available(command: Command, scope: Scope, context: KeyContext) -> bool:
    """Shared pure NAV/TEXT/Select and screen/application modal-scope guard."""
    return (
        context.owner_active
        and not (scope is Scope.APPLICATION and context.modal_open)
        and command.policy is context.policy
    )


def context_for(owner) -> KeyContext:
    """Snapshot the current screen and active editor without changing either."""
    app = owner.app
    current = app.screen
    screen = owner if isinstance(owner, Screen) else current
    active_editor = getattr(screen, "_active_command_text_widget", None)
    return KeyContext(
        owner_active=not isinstance(owner, Screen) or owner is current,
        typing=bool(getattr(app.focused, "editing", False)
                    or getattr(active_editor, "editing", False)),
        select_expanded=any(select.expanded for select in screen.query(Select)),
        modal_open=isinstance(current, ModalScreen),
    )


class KeymapScreenMixin:
    """Availability adapter only; Textual continues to resolve and run actions.

    Put before CommandScreenMixin so registry guards run first. That legacy
    mixin still supplies focus mechanics during the incremental migration.
    Declare BINDINGS = bindings_for(KEYMAP) in the screen class itself.
    """

    KEYMAP: ClassVar[Profile]

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        commands = [command for command in self.KEYMAP.commands
                    if command.action_signature == (action, parameters)]
        if commands and not all(
            available(command, self.KEYMAP.scope, context_for(self))
            for command in commands
        ):
            return False
        return super().check_action(action, parameters)

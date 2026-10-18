"""Typed command definitions; no screens, application services or dispatch loop.

IDs describe operations and remain stable when keys or Python actions change.
Only migrated profiles belong here; legacy screens keep their existing bindings
until their migration. Textual's native dispatcher remains authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from textual.actions import parse
from textual.binding import Binding


class Scope(Enum):
    SCREEN = "screen"
    APPLICATION = "application"


class Policy(Enum):
    NAV = "navigation"
    TEXT = "text"
    SELECT = "select"


@dataclass(frozen=True)
class Command:
    id: str
    keys: tuple[str, ...]
    action: str
    description: str
    policy: Policy = Policy.NAV
    priority: bool = False
    # Compact hints are a subset of the same declared keys, never another map.
    hint: str | None = None

    @property
    def action_signature(self) -> tuple[str, tuple[object, ...]]:
        namespace, name, parameters = parse(self.action)
        if namespace:
            raise ValueError(f"{self.id}: actions must belong to their profile owner")
        return name, parameters


@dataclass(frozen=True)
class Profile:
    id: str
    commands: tuple[Command, ...]
    scope: Scope = Scope.SCREEN

    def __post_init__(self) -> None:
        ids: set[str] = set()
        keys: set[str] = set()
        policies: dict[tuple[str, tuple[object, ...]], Policy] = {}
        for command in self.commands:
            if not command.id or command.id in ids:
                raise ValueError(f"{self.id}: duplicate/empty command ID {command.id!r}")
            ids.add(command.id)
            if not command.description or not command.keys:
                raise ValueError(f"{command.id}: description and keys are required")
            signature = command.action_signature
            if signature in policies and policies[signature] != command.policy:
                raise ValueError(f"{command.id}: one action cannot have conflicting policies")
            policies[signature] = command.policy
            for key in command.keys:
                if not key or key.strip() != key or "," in key or key in keys:
                    raise ValueError(f"{command.id}: invalid or duplicate key {key!r}")
                keys.add(key)


# Reused semantic IDs; each profile compiles its own native bindings.
NAVIGATION = (
    Command("ui.focus.up", ("w", "up"), "cursor_up", "Up", priority=True),
    Command("ui.focus.down", ("s", "down"), "cursor_down", "Down", priority=True),
    Command("ui.focus.left", ("a", "left"), "cursor_left", "Left", priority=True),
    Command("ui.focus.right", ("d", "right"), "cursor_right", "Right", priority=True),
    Command("ui.activate", ("e", "enter"), "activate_focused", "Activate", priority=True),
)

CONFIRM = Profile("confirm", (
    Command("confirm.accept", ("y",), "confirm_yes", "Yes", hint="confirm"),
    Command("confirm.reject", ("n", "escape"), "confirm_no", "No", hint="cancel"),
    Command("confirm.cancel", ("ctrl+q",), "confirm_no", "Cancel", priority=True),
    *NAVIGATION,
))

PROFILES = (CONFIRM,)


def bindings_for(profile: Profile) -> list[Binding]:
    """Compile at class definition time, before Textual merges the MRO bindings."""
    return [
        Binding(
            key, command.action, command.description,
            id=command.id, priority=command.priority,
        )
        for command in profile.commands
        for key in command.keys
    ]


def display_key(key: str) -> str:
    """Consistent spelling for app hints; the input remains a native key name."""
    return {"escape": "Esc", "enter": "Enter", "up": "↑", "down": "↓",
            "left": "←", "right": "→"}.get(key, key.upper())


def hint_for(profile: Profile) -> str:
    """Initial compact display consumer; full contextual Help follows in PR 3."""
    return "  ".join(
        f"{' / '.join(display_key(key) for key in command.keys)} {command.hint}"
        for command in profile.commands if command.hint is not None
    )

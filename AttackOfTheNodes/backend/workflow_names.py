"""Workflow name rules shared by the library, New and ``aotn build``.

A name is trimmed, must not be blank, and must differ (ignoring case) from
every other saved workflow's name of the same kind: a standard workflow and
its subworkflow copy may share a name (owner, 2026-10-18), the way the File
window shows them on separate tabs. ``aotn run <name>`` picks the standard one;
``<name> [sub]`` picks the subworkflow. Unsaved workflows are not checked.
"""

from __future__ import annotations

from typing import Optional

from . import persistence

DEFAULT_NAME = "Untitled Workflow"


SUB_SUFFIX = " [sub]"


def name_taken(name: str, exclude_id: Optional[str] = None, callable_: bool = False) -> bool:
    """Whether a saved workflow of the same kind, other than ``exclude_id``,
    already uses ``name``."""
    wanted = name.strip().casefold()
    return any(
        str(entry.get("name") or "").strip().casefold() == wanted
        for entry in persistence.list_workflows()
        if entry.get("id") != exclude_id and bool(entry.get("callable")) == bool(callable_)
    )


def name_problem(name: str, exclude_id: Optional[str] = None, callable_: bool = False) -> Optional[str]:
    """Why ``name`` can't be used, or None when it can."""
    if not name.strip():
        return "Name can't be blank"
    if name.strip().casefold().endswith(SUB_SUFFIX.strip().casefold()):
        return "Names can't end with [sub]; the Subworkflows tab marks them"
    if name_taken(name, exclude_id, callable_):
        kind = "subworkflow" if callable_ else "workflow"
        return f"A saved {kind} is already named '{name.strip()}'"
    return None


def unused_name(base: str = DEFAULT_NAME, callable_: bool = False) -> str:
    """``base``, or ``base 2``, ``base 3``... the first no saved workflow of
    that kind uses."""
    candidate, number = base, 2
    while name_taken(candidate, callable_=callable_):
        candidate, number = f"{base} {number}", number + 1
    return candidate


def unused_copy_name(base: str, callable_: bool = True) -> str:
    """``base``, or ``base (2)``, ``base (3)``... for a copy (owner, 2026-10-18)."""
    candidate, number = base, 2
    while name_taken(candidate, callable_=callable_):
        candidate, number = f"{base} ({number})", number + 1
    return candidate

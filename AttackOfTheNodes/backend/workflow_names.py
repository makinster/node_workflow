"""Workflow name rules shared by the library, New and ``aotn build``.

A name is trimmed, must not be blank, and must differ (ignoring case) from
every other saved workflow's name, the way ``aotn run <name>`` resolves
names. Unsaved workflows are not checked: only saved names can collide.
"""

from __future__ import annotations

from typing import Optional

from . import persistence

DEFAULT_NAME = "Untitled Workflow"


def name_taken(name: str, exclude_id: Optional[str] = None) -> bool:
    """Whether a saved workflow other than ``exclude_id`` already uses ``name``."""
    wanted = name.strip().casefold()
    return any(
        str(entry.get("name") or "").strip().casefold() == wanted
        for entry in persistence.list_workflows()
        if entry.get("id") != exclude_id
    )


def name_problem(name: str, exclude_id: Optional[str] = None) -> Optional[str]:
    """Why ``name`` can't be used, or None when it can."""
    if not name.strip():
        return "Name can't be blank"
    if name_taken(name, exclude_id):
        return f"A saved workflow is already named '{name.strip()}'"
    return None


def unused_name(base: str = DEFAULT_NAME) -> str:
    """``base``, or ``base 2``, ``base 3``... the first no saved workflow uses."""
    candidate, number = base, 2
    while name_taken(candidate):
        candidate, number = f"{base} {number}", number + 1
    return candidate

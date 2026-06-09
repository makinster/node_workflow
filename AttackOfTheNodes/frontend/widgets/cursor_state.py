"""App-owned cursor mode tracker for command-mode screens."""

from __future__ import annotations


class CursorState:
    """Tracks whether the active screen is in NAV or EDIT mode.

    Owned by AttackOfTheNodesApp and updated by CommandScreenMixin whenever
    navigation moves or a text widget enters/leaves edit mode.
    """

    def __init__(self) -> None:
        self.mode: str = "nav"  # "nav" or "edit"

    def set_edit(self) -> None:
        self.mode = "edit"

    def set_nav(self) -> None:
        self.mode = "nav"

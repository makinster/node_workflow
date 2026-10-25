"""The TUI's text colours (owner, 2026-10-20). One meaning, one colour.

Use these names in Rich ``Text`` styles and markup instead of colour
literals; ``styles.tcss`` uses the matching Textual variables (listed in
docs/UI_QUICK_REFERENCE.md, "Colours"). Colour is never the only signal:
each status also has its mark (✓ ▶ ⏸ ⚠ ✗).

- ``MUTED``: hints, descriptions, ids, "nothing yet", separators.
- ``TYPE``: data types, ``[string]``; only types.
- ``SOURCE``: where a value comes from or goes: ``Vault key "count"``,
  ``next node``, ``typed: "Kim"``, a Vault log Source.
- ``SUCCESS`` / ``RUNNING`` / ``WARNING`` / ``ERROR``: run status and
  messages of that kind. Waiting for you is a warning.
- ``NAME``: node names and aliases (bold).
- ``PAYLOAD``: input and payload names (``who``, ``greeted``).
- ``KEY``: Vault key names (the ``"count"`` in ``Vault key "count"``).
- ``VALUE``: literal values (``"Kim"``, ``2``).
- ``HIGHLIGHT``: the background of the highlighted row or card, one solid
  colour over the whole row; text on it is plain.
Messages and headings use the normal text colour (headings bold).

**Palettes.** Every colour is a fixed hex value, so it looks the same in
every terminal (named ANSI colours such as "green" are redrawn by each
terminal's own theme). ``PALETTES`` holds one set per theme; ``use(name)``
switches the module's names. Code that should follow a switch while the app
runs reads ``colors.NAME`` when it draws, rather than copying the value at
import. ``tests/test_colors.py`` checks every text colour stays readable on
the palette's backgrounds.
"""

from typing import Dict

PALETTES: Dict[str, Dict[str, str]] = {
    "dark": {
        "MUTED": "#A0A6B0",
        "TYPE": "#4EC9B0",
        "SOURCE": "#9CDCFE",
        "SUCCESS": "#5FD068",
        "RUNNING": "#56C8D8",
        "WARNING": "#E5C07B",
        "ERROR": "#F48A90",
        "NAME": "#E8E8E8",
        "PAYLOAD": "#D7A3D3",
        "KEY": "#DCDCAA",
        "VALUE": "#E0A383",
        "HIGHLIGHT": "#1a3a5c",
        "MAP_BACKGROUND": "#101418",
        # The panel background text sits on outside the map (Textual's dark theme).
        "PANEL_BACKGROUND": "#1e1e1e",
    },
}
#: Text colours; each must read on every background below.
TEXT_ROLES = ("MUTED", "TYPE", "SOURCE", "SUCCESS", "RUNNING", "WARNING", "ERROR",
              "NAME", "PAYLOAD", "KEY", "VALUE")
BACKGROUND_ROLES = ("MAP_BACKGROUND", "PANEL_BACKGROUND", "HIGHLIGHT")

MUTED = TYPE = SOURCE = SUCCESS = RUNNING = WARNING = ERROR = ""
NAME = PAYLOAD = KEY = VALUE = ""
HIGHLIGHT = MAP_BACKGROUND = PANEL_BACKGROUND = ""
current = ""


def use(name: str) -> None:
    """Switch every colour name to the palette ``name``."""
    global current
    palette = PALETTES[name]
    globals().update(palette)
    current = name


use("dark")

#: One colour per Branch path (the gutter and path labels), in path order.
BRANCH_PATHS = (
    "#2dd4bf",  # teal
    "#60a5fa",  # blue
    "#a78bfa",  # violet
    "#f472b6",  # pink
    "#fb7185",  # rose
    "#fbbf24",  # amber
    "#a3e635",  # lime
    "#34d399",  # emerald
    "#22d3ee",  # cyan
    "#c084fc",  # purple
)

# Shared compact-table selection follows the same theme roles as nav-highlight.
# These are Textual tokens, so theme changes never leave a fixed bright cursor.
SELECTION_BACKGROUND = "$boost"
SELECTION_FOREGROUND = "$foreground"

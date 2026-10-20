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
- ``HIGHLIGHT``: the background of the highlighted row or card, one solid
  colour over the whole row; text on it is plain.
Values, names and headings use the normal text colour (headings bold).
"""

MUTED = "grey50"
TYPE = "#4EC9B0"
SOURCE = "#9CDCFE"
SUCCESS = "green"
RUNNING = "cyan"
WARNING = "yellow"
ERROR = "red"
HIGHLIGHT = "#1a3a5c"
#: The map rows behind the cards (not highlighted).
MAP_BACKGROUND = "#101418"

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

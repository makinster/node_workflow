"""Text colours come from frontend/colors.py (owner, 2026-10-20): one meaning,
one colour. This guard keeps colour literals out of the rest of the TUI.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_colors.py -v
"""

import re
from pathlib import Path

from frontend import colors

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
LITERAL = re.compile(
    r"""["'](?:grey\d+|green|red|yellow|cyan|#[0-9a-fA-F]{6})["']|\[/?dim\]|\[(?:red|green|yellow|cyan)\]""")
# Branch path colours are their own palette (one per path), not text meanings.
ALLOWED = {"colors.py", "branch_colors.py"}


def test_no_colour_literals_outside_colors_py():
    found = []
    for path in FRONTEND.rglob("*.py"):
        if path.name in ALLOWED:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if LITERAL.search(line):
                found.append(f"{path.relative_to(FRONTEND)}:{number}: {line.strip()}")
    assert found == []


def test_each_meaning_has_its_own_colour():
    names = ["MUTED", "TYPE", "SOURCE", "SUCCESS", "RUNNING", "WARNING", "ERROR", "HIGHLIGHT"]
    values = [getattr(colors, name) for name in names]
    assert len(set(values)) == len(values)

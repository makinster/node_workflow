"""Text colours come from frontend/colors.py (owner, 2026-10-20): one meaning,
one colour, fixed hex values, readable on dark backgrounds, and swappable as
a palette. These checks keep it that way.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_colors.py -v
"""

import re
from pathlib import Path

import pytest

from frontend import colors

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
LITERAL = re.compile(
    r"""["'](?:grey\d+|green|red|yellow|cyan|#[0-9a-fA-F]{6})["']"""
    r"""|\[/?(?:dim|grey\d+|red|green|yellow|cyan|#[0-9a-fA-F]{6})\]""")
ALLOWED = {"colors.py"}


def test_no_colour_literals_outside_colors_py():
    found = []
    for path in FRONTEND.rglob("*.py"):
        if path.name in ALLOWED:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if LITERAL.search(line):
                found.append(f"{path.relative_to(FRONTEND)}:{number}: {line.strip()}")
    assert found == []


@pytest.mark.parametrize("name", sorted(colors.PALETTES))
def test_each_palette_has_every_role_as_a_fixed_hex_colour(name):
    palette = colors.PALETTES[name]
    assert set(palette) == set(colors.TEXT_ROLES) | set(colors.BACKGROUND_ROLES)
    assert all(re.fullmatch(r"#[0-9a-fA-F]{6}", value) for value in palette.values())
    text = [palette[role] for role in colors.TEXT_ROLES]
    assert len(set(text)) == len(text)  # one meaning, one colour


def _luminance(hex_colour):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    light, dark = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("name", sorted(colors.PALETTES))
def test_every_text_colour_reads_on_every_background(name):
    """WCAG AA for normal text (4.5:1) on the map, the panels and the highlight."""
    palette = colors.PALETTES[name]
    weak = [(text, back, round(contrast(palette[text], palette[back]), 2))
            for text in colors.TEXT_ROLES for back in colors.BACKGROUND_ROLES
            if contrast(palette[text], palette[back]) < 4.5]
    assert weak == []


def test_use_switches_every_name():
    colors.PALETTES["test"] = dict(colors.PALETTES["dark"], TYPE="#123456")
    try:
        colors.use("test")
        assert colors.TYPE == "#123456" and colors.current == "test"
    finally:
        colors.use("dark")
        del colors.PALETTES["test"]

"""Focused tests for backend.text_format (FO2, docs/FILE_OUTPUT_BUILD_PLAN.md).

Run from AttackOfTheNodes/:
    python -m pytest tests/test_text_format.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.text_format import format_markdown  # noqa: E402


def test_empty_input_stays_empty():
    assert format_markdown("") == ""
    assert format_markdown("\n\n\n") == ""


def test_line_endings_and_trailing_whitespace_normalize():
    text = "alpha  \r\nbeta\r\ngamma\t\n"
    assert format_markdown(text) == "alpha\nbeta\ngamma\n"


def test_headings_get_space_and_surrounding_blank_lines():
    text = "intro\n##Heading##\nbody text"
    assert format_markdown(text) == "intro\n\n## Heading\n\nbody text\n"


def test_heading_hash_run_is_preserved():
    assert format_markdown("###   Deep Title").strip() == "### Deep Title"


def test_bullet_markers_normalize_to_dash():
    text = "* one\n+ two\n- three\n  * nested"
    assert format_markdown(text) == "- one\n- two\n- three\n  - nested\n"


def test_emphasis_at_line_start_is_not_a_bullet():
    assert format_markdown("*emphasis* stays").strip() == "*emphasis* stays"


def test_ordered_items_normalize_marker_spacing():
    text = "1)  first\n2.   second"
    assert format_markdown(text) == "1. first\n2. second\n"


def test_blank_line_runs_collapse():
    text = "one\n\n\n\ntwo"
    assert format_markdown(text) == "one\n\ntwo\n"


def test_table_columns_align():
    text = "| Name | Qty |\n|---|---|\n| apples | 12 |\n| plum | 1 |"
    assert format_markdown(text) == (
        "| Name   | Qty |\n"
        "| ------ | --- |\n"
        "| apples | 12  |\n"
        "| plum   | 1   |\n"
    )


def test_table_alignment_markers_survive():
    text = "| L | C | R |\n|:--|:-:|--:|\n| a | b | c |"
    out = format_markdown(text)
    separator = out.split("\n")[1]
    cells = [cell.strip() for cell in separator.strip("|").split("|")]
    assert cells[0].startswith(":") and not cells[0].endswith(":")
    assert cells[1].startswith(":") and cells[1].endswith(":")
    assert not cells[2].startswith(":") and cells[2].endswith(":")


def test_fenced_code_blocks_pass_through_untouched():
    code = "```python\n#not a heading\n* not  a  bullet\nx = 1   \n```"
    out = format_markdown(f"before\n{code}\nafter")
    assert "#not a heading" in out
    assert "* not  a  bullet" in out
    assert "x = 1   \n" in out


def test_wrap_reflows_plain_paragraphs_only():
    text = (
        "# Title\n"
        "this is a long paragraph that should be re-flowed to a narrow width for reading\n"
        "- a list item that is also quite long and must not be wrapped by the formatter\n"
    )
    out = format_markdown(text, wrap_width=30)
    lines = out.split("\n")
    assert "# Title" in lines
    for line in lines:
        if line.startswith("- "):
            assert "must not be wrapped" in line
        elif line and not line.startswith("#"):
            assert len(line) <= 30


def test_wrap_joins_adjacent_paragraph_lines():
    text = "one two\nthree four"
    assert format_markdown(text, wrap_width=80) == "one two three four\n"


def test_zero_wrap_keeps_existing_breaks():
    text = "one two\nthree four"
    assert format_markdown(text) == "one two\nthree four\n"


def test_messy_llm_output_end_to_end():
    messy = (
        "##Summary\r\n"
        "\r\n"
        "\r\n"
        "*  first point   \r\n"
        "+ second point\r\n"
        "| a | b |\r\n"
        "|--|--|\r\n"
        "| 1 | 22 |\r\n"
    )
    out = format_markdown(messy)
    assert out == (
        "## Summary\n"
        "\n"
        "- first point\n"
        "- second point\n"
        "\n"
        "| a   | b   |\n"
        "| --- | --- |\n"
        "| 1   | 22  |\n"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

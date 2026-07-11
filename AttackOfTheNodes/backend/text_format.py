"""Human-friendly Markdown/text formatting (FO2, docs/FILE_OUTPUT_BUILD_PLAN.md).

Pure string→string helpers with no node or runtime coupling, so a workflow
can pipe LLM or raw text through a formatter before writing (FO1) or viewing
(FO3) it. Exposed to workflows as the `markdown format` operation on
`text_transform_node`.

Deliberately conservative: it normalizes structure that renders poorly
(heading spacing, bullet markers, ragged tables, blank-line runs) and never
touches fenced code blocks. It does not attempt full CommonMark
canonicalization.
"""

from __future__ import annotations

import re
import textwrap
from typing import List


_HEADING_RE = re.compile(r"^(#{1,6})\s*(.*?)\s*#*\s*$")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{1,}:?$")
_FENCE_RE = re.compile(r"^(\s*)(```|~~~)")


def format_markdown(text: str, wrap_width: int = 0) -> str:
    """Return *text* tidied for human reading as Markdown.

    - Line endings normalized to ``\\n``; trailing whitespace stripped.
    - ATX headings get one space after the hashes, closing hashes dropped,
      and one blank line before and after.
    - Bullet markers normalize to ``- ``; ordered items to ``N. ``.
    - Table blocks align their pipes to uniform column widths (separator
      rows keep their ``:`` alignment markers).
    - Runs of blank lines collapse to one.
    - With ``wrap_width > 0``, plain paragraphs re-flow to that width.
      Headings, lists, tables, blockquotes, and code are never wrapped.
    - Fenced code blocks (``` or ~~~) pass through untouched.
    - Output ends with exactly one trailing newline (empty input stays "").
    """
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    normalized: List[str] = []
    in_fence = False
    fence_marker = ""
    for line in lines:
        fence = _FENCE_RE.match(line)
        if in_fence:
            normalized.append(line)
            if fence and fence.group(2) == fence_marker:
                in_fence = False
            continue
        if fence:
            in_fence = True
            fence_marker = fence.group(2)
            normalized.append(line.rstrip())
            continue
        normalized.append(_normalize_line(line.rstrip()))

    normalized = _align_tables(normalized)
    if wrap_width > 0:
        normalized = _wrap_paragraphs(normalized, wrap_width)
    normalized = _space_headings(normalized)
    normalized = _collapse_blank_runs(normalized)

    body = "\n".join(normalized).strip("\n")
    return body + "\n" if body else ""


def _normalize_line(line: str) -> str:
    heading = _HEADING_RE.match(line)
    if heading:
        title = heading.group(2)
        return f"{heading.group(1)} {title}" if title else heading.group(1)
    bullet = _BULLET_RE.match(line)
    if bullet:
        return f"{bullet.group(1)}- {bullet.group(2)}"
    ordered = _ORDERED_RE.match(line)
    if ordered:
        return f"{ordered.group(1)}{ordered.group(2)}. {ordered.group(3)}"
    return line


def _is_protected(line: str) -> bool:
    """Lines that must never be merged into or wrapped as paragraph text."""
    stripped = line.strip()
    if not stripped:
        return True
    return (
        stripped.startswith("#")
        or stripped.startswith(">")
        or bool(_BULLET_RE.match(line))
        or bool(_ORDERED_RE.match(line))
        or bool(_TABLE_ROW_RE.match(line))
        or bool(_FENCE_RE.match(line))
        or line.startswith("    ")  # indented code
    )


def _wrap_paragraphs(lines: List[str], width: int) -> List[str]:
    out: List[str] = []
    paragraph: List[str] = []
    in_fence = False

    def flush() -> None:
        if paragraph:
            out.extend(textwrap.wrap(" ".join(paragraph), width) or [""])
            paragraph.clear()

    for line in lines:
        if _FENCE_RE.match(line):
            flush()
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or _is_protected(line):
            flush()
            out.append(line)
            continue
        paragraph.append(line.strip())
    flush()
    return out


def _space_headings(lines: List[str]) -> List[str]:
    out: List[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence and _HEADING_RE.match(line):
            if out and out[-1].strip():
                out.append("")
            out.append(line)
            out.append("")
            continue
        out.append(line)
    return out


def _collapse_blank_runs(lines: List[str]) -> List[str]:
    out: List[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence and not line.strip() and out and not out[-1].strip():
            continue
        out.append(line)
    return out


def _align_tables(lines: List[str]) -> List[str]:
    out: List[str] = []
    block: List[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence and _TABLE_ROW_RE.match(line):
            block.append(line)
            continue
        if block:
            _flush_table_block(out, block)
            block = []
        out.append(line)
    if block:
        _flush_table_block(out, block)
    return out


def _flush_table_block(out: List[str], block: List[str]) -> None:
    aligned = _align_table_block(block)
    if len(aligned) >= 2 and out and out[-1].strip():
        # A table butted against preceding text (often a list) is absorbed
        # into it by most renderers; give it room.
        out.append("")
    out.extend(aligned)


def _align_table_block(block: List[str]) -> List[str]:
    if len(block) < 2:
        return block
    rows = [_split_table_row(line) for line in block]
    columns = max(len(row) for row in rows)
    widths = [0] * columns
    for row in rows:
        for index, cell in enumerate(row):
            if not _TABLE_SEPARATOR_CELL_RE.match(cell):
                widths[index] = max(widths[index], len(cell))
    widths = [max(width, 3) for width in widths]

    aligned: List[str] = []
    for row in rows:
        cells: List[str] = []
        for index in range(columns):
            cell = row[index] if index < len(row) else ""
            if _TABLE_SEPARATOR_CELL_RE.match(cell):
                left = ":" if cell.startswith(":") else "-"
                right = ":" if cell.endswith(":") else "-"
                cells.append(left + "-" * max(widths[index] - 2, 1) + right)
            else:
                cells.append(cell.ljust(widths[index]))
        aligned.append("| " + " | ".join(cells) + " |")
    return aligned


def _split_table_row(line: str) -> List[str]:
    inner = line.strip().strip("|")
    return [cell.strip() for cell in inner.split("|")]

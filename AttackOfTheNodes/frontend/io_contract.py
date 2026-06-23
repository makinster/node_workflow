"""Shared rendering helpers for the per-port I/O contract panels.

Both the node selector (generic contract) and the editor details panel
(configured instance) render ports in the same visual language: a
``name  [type]`` line, a dim description, and a ``└─<``/``└─>`` source or
destination line. These helpers keep that language identical across screens.
"""

from __future__ import annotations

import textwrap
from typing import Any, Callable, Dict, List

# VS Code Dark+ teal, used for the bracketed [type] labels.
TYPE_COLOR = "#4EC9B0"

# Pre-layout wrap width used before a panel has been measured (and by unmounted
# screens in tests). Both contract panels share it so they wrap identically.
DETAIL_WIDTH_FALLBACK = 36

# The pass-through output marker, shared so both panels render it the same way.
PASS_THROUGH_LINE = "  [bold]↔ pass-thru[/bold]"

# A callable that wraps prose with a hanging indent: (text, indent, prefix).
WrapFn = Callable[[str, int, str], List[str]]


def type_label(data_type: str) -> str:
    """Return a Rich-markup ``[type]`` label: literal brackets, teal type."""
    return f"\\[[{TYPE_COLOR}]{data_type}[/]]"


def render_port_block(
    name: str,
    data_type: str,
    description: str,
    flow_lines: List[str],
    wrap: WrapFn,
) -> List[str]:
    """Render one port in the shared style: ``name  [type]`` / dim description /
    flow line(s). Empty description/flow are omitted. ``flow_lines`` is already
    built (it differs per screen — allowed kinds vs configured wiring)."""
    block = [f"  {name}  {type_label(data_type)}"]
    if description:
        block.extend(wrap(description, 2, ""))
    block.extend(flow_lines)
    return block


def metadata_flow_lines(meta: Dict[str, Any], direction: str, wrap: WrapFn) -> List[str]:
    """The ``└─<`` sources / ``└─>`` dests / ``↔ pass-thru`` line(s) derived
    purely from a port's metadata (the generic contract). Returns a possibly
    empty list. Editors use this as the fallback when a port is unwired."""
    if direction == "input":
        sources = meta.get("sources") or meta.get("from") or []
        if sources:
            return wrap(" ".join(str(s) for s in sources), 2, "└─< ")
        return []
    if meta.get("pass_through"):
        return [PASS_THROUGH_LINE]
    dests = meta.get("to") or []
    if dests:
        return wrap(" ".join(str(d) for d in dests), 2, "└─> ")
    return []


def wrap_dim(text: str, width: int, indent: int = 0, prefix: str = "") -> List[str]:
    """Wrap dim prose so continuation lines align under the first word.

    ``indent`` is the leading-space column for the line; ``prefix`` (e.g.
    ``"└─< "``) renders only on the first line and the wrap hangs to the column
    immediately after it. Pre-wrapping here (rather than letting a Static
    soft-wrap) is what preserves the hanging indent — a Static's own wrapping
    always falls back to column 0. Callers should pass a ``width`` a hair under
    the laid-out panel width so the Static never re-wraps these lines.
    """
    avail = max(6, width - indent - len(prefix))
    chunks = textwrap.wrap(text, avail) or [""]
    lines: List[str] = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            lines.append(f"{' ' * indent}[dim]{prefix}{chunk}[/dim]")
        else:
            lines.append(f"{' ' * (indent + len(prefix))}[dim]{chunk}[/dim]")
    return lines

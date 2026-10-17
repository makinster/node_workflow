"""Turn a pasted or dropped string into Stash candidates (Stash S1).

Terminals deliver a file drop as text, and each one quotes it differently:
Windows Terminal into WSL sends ``"C:\\Users\\me\\a b.txt"`` (quoted only when
needed), Linux terminals send ``'/home/me/a b.txt'`` or ``/home/me/a\\ b.txt``,
and some send ``file:///home/me/a%20b.txt``. Several files arrive separated
by spaces or newlines.

The rule (STASH_PROPOSAL.md §9.7):

- Split the paste into pieces, honouring quotes and backslash escapes.
- If **every** piece looks like a path (absolute, ``~/``, a Windows drive or
  UNC path, or a ``file://`` URI), each one is resolved on this machine:
  an existing file becomes a file candidate; anything else is reported, not
  stored (a path from another machine is common over SSH).
- Otherwise the whole paste is one text candidate, so prose that mentions a
  path stays text.

No Textual imports: the Stash modal, the CLI and later callers share this.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import unquote, urlparse

from .file_paths import normalize_local_path

_WINDOWS_START = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")
# Characters a POSIX terminal escapes with a backslash in a dropped path.
_ESCAPABLE = set(" \t'\"()&;$`!*?[]{}<>|#~=,\\")


@dataclass
class Rejected:
    """A path-like piece that can't be stored, and why."""

    piece: str
    reason: str


@dataclass
class PasteResult:
    """What a paste turns into. At most one of ``files``/``text`` is used:
    a path paste fills ``files`` and ``rejected``; anything else is ``text``."""

    files: List[Path] = field(default_factory=list)
    rejected: List[Rejected] = field(default_factory=list)
    text: Optional[str] = None

    @property
    def empty(self) -> bool:
        return not self.files and not self.rejected and self.text is None


def split_pieces(text: str) -> List[Tuple[str, bool]]:
    """Split a paste into ``(piece, quoted_or_escaped)`` pairs.

    Quotes group a piece; a backslash escapes the next character in POSIX
    pieces only. A piece that starts like a Windows path keeps its
    backslashes, since Windows Terminal quotes a path with spaces instead.
    """
    pieces: List[Tuple[str, bool]] = []
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        windows = bool(_WINDOWS_START.match(text[i:])) or (
            text[i] in "\"'" and bool(_WINDOWS_START.match(text[i + 1:]))
        )
        chars: List[str] = []
        marked = False
        while i < n and not text[i].isspace():
            char = text[i]
            if char in "\"'":
                close = text.find(char, i + 1)
                if close == -1:  # unbalanced: keep the quote literally
                    chars.append(char)
                    i += 1
                    continue
                chars.append(text[i + 1:close])
                marked = True
                i = close + 1
                continue
            if char == "\\" and not windows and i + 1 < n and text[i + 1] in _ESCAPABLE:
                chars.append(text[i + 1])
                marked = True
                i += 2
                continue
            chars.append(char)
            i += 1
        pieces.append(("".join(chars), marked))
    return pieces


def looks_like_path(piece: str) -> bool:
    """Absolute, home-relative, Windows drive/UNC, or a file:// URI."""
    return (
        piece.startswith("/")
        or piece == "~"
        or piece.startswith("~/")
        or bool(_WINDOWS_START.match(piece))
        or piece.lower().startswith("file://")
    )


def resolve_piece(piece: str) -> Path:
    """The local path a path-like piece names; ValueError when it can't."""
    if piece.lower().startswith("file://"):
        parsed = urlparse(piece)
        if parsed.netloc not in ("", "localhost"):
            raise ValueError(f"file URI names another host ({parsed.netloc})")
        piece = unquote(parsed.path)
        # file:///C:/Users/... carries a leading slash before the drive.
        if re.match(r"^/[A-Za-z]:/", piece):
            piece = piece[1:]
    if piece == "~" or piece.startswith("~/"):
        return Path(piece).expanduser()
    return normalize_local_path(piece)


def parse_paste(text: str) -> PasteResult:
    """Apply the paste rule above to ``text``."""
    result = PasteResult()
    if not text or not text.strip():
        return result
    pieces = [piece for piece, _ in split_pieces(text) if piece]
    if not pieces or not all(looks_like_path(piece) for piece in pieces):
        result.text = text.strip()
        return result
    for piece in pieces:
        try:
            path = resolve_piece(piece)
        except ValueError as exc:
            result.rejected.append(Rejected(piece, str(exc)))
            continue
        if path.is_dir():
            result.rejected.append(Rejected(piece, "is a folder; folder import comes later (S4)"))
        elif not path.is_file():
            result.rejected.append(Rejected(piece, "not found on this machine"))
        elif path not in result.files:
            result.files.append(path)
    return result

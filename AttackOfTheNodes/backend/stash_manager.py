"""The Stash: machine-local reusable paths and text (Stash S1).

Entries live outside every workflow, in ``<data dir>/stash/entries.json``, so
the same workflow can run on another machine after its inputs are re-pointed
(STASH_PROPOSAL.md). An entry is::

    {"id": "stash_8f3a1c2d9e0b", "name": "march_report", "type": "file",
     "value": {"type": "file", "ref_key": "file:/…/march.csv", "path": "/…/march.csv"},
     "group": null, "created": "2026-10-17T…Z", "updated": "…"}

- ``id`` is generated and never changes, so a later binding survives renames.
- ``type`` is a canonical data type: ``file`` (a file reference) or
  ``string`` (the text itself).
- ``group`` is reserved for folder import (S4).
- Names are trimmed, not blank and unique ignoring case.

Secrets don't belong here; they stay in ``SecretsManager``. Text that looks
like a key is accepted but warned about, on add and on export.

No Textual imports: the Stash modal, the CLI and contract bindings share it.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import persistence
from .file_refs import file_reference, reference_path
from .paste_parser import PasteResult, looks_like_path, parse_paste, resolve_piece

FORMAT = "aotn-stash/1"
ENTRY_TYPES = ("file", "string")
ENTRIES_FILE = "entries.json"

_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]", re.IGNORECASE),
)


class StashError(ValueError):
    """A Stash request that can't be done; the message says why."""


class StashDuplicate(StashError):
    """The value is already stashed; ``entry`` is the existing entry.

    Owner, 2026-10-17: the same file (or text) is the same reference, so it
    never gets a second entry; callers show "Duplicate found" instead.
    """

    def __init__(self, entry: Dict[str, Any]) -> None:
        super().__init__(f"Duplicate found: already in the Stash as '{entry['name']}'")
        self.entry = entry


def duplicates_message(entries: List[Dict[str, Any]]) -> str:
    """The short notice for a paste that found entries already stashed."""
    names = ", ".join(f"'{e['name']}'" for e in entries)
    if len(entries) == 1:
        return f"Duplicate found: {names}"
    return f"{len(entries)} duplicates found: {names}"


def looks_like_secret(text: str) -> bool:
    """A cheap guess that ``text`` holds a key or password."""
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class StashManager:
    """CRUD, type checks and versioned JSON export/import for the Stash."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._dir = Path(storage_dir) if storage_dir is not None else persistence.STASH_DIR
        self._entries: Optional[List[Dict[str, Any]]] = None

    @property
    def path(self) -> Path:
        return self._dir / ENTRIES_FILE

    # -- reading ---------------------------------------------------------------

    def list_entries(self, entry_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Entries sorted by name, optionally only one type."""
        entries = [dict(e) for e in self._load()
                   if entry_type is None or e["type"] == entry_type]
        return sorted(entries, key=lambda e: e["name"].casefold())

    def get(self, id_or_name: str) -> Optional[Dict[str, Any]]:
        """An entry by id, or by name ignoring case."""
        wanted = id_or_name.strip()
        for entry in self._load():
            if entry["id"] == wanted:
                return dict(entry)
        for entry in self._load():
            if entry["name"].casefold() == wanted.casefold():
                return dict(entry)
        return None

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """An entry by name only, ignoring case. Inputs refer to entries by
        name (4d), so a name never resolves to another entry's id."""
        wanted = name.strip().casefold()
        for entry in self._load():
            if entry["name"].casefold() == wanted:
                return dict(entry)
        return None

    def name_problem(self, name: str, exclude_id: Optional[str] = None) -> Optional[str]:
        """Why ``name`` can't be used, or None (for a rename prompt)."""
        try:
            self._check_name(name, exclude_id)
        except StashError as exc:
            return str(exc)
        return None

    def warnings_for(self, entry: Dict[str, Any]) -> List[str]:
        """Things the user should know about an entry (never blocking)."""
        if entry["type"] == "string" and looks_like_secret(str(entry["value"])):
            return [f"'{entry['name']}' looks like a key or password; secrets belong "
                    "in Settings > Secrets, not the Stash"]
        if entry["type"] == "file" and not Path(reference_path(entry["value"])).is_file():
            return [f"'{entry['name']}': {reference_path(entry['value'])} is not on this machine"]
        return []

    # -- changing --------------------------------------------------------------

    def add_file(self, path: str | Path, name: Optional[str] = None) -> Dict[str, Any]:
        """Add an existing file. ``path`` is one path in any form a paste
        accepts (quoted, escaped, Windows, ``file://``); an argument the
        shell already unquoted (spaces and all) is tried whole first."""
        if isinstance(path, Path):
            candidate: Optional[Path] = path
        else:
            candidate = _whole_path(path)
            if candidate is None:
                result = parse_paste(path)
                if result.rejected:
                    raise StashError(f"{result.rejected[0].piece}: {result.rejected[0].reason}")
                if len(result.files) != 1:
                    raise StashError("Give exactly one existing file path")
                candidate = result.files[0]
        resolved = candidate.expanduser().resolve()
        if resolved.is_dir():
            raise StashError(f"{resolved}: is a folder; folder import comes later (S4)")
        if not resolved.is_file():
            raise StashError(f"{resolved}: not found on this machine")
        self._refuse_duplicate("file", str(resolved))
        # Another file with the same name is told apart by its folder.
        default = resolved.stem
        if self._name_taken(default):
            default = f"{resolved.stem} ({resolved.parent.name})"
        return self._add("file", file_reference(str(resolved)), name, default=default)

    def add_text(self, text: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Add a piece of reusable text."""
        if not text.strip():
            raise StashError("Text can't be blank")
        self._refuse_duplicate("string", text)
        return self._add("string", text, name, default=_default_text_name(text))

    def add_paste(self, text: str) -> tuple[List[Dict[str, Any]], PasteResult]:
        """Store what a paste turns into: one entry per existing file, or one
        text entry. Rejected paths are returned, never stored."""
        result = parse_paste(text)
        added: List[Dict[str, Any]] = []
        values = [("string", result.text)] if result.text is not None else [("file", p) for p in result.files]
        for kind, value in values:
            try:
                added.append(self.add_text(value) if kind == "string" else self.add_file(value))
            except StashDuplicate as duplicate:
                result.duplicates.append(duplicate.entry)
        return added, result

    def rename(self, id_or_name: str, new_name: str) -> Dict[str, Any]:
        entry = self._require(id_or_name)
        name = self._check_name(new_name, exclude_id=entry["id"])
        return self._update(entry["id"], name=name)

    def remove(self, id_or_name: str) -> Dict[str, Any]:
        entry = self._require(id_or_name)
        self._entries = [e for e in self._load() if e["id"] != entry["id"]]
        self._save()
        return entry

    # -- export / import -------------------------------------------------------

    def export_data(self) -> Dict[str, Any]:
        """The versioned export document (``aotn-stash/1``)."""
        return {"format": FORMAT, "exported": _now(), "entries": self.list_entries()}

    def export_to(self, path: str | Path) -> List[str]:
        """Write the export to ``path``; return warnings (key-like text)."""
        data = self.export_data()
        persistence.write_json_atomic(Path(path).expanduser(), data)
        return [w for e in data["entries"] if e["type"] == "string" for w in self.warnings_for(e)]

    def import_from(self, path: str | Path) -> Dict[str, List[str]]:
        """Merge an export into this Stash.

        Returns ``added`` and ``skipped`` (each a list of readable lines). An
        entry already here (same id) is skipped; a name already used by
        another entry gets a number; a file missing on this machine is
        skipped, so nothing points at a path that isn't here.
        """
        try:
            data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StashError(f"Cannot read {path}: {exc}") from exc
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise StashError(f"{path} is not a Stash export (expected format {FORMAT!r})")
        if not isinstance(data.get("entries"), list):
            raise StashError(f"{path} has no entries list")
        added: List[str] = []
        skipped: List[str] = []
        for raw in data["entries"]:
            problem = _entry_problem(raw)
            if problem:
                skipped.append(problem)
                continue
            if any(e["id"] == raw["id"] for e in self._load()):
                skipped.append(f"{raw['name']}: already in the Stash")
                continue
            same = self.find_same(raw["type"], raw["value"])
            if same is not None:
                skipped.append(f"{raw['name']}: duplicate of '{same['name']}'")
                continue
            if raw["type"] == "file" and not Path(reference_path(raw["value"])).is_file():
                skipped.append(f"{raw['name']}: {reference_path(raw['value'])} is not on this machine")
                continue
            entry = {
                "id": raw["id"], "name": self._unique_name(raw["name"]), "type": raw["type"],
                "value": raw["value"], "group": raw.get("group"),
                "created": raw.get("created") or _now(), "updated": _now(),
            }
            self._load().append(entry)
            added.append(entry["name"] if entry["name"] == raw["name"].strip()
                         else f"{raw['name']} (as {entry['name']})")
        if added:
            self._save()
        return {"added": added, "skipped": skipped}

    # -- internals -------------------------------------------------------------

    def _add(self, entry_type: str, value: Any, name: Optional[str], *, default: str) -> Dict[str, Any]:
        """A chosen name must be free; a default one gets a number if not."""
        stamp = _now()
        entry = {
            "id": f"stash_{uuid.uuid4().hex[:12]}",
            "name": self._check_name(name) if name is not None else self._unique_name(default),
            "type": entry_type,
            "value": value,
            "group": None,
            "created": stamp,
            "updated": stamp,
        }
        self._load().append(entry)
        self._save()
        return dict(entry)

    def _update(self, entry_id: str, **changes: Any) -> Dict[str, Any]:
        for entry in self._load():
            if entry["id"] == entry_id:
                entry.update(changes, updated=_now())
                self._save()
                return dict(entry)
        raise StashError(f"No Stash entry {entry_id!r}")

    def find_same(self, entry_type: str, value: Any) -> Optional[Dict[str, Any]]:
        """The entry already holding this value: the same file path, or the
        same text ignoring surrounding whitespace."""
        wanted = _comparable(entry_type, value)
        for entry in self._load():
            if entry["type"] == entry_type and _comparable(entry_type, entry["value"]) == wanted:
                return dict(entry)
        return None

    def _refuse_duplicate(self, entry_type: str, value: Any) -> None:
        same = self.find_same(entry_type, value)
        if same is not None:
            raise StashDuplicate(same)

    def _require(self, id_or_name: str) -> Dict[str, Any]:
        entry = self.get(id_or_name)
        if entry is None:
            raise StashError(f"No Stash entry named or with id {id_or_name!r}")
        return entry

    def _check_name(self, name: str, exclude_id: Optional[str] = None) -> str:
        name = name.strip()
        if not name:
            raise StashError("Name can't be blank")
        if self._name_taken(name, exclude_id):
            raise StashError(f"A Stash entry is already named '{name}'")
        return name

    def _name_taken(self, name: str, exclude_id: Optional[str] = None) -> bool:
        return any(e["name"].casefold() == name.casefold() and e["id"] != exclude_id
                   for e in self._load())

    def _unique_name(self, base: str) -> str:
        base = base.strip() or "entry"
        candidate, number = base, 2
        while self._name_taken(candidate):
            candidate, number = f"{base} {number}", number + 1
        return candidate

    def _load(self) -> List[Dict[str, Any]]:
        if self._entries is None:
            self._entries = []
            if self.path.exists():
                try:
                    data = json.loads(self.path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    # Never overwrite a file we couldn't read.
                    raise StashError(f"Cannot read the Stash at {self.path}: {exc}") from exc
                self._entries = [e for e in data.get("entries", []) if not _entry_problem(e)]
        return self._entries

    def _save(self) -> None:
        persistence.write_json_atomic(self.path, {"format": FORMAT, "entries": self._load()})


def preview(entry: Dict[str, Any], width: int = 60) -> str:
    """One-line value preview: a path keeps its end (the file name), text
    keeps its start. Shared by the CLI and the Stash screen."""
    shown = reference_path(entry["value"]) if entry["type"] == "file" else str(entry["value"])
    shown = " ".join(shown.split())
    if len(shown) <= width:
        return shown
    return "..." + shown[-(width - 3):] if entry["type"] == "file" else shown[:width - 3] + "..."


#: ``aotn run --input key=@stash:name`` reads the value from a Stash entry (4d).
STASH_REF_PREFIX = "@stash:"


def stash_ref_name(text: Any) -> Optional[str]:
    """The entry name in an ``@stash:name`` value (quotes allowed), or None."""
    if not isinstance(text, str) or not text.startswith(STASH_REF_PREFIX):
        return None
    name = text[len(STASH_REF_PREFIX):].strip()
    # Only one matching outer pair: quotes inside a name (Managers') stay.
    if len(name) >= 2 and name[0] == name[-1] and name[0] in "\"'":
        name = name[1:-1].strip()
    return name


def input_value(entry: Dict[str, Any]) -> Any:
    """An entry as a run input: a file reference, or its text (which the
    caller parses by the input's type, like typed text)."""
    if entry["type"] == "file":
        return json.loads(json.dumps(entry["value"]))
    return str(entry["value"])


def type_word(entry_type: str) -> str:
    """What people read for a type: the canonical name, the same word as in
    every other type label (owner, 2026-10-20: "string", never "text")."""
    return entry_type


def _entry_problem(raw: Any) -> Optional[str]:
    """Why ``raw`` isn't a valid entry, or None."""
    if not isinstance(raw, dict):
        return "an entry that isn't an object"
    name = str(raw.get("name") or "").strip() or "(unnamed)"
    if not str(raw.get("id") or "").startswith("stash_"):
        return f"{name}: missing or invalid id"
    if not str(raw.get("name") or "").strip():
        return f"{raw.get('id')}: blank name"
    if raw.get("type") not in ENTRY_TYPES:
        return f"{name}: unsupported type {raw.get('type')!r}"
    if raw["type"] == "file" and not reference_path(raw.get("value")):
        return f"{name}: file entry without a path"
    if raw["type"] == "string" and not isinstance(raw.get("value"), str):
        return f"{name}: text entry without text"
    return None


def _comparable(entry_type: str, value: Any) -> str:
    if entry_type == "file":
        return reference_path(value) if not isinstance(value, str) else value.strip()
    return str(value).strip()


def _whole_path(value: str) -> Optional[Path]:
    """``value`` as one existing path, or None to fall back to paste parsing."""
    stripped = value.strip()
    if not looks_like_path(stripped.strip("\"'")):
        return None
    try:
        path = resolve_piece(stripped.strip("\"'"))
    except ValueError:
        return None
    return path if path.exists() else None


def _default_text_name(text: str) -> str:
    """The first few words, so an unnamed entry is recognisable."""
    words = text.split()
    name = " ".join(words[:4])
    return name[:40].rstrip() or "text"

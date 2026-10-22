"""Saved values: what a workflow keeps for its next run (C2).

Built on the Stash's store: the same folder (``<data dir>/stash``), the same
atomic writes, the same screen (tab 3) and the same CLI (``aotn stash saved``).
A separate file, ``saved.json``, because Stash entries refuse duplicate values
and saved values change on every run. A value is::

    {"id": "saved_3f9a0c1b2d4e", "name": "last_version",
     "place": {"kind": "workflow", "workflow": "hermes-release-watch"},
     "type": "string", "value": "v0.14.2",
     "created": "2026-10-20T16:00:02Z", "updated": "2026-10-21T16:00:03Z",
     "saved_by": {"node": "New version?", "node_id": "node_39e9571a",
                  "run_id": "run_8c1d…", "from": "command line"}}

- ``place`` is ``{"kind": "workflow", "workflow": <name>}`` (only that
  workflow; owner, 2026-10-21: values follow the workflow's name, so a cron
  workflow rebuilt from its spec keeps them) or ``{"kind": "all"}``.
- ``type`` is a ``data_types`` name: string, number, bool, var or file.
- Names are trimmed, not blank, and unique ignoring case within a place.

Two runs at once (cron and the app): reads always go to the file (no cache);
each change is one locked step (``saved.lock``): re-read, change one value,
write atomically. Different names never overwrite each other; for the same
name the later write wins. Add and If changed compare-and-save are one step,
so counters don't lose counts and two runs can't both report one change.

No Textual imports: the nodes, the Stash screen and the CLI share it.
"""

from __future__ import annotations

import json
import math
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from . import persistence
from .file_refs import is_file_reference

# One of these locks every change; with neither, changes are refused (never an
# unlocked read-modify-write).
try:  # Linux and macOS
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]
try:  # Windows
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore[assignment]

#: How long a change waits for another process's lock (seconds).
LOCK_WAIT = 10.0

FORMAT = "aotn-saved/1"
VALUES_FILE = "saved.json"
LOCK_FILE = "saved.lock"
SAVED_TYPES = ("string", "number", "bool", "var", "file")
MAX_BYTES = 64 * 1024
ALL = "all"
WORKFLOW = "workflow"

#: Error codes worth a retry (the file was busy or briefly unreadable).
RETRYABLE = frozenset({"store_unwritable", "store_unreadable"})

#: Where runs in this process come from: "app", "command line" or "MCP".
#: Each entry point sets it once; the app is the default.
RUN_FROM = "app"


class SavedValuesError(ValueError):
    """A request that can't be done; ``code`` is the node error code."""

    def __init__(self, message: str, code: str = "store_unwritable") -> None:
        super().__init__(message)
        self.code = code


def workflow_place(name: str) -> Dict[str, str]:
    return {"kind": WORKFLOW, "workflow": str(name or "").strip()}


def all_place() -> Dict[str, str]:
    return {"kind": ALL}


def place_for(keep_for: Any, workflow_name: str) -> Dict[str, str]:
    """A node's "Kept for" choice as a place."""
    return all_place() if keep_for == "All workflows" else workflow_place(workflow_name)


def place_label(place: Dict[str, Any]) -> str:
    """What people read for a place: the workflow's name, or All workflows.
    A workflow that is itself named "All workflows" is told apart."""
    if place.get("kind") == ALL:
        return "All workflows"
    name = str(place.get("workflow") or "")
    if not name:
        return "(no workflow)"
    return f"{name} (workflow)" if name.casefold() == "all workflows" else name


def place_key(place: Dict[str, Any]) -> Tuple[str, str]:
    """A place's identity, for grouping and filtering (never its label)."""
    if place.get("kind") == ALL:
        return (ALL, "")
    return (WORKFLOW, str(place.get("workflow") or ""))


def type_of(value: Any) -> str:
    """The saved type of a value."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if is_file_reference(value):
        return "file"
    return "var"


def same_value(a: Any, b: Any, loosely: bool = False) -> bool:
    """Exactly: the same JSON value. Loosely: the same text ignoring spaces
    and capitals."""
    if loosely:
        return _loose_text(a) == _loose_text(b)
    return _canonical(a) == _canonical(b)


def parse_typed(text: str, value_type: str) -> Any:
    """Typed text (the Stash screen's Change, the CLI's set) as a value."""
    if value_type == "string":
        return text
    if value_type == "number":
        for convert in (int, float):
            try:
                number = convert(text.strip())
            except ValueError:
                continue
            if isinstance(number, float) and not math.isfinite(number):
                break
            return number
        raise SavedValuesError(f"{text!r} is not a number", "wrong_type")
    if value_type == "bool":
        word = text.strip().casefold()
        if word in ("true", "yes", "1"):
            return True
        if word in ("false", "no", "0"):
            return False
        raise SavedValuesError(f"{text!r} is not yes or no", "wrong_type")
    if value_type not in ("var", "file"):
        raise SavedValuesError(f"Unknown type {value_type!r}", "wrong_type")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SavedValuesError(f"Not valid JSON: {exc}", "wrong_type") from None
    if type_of(value) != value_type:
        wanted = "a file reference" if value_type == "file" else "a JSON list or record"
        raise SavedValuesError(f"{text!r} is not {wanted}", "wrong_type")
    return value


def saved_by(context: Any) -> Dict[str, str]:
    """Which node and run saved a value, and where the run came from."""
    return {
        "node": str(getattr(context, "node_alias", "") or ""),
        "node_id": str(getattr(context, "node_id", "") or ""),
        "run_id": str(getattr(context, "run_id", "") or ""),
        "from": RUN_FROM,
    }


def node_value(node: Any, context: Any) -> Any:
    """A node's Value input: the incoming payload, a Vault key, or the
    Configured text."""
    source = node.config.get("input_source")
    if source == "Vault":
        key = str(node.config.get("input_vault_key") or "").strip()
        return context.memory_bank.read_persistent(key) if key else None
    if source == "Configured":
        return str(node.config.get("value") or "")
    return context.inputs.get("input")


def preview(record: Dict[str, Any], width: int = 40) -> str:
    """One-line value preview for the screen and the CLI."""
    value = record.get("value")
    if record.get("type") == "file":
        from .file_refs import reference_path
        shown = reference_path(value)
    elif isinstance(value, str):
        shown = value
    else:
        shown = json.dumps(value, ensure_ascii=False)
    shown = " ".join(shown.split())
    if len(shown) <= width:
        return shown
    return shown[: width - 3] + "..."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _loose_text(value: Any) -> str:
    text = value if isinstance(value, str) else _canonical(value)
    return "".join(text.split()).casefold()


def _same_place(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    if a.get("kind") != b.get("kind"):
        return False
    return a.get("kind") == ALL or str(a.get("workflow") or "") == str(b.get("workflow") or "")


class SavedValues:
    """Read and change saved values; every call reads the file afresh."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._dir = Path(storage_dir) if storage_dir is not None else persistence.STASH_DIR

    @property
    def path(self) -> Path:
        return self._dir / VALUES_FILE

    # -- reading ---------------------------------------------------------------

    def list_values(self) -> List[Dict[str, Any]]:
        """Every value: All workflows first, then by workflow, then by name."""
        def order(record: Dict[str, Any]) -> Tuple[int, str, str, str]:
            kind, workflow = place_key(record["place"])
            return (0 if kind == ALL else 1, workflow.casefold(), workflow, record["name"].casefold())
        return sorted(self._read(), key=order)

    def get(self, place: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        return self._find(self._read(), place, name)

    # -- changing --------------------------------------------------------------

    def save(self, place: Dict[str, Any], name: str, value: Any,
             saved_by: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Replace (or create) the value under ``name``."""
        name = self._check_name(name)
        self._check_value(value)
        with self._changing() as values:
            return self._put(values, place, name, value, saved_by)

    def add(self, place: Dict[str, Any], name: str, amount: Any,
            saved_by: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a number to the saved number (nothing saved counts as 0)."""
        name = self._check_name(name)
        if type_of(amount) != "number":
            raise SavedValuesError(f"Add needs a number, not {type_of(amount)}", "not_a_number")
        with self._changing() as values:
            current = self._find(values, place, name)
            base = 0
            if current is not None:
                if current["type"] != "number":
                    raise SavedValuesError(
                        f"'{name}' holds a {current['type']}, not a number", "not_a_number")
                base = current["value"]
            total = base + amount
            if not math.isfinite(total):
                raise SavedValuesError(f"'{name}' would no longer be a finite number", "not_a_number")
            return self._put(values, place, name, total, saved_by)

    def check_and_save(self, place: Dict[str, Any], name: str, value: Any,
                       saved_by: Optional[Dict[str, Any]] = None,
                       loosely: bool = False) -> Tuple[Optional[bool], Optional[Dict[str, Any]]]:
        """Compare ``value`` with the saved one, then save it, in one step.

        Returns ``(changed, previous)``: ``changed`` is None the first time
        (nothing saved yet), and ``previous`` is the record before this call.
        """
        name = self._check_name(name)
        self._check_value(value)
        with self._changing() as values:
            found = self._find(values, place, name)
            previous = json.loads(json.dumps(found)) if found is not None else None  # before _put changes it
            changed = None if previous is None else not same_value(previous["value"], value, loosely)
            self._put(values, place, name, value, saved_by)
            return changed, previous

    def forget(self, place: Dict[str, Any], name: str) -> Dict[str, Any]:
        with self._changing() as values:
            record = self._find(values, place, name)
            if record is None:
                raise SavedValuesError(f"Nothing is saved as '{name}' in {place_label(place)}", "not_saved")
            values.remove(record)
            return dict(record)

    def move_workflow(self, old_name: str, new_name: str) -> int:
        """A renamed workflow takes its values along; returns how many moved.
        A value whose name the new workflow already uses stays behind. The
        caller must not move them while another workflow still has the old
        name (a standard workflow and a subworkflow may share one)."""
        old, new = workflow_place(old_name), workflow_place(new_name)
        if not old["workflow"] or old["workflow"] == new["workflow"]:
            return 0
        if not any(_same_place(record["place"], old) for record in self._read()):
            return 0  # nothing to move: leave the file alone
        moved = 0
        with self._changing() as values:
            for record in values:
                if _same_place(record["place"], old) and self._find(values, new, record["name"]) is None:
                    record["place"] = dict(new)
                    moved += 1
        return moved

    # -- internals -------------------------------------------------------------

    def _put(self, values: List[Dict[str, Any]], place: Dict[str, Any], name: str, value: Any,
             saved_by: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        self._check_value(value)  # the last guard: nothing written may be unreadable later
        stamp = _now()
        record = self._find(values, place, name)
        if record is None:
            record = {"id": f"saved_{uuid.uuid4().hex[:12]}", "name": name, "place": dict(place),
                      "created": stamp}
            values.append(record)
        record.update(type=type_of(value), value=value, updated=stamp,
                      saved_by=dict(saved_by or {"from": RUN_FROM}))
        return dict(record)

    @staticmethod
    def _find(values: List[Dict[str, Any]], place: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        wanted = str(name or "").strip().casefold()
        for record in values:
            if _same_place(record["place"], place) and record["name"].casefold() == wanted:
                return record
        return None

    @staticmethod
    def _check_name(name: Any) -> str:
        name = str(name or "").strip()
        if not name:
            raise SavedValuesError("Saved as can't be blank", "node_error")
        return name

    @staticmethod
    def _check_value(value: Any) -> None:
        problem = _value_problem(value)
        if problem:
            raise SavedValuesError(f"This value can't be saved: {problem}", "too_big")

    def _read(self) -> List[Dict[str, Any]]:
        """Every record, or ``store_unreadable``: a damaged file is reported,
        never repaired by dropping records, and never overwritten."""
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:  # ValueError: bad JSON or bad UTF-8
            raise SavedValuesError(f"Cannot read {self.path}: {exc}", "store_unreadable") from exc
        if not isinstance(data, dict) or data.get("format") != FORMAT or not isinstance(data.get("values"), list):
            raise SavedValuesError(f"{self.path} is not a saved values file", "store_unreadable")
        seen = set()
        for number, raw in enumerate(data["values"], 1):
            problem = _record_problem(raw)
            if problem is None:
                key = (place_key(raw["place"]), raw["name"].strip().casefold())
                problem = "a second value with the same name and place" if key in seen else None
                seen.add(key)
            if problem:
                raise SavedValuesError(
                    f"{self.path} is damaged (value {number}: {problem}); fix or remove it",
                    "store_unreadable")
        return data["values"]

    @contextmanager
    def _changing(self) -> Iterator[List[Dict[str, Any]]]:
        """Lock, read, let the caller change the list, write, unlock."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            handle = open(self._dir / LOCK_FILE, "a+")
        except OSError as exc:
            raise SavedValuesError(f"Cannot write {self._dir}: {exc}") from exc
        with handle:
            _lock(handle)
            try:
                values = self._read()
                yield values
                try:
                    persistence.write_json_atomic(self.path, {"format": FORMAT, "values": values})
                except OSError as exc:
                    raise SavedValuesError(f"Cannot write {self.path}: {exc}") from exc
            finally:
                _unlock(handle)


def _lock(handle: Any) -> None:
    """Hold the lock file exclusively: ``fcntl`` on Linux and macOS,
    ``msvcrt`` on Windows; with neither, refuse the change."""
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_EX)
        return
    if msvcrt is not None:
        handle.seek(0)
        deadline = time.monotonic() + LOCK_WAIT
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise SavedValuesError("Saved values are busy (another run holds the lock); "
                                           "try again") from None
                time.sleep(0.05)
    raise SavedValuesError("Saved values can't be changed here: no file lock is available")


def _unlock(handle: Any) -> None:
    if fcntl is not None:
        fcntl.flock(handle, fcntl.LOCK_UN)
    elif msvcrt is not None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _value_problem(value: Any) -> Optional[str]:
    """The one rule for a value, checked on write and on read alike: plain
    JSON, every number finite (at any depth), at most 64 KB."""
    try:
        text = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except ValueError:
        return "it holds a number that isn't finite"
    except TypeError:
        return "it isn't plain data"
    size = len(text.encode("utf-8"))
    if size > MAX_BYTES:
        return f"it is {size // 1024} KB; the limit is 64 KB"
    return None


def _record_problem(raw: Any) -> Optional[str]:
    """Why ``raw`` isn't a whole, consistent saved value, or None."""
    if not isinstance(raw, dict):
        return "not an object"
    if not (isinstance(raw.get("id"), str) and raw["id"].startswith("saved_")):
        return "missing or invalid id"
    if not (isinstance(raw.get("name"), str) and raw["name"].strip()):
        return "blank name"
    place = raw.get("place")
    if not isinstance(place, dict) or place.get("kind") not in (ALL, WORKFLOW):
        return "invalid place"
    if place["kind"] == WORKFLOW and not isinstance(place.get("workflow"), str):
        return "a workflow place without a workflow name"
    if raw.get("type") not in SAVED_TYPES:
        return f"unknown type {raw.get('type')!r}"
    if "value" not in raw:
        return "no value"
    if type_of(raw["value"]) != raw["type"]:
        return f"the value is a {type_of(raw['value'])}, not a {raw['type']}"
    problem = _value_problem(raw["value"])
    if problem:
        return problem
    for stamp in ("created", "updated"):
        if not isinstance(raw.get(stamp), str):
            return f"missing {stamp} time"
    if not isinstance(raw.get("saved_by", {}), dict):
        return "invalid saved_by"
    return None

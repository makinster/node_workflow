"""The Hermes shared folder (AI coordination C1/C2, owner 2026-10-21).

AOTN and Hermes meet in one folder, ``$HERMES_HOME/aotn`` (``HERMES_HOME``
defaults to ``~/.hermes``). It is the one setting both sides read: Notify me
and Record event here, the outbox drain in integrations/hermes/ (#109 review:
an Options value could point the nodes somewhere the drain never looks).
AOTN owns the formats, documented in docs/integrations/HERMES_SHARED_FOLDER.md;
every line carries ``schema_version``.

- ``outbox.jsonl``: messages waiting to send. Notify me adds; the outbox
  drain (integrations/hermes/_aotn_drain.py) prints one digest per tick and
  removes what it printed.
- ``events.jsonl``: history, only ever appended to: one ``receipt`` line per
  stage of a message (queued, skipped, handed_off; delivered / failed later)
  and one ``event`` line per Record event.
- ``repeats.json``: when each repeat key last went out, for "Skip repeats".
- ``outbox.bad.jsonl`` / ``events.bad.jsonl``: unfinished or unreadable
  lines set aside.

The folder is the owner's only (700) and so are the files (600), enforced on
every change, also for files that already existed. The path is not chosen by
a workflow, so these nodes do not use the System nodes' allowed folders
(owner, 2026-10-21). Writers and the drain share ``.lock`` (``flock``).
"""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

try:  # POSIX only; AOTN runs under Linux/WSL, the lock is skipped elsewhere.
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

SCHEMA_VERSION = 1
NAMES_SETTING = "hermes_send_to_names"
DEFAULT_NAMES = "home"
OUTBOX = "outbox.jsonl"
EVENTS = "events.jsonl"
REPEATS = "repeats.json"
LOCK = ".lock"
#: Every file the folder may hold; each must be a regular file, mode 600.
FILES = (LOCK, OUTBOX, EVENTS, REPEATS, "outbox.bad.jsonl", "events.bad.jsonl")

#: One digest fits a Telegram message with room for Hermes's framing (H0).
MESSAGE_LIMIT = 3500
DEFAULT_MESSAGE_LENGTH = 1000
SUMMARY_LIMIT = 300
VALUE_LIMIT = 2000
#: "Skip repeats for" stops at a day, so repeats.json stays small.
MAX_REPEAT_MINUTES = 1440
#: A Send to name is also the drain's file name (aotn-drain-<name>.sh).
NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")

Getter = Optional[Callable[[str], Any]]


def folder() -> Path:
    """``$HERMES_HOME/aotn``; ``HERMES_HOME`` defaults to ``~/.hermes``."""
    home = os.environ.get("HERMES_HOME") or "~/.hermes"
    return Path(os.path.expanduser(home)) / "aotn"


def send_to_names(get_setting: Getter) -> List[str]:
    """The Send to names from Options, separated by ``;``."""
    raw = get_setting(NAMES_SETTING) if get_setting is not None else None
    if raw is None:
        raw = DEFAULT_NAMES
    if not isinstance(raw, str):
        return []
    return [part.strip() for part in raw.split(";") if part.strip()]


def escape(text: str) -> str:
    """Make outside text harmless to Hermes: ``[SILENT]`` variants and
    ``MEDIA:`` are neutralised, and lines starting with ``{`` get ``| ``.

    The same rule as ``integrations/hermes/_aotn_run.escape`` (H0); a test
    keeps the two identical.
    """
    # Hermes compares .upper(), including Unicode long-s, rather than casefold().
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    text = re.sub(r"\[[^\[\]\r\n]{6}\]", lambda m: (
        "［" + m[0][1:-1] + "］" if m[0].upper() == "[SILENT]" else m[0]
    ), text)
    text = text.replace("MEDIA:", "MEDIA：")
    return "".join("| " + line if line.lstrip().startswith("{") else line
                   for line in text.splitlines(keepends=True))


def units(text: str) -> int:
    """Length as Telegram counts it (UTF-16 code units)."""
    return len(text.encode("utf-16-le")) // 2


def cut(text: str, limit: int) -> str:
    """``text`` within ``limit`` UTF-16 units, ending with … when cut."""
    if units(text) <= limit:
        return text
    budget = max(0, limit - 1)
    kept = []
    for char in text:
        cost = 2 if ord(char) > 0xFFFF else 1
        if cost > budget:
            break
        kept.append(char)
        budget -= cost
    return "".join(kept) + "…"


def as_text(value: Any) -> str:
    """A payload as message text: strings as they are, None as nothing,
    anything else as compact JSON (falling back to ``str``)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, separators=(", ", ": "), default=str)
    except (TypeError, ValueError):
        return str(value)


def now_text(stamp: Optional[float] = None) -> str:
    moment = datetime.fromtimestamp(time.time() if stamp is None else stamp, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id(prefix: str) -> str:
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}_{secrets.token_hex(3)}"


def secure(path: Path) -> Path:
    """Create the folder if needed; make it and every file already in it
    the owner's only (700 / 600). A symbolic link is refused."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise OSError(f"{path} is not a plain folder")
    os.chmod(path, 0o700)
    for name in FILES:
        target = path / name
        if target.is_symlink():
            raise OSError(f"{target} is a symbolic link")
        if target.exists():
            if not stat.S_ISREG(target.stat().st_mode):
                raise OSError(f"{target} is not a regular file")
            os.chmod(target, 0o600)
    return path


def _open(path: Path, name: str, flags: int) -> int:
    """Open a folder file (created 600, existing ones set to 600), never
    through a symbolic link."""
    fd = os.open(path / name, flags | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.fchmod(fd, 0o600)
    return fd


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Hold the folder's lock (shared with the drain) for one change."""
    fd = _open(path, LOCK, os.O_RDWR)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _bad_name(name: str) -> str:
    return name.replace(".jsonl", ".bad.jsonl")


def repair_tail(path: Path, name: str) -> None:
    """Under the lock: a writer killed mid-line leaves an unfinished last
    line. Move it to ``<name>.bad.jsonl`` and cut it off, so the next line
    starts clean (#109 review)."""
    target = path / name
    if not target.exists():
        return
    fd = _open(path, name, os.O_RDWR)
    try:
        size = os.fstat(fd).st_size
        if size == 0 or os.pread(fd, 1, size - 1) == b"\n":
            return
        start = size
        while start > 0:
            step = min(65536, start)
            chunk = os.pread(fd, step, start - step)
            newline = chunk.rfind(b"\n")
            if newline >= 0:
                start = start - step + newline + 1
                break
            start -= step
        tail = os.pread(fd, size - start, start)
        _append_bytes(path, _bad_name(name), tail + b"\n")
        os.ftruncate(fd, start)
    finally:
        os.close(fd)


def _append_bytes(path: Path, name: str, data: bytes) -> None:
    fd = _open(path, name, os.O_WRONLY | os.O_APPEND)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


def append_lines(path: Path, name: str, records: List[Dict[str, Any]]) -> None:
    """Append JSON lines in one write after repairing an unfinished tail."""
    repair_tail(path, name)
    data = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    _append_bytes(path, name, data.encode("utf-8"))


def write_atomic(path: Path, name: str, text: str) -> None:
    """Replace ``name`` in one step (temporary file, then rename), as 600."""
    temp = path / f".{name}.{secrets.token_hex(4)}"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temp, path / name)
    except BaseException:
        if temp.exists():
            temp.unlink()
        raise


def _repeats(path: Path, stamp: float) -> Dict[str, float]:
    """When each key last went out, without entries a day old or from the
    future (a clock moved back must not hold messages back; #109 review)."""
    try:
        seen = json.loads((path / REPEATS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(seen, dict):
        return {}
    return {key: value for key, value in seen.items()
            if isinstance(value, (int, float)) and 0 <= stamp - value < MAX_REPEAT_MINUTES * 60}


def is_repeat(path: Path, key: str, minutes: float, stamp: float) -> bool:
    """True when ``key`` went out less than ``minutes`` ago (never for 0)."""
    if minutes <= 0 or not key:
        return False
    last = _repeats(path, stamp).get(key)
    return last is not None and stamp - last < min(minutes, MAX_REPEAT_MINUTES) * 60


def remember(path: Path, key: str, minutes: float, stamp: float) -> None:
    """Note that ``key`` went out, only after its record was written (#109
    review). Best effort: the record is already safe, so a failure here at
    worst lets the next repeat through."""
    if minutes <= 0 or not key:
        return
    seen = _repeats(path, stamp)
    seen[key] = stamp
    try:
        write_atomic(path, REPEATS, json.dumps(seen, ensure_ascii=False))
    except OSError:
        pass


def _receipt(receipt_id: str, stage: str, origin: Dict[str, Any], stamp: float) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": new_id("e"),
        "kind": "receipt",
        "receipt_id": receipt_id,
        "stage": stage,
        "stage_at": now_text(stamp),
        "by": "node",
        **origin,
    }


def queue_message(
    *,
    origin: Dict[str, Any],
    send_to: str,
    priority: str,
    message: str,
    hermes_commands: bool,
    repeat_key: str,
    repeat_minutes: float,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add a message to the outbox and its ``queued`` receipt to the events
    (or only a ``skipped`` receipt for a repeat). Returns the receipt
    ``{"receipt_id", "status", "message"}``. Raises OSError when the folder
    cannot be written."""
    path = secure(path or folder())
    receipt_id = new_id("r")
    with locked(path):
        stamp = time.time()
        if is_repeat(path, repeat_key, repeat_minutes, stamp):
            append_lines(path, EVENTS, [_receipt(receipt_id, "skipped", origin, stamp)])
            return {"receipt_id": receipt_id, "status": "skipped", "message": message}
        line = {
            "schema_version": SCHEMA_VERSION,
            "receipt_id": receipt_id,
            "created_at": now_text(stamp),
            **origin,
            "send_to": send_to,
            "priority": priority,
            "repeat_key": repeat_key,
            "hermes_commands": bool(hermes_commands),
            "message": message,
        }
        # The outbox line is the record that counts: once it is written the
        # message is queued, whatever happens to the history line after it.
        append_lines(path, OUTBOX, [line])
        remember(path, repeat_key, repeat_minutes, stamp)
        try:
            append_lines(path, EVENTS, [_receipt(receipt_id, "queued", origin, stamp)])
        except OSError:
            pass
    return {"receipt_id": receipt_id, "status": "queued", "message": message}


def record_event(
    *,
    origin: Dict[str, Any],
    name: str,
    summary: str,
    value: Optional[str],
    repeat_key: str,
    repeat_minutes: float,
    path: Optional[Path] = None,
) -> str:
    """Append one ``event`` line; return its id, or "" for a skipped repeat.
    Raises OSError when the folder cannot be written."""
    path = secure(path or folder())
    with locked(path):
        stamp = time.time()
        if is_repeat(path, repeat_key, repeat_minutes, stamp):
            return ""
        event_id = new_id("e")
        append_lines(path, EVENTS, [{
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id,
            "kind": "event",
            "name": name,
            "summary": summary,
            "value": value,
            "created_at": now_text(stamp),
            **origin,
        }])
        remember(path, repeat_key, repeat_minutes, stamp)
    return event_id


def origin_of(context: Any) -> Dict[str, Any]:
    """Where a record comes from: workflow, run, node and branch."""
    return {
        "workflow": str(getattr(context, "workflow_name", "") or ""),
        "run_id": str(getattr(context, "run_id", "") or ""),
        "node_id": str(getattr(context, "node_id", "") or ""),
        "branch": str(getattr(context, "branch_id", "") or ""),
    }


def default_repeat_key(origin: Dict[str, Any]) -> str:
    """Run + node + branch, the proposal's default (section 6)."""
    return "/".join((origin["run_id"], origin["node_id"], origin["branch"]))


def node_input(node: Any, context: Any) -> Any:
    """The node's Input: the incoming payload, or a Vault key."""
    if node.config.get("input_source") == "Vault":
        key = str(node.config.get("input_vault_key") or "").strip()
        return context.memory_bank.read_persistent(key) if key else None
    return context.inputs.get("input")


def finish(node: Any, context: Any, own: Any, type_tag: str) -> None:
    """Standard routing: the own result to the Vault when chosen; the next
    node gets the incoming payload unchanged (the default) or the own result."""
    config = node.config
    if config.get("vault_write"):
        key = str(config.get("vault_write_key") or "").strip()
        if not key:
            context.signal_error(ValueError(f"{node.display_name}: enter a Vault output key."))
            return
        context.memory_bank.store_persistent(key, own, type_tag=type_tag)
    if config.get("dead_drop_passthrough"):
        data = {"default": context.inputs.get("input")}
    elif config.get("transient_output", True):
        data = {"default": own}
    else:
        data = {}
    context.signal_done({"data": data})


def repeat_minutes(raw: Any) -> float:
    """"Skip repeats for": blank or invalid means 0 (never skip)."""
    try:
        minutes = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return min(max(minutes, 0.0), float(MAX_REPEAT_MINUTES))

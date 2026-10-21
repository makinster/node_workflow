"""The Hermes shared folder (AI coordination C1/C2, owner 2026-10-21).

AOTN and Hermes meet in one folder, ``~/.hermes/aotn/`` by default (Options:
``hermes_folder``). AOTN owns the formats, documented in
docs/integrations/HERMES_SHARED_FOLDER.md; every line carries
``schema_version``.

- ``outbox.jsonl``: messages waiting to send. Notify me adds; the outbox
  drain (integrations/hermes/_aotn_drain.py) prints one digest per tick and
  removes what it printed.
- ``events.jsonl``: history, only ever appended to: one ``receipt`` line per
  stage of a message (queued, skipped, handed_off; delivered / failed later)
  and one ``event`` line per Record event.
- ``repeats.json``: when each repeat key last went out, for "Skip repeats".

The folder is the owner's only (700) and so are the files (600). The path is
fixed by Options, never by a workflow, so these nodes do not use the System
nodes' allowed folders (owner, 2026-10-21). Writers and the drain share
``.lock`` (``flock``), so lines are never interleaved or lost.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

try:  # POSIX only; AOTN runs under Linux/WSL, the lock is skipped elsewhere.
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

SCHEMA_VERSION = 1
FOLDER_SETTING = "hermes_folder"
DEFAULT_FOLDER = "~/.hermes/aotn"
NAMES_SETTING = "hermes_send_to_names"
DEFAULT_NAMES = "home"
OUTBOX = "outbox.jsonl"
EVENTS = "events.jsonl"
REPEATS = "repeats.json"
LOCK = ".lock"

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


def _setting(get_setting: Getter, key: str, default: str) -> Any:
    value = get_setting(key) if get_setting is not None else None
    return default if value is None else value


def folder(get_setting: Getter) -> Path:
    """The shared folder from Options (``~`` allowed)."""
    raw = str(_setting(get_setting, FOLDER_SETTING, DEFAULT_FOLDER) or "").strip() or DEFAULT_FOLDER
    return Path(os.path.expanduser(raw))


def send_to_names(get_setting: Getter) -> List[str]:
    """The Send to names from Options, separated by ``;``."""
    raw = _setting(get_setting, NAMES_SETTING, DEFAULT_NAMES)
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


def ensure_folder(path: Path) -> Path:
    """Create the folder if needed and keep it the owner's only (700)."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Hold the folder's lock (shared with the drain) for one change."""
    fd = os.open(path / LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def append_lines(path: Path, name: str, records: List[Dict[str, Any]]) -> None:
    """Append JSON lines in one write, creating the file as 600."""
    data = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records).encode("utf-8")
    fd = os.open(path / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


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


def _is_repeat(path: Path, key: str, minutes: float, stamp: float) -> bool:
    """True when ``key`` went out less than ``minutes`` ago; otherwise
    remember it went out now. Entries older than a day are dropped."""
    if minutes <= 0 or not key:
        return False
    try:
        seen = json.loads((path / REPEATS).read_text(encoding="utf-8"))
        if not isinstance(seen, dict):
            seen = {}
    except (OSError, ValueError):
        seen = {}
    seen = {k: v for k, v in seen.items()
            if isinstance(v, (int, float)) and stamp - v < MAX_REPEAT_MINUTES * 60}
    last = seen.get(key)
    if last is not None and stamp - last < min(minutes, MAX_REPEAT_MINUTES) * 60:
        return True
    seen[key] = stamp
    write_atomic(path, REPEATS, json.dumps(seen, ensure_ascii=False))
    return False


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
    get_setting: Getter,
    *,
    origin: Dict[str, Any],
    send_to: str,
    priority: str,
    message: str,
    hermes_commands: bool,
    repeat_key: str,
    repeat_minutes: float,
) -> Dict[str, Any]:
    """Add a message to the outbox and its ``queued`` receipt to the events
    (or only a ``skipped`` receipt for a repeat). Returns the receipt
    ``{"receipt_id", "status", "message"}``. Raises OSError when the folder
    cannot be written."""
    path = ensure_folder(folder(get_setting))
    stamp = time.time()
    receipt_id = new_id("r")
    with locked(path):
        if _is_repeat(path, repeat_key, repeat_minutes, stamp):
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
        append_lines(path, OUTBOX, [line])
        append_lines(path, EVENTS, [_receipt(receipt_id, "queued", origin, stamp)])
    return {"receipt_id": receipt_id, "status": "queued", "message": message}


def record_event(
    get_setting: Getter,
    *,
    origin: Dict[str, Any],
    name: str,
    summary: str,
    value: Optional[str],
    repeat_key: str,
    repeat_minutes: float,
) -> str:
    """Append one ``event`` line; return its id, or "" for a skipped repeat.
    Raises OSError when the folder cannot be written."""
    path = ensure_folder(folder(get_setting))
    stamp = time.time()
    with locked(path):
        if _is_repeat(path, repeat_key, repeat_minutes, stamp):
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

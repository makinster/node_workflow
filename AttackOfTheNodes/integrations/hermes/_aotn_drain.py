#!/usr/bin/env python3
"""Outbox drain: one digest of queued AOTN messages per Hermes cron tick (C3).

Run by ``aotn-drain-<name>.sh`` as a no-agent Hermes job; stdout becomes the
Telegram message, so an empty outbox prints nothing and Hermes sends nothing.
Formats: docs/integrations/HERMES_SHARED_FOLDER.md. Standard library only,
no AOTN imports; escaping comes from the H0 adapter beside this file.

Each tick, holding the folder's lock (the same one Notify me takes):
1. Make the folder the owner's only (700, files 600). Read outbox.jsonl
   line by line (LF only: a message may hold U+2028). Unreadable or
   unfinished lines, or lines of another schema_version, move to
   outbox.bad.jsonl and are counted in the digest.
2. Take this name's messages, urgent first, then oldest first. A message
   with Hermes commands allowed goes out alone, when it is first in line:
   its commands (such as [SILENT]) apply to the whole reply, so it is never
   mixed with other messages. The others go into one digest of at most
   3,500 UTF-16 units, every header and note included; what does not fit
   waits for the next tick.
3. Print it, escaping again any message without hermes_commands.
4. After printing: a handed_off receipt per message in events.jsonl, and the
   outbox rewritten without them.

Exit 0 (printed or nothing to send), 64 usage, 70 failure (Hermes alerts; the
queue is untouched unless printing already happened), 75 lock busy.
A crash between printing and step 4 resends those messages next tick
(at least once, never lost).
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _aotn_run import MESSAGE_LIMIT, escape, units  # noqa: E402

SCHEMA_VERSION = 1
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")
LOCK_WAIT = 10.0
FILES = (".lock", "outbox.jsonl", "events.jsonl", "repeats.json", "outbox.bad.jsonl", "events.bad.jsonl")


def stamp_text():
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id():
    return "e_" + datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(3)


def secure(folder):
    """The folder 700 and every file in it 600; refuse symbolic links."""
    if folder.is_symlink() or not folder.is_dir():
        raise OSError(f"{folder} is not a plain folder")
    os.chmod(folder, 0o700)
    for name in FILES:
        target = folder / name
        if target.is_symlink():
            raise OSError(f"{target} is a symbolic link")
        if target.exists():
            if not stat.S_ISREG(target.stat().st_mode):
                raise OSError(f"{target} is not a regular file")
            os.chmod(target, 0o600)


def open_file(folder, name, flags):
    fd = os.open(folder / name, flags | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    return fd


def lock(folder):
    fd = open_file(folder, ".lock", os.O_RDWR)
    deadline = time.monotonic() + LOCK_WAIT
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            if time.monotonic() > deadline:
                os.close(fd)
                return None
            time.sleep(0.1)


def append_raw(folder, name, data):
    if not data:
        return
    fd = open_file(folder, name, os.O_WRONLY | os.O_APPEND)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


def repair_tail(folder, name):
    """Set aside an unfinished last line (a writer killed mid-line) so the
    next line starts clean; the nodes do the same."""
    path = folder / name
    if not path.exists():
        return
    data = path.read_bytes()
    if not data or data.endswith(b"\n"):
        return
    start = data.rfind(b"\n") + 1
    append_raw(folder, name.replace(".jsonl", ".bad.jsonl"), data[start:] + b"\n")
    fd = open_file(folder, name, os.O_RDWR)
    try:
        os.ftruncate(fd, start)
    finally:
        os.close(fd)


def append(folder, name, records):
    if not records:
        return
    repair_tail(folder, name)
    append_raw(folder, name, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8"))


def rewrite(folder, name, lines):
    temp = folder / f".{name}.{secrets.token_hex(4)}"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(b"".join(lines))
    os.replace(temp, folder / name)


def read_outbox(folder):
    """(records with their raw line, bad raw lines). Lines end at LF only."""
    try:
        raw = (folder / "outbox.jsonl").read_bytes()
    except FileNotFoundError:
        return [], []
    records, bad = [], []
    pieces = raw.split(b"\n")
    for index, piece in enumerate(pieces):
        last = index == len(pieces) - 1
        if not piece.strip():
            continue
        line = piece + b"\n"
        if last:
            # No LF after it: a writer died mid-line (we hold the lock).
            bad.append(line)
            continue
        try:
            record = json.loads(piece.decode("utf-8"))
        except ValueError:
            bad.append(line)
            continue
        if (not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION
                or not isinstance(record.get("message"), str)):
            bad.append(line)
            continue
        records.append((record, line))
    return records, bad


def cut_units(text, limit):
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


def entry_text(record):
    """One ordinary message as it appears in the digest."""
    workflow = escape(str(record.get("workflow") or "AOTN")).strip() or "AOTN"
    mark = "⚠ " if record.get("priority") == "urgent" else ""
    return f"{mark}{workflow}: {escape(record['message'])}"


def render(name, entries, left, bad_count):
    count = len(entries)
    lines = [f"AOTN · {name} · {count} message{'s' if count != 1 else ''}"] + entries
    notes = []
    if left:
        notes.append(f"+{left} more next time")
    if bad_count:
        notes.append(f"{bad_count} unreadable moved to outbox.bad.jsonl")
    if notes:
        lines.append("(" + "; ".join(notes) + ")")
    return "\n\n".join(lines) + "\n"


def command_reply(record):
    """A message with Hermes commands allowed, alone: its own lines kept so a
    directive can start a line."""
    workflow = escape(str(record.get("workflow") or "AOTN")).strip() or "AOTN"
    mark = "⚠ " if record.get("priority") == "urgent" else ""
    head = f"{mark}{workflow}:\n"
    return head + cut_units(record["message"], MESSAGE_LIMIT - units(head) - 1) + "\n"


def build_digest(name, records, bad_count):
    """(text to print, records it covers, whether bad lines were reported).

    Ordinary messages in one digest; a command message alone (see step 2).
    The finished text, notes included, is at most MESSAGE_LIMIT units."""
    ordered = [r for r in records if r[0].get("priority") == "urgent"] + \
              [r for r in records if r[0].get("priority") != "urgent"]
    if ordered and ordered[0][0].get("hermes_commands") is True:
        return command_reply(ordered[0][0]), [ordered[0]], False
    plain = [r for r in ordered if r[0].get("hermes_commands") is not True]
    waiting_commands = len(ordered) - len(plain)
    entries, taken = [], []
    for record, line in plain:
        text = entry_text(record)
        left = len(plain) - len(taken) - 1 + waiting_commands
        if units(render(name, entries + [text], left, bad_count)) > MESSAGE_LIMIT:
            if taken:
                break
            # A single message always goes, cut to fit around everything else.
            room = MESSAGE_LIMIT - units(render(name, [""], left, bad_count))
            text = cut_units(text, room)
        entries.append(text)
        taken.append((record, line))
    if not taken and not bad_count:
        return "", [], False
    left = len(ordered) - len(taken)
    return render(name, entries, left, bad_count), taken, True


def drain(name, folder):
    if not folder.exists():
        return 0
    secure(folder)
    fd = lock(folder)
    if fd is None:
        print("outbox drain: the Hermes folder is busy; trying next tick", file=sys.stderr)
        return 75
    try:
        records, bad = read_outbox(folder)
        mine = [r for r in records if r[0].get("send_to") == name]
        digest, taken, reported_bad = build_digest(name, mine, len(bad))
        if not digest:
            return 0
        if units(digest) > MESSAGE_LIMIT:
            print("outbox drain: digest over the limit; nothing sent", file=sys.stderr)
            return 70
        sys.stdout.write(digest)
        sys.stdout.flush()
        # Printed: from here on, record it and remove it.
        if reported_bad:
            append_raw(folder, "outbox.bad.jsonl", b"".join(bad))
        stamp = stamp_text()
        append(folder, "events.jsonl", [{
            "schema_version": SCHEMA_VERSION,
            "event_id": new_id(),
            "kind": "receipt",
            "receipt_id": record.get("receipt_id"),
            "stage": "handed_off",
            "stage_at": stamp,
            "by": "drain",
            **{key: record.get(key) for key in ("workflow", "run_id", "node_id", "branch")},
        } for record, _ in taken])
        sent = {id(line) for _, line in taken}
        remaining = [line for _, line in records if id(line) not in sent]
        if not reported_bad:
            remaining += bad
        rewrite(folder, "outbox.jsonl", remaining)
        return 0
    finally:
        os.close(fd)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"outbox drain: {message}", file=sys.stderr)
        sys.exit(64)


def main(argv=None):
    parser = Parser(description=__doc__.splitlines()[0])
    parser.add_argument("--send-to", required=True)
    parser.add_argument("--folder", required=True, type=Path)
    args = parser.parse_args(argv)
    if not NAME.match(args.send_to) or not args.folder.is_absolute():
        print("outbox drain: --send-to must be a name like home; --folder an absolute path", file=sys.stderr)
        return 64
    try:
        return drain(args.send_to, args.folder)
    except BrokenPipeError:
        return 70
    except OSError as exc:
        print(f"outbox drain: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    sys.exit(main())

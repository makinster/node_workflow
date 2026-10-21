#!/usr/bin/env python3
"""Outbox drain: one digest of queued AOTN messages per Hermes cron tick (C3).

Run by ``aotn-drain-<name>.sh`` as a no-agent Hermes job; stdout becomes the
Telegram message, so an empty outbox prints nothing and Hermes sends nothing.
Formats: docs/integrations/HERMES_SHARED_FOLDER.md. Standard library only,
no AOTN imports; escaping comes from the H0 adapter beside this file.

Each tick, holding the folder's lock (the same one Notify me takes):
1. Read outbox.jsonl. Unreadable lines, or lines of another schema_version,
   move to outbox.bad.jsonl and are counted in the digest.
2. Take this name's messages, urgent first, then oldest first; build one
   digest up to 3,500 characters. What does not fit waits for the next tick.
3. Print the digest. Escape again any message without hermes_commands.
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
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _aotn_run import MESSAGE_LIMIT, escape, units  # noqa: E402

SCHEMA_VERSION = 1
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")
LOCK_WAIT = 10.0


def stamp_text():
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id():
    return "e_" + datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(3)


def lock(folder):
    fd = os.open(folder / ".lock", os.O_RDWR | os.O_CREAT, 0o600)
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


def append(folder, name, records):
    append_raw(folder, name, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))


def append_raw(folder, name, text):
    if not text:
        return
    data = text.encode("utf-8")
    fd = os.open(folder / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


def rewrite(folder, name, lines):
    temp = folder / f".{name}.{secrets.token_hex(4)}"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("".join(lines))
    os.replace(temp, folder / name)


def read_outbox(folder):
    """(records with their raw line, bad raw lines)."""
    try:
        raw = (folder / "outbox.jsonl").read_bytes().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return [], []
    records, bad = [], []
    for line in raw.splitlines(keepends=True):
        if not line.strip():
            continue
        if not line.endswith("\n"):
            line += "\n"
        try:
            record = json.loads(line)
        except ValueError:
            bad.append(line)
            continue
        if (not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION
                or not isinstance(record.get("message"), str)):
            bad.append(line)
            continue
        records.append((record, line))
    return records, bad


def entry_text(record):
    """One message as it appears in the digest."""
    workflow = escape(str(record.get("workflow") or "AOTN")).strip() or "AOTN"
    mark = "⚠ " if record.get("priority") == "urgent" else ""
    message = record["message"]
    if record.get("hermes_commands") is True:
        # Directives only work at the start of a line: keep the message's own lines.
        return f"{mark}{workflow}:\n{message}"
    return f"{mark}{workflow}: {escape(message)}"


def build_digest(name, records, bad_count):
    """(digest text, records included). Urgent first, then file order."""
    ordered = [r for r in records if r[0].get("priority") == "urgent"] + \
              [r for r in records if r[0].get("priority") != "urgent"]
    entries, taken = [], []
    footer_room = 60
    for record, line in ordered:
        text = entry_text(record)
        header = f"AOTN · {name} · {len(taken) + 1} messages"
        size = units("\n\n".join([header] + entries + [text])) + footer_room
        if size > MESSAGE_LIMIT:
            if taken:
                break
            # A single message always goes, cut to fit.
            budget = MESSAGE_LIMIT - footer_room - units(header) - 3
            text = text[:max(1, budget)] + "…"
        entries.append(text)
        taken.append((record, line))
    if not taken and not bad_count:
        return "", []
    count = len(taken)
    header = f"AOTN · {name} · {count} message{'s' if count != 1 else ''}"
    lines = [header] + entries
    left = len(ordered) - count
    notes = []
    if left:
        notes.append(f"+{left} more next time")
    if bad_count:
        notes.append(f"{bad_count} unreadable moved to outbox.bad.jsonl")
    if notes:
        lines.append("(" + "; ".join(notes) + ")")
    return "\n\n".join(lines) + "\n", taken


def drain(name, folder):
    if not folder.is_dir():
        return 0
    fd = lock(folder)
    if fd is None:
        print("outbox drain: the Hermes folder is busy; trying next tick", file=sys.stderr)
        return 75
    try:
        records, bad = read_outbox(folder)
        mine = [r for r in records if r[0].get("send_to") == name]
        digest, taken = build_digest(name, mine, len(bad))
        if not digest:
            return 0
        sys.stdout.write(digest)
        sys.stdout.flush()
        # Printed: from here on, record it and remove it.
        append_raw(folder, "outbox.bad.jsonl", "".join(bad))
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

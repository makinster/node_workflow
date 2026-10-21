#!/usr/bin/env python3
"""Bounded, directive-safe Hermes handoff through AOTN's JSON CLI (POSIX)."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time

DEADLINE = 100.0
GRACE = 5.0
REPORT_LIMIT = 1024 * 1024
DIAGNOSTIC_LIMIT = 64 * 1024
MESSAGE_LIMIT = 3500
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")


def escape(text):
    # Hermes compares .upper(), including Unicode long-s, rather than casefold().
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    text = re.sub(r"\[[^\[\]\r\n]{6}\]", lambda m: (
        "［" + m[0][1:-1] + "］" if m[0].upper() == "[SILENT]" else m[0]
    ), text)
    text = text.replace("MEDIA:", "MEDIA：")
    return "".join("| " + line if line.lstrip().startswith("{") else line
                   for line in text.splitlines(keepends=True))


def units(text):
    return len(text.encode("utf-16-le")) // 2


def bounded(text, run_id=None):
    text = escape(text)
    if units(text) <= MESSAGE_LIMIT:
        return text
    # Sanitize identifiers too: a malformed child must not inject via the tail.
    identity = escape(run_id) if run_id else "unavailable"
    tail = "\n| …truncated; see run " + identity
    if units(tail) > MESSAGE_LIMIT // 2:
        tail = "\n| …truncated; run unavailable"
    budget = MESSAGE_LIMIT - units(tail)
    prefix = []
    for char in text:
        cost = 2 if ord(char) > 0xFFFF else 1
        if cost > budget:
            break
        prefix.append(char)
        budget -= cost
    return "".join(prefix) + tail


def display(value):
    return json.dumps(value) if isinstance(value, (dict, list)) else str(value)


def render(report):
    lines = []
    for value in report["outputs"]:
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        lines.append(display(value))
    lines.extend(f"{name} = {display(value)}" for name, value in report["values"].items())
    return "".join(line + "\n" for line in lines)


def parse_report(raw, code):
    if not raw.strip() and code != 0:
        return None  # CLI preflight errors legitimately have no report.
    report = json.loads(raw)
    if (not isinstance(report, dict)
            or not isinstance(report.get("run_id"), str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", report["run_id"])
            or not isinstance(report.get("outputs"), list)
            or not isinstance(report.get("values"), dict)
            or not isinstance(report.get("final_state"), str)
            or type(report.get("exit_code")) is not int
            or report["exit_code"] != code):
        raise ValueError("invalid report shape or exit_code mismatch")
    return report


def group_signal(child, sig):
    try:
        os.killpg(child.pid, sig)
    except ProcessLookupError:
        pass


def collect(argv, cwd):
    """Drain both pipes without unbounded storage; own the whole process group."""
    stopped = [None]
    old_handlers = {}
    child = None
    selector = selectors.DefaultSelector()
    stdout, stderr = bytearray(), bytearray()
    overflow = False
    stderr_truncated = False
    reason = None
    kill_at = None
    started = time.monotonic()

    def interrupted(sig, _frame):
        if stopped[0] is None:
            stopped[0] = sig

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            old_handlers[sig] = signal.signal(sig, interrupted)
        child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
        for stream, label in ((child.stdout, "stdout"), (child.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, label)
        while selector.get_map() or child.poll() is None:
            now = time.monotonic()
            if stopped[0] is not None and reason != "signal":
                reason = "signal"
                kill_at = now + GRACE
                group_signal(child, signal.SIGINT)
            if reason is None and now >= started + DEADLINE - GRACE:
                reason = "deadline"
                kill_at = started + DEADLINE
                group_signal(child, signal.SIGINT)
            if overflow and reason is None:
                reason = "overflow"
                kill_at = now + GRACE
                group_signal(child, signal.SIGINT)
            if kill_at is not None and now >= kill_at:
                group_signal(child, signal.SIGKILL)
                child.wait()
                # A descendant may have escaped the group with inherited pipes.
                # Do not let it hold this adapter or its overlap lock forever.
                break
            for key, _ in selector.select(timeout=0.05):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                target, limit = (stdout, REPORT_LIMIT) if key.data == "stdout" else (stderr, DIAGNOSTIC_LIMIT)
                room = max(0, limit - len(target))
                target.extend(chunk[:room])
                if len(chunk) > room:
                    if key.data == "stdout":
                        overflow = True
                    else:
                        stderr_truncated = True
        child.wait()
        # Clean up any lingering same-group descendants even when the leader exits.
        group_signal(child, signal.SIGKILL)
        if stopped[0] is not None:
            code = 128 + stopped[0]
            reason = "signal"
        elif reason == "deadline":
            code = 124
        elif overflow:
            code = 70
            reason = "overflow"
        else:
            code = child.returncode if child.returncode >= 0 else 128 - child.returncode
        diagnostic = stderr.decode("utf-8", errors="replace")
        if stderr_truncated:
            diagnostic += "\nChild stderr truncated after 64 KiB.\n"
        natural_code = child.returncode if child.returncode >= 0 else 128 - child.returncode
        return code, bytes(stdout), diagnostic, reason, natural_code
    finally:
        if child is not None:
            group_signal(child, signal.SIGKILL)
            child.wait()
            for stream in (child.stdout, child.stderr):
                stream.close()
        selector.close()
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


def run(args):
    if not SLUG.fullmatch(args.workflow_slug):
        raise ValueError("invalid workflow slug")
    for name in ("project_root", "data_dir", "python"):
        if not Path(getattr(args, name)).is_absolute():
            raise ValueError(f"{name} must be absolute")
    root, data = Path(args.project_root), Path(args.data_dir)
    repository_app = (root / "AttackOfTheNodes").resolve()
    repository_workflows = repository_app / "workflows"
    if data.resolve() == repository_app or data.resolve().is_relative_to(repository_workflows):
        raise ValueError("cron data directory must be separate from repository workflows")
    locks = data / ".hermes-locks"
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / (args.workflow_slug + ".lock")).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.stderr.write(bounded("AOTN overlap: workflow already running; run unavailable\n"))
            return 75
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        argv = [args.python, str(root / "AttackOfTheNodes/main.py"), "run", args.workflow_slug,
                "--policy", "terminate_workflow", "--data-dir", str(data),
                "--input", "checked_at=" + stamp, "--json"]
        code, raw, diagnostic, reason, natural_code = collect(argv, str(root))
        report = None
        try:
            report = parse_report(raw, natural_code)
        except (ValueError, TypeError, RecursionError) as exc:
            if reason is None:
                code = 70
                diagnostic += f"\nAOTN adapter failure: {exc}; run unavailable\n"
        identity = report["run_id"] if report else "unavailable"
        if reason == "deadline":
            diagnostic += f"\nAOTN deadline exceeded (100 seconds); run {identity}\n"
        elif reason == "signal":
            diagnostic += f"\nAOTN interrupted (exit {code}); run {identity}\n"
        elif reason == "overflow":
            diagnostic += "\nAOTN adapter failure: stdout exceeded 1 MiB; run unavailable\n"
        run_id = report["run_id"] if report else None
        if code == 0:
            sys.stdout.write(bounded(render(report), run_id))
        else:
            diagnostic += f"\nAOTN failed (exit {code}); run {run_id or 'unavailable'}\n"
        sys.stderr.write(bounded(diagnostic, run_id))
        return code


class AdapterParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    try:
        parser = AdapterParser(description=__doc__)
        for option in ("workflow-slug", "project-root", "data-dir", "python"):
            parser.add_argument("--" + option, required=True)
        return run(parser.parse_args())
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        sys.stderr.write(bounded(f"AOTN adapter failure: {exc}; run unavailable\n"))
        return 70


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Bounded, directive-safe Hermes handoff through AOTN's JSON CLI (POSIX)."""
import argparse
import ctypes
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
LAUNCHER_DEADLINE = 25.0
GRACE = 5.0
CLEANUP_WAIT = 1.0
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


class CleanupFailure(OSError):
    """Cleanup could not be confirmed; the persistent lock marker must remain."""


def enable_subreaper():
    if sys.platform != "linux":
        return False  # Other POSIX systems retain process-group cleanup.
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
    prctl.restype = ctypes.c_int
    if prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "cannot enable child subreaper")
    return True


def descendants():
    """Snapshot the adapter's descendants, including adopted session leaders."""
    parents = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            parents[int(entry.name)] = int(fields[1])
        except (FileNotFoundError, ProcessLookupError):
            continue
    owned = {os.getpid()}
    while True:
        added = {pid for pid, parent in parents.items() if parent in owned} - owned
        if not added:
            return owned - {os.getpid()}
        owned.update(added)


def cleanup(child, linux, timeout):
    """Kill and reap within a fixed budget, including escaped descendants."""
    until = time.monotonic() + timeout
    while True:
        try:
            group_signal(child, signal.SIGKILL)
            remaining = descendants() if linux else set()
            for pid in remaining:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            # Let Popen own its direct child's status before reaping adoptees.
            if child.poll() is not None:
                if linux:
                    for _ in range(256):
                        try:
                            if os.waitpid(-1, os.WNOHANG)[0] == 0:
                                break
                        except ChildProcessError:
                            break
                if not linux or not descendants():
                    return
        except OSError as exc:
            raise CleanupFailure(f"descendant cleanup unconfirmed: {exc}; lock marked stale") from exc
        if time.monotonic() >= until:
            raise CleanupFailure("descendant cleanup timed out; lock marked stale")
        time.sleep(min(0.01, max(0, until - time.monotonic())))


def collect(argv, cwd, deadline=None):
    """Drain bounded streams; own the process group and Linux descendants."""
    stopped = [None]
    old_handlers = {}
    child = None
    cleanup_attempted = False
    linux = enable_subreaper()
    cleanup_budget = min(CLEANUP_WAIT, GRACE / 2)
    selector = selectors.DefaultSelector()
    stdout, stderr = bytearray(), bytearray()
    overflow = False
    stderr_truncated = False
    reason = None
    kill_at = None
    started = time.monotonic()
    hard_deadline = deadline is not None
    deadline = DEADLINE if deadline is None else deadline

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
                kill_at = now + GRACE - cleanup_budget
                group_signal(child, signal.SIGINT)
            if reason is None and now >= started + deadline - GRACE:
                reason = "deadline"
                kill_at = started + deadline - cleanup_budget
                group_signal(child, signal.SIGINT)
            if overflow and reason is None:
                reason = "overflow"
                kill_at = now + GRACE - cleanup_budget
                group_signal(child, signal.SIGINT)
            if hard_deadline and kill_at is not None:
                # Signals/overflow late in a quick command must not restart
                # its cleanup clock beyond Hermes's reply window.
                kill_at = min(kill_at, started + deadline - cleanup_budget)
            if kill_at is not None and now >= kill_at:
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
        cleanup_attempted = True
        cleanup(child, linux, cleanup_budget)
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
        try:
            if child is not None and not cleanup_attempted:
                cleanup(child, linux, cleanup_budget)
        finally:
            if child is not None:
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
    with (locks / (args.workflow_slug + ".lock")).open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if args.telegram_launcher:
                return launcher_failure(args, "workflow already running", 75)
            sys.stderr.write(bounded("AOTN overlap: workflow already running; run unavailable\n"))
            return 75
        lock.seek(0)
        if lock.read(1):
            if args.telegram_launcher:
                return launcher_failure(args, "previous run cleanup needs checking", 75)
            sys.stderr.write(bounded("AOTN overlap: lock marked stale; verify prior descendants before clearing it; run unavailable\n"))
            return 75
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        argv = [args.python, str(root / "AttackOfTheNodes/main.py"), "run", args.workflow_slug,
                "--policy", "terminate_workflow", "--data-dir", str(data),
                "--input-if-declared" if args.telegram_launcher else "--input",
                "checked_at=" + stamp, "--json"]
        # Persist before spawning: a crash or unconfirmed cleanup blocks ticks
        # even after the OS releases flock. Clear only after confirmed cleanup.
        lock.write(f"stale: adapter pid {os.getpid()}; descendant cleanup not confirmed\n")
        lock.flush()
        os.fsync(lock.fileno())
        try:
            code, raw, diagnostic, reason, natural_code = collect(
                argv, str(root), LAUNCHER_DEADLINE if args.telegram_launcher else None)
        except CleanupFailure:
            raise
        except BaseException:
            lock.seek(0)
            lock.truncate()
            lock.flush()
            raise
        else:
            lock.seek(0)
            lock.truncate()
            lock.flush()
        report = None
        try:
            report = parse_report(raw, natural_code)
        except (ValueError, TypeError, RecursionError) as exc:
            if reason is None:
                code = 70
                diagnostic += f"\nAOTN adapter failure: {exc}; run unavailable\n"
        identity = report["run_id"] if report else "unavailable"
        if args.telegram_launcher:
            if code == 0:
                sys.stdout.write(bounded(render(report), report["run_id"]))
                return 0
            if reason == "deadline":
                message = "stopped after 25 s"
            elif reason == "signal":
                message = "run interrupted"
            else:
                message = {
                    1: "run finished with errors", 2: "run failed; see run history",
                    3: "workflow is invalid or could not start",
                    4: "saved workflow not found or unreadable",
                    5: "required inputs are missing or invalid; v0 supplies only checked_at",
                }.get(code, "adapter failed; check the installation and run history")
            return launcher_failure(args, message, code)
        if reason == "deadline":
            diagnostic += f"\nAOTN deadline exceeded ({DEADLINE:g} seconds); run {identity}\n"
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


def launcher_failure(args, reason, code):
    sys.stdout.write(bounded(f"Couldn't run {args.workflow_slug}: {reason}\n"))
    return code


def main():
    args = None
    try:
        parser = AdapterParser(description=__doc__)
        for option in ("workflow-slug", "project-root", "data-dir", "python"):
            parser.add_argument("--" + option, required=True)
        parser.add_argument("--telegram-launcher", action="store_true",
                            help="25-second run budget and one-line failure receipts")
        args = parser.parse_args()
        return run(args)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        if args is not None and args.telegram_launcher:
            reason = ("previous run cleanup could not be confirmed" if isinstance(exc, CleanupFailure)
                      else "adapter failed; check the installation and data directory")
            return launcher_failure(args, reason, 70)
        sys.stderr.write(bounded(f"AOTN adapter failure: {exc}; run unavailable\n"))
        return 70


if __name__ == "__main__":
    sys.exit(main())

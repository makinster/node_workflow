"""Bounded cleanup for the single active MCP worker and its descendants."""
import ctypes
import os
from pathlib import Path
import signal
import sys
import time


def subreaper():
    if sys.platform != 'linux':
        return False
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(36, 1, 0, 0, 0):  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'cannot enable MCP child subreaper')
    return True


def descendants():
    parents = {}
    for path in Path('/proc').iterdir():
        if path.name.isdecimal():
            try:
                parents[int(path.name)] = int((path / 'stat').read_text(errors='replace').rsplit(')', 1)[1].split()[1])
            except (FileNotFoundError, ProcessLookupError):
                pass
    owned = {os.getpid()}
    while True:
        new = {pid for pid, ppid in parents.items() if ppid in owned} - owned
        if not new:
            return owned - {os.getpid()}
        owned.update(new)


def kill_and_reap(pid, linux):
    # Called inside the serial tool-call lock, including cancellation/EOF.
    until = time.monotonic() + 1
    while True:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if linux:
            for descendant in descendants():
                try:
                    os.kill(descendant, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            # asyncio owns the direct worker's wait status. Only reap adoptees.
            for descendant in descendants() - {pid}:
                try:
                    os.waitpid(descendant, os.WNOHANG)
                except ChildProcessError:
                    pass
            if not descendants() - {pid}:
                return
        else:
            # The asyncio subprocess transport reaps the direct child.
            return
        if time.monotonic() >= until:
            raise OSError('MCP descendant cleanup timed out; restart only after checking remaining processes')
        time.sleep(0.01)

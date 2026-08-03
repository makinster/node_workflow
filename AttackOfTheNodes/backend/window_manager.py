"""OS window launch/placement adapter (FO4, docs/FILE_OUTPUT_BUILD_PLAN.md).

Small protocol behind a platform factory: open a file in its OS-default app,
discover the resulting window once (launch-time snapshot diff, D4), place it
by semantic preset (D3), and focus/minimize/close it later by reference (D6).

Design constraints this module honors:

- **pywin32 is optional and guarded (D5).** The Windows implementation
  imports pywin32 lazily; when it is missing — or on any non-Windows OS —
  files still open (``os.startfile`` / ``xdg-open`` / ``open``) and placement
  degrades to a logged warning. ``capabilities()`` tells the validator what
  actually works so workflows stay portable documents.
- **Discovery failure is never an error (D4).** ``open_path`` returns
  ``None`` when the new window cannot be identified; callers treat the file
  as "opened but unplaced".
- **No run-state coupling (D11).** The adapter never touches MasterState,
  RunSession, or Textual, so it can be lifted behind an event boundary
  unchanged when the backend becomes a remote server.
- **Presets define position AND size (D3).** ``placement_rect`` is a pure
  function over monitor rects, fully unit-testable on any OS.

The Windows-specific branch cannot be pytest-verified in this repo's Linux
environment; it ships against the FO7 manual verification protocol.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence, Set


logger = logging.getLogger(__name__)


# ── Placement preset vocabulary (D3) ─────────────────────────────────────────
# Semantic, OS-neutral presets — never pixel coordinates. A future
# macOS/Linux adapter implements the same options.

PLACE_OS_DEFAULT = "OS default"
PLACE_RIGHT_OF_AOTN = "Right of AOTN"
PLACE_LEFT_OF_AOTN = "Left of AOTN"
PLACE_OTHER_MONITOR = "Other monitor"
PLACE_RIGHT_HALF = "Same monitor, right half"

PLACEMENT_PRESETS = [
    PLACE_OS_DEFAULT,
    PLACE_RIGHT_OF_AOTN,
    PLACE_LEFT_OF_AOTN,
    PLACE_OTHER_MONITOR,
    PLACE_RIGHT_HALF,
]

# Capability strings reported by capabilities() and consumed by the D5
# validator warning: "open" = can launch files at all; "place" = presets do
# something; "focus"/"minimize"/"close" = window_control_node verbs work.
CAP_OPEN = "open"
CAP_PLACE = "place"
CAP_FOCUS = "focus"
CAP_MINIMIZE = "minimize"
CAP_CLOSE = "close"

# A side preset narrower than this degrades to a half-monitor split — a
# 40-px sliver next to a nearly fullscreen terminal helps nobody.
MIN_SIDE_WIDTH = 200

# How long open_path polls for the newly launched window (D4).
DISCOVERY_TIMEOUT_SECONDS = 5.0
DISCOVERY_POLL_SECONDS = 0.25


@dataclass(frozen=True)
class Rect:
    """A screen rectangle in virtual-desktop pixel coordinates."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains_point(self, x: int, y: int) -> bool:
        return self.x <= x < self.right and self.y <= y < self.bottom


@dataclass(frozen=True)
class Monitor:
    """One display: full bounds plus the taskbar-free work area."""

    bounds: Rect
    work_area: Rect
    is_primary: bool = False


@dataclass
class WindowRef:
    """Opaque handle to one discovered OS window.

    Lives only in RunSession (reference types rule, D2) — never in
    MemoryBank payloads or saves. ``handle`` is an HWND int on Windows.
    """

    handle: Any
    path: str


# ── Preset → rect math (pure, unit-tested) ───────────────────────────────────

def placement_rect(
    preset: str,
    monitors: Sequence[Monitor],
    own_rect: Optional[Rect],
) -> Optional[Rect]:
    """Compute the target rect for a placement preset.

    ``own_rect`` is AOTN's own window rect when it could be resolved (see the
    D3 Windows Terminal caveat); ``None`` degrades AOTN-relative presets to
    their monitor-relative equivalents. Returns ``None`` for ``OS default``
    (leave the window wherever the OS puts it) or when no monitors are known.
    """
    if preset not in PLACEMENT_PRESETS:
        logger.warning("Unknown placement preset %r; using OS default", preset)
        return None
    if preset == PLACE_OS_DEFAULT or not monitors:
        return None

    home = _monitor_for_rect(monitors, own_rect)
    work = home.work_area

    if preset == PLACE_OTHER_MONITOR:
        for monitor in monitors:
            if monitor is not home:
                return monitor.work_area
        # Single monitor: degrade to filling the one we have.
        logger.warning("No other monitor found; using the current monitor")
        return work

    if preset == PLACE_RIGHT_HALF:
        return _right_half(work)

    if own_rect is None:
        # AOTN-relative preset without a resolvable own window (D3 caveat):
        # degrade to the monitor-relative half on the requested side.
        logger.warning(
            "AOTN window rect unavailable; degrading %r to a monitor half",
            preset,
        )
        return _right_half(work) if preset == PLACE_RIGHT_OF_AOTN else _left_half(work)

    if preset == PLACE_RIGHT_OF_AOTN:
        width = work.right - min(own_rect.right, work.right)
        if width < MIN_SIDE_WIDTH:
            return _right_half(work)
        return Rect(work.right - width, work.y, width, work.height)

    # PLACE_LEFT_OF_AOTN
    width = max(own_rect.x, work.x) - work.x
    if width < MIN_SIDE_WIDTH:
        return _left_half(work)
    return Rect(work.x, work.y, width, work.height)


def _right_half(work: Rect) -> Rect:
    half = work.width // 2
    return Rect(work.x + work.width - half, work.y, half, work.height)


def _left_half(work: Rect) -> Rect:
    return Rect(work.x, work.y, work.width // 2, work.height)


def _monitor_for_rect(monitors: Sequence[Monitor], rect: Optional[Rect]) -> Monitor:
    """The monitor containing *rect*'s center, else the primary, else the first."""
    if rect is not None:
        center_x = rect.x + rect.width // 2
        center_y = rect.y + rect.height // 2
        for monitor in monitors:
            if monitor.bounds.contains_point(center_x, center_y):
                return monitor
    for monitor in monitors:
        if monitor.is_primary:
            return monitor
    return monitors[0]


# ── Protocol implementations ─────────────────────────────────────────────────

class WindowManager:
    """Adapter protocol (kept small on purpose, D9)."""

    def capabilities(self) -> Set[str]:
        raise NotImplementedError

    def open_path(
        self, path: str, placement: str = PLACE_OS_DEFAULT
    ) -> Optional[WindowRef]:
        """Open *path* in its OS-default app; discover and place the window.

        Always attempts the launch. Returns the discovered ``WindowRef`` or
        ``None`` when discovery/placement is unsupported or failed — which is
        a degraded success, never an error (D4).
        """
        raise NotImplementedError

    def focus(self, ref: WindowRef) -> bool:
        raise NotImplementedError

    def minimize(self, ref: WindowRef) -> bool:
        raise NotImplementedError

    def close(self, ref: WindowRef) -> bool:
        raise NotImplementedError


class FallbackWindowManager(WindowManager):
    """Any OS without a real adapter: open files, no window choreography (D5)."""

    def __init__(self) -> None:
        self._opener = "open" if platform.system() == "Darwin" else "xdg-open"

    def capabilities(self) -> Set[str]:
        return {CAP_OPEN}

    def open_path(
        self, path: str, placement: str = PLACE_OS_DEFAULT
    ) -> Optional[WindowRef]:
        if placement != PLACE_OS_DEFAULT:
            logger.warning(
                "Window placement %r is not supported on %s; opening with the "
                "OS default placement",
                placement,
                platform.system(),
            )
        try:
            subprocess.Popen(
                [self._opener, str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            logger.warning("Could not open %s with %s: %s", path, self._opener, exc)
        return None

    def focus(self, ref: WindowRef) -> bool:
        logger.warning("Window focus is not supported on %s", platform.system())
        return False

    def minimize(self, ref: WindowRef) -> bool:
        logger.warning("Window minimize is not supported on %s", platform.system())
        return False

    def close(self, ref: WindowRef) -> bool:
        logger.warning("Window close is not supported on %s", platform.system())
        return False


class FakeWindowManager(WindowManager):
    """In-memory adapter for node tests (FO5/FO6) and protocol documentation.

    Records every call; ``open_path`` returns a fabricated ``WindowRef``
    unless ``discovery_fails`` is set (exercising the D4 degraded path).
    """

    def __init__(self, discovery_fails: bool = False) -> None:
        self.discovery_fails = discovery_fails
        self.opened: List[tuple] = []
        self.focused: List[WindowRef] = []
        self.minimized: List[WindowRef] = []
        self.closed: List[WindowRef] = []
        self._next_handle = 1000

    def capabilities(self) -> Set[str]:
        return {CAP_OPEN, CAP_PLACE, CAP_FOCUS, CAP_MINIMIZE, CAP_CLOSE}

    def open_path(
        self, path: str, placement: str = PLACE_OS_DEFAULT
    ) -> Optional[WindowRef]:
        self.opened.append((str(path), placement))
        if self.discovery_fails:
            return None
        self._next_handle += 1
        return WindowRef(handle=self._next_handle, path=str(path))

    def focus(self, ref: WindowRef) -> bool:
        self.focused.append(ref)
        return True

    def minimize(self, ref: WindowRef) -> bool:
        self.minimized.append(ref)
        return True

    def close(self, ref: WindowRef) -> bool:
        self.closed.append(ref)
        return True


class WindowsWindowManager(WindowManager):
    """pywin32-backed adapter (D5 decision record: pywin32 over raw ctypes).

    Everything here degrades: without pywin32 installed this behaves like the
    fallback manager (files open via ``os.startfile``, no choreography). The
    pywin32 branch is exercised by the FO7 manual protocol, not CI.
    """

    def __init__(self) -> None:
        self._win32 = _load_pywin32()
        if self._win32 is None:
            logger.warning(
                "pywin32 is not installed; window placement/control disabled. "
                "Install the 'windows' extra to enable it."
            )

    def capabilities(self) -> Set[str]:
        if self._win32 is None:
            return {CAP_OPEN}
        return {CAP_OPEN, CAP_PLACE, CAP_FOCUS, CAP_MINIMIZE, CAP_CLOSE}

    def open_path(
        self, path: str, placement: str = PLACE_OS_DEFAULT
    ) -> Optional[WindowRef]:
        if self._win32 is None:
            if placement != PLACE_OS_DEFAULT:
                logger.warning(
                    "Window placement %r needs pywin32; opening with the OS "
                    "default placement",
                    placement,
                )
            os.startfile(str(path))  # noqa: S606 - opening user-chosen file
            return None

        before = self._snapshot_windows()
        os.startfile(str(path))  # noqa: S606
        hwnd = self._discover_window(str(path), before)
        if hwnd is None:
            logger.warning(
                "Could not identify the window opened for %s; it is open but "
                "unplaced",
                path,
            )
            return None
        ref = WindowRef(handle=hwnd, path=str(path))
        if placement != PLACE_OS_DEFAULT:
            self._apply_placement(ref, placement)
        return ref

    def focus(self, ref: WindowRef) -> bool:
        win32gui, _, win32con = self._win32 or (None, None, None)
        if win32gui is None:
            return False
        try:
            win32gui.ShowWindow(ref.handle, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(ref.handle)
            return True
        except Exception as exc:  # window state races the user; soft-fail
            logger.warning("Could not focus window for %s: %s", ref.path, exc)
            return False

    def minimize(self, ref: WindowRef) -> bool:
        win32gui, _, win32con = self._win32 or (None, None, None)
        if win32gui is None:
            return False
        try:
            win32gui.ShowWindow(ref.handle, win32con.SW_MINIMIZE)
            return True
        except Exception as exc:
            logger.warning("Could not minimize window for %s: %s", ref.path, exc)
            return False

    def close(self, ref: WindowRef) -> bool:
        win32gui, _, win32con = self._win32 or (None, None, None)
        if win32gui is None:
            return False
        try:
            win32gui.PostMessage(ref.handle, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception as exc:
            logger.warning("Could not close window for %s: %s", ref.path, exc)
            return False

    # ── Windows internals (FO7-verified) ────────────────────────────────────

    def _snapshot_windows(self) -> Set[int]:
        win32gui, _, _ = self._win32
        found: Set[int] = set()

        def collect(hwnd: int, _extra: Any) -> None:
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                found.add(hwnd)

        win32gui.EnumWindows(collect, None)
        return found

    def _discover_window(self, path: str, before: Set[int]) -> Optional[int]:
        """Snapshot-diff discovery with title fallback (D4).

        Polls for a visible top-level window that did not exist before the
        launch. Falls back to title-contains-filename only when the diff is
        empty (single-process apps reusing an existing window) or ambiguous.
        """
        filename = Path(path).name.lower()
        stem = Path(path).stem.lower()
        deadline = time.monotonic() + DISCOVERY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            current = self._snapshot_windows()
            new_windows = current - before
            if len(new_windows) == 1:
                return next(iter(new_windows))
            if len(new_windows) > 1:
                by_title = self._match_by_title(new_windows, filename, stem)
                return by_title if by_title is not None else next(iter(new_windows))
            time.sleep(DISCOVERY_POLL_SECONDS)
        # No new window at all: e.g. Excel opening a workbook into an
        # existing instance. Last resort is a title match across all windows.
        return self._match_by_title(self._snapshot_windows(), filename, stem)

    def _match_by_title(
        self, hwnds: Set[int], filename: str, stem: str
    ) -> Optional[int]:
        win32gui, _, _ = self._win32
        for hwnd in hwnds:
            title = win32gui.GetWindowText(hwnd).lower()
            if filename in title or (stem and stem in title):
                return hwnd
        return None

    def _apply_placement(self, ref: WindowRef, placement: str) -> None:
        win32gui, _, win32con = self._win32
        target = placement_rect(placement, self._monitors(), self._own_window_rect())
        if target is None:
            return
        try:
            win32gui.ShowWindow(ref.handle, win32con.SW_RESTORE)
            win32gui.MoveWindow(
                ref.handle, target.x, target.y, target.width, target.height, True
            )
        except Exception as exc:
            logger.warning("Could not place window for %s: %s", ref.path, exc)

    def _monitors(self) -> List[Monitor]:
        _, win32api, _ = self._win32
        monitors: List[Monitor] = []
        try:
            for handle, _dc, _rect in win32api.EnumDisplayMonitors(None, None):
                info = win32api.GetMonitorInfo(handle)
                left, top, right, bottom = info["Monitor"]
                w_left, w_top, w_right, w_bottom = info["Work"]
                monitors.append(
                    Monitor(
                        bounds=Rect(left, top, right - left, bottom - top),
                        work_area=Rect(
                            w_left, w_top, w_right - w_left, w_bottom - w_top
                        ),
                        is_primary=(info.get("Flags", 0) & 1) == 1,
                    )
                )
        except Exception as exc:
            logger.warning("Could not enumerate monitors: %s", exc)
        return monitors

    def _own_window_rect(self) -> Optional[Rect]:
        """Resolve AOTN's real terminal window rect (D3 Windows Terminal caveat).

        Under ConPTY hosts (Windows Terminal), ``GetConsoleWindow()`` returns
        a hidden pseudo-console window whose rect is meaningless, so walk the
        parent-process chain looking for a visible top-level window owned by
        an ancestor (the real terminal). Legacy conhost keeps a visible
        console window, which the fallback covers. ``None`` degrades
        AOTN-relative presets to monitor-relative in ``placement_rect``.
        """
        win32gui, _, _ = self._win32
        hwnd = self._ancestor_window()
        if hwnd is None:
            try:
                import ctypes

                console = ctypes.windll.kernel32.GetConsoleWindow()
                if console and win32gui.IsWindowVisible(console):
                    hwnd = console
            except Exception:
                hwnd = None
        if not hwnd:
            return None
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            return Rect(left, top, right - left, bottom - top)
        except Exception as exc:
            logger.warning("Could not read AOTN window rect: %s", exc)
            return None

    def _ancestor_window(self) -> Optional[int]:
        """The first visible top-level window owned by a process ancestor."""
        win32gui, _, _ = self._win32
        try:
            import win32process

            ancestors = self._ancestor_pids()
            if not ancestors:
                return None
            matches: dict[int, int] = {}  # pid -> hwnd

            def collect(hwnd: int, _extra: Any) -> None:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in ancestors and pid not in matches:
                    matches[pid] = hwnd

            win32gui.EnumWindows(collect, None)
            for pid in ancestors:  # nearest ancestor first
                if pid in matches:
                    return matches[pid]
        except Exception as exc:
            logger.warning("Parent-process window walk failed: %s", exc)
        return None

    def _ancestor_pids(self, max_depth: int = 10) -> List[int]:
        """Our parent-process chain, nearest first (NtQueryInformationProcess)."""
        import ctypes

        class ProcessBasicInformation(ctypes.Structure):
            _fields_ = [
                ("Reserved1", ctypes.c_void_p),
                ("PebBaseAddress", ctypes.c_void_p),
                ("Reserved2", ctypes.c_void_p * 2),
                ("UniqueProcessId", ctypes.c_void_p),
                ("InheritedFromUniqueProcessId", ctypes.c_void_p),
            ]

        ntdll = ctypes.windll.ntdll
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        def parent_of(pid: int) -> Optional[int]:
            handle = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if not handle:
                return None
            try:
                info = ProcessBasicInformation()
                status = ntdll.NtQueryInformationProcess(
                    handle, 0, ctypes.byref(info), ctypes.sizeof(info), None
                )
                if status != 0 or not info.InheritedFromUniqueProcessId:
                    return None
                return int(info.InheritedFromUniqueProcessId)
            finally:
                kernel32.CloseHandle(handle)

        chain: List[int] = []
        pid: Optional[int] = os.getpid()
        for _ in range(max_depth):
            pid = parent_of(pid)
            if not pid or pid in chain:
                break
            chain.append(pid)
        return chain


def _load_pywin32() -> Optional[tuple]:
    """Import pywin32 lazily; None when unavailable (D5 guarded dependency)."""
    try:
        import win32api
        import win32con
        import win32gui

        return (win32gui, win32api, win32con)
    except ImportError:
        return None


def get_window_manager() -> WindowManager:
    """Platform factory: the only place adapter selection happens (D5/D10)."""
    if platform.system() == "Windows":
        return WindowsWindowManager()
    return FallbackWindowManager()

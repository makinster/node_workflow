"""Focused tests for backend.window_manager (FO4, docs/FILE_OUTPUT_BUILD_PLAN.md).

Covers the factory, the fallback manager, the FakeWindowManager test double,
and the pure preset→rect geometry (D3). The pywin32 branch is import-guarded
and verified manually on Windows per the FO7 protocol — not here.

Run from AttackOfTheNodes/:
    python -m pytest tests/test_window_manager.py -v
"""

import platform
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.window_manager import (  # noqa: E402
    CAP_OPEN,
    CAP_PLACE,
    FakeWindowManager,
    FallbackWindowManager,
    Monitor,
    PLACE_LEFT_OF_AOTN,
    PLACE_OS_DEFAULT,
    PLACE_OTHER_MONITOR,
    PLACE_RIGHT_HALF,
    PLACE_RIGHT_OF_AOTN,
    PLACEMENT_PRESETS,
    Rect,
    WindowRef,
    WindowsWindowManager,
    get_window_manager,
    placement_rect,
)


PRIMARY = Monitor(
    bounds=Rect(0, 0, 1920, 1080),
    work_area=Rect(0, 0, 1920, 1040),  # 40px taskbar
    is_primary=True,
)
SECONDARY = Monitor(
    bounds=Rect(1920, 0, 2560, 1440),
    work_area=Rect(1920, 0, 2560, 1440),
)
# AOTN's terminal sits on the left 60% of the primary monitor.
AOTN_RECT = Rect(100, 100, 1000, 800)


# ---------------------------------------------------------------------------
# Factory + fallback manager
# ---------------------------------------------------------------------------

def test_factory_returns_platform_manager():
    manager = get_window_manager()
    if platform.system() == "Windows":
        assert isinstance(manager, WindowsWindowManager)
    else:
        assert isinstance(manager, FallbackWindowManager)


def test_fallback_capabilities_are_open_only():
    assert FallbackWindowManager().capabilities() == {CAP_OPEN}


def test_fallback_opens_via_os_opener(monkeypatch):
    import backend.window_manager as wm

    launched = []
    monkeypatch.setattr(
        wm.subprocess,
        "Popen",
        lambda cmd, **kwargs: launched.append(cmd),
    )
    manager = FallbackWindowManager()
    ref = manager.open_path("/tmp/report.md", PLACE_RIGHT_OF_AOTN)

    assert ref is None, "Fallback has no window discovery"
    assert len(launched) == 1
    assert launched[0][0] in ("xdg-open", "open")
    assert launched[0][1] == "/tmp/report.md"


def test_fallback_launch_failure_is_soft(monkeypatch):
    import backend.window_manager as wm

    def boom(cmd, **kwargs):
        raise OSError("no opener")

    monkeypatch.setattr(wm.subprocess, "Popen", boom)
    manager = FallbackWindowManager()
    assert manager.open_path("/tmp/x.txt") is None  # no raise


def test_fallback_control_verbs_soft_fail():
    manager = FallbackWindowManager()
    ref = WindowRef(handle=1, path="/tmp/x.txt")
    assert manager.focus(ref) is False
    assert manager.minimize(ref) is False
    assert manager.close(ref) is False


# ---------------------------------------------------------------------------
# FakeWindowManager (the FO5/FO6 node-test double)
# ---------------------------------------------------------------------------

def test_fake_manager_records_calls_and_returns_refs():
    fake = FakeWindowManager()
    assert CAP_PLACE in fake.capabilities()

    ref = fake.open_path("/tmp/out.md", PLACE_RIGHT_OF_AOTN)
    assert isinstance(ref, WindowRef)
    assert ref.path == "/tmp/out.md"
    assert fake.opened == [("/tmp/out.md", PLACE_RIGHT_OF_AOTN)]

    assert fake.focus(ref) and fake.minimize(ref) and fake.close(ref)
    assert fake.focused == [ref]
    assert fake.minimized == [ref]
    assert fake.closed == [ref]


def test_fake_manager_discovery_failure_mode():
    fake = FakeWindowManager(discovery_fails=True)
    assert fake.open_path("/tmp/out.md") is None
    assert fake.opened, "The launch still happens when discovery fails (D4)"


# ---------------------------------------------------------------------------
# Preset → rect geometry (pure math, D3: position AND size)
# ---------------------------------------------------------------------------

def test_os_default_returns_none():
    assert placement_rect(PLACE_OS_DEFAULT, [PRIMARY, SECONDARY], AOTN_RECT) is None


def test_unknown_preset_returns_none():
    assert placement_rect("x=1920", [PRIMARY], AOTN_RECT) is None


def test_no_monitors_returns_none():
    assert placement_rect(PLACE_RIGHT_OF_AOTN, [], AOTN_RECT) is None


def test_every_preset_yields_full_position_and_size():
    for preset in PLACEMENT_PRESETS:
        rect = placement_rect(preset, [PRIMARY, SECONDARY], AOTN_RECT)
        if preset == PLACE_OS_DEFAULT:
            assert rect is None
        else:
            assert rect.width > 0 and rect.height > 0


def test_right_of_aotn_fills_space_to_monitor_edge():
    rect = placement_rect(PLACE_RIGHT_OF_AOTN, [PRIMARY, SECONDARY], AOTN_RECT)
    assert rect == Rect(1100, 0, 820, 1040)  # AOTN right edge → work-area edge


def test_left_of_aotn_degrades_sliver_to_half():
    # Only 100px sits left of AOTN — under MIN_SIDE_WIDTH → left half.
    rect = placement_rect(PLACE_LEFT_OF_AOTN, [PRIMARY, SECONDARY], AOTN_RECT)
    assert rect == Rect(0, 0, 960, 1040)


def test_left_of_aotn_fills_space_from_monitor_edge():
    centered_terminal = Rect(700, 100, 1000, 800)
    rect = placement_rect(PLACE_LEFT_OF_AOTN, [PRIMARY, SECONDARY], centered_terminal)
    assert rect == Rect(0, 0, 700, 1040)


def test_sliver_right_space_degrades_to_half():
    wide_terminal = Rect(0, 0, 1850, 1000)  # only 70px left of the edge
    rect = placement_rect(PLACE_RIGHT_OF_AOTN, [PRIMARY], wide_terminal)
    assert rect == Rect(960, 0, 960, 1040)


def test_other_monitor_targets_the_non_home_monitor():
    rect = placement_rect(PLACE_OTHER_MONITOR, [PRIMARY, SECONDARY], AOTN_RECT)
    assert rect == SECONDARY.work_area


def test_other_monitor_respects_mixed_resolutions_from_secondary_home():
    # AOTN on the 2560x1440 secondary: "other" is the primary work area.
    aotn_on_secondary = Rect(2000, 50, 1200, 900)
    rect = placement_rect(
        PLACE_OTHER_MONITOR, [PRIMARY, SECONDARY], aotn_on_secondary
    )
    assert rect == PRIMARY.work_area


def test_other_monitor_single_monitor_degrades_to_current():
    rect = placement_rect(PLACE_OTHER_MONITOR, [PRIMARY], AOTN_RECT)
    assert rect == PRIMARY.work_area


def test_same_monitor_right_half():
    rect = placement_rect(PLACE_RIGHT_HALF, [PRIMARY, SECONDARY], AOTN_RECT)
    assert rect == Rect(960, 0, 960, 1040)


def test_unresolvable_own_rect_degrades_side_presets_to_halves():
    # The D3 Windows Terminal caveat: no own rect → monitor-relative halves.
    right = placement_rect(PLACE_RIGHT_OF_AOTN, [PRIMARY, SECONDARY], None)
    left = placement_rect(PLACE_LEFT_OF_AOTN, [PRIMARY, SECONDARY], None)
    assert right == Rect(960, 0, 960, 1040)
    assert left == Rect(0, 0, 960, 1040)


def test_home_monitor_found_by_own_rect_center():
    aotn_on_secondary = Rect(3000, 100, 800, 600)
    rect = placement_rect(
        PLACE_RIGHT_HALF, [PRIMARY, SECONDARY], aotn_on_secondary
    )
    assert rect == Rect(1920 + 2560 - 1280, 0, 1280, 1440)


def test_windows_manager_without_pywin32_degrades():
    # On this Linux dev environment pywin32 can never import, so the
    # Windows manager must construct cleanly and report open-only.
    manager = WindowsWindowManager()
    assert manager._win32 is None
    assert manager.capabilities() == {CAP_OPEN}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

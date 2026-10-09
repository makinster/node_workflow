"""Keyboard recovery and validation navigation with production styling."""

from pathlib import Path

import pytest
from textual.containers import VerticalScroll

from frontend.app import AttackOfTheNodesApp
from frontend.screens.error_details import ErrorDetailsScreen
from tests.test_debug_nodes import _make_services


OPTIONS = ["RETRY", "SKIP", "TERMINATE_BRANCH", "TERMINATE_WORKFLOW"]


class ErrorApp(AttackOfTheNodesApp):
    CSS_PATH = str(Path(__file__).parent.parent / "frontend" / "styles.tcss")

    def __init__(self, payload):
        master, wm, mb, bus = _make_services()
        super().__init__(bus, wm._factory, wm, mb, master)
        self.payload = payload
        self.results = []

    async def on_ready(self):
        self._error_modal_open = "validation" not in self.payload
        await self.push_screen(ErrorDetailsScreen(self.payload), self._record_result)

    def _record_result(self, result):
        self.results.append(result)
        if "validation" not in self.payload:
            self._submit_recovery_from_modal(result)


def runtime_payload(long=False):
    return {
        "branch_id": "branch_test", "node_id": "file_node",
        "error_message": "File to view was not found: C:\\Users\\name\\test.md",
        "traceback": "\n".join(["FileNotFoundError: test.md"] * (50 if long else 2)),
        "options": OPTIONS,
    }


@pytest.mark.parametrize("width", [60, 100, 140])
@pytest.mark.parametrize("long", [False, True])
async def test_error_buttons_have_keyboard_focus_and_scroll(width, long):
    app = ErrorApp(runtime_payload(long))
    async with app.run_test(size=(width, 24)) as pilot:
        await pilot.pause()
        screen = app.screen
        card = screen.query_one("#modal-card", VerticalScroll)
        ids = [f"recovery-{option}" for option in OPTIONS] + ["close-error"]
        assert app.focused.id == ids[0]
        for index, button_id in enumerate(ids):
            if index:
                await pilot.press("s" if index % 2 else "down")
                await pilot.pause()
            assert app.focused.id == button_id
            assert app.focused.region.intersection(card.content_region).height >= 1
        for index in range(len(ids) - 2, -1, -1):
            await pilot.press("w" if index % 2 else "up")
            await pilot.pause()
            assert app.focused.id == ids[index]
        await pilot.press("s", "e")
        await pilot.pause()
        assert app.results == [{"branch_id": "branch_test", "action": "SKIP"}]


@pytest.mark.parametrize("index", range(4))
async def test_keyboard_recovery_returns_requested_action(index):
    app = ErrorApp(runtime_payload())
    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        await pilot.press(*(["s"] * index), "enter")
        await pilot.pause()
        assert app.results == [{"branch_id": "branch_test", "action": OPTIONS[index]}]


@pytest.mark.parametrize("key", ["escape", "q", "ctrl+q", "e"])
async def test_error_keyboard_close(key):
    app = ErrorApp(runtime_payload())
    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        if key == "e":
            await pilot.press(*(["s"] * len(OPTIONS)))
        await pilot.press(key)
        await pilot.pause()
        assert app.results == [None]
        assert not app._error_modal_open


async def test_validation_error_keyboard_jump_and_close():
    payload = {"validation": {"errors": [
        {"node_id": f"node_{index}", "message": "Missing connection target"}
        for index in range(6)
    ], "warnings": []}}
    app = ErrorApp(payload)
    async with app.run_test(size=(60, 24)) as pilot:
        await pilot.pause()
        assert app.focused.id == "jump-validation-error-0"
        await pilot.press("s", "s", "enter")
        await pilot.pause()
        assert app.results == [{"action": "jump", "node_id": "node_2"}]
        await app.push_screen(ErrorDetailsScreen(payload), app.results.append)
        await pilot.pause()
        await pilot.press(*(["s"] * 6))
        await pilot.pause()
        assert app.focused.id == "close-error"
        await pilot.press("e")
        await pilot.pause()
        assert app.results[-1] is None

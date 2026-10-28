"""Large modals fill the terminal (owner, 2026-10-20): no unused strip on the
right or at the bottom; small dialogs may grow to the whole terminal.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_modal_size.py -v
"""

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from tests.test_contract_screens import _map
from frontend.screens.node_config import NodeConfigScreen

SIZE = (120, 40)


def card_size(make_screen):
    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(make_screen())

    async def run():
        app = Host()
        async with app.run_test(size=SIZE) as pilot:
            await pilot.pause(0.1)
            region = app.screen.query_one("#modal-card").region
            return region.x, region.y, region.width, region.height

    return asyncio.run(run())


def test_node_config_fills_the_terminal():
    factory, workflow_map, ids = _map()
    node = ids["reader"]
    assert card_size(lambda: NodeConfigScreen(factory, workflow_map, node,
                                              workflow_map.get_node_data(node))) == (0, 0, *SIZE)


def test_a_long_small_dialog_can_use_the_whole_height():
    class Long(ModalScreen):
        def compose(self) -> ComposeResult:
            with Vertical(id="modal-card"):
                yield Static("\n".join(f"line {n}" for n in range(80)))

    assert card_size(Long)[3] == SIZE[1]


# -- #93 review: actions stay reachable (2026-10-20) ---------------------------------------

import pytest
from tests.ui_sizes import LAYOUT_SIZES  # noqa: E402

from backend import persistence  # noqa: E402


def buttons_inside(make_screen, ids, size, focus=None, whole=False):
    """Whether each button lies inside the card's content area (after
    focusing ``focus``, which scrolls a tall dialog to it). ``whole``: and
    nothing in the card is cut off (it does not need to scroll)."""
    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(make_screen())

    async def run():
        app = Host()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.2)
            if focus:
                app.screen.query_one(f"#{focus}").focus()
                await pilot.pause(0.2)
            card = app.screen.query_one("#modal-card").content_region
            inside = all(card.contains_region(app.screen.query_one(f"#{i}").region) for i in ids)
            return inside and not (whole and app.screen.query_one("#modal-card").max_scroll_y)

    return asyncio.run(run())


@pytest.mark.parametrize("size", LAYOUT_SIZES)
def test_options_shows_save_and_cancel(size):
    from backend.configuration_manager import DEFAULT_SETTINGS
    from frontend.screens.settings import SettingsScreen

    class Configuration:
        def get_all(self):
            return dict(DEFAULT_SETTINGS)

    assert buttons_inside(lambda: SettingsScreen(Configuration()), ["save-settings", "cancel-settings"], size)


@pytest.mark.parametrize("size", LAYOUT_SIZES)
def test_a_full_file_window_shows_open_and_close(size, tmp_path, monkeypatch):
    from frontend.screens.workflow_library import WorkflowLibraryScreen

    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    for index in range(20):
        persistence.save_workflow(f"wf_{index:02d}", {"name": f"Workflow {index:02d}", "nodes": {}})
    assert buttons_inside(WorkflowLibraryScreen, ["load-workflow-library", "cancel-workflow-library"], size)


def test_a_tall_row_editor_scrolls_to_its_buttons():
    from frontend.widgets.contract_rows import INPUT, ContractRowEditor

    row = {"name": "report", "type": "file", "to": "Both", "vault_key": "report"}
    assert buttons_inside(lambda: ContractRowEditor(INPUT, row, []), ["confirm-row"], (80, 24),
                          focus="confirm-row")


@pytest.mark.parametrize("size", LAYOUT_SIZES)
def test_a_long_keep_picker_shows_its_whole_button_row(size):
    from frontend.screens.branch_keep_selector_screen import BranchKeepSelectorScreen

    ports = [f"path_{index}" for index in range(64)]
    assert buttons_inside(lambda: BranchKeepSelectorScreen("b1", "Dispatch", ports, required=1),
                          ["choose-branch-keep", "cancel-branch-keep"], size, whole=True)

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

"""Mounted Wait Until layout, navigation and save-contract tests."""
import asyncio
from copy import deepcopy
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Input, SelectionList, Static, TabPane, TabbedContent

from frontend.screens.node_config import NodeConfigScreen
from tests.test_debug_nodes import _make_services


def make_screen():
    _, wm, _, _ = _make_services()
    wm.create_new('wait_ui')
    wait = wm.add_node('wait_until_node')
    target = wm.add_node('user_text_input_node')
    downstream = wm.add_node('chat_completion_node')
    wm.connect(wait, 'default', downstream, 'prompt')
    wm.update_node_config(wait, {
        'target_node_ids': [target], 'timeout_seconds': 0.0, 'custom_note': 'keep',
        'membank_inputs': ['old_read'], 'membank_outputs': [{'id': 'old_write'}],
        'transient_outputs': [{'port': 'default', 'name': 'old'}],
    })
    return wm, wait, target, downstream


class ConfigApp(App):
    CSS_PATH = str(Path(__file__).resolve().parents[1] / "frontend/styles.tcss")
    def __init__(self, screen, results):
        super().__init__()
        self.config_screen = screen
        self.results = results

    def on_mount(self):
        self.push_screen(self.config_screen, self.results.append)


@pytest.mark.parametrize('width', [60, 100, 140])
def test_wait_layout_navigation_and_clean_save(width):
    async def check():
        wm, wait, target, _ = make_screen()
        for i in range(20):
            node = wm.add_node('no_op_node')
            wm.update_node_alias(node, f'Other {i:02d}')
        original = deepcopy(wm.get_node_data(wait))
        screen = NodeConfigScreen(wm._factory, wm, wait, wm.get_node_data(wait))
        results = []
        app = ConfigApp(screen, results)
        async with app.run_test(size=(width, 24)) as pilot:
            await pilot.pause()
            assert [p.id for p in screen.query(TabPane)] == ['node-config-tab-core', 'node-config-tab-connections']
            for widget_id in ['membank-reads', 'membank-inputs', 'membank-writes',
                              'membank-output-count', 'transient-output-name-default',
                              'show-previous-output', 'show-payload-vault-payload']:
                assert not screen.query(f'#{widget_id}')
            alias = screen.query_one('#alias-input', Input)
            targets = screen.query_one('#wait-targets', SelectionList)
            timeout = screen.query_one('#field-timeout_seconds', Input)
            tabs = screen.query_one(TabbedContent)
            assert app.focused is alias
            assert not alias.editing
            assert targets.selected == [target]
            await pilot.press('s')
            assert app.focused is targets
            targets.highlighted = len(targets._options) - 1
            await pilot.press('s')
            assert app.focused is timeout
            assert timeout.region.y < 24
            targets.highlighted = 0
            app.set_focus(targets)
            await pilot.press('w')
            assert app.focused is alias
            await pilot.press('2')
            await pilot.pause()
            assert tabs.active == 'node-config-tab-connections'
            await pilot.press('1')
            await pilot.pause()
            assert tabs.active == 'node-config-tab-core'
            assert targets.selected == [target]
            app.set_focus(targets)
            targets.highlighted = len(targets._options) - 1
            await pilot.pause()
            remembered_scroll = targets.scroll_y
            await pilot.press('2', '1')
            await pilot.pause()
            assert app.focused is targets
            assert targets.highlighted == len(targets._options) - 1
            assert targets.scroll_y == remembered_scroll
            app.set_focus(alias)
            await pilot.press('e', 'w', 's', 'a', 'd', '2')
            assert alias.value.endswith('wsad2')
            assert tabs.active == 'node-config-tab-core'
            await pilot.press('escape')
            assert wm.get_node_data(wait) == original
            await pilot.press('ctrl+s')
            await pilot.pause()
            config = results[0]['config']
            assert config['target_node_ids'] == [target]
            assert config['timeout_seconds'] == 0
            assert config['custom_note'] == 'keep'
            assert config['membank_inputs'] == config['membank_outputs'] == config['transient_outputs'] == []
            assert wm.get_node_data(wait) == original  # caller owns applying Save
            wm.update_node_config(wait, config)
            from backend.validator import derive_input_sources
            assert not any(s['type'] == 'membank' for s in derive_input_sources(wm.get_all_node_data())[wait])
    asyncio.run(check())


@pytest.mark.parametrize('invalid_kind', ['missing', 'self', 'downstream'])
def test_unavailable_wait_target_requires_explicit_removal(invalid_kind):
    async def check():
        wm, wait, target, downstream = make_screen()
        invalid = {'missing': 'gone_node', 'self': wait, 'downstream': downstream}[invalid_kind]
        config = dict(wm.get_node_data(wait)['config'])
        config['target_node_ids'] = [target, invalid]
        wm.update_node_config(wait, config)
        screen = NodeConfigScreen(wm._factory, wm, wait, wm.get_node_data(wait))
        results = []
        async with ConfigApp(screen, results).run_test() as pilot:
            await pilot.pause()
            targets = screen.query_one('#wait-targets', SelectionList)
            assert set(targets.selected) == {target, invalid}
            screen.action_save()
            assert not results
            assert 'Remove unavailable' in str(screen.query_one('#wait-config-error', Static).content)
            targets.deselect(invalid)
            screen.action_save()
            await pilot.pause()
            assert results[0]['config']['target_node_ids'] == [target]
    asyncio.run(check())


@pytest.mark.parametrize('bad_timeout', ['oops', '-1', 'nan', 'inf', ''])
def test_wait_timeout_validation_and_cancel(bad_timeout):
    async def check():
        wm, wait, _, _ = make_screen()
        original = deepcopy(wm.get_node_data(wait))
        screen = NodeConfigScreen(wm._factory, wm, wait, wm.get_node_data(wait))
        results = []
        async with ConfigApp(screen, results).run_test() as pilot:
            await pilot.pause()
            screen.query_one('#field-timeout_seconds', Input).value = bad_timeout
            screen.action_save()
            assert not results
            assert 'nonnegative number' in str(screen.query_one('#wait-config-error', Static).content)
            screen.action_cancel()
            await pilot.pause()
            assert results == [None]
            assert wm.get_node_data(wait) == original
    asyncio.run(check())


def test_wait_target_toggle_empty_selection_and_no_options():
    async def check():
        wm, wait, target, _ = make_screen()
        screen = NodeConfigScreen(wm._factory, wm, wait, wm.get_node_data(wait))
        results = []
        app = ConfigApp(screen, results)
        async with app.run_test() as pilot:
            await pilot.pause()
            targets = screen.query_one('#wait-targets', SelectionList)
            app.set_focus(targets)
            targets.highlighted = next(i for i,o in enumerate(targets._options) if o.value == target)
            await pilot.press('enter')
            await pilot.pause()
            assert targets.selected == []
            assert not results
            assert 'continue immediately' in str(screen.query_one('#wait-target-summary', Static).content)
            screen.action_save()
            await pilot.pause()
            assert results[0]['config']['target_node_ids'] == []
        _, wm, _, _ = _make_services()
        wm.create_new('empty_wait')
        wait = wm.add_node('wait_until_node')
        results = []
        screen = NodeConfigScreen(wm._factory, wm, wait, wm.get_node_data(wait))
        async with ConfigApp(screen, results).run_test() as pilot:
            await pilot.pause()
            assert not screen.query('#wait-targets')
            screen.action_save()
            await pilot.pause()
            assert results[0]['config']['target_node_ids'] == []
    asyncio.run(check())

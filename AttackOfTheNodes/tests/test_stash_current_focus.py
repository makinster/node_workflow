"""P is resolved from current focus, even after a text editing session."""
from copy import deepcopy
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Button, Checkbox, Select

from frontend.widgets.command_input import CommandInput, CommandTextArea
from frontend.widgets.local_model_picker import LocalModelPicker
from frontend.widgets.long_text import LongTextEditor
from tests.test_local_model_picker import Config, Options, discovery, server, settled
from tests.test_stash_insert import _config_app, stash


async def move_to(pilot, screen, target, *, options=False):
    if target in ('closed-select', 'open-select'):
        selector = screen.query_one(LocalModelPicker).query_one(Select) if options else screen.query_one('#field-write_mode', Select)
        # The review's click opens a menu; Escape leaves a closed Select focused.
        selector.scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click(selector)
        await pilot.pause()
        assert selector.expanded
        if target == 'closed-select':
            await pilot.press('escape')
            await pilot.pause()
            assert not selector.expanded and screen.focused is selector
        return screen.focused
    selectors = {
        'checkbox': Checkbox,
        'button': '#save-settings' if options else '#stash-insert-node-config',
        'other-text': '#setting-hermes_command' if options else '#alias-input',
    }
    widget = screen.query_one(selectors[target])
    widget.focus()
    await pilot.pause()
    assert screen.focused is widget
    return widget


def options_values(screen):
    return {w.id: w.value for cls in (CommandInput, Checkbox, LocalModelPicker) for w in screen.query(cls) if str(w.id).startswith("setting-")}


@pytest.mark.asyncio
@pytest.mark.parametrize('size', [(80, 24)])
@pytest.mark.parametrize('target', ['closed-select', 'open-select', 'checkbox', 'button', 'other-text'])
async def test_options_p_after_edit_never_changes_values_or_unsaved_state(discovery, monkeypatch, size, target):
    messages = []
    monkeypatch.setattr('frontend.notifications.notify_info', lambda app, msg: messages.append(msg))
    app = Options(Config(discovery.url, discovery.tags['models'][0]['name']))
    async with app.run_test(size=size) as pilot:
        screen = app.screen
        await settled(pilot, screen.query_one(LocalModelPicker))
        original = options_values(screen)
        persisted = deepcopy(app.config.values)
        # A clean draft and an already edited draft must both retain their state.
        for dirty in (False, True):
            field = screen.query_one('#setting-local_model_server_url', CommandInput)
            field.focus()
            field.begin_edit()
            await pilot.press('end', '/')
            if not dirty:
                await pilot.press('backspace')
            await pilot.pause(.4)
            await settled(pilot, screen.query_one(LocalModelPicker))
            assert field.editing
            focused = await move_to(pilot, screen, target, options=True)
            before = deepcopy(options_values(screen))
            unsaved = before != original
            assert unsaved == dirty
            count = len(messages)
            await pilot.press('p')
            await pilot.pause()
            assert options_values(screen) == before
            assert (options_values(screen) != original) == unsaved
            assert screen.focused is focused
            assert app.saved == [] and app.config.get_all() == persisted
            assert messages[count:] == ["Stash text can't go into this field"]
            if target == 'open-select':
                await pilot.press('escape')
        expected = options_values(screen)
        await pilot.press('ctrl+s')
        await pilot.pause()
        assert app.saved[0]['settings']['local_model_server_url'] == expected['setting-local_model_server_url']
        assert not app.saved[0]['settings']['local_model_server_url'].endswith('p')


@pytest.mark.asyncio
@pytest.mark.parametrize('target', ['closed-select', 'open-select', 'checkbox', 'button', 'other-text'])
async def test_node_p_after_edit_preserves_form_and_workflow_dirty_state(stash, monkeypatch, target):
    messages = []
    monkeypatch.setattr('frontend.notifications.notify_info', lambda app, msg: messages.append(msg))
    app, open_config = _config_app(stash, 'file_output_node', {'file_path_source': 'Configured', 'file_path': '/tmp/report.txt'})
    async with app.run_test(size=(120, 40)) as pilot:
        screen = await open_config(pilot)
        await pilot.press('2')
        await pilot.pause()
        screen.workflow_map.mark_saved()
        for dirty in (False, True):
            field = screen.query_one('#field-file_path', CommandInput)
            field.focus()
            field.begin_edit()
            await pilot.press('end', 'x')
            if not dirty:
                await pilot.press('backspace')
            await pilot.pause()
            assert field.editing
            focused = await move_to(pilot, screen, target)
            before = deepcopy(screen._get_form_values())
            persisted = deepcopy(screen.workflow_map.get_node_data(screen.node_id))
            state = (screen._is_dirty(), screen.workflow_map.is_dirty)
            assert state[0] == dirty
            count = len(messages)
            await pilot.press('p')
            await pilot.pause()
            assert screen._get_form_values() == before
            assert screen.workflow_map.get_node_data(screen.node_id) == persisted
            assert (screen._is_dirty(), screen.workflow_map.is_dirty) == state
            assert screen.focused is focused
            assert messages[count:] == ["Stash text can't go into this field"]
            if target == 'open-select':
                await pilot.press('escape')


@pytest.mark.asyncio
async def test_long_text_p_on_button_after_typing_keeps_draft_unchanged(monkeypatch):
    messages = []
    monkeypatch.setattr('frontend.notifications.notify_info', lambda app, msg: messages.append(msg))
    class Host(App):
        CSS_PATH = str(Path(__file__).parents[1] / 'frontend/styles.tcss')
        def on_mount(self): self.push_screen(LongTextEditor('Keep text'))
        def action_stash(self, *a, **kw): raise AssertionError('A button cannot open Stash')
    app = Host()
    async with app.run_test() as pilot:
        screen = app.screen
        area = screen.query_one(CommandTextArea)
        for dirty in (False, True):
            area.focus()
            area.begin_edit()
            await pilot.press('end', 'x')
            if not dirty:
                await pilot.press('backspace')
            button = screen.query_one('#long-text-cancel', Button)
            button.focus()
            await pilot.pause()
            before = (area.text, screen.saved_value, screen.changed)
            assert screen.changed == dirty
            count = len(messages)
            await pilot.press('p')
            await pilot.pause()
            assert (area.text, screen.saved_value, screen.changed) == before
            assert screen.focused is button
            assert messages[count:] == ["Stash text can't go into this field"]

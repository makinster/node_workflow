"""Cross-branch user answers must be readable when Wait Until releases."""
import asyncio

import pytest

from backend.events import NODE_EXECUTION_UPDATE, USER_INPUT_NEEDED
from tests.test_chat_completion_node import FakeClient, FakeSecrets, _patch_client, _make_context
from tests.test_debug_nodes import _make_services


@pytest.mark.parametrize('target_format', ['list', 'string'])
@pytest.mark.parametrize('continue_session', [False, True])
@pytest.mark.parametrize('wait_timeout', [0.0, 2.0])
def test_wait_until_releases_llm_after_answer_is_published(monkeypatch, target_format, continue_session, wait_timeout):
    async def check():
        master, wm, memory, bus = _make_services()
        wm.create_new('wait_until_vault')
        start, fork, wait, chat, answer, end = [wm.add_node(t) for t in (
            'start_node', 'branch_node', 'wait_until_node', 'chat_completion_node',
            'user_text_input_node', 'end_node')]
        wm.update_node_config(answer, {'prompt': 'Answer?', 'membank_outputs': [
            {'id': 'user_text', 'output': 'user_text'}]})
        wm.update_node_config(wait, {'target_node_ids': [answer] if target_format == 'list' else answer,
                                     'timeout_seconds': wait_timeout})
        # A zero Wait Until timeout must outlast this global timeout.
        monkeypatch.setitem(master._configuration_manager._settings, 'node_timeout_seconds', .005)
        config = wm._factory.create_config_template('chat_completion_node')
        config.update({'prompt_source': 'Continue AI session' if continue_session else 'Configured',
                       'prompt': 'Respond to the user', 'api_key_secret': 'test_key',
                       'document_source': 'Vault', 'document_vault_key': 'user_text',
                       'continue_session_key': 'session', 'vault_write_key': 'llm_reply'})
        wm.update_node_config(chat, config)
        for source, port, target, target_port in [
            (start, 'default', fork, 'input'), (fork, 'path_a', wait, 'input'),
            (wait, 'default', chat, 'prompt'), (chat, 'default', end, 'input'),
            (fork, 'path_b', answer, 'input')]:
            wm.connect(source, port, target, target_port)
        client = FakeClient()
        _patch_client(monkeypatch, client)
        master._secrets_manager = FakeSecrets({'test_key': 'test-only'})
        requested = asyncio.Event()
        requests, events, completed_values = [], [], []
        def request(payload):
            requests.append(payload)
            requested.set()
        bus.subscribe(USER_INPUT_NEEDED, request)
        bus.subscribe(NODE_EXECUTION_UPDATE, lambda p: events.append((p['node_id'], p['status'])))
        original_mark = master.mark_node_completed
        async def mark(node_id):
            if node_id == answer:
                completed_values.append((memory.read_persistent('user_text'),
                                         memory.read_transient(answer, 'default')))
            await original_mark(node_id)
        master.mark_node_completed = mark
        try:
            await master.start_workflow()
            if continue_session:
                master._run_session.append_chat_message('session', 'user', 'Earlier question')
                master._run_session.append_chat_message('session', 'assistant', 'Earlier reply')
                memory.store_persistent('session', {'type': 'ai_session', 'ref_key': 'session'})
            await asyncio.wait_for(requested.wait(), 1)
            await asyncio.sleep(.02)
            assert (wait, 'running') in events
            assert (wait, 'done') not in events
            assert (chat, 'running') not in events
            assert not client.calls
            assert answer not in master.completed_nodes
            master.submit_user_input(requests[0]['branch_id'], 'My cross-branch answer')
            await asyncio.wait_for(master.wait_for_completion(), 3)
            assert completed_values == [('My cross-branch answer', 'My cross-branch answer')]
            assert master.state.value == 'FINISHED'
            assert memory.read_persistent('llm_reply') == 'mock response'
            assert len(client.calls) == 1
            assert 'My cross-branch answer' in client.calls[0]['messages'][-1]['content']
            assert events.index((answer, 'done')) < events.index((chat, 'running'))
        finally:
            master.stop()
            await asyncio.wait_for(master.wait_for_completion(), 3)
    asyncio.run(asyncio.wait_for(check(), 6))


@pytest.mark.parametrize('declaration', [{'id': 'answer'}, {'output': 'answer'},
                                       {'id': 'old', 'output': 'answer'}])
@pytest.mark.parametrize('value', ['', 'hello'])
def test_user_input_publishes_declared_keys(declaration, value):
    from backend.nodes.user_text_input_node import UserTextInputNode
    async def check():
        context, signals = _make_context()
        async def read(prompt):
            return value
        context.signal_waiting_for_input = read
        node = UserTextInputNode('input', {'membank_outputs': [declaration]})
        await node.execute(context)
        assert context.memory_bank.read_persistent('answer', 'MISSING') == value
        assert signals['done']['data']['default'] == value
    asyncio.run(check())


def test_stop_during_input_does_not_publish_or_complete_target():
    async def check():
        master, wm, memory, bus = _make_services()
        wm.create_new('stop_input_vault')
        start, answer = [wm.add_node(t) for t in ('start_node', 'user_text_input_node')]
        wm.update_node_config(answer, {'membank_outputs': [{'id': 'answer'}]})
        wm.connect(start, 'default', answer, 'input')
        requested = asyncio.Event()
        bus.subscribe(USER_INPUT_NEEDED, lambda p: requested.set())
        try:
            await master.start_workflow()
            await asyncio.wait_for(requested.wait(), 1)
            master.stop()
            await asyncio.wait_for(master.wait_for_completion(), 2)
            assert answer not in master.completed_nodes
            assert 'answer' not in memory.get_state()['persistent']
            assert memory.read_transient(answer, 'default', 'MISSING') == 'MISSING'
        finally:
            master.stop()
    asyncio.run(check())


@pytest.mark.parametrize('answer', ['w', 's', 'what is your answer', 'some words'])
def test_user_input_dialog_preserves_navigation_letters(answer):
    from textual.app import App
    from frontend.screens.user_input import UserInputScreen
    from frontend.widgets.command_input import CommandInput

    async def check():
        submitted = []
        class InputApp(App):
            def on_mount(self):
                self.push_screen(UserInputScreen('branch', 'node', 'Answer?'), submitted.append)
        app = InputApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            field = app.screen.query_one('#user-input-value', CommandInput)
            await pilot.press(*['space' if c == ' ' else c for c in answer])
            assert field.value == answer
            assert app.focused is field
            await pilot.press('ctrl+enter')
            await pilot.pause()
            assert submitted == [{'branch_id': 'branch', 'value': answer}]
    asyncio.run(check())

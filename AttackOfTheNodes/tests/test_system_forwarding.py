"""Standard System-node forwarding keeps the computed report in the Vault."""
import os
import shutil
import time
from types import SimpleNamespace

import pytest
from tests.ui_sizes import LAYOUT_SIZES
from textual.app import App
from textual.widgets import Checkbox
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_factory import NodeFactory
from backend.port_types import trace_producers
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen
from tests.test_system_nodes import git

NODE_TYPES = ('disk_space_node', 'git_status_node', 'file_age_node')
CASES = [('disk_space_node', 'Used percent', 25.0, 'number'),
         ('file_age_node', 'Hours', 2.0, 'number'),
         ('git_status_node', 'Clean', False, 'bool'),
         ('git_status_node', 'Branch', 'main', 'string'),
         ('git_status_node', 'Changed files', ['untracked.txt'], 'var'),
         ('git_status_node', 'Commits ahead', 0, 'number')]


@pytest.mark.asyncio
@pytest.mark.parametrize('forwarding', [False, True])
@pytest.mark.parametrize('node_type,report,expected,type_tag', CASES)
async def test_forwarding_preserves_incoming_identity_and_computed_vault_report(
        tmp_path, monkeypatch, forwarding, node_type, report, expected, type_tag):
    node = NodeFactory().create_node(node_type, 'report')
    if node_type == 'git_status_node':
        if shutil.which('git') is None:
            pytest.skip('git is not installed')
        git(tmp_path, 'init', '-q', '-b', 'main')
        (tmp_path / 'untracked.txt').write_text('new')
        node.config.update(folder=str(tmp_path), report=report)
    elif node_type == 'disk_space_node':
        monkeypatch.setattr(shutil, 'disk_usage', lambda path: SimpleNamespace(total=16, used=4, free=12))
        node.config.update(folder=str(tmp_path), report=report)
    else:
        target = tmp_path / 'report.txt'
        target.write_text('data')
        stamp = time.time() - 7200
        os.utime(target, (stamp, stamp))
        node.config.update(path=str(target), unit=report)
    node.config.update(dead_drop_passthrough=forwarding, transient_output=not forwarding,
                       vault_write=True, vault_write_key='computed')
    incoming = {'original': ['keep', 'this']}
    memory = MemoryBank(EventBus())
    done, errors = [], []
    context = NodeContext(node_id='report', branch_id='S1', run_id='test',
        inputs={'input': incoming}, memory_bank=memory,
        signal_done=done.append, signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None, wait_for_nodes=lambda *args: None,
        wait_for_merge=lambda *args: None, get_setting=lambda key: str(tmp_path))
    await node.execute(context)
    assert not errors
    assert memory.read_persistent('computed') == expected
    assert memory.read_persistent_by_type(type_tag)['computed'] == expected
    if forwarding:
        assert done[0]['data']['default'] is incoming
    else:
        assert done[0]['data']['default'] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('size', LAYOUT_SIZES)
@pytest.mark.parametrize('node_type', NODE_TYPES)
async def test_standard_forwarding_toggle_save_reopen(node_type, size):
    factory = NodeFactory()
    workflow = WorkflowMap(factory, EventBus())
    workflow.create_new('Forward reports')
    node_id = workflow.add_node(node_type)
    config = workflow.get_node_data(node_id)['config']
    config.update(vault_write=True, vault_write_key='computed')
    workflow.update_node_config(node_id, config)
    class Host(App):
        CSS_PATH = '../frontend/styles.tcss'
        def on_mount(self):
            self.push_screen(NodeConfigScreen(factory, workflow, node_id,
                                              workflow.get_node_data(node_id)))
    async with Host().run_test(size=size) as pilot:
        await pilot.press('3'); await pilot.pause()
        screen = pilot.app.screen
        assert not screen.query('#publish-downstream')
        forward = screen.query_one('#dead-drop-passthrough', Checkbox)
        assert str(forward.label) == 'Forward incoming payload unchanged'
        assert not forward.value
        forward.focus(); await pilot.press('space'); await pilot.pause()
        assert screen.query_one('#transient-output-name-default').disabled
        assert not screen.query_one('#downstream-name-row-default').display
        saved = screen._save_result()['config']
        assert saved['dead_drop_passthrough'] and not saved['transient_output']
        assert saved['vault_write'] and saved['vault_write_key'] == 'computed'
        for selector in ('#save-node-config', '#cancel-node-config'):
            assert screen.query_one(selector).region.bottom <= size[1]
        workflow.update_node_config(node_id, saved)
        pilot.app.push_screen(NodeConfigScreen(factory, workflow, node_id,
                                               workflow.get_node_data(node_id)))
        await pilot.pause(); await pilot.press('3'); await pilot.pause()
        reopened = pilot.app.screen
        forward = reopened.query_one('#dead-drop-passthrough', Checkbox)
        assert forward.value
        assert reopened.query_one('#vault-output-key-default').value == 'computed'
        forward.focus(); await pilot.press('space'); await pilot.pause()
        assert not reopened.query_one('#transient-output-name-default').disabled
        saved = reopened._save_result()['config']
        assert not saved['dead_drop_passthrough'] and saved['transient_output']
        assert saved['vault_write_key'] == 'computed'


@pytest.mark.parametrize('node_type', NODE_TYPES)
def test_forwarded_type_traces_upstream(node_type):
    factory = NodeFactory()
    workflow = WorkflowMap(factory, EventBus())
    workflow.create_new('Types')
    source = workflow.add_node('start_node')
    node_id = workflow.add_node(node_type)
    workflow.connect(source, 'default', node_id, 'input')
    config = workflow.get_node_data(node_id)['config']
    config['dead_drop_passthrough'] = True
    workflow.update_node_config(node_id, config)
    assert trace_producers(workflow.get_all_node_data(), factory, node_id, 'default') == [(source, 'string')]

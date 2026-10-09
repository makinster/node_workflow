"""Owner-reported saved file-chain provenance and routing-only summaries."""
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Input, Select, Static

from backend.file_refs import file_reference
from frontend.node_io_display import trace_transient_producer, output_display_name
from frontend.screens.node_config import NodeConfigScreen
from tests.test_debug_nodes import _make_services
from tests.generated.test_file_output_node import _make_context


async def test_writer_forwards_file_path_connection_when_content_is_configured(tmp_path):
    _, wm, _, _ = _make_services()
    wm.create_new('reported_writer')
    start = wm.add_node('start_node')
    manager = wm.add_node('file_view_node')
    writer = wm.add_node('file_output_node')
    wm.connect(start, 'default', manager, 'file')
    wm.connect(manager, 'default', writer, 'file_path')
    wm.update_node_config(manager, {'dead_drop_passthrough': True, 'transient_output': False})
    wm.update_node_config(writer, {'dead_drop_passthrough': True, 'transient_output': False,
        'content_source': 'Configured', 'content': 'written content',
        'file_path_source': 'Vault', 'file_path_vault_key': 'destination'})
    producer = trace_transient_producer(wm, wm._factory, writer, 'default')
    assert producer['node_id'] == start
    assert producer['data_type'] == 'string'
    assert producer['chain_node_ids'] == [start, manager, writer]
    path = tmp_path/'written.txt'
    context, done, errors = _make_context(inputs={'file_path': 'unchanged incoming greeting'})
    context.memory_bank.store_persistent('destination', file_reference(str(path)), type_tag='file')
    await wm.get_node_instance(writer).execute(context)
    assert not errors
    assert path.read_text() == 'written content'
    assert done[0]['data']['default'] == 'unchanged incoming greeting'


class ConfigApp(App):
    CSS_PATH = str(Path(__file__).parents[1]/'frontend/styles.tcss')
    def __init__(self, screen, results):
        super().__init__()
        self.target, self.results = screen, results
    def on_mount(self):
        self.push_screen(self.target, self.results.append)


@pytest.mark.parametrize('width', [60, 100, 140])
async def test_start_value_has_one_editor_and_routing_preview_updates(width):
    _, wm, mb, _ = _make_services()
    wm.create_new('start_preview')
    start = wm.add_node('start_node')
    wm.update_node_config(start, {'greeting': 'real value', 'transient_outputs': [{'port':'default', 'name':'misleading value'}]})
    assert output_display_name(wm._factory, wm.get_node_data(start), 'default') == 'Greeting'
    screen = NodeConfigScreen(wm._factory, wm, start, wm.get_node_data(start), memory_bank=mb)
    results = []
    async with ConfigApp(screen, results).run_test(size=(width, 30)) as pilot:
        await pilot.pause()
        await pilot.press('3')
        await pilot.pause()
        assert screen.query_one('#configured-output-preview-default', Static).region.height >= 2
        assert not screen.query('#transient-output-name-default')
        assert not screen.query('#transient-output-desc-default')
        assert 'real value' in str(screen.query_one('#configured-output-preview-default', Static).content)
        screen.query_one('#field-greeting', Input).value = 'edited once'
        await pilot.pause()
        assert 'edited once' in str(screen.query_one('#configured-output-preview-default', Static).content)
        screen.action_save()
        await pilot.pause()
        assert results[0]['config']['greeting'] == 'edited once'
        assert results[0]['config']['transient_outputs'] == []


@pytest.mark.parametrize('width', [60, 100, 140])
async def test_text_output_payload_tab_describes_vault_and_format(width):
    _, wm, mb, _ = _make_services()
    wm.create_new('output_preview')
    start = wm.add_node('start_node')
    output = wm.add_node('text_output_node')
    wm.connect(start, 'default', output, 'input')
    wm.update_node_config(start, {'vault_write': True, 'vault_write_key': 'message'})
    wm.update_node_config(output, {'input_source':'Vault', 'input_vault_key':'message', 'label':'Notice', 'template':'Result: {input}'})
    mb.store_persistent('message', 'the actual text', type_tag='string')
    screen = NodeConfigScreen(wm._factory, wm, output, wm.get_node_data(output), memory_bank=mb)
    async with ConfigApp(screen, []).run_test(size=(width, 30)) as pilot:
        await pilot.pause()
        await pilot.press('3')
        await pilot.pause()
        preview = screen.query_one('#formatted-output-preview', Static)
        assert preview.region.height >= 3
        assert 'Source: Vault: message' in str(preview.content)
        assert '[Notice] Result: the actual text' in str(preview.content)
        screen.query_one('#field-template', Input).value = 'Changed {input}'
        await pilot.pause()
        assert '[Notice] Changed the actual text' in str(preview.content)
        screen.query_one('#field-input_source', Select).value = 'Upstream payload'
        await pilot.pause()
        assert 'Source: Upstream payload' in str(preview.content)
        assert 'the actual text' not in str(preview.content)
        assert 'after the selected source' in str(preview.content)


@pytest.mark.parametrize('target_name', ['writer', 'writer_output'])
async def test_text_output_before_wait_releases_after_parallel_file_vault_write(tmp_path, target_name):
    import asyncio
    import json
    from backend.events import NODE_EXECUTION_UPDATE, RECOVERY_OPTIONS_AVAILABLE
    master, wm, mb, bus = _make_services()
    wm.create_new('reported_wait_file_vault')
    types = {'start':'start_node', 'split':'branch_node', 'delay':'sleep_node',
        'writer':'file_output_node', 'writer_output':'text_output_node',
        'before_wait':'text_output_node', 'wait':'wait_until_node',
        'reader':'file_reader_node', 'final':'text_output_node'}
    n = {key:wm.add_node(t) for key,t in types.items()}
    wm.update_node_config(n['delay'], {'seconds': .03})
    path = tmp_path/'cross_branch.txt'
    wm.update_node_config(n['writer'], {'file_path_source':'Configured', 'file_path':str(path),
        'content_source':'Configured', 'content':'cross branch contents', 'vault_write':True,
        'vault_write_key':'shared_file', 'dead_drop_passthrough':True, 'transient_output':False})
    wm.update_node_config(n['wait'], {'target_node_ids':[n[target_name]], 'timeout_seconds':1.0})
    wm.update_node_config(n['reader'], {'input_source':'Vault', 'input_vault_key':'shared_file'})
    for source, port, target, input_port in [
        ('start','default','split','input'), ('split','path_a','delay','input'),
        ('delay','default','writer','content'), ('writer','default','writer_output','input'),
        ('split','path_b','before_wait','input'), ('before_wait','default','wait','input'),
        ('wait','default','reader','input'), ('reader','default','final','input')]:
        wm.connect(n[source],port,n[target],input_port)
    wm.load_data(json.loads(json.dumps(wm.get_workflow_data_for_save())))
    events, errors = [], []
    bus.subscribe(NODE_EXECUTION_UPDATE, lambda p:events.append((p['node_id'],p['status'])))
    def recover(payload):
        errors.append(payload)
        master.submit_recovery_action(payload['branch_id'], 'TERMINATE_WORKFLOW')
    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, recover)
    try:
        for _ in range(2):
            events.clear()
            assert await master.start_workflow()
            await asyncio.wait_for(master.wait_for_completion(), 3)
            assert not errors
            assert (n['wait'], 'running') in events
            assert (n['wait'], 'done') in events
            assert events.index((n[target_name], 'done')) < events.index((n['wait'], 'done'))
            assert mb.read_transient(n['wait'], 'default') == '[Output] Workflow started'
            assert mb.read_transient(n['reader'], 'default') == 'cross branch contents'
            assert mb.read_transient(n['final'], 'default') == '[Output] cross branch contents'
    finally:
        master.stop()
        await asyncio.wait_for(master.wait_for_completion(), 3)


def test_branch_health_follows_connected_text_output_to_unmerged_beacon():
    from backend.branch_health import derive_branch_health, output_types_from_factory, ENDED_UNMERGED
    _, wm, _, _ = _make_services()
    wm.create_new('connected_output_health')
    split = wm.add_node('branch_node')
    output = wm.add_node('text_output_node')
    beacon = wm.add_node('branch_end_node')
    wm.connect(split, 'path_a', output, 'input')
    wm.connect(output, 'default', beacon, 'input')
    health = derive_branch_health(wm.get_all_node_data(), output_types_from_factory(wm._factory))
    branch = next(item for item in health if item.port == 'path_a')
    assert branch.state == ENDED_UNMERGED
    assert branch.terminus_node_id == beacon


@pytest.mark.parametrize('payload', [42, {'type':'file', 'path':'/not/read/by/text-output', 'ref_key':'file:test'}])
async def test_text_output_formats_nontext_without_dereferencing_files(payload):
    from backend.node_factory import NodeFactory
    node = NodeFactory().create_node('text_output_node', 'output')
    context, done, errors = _make_context(inputs={'input':payload})
    await node.execute(context)
    assert not errors
    assert done[0]['data']['default'] == f'[Output] {payload}'
    assert not done[0].get('terminate_branch')

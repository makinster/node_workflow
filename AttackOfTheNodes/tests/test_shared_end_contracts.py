"""Real local engine proof for shared inputs/Ends and saved-file display."""
from collections import Counter
import json

import pytest

from tests.test_node_metadata_behavior import engine
from tests.test_meta_nodes import runner as node_runner


@pytest.mark.asyncio
@pytest.mark.parametrize('shared_output', [False, True])
async def test_parallel_arrivals_run_shared_nodes_and_end_separately(engine, shared_output):
    wm = engine.workflow_map
    wm.create_new('Shared End proof')
    start = wm.add_node('start_node')
    branch = wm.add_node('branch_node')
    end = wm.add_node('end_node')
    wm.update_node_config(end, {'record_line': True, 'message': 'finished here'})
    wm.connect(start, 'default', branch, 'input')
    if shared_output:
        shown = wm.add_node('text_output_node')
        wm.update_node_config(shown, {'label': '', 'template': '{input}'})
        wm.connect(shown, 'default', end, 'input')
    for port, text in [('path_a', 'left value'), ('path_b', 'right value')]:
        source = wm.add_node('concat_node')
        wm.update_node_config(source, {'template': text})
        wm.connect(branch, port, source, 'input')
        if shared_output:
            wm.connect(source, 'default', shown, 'input')
        else:
            output = wm.add_node('text_output_node')
            wm.update_node_config(output, {'label': '', 'template': '{input}'})
            wm.connect(source, 'default', output, 'input')
            wm.connect(output, 'default', end, 'input')
    events = []
    engine.subscribe('NODE_EXECUTION_UPDATE', events.append)
    await engine.start()
    result = await engine.wait()
    assert result.exit_code == 0 and not result.errors
    assert Counter(map(str, result.outputs)) == Counter([
        'left value', 'right value', '[END] finished here', '[END] finished here'])
    arrivals = [event for event in events if event['node_id'] == end and event['status'] == 'done']
    assert len(arrivals) == 2 and len({event['branch_id'] for event in arrivals}) == 2
    if shared_output:
        assert len([e for e in events if e['node_id'] == shown and e['status'] == 'done']) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('template', ['{input}', '{input[path]}'])
async def test_file_write_record_display_is_distinct_from_path(tmp_path, template):
    saved = tmp_path / 'saved.txt'
    writer, ctx, _, done, errors = node_runner('file_output_node', dict(
        content_source='Configured', content='Saved payload', file_path=str(saved),
        write_mode='Create unique', open_after_write=False))
    await writer.execute(ctx)
    assert not errors
    ref = done[0]['data']['default']
    assert set(ref) == {'type', 'ref_key', 'path'} and ref['path'] == str(saved)
    output, ctx, memory, done, errors = node_runner('text_output_node', dict(
        label='', template=template), ref)
    await output.execute(ctx)
    assert not errors
    rendered = done[0]['data']['default']
    assert rendered == str(memory.read_persistent('output_log')[0])
    if template == '{input}':
        assert rendered == str(ref) and rendered != ref['path']
    else:
        assert rendered == ref['path']


@pytest.mark.asyncio
async def test_full_contracts_and_judge_explain_shared_arrivals_and_file_display():
    from backend import authoring, node_catalogue
    from backend.node_factory import NodeFactory
    from tools.draft_trials import runner
    factory = NodeFactory()
    config = factory.metadata_for_type('node_catalogue_node')['default_config']
    records = await node_catalogue.build(factory, dict(config, format='JSON', max_chars=200000))
    assert 'Each arriving path runs the node separately' in records['input_routing']
    assert authoring.describe_node_type(factory, 'end_node')['input_routing'] == records['input_routing']
    text, _ = await runner.contract_inventory()
    assert 'Several paths may share one End input' in text
    assert 'Each arriving path runs End separately and finishes there' in text
    for kind in ('file_output_node', 'text_output_node'):
        contract = factory.metadata_for_type(kind)['node_metadata']['execution_contract']
        assert '{input} shows the whole file record {type, ref_key, path}' in contract['notes']
        assert 'To show the saved path, use {input[path]}' in contract['notes']
    spec = json.loads(runner.SPEC.read_text())
    template = spec['nodes']['judge_question']['config']['template']
    prompt = template.format_map(dict(draft_request='',clarification_answer='',frozen_requirements='',draft_text='',spec_check=''))
    assert 'Unconnected means a node no path reaches' in prompt
    assert 'Several paths ending at one shared node is not a problem' in prompt
    assert '{input} after File Write shows the whole file record {type, ref_key, path}' in prompt
    assert 'use {input[path]}' in prompt

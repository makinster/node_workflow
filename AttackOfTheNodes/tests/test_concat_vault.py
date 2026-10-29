"""Local runtime proof and shared preflight diagnostics; no provider calls."""
import json

import pytest

from backend import authoring
from backend.node_factory import NodeFactory
from backend.vault_declarations import standard_vault_writes
from tests.test_meta_nodes import runner
from tests.test_node_metadata_behavior import engine


@pytest.mark.asyncio
@pytest.mark.parametrize('transient,forward', [(True, False), (False, False), (False, True)])
async def test_concat_writes_result_and_routes_payload(transient, forward):
    payload = {'keep': ['identity']}
    node, ctx, memory, done, errors = runner('concat_node', dict(
        template='Report: {review}', vault_write=True, vault_write_key='report',
        transient_output=transient, dead_drop_passthrough=forward), payload)
    memory.store_persistent('review', 'approved')
    await node.execute(ctx)
    assert not errors
    assert memory.read_persistent('report') == 'Report: approved'
    assert memory.read_persistent_by_type('string')['report'] == 'Report: approved'
    data = done[0]['data']
    assert data == ({'default': payload if forward else 'Report: approved'} if transient or forward else {})
    if forward:
        assert data['default'] is payload


@pytest.mark.asyncio
@pytest.mark.parametrize('template', ['A[{missing}] B[{input}]', '{input[missing]}', '{input.attr}', '{'])
async def test_concat_missing_key_or_bad_template_errors_without_publishing(template):
    node, ctx, memory, done, errors = runner('concat_node', dict(
        template=template, vault_write=True, vault_write_key='report'), 'hello')
    await node.execute(ctx)
    assert not done and len(errors) == 1
    assert 'Concat template failed' in str(errors[0])
    if '{missing}' in template:
        assert 'missing' in str(errors[0])
    assert 'report' not in memory.get_state()['persistent']


def draft(kind='concat_node', config=None):
    return dict(format='aotn-workflow/1', name='Vault proof', nodes={
        'start': {'type': 'start_node'}, 'work': {'type': kind, 'config': config or {}},
        'end': {'type': 'end_node'}}, connections=[
        {'from': 'start.default', 'to': 'work.input'},
        {'from': 'work.default', 'to': 'end.input'}])


@pytest.mark.parametrize('kind', ['text_output_node', 'text_transform_node', 'json_path_node', 'wait_until_node'])
def test_unsupported_standard_write_warns_and_declares_no_writer(kind):
    config = dict(vault_write=True, vault_write_key='phantom')
    factory = NodeFactory()
    assert standard_vault_writes(kind, config, factory.metadata_for_type(kind)) == {}
    result = authoring.check_workflow_spec(factory, draft(kind, config))
    assert any(d['code'] == 'vault_write_unsupported' and d['node'] == 'work'
               for d in result['diagnostics']), result


def test_concat_template_warns_about_no_earlier_writer():
    factory = NodeFactory()
    spec = draft(config={'template': '{missing} {input[path]} {{literal}}'})
    result = authoring.check_workflow_spec(factory, spec)
    warnings = [d for d in result['diagnostics'] if d['code'] == 'template_vault_key_unwritten']
    assert len(warnings) == 1 and 'missing' in warnings[0]['message'], result
    spec['nodes']['start']['config'] = dict(vault_write=True, vault_write_key='missing')
    assert not any(d['code'] == 'template_vault_key_unwritten' for d in
                   authoring.check_workflow_spec(factory, spec)['diagnostics'])


def test_every_unsupported_registered_type_warns_in_shared_check():
    """Retained shared keys must not invent a writer for any registered type."""
    factory = NodeFactory()
    for meta in factory.get_node_types_metadata():
        if 'vault' in ((meta.get('output_port_metadata') or {}).get('default') or {}).get('to', []):
            continue
        kind = meta['type']
        if kind == 'tombstone_node':
            continue  # Not authorable; execution always refuses it.
        config = dict(vault_write=True, vault_write_key='phantom')
        assert 'phantom' not in standard_vault_writes(kind, config, meta), kind
        result = authoring.check_workflow_spec(factory, draft(kind, config))
        assert any(d['code'] == 'vault_write_unsupported' and d['node'] == 'work'
                   for d in result['diagnostics']), (kind, result)


def test_unsupported_write_does_not_satisfy_a_required_vault_reader():
    spec = draft('text_transform_node', {'vault_write': True, 'vault_write_key': 'phantom'})
    spec['nodes']['end'] = {'type': 'text_output_node', 'config': {
        'input_source': 'Vault', 'input_vault_key': 'phantom'}}
    result = authoring.check_workflow_spec(NodeFactory(), spec)
    assert not result['ok']
    assert any(d['code'] == 'undeclared_vault_key' and 'phantom' in d['message']
               for d in result['diagnostics'])


@pytest.mark.asyncio
async def test_concat_blank_write_key_is_an_error():
    node, ctx, memory, done, errors = runner('concat_node', {'vault_write': True})
    await node.execute(ctx)
    assert not done and len(errors) == 1 and 'Vault output key' in str(errors[0])


@pytest.mark.asyncio
async def test_concat_result_reaches_a_downstream_vault_template(engine):
    wm = engine.workflow_map
    wm.create_new('Concat report')
    start = wm.add_node('start_node')
    first = wm.add_node('concat_node')
    second = wm.add_node('concat_node')
    shown = wm.add_node('text_output_node')
    wm.update_node_config(first, {'template': 'Review report', 'vault_write': True, 'vault_write_key': 'report'})
    wm.update_node_config(second, {'template': 'Summary: {report}'})
    wm.update_node_config(shown, {'label': '', 'template': '{input}'})
    for source, target in [(start, first), (first, second), (second, shown)]:
        wm.connect(source, 'default', target, 'input')
    await engine.start()
    result = await engine.wait()
    assert result.exit_code == 0 and not result.errors
    assert list(map(str, result.outputs)) == ['Summary: Review report']

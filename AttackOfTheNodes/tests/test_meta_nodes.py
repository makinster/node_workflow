"""Live registry contracts, shared validation parity, and check-only isolation."""
import asyncio
from copy import deepcopy
import json
import socket
import subprocess

import pytest

from backend import authoring, meta_workflow, node_catalogue, persistence
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from backend.save_manager import SaveManager
from backend.workflow_map import WorkflowMap


@pytest.fixture
def spec():
    return dict(format='aotn-workflow/1', name='A checked draft',
                nodes=dict(start=dict(type='start_node'), end=dict(type='end_node')),
                connections=[dict(**{'from': 'start.default', 'to': 'end.input'})])


def runner(kind, config=None, value=None):
    node = NodeFactory().create_node(kind, 'meta')
    node.config.update(config or {})
    memory = MemoryBank(EventBus())
    done, errors = [], []
    context = NodeContext(node_id='meta', branch_id='branch', run_id='run',
        inputs={'input': value}, memory_bank=memory, signal_done=done.append,
        signal_error=errors.append, signal_waiting_for_input=lambda _: None,
        wait_for_nodes=lambda *args: None, wait_for_merge=lambda *args: None)
    return node, context, memory, done, errors


def snapshot(directory):
    return {p.relative_to(directory).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in directory.rglob('*') if p.is_file()}


@pytest.fixture
def check_only(monkeypatch, tmp_path):
    library = tmp_path / 'workflows'
    library.mkdir()
    (library / 'owner.json').write_text('{"name":"Owner work","private":"untouched"}')
    monkeypatch.setattr(persistence, 'WORKFLOWS_DIR', library)
    before = snapshot(library)
    def forbidden(*args, **kwargs):
        raise AssertionError('check-only boundary crossed')
    for obj, names in [
        (persistence, ['write_json_atomic', 'save_workflow', 'delete_workflow', 'save_json_record']),
        (SaveManager, ['save_current_workflow']), (WorkflowMap, ['save']),
        (authoring, ['build_workflow', '_reload_problem', 'name_taken']),
        (socket, ['create_connection']), (socket.socket, ['connect', 'connect_ex']),
        (subprocess, ['Popen', 'run']),
    ]:
        for name in names:
            monkeypatch.setattr(obj, name, forbidden)
    # Construction or execution of any product node is forbidden. Metadata and
    # the ephemeral validation graph use neither factory method nor execute().
    monkeypatch.setattr(NodeFactory, 'create_node', forbidden)
    for cls in NodeFactory()._node_registry.values():
        monkeypatch.setattr(cls, 'execute', forbidden)
    yield forbidden
    assert snapshot(library) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('case', ['valid', 'warning', 'invalid', 'name_collision'])
async def test_shared_check_without_save_build_execute_or_network(spec, check_only, case):
    if case == 'warning':
        spec['nodes']['loose'] = dict(type='text_output_node')
    if case == 'invalid':
        spec['nodes']['end']['config'] = {'unknown_private_field': 'never quote this'}
    if case == 'name_collision':
        spec['name'] = 'Owner work'
    checked = authoring.check_workflow_spec(NodeFactory(), spec)
    if checked['ok']:
        value, report = await meta_workflow.check(NodeFactory(), json.dumps(spec), 32000)
        assert value == spec
        assert report['ok']
        assert report['warning_count'] == sum(d['level'] == 'warning' for d in checked['diagnostics'])
        assert 'ids' not in report
    else:
        with pytest.raises(NodeError) as err:
            await meta_workflow.check(NodeFactory(), json.dumps(spec), 32000)
        assert err.value.code == 'spec_invalid'
        assert 'never quote this' not in str(err.value)
        assert err.value.details['problems'][0]['field'] == 'config.unknown_private_field'
    # Prove the guard is armed, not just an unchanged empty directory.
    with pytest.raises(AssertionError, match='boundary crossed'):
        check_only()


@pytest.mark.parametrize('mutation', ['valid', 'unknown_type', 'unknown_key', 'bad_edge', 'warning'])
def test_cli_check_and_node_share_verdict_and_structured_diagnostics(spec, mutation):
    if mutation == 'unknown_type': spec['nodes']['end']['type'] = 'not_a_type'
    if mutation == 'unknown_key': spec['nodes']['end']['config'] = {'unknown': 3}
    if mutation == 'bad_edge': spec['connections'][0]['to'] = 'end.missing'
    if mutation == 'warning': spec['nodes']['extra'] = dict(type='text_output_node')
    old = authoring.build_workflow(NodeFactory(), spec, write=False)
    new = authoring.check_workflow_spec(NodeFactory(), spec)
    assert old['ok'] == new['ok']
    assert old['diagnostics'] == new['diagnostics']


@pytest.mark.asyncio
@pytest.mark.parametrize('source', ['Upstream payload', 'Vault', 'Configured'])
@pytest.mark.parametrize('node_form', ['keyed', 'list'])
async def test_check_sources_preserve_original_spec_and_typed_outputs(spec, source, node_form):
    supplied = spec if node_form == 'keyed' else {**spec, 'nodes': [dict(id=key, **node) for key, node in spec['nodes'].items()]}
    encoded = json.dumps(supplied)
    node, ctx, memory, done, errors = runner('check_workflow_spec_node',
        dict(input_source=source, input=encoded, input_vault_key='draft',
             vault_write=True, vault_write_key='checked', report_vault_write=True, report_vault_key='report'), encoded)
    memory.store_persistent('draft', encoded, type_tag='string')
    await node.execute(ctx)
    assert not errors
    assert done == [{'data': {'default': spec}}]
    assert memory.read_persistent('checked') == spec
    assert memory.read_persistent('report')['ok']
    assert 'ids' not in memory.read_persistent('report')
    assert set(done[0]['data']['default']['nodes']) == {'start', 'end'}


@pytest.mark.asyncio
@pytest.mark.parametrize('config,value,code', [
    ({}, '```json\n{}\n```', 'invalid_json'),
    ({}, {}, 'invalid_json'), ({}, 'NaN', 'invalid_json'),
    ({}, '"\\ud800"', 'invalid_json'), ({}, '1e999', 'invalid_json'),
    ({}, '{}', 'spec_invalid'), ({'max_spec': True}, '{}', 'invalid_config'),
    ({'input_source': 'Stash'}, '{}', 'invalid_config'),
    ({'dead_drop_passthrough': True}, '{}', 'invalid_config'),
    ({'vault_write': True, 'vault_write_key': ''}, '{}', 'invalid_config'),
    ({'vault_write': True, 'vault_write_key': 'same', 'report_vault_write': True,
      'report_vault_key': 'same'}, '{}', 'invalid_config'),
    ({'max_spec': 5}, '{"long":"value"}', 'spec_too_large'),
    ({}, '['*65+'0'+']'*65, 'spec_too_large'),
    ({}, json.dumps({'nodes': {str(n): {} for n in range(129)}}), 'spec_too_large'),
    ({}, json.dumps({'connections': [{}]*257}), 'spec_too_large'),
])
async def test_check_failure_never_publishes(config, value, code):
    node, ctx, memory, done, errors = runner('check_workflow_spec_node',
        dict(vault_write=True, vault_write_key='checked', report_vault_write=True,
             report_vault_key='report', **config) if not any(k in config for k in ('vault_write','report_vault_write')) else config,
        value)
    memory.store_persistent('checked', 'prior', type_tag='string')
    memory.store_persistent('report', 'prior report', type_tag='string')
    await node.execute(ctx)
    assert not done
    assert errors[0].code == code
    assert memory.read_persistent('checked') == 'prior'
    assert memory.read_persistent('report') == 'prior report'


@pytest.mark.asyncio
async def test_no_success_writes_even_when_cancelled_after_check(spec, monkeypatch):
    node, ctx, memory, done, errors = runner('check_workflow_spec_node',
        dict(vault_write=True, vault_write_key='out'), json.dumps(spec))
    real = authoring.check_workflow_spec
    def cancel(*args):
        result = real(*args)
        asyncio.current_task().cancel()
        return result
    monkeypatch.setattr(authoring, 'check_workflow_spec', cancel)
    task = asyncio.create_task(node.execute(ctx))
    with pytest.raises(asyncio.CancelledError): await task
    assert not done and not errors
    assert memory.read_persistent('out') is None


def test_problem_list_is_bounded_redacted_and_explicit_about_omissions():
    private = 'untrusted-private-config-value'
    diagnostics = [dict(node=f'node_{n}', field='config.'+'x'*1000, level='error',
                        code='unknown_config_key', message=private) for n in range(200)]
    message, details = meta_workflow.problem_report(diagnostics, invalid=True)
    assert private not in message + json.dumps(details)
    assert 0 < len(details['problems']) <= 100
    assert len(json.dumps(dict(message=message, details=details), ensure_ascii=False)) < 8000
    assert len(details['problems']) + details['omitted_count'] == 200
    assert 'omitted' in message and 'node_0' in message and 'config.' in message


@pytest.mark.asyncio
async def test_catalogue_complete_default_and_headroom():
    factory = NodeFactory()
    cfg = deepcopy(factory._node_registry['node_catalogue_node'].default_config)
    text = await node_catalogue.build(factory, cfg)
    # Catalogue v2: the full JSON outgrew the retained 64k default. It errors
    # visibly with both counts; an explicit larger cap returns it complete.
    with pytest.raises(NodeError) as too_large:
        await node_catalogue.build(factory, dict(cfg, format='JSON'))
    assert too_large.value.details['failed'] == 'characters'
    assert too_large.value.details['limit'] == 64000 and too_large.value.details['bytes']
    record = await node_catalogue.build(factory, dict(cfg, format='JSON', max_chars=node_catalogue.MAX_CHARS_LIMIT))
    kinds = {e['type'] for e in record['entries']}
    assert {'start_node','end_node','node_catalogue_node','check_workflow_spec_node'} <= kinds
    assert 'tombstone_node' not in kinds
    assert kinds == {r['type'] for r in authoring.list_node_types(factory)
                     if not node_catalogue.is_debug(factory.metadata_for_type(r['type']))
                     and not factory.metadata_for_type(r['type']).get('editor_only')}
    # Owner restored complete per-node descriptions. The full registry fits
    # the unchanged 64k cap; planning headroom applies to admitted contracts.
    assert cfg['max_chars'] == 64000 and len(text) <= 64000
    from backend.palette_selection import ADMITTED, CONTRACT_LIMIT
    admitted = await node_catalogue.build(factory, dict(cfg, scope='Exact IDs',
        type_ids=sorted(ADMITTED), max_chars=CONTRACT_LIMIT))
    assert len(admitted) * 1.2 <= CONTRACT_LIMIT
    assert record['schema_version'] == 2 and record['node_metadata_version'] == 1
    assert record['metadata_projection'] == 'full'
    assert all(e['entry_kind'] == 'node' and isinstance(e['inputs'], list)
               and isinstance(e['outputs'], list) for e in record['entries'])
    for e in record['entries']:
        for port in e['inputs'] + e['outputs']:
            assert {'id','name','data_type','required'} <= port.keys()
    assert record['ports_basis'] == 'defaults' and record['complete']
    assert 'input ("Spec") [string] required (upstream/vault/configured)' in text
    assert 'input ("Continue") [any] optional (upstream)' in text
    assert 'node node_catalogue_node |' in text
    # Detailed full catalogue may overflow by design. Filter to one entry.
    detailed = await node_catalogue.build(factory, dict(cfg, scope='Filtered', search='node_catalogue_node', detail='Detailed',format='JSON'))
    entry = detailed['entries'][0]
    assert entry['defaults']['max_chars'] == cfg['max_chars']
    assert isinstance(entry['errors'][0], dict)
    assert entry['inputs'][0]['sources'] == ['upstream']


@pytest.mark.asyncio
@pytest.mark.parametrize('kind,field,default', [
    ('start_node', 'greeting', 'Workflow started'),
    ('end_node', 'message', 'Branch completed'),
])
async def test_compact_catalogue_config_defaults_are_optional(kind, field, default):
    factory = NodeFactory()
    cfg = dict(factory._node_registry['node_catalogue_node'].default_config,
               scope='Filtered', search=kind)
    before = deepcopy(factory.metadata_for_type(kind))
    record = await node_catalogue.build(factory, dict(cfg, format='JSON'))
    fields = next(e for e in record['entries'] if e['type'] == kind)['config_fields']
    assert fields[field] == {'type': 'string', 'default': default}
    for key, value in before['default_config'].items():
        if key in fields:
            assert fields[key]['default'] == value
            assert 'required' not in fields[key]
    text = await node_catalogue.build(factory, cfg)
    assert f'{field}:string=' + node_catalogue.compact_json(default) in text
    assert 'field:type=default; required=no default' in text
    assert factory.metadata_for_type(kind) == before


def test_compact_field_keeps_required_without_a_default():
    info = {'type': 'boolean', 'required': True}
    assert node_catalogue._field(info) == info
    for default in (False, 0, '', [], {}, None):
        assert node_catalogue._field(info, default) == {'type': 'boolean', 'default': default}


@pytest.mark.asyncio
async def test_debug_optin_and_and_filters():
    f = NodeFactory();cfg = deepcopy(f._node_registry['node_catalogue_node'].default_config)
    # Full debug catalogue may exceed cap in JSON: use Text, then filtered JSON.
    text = await node_catalogue.build(f, dict(cfg, include_debug=True))
    assert 'probe_node |' in text
    record = await node_catalogue.build(f, dict(cfg, scope='Filtered',format='JSON',
        search='CATALOGUE NODE', tag_filter='META', group_filter='Any group'))
    assert [e['type'] for e in record['entries']] == ['node_catalogue_node']
    with pytest.raises(NodeError, match='Broaden'):
        await node_catalogue.build(f, dict(cfg,scope='Filtered',search='CATALOGUE NODE',tag_filter='absent'))
    with pytest.raises(NodeError):
        await node_catalogue.build(f, dict(cfg,scope='Filtered',search='.*'))


@pytest.mark.asyncio
async def test_catalogue_caps_no_partial_output_or_forwarding():
    node, ctx, memory, done, errors = runner('node_catalogue_node',
        dict(max_chars=512,vault_write=True,vault_write_key='catalogue'), 'MUST NOT BE FORWARDED')
    memory.store_persistent('catalogue','prior',type_tag='string')
    await node.execute(ctx)
    assert not done and errors[0].code == 'catalogue_too_large'
    assert memory.read_persistent('catalogue') == 'prior'
    node.config.update(max_chars=62400,format='JSON',scope='Filtered',search='notify')
    errors.clear();await node.execute(ctx)
    assert not errors and done[0]['data']['default']['schema_version']==2
    assert done[0]['data']['default'] != ctx.inputs['input']
    assert memory.read_persistent('catalogue') == done[0]['data']['default']
    resolved = NodeFactory().node_output_port_metadata(dict(type=node.node_type,config=node.config))
    assert resolved['default']['data_type']=='var'


@pytest.mark.asyncio
async def test_catalogue_exact_limit_includes_envelope_and_full_json():
    f=NodeFactory();cfg=deepcopy(f._node_registry['node_catalogue_node'].default_config)
    cfg.update(scope='Filtered',search='notify',format='JSON')
    result=await node_catalogue.build(f,cfg);size=len(node_catalogue.compact_json(result))
    assert await node_catalogue.build(f,dict(cfg,max_chars=size)) == result
    with pytest.raises(NodeError) as err:
        await node_catalogue.build(f,dict(cfg,max_chars=size-1))
    assert err.value.code=='catalogue_too_large'
    assert err.value.details['matched_count']==len(result['entries'])


@pytest.mark.asyncio
async def test_catalogue_no_library_or_network_calls(check_only):
    f=NodeFactory();cfg=deepcopy(f._node_registry['node_catalogue_node'].default_config)
    value=await node_catalogue.build(f,cfg)
    assert 'node_catalogue_node' in value


@pytest.mark.asyncio
async def test_spec_limits_precede_validation_and_braces_in_strings_are_not_depth(spec, monkeypatch):
    def forbidden(*args): raise AssertionError('oversize input reached validator')
    with monkeypatch.context() as m:
        m.setattr(authoring, 'check_workflow_spec', forbidden)
        m.setattr(meta_workflow, 'MAX_BYTES', 100)
        with pytest.raises(NodeError) as err:
            await meta_workflow.check(NodeFactory(), json.dumps({'text':'é'*100},ensure_ascii=False), 32000)
        assert err.value.code=='spec_too_large'
    spec['nodes']['start']['config']={'greeting':'['*70+']'*70}
    parsed, _ = await meta_workflow.check(NodeFactory(),json.dumps(spec),32000)
    assert parsed==spec


@pytest.mark.asyncio
async def test_catalogue_cancellation_never_publishes():
    node,ctx,memory,done,errors=runner('node_catalogue_node',dict(vault_write=True,vault_write_key='out'))
    task=asyncio.create_task(node.execute(ctx))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert not done and not errors and memory.read_persistent('out') is None


def test_problem_locations_use_existing_redactor_before_capping(monkeypatch):
    calls=[]
    def redactor(value,manager,encoded):
        calls.append((manager,encoded));return value.replace('private','[redacted]')
    monkeypatch.setattr(meta_workflow,'redact',redactor)
    message,details=meta_workflow.problem_report([dict(node='private',field='config.private',code='unknown_config_key')],manager='manager')
    assert 'private' not in message+json.dumps(details)
    assert calls and all(x==('manager',True) for x in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize('draft,path', [
    # A first, broken definition must not be hidden by a later valid one.
    ('{"format":"aotn-workflow/1","name":"D","nodes":{"start":{"type":"start_node"},'
     '"end":{"type":"does_not_exist"},"end":{"type":"end_node"}},'
     '"connections":[{"from":"start.default","to":"end.input"}]}', 'nodes.end'),
    ('{"format":"aotn-workflow/1","name":"D","nodes":{"start":{"type":"start_node"},'
     '"say":{"type":"text_output_node","config":{"template":"a","template":"b"}}},'
     '"connections":[{"from":"start.default","to":"say.input"}]}', 'nodes.say.config.template'),
])
async def test_duplicate_json_keys_are_invalid_json_with_their_path(draft, path):
    node, ctx, memory, done, errors = runner('check_workflow_spec_node',
        dict(vault_write=True, vault_write_key='checked'), draft)
    await node.execute(ctx)
    assert not done and memory.read_persistent('checked') is None
    assert errors[0].code == 'invalid_json'
    problems = errors[0].details['problems']
    assert [(p['field'], p['code']) for p in problems] == [(path, 'duplicate_key')]
    assert problems[0]['node'] == path.split('.')[1]


@pytest.mark.asyncio
async def test_brief_catalogue_fits_ask_local_model_context_with_headroom():
    factory = NodeFactory()
    cfg = dict(deepcopy(factory._node_registry['node_catalogue_node'].default_config), detail='Brief')
    text = await node_catalogue.build(factory, cfg)
    record = await node_catalogue.build(factory, dict(cfg, format='JSON'))
    compact = await node_catalogue.build(factory, dict(cfg, detail='Compact', format='JSON',
                                                       max_chars=node_catalogue.MAX_CHARS_LIMIT))
    assert {e['type'] for e in record['entries']} == {e['type'] for e in compact['entries']}
    # Purpose-first Brief no longer fits the 8,000 local-model default (plan:
    # the deprecated v1 designer used that); v2 gives Brief an explicit 50k cap.
    assert len(text) * 1.2 <= 50000
    assert record['metadata_projection'] == 'selection'
    for e in record['entries']:
        assert set(e) == {'entry_kind', 'type', 'display_name', 'description', 'inputs', 'outputs',
                          'node_metadata'}
        assert all(isinstance(name, str) for name in e['inputs'] + e['outputs'])
    assert 'check_workflow_spec_node|Check workflow spec|' in text
    assert 'input "Spec" -> default "Checked spec", report "Check report"' in text
    assert 'max_spec' not in text and node_catalogue.PORT_LEGEND in text


@pytest.mark.asyncio
@pytest.mark.parametrize('detail', ['Brief', 'Compact', 'Detailed'])
async def test_text_ports_separate_machine_ids_from_display_names(detail):
    factory = NodeFactory()
    cfg = dict(factory._node_registry['node_catalogue_node'].default_config,
               scope='Filtered', search='start_node', detail=detail)
    before = await node_catalogue.build(factory, dict(cfg, format='JSON'))
    text = await node_catalogue.build(factory, cfg)
    assert 'Connections use port ids only; quoted names are labels.' in text
    expected = 'default "Greeting"' if detail == 'Brief' else 'default ("Greeting") [string]'
    assert expected in text
    assert 'default/Greeting' not in text
    assert ('error "Error"' if detail == 'Brief' else 'error ("Error")') in text
    assert await node_catalogue.build(factory, dict(cfg, format='JSON')) == before
    row = before['entries'][0]
    if detail == 'Brief':
        # Existing JSON names-only representation remains unchanged.
        assert row['inputs'] == []
        assert row['outputs'] == ['Greeting', 'Error']
        assert set(row) == {'entry_kind','type','display_name','description','inputs','outputs',
                            'node_metadata'}
    else:
        assert row['outputs'][0]['id'] == 'default'
        assert row['outputs'][0]['name'] == 'Greeting'


@pytest.mark.asyncio
async def test_text_port_display_name_is_quoted_not_a_connection_fragment(monkeypatch):
    factory = NodeFactory()
    # A display name may itself contain slashes, quotes or a newline.
    cls = factory._node_registry['start_node']
    monkeypatch.setattr(cls, 'output_port_metadata', {
        **cls.output_port_metadata,
        'default': {'name': 'Greeting/"label"\nnext', 'data_type': 'string'}})
    cfg = dict(factory._node_registry['node_catalogue_node'].default_config,
               scope='Filtered', search='start_node')
    text = await node_catalogue.build(factory, cfg)
    assert 'default ("Greeting/\\"label\\"\\nnext") [string]' in text

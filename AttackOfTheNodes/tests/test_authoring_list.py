"""Format-level list normalization and safe, actionable shape diagnostics."""
from copy import deepcopy
import json
import subprocess
import sys

import pytest

from backend import authoring, meta_workflow
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory


@pytest.fixture
def spec():
    return {
        'format': authoring.FORMAT, 'name': 'List example',
        'nodes': {
            'start': {'type': 'start_node', 'alias': 'Hello', 'config': {'greeting': 'é\n🙂'}},
            'end': {'type': 'end_node'},
        },
        'connections': [{'from': 'start.default', 'to': 'end.input'}],
    }


def as_list(spec):
    return {**deepcopy(spec), 'nodes': [dict(id=k, **deepcopy(v)) for k, v in spec['nodes'].items()]}


@pytest.mark.asyncio
async def test_list_normalizes_losslessly_without_mutation(spec):
    listed = as_list(spec)
    before = deepcopy(listed)
    result, report = await meta_workflow.check(NodeFactory(), json.dumps(listed), 32000)
    assert result == spec
    assert listed == before
    assert report['node_count'] == 2
    assert authoring.check_workflow_spec(NodeFactory(), listed)['ok']
    assert authoring.build_workflow(NodeFactory(), listed, write=False)['ok']


@pytest.mark.parametrize('case,phrase', [
    ('missing', 'id is required'), ('invalid', 'id must be'),
    ('duplicate', 'duplicate id'), ('mixed', 'mixed keyed entries'),
    ('scalar', 'each item must be an object'),
])
@pytest.mark.asyncio
async def test_list_rejections_are_specific_and_do_not_cascade(spec, case, phrase):
    listed = as_list(spec)
    if case == 'missing':
        del listed['nodes'][0]['id']
    elif case == 'invalid':
        listed['nodes'][0]['id'] = 'CANARY invalid'
    elif case == 'duplicate':
        listed['nodes'][1]['id'] = 'start'
    elif case == 'mixed':
        listed['nodes'][1] = {'end': {'type': 'end_node'}}
    else:
        listed['nodes'][0] = 'CANARY'
    checked = authoring.build_workflow(NodeFactory(), listed, write=False)
    assert not checked['ok']
    messages = ' '.join(d['message'] for d in checked['diagnostics'])
    assert phrase in messages
    assert 'CANARY' not in messages
    assert not any((d['field'] or '').startswith('connections') for d in checked['diagnostics'])
    with pytest.raises(NodeError) as error:
        await meta_workflow.check(NodeFactory(), json.dumps(listed), 32000)
    assert phrase in str(error.value)
    assert 'CANARY' not in str(error.value)


@pytest.mark.parametrize('value', [None, 1, True, {}, [], 'Bad', 'a' * 41, 'abc\n'])
def test_invalid_list_ids(spec, value):
    listed = as_list(spec)
    listed['nodes'][0]['id'] = value
    checked = authoring.check_workflow_spec(NodeFactory(), listed)
    assert not checked['ok']
    assert any('id must be' in d['message'] for d in checked['diagnostics'])


@pytest.mark.asyncio
@pytest.mark.parametrize('field,value,expected', [
    ('nodes', 'CANARY supplied text', 'got a string'),
    ('nodes', {}, 'non-empty'), ('nodes', [], 'non-empty'),
    ('format', 'CANARY', 'format:'), ('name', False, 'name:'),
    ('connections', 'CANARY', 'connections:'), ('callable', 'CANARY', 'callable:'),
])
async def test_safe_actionable_shape_messages(spec, field, value, expected):
    spec[field] = value
    checked = authoring.check_workflow_spec(NodeFactory(), spec)
    messages = ' '.join(d['message'] for d in checked['diagnostics'])
    assert expected in messages and 'Example:' in messages
    assert 'CANARY' not in messages
    if field == 'nodes':
        assert len(checked['diagnostics']) == 1
    with pytest.raises(NodeError) as error:
        await meta_workflow.check(NodeFactory(), json.dumps(spec), 32000)
    assert expected in str(error.value)
    assert 'CANARY' not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize('node', [
    'CANARY', {'type': 'CANARY', 'config': 'CANARY'},
    {'type': 'CANARY', 'alias': ['CANARY']}, {'type': 'CANARY', 'CANARY': 'CANARY'},
    {'type': ['CANARY']},
])
async def test_node_shape_messages_never_quote_values(spec, node):
    spec['nodes']['start'] = node
    checked = authoring.check_workflow_spec(NodeFactory(), spec)
    shapes = [d for d in checked['diagnostics'] if d['code'] == 'spec_invalid']
    assert shapes
    assert all('Example:' in d['message'] and 'CANARY' not in d['message'] for d in shapes)
    message, details = meta_workflow.problem_report(shapes)
    assert 'Example:' in message and 'CANARY' not in message


@pytest.mark.parametrize('check', [True, False])
def test_cli_list_build_and_check(spec, tmp_path, check):
    source = tmp_path / 'spec.json'
    source.write_text(json.dumps(as_list(spec)))
    data = tmp_path / 'data'
    command = [sys.executable, 'main.py', 'build', str(source), '--data-dir', str(data), '--json']
    if check:
        command.append('--check')
    run = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stdout + run.stderr
    report = json.loads(run.stdout)
    assert set(report['nodes']) == set(spec['nodes'])
    files = list((data / 'workflows').glob('*.json'))
    assert len(files) == (0 if check else 1)
    if files:
        saved = json.loads(files[0].read_text())
        assert isinstance(saved['nodes'], dict)


@pytest.mark.asyncio
async def test_list_node_cap_still_applies(spec):
    listed = as_list(spec)
    listed['nodes'] = [dict(id=f'n{i}', type='end_node') for i in range(129)]
    with pytest.raises(NodeError) as error:
        await meta_workflow.check(NodeFactory(), json.dumps(listed), 32000)
    assert error.value.code == 'spec_too_large'


@pytest.mark.parametrize('form', ['keyed', 'list'])
def test_normalization_does_not_discard_unknown_node_fields(spec, form):
    spec['nodes']['start']['unexpected'] = {'private': 'CANARY'}
    supplied = as_list(spec) if form == 'list' else spec
    checked = authoring.check_workflow_spec(NodeFactory(), supplied)
    assert not checked['ok']
    assert any(d.get('hint') == 'node_fields' for d in checked['diagnostics'])
    assert 'CANARY' not in ' '.join(d['message'] for d in checked['diagnostics'])


@pytest.mark.parametrize('connections,hint', [
    (['CANARY'], 'connection'),
    ([{'from': ['CANARY'], 'to': 'end.input'}], 'endpoint'),
    ([{'from': 'CANARY.default', 'to': 'end.input'}], 'endpoint_handle'),
])
def test_connection_shape_guidance_is_safe(spec, connections, hint):
    spec['connections'] = connections
    checked = authoring.check_workflow_spec(NodeFactory(), spec)
    diagnostics = [d for d in checked['diagnostics'] if d.get('hint') == hint]
    assert diagnostics
    assert all('Example:' in d['message'] and 'CANARY' not in d['message'] for d in diagnostics)
    rendered, _ = meta_workflow.problem_report(diagnostics)
    assert 'CANARY' not in rendered


def test_list_items_may_name_handle_instead_of_id(spec):
    # Drafts write "handle" as often as "id"; both are the keyed handle.
    listed = {**deepcopy(spec), 'nodes': [dict(handle=k, **deepcopy(v)) for k, v in spec['nodes'].items()]}
    normalized, problems = authoring.normalize_spec(listed)
    assert not problems and normalized['nodes'] == spec['nodes']
    same = as_list(spec)
    same['nodes'][0]['handle'] = same['nodes'][0]['id']
    assert authoring.normalize_spec(same)[0]['nodes'] == spec['nodes']


def test_conflicting_id_and_handle_is_rejected_without_type_noise(spec):
    listed = as_list(spec)
    listed['nodes'][0]['handle'] = 'other'
    _, problems = authoring.normalize_spec(listed)
    assert [p['hint'] for p in problems] == ['id_conflict']
    duplicate = as_list(spec)
    duplicate['nodes'].append(deepcopy(duplicate['nodes'][0]))
    _, problems = authoring.normalize_spec(duplicate)
    assert [p['hint'] for p in problems] == ['id_duplicate'] and 'got' not in problems[0]['message'].split('Example:')[0]

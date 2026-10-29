"""Mocked evidence for the batch-1 node metadata claims (record v1).

Each test exercises the node code a record sentence relies on, including
nondefault modes. No network, model, login, Secrets or owner files are used.
The review manifest (backend/node_metadata_review.json) cites these tests.
"""
import pytest

from backend.node_factory import NodeFactory
from backend.window_manager import FakeWindowManager
from backend.nodes.io.window_support import WINDOW_MANAGER_RESOURCE
from backend.run_session import RunSession
from tests.test_meta_nodes import runner


@pytest.fixture
def engine(tmp_path, monkeypatch):
    from backend import configuration_manager, error_handler, output_manager, run_history
    from backend.run_service import RunService
    for module, field in ((error_handler, 'RUN_ERRORS_DIR'), (output_manager, 'RUN_OUTPUTS_DIR'),
                          (run_history, 'RUN_HISTORY_DIR'), (configuration_manager, 'SETTINGS_DIR')):
        monkeypatch.setattr(module, field, tmp_path / field)
    service = RunService.create()
    yield service
    service.close()


def output_text(result):
    return [str(getattr(line, 'text', line)) for line in result.outputs]


async def run_start_then_show(service, start_config):
    wm = service.workflow_map
    wm.create_new('Start then show')
    start, show, end = wm.add_node('start_node'), wm.add_node('text_output_node'), wm.add_node('end_node')
    wm.update_node_config(start, {**wm.get_node_data(start)['config'], **start_config})
    wm.update_node_config(show, {**wm.get_node_data(show)['config'], 'label': '', 'template': '<{input}>'})
    wm.update_node_config(end, {**wm.get_node_data(end)['config'], 'record_line': False})
    wm.connect(start, 'default', show, 'input')
    wm.connect(show, 'default', end, 'input')
    await service.start()
    return await service.wait()


@pytest.mark.asyncio
@pytest.mark.parametrize('start_config,shown', [
    ({'greeting': ''}, '<>'),
    ({'greeting': 'Hello'}, '<Hello>'),
    ({'greeting': 'Hello', 'transient_output': False}, '<>'),
])
async def test_start_greeting_runs_next_step_even_when_empty_and_is_never_displayed(
        engine, start_config, shown):
    result = await run_start_then_show(engine, start_config)
    assert result.exit_code == 0
    # The next step ran; only Text Output put anything in the run output.
    assert output_text(result) == [shown]


@pytest.mark.asyncio
@pytest.mark.parametrize('record_line,value,logged', [
    (True, 'x', ['[END] Branch completed (received: x)']),
    (True, '', ['[END] Branch completed']),
    (False, 'x', []),
])
async def test_end_line_framing_and_silence(record_line, value, logged):
    node, ctx, memory, done, errors = runner('end_node', dict(record_line=record_line), value)
    await node.execute(ctx)
    assert not errors and done[0]['terminate_branch'] and done[0]['data'] == {}
    assert [str(getattr(e, 'text', e)) for e in memory.read_persistent('output_log', default=[])] == logged


@pytest.mark.asyncio
@pytest.mark.parametrize('value,expected', [({'k': 1}, {'k': 1}), (None, '')])
async def test_merge_beacon_forwards_unchanged(value, expected):
    node, ctx, _, done, errors = runner('branch_end_node', {}, value)
    if value is None:
        ctx.inputs = {}
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {'default': expected}
    assert 'terminate_branch' not in done[0]


@pytest.mark.asyncio
async def test_parallel_branch_default_starts_every_path_and_ignores_legacy_condition():
    node, ctx, memory, done, errors = runner('branch_node', dict(
        branch_count=3, condition='path_a_only', branch_payload_sources={'path_b': 'vault:seed'}), 'v')
    memory.store_persistent('seed', 'from vault')
    await node.execute(ctx)
    branches = done[0]['branches']
    assert [b['output_port'] for b in branches] == ['path_a', 'path_b', 'path_c']
    assert [b['initial_data']['input'] for b in branches] == ['v', 'from vault', 'v']
    # Legacy config without branch_count still honours its condition.
    legacy = NodeFactory().create_node('branch_node', 'legacy')
    legacy.config = {'condition': 'path_a_only'}
    ctx.signal_done = done.append
    await legacy.execute(ctx)
    assert [b['output_port'] for b in done[-1]['branches']] == ['path_a']


@pytest.mark.asyncio
async def test_user_text_input_waits_for_a_person_and_emits_the_answer():
    node, ctx, _, done, errors = runner('user_text_input_node', dict(prompt='Note?'), 'ignored')
    asked = []

    async def answer(prompt):
        asked.append(prompt)
        return 'my note'
    ctx.signal_waiting_for_input = answer
    await node.execute(ctx)
    assert asked == ['Note?'] and done[0]['data'] == {'default': 'my note'}


@pytest.mark.asyncio
@pytest.mark.parametrize('label,expected', [('', 'hi'), ('  ', 'hi'), ('Output', '[Output] hi')])
async def test_text_output_label_framing(label, expected):
    node, ctx, memory, done, errors = runner('text_output_node', dict(label=label), 'hi')
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {'default': expected}
    assert [str(getattr(e, 'text', e)) for e in memory.read_persistent('output_log')] == [expected]


@pytest.mark.asyncio
async def test_text_output_default_label_template_errors_and_legacy_prompt():
    assert NodeFactory().create_config_template('text_output_node')['label'] == 'Output'
    node, ctx, _, done, errors = runner('text_output_node', dict(template='{other}'), 'hi')
    await node.execute(ctx)
    assert errors and not done
    node, ctx, _, done, errors = runner('text_output_node', dict(input_source='Vault', input_vault_key='gone'), 'hi')
    await node.execute(ctx)
    assert errors and not done
    node, ctx, _, done, errors = runner('text_output_node', dict(label='', request_user_input=True), 'hi')

    async def answer(prompt):
        return 'typed'
    ctx.signal_waiting_for_input = answer
    await node.execute(ctx)
    assert done[0]['data'] == {'default': 'typed'}


@pytest.mark.asyncio
@pytest.mark.parametrize('operation,value,expected', [
    ('strip', '  a  b \n', 'a  b'),
    ('uppercase', {'type': 'file', 'path': '/x'}, "{'TYPE': 'FILE', 'PATH': '/X'}"),
    ('lowercase', None, ''),
    ('title', 'one two', 'One Two'),
    ('reverse', 'abc', 'cba'),
])
async def test_text_transform_operations(operation, value, expected):
    node, ctx, _, done, errors = runner('text_transform_node', dict(operation=operation), value)
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {'default': expected}
    assert NodeFactory().create_config_template('text_transform_node')['operation'] == 'uppercase'


@pytest.mark.asyncio
async def test_file_reader_needs_a_typed_reference_from_upstream(tmp_path):
    path = tmp_path / 'notes.txt'
    path.write_text('héllo\n', encoding='utf-8')
    node, ctx, _, done, errors = runner('file_reader_node', dict(input_source='Upstream payload'), str(path))
    await node.execute(ctx)
    assert errors and not done
    ref = {'type': 'file', 'ref_key': f'file:{path}', 'path': str(path)}
    node, ctx, _, done, errors = runner('file_reader_node', dict(input_source='Upstream payload'), ref)
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {'default': 'héllo\n'}
    node, ctx, _, done, errors = runner('file_reader_node', dict(file_path=str(tmp_path / 'missing.txt')), None)
    await node.execute(ctx)
    assert errors and not done


@pytest.mark.asyncio
async def test_file_write_overwrites_by_default_and_open_after_write_uses_window_manager(tmp_path):
    path = tmp_path / 'out.txt'
    path.write_text('old')
    assert NodeFactory().create_config_template('file_output_node')['write_mode'] == 'Overwrite'
    node, ctx, _, done, errors = runner('file_output_node', dict(
        content_source='Configured', content='new', file_path=str(path)))
    await node.execute(ctx)
    assert not errors and path.read_text() == 'new'
    assert done[0]['data']['default']['path'] == str(path)

    fake = FakeWindowManager()
    session = RunSession('run')
    session.register_resource(WINDOW_MANAGER_RESOURCE, fake)
    node, ctx, _, done, errors = runner('file_output_node', dict(
        content_source='Configured', content='again', file_path=str(path), open_after_write=True))
    ctx.run_session = session
    try:
        await node.execute(ctx)
    finally:
        session.close_all()
    assert not errors and fake.opened == [(str(path), 'OS default')]


@pytest.mark.asyncio
@pytest.mark.parametrize('config,left,port', [
    ({}, 'anything', 'true'),  # default contains with empty right_value
    ({'right_value': 'es'}, 'yes', 'true'),
    ({'condition_type': 'regex', 'right_value': '^y'}, 'yes', 'true'),
    ({'condition_type': 'not_equals', 'right_value': 'yes'}, 'Yes', 'true'),
    ({'condition_type': 'equals', 'right_value': 'yes'}, 'yes ', 'false'),
])
async def test_conditional_modes_emit_one_port_with_the_left_value(config, left, port):
    node, ctx, _, done, errors = runner('conditional_node', config, left)
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {port: left} and done[0]['output_port'] == port


@pytest.mark.asyncio
async def test_concat_unknown_names_empty_literal_braces_and_vault_values():
    node, ctx, memory, done, errors = runner('concat_node', dict(
        template='{greeting} {input} {missing}| {{x}}'), 'in')
    memory.store_persistent('greeting', 'Hi')
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {'default': 'Hi in | {x}'}
    node, ctx, _, done, errors = runner('concat_node', dict(template='Fixed'), 'ignored')
    await node.execute(ctx)
    assert done[0]['data'] == {'default': 'Fixed'}


@pytest.mark.asyncio
@pytest.mark.parametrize('path,value,expected', [
    ('', '{"a": 1}', {'a': 1}),
    ('items.1', '{"items": [5, 6]}', 6),
    ('items.-1', '{"items": [5, 6]}', 6),
    ('path', {'type': 'file', 'path': '/saved/x.txt'}, '/saved/x.txt'),
    ('missing', '{"a": 1}', 'fallback'),
])
async def test_json_path_lookup(path, value, expected):
    node, ctx, _, done, errors = runner('json_path_node', dict(path=path, default_value='fallback'), value)
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {'default': expected}
    node, ctx, _, done, errors = runner('json_path_node', dict(path='a'), 'not json')
    await node.execute(ctx)
    assert errors[0].code == 'invalid_json'


@pytest.mark.asyncio
@pytest.mark.parametrize('kind,config,value', [
    ('concat_node', dict(template='{input[missing]}'), {'other': 1}),
    ('concat_node', dict(template='{input.attr}'), 'text'),
    ('text_output_node', dict(template='{input[missing]}'), {'other': 1}),
    ('conditional_node', dict(condition_type='regex', right_value='('), 'x'),
    ('json_path_node', dict(path='a'), None),
])
async def test_documented_failures_fail_the_node(kind, config, value):
    node, ctx, _, done, errors = runner(kind, config, value)
    if value is None:
        ctx.inputs = {}
    try:
        await node.execute(ctx)
    except Exception:
        failed = True  # uncaught here; the supervisor turns it into a node failure
    else:
        failed = bool(errors) and not done
    assert failed


@pytest.mark.asyncio
async def test_conditional_missing_vault_variable_compares_as_empty_and_transform_fallback():
    node, ctx, _, done, errors = runner('conditional_node', dict(
        left_value_source='variable', variable_name='absent', condition_type='equals', right_value=''), 'x')
    await node.execute(ctx)
    assert done[0]['data'] == {'true': ''}
    node, ctx, _, done, errors = runner('text_transform_node', dict(operation='unknown'), 'abc')
    await node.execute(ctx)
    assert done[0]['data'] == {'default': 'ABC'}


@pytest.mark.asyncio
async def test_file_reader_text_mode_normalizes_line_endings(tmp_path):
    path = tmp_path / 'crlf.txt'
    path.write_bytes(b'a\r\nb')
    node, ctx, _, done, errors = runner('file_reader_node', dict(file_path=str(path)), None)
    await node.execute(ctx)
    assert done[0]['data'] == {'default': 'a\nb'}

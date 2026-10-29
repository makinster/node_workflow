"""Local engine runs only; no provider adapters are called."""
import json

import pytest

from tests.test_meta_nodes import runner as node_runner
from tools.draft_trials import runner
from tools.draft_trials.cases import case_record, good_draft


@pytest.mark.asyncio
@pytest.mark.parametrize('source', ['Upstream payload', 'Vault'])
@pytest.mark.parametrize('label,prefix', [('', ''), (' \t\n', ''), ('Shown', '[Shown] '), (' Shown ', '[ Shown ] ')])
async def test_label_policy_logs_emits_and_writes_vault(label, prefix, source):
    node, ctx, memory, done, errors = node_runner('text_output_node', dict(
        label=label, input_source=source, input_vault_key='source', template='{input}', membank_outputs=[{'id': 'saved', 'output': 'saved'}]), '[END] user text')
    memory.store_persistent('source', '[END] user text', type_tag='string')
    if source == 'Vault':
        ctx.inputs = {'input': 'ignored upstream'}
    await node.execute(ctx)
    expected = prefix + '[END] user text'
    assert not errors and done[0]['data']['default'] == expected
    assert str(memory.read_persistent('output_log')[0]) == expected
    assert memory.read_persistent('saved') == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('number', [5, 10])
@pytest.mark.parametrize('label', ['', ' \t', 'Saved', 'END'])
async def test_target_behavior_accepts_framed_actual_path(number, label, tmp_path):
    case = case_record(number, tmp_path / 'fixtures')
    spec = good_draft(number, case['root'])
    for node in spec['nodes'].values():
        if node['type'] == 'text_output_node':
            node['config'].update(label=label, template='Saved path: {input[path]}')
    for node in spec['nodes'].values():
        if node['type'] == 'end_node':
            node.setdefault('config', {})['record_line'] = True
    report = await runner.target_fixtures(spec, case, tmp_path / 'runs')
    assert report['result'] == 'pass', report
    assert all(r['outputs'][0].startswith('Saved path: ') for r in report['fixtures'])
    assert all(r['completion_noise'] for r in report['fixtures'])
    spec['name'] += ' strict'
    case['request'] = 'Show only the saved path.'
    case['clarification'] = ''
    assert (await runner.target_fixtures(spec, case, tmp_path / 'exact'))['result'] == 'fail'


@pytest.mark.asyncio
async def test_bare_bracketed_data_is_not_a_label_or_end_line(tmp_path, monkeypatch):
    case = case_record(1, tmp_path / 'fixtures')
    spec = good_draft(1, case['root'])
    spec['nodes']['show']['config'].update(label='', template='[END] Ready')
    monkeypatch.setattr(runner, 'fixture_variants', lambda _: [dict(
        name='brackets', files={}, answers=[], outputs=['[END] Ready'], writes={}, error=False)])
    for node in spec['nodes'].values():
        if node['type'] == 'end_node':
            node.setdefault('config', {})['record_line'] = True
    report = await runner.target_fixtures(spec, case, tmp_path / 'runs')
    assert report['result'] == 'pass', report
    assert report['fixtures'][0]['outputs'] == ['[END] Ready']
    assert len(report['fixtures'][0]['completion_noise']) == 1


def test_both_requirements_prompts_preserve_requested_strictness():
    spec = json.loads(runner.SPEC.read_text())
    for handle in ('analysis_question', 'resolve_question'):
        prompt = spec['nodes'][handle]['config']['template']
        assert 'Do not add exactly, nothing else, or only' in prompt
        assert 'normal run framing' in prompt


@pytest.mark.asyncio
async def test_behavior_saved_content_is_not_display_framing(tmp_path):
    case = case_record(5, tmp_path / 'fixtures')
    spec = good_draft(5, case['root'])
    spec['nodes']['write']['config'].update(content_source='Configured', content='Content: Line one\nLine two\n')
    spec['nodes']['show']['config'].update(template='Saved path: {input[path]}')
    report = await runner.target_fixtures(spec, case, tmp_path / 'runs')
    assert report['result'] == 'fail'
    assert all(r['sentinels_preserved'] for r in report['fixtures'])


@pytest.mark.asyncio
async def test_run_artifact_keeps_output_emitter_handles(tmp_path):
    case = case_record(1, tmp_path / 'fixtures')
    spec = good_draft(1, case['root'])
    spec['nodes']['show']['config']['label'] = ''
    spec['nodes']['end']['config']['record_line'] = True
    artifact = tmp_path / 'run.json'
    await runner.run_workflow(spec, [], artifact)
    stored = json.loads(artifact.read_text())
    assert [r['handle'] for r in stored['output_records']] == ['show', 'end']
    assert stored['output_records'][0]['text'] == 'Ready'

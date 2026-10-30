"""Palette contracts and diagnostic trials; provider transport is always mocked."""
import json
import sys

import pytest

from backend import authoring, node_catalogue
from backend.node_factory import NodeFactory
from tests.test_meta_nodes import runner as node_runner
from tools.draft_trials import __main__ as cli, runner
from tools.draft_trials.cases import PALETTE


@pytest.mark.asyncio
async def test_palette_contracts_describe_payloads_and_configured_inputs():
    factory = NodeFactory()
    cfg = dict(factory.metadata_for_type('node_catalogue_node')['default_config'], format='JSON',
               max_chars=node_catalogue.MAX_CHARS_LIMIT)
    record = await node_catalogue.build(factory, cfg)
    entries = {e['type']: e for e in record['entries']}
    for kind in PALETTE:
        # Catalogue v2 carries the contract once, inside the full record.
        assert 'execution_contract' not in entries[kind]
        contract = entries[kind]['node_metadata']['execution_contract']
        assert contract['output_payload']
        assert authoring.describe_node_type(factory, kind)['execution_contract'] == contract
    text, inventory = await runner.contract_inventory()
    assert set(t for ts in inventory.values() for t in ts) == PALETTE
    assert len(text) <= 50000
    for kind in PALETTE:
        assert entries[kind]['node_metadata']['execution_contract']['output_payload'] in text
    assert 'Output payload:' in text
    for word in ('ref_key', 'path', 'actual saved', 'Configured', 'trigger only',
                 'Create unique', ' (1)', 'case-sensitive', 'whitespace'):
        assert word in text
    reader = entries['file_reader_node']
    assert 'trigger only' in reader['configured_inputs']['input']
    assert 'file_path' in reader['configured_inputs']['input']
    assert 'configured_inputs' not in entries['text_output_node']


@pytest.mark.asyncio
async def test_verified_file_write_and_configured_reader_behavior(tmp_path):
    path = tmp_path / 'copy.txt'
    path.write_text('old')
    (tmp_path / 'copy (1).txt').write_text('also old')
    node, ctx, _, done, errors = node_runner('file_output_node', dict(
        content_source='Configured', content='new', file_path=str(path), write_mode='Create unique'))
    ctx.inputs = {'content': {'ignored': True}, 'file_path': 'also ignored'}
    await node.execute(ctx)
    assert not errors
    ref = done[0]['data']['default']
    assert ref == {'type': 'file', 'ref_key': f'file:{tmp_path}/copy (2).txt',
                   'path': str(tmp_path / 'copy (2).txt')}
    assert path.read_text() == 'old'
    assert (tmp_path / 'copy (1).txt').read_text() == 'also old'
    reader, ctx, _, done, errors = node_runner('file_reader_node',
        dict(input_source='Configured', file_path=ref['path']), 'start string, not a file reference')
    await reader.execute(ctx)
    assert not errors and done[0]['data']['default'] == 'new'


@pytest.mark.asyncio
@pytest.mark.parametrize('left,port', [('yes', 'true'), ('Yes', 'false'), (' yes', 'false'), ('yes\n', 'false')])
async def test_verified_equals_is_exact(left, port):
    node, ctx, _, done, errors = node_runner('conditional_node',
        dict(condition_type='equals', right_value='yes'), left)
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {port: left}


@pytest.mark.parametrize('continue_cases,only,expected_cases', [
    (False, False, 0), (True, False, 10), (True, True, 0),
])
def test_failed_mock_calibration_cases_flag(tmp_path, monkeypatch, capsys,
                                           continue_cases, only, expected_cases):
    root = tmp_path / 'trial'
    argv = ['draft_trials', '--trial-root', str(root)]
    if continue_cases:
        argv.append('--cases-even-if-calibration-fails')
    if only:
        argv.append('--calibrate-only')
    monkeypatch.setattr(sys, 'argv', argv)
    original = runner.calibrate

    async def failed_calibration(*args, **kwargs):
        return await original(*args, judge_replies=[runner.meaning('fail')] * 60, **kwargs)

    monkeypatch.setattr(runner, 'calibrate', failed_calibration)
    assert cli.main() == 1
    stdout = json.loads(capsys.readouterr().out)
    report = json.loads((root / 'runs/000001/report.json').read_text())
    assert stdout['calibration'] == report['calibration'] == 'fail'
    assert stdout['result'] == report['result'] == 'fail'
    assert stdout['cases'] == report['case_count'] == expected_cases
    assert report['cases_even_if_calibration_fails'] is continue_cases
    assert all(c['result'] == 'pass' for c in report['cases'])
    assert len(json.loads((root / 'runs/000001/calibration-report.json').read_text())['fixtures']) == 60


@pytest.mark.asyncio
@pytest.mark.parametrize('limit', ['cost', 'time', 'unknown'])
async def test_continue_cases_preserves_budget_guards(tmp_path, monkeypatch, limit):
    async def failed_calibration(*args, **kwargs):
        if limit == 'cost':
            runner._budget.cost = runner._budget.limit
        elif limit == 'time':
            runner._budget.started -= runner._budget.time_limit
        else:
            runner._budget.unknown = True
        return {'result': 'fail'}

    async def forbidden_case(*args, **kwargs):
        raise AssertionError('exhausted guard must stop cases')

    monkeypatch.setattr(runner, 'calibrate', failed_calibration)
    monkeypatch.setattr(runner, 'run_case', forbidden_case)
    report = await runner.batch(tmp_path, real_calls=True, budget_usd=1,
        shared_library=tmp_path / 'shared', cases_even_if_calibration_fails=True)
    assert report['calibration'] == report['result'] == 'fail'
    assert report['case_count'] == 0 and 'budget' in report['failure']


def test_judge_prompt_restricts_problems_to_blockers():
    prompt = json.loads(runner.SPEC.read_text())['nodes']['judge_question']['config']['template']
    assert 'problems' in prompt and 'every other observation goes in remarks' in prompt
    reply = runner.meaning()
    reply['problems'] = ['harmless remark']
    assert not runner.valid_judge(reply, runner.requirements({'request': 'Show Ready'}))

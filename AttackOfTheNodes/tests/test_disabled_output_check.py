"""Mock/local structural diagnostics and the existing one-redraft path."""
import json

import pytest

from backend import authoring, meta_workflow
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from tools.draft_trials.cases import calibration_pairs

from tests.test_concat_vault import draft


@pytest.mark.asyncio
async def test_disabled_transient_calibration_fails_structurally_only_when_opted_in():
    pair = next(p for p in calibration_pairs() if p['id'] == 'disabled_transient')
    factory = NodeFactory()
    _, report = await meta_workflow.check(factory, json.dumps(pair['bad']), 32000)
    assert any(p['code'] == 'disabled_output_connection' for p in report['problems'])
    with pytest.raises(NodeError) as caught:
        await meta_workflow.check(factory, json.dumps(pair['bad']), 32000, fail_on_disabled_output=True)
    assert caught.value.code == 'spec_invalid'
    assert any(p['code'] == 'disabled_output_connection' for p in caught.value.details['problems'])
    await meta_workflow.check(factory, json.dumps(pair['good']), 32000, fail_on_disabled_output=True)


@pytest.mark.parametrize('kind,config,expected', [
    ('concat_node', {'transient_output': False}, True),
    ('concat_node', {'transient_output': False, 'dead_drop_passthrough': True}, False),
    ('concat_node', {'transient_output': True}, False),
    ('text_output_node', {'transient_output': False}, False),  # legacy switch is ignored
    ('start_node', {'rows': [{'name': 'value', 'type': 'string', 'to': 'Downstream', 'value': 'x'}],
                    'transient_output': False}, False),  # rows override the legacy switch
])
def test_disabled_output_warning_respects_runtime_routing(kind, config, expected):
    spec = draft(config={'template': 'Fixed'})
    handle = 'start' if kind == 'start_node' else 'work'
    spec['nodes'][handle] = {'type': kind, 'config': config}
    result = authoring.check_workflow_spec(NodeFactory(), spec)
    assert any(d['code'] == 'disabled_output_connection' and d['node'] == handle
               for d in result['diagnostics']) is expected


@pytest.mark.asyncio
async def test_disabled_output_uses_one_redraft_and_records_exact_warning(tmp_path):
    from tools.draft_trials import runner as trials
    from tools.draft_trials.cases import case_record, good_draft
    case = case_record(5, tmp_path / 'cases/5/fixtures')
    good = good_draft(5, case['root'])
    bad = json.loads(json.dumps(good))
    bad['nodes']['read']['config']['transient_output'] = False
    report = await trials.run_case(5, tmp_path, tmp_path / 'library', replies=[
        trials.requirements(case), bad, good, trials.meaning()])
    assert report['result'] == 'pass', report
    assert report['draft_retry']['attempted'] == 1
    assert report['calls']['attempted'] == 4
    evidence = json.loads((tmp_path / 'cases/5/evidence.json').read_text())
    problem = next(p for p in evidence['first_check_error']['details']['problems']
                   if p['code'] == 'disabled_output_connection')
    prompt = json.loads((tmp_path / 'cases/5/calls.json').read_text())[2]['messages'][0]['content']
    assert problem['message'] in prompt


@pytest.mark.asyncio
async def test_second_disabled_output_stops_before_judge_or_save(tmp_path):
    from tools.draft_trials import runner as trials
    from tools.draft_trials.cases import case_record, good_draft
    case = case_record(5, tmp_path / 'cases/5/fixtures')
    bad = good_draft(5, case['root'])
    bad['nodes']['read']['config']['transient_output'] = False
    report = await trials.run_case(5, tmp_path, tmp_path / 'library', replies=[
        trials.requirements(case), bad, bad])
    assert report['result'] == 'fail' and report['calls']['attempted'] == 3
    assert not report['draft_retry']['check_passed']
    assert report['meaning_review'] == 'not_run'
    assert not list((tmp_path / 'cases/5/drafts').glob('*'))


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['true', None])
async def test_disabled_output_option_requires_boolean(value):
    with pytest.raises(NodeError) as caught:
        await meta_workflow.check(NodeFactory(), json.dumps(draft()), 8000, fail_on_disabled_output=value)
    assert caught.value.code == 'invalid_config'

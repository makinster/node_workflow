"""Scoring, prompt evidence and known-cost failures; no provider network access."""
from contextlib import ExitStack
import json

import pytest

from backend import node_catalogue, reply_shape
from backend.node_factory import NodeFactory
from tests.test_meta_nodes import runner as node_runner
from tools.draft_trials import runner
from tools.draft_trials.cases import case_record, good_draft


@pytest.mark.asyncio
@pytest.mark.parametrize('order', [1, '1'])
@pytest.mark.parametrize('number', [2, 10])
async def test_integer_and_string_order_pass_workflow_and_case_scoring(tmp_path, order, number):
    root = tmp_path / 'trial'
    case = case_record(number, root / f'cases/{number}/fixtures')
    requirements = runner.requirements(case)
    requirements['requirements'][0]['order'] = order
    config = json.loads(runner.SPEC.read_text())['nodes']['analysis_shape']['config']
    assert await reply_shape.check(json.dumps(requirements), config['expected_fields'],
        config['max_reply'], config['allow_other_fields'], config.get('reply_schema')) == requirements
    assert runner.valid_analysis(requirements)
    replies = [requirements, good_draft(number, case['root']), runner.meaning()]
    if number == 10:
        first = runner.requirements(case, 'clarify')
        first['requirements'][0]['order'] = order
        replies.insert(0, first)
    result = await runner.run_case(number, root, root / 'library', replies=replies)
    assert result['clarification'] == result['meaning_review'] == result['result'] == 'pass'


@pytest.mark.asyncio
async def test_unexpected_prompt_keeps_evidence_and_runs_next_case_with_known_cost(tmp_path, monkeypatch):
    original = runner.run_case

    async def unexpected_ninth(number, trial_root, library, replies=None, real_calls=False, scenario='ready', **kwargs):
        if number == 9:
            case = case_record(number, trial_root / 'cases/9/fixtures')
            replies = [runner.requirements(case, 'clarify')]
        return await original(number, trial_root, library, replies, real_calls, scenario, **kwargs)

    replies = [runner.meaning(v) for _ in range(25) for v in ('pass', 'fail')]
    case9 = case_record(9, tmp_path / 'cases/9/fixtures')
    case10 = case_record(10, tmp_path / 'cases/10/fixtures')
    replies += [runner.requirements(case9, 'clarify'), runner.requirements(case10, 'clarify'),
                runner.requirements(case10), good_draft(10, case10['root']), runner.meaning()]
    monkeypatch.setattr(runner, 'run_case', unexpected_ninth)
    mock = runner.MockSDK(replies)
    with ExitStack() as stack:
        mock.install(stack)
        report = await runner.batch(tmp_path, case_ids=[9, 10], real_calls=True,
            budget_usd=1, shared_library=tmp_path / 'shared')
    assert report['result'] == 'fail' and report['case_count'] == 2
    ninth, tenth = report['cases']
    assert ninth['result'] == 'fail' and 'unexpected prompt' in ninth['failure']
    assert tenth['result'] == 'pass'
    assert ninth['usage_summary']['not_reported'] == 0
    trace = ninth['input_trace']
    assert trace[0]['answer'] == case9['request']
    assert trace[-1]['answer'] is None and trace[-1]['failure'] == 'unexpected prompt'
    assert trace[-1]['prompt'] == 'Answer the questions above'
    evidence = json.loads((tmp_path / 'cases/9/evidence.json').read_text())
    assert json.loads(evidence['first_analysis'])['status'] == 'clarify'
    run = json.loads((tmp_path / 'cases/9/designer-run.json').read_text())
    assert run['input_trace'] == trace and run['input_failure'] == 'unexpected prompt'
    assert (tmp_path / 'cases/9/calls.json').exists()
    assert not mock.replies


@pytest.mark.parametrize('reported,attempts,expected_unknown', [(1, 1, False), (0, 1, True)])
def test_known_error_cost_is_distinct_from_missing_call_usage(reported, attempts, expected_unknown):
    budget = runner.TrialBudget(1)
    receipts = [{'usage': {'estimated_cost_usd': .01}}] * reported
    from backend.agent_usage import usage_summary
    budget.record({'agent_usage': receipts, 'agent_usage_summary': usage_summary(receipts),
                   'errors': [{'message': 'unexpected prompt'}]}, attempted_calls=attempts)
    assert budget.unknown is expected_unknown
    if expected_unknown:
        with pytest.raises(ValueError, match='cost unknown'):
            budget.before()
    else:
        budget.before()


@pytest.mark.asyncio
async def test_text_output_logs_and_emits_labelled_text_and_contract_explains_framing():
    node, ctx, memory, done, errors = node_runner('text_output_node',
        dict(label='Shown', template='{input}'), 'Ready')
    await node.execute(ctx)
    assert not errors
    assert done[0]['data']['default'] == str(memory.read_persistent('output_log')[0]) == '[Shown] Ready'
    factory = NodeFactory()
    config = dict(factory.metadata_for_type('node_catalogue_node')['default_config'],
        scope='Filtered', search='text_output_node')
    text = await node_catalogue.build(factory, config)
    assert 'display framing' in text and 'downstream' in text


@pytest.mark.asyncio
@pytest.mark.parametrize('node', ['analysis_shape', 'resolved_shape', 'judge_shape'])
@pytest.mark.parametrize('mutation', ['valid', 'missing', 'extra', 'wrong_type'])
async def test_workflow_and_harness_share_top_level_shape_gate(node, mutation):
    from backend.node_errors import NodeError
    record = runner.meaning() if node == 'judge_shape' else runner.requirements({'request': 'Show Ready'})
    field = 'summary' if node == 'judge_shape' else 'reason'
    if mutation == 'missing':
        del record[field]
    elif mutation == 'extra':
        record['extra'] = True
    elif mutation == 'wrong_type':
        record[field] = 1
    config = json.loads(runner.SPEC.read_text())['nodes'][node]['config']
    try:
        await reply_shape.check(json.dumps(record), config['expected_fields'],
            config['max_reply'], config['allow_other_fields'], config.get('reply_schema'))
        accepted = True
    except NodeError:
        accepted = False
    assert runner.valid_v2_shape(record, node) is accepted


@pytest.mark.asyncio
async def test_unreported_attempt_still_stops_before_next_case(tmp_path):
    replies = [runner.meaning(v) for _ in range(25) for v in ('pass', 'fail')]
    mock = runner.MockSDK(replies + [{'_error': 'no usage returned'}])
    with ExitStack() as stack:
        mock.install(stack)
        report = await runner.batch(tmp_path, case_ids=[9, 10], real_calls=True,
            budget_usd=1, shared_library=tmp_path / 'shared')
    assert report['result'] == 'fail' and report['case_count'] == 1
    assert 'cost unknown' in report['failure']
    assert len(mock.calls) == 51 and not (tmp_path / 'cases/10').exists()
    assert (tmp_path / 'cases/9/evidence.json').exists()

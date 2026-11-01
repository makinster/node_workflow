"""One structural repair with SDK transport mocked and real engine gates."""
from contextlib import ExitStack
from pathlib import Path
import json

import pytest

from tools.draft_trials import runner
from tools.draft_trials.cases import case_record, good_draft


def drafts(tmp_path, number=7):
    case = case_record(number, tmp_path / f'trial/cases/{number}/fixtures')
    good = good_draft(number, case['root'])
    bad = dict(good, nodes=list(good['nodes'].values()))
    return case, bad, good


@pytest.mark.asyncio
async def test_rejected_shape_redrafted_once_then_judged_and_saved(tmp_path):
    case, bad, good = drafts(tmp_path)
    report = await runner.run_case(7, tmp_path / 'trial', tmp_path / 'library', replies=[
        runner.requirements(case), bad, good, runner.meaning()])
    assert report['result'] == 'pass', report
    assert report['draft_retry'] == dict(requested=True, attempted=1, succeeded=1, check_passed=True)
    assert report['calls']['attempted'] == report['model_calls']['succeeded'] == 4
    directory = tmp_path / 'trial/cases/7'
    evidence = json.loads((directory / 'evidence.json').read_text())
    assert json.loads(evidence['first_draft_text']) == bad
    assert json.loads(evidence['draft_text']) == good
    assert evidence['first_check_error']['code'] == 'spec_invalid'
    calls = json.loads((directory / 'calls.json').read_text())
    question = calls[2]['messages'][0]['content']
    assert evidence['first_draft_text'] in question
    assert str(evidence['first_check_error']) in question
    assert evidence['draft_brief'] in question
    assert Path(report['saved_path']).read_text() == evidence['draft_text']


@pytest.mark.asyncio
async def test_second_rejection_stops_without_judge_or_save(tmp_path):
    case, bad, _ = drafts(tmp_path)
    report = await runner.run_case(7, tmp_path / 'trial', tmp_path / 'library', replies=[
        runner.requirements(case), bad, bad])
    assert report['result'] == 'fail'
    assert report['draft_retry'] == dict(requested=True, attempted=1, succeeded=1, check_passed=False)
    assert report['calls']['attempted'] == 3 and report['calls']['remaining'] == 0
    assert report['meaning_review'] == 'not_run'
    assert not list((tmp_path / 'trial/cases/7/drafts').glob('*'))


@pytest.mark.asyncio
async def test_retry_usage_and_budget_guard_use_existing_call_boundary(tmp_path, monkeypatch):
    case, bad, good = drafts(tmp_path)
    mock = runner.MockSDK([runner.requirements(case), bad, good, runner.meaning()])
    budget = runner.TrialBudget(1)
    monkeypatch.setattr(runner, '_budget', budget)
    with ExitStack() as stack:
        mock.install(stack)
        report = await runner.run_case(7, tmp_path / 'trial', tmp_path / 'library', real_calls=True)
    assert report['result'] == 'pass', report
    assert budget.calls == budget.succeeded == len(report['usage']) == 4
    assert not budget.unknown
    assert budget.cost == pytest.approx(sum(r['usage']['estimated_cost_usd'] for r in report['usage']))


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["cost", "time", "unknown"])
async def test_budget_can_stop_before_retry_adapter(tmp_path, monkeypatch, guard):
    case, bad, good = drafts(tmp_path)
    mock = runner.MockSDK([runner.requirements(case), bad, good, runner.meaning()])
    budget = runner.TrialBudget(1)
    original = budget.before
    def before():
        if budget.calls == 2:
            if guard == 'cost':
                budget.limit = budget.cost
            elif guard == 'time':
                budget.started -= budget.time_limit
            else:
                budget.unknown = True
        original()
    monkeypatch.setattr(budget, 'before', before)
    monkeypatch.setattr(runner, '_budget', budget)
    with ExitStack() as stack:
        mock.install(stack)
        report = await runner.run_case(7, tmp_path / 'trial', tmp_path / 'library', real_calls=True)
    assert report['result'] == 'fail' and len(mock.calls) == budget.calls == 2
    assert report['draft_retry']['requested']
    evidence = json.loads((tmp_path / 'trial/cases/7/evidence.json').read_text())
    assert 'first_check_error' in evidence and 'first_draft_text' in evidence


@pytest.mark.asyncio
async def test_adapter_json_rejection_does_not_trigger_structural_retry(tmp_path):
    case, _, _ = drafts(tmp_path)
    report = await runner.run_case(7, tmp_path / 'trial', tmp_path / 'library', replies=[
        runner.requirements(case), '{"nodes":'])
    assert report['result'] == 'fail' and report['calls']['attempted'] == 2
    assert report['draft_retry'] == dict(requested=False, attempted=0, succeeded=0, check_passed=False)
    evidence = json.loads((tmp_path / 'trial/cases/7/evidence.json').read_text())
    assert 'first_check_error' not in evidence


@pytest.mark.asyncio
async def test_retry_prompt_and_contracts_have_context_headroom():
    from tools.draft_trials.runner import contract_inventory
    spec = json.loads(runner.SPEC.read_text())
    prompt = spec['nodes']['retry_question']['config']['template'].format_map(dict(
        draft_brief='b' * 12000, first_draft_text='d' * 8000,
        first_check_error='e' * 12000))
    contracts, _ = await contract_inventory()
    assert len(prompt) + len(contracts) <= .8 * spec['nodes']['draft_retry']['config']['context_limit']
    assert spec['nodes']['draft_retry']['config']['max_tokens'] == spec['nodes']['draft']['config']['max_tokens']


@pytest.mark.asyncio
@pytest.mark.parametrize('case_set,number', [(1, 7), (2, 1), (3, 1), (4, 2)])
@pytest.mark.parametrize('redraft', [False, True])
async def test_blocked_empty_draft_explains_stop_without_check_retry_or_save(tmp_path, case_set, number, redraft):
    case = case_record(number, tmp_path / f'trial/cases/{number}/fixtures', case_set)
    good = good_draft(number, case['root'], case_set)
    blocked = dict(good, status='blocked', nodes={},
                   reason='The selected contracts cannot preserve the requested ordering.',
                   blocked_requirements=['r1: preserve ordering', 'r2: show both results'])
    replies = [runner.requirements(case)]
    if redraft:
        replies.append(dict(good, nodes={}))
    replies.append(blocked)
    report = await runner.run_case(number, tmp_path / 'trial', tmp_path / 'library',
                                   case_set=case_set, replies=replies)
    directory = tmp_path / f'trial/cases/{number}'
    run = json.loads((directory / 'designer-run.json').read_text())
    shown = '\n'.join(run['outputs'])
    assert blocked['reason'] in shown
    assert all(requirement in shown for requirement in blocked['blocked_requirements'])
    assert 'aotn build' not in shown
    assert 'Workflow spec did not pass' not in shown
    assert report['calls']['attempted'] == 2 + redraft
    assert all(error['code'] == 'spec_invalid' and error['handled'] for error in report['errors'])
    assert report['draft_retry']['requested'] == redraft
    assert report['draft_retry']['attempted'] == int(redraft)
    forbidden = {'check_retry', 'judge', 'write'}
    if not redraft:
        forbidden.update({'check', 'draft_retry'})
    assert not any(step['handle'] in forbidden
                   for step in report['gate_evidence'] if step['status'] == 'running')
    assert not list((directory / 'drafts').glob('*'))


@pytest.mark.asyncio
async def test_ready_empty_draft_still_fails_check_and_redrafts_once(tmp_path):
    case, _, good = drafts(tmp_path)
    empty = dict(good, status='ready', nodes={})
    report = await runner.run_case(7, tmp_path / 'trial', tmp_path / 'library', replies=[
        runner.requirements(case), empty, empty])
    assert report['spec_valid'] == 'fail'
    assert report['calls']['attempted'] == 3
    assert report['draft_retry'] == dict(requested=True, attempted=1, succeeded=1, check_passed=False)
    assert any('nodes: expected a non-empty object' in error['message'] for error in report['errors'])
    assert not list((tmp_path / 'trial/cases/7/drafts').glob('*'))

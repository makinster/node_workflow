"""Shared flow refusals reach the one repair as plain evidence; transport is mocked."""
import json
import pytest
from backend import meta_workflow
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from tests.test_stage_two_admission import second_merge_in_one_group, rewire
from tools.draft_trials import runner
from tools.draft_trials.case_set_four import case_record, good_draft


@pytest.mark.asyncio
@pytest.mark.parametrize('number', [3, 5], ids=['second_merge', 'escaping_route'])
async def test_shared_refusal_is_plain_and_redraft_passes(tmp_path, number):
    case = case_record(number, tmp_path / f'trial/cases/{number}/fixtures')
    good = good_draft(number, case['root'])
    bad = (json.loads(json.dumps(second_merge_in_one_group()).replace('/tmp/fixtures', case['root']))
           if number == 3 else rewire(json.loads(json.dumps(good)), 'no.default', 'end.input'))
    report = await runner.run_case(number, tmp_path / 'trial', tmp_path / 'library', case_set=4,
                                  replies=[runner.requirements(case), bad, good, runner.meaning()])
    directory = tmp_path / f'trial/cases/{number}'
    evidence = json.loads((directory / 'evidence.json').read_text())
    prompt = json.loads((directory / 'calls.json').read_text())[2]['messages'][0]['content']
    print(f"{number}: error={len(str(evidence['first_check_error']))} prompt={len(prompt)}")
    assert report['result'] == 'pass', report
    assert report['draft_retry'] == dict(requested=True, attempted=1, succeeded=1, check_passed=True)
    with pytest.raises(NodeError) as caught:
        await meta_workflow.check(NodeFactory(), json.dumps(bad), 8000)
    refusal = caught.value
    flow = refusal.details['flow_analysis']
    assert flow['profiles'] and flow['groups'] and flow['merges']['join']['arrivals']
    for finding in flow['findings']:
        assert finding['message'] in str(refusal)
        assert finding['message'] in prompt
        if finding['repair']:
            assert finding['repair'] in str(refusal)
            assert finding['repair'] in prompt
    assert 'Check this node’s configuration:' not in str(refusal)
    reduced = evidence['first_check_error']['details']
    assert reduced == meta_workflow.review_report(refusal.details)
    assert all(set(merge) == {'summary'} for merge in reduced['flow_analysis']['merges'].values())
    for raw_key in ('profiles', 'arrivals', 'dependencies', 'provenance', 'continuation_candidates'):
        assert f"'{raw_key}':" not in prompt
    assert evidence['first_draft_text'] in prompt
    assert evidence['draft_brief'] in prompt


@pytest.mark.asyncio
async def test_impossible_wait_uses_finding_message_and_repair():
    spec = dict(format='aotn-workflow/1', name='Impossible', nodes={
        'start': dict(type='start_node'),
        'wait': dict(type='wait_until_node', config=dict(target_node_ids=['end'])),
        'end': dict(type='end_node')}, connections=[
            {'from': 'start.default', 'to': 'wait.input'},
            {'from': 'wait.default', 'to': 'end.input'}])
    with pytest.raises(NodeError) as caught:
        await meta_workflow.check(NodeFactory(), json.dumps(spec), 8000)
    finding = next(f for f in caught.value.details['flow_analysis']['findings'] if f['code'] == 'impossible_wait')
    assert finding['message'] in str(caught.value)
    assert finding['repair'] in str(caught.value)


@pytest.mark.parametrize('node_id', ['join\nnode', ''])
def test_only_flow_findings_supply_prose_and_locations_remain_sanitized(node_id):
    finding = dict(code='flow_needs_review', node_id=node_id,
                   message='Reconnect password=do-not-show.', repair='Use one Merge.')
    diagnostic = dict(code=finding['code'], node=finding['node_id'] or None,
                      message=finding['message'], level='error')
    message, details = meta_workflow.problem_report([diagnostic], flow_findings=[finding], invalid=True)
    assert 'Use one Merge.' in message and 'do-not-show' not in message
    assert details['problems'][0]['node'] == ('join node' if node_id else None)
    message, _ = meta_workflow.problem_report([diagnostic], invalid=True)
    assert 'Reconnect' not in message
    assert 'Check this node’s configuration: flow needs review.' in message

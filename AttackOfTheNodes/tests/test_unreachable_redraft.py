import json
import pytest
from backend import meta_workflow
from backend.node_factory import NodeFactory
from backend.node_errors import NodeError
from tools.draft_trials import runner
from tools.draft_trials.cases import good_draft, case_record


@pytest.mark.asyncio
async def test_default_warns_opt_in_rejects_with_same_warning():
    draft = good_draft(8)
    draft['nodes']['spare_end'] = {'type': 'end_node'}
    raw = json.dumps(draft)
    _, report = await meta_workflow.check(NodeFactory(), raw, 8000)
    assert report['ok'] and report['warning_count'] == 1
    with pytest.raises(NodeError) as caught:
        await meta_workflow.check(NodeFactory(), raw, 8000, fail_on_unreachable=True)
    assert caught.value.code == 'spec_invalid'
    assert caught.value.details['problems'] == report['problems']
    assert report['problems'][0]['code'] == 'unreachable'
    assert report['problems'][0]['severity'] == 'warning'


@pytest.mark.asyncio
async def test_unreachable_end_redrafts_then_passes(tmp_path):
    case = case_record(8, tmp_path / 'trial/cases/8/fixtures')
    good = good_draft(8, case['root'])
    bad = json.loads(json.dumps(good))
    bad['nodes']['spare_end'] = {'type': 'end_node'}
    report = await runner.run_case(8, tmp_path / 'trial', tmp_path / 'library', replies=[
        runner.requirements(case), bad, good, runner.meaning()])
    assert report['result'] == 'pass', report
    assert report['draft_retry']['attempted'] == 1
    evidence = json.loads((tmp_path / 'trial/cases/8/evidence.json').read_text())
    assert evidence['first_check_error']['details']['problems'][0]['code'] == 'unreachable'
    prompt = json.loads((tmp_path / 'trial/cases/8/calls.json').read_text())[2]['messages'][0]['content']
    assert evidence['first_check_error']['details']['problems'][0]['message'] in prompt


def test_retry_template_uses_actual_newlines():
    spec = json.loads(runner.SPEC.read_text())
    text = spec['nodes']['retry_question']['config']['template']
    assert '\nEXACT CHECK ERROR:\n' in text and '\\n' not in text
    assert all(spec['nodes'][h]['config']['fail_on_unreachable'] for h in ('check', 'check_retry'))


@pytest.mark.asyncio
async def test_second_unreachable_draft_stops_before_judge_or_save(tmp_path):
    case=case_record(8,tmp_path/'cases/8/fixtures')
    bad=good_draft(8,case['root'])
    bad['nodes']['spare_end']={'type':'end_node'}
    report=await runner.run_case(8,tmp_path,tmp_path/'library',replies=[runner.requirements(case),bad,bad])
    assert report['result']=='fail' and report['calls']['attempted']==3
    assert not report['draft_retry']['check_passed']
    assert report['meaning_review']=='not_run'
    assert not list((tmp_path/'cases/8/drafts').glob('*'))


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['true', None])
async def test_unreachable_option_requires_boolean(value):
    with pytest.raises(NodeError) as caught:
        await meta_workflow.check(NodeFactory(),json.dumps(good_draft(1)),8000,fail_on_unreachable=value)
    assert caught.value.code=='invalid_config'

"""Second-set semantic/provenance checks and local behavior, SDK always mocked."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.draft_trials import runner
from tools.draft_trials.cases import case_record, fixture_variants, good_draft
from tools.draft_trials.rules import check_rules

RUNNABLE = [1,2,3,4,5,8,9,10]


@pytest.mark.parametrize('number', RUNNABLE)
@pytest.mark.asyncio
async def test_references_pass_rules_and_real_target_behavior(tmp_path, number):
    case=case_record(number,tmp_path/'fixtures',2)
    runner.prepare_files(Path(case['root']),fixture_variants(number,2)[0])
    spec=good_draft(number,case['root'],2)
    assert check_rules(spec,case)['result']=='pass'
    report=await runner.target_fixtures(spec,case,tmp_path/'target-runs')
    assert report['result']=='pass',report


def corrupt(spec,number):
    n=spec['nodes']
    if number==1:
        n['uppercase']['config']['operation']='lowercase'
    elif number==2:
        n['combine']['config']['template']='{input} {input}'
    elif number==3:
        n['show']['config']['template']='Wrong nickname'
    elif number==4:
        n['uppercase']['config']['operation']='strip'
    elif number==5:
        n['show']['config']['template']='reversed text'
    elif number in (8,9):
        n['write']['config'].update(content_source='Configured',content='invented')
    else:
        n['show']['config']['template']='Goodbye team'


@pytest.mark.parametrize('number', RUNNABLE)
@pytest.mark.asyncio
async def test_observable_defects_fail_rules_and_behavior(tmp_path,number):
    case=case_record(number,tmp_path/'fixtures',2)
    runner.prepare_files(Path(case['root']),fixture_variants(number,2)[0])
    bad=good_draft(number,case['root'],2)
    corrupt(bad,number)
    assert check_rules(bad,case)['result']=='fail'
    assert (await runner.target_fixtures(bad,case,tmp_path/'bad'))['result']=='fail'


@pytest.mark.parametrize('number', RUNNABLE)
def test_roles_and_provenance_do_not_require_reference_handles(tmp_path,number):
    case=case_record(number,tmp_path/'fixtures',2)
    runner.prepare_files(Path(case['root']),fixture_variants(number,2)[0])
    spec=good_draft(number,case['root'],2)
    mapping={h:'step_'+str(i) for i,h in enumerate(spec['nodes'])}
    spec['nodes']={mapping[h]:n for h,n in spec['nodes'].items()}
    for e in spec['connections']:
        for side in ('from','to'):
            h,port=e[side].split('.',1)
            e[side]=mapping[h]+'.'+port
    assert check_rules(spec,case)['result']=='pass'


@pytest.mark.asyncio
async def test_full_set_two_mock_batch_reports_statuses_and_case_set(tmp_path):
    report=await runner.batch(tmp_path,case_set=2)
    assert report['result']=='pass',report
    assert report['case_set']==2 and report['case_count']==10
    assert report['model_calls']==dict(attempted=77,succeeded=77) # 50 calibration + 27 case calls
    assert report['fixture_count']==23
    by_id={r['case']:r for r in report['cases']}
    assert by_id[5]['expected_outcome']=='clarified_workflow'
    assert by_id[5]['clarification']=='pass' and len(by_id[5]['input_trace'])==2
    for number,status in [(6,'outside_scope'),(7,'needs_new_node')]:
        row=by_id[number]
        assert row['scope']==row['status_check']['final']==status
        assert row['no_saved_workflow'] and not row['saved_workflow_expected']
        assert row['expected_outcome']=='status_only'
        assert row['behavior']['result']=='not_applicable'
        assert not list((tmp_path/f'cases/{number}/drafts').glob('*'))
    calibration=json.loads((tmp_path/'calibration-report.json').read_text())
    assert len(calibration['fixtures'])==50 and calibration['judge_false_passes']==0


@pytest.mark.asyncio
@pytest.mark.parametrize('number', [6,7])
async def test_wrong_terminal_status_fails(tmp_path,number):
    case=case_record(number,tmp_path/f'cases/{number}/fixtures',2)
    reply=runner.requirements(case)
    reply['status']='needs_new_node' if number==6 else 'outside_scope'
    report=await runner.run_case(number,tmp_path,tmp_path/'library',case_set=2,replies=[reply])
    assert report['result']=='fail' and report['calls']['attempted']==1
    assert report['no_saved_workflow']


@pytest.mark.asyncio
async def test_missing_path_must_clarify_before_drafting(tmp_path):
    case=case_record(5,tmp_path/'cases/5/fixtures',2)
    report=await runner.run_case(5,tmp_path,tmp_path/'library',case_set=2,replies=[runner.requirements(case)])
    assert report['result']=='fail' and report['behavior']['result']=='not_run'
    assert report['input_failure']=='missing expected prompt'


def test_cli_case_set_two_and_default_one(tmp_path):
    app=Path(runner.APP)
    for name,args,expected in [('two',['--case-set','2','--cases','6,7'],2),('one',['--cases','1'],1)]:
        proc=subprocess.run([sys.executable,'-m','tools.draft_trials','--trial-root',str(tmp_path/name),*args],cwd=app,
                            text=True,capture_output=True,timeout=30)
        assert proc.returncode==0,proc.stderr+proc.stdout
        stdout=json.loads(proc.stdout)
        assert stdout['case_set']==expected
        report=json.loads(Path(stdout['report']).read_text())
        assert report['case_set']==expected


def test_frozen_second_set_artifact_matches_definitions():
    from tools.draft_trials.case_set_two import frozen_cases
    stored=json.loads((Path(runner.__file__).parent/'fixtures/case_set_2.json').read_text())
    assert stored==json.loads(json.dumps(frozen_cases()))


@pytest.mark.asyncio
@pytest.mark.parametrize('number', [6,7])
async def test_status_without_reason_is_not_fully_right(tmp_path,number):
    case=case_record(number,tmp_path/f'cases/{number}/fixtures',2)
    reply=runner.requirements(case)
    reply['reason']=''
    report=await runner.run_case(number,tmp_path,tmp_path/'library',case_set=2,replies=[reply])
    assert report['result']=='fail' and report['fully_right'] is False
    assert report['no_saved_workflow']


def test_bad_case_set_rejected_before_creating_root(tmp_path):
    root=tmp_path/'unused'
    proc=subprocess.run([sys.executable,'-m','tools.draft_trials','--trial-root',str(root),'--case-set','3'],
                        cwd=runner.APP,text=True,capture_output=True,timeout=10)
    assert proc.returncode!=0 and not root.exists()


@pytest.mark.asyncio
async def test_two_answer_vault_copy_is_documented_in_full_contracts():
    contracts,_=await runner.contract_inventory()
    assert 'Optional membank_outputs copies the answer to Vault before continuing' in contracts
    assert 'Concat can read {key} alongside its current {input}' in contracts


@pytest.mark.asyncio
async def test_trim_and_uppercase_can_use_observably_equivalent_order(tmp_path):
    case=case_record(4,tmp_path/'fixtures',2)
    runner.prepare_files(Path(case['root']),fixture_variants(4,2)[0])
    spec=good_draft(4,case['root'],2)
    for edge in spec['connections']:
        for side in ('from','to'):
            h,port=edge[side].split('.',1)
            h={'strip':'uppercase','uppercase':'strip'}.get(h,h)
            edge[side]=h+'.'+port
    assert check_rules(spec,case)['result']=='pass'
    assert (await runner.target_fixtures(spec,case,tmp_path/'runs'))['result']=='pass'

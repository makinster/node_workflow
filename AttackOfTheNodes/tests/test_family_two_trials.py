"""Offline set 4, independent collector/provenance oracle and real-engine proof."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from backend.palette_selection import ADMITTED, ROLE_TYPES
from tools.draft_trials.case_set_four import (case_record,case_ids,fixture_variants,good_draft,calibration_pairs,REQUESTS,STAGES)
from tools.draft_trials.rules_family_two import check_rules,evaluate,safety,RuleFailure
from tools.draft_trials.family_two import verify,evidence
from tools.draft_trials.family_two_engine import run_fixture
from tools.draft_trials.dependencies import sets_from_text

APP=Path(__file__).parents[1]
FIXTURES=APP/'tools/draft_trials/fixtures'


def relocated(spec,root):
    return json.loads(json.dumps(spec).replace('ROOT',str(root)))


def test_frozen_thirty_pairs_and_admission_are_unchanged():
    from tools.draft_trials.cases import calibration_pairs as original
    frozen=(FIXTURES/'calibration.json').read_bytes()
    assert hashlib.sha256(frozen).hexdigest()=='684dc67afa52c557e501501a450c8706c55dc03fa943cb110af039fdff47cbf5'
    assert len(json.loads(frozen))==len(original())==30
    assert not {'merge_node','wait_until_node','branch_end_node'} & ADMITTED
    assert 'wait' not in ROLE_TYPES
    assert sets_from_text('all')==[1,2,3]
    with pytest.raises(ValueError):
        sets_from_text('4')


def test_data_snapshots_and_stage_partitions_are_explicit():
    data=json.loads((FIXTURES/'case_set_4.json').read_text())
    pairs=json.loads((FIXTURES/'calibration_set_4.json').read_text())
    assert not data['admitted'] and data['default_evaluation_stage']==1
    assert [c['key'] for c in data['cases']]==[f'F2-{i:02d}' for i in range(1,6)]
    for row in data['cases']:
        n=row['id']
        assert row['request']==REQUESTS[n-1] and row['expected_status']=='ready'
        assert row['required_stage']==STAGES[n]
        assert row['good']==good_draft(n)
        assert row['variants']==json.loads(json.dumps(fixture_variants(n)))
        assert all(v['answers']==[] and v['writes']=={} for v in row['variants'])
    assert pairs==calibration_pairs(stage=2)
    assert case_ids()==[1,2] and case_ids(2)==[1,2,3,4,5]
    assert {p['number'] for p in calibration_pairs()}=={1,6}
    assert {p['number'] for p in pairs if p['required_stage']==2}=={2,3,4,5}
    assert all(not p['admitted'] for p in pairs)
    assert good_draft(4)['nodes']['ready']['config']['label']==''


@pytest.mark.parametrize('n',range(1,6))
def test_good_cases_and_bad_pairs_have_expected_mechanical_verdict(n,tmp_path):
    case=case_record(n,tmp_path,stage=2)
    assert check_rules(good_draft(n,str(tmp_path)),case)['result']=='pass'
    for pair in calibration_pairs(stage=2):
        if pair['case']!=n:
            continue
        assert check_rules(relocated(pair['good'],tmp_path),case)['result']=='pass'
        assert check_rules(relocated(pair['bad'],tmp_path),case)['result']=='fail'


@pytest.mark.parametrize('n',[3,4,5])
def test_stage_two_is_outside_stage_one_not_an_engine_limitation(n,tmp_path):
    result=check_rules(good_draft(n,str(tmp_path)),case_record(n,tmp_path))
    assert result['result']=='fail'
    assert 'outside this admission stage' in str(result)
    assert 'engine cannot' not in str(result)


def test_beacon_is_not_admitted_in_any_legacy_scorer(tmp_path):
    from tools.draft_trials.cases import good_draft as old_draft,case_record as old_case
    from tools.draft_trials.rules import check_rules as all_rules
    for suite in (1,2,3):
        spec=old_draft(1,str(tmp_path),suite)
        spec['nodes']['forbidden']=dict(type='branch_end_node',config={})
        result=all_rules(spec,old_case(1,tmp_path,suite))
        assert result['result']=='fail'
        assert any(word in str(result).lower() for word in ('palette','admitted'))


async def test_every_fixture_and_pair_has_real_engine_differential_evidence(tmp_path):
    report=await verify(tmp_path/'evidence',stage=2)
    assert report['result']=='pass'
    assert len(report['cases'])==5 and len(report['calibration'])==6
    assert all(c['result']=='pass' for c in report['controls'])
    rows=[f for c in report['cases'] for f in c['fixtures']]
    rows += [f for p in report['calibration'] for v in p['variants'].values() for f in v['fixtures']]
    assert len(rows)==110 and all(r['result']=='pass' for r in rows)
    assert all(r['engine']['files_preserved'] for r in rows if r['engine']['state']=='finished')
    assert report['provenance']['real_api_calls']==0 and not report['admitted']
    assert report['provenance']['source_sha256']['backend/flow_behaviors.py']
    for pair in report['calibration']:
        bad=pair['variants']['bad']['fixtures']
        expected='preflight_rejected' if pair['number'] in (3,4) else 'finished'
        assert all(r['engine']['state']==expected and not r['correct_output'] for r in bad)
        if expected=='preflight_rejected':
            assert all(r['engine']['executions']==[] for r in bad)
    # Reverse scheduling changes who arrives first, not collection order.
    case1=report['cases'][0]['fixtures'][:2]
    winners=[]
    for r in case1:
        pubs=r['engine']['publications']
        join=next(p for p in pubs if p['handle']=='join')
        winners.append(next(p['handle'] for p in pubs if p['branch']==join['branch'] and p['handle'] in ('a','b')))
    assert winners==['a','b']
    assert all(r['facts']['shallow_continuation'] for r in report['cases'][2]['fixtures'])
    assert all(r['facts']['gate_after_read'] for r in report['cases'][3]['fixtures'])


async def test_default_offline_evaluation_omits_stage_two(tmp_path):
    report=await verify(tmp_path/'stage-one')
    assert report['result']=='pass'
    assert [c['id'] for c in report['cases']]==['F2-01','F2-02']
    assert {p['number'] for p in report['calibration']}=={1,6}
    assert all(c['required_stage']==1 for c in report['controls'])


def test_handles_concat_and_label_framing_do_not_define_the_layout(tmp_path):
    spec=good_draft(1,str(tmp_path))
    spec['nodes']['format']=dict(type='concat_node',config={'template':'[A] {input[path_a]}\n[B] {input[path_b]}'})
    spec['nodes']['show']['config']['template']='{input}'
    for e in spec['connections']:
        if e['from']=='join.default':
            e['to']='format.input'
    spec['connections'].append({'from':'format.default','to':'show.input'})
    renames={h:'renamed_'+str(i) for i,h in enumerate(spec['nodes'])}
    spec['nodes']={renames[h]:n for h,n in spec['nodes'].items()}
    for e in spec['connections']:
        for side in ('from','to'):
            h,p=e[side].split('.',1)
            e[side]=renames[h]+'.'+p
    assert check_rules(spec,case_record(1,tmp_path))['result']=='pass'


@pytest.mark.parametrize('mistake',['same-source','literal-answer','reversed','two-outputs','serial'])
def test_wrong_provenance_or_order_cannot_be_hidden_by_matching_words(mistake,tmp_path):
    spec=good_draft(1,str(tmp_path))
    if mistake=='same-source':
        spec['nodes']['b']['config']['file_path']=str(tmp_path/'report-a.txt')
    elif mistake=='literal-answer':
        spec['nodes']['show']['config']['template']='A: Alpha report\nB: Beta report'
    elif mistake=='reversed':
        spec['nodes']['show']['config']['template']='B: {input[path_b]}\nA: {input[path_a]}'
    elif mistake=='two-outputs':
        spec=relocated(next(p for p in calibration_pairs() if p['number']==6)['bad'],tmp_path)
    else:
        spec['connections']=[e for e in spec['connections'] if e['from'] not in ('split.path_b','a.default')]
        spec['connections'] += [{'from':'a.default','to':'b.input'},{'from':'split.path_b','to':'end.input'}]
        spec['nodes']['a']['config'].update(vault_write=True,vault_write_key='a')
        spec['nodes']['format']=dict(type='concat_node',config={'template':'A: {a}\nB: {input[path_b]}'})
        spec['nodes']['show']['config']['template']='{input}'
        for e in spec['connections']:
            if e['from']=='join.default':
                e['to']='format.input'
        spec['connections'].append({'from':'format.default','to':'show.input'})
    assert check_rules(spec,case_record(1,tmp_path,stage=2))['result']=='fail'


@pytest.mark.parametrize('order',['forward','reverse'])
async def test_ready_show_label_trap_and_branch_completion_is_not_reader_completion(order,tmp_path):
    c=case_record(4,tmp_path/'label',stage=2)
    spec=good_draft(4,c['root'])
    spec['nodes']['ready']['config'].pop('label')
    result=check_rules(spec,c)
    assert result['result']=='fail'
    r=await evidence(spec,c,fixture_variants(4)[0],order)
    assert r['result']=='pass' and not r['correct_output']
    assert 'Status: [Output] Ready' in r['engine']['outputs'][-1]
    c=case_record(4,tmp_path/'wrong-target',stage=2)
    spec=good_draft(4,c['root'])
    spec['nodes']['wait']['config']['target_node_ids']=['split']
    assert check_rules(spec,c)['result']=='fail'
    actual=await run_fixture(spec,c,fixture_variants(4)[0],order='reverse')
    read_done=next(i for i,e in enumerate(actual['events']) if e['handle']=='read' and e['status']=='done')
    ready_done=next(i for i,e in enumerate(actual['events']) if e['handle']=='ready' and e['status']=='done')
    assert ready_done<read_done


@pytest.mark.parametrize('target',['wait','show'])
def test_impossible_waits_use_the_shared_checker(target,tmp_path):
    spec=good_draft(4,str(tmp_path))
    spec['nodes']['wait']['config']['target_node_ids']=[target]
    result=check_rules(spec,case_record(4,tmp_path,stage=2))
    assert result['result']=='fail' and 'impossible_wait' in str(result)


def test_loop_and_independent_end_controls_use_shared_findings(tmp_path):
    from tools.draft_trials.family_two_controls import controls
    examples={c['id']:relocated(c['spec'],tmp_path) for c in controls(2)}
    loop=check_rules(examples['control_back_edge'],case_record(1,tmp_path))
    assert 'loops are not supported in drafts yet' in str(loop) and 'impossible_wait' not in str(loop)
    assert check_rules(examples['independent_side_end'],case_record(1,tmp_path))['result']=='fail'
    assert check_rules(examples['independent_side_end'],case_record(1,tmp_path,stage=2))['result']=='pass'


async def test_missing_is_not_empty_and_failures_do_not_publish_partial_records(tmp_path):
    c=case_record(1,tmp_path,stage=2)
    spec=good_draft(1,c['root'])
    spec['nodes']['b']['config']['transient_output']=False
    variant=fixture_variants(1)[2]
    logical=evaluate(spec,c,variant)
    assert logical['state']=='failed' and logical['collected'][0]['value']=={'path_a':'Alpha report'}
    real=await run_fixture(spec,c,variant)
    assert real['state']=='failed' and real['outputs']==[]
    spec['nodes']['b']['config'].update(transient_output=True,file_path=str(tmp_path/'missing.txt'))
    logical=evaluate(spec,c,variant)
    assert logical['state']=='failed' and logical['collected']==[]
    real=await run_fixture(spec,c,variant)
    assert real['state']=='failed' and not any(p['handle']=='join' for p in real['publications'])


async def test_stop_cancels_without_partial_collection_or_error(tmp_path):
    c=case_record(1,tmp_path)
    spec=good_draft(1,c['root'])
    variant=fixture_variants(1)[0]
    logical=evaluate(spec,c,variant,stop_after=3)
    assert logical['state']=='cancelled' and not logical['errors'] and not logical['outputs']
    real=await run_fixture(spec,c,variant,stop_after=3)
    assert real['state']=='cancelled' and not real['errors'] and not real['outputs']


def test_bad_numeric_list_projection_is_not_a_scalar_or_a_lost_member(tmp_path):
    spec=good_draft(3,str(tmp_path),same_slot=True)
    case=case_record(3,tmp_path,stage=2)
    assert check_rules(spec,case)['result']=='pass'
    for order in ('forward','reverse'):
        result=evaluate(spec,case,fixture_variants(3)[0],order=order)
        assert result['collected'][0]['value']['path_b']==['MIXED CASE','mixed case']
        assert sum(e['event']=='completed' and e.get('node')=='join' for e in result['events'])==1
        assert sum(e['event']=='absorbed' for e in result['events'])==2


async def test_context_pack_uses_distinct_vault_sources_and_fixed_contract(tmp_path):
    c=case_record(5,tmp_path,stage=2)
    spec=good_draft(5,c['root'])
    spec['nodes']['note']['config'].update(vault_write=True,vault_write_key='note')
    for h in ('yes','no'):
        spec['nodes'][h]['config'].update(vault_write=True,vault_write_key='decision')
    spec['nodes']['pack']=dict(type='context_pack_node',config=dict(include_run=False,include_errors=False,items=[
        dict(id='note',label='Note',source='Vault',vault_key='note'),
        dict(id='decision',label='Decision',source='Vault',vault_key='decision')]))
    spec['nodes']['show']['config']['template']='{input}'
    for e in spec['connections']:
        if e['from']=='join.default':
            e['to']='pack.input'
    spec['connections'].append({'from':'pack.default','to':'show.input'})
    assert check_rules(spec,c)['result']=='pass'
    r=await evidence(spec,c,fixture_variants(5)[0],'reverse')
    assert r['result']=='pass'
    spec['nodes']['pack']['config']['items'][0].update(source='Configured text',text='Hello')
    assert check_rules(spec,c)['result']=='fail'


def test_cli_has_no_real_call_path_or_default_stage_two(tmp_path):
    for args in (['--real-calls'],['--stage','3']):
        out=tmp_path/str(len(args))
        result=subprocess.run([sys.executable,'-m','tools.draft_trials.family_two','--output',str(out),*args],cwd=APP,capture_output=True,text=True)
        assert result.returncode==2 and not out.exists()

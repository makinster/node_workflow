"""Admission proofs: schemas, exact frozen scope, fixtures and contained engine."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from backend.node_factory import NodeFactory
from backend.node_errors import NodeError
from backend import node_catalogue
from backend.palette_selection import (ADMITTED, HELPER_PALETTE, ORIGINAL_PALETTE, HELPERS, ROLE_TYPES, STAGE_ONE,
    CONTRACT_LIMIT, CONTEXT_LIMIT, exact_ids, snapshot, read_snapshot)
from backend.node_metadata import record_problems,selection,selection_problems,NODE_METADATA
from tools.draft_trials import runner
from tools.draft_trials.cases import PALETTE,calibration_pairs,case_record,good_draft,fixture_variants
from tools.draft_trials.admission import configure
from tools.draft_trials.reply_schemas import analysis_schema
from tools.draft_trials.rules import check_rules


def test_family_schema_enums_and_frozen_baseline():
    assert ORIGINAL_PALETTE==PALETTE and len(ORIGINAL_PALETTE)==11
    assert HELPER_PALETTE==ORIGINAL_PALETTE|HELPERS and len(HELPER_PALETTE)==15
    assert ADMITTED==HELPER_PALETTE|STAGE_ONE and len(ADMITTED)==16
    spec=json.loads(runner.SPEC.read_text())
    for node in ('analysis','resolve','analysis_shape','resolved_shape'):
        schema=spec['nodes'][node]['config']['reply_schema']
        assert schema==analysis_schema()
        selection=schema['properties']['selection']['properties']
        assert selection['candidates']['items']['properties']['type_id']['enum']==sorted(ADMITTED)
        assert selection['roles']['items']['properties']['role']['enum']==sorted(ROLE_TYPES)
    frozen=configure(deepcopy(spec),ORIGINAL_PALETTE)
    assert set(frozen['nodes']['brief']['config']['type_ids'])==PALETTE
    assert set(frozen['nodes']['selected_contracts']['config']['admitted_type_ids'])==PALETTE
    schema=frozen['nodes']['analysis']['config']['reply_schema']
    assert set(schema['properties']['selection']['properties']['candidates']['items']['properties']['type_id']['enum'])==PALETTE
    with pytest.raises(NodeError,match='Not admitted'):
        exact_ids(NodeFactory(),['find_lines_node'],allowed=ORIGINAL_PALETTE)
    # No judge prompt tuning as part of family admission.
    old=json.loads(subprocess.check_output(['git','show','8ee108b:AttackOfTheNodes/docs/delivery_tests/specs/draft-a-workflow-v2.json']))
    assert spec['nodes']['judge_question']==old['nodes']['judge_question']
    for name in ('analysis_question','resolve_question','draft_question'):
        assert 'find_lines_node' in spec['nodes'][name]['config']['template']


@pytest.mark.parametrize('kind',sorted(HELPERS))
def test_reviewed_links_are_explicit_and_valid(kind):
    record=NODE_METADATA[kind]
    assert not record_problems(kind,record)
    assert not selection_problems(kind,selection(record))
    assert record['use_instead']
    for target in ('unknown_node',kind,'tombstone_node'):
        broken=deepcopy(record);broken['use_instead'][0]['node_type']=target
        assert record_problems(kind,broken)


@pytest.mark.asyncio
@pytest.mark.parametrize('number',range(1,5))
async def test_family_real_pipeline_and_target_fixtures(tmp_path,number):
    report=await runner.run_case(number,tmp_path/'trial',tmp_path/'library',case_set=3)
    assert report['result']=='pass',report
    assert report['calls']==dict(attempted=3,succeeded=3,remaining=0)
    assert report['usage_summary']['reported']==3
    assert not report['recall']['missing_roles']
    assert report['selection']['contracts_characters']<CONTRACT_LIMIT
    assert all(row['result']=='pass' for row in report['behavior']['fixtures'])
    for row in report['behavior']['fixtures']:
        artifact=json.loads(Path(row['run_artifact']).read_text())
        assert artifact['system_node_folders']==str(tmp_path/'trial/cases'/str(number)/'fixtures')


@pytest.mark.parametrize('pair',[p for p in calibration_pairs() if p.get('case_set')==3],ids=lambda p:p['id'])
def test_family_calibration_expected_verdicts(tmp_path,pair):
    case=case_record(pair['case'],tmp_path,3)
    runner.prepare_files(tmp_path,fixture_variants(pair['case'],3)[0])
    for variant,wanted in [('good','pass'),('bad','fail')]:
        spec=json.loads(json.dumps(pair[variant]).replace('ROOT',str(tmp_path)))
        assert check_rules(spec,case)['result']==wanted
    assert pair['dependencies']['family']=='text_json_line_helpers'
    assert pair['dependencies']['used_types']


@pytest.mark.asyncio
async def test_complete_family_contracts_and_snapshot_budget():
    factory=NodeFactory();cfg=factory.create_config_template('node_catalogue_node')
    cfg.update(scope='Exact IDs',type_ids=sorted(ADMITTED),max_chars=CONTRACT_LIMIT)
    text=await node_catalogue.build(factory,cfg)
    brief=await node_catalogue.build(factory,dict(cfg,detail='Brief'))
    assert len(text)<CONTRACT_LIMIT and len(brief)+len(text)<CONTEXT_LIMIT
    for kind in HELPERS:assert 'node '+kind+' |' in text
    for n in range(1,5):
        case=case_record(n,'/tmp/family',3)
        selected=await snapshot(factory,runner.requirements(case),case['request'],cfg)
        assert len(selected)<CONTRACT_LIMIT
        assert read_snapshot(selected)['missing_roles']==[]
    held=[p for p in calibration_pairs() if p.get('held_out')]
    assert held and len(calibration_pairs())==30


@pytest.mark.parametrize('number',range(1,5))
def test_equivalent_routing_and_renamed_handles(tmp_path,number):
    case=case_record(number,tmp_path,3)
    runner.prepare_files(tmp_path,fixture_variants(number,3)[0])
    spec=good_draft(number,str(tmp_path),3)
    if number==1:spec['nodes']['start']['config']['greeting']='999'  # configured line number wins
    if number==2:
        spec['nodes']['find']['config'].update(vault_write=True,vault_write_key='matches')
        spec['nodes']['read']['config'].update(input_source='Vault',input_vault_key='matches')
    if number==3:
        del spec['nodes']['field']
        spec['connections']=[e for e in spec['connections'] if not e['from'].startswith('field.') and e['to']!='field.input']
        spec['connections'].append({'from':'check.default','to':'show.input'})
        spec['nodes']['show']['config']['template']='{input[summary]}'
    # Identity/aliases cannot be oracle answers.
    spec['nodes']={'renamed_'+h:n for h,n in spec['nodes'].items()}
    for edge in spec['connections']:
        for key in ('from','to'):edge[key]='renamed_'+edge[key]
    assert check_rules(spec,case)['result']=='pass'


@pytest.mark.slow
def test_mock_set_three_cli(tmp_path):
    result=subprocess.run([sys.executable,'-m','tools.draft_trials','--case-set','3','--trial-root',str(tmp_path/'trial')],
                          text=True,capture_output=True,timeout=60,cwd=runner.APP)
    assert result.returncode==0,result.stdout+result.stderr
    report=json.loads(Path(json.loads(result.stdout)['report']).read_text())
    assert report['case_set']==3 and report['case_count']==4 and report['fully_right']==4
    assert report['fixture_count']==12


def test_original_suites_and_calibration_content_are_frozen():
    from tools.draft_trials import cases,case_set_two
    from backend.palette_selection import ORIGINAL_ROLE_IDS
    receipt=json.loads((Path(runner.__file__).parent/'fixtures/admission_baseline.json').read_text())
    assert receipt['type_ids']==sorted(PALETTE)==sorted(ORIGINAL_PALETTE)
    assert receipt['role_ids']==sorted(ORIGINAL_ROLE_IDS)
    def digest(v):
        return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert digest(calibration_pairs()[:receipt['calibration_pair_count']])==receipt['calibration_sha256']
    for s in (1,2):
        module=cases if s==1 else case_set_two
        content=dict(requests=module.REQUESTS,drafts=[None if s==2 and n in (6,7) else good_draft(n,'ROOT',s) for n in range(1,11)],
                     variants=[fixture_variants(n,s) for n in range(1,11)],structures=module.STRUCTURES)
        assert digest(content)==receipt['sets_sha256'][str(s)]


def test_pending_lookalike_is_visible_without_granting_admission():
    from backend.node_catalogue import intent_lines
    record=deepcopy(NODE_METADATA['context_pack_node'])
    record['use_instead']=[dict(when='Cross-run storage',node_type='remember_node')]
    assert not record_problems('context_pack_node',record)
    assert any('remember_node (not admitted)' in line for line in intent_lines(record,notes=False))
    with pytest.raises(NodeError,match='Not admitted'):
        exact_ids(NodeFactory(),['remember_node'])
    record['use_instead']*=2
    assert record_problems('context_pack_node',record)


@pytest.mark.asyncio
@pytest.mark.parametrize('role,kind', [('find_in_file','find_lines_node'),('read_excerpt','read_lines_node'),
    ('check_json_reply','check_reply_node'),('pack_context','context_pack_node')])
async def test_family_role_expansion_is_narrow_and_original_scope_stops(role,kind):
    req=runner.requirements(case_record(1,'/tmp/family',3))
    req['selection']=dict(candidates=[],roles=[dict(role=role,requirement_ids=['r1'],reason='Need '+role)])
    factory=NodeFactory()
    cfg=factory.create_config_template('node_catalogue_node')
    text=await snapshot(factory,req,kind+' '+role,cfg)
    receipt=read_snapshot(text)
    assert receipt['selected_type_ids']==sorted({'start_node','end_node',kind})
    assert receipt['expansion_count']==1
    cfg['admitted_type_ids']=sorted(ORIGINAL_PALETTE)
    with pytest.raises(NodeError) as exc:
        await snapshot(factory,req,kind+' '+role,cfg)
    assert exc.value.code=='selection_incomplete'
    assert exc.value.details['status']=='not_admitted'
    assert exc.value.details['not_admitted']==[kind]

"""Paid-trial regressions: real local nodes, canned inference only."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from backend import node_catalogue
from backend.node_factory import NodeFactory
from backend.node_errors import NodeError
from backend import palette_selection as selection
from tools.draft_trials import runner
from tools.draft_trials.cases import case_record, fixture_variants, good_draft
from tools.draft_trials.rules import check_rules
from tools.draft_trials.admission import configure
from tools.draft_trials.reply_schemas import analysis_schema
from backend.reply_schema import check, provider_schema

FIXTURE = Path(runner.__file__).parent/'fixtures/regressions/run_000035_case_3.json'


@pytest.mark.parametrize('kind', ['action', None, 'constraint'])
def test_only_constraints_are_exempt_from_role_coverage(kind):
    value = runner.requirements(case_record(2, '/tmp/constraint-fixtures', 3))
    value['selection'] = dict(candidates=[], roles=[])
    if kind is not None:
        value['requirements'][0]['kind'] = kind
    original = deepcopy(value)
    check(value, analysis_schema())
    if kind == 'constraint':
        assert selection.validate_analysis(NodeFactory(), value) == value['selection']
        assert runner.valid_analysis(value)
    else:
        with pytest.raises(NodeError, match='cover every action requirement'):
            selection.validate_analysis(NodeFactory(), value)
        assert not runner.valid_analysis(value)
    assert value == original


@pytest.mark.parametrize('kind', ['prohibition', '', None, [], True])
def test_unknown_requirement_kind_is_rejected_by_schema_and_selection(kind):
    value = runner.requirements(case_record(2, '/tmp/constraint-fixtures', 3))
    value['requirements'][0]['kind'] = kind
    with pytest.raises(NodeError, match='schema'):
        check(value, analysis_schema())
    with pytest.raises(NodeError, match='Requirement kind'):
        selection.validate_analysis(NodeFactory(), value)
    assert not runner.valid_analysis(value)


def test_requirement_kind_is_optional_before_acceptance_for_both_admissions():
    spec = json.loads(runner.SPEC.read_text())
    for admitted in (selection.ORIGINAL_PALETTE, selection.ADMITTED):
        active = configure(deepcopy(spec), admitted)
        for name in ('analysis', 'resolve', 'analysis_shape', 'resolved_shape'):
            schema = active['nodes'][name]['config']['reply_schema']
            for checked in (schema, provider_schema(schema)):
                row = checked['properties']['requirements']['items']
                fields = list(row['properties'])
                assert fields.index('kind') + 1 == fields.index('acceptance')
                assert row['properties']['kind'] == dict(type='string', enum=['action', 'constraint'], default='action')
                assert 'kind' not in row['required']
                assert set(row['required']) == set(fields) - {'kind'}
            ids = schema['properties']['selection']['properties']['candidates']['items']['properties']['type_id']['enum']
            assert ids == sorted(admitted)
        for name in ('analysis_question', 'resolve_question'):
            prompt = active['nodes'][name]['config']['template']
            assert 'Prohibitions and limits are constraints, not steps.' in prompt
            assert 'Cover every action requirement.' in prompt


def test_ready_still_needs_a_requirement():
    value = dict(status='ready', requirements=[], selection=dict(candidates=[], roles=[]))
    with pytest.raises(NodeError, match='cover every action requirement'):
        selection.validate_analysis(NodeFactory(), value)


@pytest.mark.asyncio
async def test_uncovered_constraint_reaches_draft_and_judge_and_remains_enforced(tmp_path):
    case = case_record(2, tmp_path/'trial/cases/2/fixtures', 3)
    value = runner.requirements(case)
    constraint = dict(id='r2', action='Do not write or change any file', source='fixture library',
                      destination='unchanged files', order=2, kind='constraint', acceptance='No filesystem writes')
    value['requirements'].append(constraint)
    verdict = runner.meaning()
    assert not runner.valid_judge(verdict, value)  # Constraints still need judge coverage.
    verdict['coverage'].append(dict(requirement_id='r2', evidence='All nodes are read-only', met=True))
    assert runner.valid_judge(verdict, value)
    draft = good_draft(2, case['root'], 3)
    report = await runner.run_case(2, tmp_path/'trial', tmp_path/'library', case_set=3,
        replies=[value, draft, verdict])
    assert report['result'] == 'pass', report
    assert report['model_calls'] == dict(attempted=3, succeeded=3)
    evidence = json.loads((tmp_path/'trial/cases/2/evidence.json').read_text())
    assert json.loads(evidence['frozen_requirements'])['requirements'][-1] == constraint
    calls = json.loads((tmp_path/'trial/cases/2/calls.json').read_text())
    for call in calls[1:]:
        assert constraint['action'] in json.dumps(call)
        assert 'constraint' in json.dumps(call)
    # Case rules still reject a write even when it targets the allowed fixture directory.
    bad = deepcopy(draft)
    bad['nodes']['write'] = dict(type='file_output_node', config=dict(file_path=str(Path(case['root'])/'extra.txt')))
    for edge in bad['connections']:
        if edge['from'] == 'show.default':
            edge['to'] = 'write.content'
    bad['connections'].append({'from': 'write.default', 'to': 'end.input'})
    rules = check_rules(bad, case)
    assert rules['result'] == 'fail'
    assert any(row['result'] == 'fail' and 'Unrequested filesystem write' in str(row['evidence'])
               for row in rules['rules'])


def recorded_draft(root):
    return json.loads(FIXTURE.read_text().replace('ROOT',str(root)))


@pytest.mark.asyncio
@pytest.mark.parametrize('detail',['Compact','Detailed'])
async def test_per_node_standard_and_configured_descriptions(detail):
    factory=NodeFactory()
    cfg=factory.create_config_template('node_catalogue_node')
    cfg.update(scope='Exact IDs',type_ids=sorted(selection.ADMITTED),detail=detail,max_chars=200000)
    text=await node_catalogue.build(factory,cfg)
    record=await node_catalogue.build(factory,dict(cfg,format='JSON'))
    for entry in record['entries']:
        chunk=text.split('node '+entry['type']+' |',1)[1].split('\nnode ',1)[0]
        for key,value in entry.get('standard_key_docs',{}).items():
            assert 'Standard config: '+key+': '+value in chunk
        if entry.get('configured_inputs'):
            assert 'Configured: '+' '.join(entry['configured_inputs'].values()) in chunk
    assert 'Configured mappings:' not in text
    assert 'for nodes declaring this flag' not in text


@pytest.mark.asyncio
async def test_saved_conditional_json_shape_passes_rules_and_real_engine(tmp_path):
    case=case_record(3,tmp_path/'fixtures',3)
    runner.prepare_files(Path(case['root']),fixture_variants(3,3)[0])
    draft=recorded_draft(case['root'])
    report=check_rules(draft,case)
    assert report['result']=='pass',report
    behavior=await runner.target_fixtures(draft,case,tmp_path/'runs')
    assert behavior['result']=='pass',behavior
    assert len(behavior['fixtures'])==4
    bad=deepcopy(draft)
    bad['nodes']['guard']['config']['condition_type']='equals'
    assert check_rules(bad,case)['result']=='fail'
    bad=deepcopy(draft)
    bad['nodes']['extract_summary']['config']['path']='count'
    assert check_rules(bad,case)['result']=='fail'


def test_merge_beacon_is_refused_in_a_set_three_draft(tmp_path):
    case=case_record(3,tmp_path,3)
    runner.prepare_files(tmp_path,fixture_variants(3,3)[0])
    draft=recorded_draft(tmp_path)
    draft['nodes']['extra']=dict(type='branch_end_node',config={})
    report=check_rules(draft,case)
    assert report['result']=='fail' and 'outside admitted palette' in str(report['rules'])


@pytest.mark.parametrize('kind',['text_transform_node'])
def test_other_locally_executable_admitted_types_are_evaluated(tmp_path,kind):
    case=case_record(3,tmp_path,3)
    runner.prepare_files(tmp_path,fixture_variants(3,3)[0])
    draft=recorded_draft(tmp_path)
    draft['nodes']['extra']=dict(type=kind,config={'operation':'uppercase'} if kind=='text_transform_node' else {})
    for edge in draft['connections']:
        if edge['from']=='extract_summary.default':edge['to']='extra.input'
    draft['connections'].append({'from':'extra.default','to':'show_summary.input'})
    report=check_rules(draft,case)
    assert report['result']==('fail' if kind=='text_transform_node' else 'pass'),report
    assert all('bounded local helpers' not in str(row['evidence']) for row in report['rules'])


def parallel_draft(root):
    draft=good_draft(3,str(root),3)
    draft['nodes']['fork']=dict(type='branch_node',config={'branch_count':2})
    for edge in draft['connections']:
        if edge['from']=='start.default':edge['to']='fork.input'
    draft['connections'] += [{'from':'fork.path_a','to':'read.input'},
                             {'from':'fork.path_b','to':'end.input'}]
    return draft


def test_unmodelled_admitted_composition_needs_review(tmp_path):
    case=case_record(3,tmp_path,3)
    runner.prepare_files(tmp_path,fixture_variants(3,3)[0])
    report=check_rules(parallel_draft(tmp_path),case)
    assert report['result']=='needs_review',report
    assert any(row['result']=='needs_review' for row in report['rules'])
    # A known invalid path must still fail, even alongside an oracle limitation.
    bad=parallel_draft(tmp_path)
    bad['nodes']['read']['config']['file_path']='/outside-fixture/reply.json'
    assert check_rules(bad,case)['result']=='fail'


@pytest.mark.asyncio
async def test_needs_review_is_preserved_in_case_and_batch_reports(tmp_path,monkeypatch):
    case=case_record(3,tmp_path/'trial/cases/3/fixtures',3)
    analysis=runner.requirements(case)
    row=dict(type_id='branch_node',role='parallel_paths',requirement_ids=['r1'],reason='Parallel composition')
    analysis['selection']['candidates'].append(row)
    analysis['selection']['roles'].append({k:v for k,v in row.items() if k!='type_id'})
    report=await runner.run_case(3,tmp_path/'trial',tmp_path/'library',case_set=3,
        replies=[analysis,parallel_draft(case['root']),runner.meaning()])
    assert report['result']=='needs_review',report
    assert report['case_rules']['result']=='needs_review'
    assert report['behavior']['result']=='not_run'
    assert not report['fully_right']
    assert not (tmp_path/'trial/cases/3/target-runs').exists()
    assert report['model_calls']==dict(attempted=3,succeeded=3)
    async def calibration(*args,**kwargs):
        return dict(result='pass',model_calls=dict(attempted=0,succeeded=0))
    async def case_report(*args,**kwargs):
        return report
    monkeypatch.setattr(runner,'calibrate',calibration)
    monkeypatch.setattr(runner,'run_case',case_report)
    (tmp_path/'batch').mkdir()
    result=await runner.batch(tmp_path/'batch',case_ids=[3],case_set=3)
    assert result['result']=='needs_review',result
    assert result['fully_right']==0
    assert not result['failures']
    assert result['reviews_needed'][0]['case']==3


def analysis(roles,candidates):
    return dict(status='ready',requirements=[dict(id='r1')],selection=dict(
        roles=[dict(role=r,reason='Required outcome',requirement_ids=['r1']) for r in roles],
        candidates=[dict(type_id=t,role=r,reason='Candidate capability',requirement_ids=['r1']) for t,r in candidates]))


@pytest.mark.parametrize('kind',['start_node','end_node'])
def test_undeclared_always_included_candidates_are_dropped(kind):
    value=analysis(['show_text'],[(kind,kind.removesuffix('_node')),('text_output_node','show_text')])
    original=deepcopy(value)
    result=selection.validate_analysis(NodeFactory(),value)
    assert [c['type_id'] for c in result['candidates']]==['text_output_node']
    assert value==original


def test_candidate_is_reassigned_to_its_unique_declared_role():
    value=analysis(['show_saved_path'],[('text_output_node','show_text')])
    original=deepcopy(value)
    result=selection.validate_analysis(NodeFactory(),value)
    assert result['candidates'][0]['role']=='show_saved_path'
    assert value==original


def _vault_only_reply(candidates, vault_ids):
    rows = [dict(type_id=kind, role=role, requirement_ids=ids, reason='A step') for kind, role, ids in candidates]
    ids = sorted({i for _, _, row in candidates for i in row})
    return dict(status='ready', requirements=[dict(id=i, kind='action') for i in ids],
                selection=dict(candidates=rows, roles=[dict(role='vault_state', reason='Keeps values', requirement_ids=vault_ids)]))


def test_steps_named_only_on_nodes_are_declared_when_roles_lists_only_the_vault():
    value=_vault_only_reply([('start_node','start',['r1']),('user_text_input_node','ask_text',['r1','r2']),
                             ('concat_node','compose_text',['r3']),('text_output_node','show_text',['r4'])],['r1','r2','r3'])
    original=deepcopy(value)
    result=selection.validate_analysis(NodeFactory(),value)
    assert [r['role'] for r in result['roles']]==['vault_state','ask_text','compose_text','show_text']
    assert next(c for c in result['candidates'] if c['type_id']=='concat_node')['role']=='compose_text'
    assert 'start_node' not in [c['type_id'] for c in result['candidates']]
    assert value==original


def test_a_node_role_that_does_not_fit_its_type_is_still_refused_with_the_vault_only():
    value=_vault_only_reply([('text_output_node','read_file',['r1'])],['r1'])
    with pytest.raises(NodeError,match='Candidate roles'):
        selection.validate_analysis(NodeFactory(),value)


def test_ambiguous_candidate_role_still_errors():
    value=analysis(['show_saved_path','error_route'],[('text_output_node','show_text')])
    with pytest.raises(NodeError,match='Candidate roles'):
        selection.validate_analysis(NodeFactory(),value)


def test_declared_start_role_is_not_dropped_and_no_match_still_errors():
    value=analysis(['start'],[('start_node','start')])
    assert selection.validate_analysis(NodeFactory(),value)['candidates'][0]['type_id']=='start_node'
    value=analysis(['read_file'],[('text_output_node','show_text')])
    with pytest.raises(NodeError,match='Candidate roles'):
        selection.validate_analysis(NodeFactory(),value)


@pytest.mark.asyncio
async def test_repaired_selection_passes_the_mock_pipeline_without_an_extra_call(tmp_path):
    case=case_record(5,tmp_path/'trial/cases/5/fixtures')
    value=runner.requirements(case)
    for row in value['selection']['roles']:
        if row['role']=='show_text':row['role']='show_saved_path'
    value['selection']['candidates'].append(dict(type_id='start_node',role='start',
        reason='Always starts',requirement_ids=['r1']))
    report=await runner.run_case(5,tmp_path/'trial',tmp_path/'library',
        replies=[value,good_draft(5,case['root']),runner.meaning()])
    assert report['result']=='pass',report
    assert report['model_calls']==dict(attempted=3,succeeded=3)
    assert report['selection']['expansion_count']==0


@pytest.mark.parametrize('source',['Upstream payload','Vault'])
def test_unmodelled_active_reader_source_needs_review(tmp_path,source):
    case=case_record(3,tmp_path,3)
    runner.prepare_files(tmp_path,fixture_variants(3,3)[0])
    draft=recorded_draft(tmp_path)
    draft['nodes']['start']['config']['rows']=[dict(name='file',type='file',to='Both',
        value=dict(type='file',ref_key='source',path=str(tmp_path/'reply.json')))]
    draft['nodes']['read_reply']['config'].update(input_source=source,file_path='',input_vault_key='file')
    report=check_rules(draft,case)
    assert report['result']=='needs_review',report
    assert 'Dynamic File Reader references' in str(report['rules'])

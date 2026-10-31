"""Family 2 Stage 1: one split, each path wired to one Merge, result used downstream."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from backend import node_catalogue
from backend.authoring import check_workflow_spec
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from backend.palette_selection import (ADMISSION_VERSIONS, ADMITTED, CONTEXT_LIMIT, CONTRACT_LIMIT, HELPER_PALETTE,
    ORIGINAL_PALETTE, ROLE_TYPES, check_draft, implemented_not_admitted, read_snapshot, snapshot, stage_one_problems)
from tools.draft_trials import runner
from tools.draft_trials.admission import JOIN_ANALYSIS, JOIN_DRAFT, SUITE_SCOPE, configure
from tools.draft_trials.case_set_four import calibration_pairs, case_ids, case_record, fixture_variants, good_draft
from tools.draft_trials.cases import case_record as any_case
from tools.draft_trials.rules import check_rules
from tools.draft_trials.rules_family_two import shown_fields_match

F = NodeFactory()
SPEC = json.loads(runner.SPEC.read_text())
BASELINE = json.loads((Path(runner.__file__).parent/'fixtures/admission_baseline.json').read_text())['stage_1']


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def flow_of(spec):
    report = check_workflow_spec(F, spec)
    assert report['ok'], report['diagnostics']
    return report['flow_analysis']


def wire(spec, source, target):
    spec['connections'] = [e for e in spec['connections'] if e['from'] != source]
    spec['connections'].append({'from': source, 'to': target})


def transform(spec, handle, operation='uppercase'):
    spec['nodes'][handle] = dict(type='text_transform_node', config=dict(operation=operation))


def nested_join():
    return good_draft(3, '/tmp/fixtures')


def same_slot_concurrent():
    return good_draft(3, '/tmp/fixtures', same_slot=True)


def same_slot_either_or():
    return good_draft(5, '/tmp/fixtures')


def wait_gate():
    return good_draft(4, '/tmp/fixtures')


def nested_split_without_merge():
    spec = good_draft(1, '/tmp/fixtures')
    del spec['nodes']['join']
    spec['connections'] = [e for e in spec['connections'] if 'join.' not in e['from']+e['to']]
    spec['nodes']['inner'] = dict(type='branch_node', config=dict(branch_count=2))
    transform(spec, 'upper'); transform(spec, 'lower', 'lowercase')
    spec['connections'] += [{'from': 'a.default', 'to': 'end.input'}, {'from': 'b.default', 'to': 'inner.input'},
                            {'from': 'inner.path_a', 'to': 'upper.input'}, {'from': 'inner.path_b', 'to': 'lower.input'},
                            {'from': 'upper.default', 'to': 'show.input'}, {'from': 'lower.default', 'to': 'end.input'}]
    return spec


def two_merges_on_either_or_routes():
    # Separate groups on exclusive routes: analysis alone reports no repeated join.
    spec = dict(format='aotn-workflow/1', name='Two', nodes={'start': dict(type='start_node'), 'end': dict(type='end_node'),
        'choose': dict(type='conditional_node', config=dict(condition_type='equals', right_value='yes', left_value_source='input'))},
        connections=[{'from': 'start.default', 'to': 'choose.input'}])
    for route in ('true', 'false'):
        split, one, two, join, show = (route+'_'+h for h in ('split', 'one', 'two', 'join', 'show'))
        spec['nodes'].update({split: dict(type='branch_node', config=dict(branch_count=2)), join: dict(type='merge_node'),
                              show: dict(type='text_output_node', config=dict(template='{input[path_a]}'))})
        transform(spec, one); transform(spec, two, 'lowercase')
        spec['connections'] += [{'from': 'choose.'+route, 'to': split+'.input'}, {'from': split+'.path_a', 'to': one+'.input'},
                                {'from': split+'.path_b', 'to': two+'.input'}, {'from': one+'.default', 'to': join+'.path_a'},
                                {'from': two+'.default', 'to': join+'.path_b'}, {'from': join+'.default', 'to': show+'.input'},
                                {'from': show+'.default', 'to': 'end.input'}]
    return spec


def split_after_merge():
    spec = good_draft(1, '/tmp/fixtures')
    spec['nodes']['later'] = dict(type='branch_node', config=dict(branch_count=2))
    wire(spec, 'join.default', 'later.input')
    transform(spec, 'other')
    spec['connections'] += [{'from': 'later.path_a', 'to': 'show.input'}, {'from': 'later.path_b', 'to': 'other.input'},
                            {'from': 'other.default', 'to': 'end.input'}]
    return spec


def path_ends_before_merge():
    spec = good_draft(1, '/tmp/fixtures')
    spec['nodes']['split']['config']['branch_count'] = 3
    spec['connections'].append({'from': 'split.path_c', 'to': 'end.input'})
    return spec


def result_goes_straight_to_end():
    spec = good_draft(1, '/tmp/fixtures')
    del spec['nodes']['show']
    spec['connections'] = [e for e in spec['connections'] if 'show.' not in e['from']+e['to']]
    spec['connections'].append({'from': 'join.default', 'to': 'end.input'})
    return spec


@pytest.mark.parametrize('build, words', [
    (nested_join, 'split inside a path'),
    (nested_split_without_merge, 'split inside a path'),
    (same_slot_concurrent, 'two paths into one Merge input'),
    (same_slot_either_or, 'two paths into one Merge input'),
    (wait_gate, 'Wait Until gates'),
    (two_merges_on_either_or_routes, 'one Merge'),
    (split_after_merge, 'one split'),
    (path_ends_before_merge, 'every path must reach the Merge'),
    (result_goes_straight_to_end, 'must feed a later step'),
], ids=lambda v: getattr(v, '__name__', None))
def test_beyond_stage_one_is_refused_plainly_from_the_shared_analysis(build, words):
    problems = stage_one_problems(flow_of(build()))
    assert any(words in p for p in problems), problems
    assert all('outside this admission stage' in p and 'engine' not in p and 'path_' not in p.split(':')[0] for p in problems)


def test_merge_with_no_split_and_second_merge_stop_at_the_shared_check():
    from tools.draft_trials.family_two_controls import controls
    examples = {c['id']: c['spec'] for c in controls()}
    for name, code in [('standalone_merge', 'merge_outside_split'), ('second_merge_same_group', 'flow_needs_review'),
                       ('control_back_edge', 'flow_loop')]:
        report = check_workflow_spec(F, examples[name])
        assert not report['ok'] and code in {d['code'] for d in report['diagnostics']}


@pytest.mark.parametrize('number', [1, 2])
def test_admitted_shapes_have_no_problems_and_analysis_says_stage_one(number):
    flow = flow_of(good_draft(number, '/tmp/fixtures'))
    assert flow['admission_stage'] == 1 and stage_one_problems(flow) == []


def test_independent_parallel_paths_without_merge_stay_allowed():
    # Set 2 case 8's shape: no join requested, nothing to refuse.
    assert stage_one_problems(flow_of(any_case_draft())) == []


def any_case_draft():
    from tools.draft_trials.cases import good_draft as old
    return old(8, '/tmp/fixtures', 2)


# --- admission boundary ---------------------------------------------------------------

def test_exact_membership_and_withheld_types():
    assert ADMITTED - HELPER_PALETTE == {'merge_node'}
    for kind in ('wait_until_node', 'branch_end_node', 'set_variable_node', 'get_variable_node'):
        assert kind not in ADMITTED
    assert ROLE_TYPES['join'] == [('merge_node',)] and 'wait' not in ROLE_TYPES
    assert 'merge_node' not in implemented_not_admitted(F, ADMITTED)
    assert 'merge_node' in implemented_not_admitted(F, HELPER_PALETTE)
    schema = SPEC['nodes']['analysis']['config']['reply_schema']
    assert schema['properties']['selection']['properties']['candidates']['items']['properties']['type_id']['enum'] == sorted(ADMITTED)
    assert SPEC['nodes']['selected_contracts']['config']['admitted_type_ids'] == sorted(ADMITTED)


def test_admission_baseline_pins_stage_one_and_the_frozen_scopes():
    assert BASELINE['admission'] == ADMISSION_VERSIONS and ADMISSION_VERSIONS['draft_stage'] == 1
    assert len(set(ADMISSION_VERSIONS.values())) == 2  # Every version moved to 2 together.
    assert BASELINE['type_ids'] == sorted(ADMITTED) and BASELINE['role_ids'] == sorted(ROLE_TYPES)
    assert BASELINE['frozen_helper_type_ids'] == sorted(HELPER_PALETTE)
    assert BASELINE['case_ids'] == case_ids() == [1, 2]
    assert BASELINE['pair_ids'] == [p['id'] for p in calibration_pairs()] == ['collect_vs_pick_one', 'join_vs_shared_end']
    assert canonical_sha(dict(cases=[good_draft(n) for n in case_ids()], variants=[fixture_variants(n) for n in case_ids()],
                              pairs=calibration_pairs())) == BASELINE['stage_1_sha256']


@pytest.mark.parametrize('name, scope', [('original', ORIGINAL_PALETTE), ('helpers', HELPER_PALETTE)])
def test_frozen_scopes_get_the_exact_designer_they_had_before_stage_one(name, scope):
    configured = configure(deepcopy(SPEC), scope)
    assert canonical_sha(configured) == BASELINE['frozen_designer_sha256'][name]
    assert 'merge_node' not in json.dumps({k: v for k, v in configured['nodes'].items() if k.endswith('_question')})


def test_suites_use_their_own_scope_and_set_three_scoring_refuses_merge(tmp_path):
    assert SUITE_SCOPE == {1: ORIGINAL_PALETTE, 2: ORIGINAL_PALETTE, 3: HELPER_PALETTE, 4: ADMITTED}
    from tools.draft_trials.cases import good_draft as old
    spec = old(1, str(tmp_path), 3)
    spec['nodes']['join'] = dict(type='merge_node', config={})
    result = check_rules(spec, any_case(1, tmp_path, 3))
    assert result['result'] == 'fail' and 'outside admitted palette' in str(result)


# --- what the drafter is told ------------------------------------------------------------

def test_drafter_gets_one_worked_slot_example_and_no_shared_end_join():
    draft = SPEC['nodes']['draft_question']['config']['template']
    assert JOIN_DRAFT in draft
    rendered = draft.format_map(dict(draft_request='', clarification_answer='', frozen_requirements=''))
    assert '{input[path_a]}' in rendered and '{input[path_b]}' in rendered
    for text in (JOIN_DRAFT, JOIN_ANALYSIS):
        assert 'shared End only finishes' in text and 'never waits' in text
        assert not any(word in text for word in ('Beacon', 'wait_until', 'Set Variable', 'Get Variable'))
    for handle in ('analysis_question', 'resolve_question'):
        assert JOIN_ANALYSIS in SPEC['nodes'][handle]['config']['template']
    assert 'merge_node' not in SPEC['nodes']['judge_question']['config']['template']


@pytest.mark.asyncio
@pytest.mark.parametrize('number', [1, 2])
async def test_selected_snapshot_includes_merge_within_caps(number, tmp_path):
    case = case_record(number, tmp_path)
    cfg = F.create_config_template('node_catalogue_node')
    text = await snapshot(F, runner.requirements(case), case['request'], cfg)
    receipt = read_snapshot(text)
    assert 'merge_node' in receipt['selected_type_ids'] and receipt['draft_stage'] == 1
    assert receipt['admission'] == ADMISSION_VERSIONS
    assert len(text) <= CONTRACT_LIMIT * .8
    for key in ('draft_question', 'judge_question', 'retry_question'):
        assert len(text) + len(SPEC['nodes'][key]['config']['template']) + 8000 + 8000*2 + 4000 <= CONTEXT_LIMIT * .8


@pytest.mark.asyncio
async def test_full_admitted_catalogue_fits_its_caps():
    cfg = F.create_config_template('node_catalogue_node')
    cfg.update(scope='Exact IDs', type_ids=sorted(ADMITTED), max_chars=CONTRACT_LIMIT)
    compact = await node_catalogue.build(F, cfg)
    brief = await node_catalogue.build(F, dict(cfg, detail='Brief'))
    assert 'node merge_node |' in compact and len(compact) < CONTRACT_LIMIT and len(brief) + len(compact) < CONTEXT_LIMIT
    assert 'wait_until_node (not admitted)' in compact


@pytest.mark.asyncio
async def test_snapshots_from_another_admission_version_are_stale():
    text = await snapshot(F, runner.requirements(case_record(1, '/tmp/f')), 'Read', F.create_config_template('node_catalogue_node'))
    header, contracts = text.split('\n', 1)
    receipt = json.loads(header.split(': ', 1)[1])
    receipt['admission'] = dict(receipt['admission'], cache=1)
    with pytest.raises(NodeError, match='stale'):
        read_snapshot('Selection snapshot: '+json.dumps(receipt)+'\n'+contracts)


# --- the real designer graph, mocked transport only -----------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize('number, fixtures', [(1, 3), (2, 6)])
async def test_set_four_runs_through_the_normal_pipeline_and_real_engine(number, fixtures, tmp_path):
    report = await runner.run_case(number, tmp_path/'trial', tmp_path/'library', case_set=4)
    assert report['result'] == 'pass', report
    assert report['calls'] == dict(attempted=3, succeeded=3, remaining=0)
    assert 'merge_node' in report['selection']['selected_type_ids']
    assert len(report['behavior']['fixtures']) == fixtures
    assert report['case_rules']['admitted'] is True
    spec = json.loads((tmp_path/'trial/cases'/str(number)/'trial-designer.json').read_text())
    assert JOIN_DRAFT in spec['nodes']['draft_question']['config']['template']


@pytest.mark.asyncio
async def test_a_refused_shape_gets_the_one_redraft_with_the_plain_message(tmp_path):
    case = case_record(1, tmp_path/'trial/cases/1/fixtures')
    analysis, draft = runner.requirements(case), good_draft(1, case['root'])
    bad = path_ends_before_merge()
    bad['nodes']['a']['config']['file_path'] = draft['nodes']['a']['config']['file_path']
    bad['nodes']['b']['config']['file_path'] = draft['nodes']['b']['config']['file_path']
    report = await runner.run_case(1, tmp_path/'trial', tmp_path/'library', case_set=4,
                                   replies=[analysis, bad, draft, runner.meaning()])
    assert report['result'] == 'pass', report
    assert report['draft_retry'] == dict(requested=True, attempted=1, succeeded=1, check_passed=True)
    error = str(json.loads((tmp_path/'trial/cases/1/evidence.json').read_text())['first_check_error'])
    assert 'outside this admission stage' in error and 'every path must reach the Merge' in error
    repeat = await runner.run_case(1, tmp_path/'second', tmp_path/'library', case_set=4,
                                   replies=[analysis, bad, bad])
    assert repeat['result'] == 'fail' and not list((tmp_path/'second/cases/1/drafts').iterdir())


@pytest.mark.asyncio
async def test_frozen_boundary_snapshot_skips_the_stage_gate():
    # Sets 1-3 keep exactly the checks they were measured with.
    spec = nested_split_without_merge()
    cfg = F.create_config_template('node_catalogue_node')
    cfg['admitted_type_ids'] = sorted(ORIGINAL_PALETTE)
    analysis = runner.requirements(dict(id=1, case_set=2, request='r', root='/tmp/f', expected_status='ready'))
    analysis['selection'] = dict(roles=[dict(role='parallel_paths', requirement_ids=['r1'], reason='split')], candidates=[
        dict(type_id=t, role='parallel_paths', requirement_ids=['r1'], reason='x') for t in
        ('branch_node', 'file_reader_node', 'text_transform_node', 'text_output_node')])
    text = await snapshot(F, analysis, 'r', cfg)
    assert read_snapshot(text)['draft_stage'] is None
    check_draft(F, spec, text, flow=flow_of(spec))
    live = await snapshot(F, analysis, 'r', F.create_config_template('node_catalogue_node'))
    with pytest.raises(NodeError, match='split inside a path'):
        check_draft(F, spec, live, flow=flow_of(spec))


# --- normal run membership and target checks ---------------------------------------------------

def test_only_stage_one_requests_and_pairs_join_the_normal_run():
    from tools.draft_trials.dependencies import CASE_COUNTS, sets_from_text
    assert sets_from_text('all') == [1, 2, 3, 4] and CASE_COUNTS[4] == 2
    assert {p['number'] for p in calibration_pairs()} == {1, 6}
    assert case_record(1, '/tmp/f')['admitted'] and not case_record(3, '/tmp/f', stage=2)['admitted']


@pytest.mark.parametrize('body, right', [
    ('A: Alpha report\nB: Beta report', True),
    ('[A] Alpha report\n[B] Beta report', True),
    ('A:\nAlpha report\n\nB:\nBeta report', True),
    ('B: Beta report\nA: Alpha report', False),
    ('A: Alpha report', False),
    ('A: Alpha reports\nB: Beta report', False),
])
def test_target_runs_accept_the_same_label_spellings_as_the_rules(body, right):
    assert shown_fields_match([body], fixture_variants(1)[0]) is right


def test_target_runs_refuse_a_second_show_and_keep_empty_text():
    variant = fixture_variants(1)[0]
    assert not shown_fields_match(['A: Alpha report', 'B: Beta report'], variant)
    assert shown_fields_match(['A: Alpha report\nB: '], fixture_variants(1)[2])


def test_draft_guidance_says_how_to_get_more_than_two_paths():
    # Run 000048: the drafter read Branch's default ports as a fixed limit of two.
    draft = SPEC['nodes']['draft_question']['config']['template']
    assert 'set branch_count on the branch_node' in JOIN_DRAFT and JOIN_DRAFT in draft
    assert 'path_a to path_e unless input_slots' in JOIN_DRAFT


def test_reviewer_sees_flow_in_words_and_nothing_extra_without_a_merge():
    # Runs 000048/49: the raw analysis nearly doubled the judge's question.
    from backend.meta_workflow import review_report
    factory = NodeFactory()
    with_merge = dict(ok=True, flow_analysis=check_workflow_spec(factory, good_draft(1))['flow_analysis'])
    reviewed = review_report(with_merge)
    assert set(reviewed['flow_analysis']) == {'merges', 'findings'}
    assert reviewed['flow_analysis']['merges']['join']['summary'].startswith('Merge')
    assert 'provenance' not in json.dumps(reviewed) and 'flow_analysis' in with_merge
    no_merge = dict(flow_analysis=dict(merges={}, findings=[]), ok=True)
    assert review_report(no_merge) == dict(ok=True)
    assert review_report(dict(ok=True)) == dict(ok=True)

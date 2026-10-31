"""Family 2 Stage 2: sub-path joins, Wait Until gates and same-slot rejoins in drafts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from backend.authoring import check_workflow_spec
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from backend.palette_selection import (ADMISSION_VERSIONS, ADMITTED, HELPER_PALETTE, ORIGINAL_ROLE_IDS, ROLE_TYPES,
    STAGE_TWO_ROLES, check_draft, draft_stage_problems, positive_matches, read_snapshot, role_ids, snapshot)
from tools.draft_trials import runner
from tools.draft_trials.admission import JOIN_ANALYSIS, JOIN_DRAFT, SUITE_SCOPE, configure
from tools.draft_trials.case_set_four import calibration_pairs, case_ids, case_record, fixture_variants, good_draft
from tools.draft_trials.dependencies import CASE_COUNTS
from tools.draft_trials.family_two_engine import run_fixture
from tools.draft_trials.reply_schemas import analysis_schema

F = NodeFactory()
SPEC = json.loads(runner.SPEC.read_text())
BASELINE = json.loads((Path(runner.__file__).parent/'fixtures/admission_baseline.json').read_text())['stage_2']
ROOT = '/tmp/fixtures'


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def flow_of(spec):
    report = check_workflow_spec(F, spec)
    assert report['ok'], report['diagnostics']
    return report['flow_analysis']


def problems_of(spec):
    return draft_stage_problems(flow_of(spec), spec)


def diagnostics_of(spec):
    report = check_workflow_spec(F, spec)
    return report['ok'], {d['code'] for d in report['diagnostics']}


def rewire(spec, source, target):
    spec['connections'] = [e for e in spec['connections'] if e['from'] != source]
    spec['connections'].append({'from': source, 'to': target})
    return spec


# --- the three new shapes pass, each with the right facts ---------------------------------

@pytest.mark.parametrize('number', [3, 4, 5])
def test_each_new_shape_passes_the_draft_stage_check(number):
    flow = flow_of(good_draft(number, ROOT))
    assert flow['admission_stage'] == 2
    assert problems_of(good_draft(number, ROOT)) == []


def test_concurrent_paths_in_one_input_are_allowed_and_declared_a_list():
    spec = good_draft(3, ROOT, same_slot=True)
    assert problems_of(spec) == []
    assert flow_of(spec)['merges']['join']['slots']['path_b']['cardinality'] == 'many'


def test_either_or_routes_in_one_input_are_one_value():
    assert flow_of(good_draft(5, ROOT))['merges']['join']['slots']['path_b']['cardinality'] == 'one'


def test_a_path_ending_on_its_own_stays_allowed_and_the_summary_says_so():
    # Decision 4 and the set 4 proposal: an independent side path may End in Stage 2.
    spec = good_draft(1, ROOT)
    spec['nodes']['split']['config']['branch_count'] = 3
    spec['connections'].append({'from': 'split.path_c', 'to': 'end.input'})
    assert problems_of(spec) == []
    assert 'supplies no Merge value' in flow_of(spec)['merges']['join']['summary']


def test_a_choice_after_the_merge_is_a_later_step_not_a_route_leaving_it():
    # The group has closed by then, so no required path can escape.
    spec = good_draft(1, ROOT)
    spec['nodes']['choose'] = dict(type='conditional_node', config=dict(condition_type='equals', right_value='yes', left_value_source='input'))
    rewire(spec, 'join.default', 'choose.input')
    spec['connections'] += [{'from': 'choose.true', 'to': 'show.input'}, {'from': 'choose.false', 'to': 'end.input'}]
    assert problems_of(spec) == []


def separate_joins_on_either_or_routes():
    # Two groups, one Merge each: exclusive routes, so only one ever runs.
    def read(name):
        return dict(type='file_reader_node', config=dict(file_path=ROOT+'/'+name, input_source='Configured'))
    spec = dict(format='aotn-workflow/1', name='Two', nodes={
        'start': dict(type='start_node', config=dict(greeting='yes')),
        'end': dict(type='end_node', config=dict(record_line=False)),
        'choose': dict(type='conditional_node', config=dict(condition_type='equals', right_value='yes', left_value_source='input'))},
        connections=[{'from': 'start.default', 'to': 'choose.input'}])
    for route in ('true', 'false'):
        split, one, two, join, show = (route+'_'+h for h in ('split', 'one', 'two', 'join', 'show'))
        spec['nodes'].update({split: dict(type='branch_node', config=dict(branch_count=2)), join: dict(type='merge_node', config={}),
                              one: read('report-a.txt'), two: read('report-b.txt'),
                              show: dict(type='text_output_node', config=dict(label='', template='A: {input[path_a]}\nB: {input[path_b]}'))})
        spec['connections'] += [{'from': 'choose.'+route, 'to': split+'.input'}, {'from': split+'.path_a', 'to': one+'.input'},
                                {'from': split+'.path_b', 'to': two+'.input'}, {'from': one+'.default', 'to': join+'.path_a'},
                                {'from': two+'.default', 'to': join+'.path_b'}, {'from': join+'.default', 'to': show+'.input'},
                                {'from': show+'.default', 'to': 'end.input'}]
    return spec


@pytest.mark.parametrize('order', ['forward', 'reverse'])
async def test_one_merge_per_group_allows_separate_groups_and_the_engine_runs_them(order, tmp_path):
    assert problems_of(separate_joins_on_either_or_routes()) == []
    case = case_record(1, tmp_path)
    spec = json.loads(json.dumps(separate_joins_on_either_or_routes()).replace(ROOT, case['root']))
    actual = await run_fixture(spec, case, fixture_variants(1)[0], order=order)
    assert actual['state'] == 'finished' and actual['outputs'] == fixture_variants(1)[0]['outputs']


# --- what stays refused, in plain words --------------------------------------------------

def second_merge_in_one_group():
    spec = good_draft(3, ROOT)
    spec['nodes']['inner_join'] = dict(type='merge_node', config={})
    rewire(spec, 'upper.default', 'inner_join.path_a')
    rewire(spec, 'lower.default', 'inner_join.path_b')
    spec['connections'].append({'from': 'inner_join.default', 'to': 'join.path_b'})
    return spec


def merge_only_through_its_error_output():
    spec = good_draft(1, ROOT)
    spec['connections'] = [e for e in spec['connections'] if e['from'] != 'join.default']
    spec['connections'].append({'from': 'join.error', 'to': 'show.input'})
    return spec


def merge_with_an_error_route_too():
    spec = good_draft(1, ROOT)
    spec['nodes']['side'] = dict(type='text_output_node', config=dict(label='', template='Failed'))
    spec['connections'] += [{'from': 'join.error', 'to': 'side.input'}, {'from': 'side.default', 'to': 'end.input'}]
    return spec


def nothing_after_the_merge():
    spec = good_draft(1, ROOT)
    del spec['nodes']['show']
    spec['connections'] = [e for e in spec['connections'] if 'show.' not in e['from']+e['to']]
    spec['connections'].append({'from': 'join.default', 'to': 'end.input'})
    return spec


def split_with_no_join_beside_a_merge():
    spec = good_draft(1, ROOT)
    spec['nodes']['later'] = dict(type='branch_node', config=dict(branch_count=2))
    rewire(spec, 'join.default', 'later.input')
    spec['connections'] += [{'from': 'later.path_a', 'to': 'show.input'}, {'from': 'later.path_b', 'to': 'end.input'}]
    return spec


def wait_on_the_split():
    spec = good_draft(4, ROOT)
    spec['nodes']['wait']['config']['target_node_ids'] = ['split']
    return spec


def wait_on_nothing():
    spec = good_draft(4, ROOT)
    spec['nodes']['wait']['config']['target_node_ids'] = []
    return spec


@pytest.mark.parametrize('build, words', [
    (merge_only_through_its_error_output, 'a route leaving the Merge'),
    (merge_only_through_its_error_output, 'must feed a later step'),
    (merge_with_an_error_route_too, 'a route leaving the Merge'),
    (nothing_after_the_merge, 'must feed a later step'),
    (split_with_no_join_beside_a_merge, 'beside a Merge'),
    (wait_on_the_split, 'not a split'),
    (wait_on_nothing, 'must name the step'),
], ids=lambda v: getattr(v, '__name__', None))
def test_the_stage_check_refuses_in_plain_words(build, words):
    problems = problems_of(build())
    assert any(words in p for p in problems), problems
    assert all(p.startswith('This is outside this admission stage: ') and 'engine' not in p for p in problems)


@pytest.mark.parametrize('name, code', [('standalone_merge', 'merge_outside_split'), ('second_merge_same_group', 'flow_needs_review'),
                                        ('control_back_edge', 'flow_loop')])
def test_merge_with_no_split_repeated_join_and_loops_stop_at_the_shared_check(name, code):
    from tools.draft_trials.family_two_controls import controls
    spec = next(c['spec'] for c in controls() if c['id'] == name)
    ok, codes = diagnostics_of(spec)
    assert not ok and code in codes


def test_second_merge_in_one_group_stops_at_the_shared_check():
    ok, codes = diagnostics_of(second_merge_in_one_group())
    assert not ok and codes & {'flow_needs_review', 'repeated_join_unsupported'}


def test_a_route_leaving_a_required_join_stops_at_the_shared_check():
    ok, codes = diagnostics_of(rewire(good_draft(5, ROOT), 'no.default', 'end.input'))
    assert not ok and 'merge_required_path_escape' in codes


def test_the_stage_check_itself_names_merge_with_no_split_loops_and_beacons():
    flow = flow_of(good_draft(1, ROOT))
    spec = good_draft(1, ROOT)
    assert any('no split' in p for p in draft_stage_problems(dict(flow, merges=dict(join=dict(flow['merges']['join'], group_roots=[]))), spec))
    assert any('loops are not supported' in p for p in draft_stage_problems(dict(flow, back_edges=[['show', 'split']]), spec))
    beacon = deepcopy(flow)
    beacon['profiles']['a']['kind'] = 'beacon'
    assert any('Merge Beacons' in p for p in draft_stage_problems(beacon, spec))
    two = deepcopy(flow)
    two['merges']['again'] = deepcopy(two['merges']['join'])
    spec['connections'].append({'from': 'again.default', 'to': 'show.input'})
    assert any('only one Merge' in p for p in draft_stage_problems(two, spec))


# --- the real draft check, end to end ----------------------------------------------------

@pytest.mark.parametrize('number', [3, 4, 5])
async def test_real_draft_check_passes_a_good_draft_and_refuses_an_error_wire(number, tmp_path):
    case = case_record(number, tmp_path)
    text = await snapshot(F, runner.requirements(case), case['request'], F.create_config_template('node_catalogue_node'))
    assert read_snapshot(text)['draft_stage'] == 2
    good = good_draft(number, ROOT)
    check_draft(F, good, text, flow=flow_of(good))
    bad = rewire(deepcopy(good), 'join.default', 'end.input')
    with pytest.raises(NodeError, match='must feed a later step'):
        check_draft(F, bad, text, flow=flow_of(bad))


async def test_wait_for_step_role_adds_wait_until_and_needs_no_candidate(tmp_path):
    case = case_record(4, tmp_path)
    analysis = runner.requirements(case)
    assert 'wait_for_step' in [r['role'] for r in analysis['selection']['roles']]
    analysis['selection']['candidates'] = [c for c in analysis['selection']['candidates'] if c['type_id'] != 'wait_until_node']
    receipt = read_snapshot(await snapshot(F, analysis, case['request'], F.create_config_template('node_catalogue_node')))
    assert 'wait_until_node' in receipt['selected_type_ids']


def test_wait_words_find_wait_until_and_touch_no_frozen_request():
    from backend.palette_selection import SYNONYMS
    from tools.draft_trials import case_set_three, case_set_two, cases
    assert 'wait_until_node' in positive_matches(F, 'wait until that read has finished')
    frozen = ' '.join(cases.REQUESTS + case_set_two.REQUESTS + case_set_three.REQUESTS).casefold()
    assert not [word for word in SYNONYMS['wait_for_step'] if word in frozen]


async def test_scorer_refuses_an_error_wire_as_the_only_way_on(tmp_path):
    from tools.draft_trials.rules import check_rules
    case = case_record(1, tmp_path)
    spec = json.loads(json.dumps(merge_only_through_its_error_output()).replace(ROOT, case['root']))
    result = check_rules(spec, case)
    assert result['result'] == 'fail' and 'must feed a later step' in str(result)


# --- admission boundary and frozen sets ---------------------------------------------------

def test_versions_moved_together_and_baseline_pins_stage_two():
    assert ADMISSION_VERSIONS == dict(admission=3, role_schema=3, contracts=3, cache=3, draft_stage=2)
    assert BASELINE['admission'] == ADMISSION_VERSIONS
    assert BASELINE['type_ids'] == sorted(ADMITTED) and BASELINE['role_ids'] == sorted(ROLE_TYPES)
    assert BASELINE['withheld_type_ids'] == ['branch_end_node', 'get_variable_node', 'set_variable_node']
    assert BASELINE['case_ids'] == case_ids() == [1, 2, 3, 4, 5] and CASE_COUNTS[4] == 5
    assert BASELINE['pair_ids'] == [p['id'] for p in calibration_pairs()] and len(BASELINE['pair_ids']) == 6
    assert canonical_sha(dict(cases=[good_draft(n) for n in case_ids()], variants=[fixture_variants(n) for n in case_ids()],
                              pairs=calibration_pairs())) == BASELINE['stage_2_sha256']
    assert all(p['admitted'] for p in calibration_pairs())


@pytest.mark.parametrize('suite', [1, 2, 3])
def test_frozen_sets_keep_their_designer_and_see_nothing_new(suite):
    name = 'helpers' if suite == 3 else 'original'
    configured = configure(deepcopy(SPEC), SUITE_SCOPE[suite])
    assert canonical_sha(configured) == BASELINE['frozen_designer_sha256'][name]
    text = json.dumps(configured)
    assert 'wait_for_step' not in text and 'wait_until_node' not in text and 'merge_node' not in json.dumps(
        {k: v for k, v in configured['nodes'].items() if k.endswith('_question')})


def test_frozen_boundaries_keep_their_role_lists():
    assert role_ids(HELPER_PALETTE) == frozenset(ROLE_TYPES) - STAGE_TWO_ROLES
    assert 'wait_for_step' in role_ids(ADMITTED) and not STAGE_TWO_ROLES & ORIGINAL_ROLE_IDS
    roles = analysis_schema(HELPER_PALETTE)['properties']['selection']['properties']['roles']
    assert 'wait_for_step' not in roles['items']['properties']['role']['enum']


@pytest.mark.parametrize('scope', [SUITE_SCOPE[1], SUITE_SCOPE[3]], ids=['original', 'helpers'])
async def test_frozen_contract_text_does_not_mention_wait_as_admitted(scope):
    from backend import node_catalogue
    config = F.create_config_template('node_catalogue_node')
    config.update(scope='Exact IDs', type_ids=sorted(scope), max_chars=50000)
    assert 'wait_until_node' not in await node_catalogue.build(F, config)


# --- what the drafter is told -------------------------------------------------------------

def test_guidance_carries_the_facts_the_new_shapes_need():
    draft = SPEC['nodes']['draft_question']['config']['template']
    assert JOIN_DRAFT in draft
    for handle in ('analysis_question', 'resolve_question'):
        assert JOIN_ANALYSIS in SPEC['nodes'][handle]['config']['template']
        assert 'wait_for_step' in SPEC['nodes'][handle]['config']['template']
    rendered = draft.format_map(dict(draft_request='', clarification_answer='', frozen_requirements=''))
    for fact in ('its children join the same Merge', 'yes.default and no.default both to join.path_b', '{input[path_b][0]}',
                 'wait_until_node first on the waiting path', 'never the branch_node', '"label": ""', 'only one Merge', 'No loops'):
        assert fact in rendered, fact
    for text in (JOIN_DRAFT, JOIN_ANALYSIS):
        assert not any(word in text for word in ('Beacon', 'Set Variable', 'Get Variable'))
    assert 'wait_until' not in SPEC['nodes']['judge_question']['config']['template']


# --- the real designer graph, mocked transport only -----------------------------------------

@pytest.mark.parametrize('number, fixtures', [(3, 2), (4, 2), (5, 4)])
async def test_new_requests_run_through_the_normal_pipeline_and_real_engine(number, fixtures, tmp_path):
    report = await runner.run_case(number, tmp_path/'trial', tmp_path/'library', case_set=4)
    assert report['result'] == 'pass', report
    assert report['calls'] == dict(attempted=3, succeeded=3, remaining=0)
    assert len(report['behavior']['fixtures']) == fixtures
    assert report['case_rules']['admitted'] is True
    if number == 4:
        assert 'wait_until_node' in report['selection']['selected_type_ids']


async def test_a_refused_error_wire_gets_the_one_redraft_with_the_plain_message(tmp_path):
    case = case_record(1, tmp_path/'trial/cases/1/fixtures')
    analysis, draft = runner.requirements(case), good_draft(1, case['root'])
    bad = json.loads(json.dumps(merge_only_through_its_error_output()).replace(ROOT, case['root']))
    report = await runner.run_case(1, tmp_path/'trial', tmp_path/'library', case_set=4,
                                   replies=[analysis, bad, draft, runner.meaning()])
    assert report['result'] == 'pass', report
    assert report['draft_retry'] == dict(requested=True, attempted=1, succeeded=1, check_passed=True)
    error = str(json.loads((tmp_path/'trial/cases/1/evidence.json').read_text())['first_check_error'])
    assert 'a route leaving the Merge' in error and 'must feed a later step' in error

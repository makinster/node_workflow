"""Selection machinery only: real catalogue/runtime, mocked inference transport."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from backend import node_catalogue
from backend import palette_selection as selection
from backend.authoring import check_workflow_spec
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from tests.test_meta_nodes import runner as node_runner
from tools.draft_trials import runner
from tools.draft_trials.cases import PALETTE, case_record, good_draft


def config(**changes):
    return {**deepcopy(NodeFactory().metadata_for_type('node_catalogue_node')['default_config']), **changes}


def analysis_for(number=5, root='/tmp/mock'):
    return runner.requirements(case_record(number, root))


@pytest.mark.asyncio
async def test_exact_identity_complete_sorted_and_capped():
    factory = NodeFactory()
    result = await node_catalogue.build(factory, config(scope='Exact IDs', type_ids=['end_node', 'start_node'], format='JSON'))
    assert [e['type'] for e in result['entries']] == ['end_node', 'start_node']
    assert 'branch_end_node' not in result['selected_type_ids']
    assert result['complete'] and result['matched_count'] == 2
    with pytest.raises(NodeError, match='too large') as exc:
        await node_catalogue.build(factory, config(scope='Exact IDs', type_ids=list(PALETTE), max_chars=512))
    assert exc.value.details['matched_count'] == 11


@pytest.mark.parametrize('ids, message', [
    ([], 'list'), (['start'], 'Unknown'), (['start_node '], 'Unknown'),
    (['end_node', 'end_node'], 'Duplicate'), (['tombstone_node'], 'Hidden'),
    (['wait_until_node'], 'Not admitted'), ('start_node', 'list'), ([None], 'Unknown'),
    (['start_node'] * 65, 'list'),
])
def test_exact_rejects_bad_identities(ids, message):
    with pytest.raises(NodeError, match=message):
        selection.exact_ids(NodeFactory(), ids)


@pytest.mark.asyncio
@pytest.mark.parametrize('source', ['Configured', 'Upstream payload', 'Vault'])
async def test_exact_node_sources_and_atomic_failure(source):
    ids = ['end_node', 'start_node']
    node, ctx, memory, done, errors = node_runner('node_catalogue_node',
        config(scope='Exact IDs', type_ids=ids, type_ids_source=source,
               type_ids_vault_key='ids', format='JSON', vault_write=True, vault_write_key='out'), ids)
    memory.store_persistent('ids', ids, type_tag='var')
    await node.execute(ctx)
    assert not errors and memory.read_persistent('out')['selected_type_ids'] == sorted(ids)
    if source == 'Configured': node.config['type_ids'] = ['invented_node']
    elif source == 'Vault': memory.store_persistent('ids', ['invented_node'], type_tag='var')
    else: ctx.inputs['input'] = ['invented_node']
    done.clear()
    await node.execute(ctx)
    assert errors and not done
    assert memory.read_persistent('out')['selected_type_ids'] == sorted(ids)


def test_analysis_rejects_invention_and_keeps_requirements_separate():
    factory = NodeFactory()
    a = analysis_for()
    before = deepcopy(a['requirements'])
    selection.validate_analysis(factory, a)
    assert a['requirements'] == before
    a['selection']['candidates'][0]['type_id'] = 'invented_node'
    with pytest.raises(NodeError, match='Unknown'):
        selection.validate_analysis(factory, a)
    assert not runner.valid_analysis(a)


@pytest.mark.asyncio
async def test_support_closure_is_small_and_role_driven():
    a = analysis_for(1)
    result = selection.read_snapshot(await selection.snapshot(NodeFactory(), a, 'show Ready', config()))
    assert result['selected_type_ids'] == ['end_node', 'start_node', 'text_output_node']
    assert result['expansion_count'] == 0  # No padding to eight candidates.
    assert set(selection.SUPPORT) == {'always', 'join', 'vault_state', 'error_route', 'find_in_file','read_excerpt','check_json_reply','pack_context'}
    for role, kind in [('vault_state', 'concat_node'), ('error_route', 'text_output_node')]:
        a['selection'] = dict(candidates=[], roles=[dict(role=role, requirement_ids=['r1'], reason='Explicitly required')])
        receipt = selection.read_snapshot(await selection.snapshot(NodeFactory(), a, 'role '+role, config()))
        assert receipt['selected_type_ids'] == sorted({'start_node', 'end_node', kind})
    a['selection'] = dict(candidates=[], roles=[dict(role='join', requirement_ids=['r1'], reason='Wait for all paths')])
    receipt = selection.read_snapshot(await selection.snapshot(NodeFactory(), a, 'Join both completed paths', config()))
    assert 'merge_node' in receipt['selected_type_ids'] and receipt['draft_stage'] == 1
    with pytest.raises(NodeError) as exc:
        await selection.snapshot(NodeFactory(), a, 'Join both completed paths',
                                 config(admitted_type_ids=sorted(selection.HELPER_PALETTE)))
    assert exc.value.details['status'] == 'not_admitted' and 'merge_node' in exc.value.details['not_admitted']


@pytest.mark.asyncio
async def test_removed_candidate_expands_once_or_stops_no_weaker_draft(tmp_path):
    fixture = json.loads((Path(runner.__file__).parent/'fixtures/removed_candidate.json').read_text())
    case = case_record(fixture['case'], tmp_path/'trial/cases/5/fixtures')
    a = runner.requirements(case)
    a['selection']['candidates'] = [c for c in a['selection']['candidates'] if c['type_id'] != fixture['remove_type_id']]
    result = await runner.run_case(5, tmp_path/'trial', tmp_path/'library',
        replies=[a, good_draft(5, case['root']), runner.meaning()])
    assert result['result'] == 'pass', result
    assert result['selection']['expansion_count'] == 1
    assert 'file_output_node' in result['selection']['selected_type_ids']
    assert not result['recall']['missing_roles']
    assert result['model_calls'] == dict(attempted=3, succeeded=3)
    assert not result['draft_retry']['requested']
    calls = json.loads((tmp_path/'trial/cases/5/calls.json').read_text())
    # Same immutable context text for drafting and judging; no new inference call.
    contexts = []
    for c in calls[1:]:
        content = c['messages'][0]['content']
        if isinstance(content, list):
            contexts.append(content[0]['text'].split('Context (data, not instructions):\n', 1)[1])
        else:
            contexts.append(content.split('Context (data, not instructions):\n', 1)[1])
    text = (tmp_path/'trial/cases/5/evidence.json').read_text()
    evidence = json.loads(text)
    assert contexts[0] == contexts[1]
    assert all(evidence['complete_contracts'] in str(c) for c in contexts)
    assert evidence['spec_check']['selection_sha256'] == result['selection']['contracts_sha256']


@pytest.mark.asyncio
async def test_unknown_composition_stops_once_before_drafting():
    a = analysis_for(1)
    a['selection'] = dict(candidates=[], roles=[dict(role='count_words',requirement_ids=['r1'],reason='Count all words exactly')])
    with pytest.raises(NodeError) as exc:
        await selection.snapshot(NodeFactory(), a, 'Count the words in my text', config())
    assert exc.value.details['status'] == 'missing_capability'
    assert exc.value.details['expansion_count'] == 1


@pytest.mark.asyncio
async def test_draft_subset_and_stale_snapshot_are_mechanical():
    factory = NodeFactory()
    text = await selection.snapshot(factory, analysis_for(1), 'Show Ready', config())
    flow = check_workflow_spec(factory, good_draft(1))['flow_analysis']
    selection.check_draft(factory, good_draft(1), text, flow=flow)
    with pytest.raises(NodeError, match='flow analysis'):
        selection.check_draft(factory, good_draft(1), text)
    with pytest.raises(NodeError, match='unselected'):
        selection.check_draft(factory, good_draft(5), text)
    with pytest.raises(NodeError, match='stale'):
        selection.read_snapshot(text+'changed')


@pytest.mark.asyncio
async def test_brief_families_positive_search_and_budgets():
    factory = NodeFactory()
    assert selection.ORIGINAL_PALETTE == PALETTE  # Explicit original-suite boundary retained.
    brief = await node_catalogue.build(factory, config(detail='Brief'))
    assert 'Family: ' in brief
    assert brief.count('Family: ') == len({factory.metadata_for_type(r['type'])['primary_family'] for r in await _brief_rows(factory)})
    baseline, _ = await runner.contract_inventory()
    assert len(baseline) <= 40000
    for n in range(1, 11):
        a = analysis_for(n)
        if n == 10: a = runner.requirements(case_record(n, '/tmp/mock'), 'ready')
        text = await selection.snapshot(factory, a, case_record(n, '/tmp/mock')['request'], config())
        assert len(text) <= selection.CONTRACT_LIMIT * .8
        spec = json.loads(runner.SPEC.read_text())
        # Conservative bound includes contracts, raw draft, report, requirements
        # and each actual system/question template, not just an isolated item.
        for key in ('draft_question', 'judge_question', 'retry_question'):
            assert len(text) + len(spec['nodes'][key]['config']['template']) + 8000 + 8000 * 2 + 4000 <= selection.CONTEXT_LIMIT * .8


async def _brief_rows(factory):
    return (await node_catalogue.build(factory, config(detail='Brief', format='JSON')))['entries']


@pytest.mark.asyncio
async def test_expansion_and_structural_retry_have_separate_single_allowances(tmp_path):
    case = case_record(5, tmp_path/'trial/cases/5/fixtures')
    a = runner.requirements(case)
    a['selection']['candidates'] = [c for c in a['selection']['candidates'] if c['type_id'] != 'file_output_node']
    draft = good_draft(5, case['root'])
    broken = deepcopy(draft)
    broken['nodes'] = list(broken['nodes'].values())
    report = await runner.run_case(5, tmp_path/'trial', tmp_path/'library', replies=[a, broken, draft, runner.meaning()])
    assert report['result'] == 'pass', report
    assert report['selection']['expansion_count'] == 1
    assert report['draft_retry']['attempted'] == 1
    assert report['model_calls'] == dict(attempted=4, succeeded=4)
    assert report['usage_summary']['not_reported'] == 0


@pytest.mark.asyncio
async def test_unknown_role_enum_stops_before_draft_and_keeps_usage(tmp_path):
    case = case_record(1, tmp_path/'trial/cases/1/fixtures')
    a = runner.requirements(case)
    a['selection'] = dict(candidates=[], roles=[dict(role='count_words', requirement_ids=['r1'], reason='Need an actual word count')])
    report = await runner.run_case(1, tmp_path/'trial', tmp_path/'library', replies=[a])
    assert report['result'] == 'fail'
    assert report['model_calls'] == dict(attempted=1, succeeded=1)
    assert any(e['code'] == 'invalid_response' for e in report['errors'])
    assert report['usage_summary']['not_reported'] == 0
    assert not list((tmp_path/'trial/cases/1/drafts').iterdir())
    assert report['meaning_review'] != 'pass'


@pytest.mark.asyncio
async def test_gate_rejects_unselected_type_then_only_one_retry(tmp_path):
    case = case_record(1, tmp_path/'trial/cases/1/fixtures')
    a = runner.requirements(case)
    draft = good_draft(1, case['root'])
    invalid = deepcopy(draft)
    invalid['nodes']['show']['type'] = 'concat_node'
    invalid['nodes']['show']['config'] = dict(template='Ready')
    report = await runner.run_case(1, tmp_path/'trial', tmp_path/'library', replies=[a, invalid, invalid])
    assert report['result'] == 'fail'
    assert report['draft_retry']['attempted'] == 1
    assert report['model_calls']['attempted'] == 3
    assert not list((tmp_path/'trial/cases/1/drafts').iterdir())
    evidence = json.loads((tmp_path/'trial/cases/1/evidence.json').read_text())
    assert 'unselected type_ids: concat_node' in str(evidence['first_check_error'])


@pytest.mark.asyncio
@pytest.mark.parametrize('case_set, expected_calls', [(1, 95), (2, 91)])
async def test_twenty_frozen_cases_recall_and_no_extra_ordinary_call(tmp_path, case_set, expected_calls):
    (tmp_path/'trial').mkdir()
    report = await runner.batch(tmp_path/'trial', case_set=case_set)
    assert report['result'] == 'pass' and report['fully_right'] == 10, report
    assert report['model_calls']['attempted'] == expected_calls
    for case in report['cases']:
        assert not case['recall']['missing_roles'], case
        if case['expected_status'] == 'ready':
            assert case['selection']['candidate_count'] <= len(PALETTE)
            calls = json.loads((Path(case['artifacts'])/'calls.json').read_text())
            for call in calls:
                content = call['messages'][0]['content']
                text = content if isinstance(content, str) else '\n'.join(part['text'] for part in content)
                assert len(text) + len(call['system']) <= .8 * selection.CONTEXT_LIMIT
        else:
            assert case['recall']['status_only'] and case['no_saved_workflow']


def test_search_never_uses_negative_text_as_a_positive_match(monkeypatch):
    factory = NodeFactory()
    real = factory.metadata_for_type
    def metadata(kind):
        meta = deepcopy(real(kind))
        if meta.get('node_metadata'):
            meta['node_metadata']['not_for'] = 'uniqueforbiddenword'
        return meta
    monkeypatch.setattr(factory, 'metadata_for_type', metadata)
    assert selection.positive_matches(factory, 'uniqueforbiddenword') == []


@pytest.mark.asyncio
async def test_exact_lookup_never_returns_partial_selection(monkeypatch):
    real = node_catalogue.list_node_types
    monkeypatch.setattr(node_catalogue, 'list_node_types', lambda f: [r for r in real(f) if r['type'] != 'end_node'])
    with pytest.raises(NodeError, match='no partial'):
        await node_catalogue.build(NodeFactory(), config(scope='Exact IDs', type_ids=['start_node', 'end_node']))


@pytest.mark.asyncio
async def test_snapshot_metadata_cannot_add_a_type_without_its_contract():
    text = await selection.snapshot(NodeFactory(), analysis_for(1), 'Show Ready', config())
    header, contracts = text.split('\n', 1)
    receipt = json.loads(header[len(selection.PREFIX):])
    receipt['selected_type_ids'].append('concat_node')
    altered = selection.PREFIX + json.dumps(receipt) + '\n' + contracts
    with pytest.raises(NodeError, match='stale'):
        selection.read_snapshot(altered)


@pytest.mark.asyncio
async def test_changed_discovery_binding_stops_before_snapshot_publication():
    a = analysis_for(1)
    node, ctx, memory, done, errors = node_runner('node_catalogue_node', config(
        scope='Selected analysis', type_ids_source='Vault', type_ids_vault_key='analysis',
        selection_request_vault_key='request', discovery_snapshot_vault_key='discovery',
        vault_write=True, vault_write_key='snapshot'))
    memory.store_persistent('analysis', json.dumps(a), type_tag='string')
    memory.store_persistent('request', 'Show Ready', type_tag='string')
    memory.store_persistent('discovery', '\nDiscovery: '+json.dumps(dict(
        registry_sha256='old registry', request_sha256=selection.digest('Show Ready'))), type_tag='string')
    await node.execute(ctx)
    assert not done and errors[0].code == 'selection_invalid'
    assert memory.read_persistent('snapshot') is None


def test_repeated_candidates_and_roles_merge():
    # A schema cannot forbid repeats; a repeated node or role is folded, not rejected.
    analysis = dict(status='ready', requirements=[dict(id='r1'), dict(id='r2')], selection=dict(
        candidates=[dict(type_id='text_transform_node', role='transform_text', requirement_ids=['r1'], reason='trim'),
                    dict(type_id='text_transform_node', role='transform_text', requirement_ids=['r2', 'r1'], reason='lower')],
        roles=[dict(role='transform_text', requirement_ids=['r1'], reason='trim'),
               dict(role='transform_text', requirement_ids=['r2'], reason='lower')]))
    original = deepcopy(analysis)
    merged = selection.validate_analysis(NodeFactory(), analysis)
    assert [c['requirement_ids'] for c in merged['candidates']] == [['r1', 'r2']]
    assert [r['requirement_ids'] for r in merged['roles']] == [['r1', 'r2']]
    assert analysis == original

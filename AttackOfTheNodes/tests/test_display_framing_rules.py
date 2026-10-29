"""Display framing is permitted without relaxing saved-content provenance."""
import json

import pytest

from tests.test_meta_nodes import runner as node_runner
from tools.draft_trials.cases import case_record, good_draft, fixture_variants
from tools.draft_trials.rules import check_rules
from tools.draft_trials import runner


@pytest.mark.parametrize('number', range(1, 11))
def test_plain_display_framing(number, tmp_path):
    runner.prepare_files(tmp_path, fixture_variants(number)[0])
    case = case_record(number, tmp_path)
    spec = good_draft(case['id'], case['root'])
    for node in spec['nodes'].values():
        if node['type'] == 'text_output_node':
            node['config']['template'] = 'Result: ' + node['config'].get('template', '{input}') + ' (shown)'
    assert check_rules(spec, case)['result'] == 'pass'


@pytest.mark.parametrize('word', ['exactly', 'only'])
def test_exact_display_stays_exact(word, tmp_path):
    case = case_record(6, tmp_path)
    case['request'] = 'Ask for a note, uppercase and save it, then show ' + word + ' the saved path.'
    spec = good_draft(case['id'], case['root'])
    assert check_rules(spec, case)['result'] == 'pass'
    for node in spec['nodes'].values():
        if node['type'] == 'text_output_node':
            node['config']['template'] = 'Saved path: {input[path]}'
    assert check_rules(spec, case)['result'] == 'fail'


@pytest.mark.asyncio
async def test_empty_label_and_start_payload():
    node, ctx, memory, done, errors = node_runner('text_output_node', {'label': ''}, 'Ready')
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {'default': '[] Ready'}
    assert str(memory.read_persistent('output_log')[0]) == '[] Ready'
    for config, expected in [({}, 'Workflow started'), ({'greeting': '  Monday Update  ', 'rows': []}, '  Monday Update  ')]:
        node, ctx, _, done, errors = node_runner('start_node', config)
        await node.execute(ctx)
        assert not errors and done[0]['data'] == {'default': expected}


@pytest.mark.asyncio
@pytest.mark.parametrize('right,port', [('value', 'true'), ('other', 'false')])
async def test_conditional_forwards_original_value(right, port):
    node, ctx, _, done, errors = node_runner('conditional_node', {'condition_type': 'equals', 'right_value': right}, 'value')
    await node.execute(ctx)
    assert not errors and done[0]['data'] == {port: 'value'}


def test_case_five_ready_default_instruction():
    spec = json.loads(runner.SPEC.read_text())
    prompt = spec['nodes']['analysis_question']['config']['template']
    assert 'Use Create unique' in prompt and 'Return ready' in prompt
    assert 'stopping without writing does not fulfill that request' in prompt


@pytest.mark.asyncio
async def test_clarified_contract_wording():
    text, _ = await runner.contract_inventory()
    for wording in ['Empty label still emits "[] "+text', 'with rows absent/empty, greeting string verbatim', 'Nonempty rows replace greeting', 'never the comparison boolean']:
        assert wording in text


@pytest.mark.parametrize('template', [
    'Saved path: {input[path][0]}',
    'Saved path: {input[path]} {input[path]}',
    'Not saved: {input[path]}',
    '/different/{input[path]}',
])
def test_path_display_still_rejects_invalid_framing(template, tmp_path):
    case = case_record(6, tmp_path)
    spec = good_draft(6, case['root'])
    for node in spec['nodes'].values():
        if node['type'] == 'text_output_node':
            node['config']['template'] = template
    assert check_rules(spec, case)['result'] == 'fail'

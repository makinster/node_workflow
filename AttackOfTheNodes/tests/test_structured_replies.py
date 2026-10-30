"""Real request/validation paths, mocked SDK only."""
from copy import deepcopy
import json

import pytest

from backend.integrations import claude
from tests.test_ask_claude import sdk, make

SCHEMA = dict(type='object', properties=dict(ok=dict(type='boolean')), required=['ok'])


@pytest.mark.asyncio
@pytest.mark.parametrize('model', claude.MODELS)
async def test_optional_reply_schema_is_sent_and_closed(sdk, model):
    node, ctx, done, errors = make(model=model, reply_schema=deepcopy(SCHEMA))
    sdk.result.model = model
    await node.execute(ctx)
    assert not errors and done
    _, kwargs = sdk.calls[0]
    assert kwargs['output_config'] == dict(effort='low', format=dict(type='json_schema', schema={**SCHEMA, 'additionalProperties': False}))
    assert json.loads(done[0]['data']['default']) == dict(ok=True)


@pytest.mark.asyncio
@pytest.mark.parametrize('reason,code', [('refusal', 'refusal'), ('max_tokens', 'incomplete_reply')])
async def test_structured_incomplete_reply_keeps_usage_and_no_output(sdk, reason, code):
    node, ctx, done, errors = make(reply_schema=SCHEMA, vault_write=True, vault_write_key='answer')
    events = []
    ctx.publish_event = lambda name, payload: events.append(payload)
    sdk.result.stop_reason = reason
    await node.execute(ctx)
    assert not done and isinstance(errors[0], claude.IncompleteReply)
    assert errors[0].code == code and errors[0].usage['input_tokens'] == 100
    assert ctx.memory_bank.read_persistent('answer') is None
    assert events[0]['status'] == 'incomplete' and events[0]['usage']['input_tokens'] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize('name,score,valid', [('ab', 5, False), ('valid', 20, False), ('toolongname', 5, False), ('valid', 5, True)])
async def test_local_constraints_stay_in_check_reply_not_api_grammar(sdk, name, score, valid):
    from backend.reply_schema import provider_schema
    from tests.test_meta_nodes import runner as node_runner
    schema = dict(type='object', properties=dict(
        name=dict(type='string', minLength=3, maxLength=8),
        score=dict(type='number', minimum=1, maximum=10)), required=['name', 'score'])
    original = deepcopy(schema)
    wire = provider_schema(schema)
    assert 'minLength' not in wire['properties']['name']
    assert 'maximum' not in wire['properties']['score']
    assert 'Checked afterwards:' in wire['properties']['score']['description']
    assert schema == original
    sdk.result.content = [type('Text', (), dict(type='text', text=json.dumps(dict(name=name, score=score))))()]
    node, ctx, done, errors = make(reply_schema=schema)
    await node.execute(ctx)
    assert done and not errors  # API grammar constraints satisfied, bounds checked next.
    check, ctx, memory, done, errors = node_runner('check_reply_node', dict(
        reply_schema=schema, expected_fields=[dict(name='name',kind='string',required=True),
                                            dict(name='score',kind='number',required=True)]),
        json.dumps(dict(name=name, score=score)))
    await check.execute(ctx)
    if valid:
        assert done and not errors
    else:
        assert not done and errors[0].code == 'reply_mismatch'


@pytest.mark.asyncio
@pytest.mark.parametrize('schema', [dict(type='object',additionalProperties=True),
    dict(type='object',properties=dict(value={'$ref':'https://invalid.example/schema'})),
    dict(type='object',properties=dict(value={'$ref':'#/$defs/loop'}),
         **{'$defs':dict(loop=dict(type='object',properties=dict(again={'$ref':'#/$defs/loop'})))}),
    '{"type":"object","type":"array"}', 'not json'])
async def test_bad_schemas_fail_before_api_or_secrets(sdk, schema):
    node, ctx, done, errors = make(reply_schema=schema)
    ctx.secrets_manager.get_secret = lambda _: pytest.fail('Bad schema must fail before credential reads')
    await node.execute(ctx)
    assert not done and errors[0].code == 'shape_invalid' and not sdk.clients


@pytest.mark.asyncio
async def test_schema_violation_keeps_billed_usage(sdk):
    node, ctx, done, errors = make(reply_schema=SCHEMA)
    sdk.result.content = [type('Text', (), dict(type='text', text='{"ok":"not boolean"}'))()]
    await node.execute(ctx)
    assert not done and isinstance(errors[0], claude.IncompleteReply)
    assert errors[0].code == 'invalid_response' and errors[0].usage['input_tokens'] == 100


def test_generated_v2_schemas_match_live_enums_and_keep_second_checks():
    from tools.draft_trials import runner
    from tools.draft_trials.reply_schemas import analysis_schema, judge_schema
    from backend.palette_selection import ADMITTED, ROLE_TYPES
    from backend.reply_schema import provider_schema
    spec = json.loads(runner.SPEC.read_text())
    for ai, gate in [('analysis','analysis_shape'),('resolve','resolved_shape'),('judge','judge_shape')]:
        schema = analysis_schema() if ai != 'judge' else judge_schema()
        assert spec['nodes'][ai]['config']['reply_schema'] == spec['nodes'][gate]['config']['reply_schema'] == schema
        assert {'from':ai+'.default','to':gate+'.input'} in spec['connections']
        def closed(node):
            if isinstance(node, dict):
                if node.get('type') == 'object': assert node['additionalProperties'] is False
                for value in node.values(): closed(value)
            elif isinstance(node, list):
                for value in node: closed(value)
        closed(provider_schema(schema))
    selection = analysis_schema()['properties']['selection']['properties']
    assert selection['roles']['items']['properties']['role']['enum'] == sorted(ROLE_TYPES)
    assert selection['candidates']['items']['properties']['type_id']['enum'] == sorted(ADMITTED)
    assert not spec['nodes']['draft']['config'].get('reply_schema')
    assert spec['nodes']['draft']['config']['reply_json']


def test_local_reference_is_inlined_without_network():
    from backend.reply_schema import provider_schema
    schema = dict(type='object', properties=dict(result={'$ref':'#/$defs/result'}),
                  **{'$defs': dict(result=dict(type='object', properties=dict(value=dict(type='string'))))})
    wire = provider_schema(schema)
    assert '$defs' not in wire and wire['properties']['result']['additionalProperties'] is False


@pytest.mark.asyncio
async def test_json_schema_widget_shows_valid_json_for_object_config():
    from frontend.widgets.form_generator import _widget_for_field
    field = _widget_for_field('reply_schema', 'code', dict(presentation='json_schema', language='json'), SCHEMA)
    assert json.loads(field.value) == SCHEMA


@pytest.mark.asyncio
@pytest.mark.parametrize('variant,expected,text', [('good', 'pass', 'Ready'), ('bad', 'fail', 'Waiting')])
async def test_end_framing_guard_has_real_observable_difference(tmp_path, variant, expected, text):
    from tools.draft_trials import runner
    from tools.draft_trials.cases import calibration_pairs, case_record
    from tools.draft_trials.rules import check_rules
    pair = next(p for p in calibration_pairs() if p['id'] == 'end_framing_does_not_hide_missing_value')
    case = case_record(1, tmp_path/'fixtures')
    (tmp_path/'fixtures').mkdir()
    spec = pair[variant]
    assert len(calibration_pairs()) == 24
    assert check_rules(spec, case)['result'] == expected
    behavior = await runner.target_fixtures(spec, case, tmp_path/'runs')
    assert behavior['result'] == expected
    assert behavior['fixtures'][0]['outputs'] == [text]
    assert behavior['fixtures'][0]['completion_noise'] == ['[END] Branch completed']


@pytest.mark.asyncio
async def test_v2_call_sends_generated_schema_with_local_only_limits_removed(sdk):
    from tools.draft_trials import runner
    from tools.draft_trials.reply_schemas import analysis_schema
    a = runner.requirements(dict(request='Show Ready'))
    node, ctx, done, errors = make(reply_schema=analysis_schema())
    sdk.result.content = [type('Text', (), dict(type='text', text=json.dumps(a)))()]
    await node.execute(ctx)
    assert done and not errors
    schema = sdk.calls[0][1]['output_config']['format']['schema']
    assert schema['properties']['status']['enum'] == ['ready','clarify','outside_scope','needs_new_node']
    roles = schema['properties']['selection']['properties']['roles']
    assert 'maxItems' not in roles and roles['items']['additionalProperties'] is False
    assert json.loads(done[0]['data']['default']) == a


@pytest.mark.asyncio
async def test_json_text_schema_is_optional_and_works_without_reply_json(sdk):
    node, ctx, done, errors = make(reply_schema=json.dumps(SCHEMA), reply_json=False)
    await node.execute(ctx)
    assert done and not errors
    assert sdk.calls[0][1]['output_config']['format']['type'] == 'json_schema'
    assert json.loads(done[0]['data']['default']) == dict(ok=True)


@pytest.mark.asyncio
async def test_reply_schema_editor_opens_and_cancel_preserves_object():
    from tests.test_small_wins_ui import Host, make as make_check
    from frontend.widgets.command_input import CommandTextArea
    factory, wm, node = make_check(reply_schema=deepcopy(SCHEMA))
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        screen = app.screen
        preview = screen.query_one('#field-reply_schema')
        preview.focus(); await pilot.press('enter'); await pilot.pause()
        assert json.loads(app.screen.query_one(CommandTextArea).text) == SCHEMA
        await pilot.press('ctrl+q'); await pilot.pause()
        assert app.screen is screen
        assert wm.get_node_data(node)['config']['reply_schema'] == SCHEMA

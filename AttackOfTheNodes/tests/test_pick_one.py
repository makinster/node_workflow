"""Real HTTP tests use loopback exclusively; the hosted service is never called."""
import asyncio
import copy
import json
import time
from types import SimpleNamespace

import pytest
from aiohttp import web

from backend.event_bus import EventBus
from backend.integrations import jev
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_factory import NodeFactory
from backend.nodes.ai.pick_one_node import PickOneNode
from backend.port_types import resolved_metadata, trace_producers
from backend.vault_declarations import typed_vault_writes
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

SECRET = 'test-credential-do-not-store'
ROWS = [{'id': 'row1', 'answer': 'billing', 'description': 'Payments and refunds'},
        {'id': 'row2', 'answer': 'bug', 'description': 'Something is broken'}]


def reply(choice='billing', confidence=.8, scores=None):
    return {'model': 'jev-latest', 'answers': {'pick': {'type': 'choice', 'choice': choice,
            'confidence': confidence, 'probabilities': scores or {'billing': .9, 'bug': .1}}},
            'usage': {'input_tokens': 12, 'output_tokens': 3}}


@pytest.fixture
async def server(monkeypatch):
    state = SimpleNamespace(body=reply(), status=200, calls=[], delay=0, raw=None,
                            redirect=False, drip=False, started=asyncio.Event(), closed=asyncio.Event())

    async def handler(request):
        state.calls.append((await request.json(), dict(request.headers)))
        state.started.set()
        if state.drip:
            response = web.StreamResponse()
            await response.prepare(request)
            try:
                while True:
                    await response.write(b' ')
                    await asyncio.sleep(.03)
            except (ConnectionResetError, asyncio.CancelledError):
                state.closed.set()
            return response
        await asyncio.sleep(state.delay)
        if state.redirect:
            return web.Response(status=302, headers={'Location': state.url})
        if state.raw is not None:
            return web.Response(body=state.raw, status=state.status)
        return web.json_response(state.body, status=state.status)

    app = web.Application()
    app.router.add_post('/v1/systemone', handler)
    runner = web.AppRunner(app, shutdown_timeout=.1)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    state.url = f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/v1/systemone'
    monkeypatch.setattr(jev, 'API_URL', state.url)
    yield state
    await runner.cleanup()


def node_context(inputs=None, secrets=None, **changes):
    config = {**PickOneNode.default_config, 'question': 'Who should handle this?',
              'choices': copy.deepcopy(ROWS), 'api_key_secret': 'service-key', **changes}
    node = PickOneNode('pick', config)
    done, errors = [], []
    memory = MemoryBank(EventBus())
    memory.store_persistent('text', 'Vault message', type_tag='string')
    class Secrets:
        def get_secret(self, key):
            return (secrets if secrets is not None else {'service-key': SECRET}).get(key)
    context = NodeContext(node_id='pick', branch_id='s1', run_id='run-test',
        inputs=inputs if inputs is not None else {'input': 'Refund this charge'}, memory_bank=memory,
        signal_done=done.append, signal_error=errors.append,
        signal_waiting_for_input=lambda _: None, wait_for_nodes=lambda *args: None,
        wait_for_merge=lambda *args: None, secrets_manager=Secrets())
    return node, context, done, errors


@pytest.mark.asyncio
@pytest.mark.parametrize('source,text', [('Upstream payload','Refund this charge'),
                                         ('Vault','Vault message'), ('Configured','Typed message')])
async def test_sources_exact_protocol_and_default_output(server, source, text):
    node, ctx, done, errors = node_context(input_source=source, input_vault_key='text', input='Typed message')
    await node.execute(ctx)
    assert not errors and done == [{'data': {'default': 'billing'}}]
    payload, headers = server.calls[0]
    assert payload == {'model': 'jev-latest', 'state': text, 'questions': {'pick': {
        'type': 'choice', 'instructions': 'Who should handle this?',
        'criteria': {'billing': 'Payments and refunds', 'bug': 'Something is broken'}}}}
    assert headers['Authorization'] == 'Bearer ' + SECRET
    assert 'application/json' in headers['Content-Type']
    assert SECRET not in json.dumps(node.config)
    assert ctx.memory_bank.read_persistent('details') is None


@pytest.mark.asyncio
@pytest.mark.parametrize('confidence,answer', [(0,'unsure'),(.299,'unsure'),(.3,'billing'),(1,'billing')])
async def test_unsure_boundary_always_finishes(server, confidence, answer):
    server.body = reply(confidence=confidence)
    node, ctx, done, errors = node_context()
    await node.execute(ctx)
    assert not errors and done[0]['data']['default'] == answer


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['Billing',' billing','billing\n','other'])
async def test_unknown_answer_is_exact_nonretryable_error(server, text):
    server.body = reply(choice=text)
    node, ctx, done, errors = node_context()
    await node.execute(ctx)
    assert not done and errors[0].code == 'undeclared_choice' and not errors[0].retryable


@pytest.mark.asyncio
async def test_whitespace_unicode_and_case_preserved(server):
    rows = [{'answer':' A ','description':'Spaced'}, {'answer':'a','description':'Lowercase'},
            {'answer':'été','description':'French'}]
    server.body = reply(' A ', scores={' A ': .7,'a':.2,'été':.1})
    node, ctx, done, errors = node_context(choices=rows)
    await node.execute(ctx)
    assert not errors and done[0]['data']['default'] == ' A '
    assert list(server.calls[0][0]['questions']['pick']['criteria']) == [' A ','a','été']


@pytest.mark.asyncio
async def test_independent_vault_outputs_and_no_details_downstream(server):
    node, ctx, done, errors = node_context(vault_write=True, vault_write_key='answer',
                                         details_vault_write=True, details_vault_key='details')
    await node.execute(ctx)
    assert not errors and done == [{'data': {'default':'billing'}}]
    assert ctx.memory_bank.read_persistent('answer') == 'billing'
    assert ctx.memory_bank.read_persistent('details') == {
        'scores':{'billing':.9,'bug':.1},'confidence':.8,'model':'jev-latest',
        'usage':{'input_tokens':12,'output_tokens':3}}
    node.config['vault_write'] = False
    node.config['transient_output'] = False
    await node.execute(ctx)
    assert done[-1] == {'data':{}}


@pytest.mark.asyncio
@pytest.mark.parametrize('status,code,retry', [(401,'auth_failed',False),(403,'auth_failed',False),
    (400,'provider_error',True),(422,'provider_error',True),(429,'provider_error',True),
    (500,'provider_error',True),(503,'provider_error',True)])
async def test_errors_do_not_echo_headers_or_bodies(server, caplog, status, code, retry):
    server.status = status;server.body = {'error':SECRET}
    node, ctx, done, errors = node_context()
    await node.execute(ctx)
    assert not done and errors[0].code == code and errors[0].retryable == retry
    assert SECRET not in str(errors[0]) and SECRET not in caplog.text
    assert len(server.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('key', ['', None, 'bad\r\nkey'])
async def test_missing_or_invalid_key_never_calls_http(server, key):
    node, ctx, done, errors = node_context(secrets={'service-key': key})
    await node.execute(ctx)
    assert not server.calls and not done and errors[0].code == 'auth_failed'


@pytest.mark.asyncio
@pytest.mark.parametrize('damage', [
    lambda d:d.update(answers={}), lambda d:d['answers']['pick'].update(confidence=float('nan')),
    lambda d:d['answers']['pick'].update(confidence=True),
    lambda d:d['answers']['pick'].update(confidence=10**400),
    lambda d:d['answers']['pick'].update(probabilities={'billing':1}),
    lambda d:d['answers']['pick'].update(probabilities={'billing':.9,'bug':2}),
    lambda d:d.update(usage={'input_tokens':SECRET,'output_tokens':3}),
    lambda d:d.update(model={}),lambda d:d['answers']['pick'].update(type='score')])
async def test_malformed_response_fails_safely(server, damage):
    damage(server.body)
    node, ctx, done, errors = node_context()
    await node.execute(ctx)
    assert not done and errors[0].code == 'provider_error'
    assert SECRET not in str(errors[0])


@pytest.mark.asyncio
@pytest.mark.parametrize('raw', [b'not json', b'\xff', b'x'*(1024*1024+1)],
                         ids=['invalid-json','invalid-utf8','oversized'])
async def test_invalid_and_oversized_json(server, raw):
    server.raw = raw
    node, ctx, done, errors = node_context()
    await node.execute(ctx)
    assert not done and errors[0].code == 'provider_error'


@pytest.mark.asyncio
async def test_no_redirect_with_authorization(server):
    server.redirect=True
    node, ctx, done, errors = node_context()
    await node.execute(ctx)
    assert len(server.calls)==1 and not done and errors[0].code=='provider_error'


@pytest.mark.asyncio
async def test_deadline_includes_slow_drip_and_closes_connection(server):
    server.drip = True
    started = time.monotonic()
    with pytest.raises(jev.JevError) as error:
        await jev.pick_one(text='x',question='q',criteria={'a':'A'},api_key=SECRET,timeout=.15)
    assert error.value.code=='timed_out' and time.monotonic()-started < .8
    await asyncio.wait_for(server.closed.wait(), .5)


@pytest.mark.asyncio
async def test_cancellation_closes_connection(server):
    server.drip=True
    task=asyncio.create_task(jev.pick_one(text='x',question='q',criteria={'a':'A'},api_key=SECRET,timeout=10))
    await server.started.wait();task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    await asyncio.wait_for(server.closed.wait(),.5)


@pytest.mark.asyncio
async def test_node_timeout_is_retryable(server):
    server.delay=1.2
    node, ctx, done, errors=node_context(timeout=1)
    await node.execute(ctx)
    assert not done and errors[0].code=='timed_out' and errors[0].retryable


@pytest.mark.asyncio
@pytest.mark.parametrize('changes', [
    {'choices':[]}, {'choices':[ROWS[0],ROWS[0]]}, {'choices':[{'answer':'  '}]},
    {'choices':[{'answer':1}]}, {'choices':'bad'}, {'question':''}, {'timeout':-1},
    {'unsure_below':float('nan')}, {'details_vault_write':True},
    {'vault_write':True,'vault_write_key':'same','details_vault_write':True,'details_vault_key':'same'}])
async def test_bad_config_refuses_before_spending_request(server, changes):
    node,ctx,done,errors=node_context(**changes)
    await node.execute(ctx)
    assert not done and errors and not server.calls


def test_types_declarations_and_editor_do_not_create_a_details_branch():
    from frontend.error_paths import editor_output_ports
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('Routing')
    nid=wm.add_node('pick_one_node')
    config={**wm.get_node_data(nid)['config'],'choices':ROWS,'question':'Question',
            'api_key_secret':'key','vault_write':True,'vault_write_key':'answer',
            'details_vault_write':True,'details_vault_key':'details'}
    wm.update_node_config(nid,config)
    metadata=resolved_metadata(factory,'pick_one_node',config)
    assert typed_vault_writes('pick_one_node',config,metadata)=={'answer':'string','details':'var'}
    assert trace_producers(wm.get_all_node_data(),factory,nid,'default')==[(nid,'string')]
    assert editor_output_ports(factory,wm.get_node_data(nid))==['default']
    node=wm.get_node_data(nid);node['config']['choices']=[ROWS[0],ROWS[0]]
    wm.update_node_config(nid,node['config'])
    assert any(e['code']=='invalid_rows' for e in validate_workflow(wm,factory)['errors'])


@pytest.mark.asyncio
async def test_saved_run_routes_plain_answer_through_conditional(server, tmp_path, monkeypatch):
    from tests.test_subworkflow_calls import Flow
    from backend import persistence, configuration_manager, run_history
    from backend.run_service import RunService
    from backend.save_manager import SaveManager
    from backend.secrets_manager import SecretsManager
    for name in ('WORKFLOWS_DIR','RUN_HISTORY_DIR','RUN_ERRORS_DIR','RUN_OUTPUTS_DIR','RUN_FILES_DIR','SETTINGS_DIR'):
        monkeypatch.setattr(persistence,name,tmp_path/name.lower())
    monkeypatch.setattr(configuration_manager,'SETTINGS_DIR',tmp_path/'settings')
    monkeypatch.setattr(run_history,'RUN_HISTORY_DIR',tmp_path/'history')
    monkeypatch.setattr(SecretsManager,'get_secret',lambda self,key:SECRET if key=='service-key' else None)
    flow=(Flow('Support router').node('s','start_node',greeting='Refund this charge')
          .node('pick','pick_one_node',question='Who should handle this?',choices=ROWS,
                api_key_secret='service-key',details_vault_write=True,details_vault_key='pick_info')
          .node('billing','conditional_node',condition_type='equals',left_value_source='input',right_value='billing')
          .node('yes','text_output_node',input_source='Upstream payload',template='{input}',label='Billing')
          .node('no','text_output_node',input_source='Upstream payload',template='{input}',label='Other')
          .node('end_yes','end_node',record_line=False).node('end_no','end_node',record_line=False)
          .link('s','pick','billing'))
    flow.map.connect(flow.ids['billing'],'true',flow.ids['yes'],'input')
    flow.map.connect(flow.ids['billing'],'false',flow.ids['no'],'input')
    flow.link('yes','end_yes').link('no','end_no')
    workflow_id=flow.save()
    assert SECRET not in json.dumps(persistence.load_workflow(workflow_id))
    service=RunService.create();service.load(workflow_id)
    try:
        await service.start(validate=False)
        result=await asyncio.wait_for(service.wait(),3)
        assert result.exit_code==0 and result.outputs==['[Billing] billing']
        assert service.master_state._memory_bank.read_persistent('pick_info')['confidence']==.8
        assert SECRET not in json.dumps(result.to_dict())
    finally:
        service.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('size',[(80,24),(120,40)])
async def test_ui_rejects_duplicate_rows_and_saves_independent_vault_routing(tmp_path,size):
    from textual.app import App
    from textual.widgets import Checkbox
    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.form_generator import ObjectListField
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('Edit')
    nid=wm.add_node('pick_one_node');cfg=wm.get_node_data(nid)['config']
    cfg.update(question='Who?',choices=copy.deepcopy(ROWS),api_key_secret='service-key')
    wm.update_node_config(nid,cfg)
    class Host(App):
        CSS_PATH='../frontend/styles.tcss'
        def on_mount(self):
            self.push_screen(NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid)))
    async with Host().run_test(size=size) as pilot:
        screen=pilot.app.screen
        await pilot.press('2');await pilot.pause()
        assert not screen.query('#field-details_label')
        assert not screen.query('#field-provider') and not screen.query('#field-model')
        rows=screen.query_one('#field-choices',ObjectListField)
        await rows.replace_rows([ROWS[0],ROWS[0]])
        assert screen._save_result() is None
        await rows.replace_rows(ROWS)
        await pilot.press('3');await pilot.pause()
        screen.query_one('#vault-output-disabled-default',Checkbox).value=False
        screen.query_one('#vault-output-key-default').value='answer'
        assert screen.query_one('#vault-output-disabled-details',Checkbox).value
        screen.query_one('#vault-output-disabled-details',Checkbox).value=False
        screen.query_one('#vault-output-key-details').value='details'
        result=screen._save_result()
        assert result['config']['vault_write_key']=='answer'
        assert result['config']['details_vault_key']=='details'
        assert result['config']['details_vault_write'] is True
        assert SECRET not in json.dumps(result)
        wm.update_node_config(nid,result['config'])
        reopened=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid))
        pilot.app.push_screen(reopened)
        await pilot.pause()
        await pilot.press('3');await pilot.pause()
        assert reopened.query_one('#vault-output-key-default').value=='answer'
        assert reopened.query_one('#vault-output-key-details').value=='details'
        assert not reopened.query_one('#vault-output-disabled-details',Checkbox).value
        await pilot.press('escape')
        await pilot.pause()
        assert wm.get_node_data(nid)['config']['details_vault_key']=='details'
        assert screen.query_one('#save-node-config').display and screen.query_one('#cancel-node-config').display


@pytest.mark.asyncio
async def test_details_discards_untrusted_response_metadata_and_redacts_echoed_key(server,caplog):
    server.body['model']='server-'+SECRET
    server.body['usage']['debug']=SECRET
    server.body['request']=SECRET
    node,ctx,done,errors=node_context(details_vault_write=True,details_vault_key='details')
    await node.execute(ctx)
    assert not errors
    assert SECRET not in json.dumps(ctx.memory_bank.read_persistent('details'))
    assert SECRET not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize('value',[None,42,True,{},''])
async def test_non_text_input_is_refused(server,value):
    node,ctx,done,errors=node_context(inputs={'input':value})
    await node.execute(ctx)
    assert errors and not done and not server.calls


def test_vault_only_connection_is_validation_error():
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('Bad wire')
    pick=wm.add_node('pick_one_node');end=wm.add_node('end_node')
    wm.connect(pick,'details',end,'input')
    assert any(e['code']=='vault_only_connection' for e in validate_workflow(wm,factory)['errors'])


@pytest.mark.asyncio
async def test_keyboard_save_keeps_exact_answers_and_secret_reference():
    from textual.app import App
    from frontend.screens.node_config import NodeConfigScreen
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('Keys')
    nid=wm.add_node('pick_one_node');config=wm.get_node_data(nid)['config']
    config.update(question='Who?',choices=ROWS,api_key_secret='service-key')
    wm.update_node_config(nid,config)
    seen=[]
    class Host(App):
        CSS_PATH='../frontend/styles.tcss'
        def on_mount(self):
            self.push_screen(NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid)),seen.append)
    async with Host().run_test(size=(80,24)) as pilot:
        await pilot.press('2');await pilot.pause()
        field=pilot.app.screen.query_one('#field-question');field.focus()
        await pilot.press('e','end','ctrl+u','W','h','e','r','e','?','escape')
        await pilot.press('ctrl+s');await pilot.pause()
        pilot.app.screen.query_one('#save-node-config').focus()
        await pilot.press('enter');await pilot.pause()
    assert seen and seen[0]['config']['question']=='Where?'
    assert seen[0]['config']['choices']==ROWS
    assert seen[0]['config']['api_key_secret']=='service-key'
    assert SECRET not in json.dumps(seen)

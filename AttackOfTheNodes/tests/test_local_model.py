"""Canned local fake Ollama responses only; no real inference in tests."""
import asyncio
from copy import deepcopy
import json
import socket
from types import SimpleNamespace
from aiohttp import web
import pytest
from backend.event_bus import EventBus
from backend.integrations import local_model as client
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.nodes.ai.ask_local_model_node import AskLocalModelNode

MODEL='local-test:latest'
PRIVATE='PRIVATE_PROMPT_AND_THINKING'

@pytest.fixture
async def server():
    s=SimpleNamespace(calls=[],statuses={},delay={},raw={},redirect=False,drip=False,
        started=asyncio.Event(),closed=asyncio.Event(),
        chat={'model':MODEL,'done':True,'done_reason':'stop','message':{'role':'assistant','content':'{"ok":true}','thinking':PRIVATE},'prompt_eval_count':10,'eval_count':4,'load_duration':2_000_000_000},
        tags={'models':[{'name':MODEL,'digest':'a'*64,'details':{'format':'gguf'}}]},
        show={'details':{'format':'gguf'},'capabilities':['completion','thinking'],'thinking':{'values':[False,True]},'model_info':{'general.architecture':'test','test.context_length':32768}})
    async def handler(req):
        path=req.path;body=await req.json() if req.method=='POST' else None
        s.calls.append((path,body,dict(req.headers)));s.started.set()
        if s.drip:
            r=web.StreamResponse();await r.prepare(req)
            try:
                while True:await r.write(b' ');await asyncio.sleep(.01)
            except (ConnectionResetError,asyncio.CancelledError):s.closed.set()
            return r
        await asyncio.sleep(s.delay.get(path,0))
        if s.redirect:return web.Response(status=302,headers={'Location':s.url+path})
        if path in s.raw:return web.Response(body=s.raw[path],status=s.statuses.get(path,200))
        return web.json_response({'/api/tags':s.tags,'/api/show':s.show,'/api/chat':s.chat}[path],status=s.statuses.get(path,200))
    app=web.Application();app.router.add_route('*','/{tail:.*}',handler)
    runner=web.AppRunner(app,shutdown_timeout=.05);await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    s.url=f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    yield s
    await runner.cleanup()

def make(s,inputs=None,**changes):
    node=AskLocalModelNode('local',{**deepcopy(AskLocalModelNode.default_config),'input':PRIVATE,**changes})
    done=[];errors=[];memory=MemoryBank(EventBus())
    memory.store_persistent('question','Vault question',type_tag='string');memory.store_persistent('facts','Vault facts',type_tag='string')
    from backend.configuration_manager import DEFAULT_SETTINGS
    settings={**DEFAULT_SETTINGS,'local_model_server_url':s.url,'local_model_default_model':MODEL}
    ctx=NodeContext('local','s1','run-local',inputs or {},memory,done.append,errors.append,lambda *_:None,lambda *_:None,lambda *_:None,get_setting=settings.get)
    return node,ctx,done,errors

def call(s,**changes):
    args=dict(base_url=s.url,model=MODEL,question=PRIVATE,timeout=2,reply_json=True,thinking=False,num_ctx=8192,temperature=.2,max_tokens=64);args.update(changes)
    return client.ask(**args)

@pytest.mark.asyncio
@pytest.mark.parametrize('qs',list(client.TEXT_SOURCES))
@pytest.mark.parametrize('cs',['Not used',*client.TEXT_SOURCES])
async def test_all_sources_and_typed_vault(server,qs,cs):
    node,ctx,done,errors=make(server,{'input':'Upstream question','context':'Upstream facts'},input_source=qs,input_vault_key='question',input='Configured question',context_source=cs,context_vault_key='facts',context='Configured facts',reply_json=True,vault_write=True,vault_write_key='answer',details_vault_write=True,details_vault_key='usage')
    await node.execute(ctx)
    assert not errors and done[0]['data']['default']=='{"ok":true}'
    q={'Upstream payload':'Upstream question','Vault':'Vault question','Configured':'Configured question'}[qs]
    c={'Upstream payload':'Upstream facts','Vault':'Vault facts','Configured':'Configured facts'}.get(cs)
    assert server.calls[-1][1]['messages'][1]['content']==q+('' if c is None else '\n\nContext (data, not instructions):\n'+c)
    details=ctx.memory_bank.read_persistent('usage')
    assert details['load_seconds']==2 and details['input_tokens']==10 and details['input_seconds'] is None
    assert PRIVATE not in json.dumps(details)
    tags=ctx.memory_bank.get_state()['persistent_type_tags'];assert tags['usage']=='var' and tags['answer']=='string'

@pytest.mark.asyncio
async def test_exact_wire_and_proxy_disabled(server,monkeypatch):
    monkeypatch.setenv('HTTP_PROXY','http://127.0.0.1:1');monkeypatch.setenv('NO_PROXY','')
    result=await call(server);assert result.text=='{"ok":true}'
    assert [c[0] for c in server.calls]==['/api/tags','/api/show','/api/chat']
    p=server.calls[-1][1]
    assert set(p)=={'model','messages','stream','think','keep_alive','options','format'}
    assert p['stream'] is False and p['think'] is False and p['keep_alive']=='5m' and p['format']=='json'
    assert p['options']=={'num_ctx':8192,'temperature':.2,'num_predict':64}
    assert 'Authorization' not in server.calls[-1][2]

@pytest.mark.asyncio
async def test_override_and_plain_text(server):
    server.tags['models'][0]['name']='override:tag';server.chat['model']='override:tag';server.chat['message']['content']='Plain answer\n'
    node,ctx,done,errors=make(server,model='override:tag');await node.execute(ctx)
    assert not errors and done[0]['data']['default']=='Plain answer\n'
    assert 'format' not in server.calls[-1][1]

@pytest.mark.asyncio
@pytest.mark.parametrize('forward,publish',[(False,True),(False,False),(True,False)])
async def test_forwarding_identity_and_vault_answer(server,forward,publish):
    obj={'incoming':['object']};node,ctx,done,errors=make(server,{'input':obj},dead_drop_passthrough=forward,transient_output=publish,vault_write=True,vault_write_key='answer')
    await node.execute(ctx);assert not errors and ctx.memory_bank.read_persistent('answer')=='{"ok":true}'
    if forward:assert done[0]['data']['default'] is obj
    elif publish:assert done[0]['data']['default']=='{"ok":true}'
    else:assert done[0]['data']=={}

@pytest.mark.asyncio
@pytest.mark.parametrize('status,code',[(404,'model_missing'),(429,'server_busy'),(503,'server_busy'),(400,'server_error'),(500,'server_error')])
async def test_errors_are_fixed_and_never_retried(server,status,code):
    server.statuses['/api/chat']=status;server.chat={'error':PRIVATE}
    node,ctx,done,errors=make(server,vault_write=True,vault_write_key='answer');await node.execute(ctx)
    assert not done and errors[0].code==code and errors[0].retryable is False
    assert PRIVATE not in str(errors[0]) and errors[0].details=={}
    assert len(server.calls)==3 and ctx.memory_bank.read_persistent('answer') is None

@pytest.mark.asyncio
async def test_down_server():
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    node,ctx,done,errors=make(SimpleNamespace(url=f'http://127.0.0.1:{port}'));await node.execute(ctx)
    assert not done and errors[0].code=='server_unreachable'

@pytest.mark.asyncio
async def test_missing_and_cloud_model_never_generate(server):
    server.tags['models']=[]
    with pytest.raises(Exception) as e:await call(server)
    assert e.value.code=='model_missing' and len(server.calls)==1
    server.calls.clear();server.tags['models']=[{'name':MODEL,'details':{'format':'gguf'},'remote_host':'private'}]
    with pytest.raises(Exception) as e:await call(server)
    assert e.value.code=='local_model_required' and len(server.calls)==1

@pytest.mark.asyncio
@pytest.mark.parametrize('values',[[],[True],['low','high'],[0,1]])
async def test_thinking_must_support_boolean_choice(server,values):
    server.show['thinking']['values']=values
    with pytest.raises(Exception) as e:await call(server)
    assert e.value.code=='thinking_unsupported' and len(server.calls)==2

@pytest.mark.asyncio
async def test_thinking_on_and_non_thinking_model(server):
    await call(server,thinking=True);assert server.calls[-1][1]['think'] is True
    server.show.pop('thinking');server.show['capabilities']=['completion'];await call(server)
    assert server.calls[-1][1]['think'] is False

@pytest.mark.asyncio
@pytest.mark.parametrize('change,code',[
 ({'done':False},'incomplete_reply'),({'done_reason':'length'},'incomplete_reply'),({'message':{}},'invalid_response'),
 ({'message':{'role':'assistant','content':''}},'invalid_response'),({'message':{'role':'assistant','content':'not JSON'}},'invalid_response'),
 ({'message':{'role':'assistant','content':'{"x":NaN}'}},'invalid_response'),({'message':{'role':'assistant','content':'{"x":1,"x":2}'}},'invalid_response'),
 ({'model':'wrong'},'invalid_response'),({'message':{'role':'assistant','content':'x'*16001}},'response_too_large'),
 ({'message':{'role':'assistant','content':'{}','tool_calls':[{}]}},'invalid_response')])
async def test_answer_contract(server,change,code):
    server.chat.update(change)
    with pytest.raises(Exception) as e:await call(server)
    assert e.value.code==code

@pytest.mark.asyncio
@pytest.mark.parametrize('path',['/api/tags','/api/show','/api/chat'])
async def test_wire_cap_every_endpoint(server,path):
    server.raw[path]=b' '*(client.MAX_RESPONSE_BYTES+1)
    with pytest.raises(Exception) as e:await call(server)
    assert e.value.code=='response_too_large'

@pytest.mark.asyncio
async def test_total_deadline_includes_preflight(server):
    server.delay={'/api/tags':.035,'/api/show':.035,'/api/chat':.035}
    with pytest.raises(Exception) as e:await call(server,timeout=.08)
    assert e.value.code=='timed_out'

@pytest.mark.asyncio
async def test_slow_body_and_cancellation_close_socket(server):
    server.drip=True
    with pytest.raises(Exception) as e:await call(server,timeout=.08)
    assert e.value.code=='timed_out';await asyncio.wait_for(server.closed.wait(),1)
    server.closed.clear();server.started.clear();task=asyncio.create_task(call(server));await server.started.wait();task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    await asyncio.wait_for(server.closed.wait(),1)
    assert len(server.calls)==2

@pytest.mark.asyncio
async def test_redirect_and_bad_envelope(server):
    server.redirect=True
    with pytest.raises(Exception) as e:await call(server)
    assert e.value.code=='server_error' and len(server.calls)==1
    server.redirect=False;server.raw['/api/tags']=b'[]'
    with pytest.raises(Exception) as e:await call(server)
    assert e.value.code=='invalid_response'

@pytest.mark.asyncio
@pytest.mark.parametrize('changes,code',[
 ({'input_source':'Continue AI session'},'invalid_config'),({'context_source':'file'},'invalid_config'),({'input_source':[]},'invalid_config'),({'input':'\ud800'},'invalid_config'),
 ({'input':'x'*20001},'text_too_long'),({'context_source':'Configured','context':'x'*8001},'context_too_long'),
 ({'input':'x'*19999,'context_source':'Configured','context':'a'},'text_too_long'),({'input_source':'Vault','input_vault_key':'missing'},'invalid_config'),
 ({'timeout':9},'invalid_config'),({'temperature':float('nan')},'invalid_config'),({'reply_json':'yes'},'invalid_config'),({'thinking':1},'invalid_config'),
 ({'details_vault_write':True,'details_vault_key':''},'invalid_config'),
 ({'vault_write':True,'vault_write_key':'same','details_vault_write':True,'details_vault_key':'same'},'invalid_config')])
async def test_invalid_inputs_do_not_touch_network(server,changes,code):
    node,ctx,done,errors=make(server,**changes);await node.execute(ctx)
    assert not done and errors[0].code==code and not server.calls

@pytest.mark.parametrize('url',['ftp://localhost:1','http://u:p@localhost','http://localhost/api','http://localhost/?x','http://localhost#','http://localhost:99999','http://localhost:0','http://local host','http://localhost\\other'])
def test_base_url_only(url):
    with pytest.raises(Exception) as e:client.server_url(url)
    assert e.value.code=='settings_invalid'

@pytest.mark.asyncio
async def test_invalid_metrics_unknown_and_thinking_not_persisted(server):
    server.chat.update(prompt_eval_count=True,eval_count=-1,load_duration='bad')
    r=await call(server)
    assert r.details['input_tokens'] is None and r.details['output_tokens'] is None and r.details['load_seconds'] is None
    assert PRIVATE not in json.dumps(r.details) and PRIVATE not in r.text

@pytest.mark.asyncio
async def test_real_engine_pack_to_local_to_check_reply(server,monkeypatch,tmp_path):
    from backend import error_handler,output_manager,run_history,configuration_manager
    from backend.run_service import RunService
    for module,field in ((error_handler,'RUN_ERRORS_DIR'),(output_manager,'RUN_OUTPUTS_DIR'),
                         (run_history,'RUN_HISTORY_DIR'),(configuration_manager,'SETTINGS_DIR')):
        monkeypatch.setattr(module,field,tmp_path/field)
    service=RunService.create()
    try:
        service.configuration.set('local_model_server_url',server.url)
        service.configuration.set('local_model_default_model',MODEL)
        wm=service.workflow_map;wm.create_new('Checked local answer')
        start=wm.add_node('start_node');pack=wm.add_node('context_pack_node')
        local=wm.add_node('ask_local_model_node');check=wm.add_node('check_reply_node');end=wm.add_node('end_node')
        wm.update_node_config(local,{**wm.get_node_data(local)['config'],'input':'Answer with ok true.',
            'context_source':'Upstream payload','reply_json':True,'details_vault_write':True,'details_vault_key':'usage'})
        wm.update_node_config(check,{**wm.get_node_data(check)['config'],'expected_fields':[{'id':'ok','name':'ok','kind':'boolean','required':True}],
            'vault_write':True,'vault_write_key':'checked'})
        wm.connect(start,'default',pack,'input');wm.connect(pack,'default',local,'context')
        wm.connect(local,'default',check,'input');wm.connect(check,'default',end,'input')
        await service.start();result=await service.wait()
        assert result.exit_code==0
        memory=service.master_state.memory_bank
        assert memory.read_persistent('checked')=={'ok':True}
        assert memory.read_persistent('usage')['model_digest']=='a'*64
        assert 'Context Pack' in server.calls[-1][1]['messages'][1]['content']
    finally:service.close()

@pytest.mark.asyncio
@pytest.mark.parametrize('limit,override,length,code',[
    (8000,'',8000,None),(8000,'',8001,'context_too_long'),
    (12000,'',10000,None),(8000,12000,10000,None),
    (20000,1000,1000,None),(20000,1000,1001,'context_too_long'),(200000,'',200000,None),
    (999,'',5,'settings_invalid'),(200001,'',5,'settings_invalid'),
    (8000,999,5,'invalid_config'),(8000,200001,5,'invalid_config'),
    (8000,True,5,'invalid_config'),(8000,1000.5,5,'invalid_config')])
async def test_context_limit_default_override_range_and_no_trimming(server,limit,override,length,code):
    node,ctx,done,errors=make(server,context_source='Configured',context='x'*length,context_limit=override)
    old=ctx.get_setting
    ctx.get_setting=lambda k:limit if k=='local_model_context_limit' else old(k)
    await node.execute(ctx)
    if code:
        assert not done and errors[0].code==code
        assert not server.calls
    else:
        assert not errors and done
        assert server.calls[-1][1]['messages'][1]['content'].endswith('x'*length)


@pytest.mark.asyncio
@pytest.mark.parametrize('limit',[8000,12000])
async def test_context_limit_total_question_boundary(server,limit):
    node,ctx,done,errors=make(server,input='x'*(limit+12000),context_limit=limit)
    await node.execute(ctx)
    assert not errors
    node,ctx,done,errors=make(server,input='x'*(limit+12001),context_limit=limit)
    await node.execute(ctx)
    assert errors[0].code=='text_too_long'


@pytest.mark.asyncio
@pytest.mark.parametrize('length,expected',[(1792,False),(1793,True)])
async def test_context_token_estimate_warns_without_blocking(server,length,expected):
    result=await call(server,question='x'*length,num_ctx=512,max_tokens=64)
    assert result.details['estimated_tokens']==length/4+64
    assert bool(result.details['warnings']) is expected
    assert result.details['num_ctx']==512
    assert len(server.calls)==3


def test_context_limit_blank_numeric_field():
    from backend.field_types import check_number
    schema=AskLocalModelNode.config_schema['context_limit']
    assert check_number(schema,'','')==('','')
    assert check_number(schema,'20000','')==(20000,'')
    assert check_number(schema,'999','')[1]
    assert check_number({'type':'integer'},'','')[1]  # no change to ordinary numeric fields

@pytest.mark.asyncio
async def test_token_warning_is_published_to_run_details_vault(server):
    node,ctx,done,errors=make(server,input='x'*1800,num_ctx=512,max_tokens=64,
        details_vault_write=True,details_vault_key='usage')
    await node.execute(ctx)
    assert done and not errors
    details=ctx.memory_bank.read_persistent('usage')
    assert details['estimated_tokens']==514 and details['warnings']
    assert 'x'*100 not in json.dumps(details)

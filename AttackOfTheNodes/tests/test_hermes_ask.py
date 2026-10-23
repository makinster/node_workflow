"""No provider calls: all success/error/cleanup cases use isolated fake workers."""
import asyncio
import copy
import json
import os
from pathlib import Path
import signal
import sys
import time

import pytest

from backend import persistence, hermes_folder
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_errors import NodeError
from backend.nodes.ai.hermes_ask_node import HermesAskNode
from backend.integrations import hermes_ask as service
from backend.integrations.hermes_worker import POLICY, PROTOCOL

SECRET = 'secret-for-unrelated-provider-never-record'


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, 'RUN_OUTPUTS_DIR', tmp_path / 'outputs')
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'hermes-home'))
    monkeypatch.setenv('UNRELATED_API_KEY', SECRET)
    events, done, errors = [], [], []
    memory = MemoryBank(EventBus())
    memory.store_persistent('question', 'Vault question', type_tag='string')
    settings = {'system_node_folders': str(tmp_path), 'hermes_allow_no_budget': True,
                'hermes_installation_folder': str(tmp_path / 'installation')}
    context = NodeContext(node_id='ask', branch_id='S1', run_id='run-test',
        inputs={'input': 'Upstream question'}, memory_bank=memory, signal_done=done.append,
        signal_error=errors.append, signal_waiting_for_input=lambda _: None,
        wait_for_nodes=lambda *_: None, wait_for_merge=lambda *_: None,
        get_setting=settings.get, publish_event=lambda name, data: events.append((name, data)))
    return context, settings, events, done, errors


def fake_worker(tmp_path, monkeypatch, program=None):
    worker = tmp_path / 'fake_worker.py'
    if program is None:
        program = '''import json,sys,os
request=json.load(sys.stdin)
print(json.dumps({'protocol':request['protocol'],'status':'ok','policy':request['policy'],
 'tool_calls':[],'turns':1,'answer':'A useful answer',
 'provider':'local','model':'configured','usage':{'input_tokens':12,'output_tokens':3,'estimated_cost_usd':None}}))
'''
    worker.write_text(program)
    broker = Path(service.__file__).with_name('hermes_process.py')
    # Change only the private worker argv in a disposable subprocess launcher.
    # Also accelerate H0 grace for tests; production timing has no env override.
    code = '''import runpy,sys
original=runpy.run_path
def loaded(path,*a,**k):
 m=original(path,*a,**k)
 if str(path).endswith('_aotn_run.py'):
  m['collect'].__globals__.update(GRACE=.2,CLEANUP_WAIT=.05)
 return m
runpy.run_path=loaded
m=original(sys.argv[1])
m['main'].__globals__['worker_command']=lambda _: [sys.executable,'-I','-S','-u',sys.argv[2]]
sys.exit(m['main']())
'''
    monkeypatch.setattr(service, 'broker_command', lambda: [sys.executable, '-I', '-S', '-u', '-c', code, str(broker), str(worker)])
    return worker


def node(context, folder, **config):
    return HermesAskNode('ask', {**HermesAskNode.default_config, 'input_source':'Configured',
                                'input':'Configured question', 'folder':str(folder), **config})


def read_record(events):
    assert events and events[-1][0] == service.USAGE_EVENT
    details = events[-1][1]
    path = Path(details['record']['path'])
    return details, path, [json.loads(line) for line in path.read_text().splitlines()]


@pytest.mark.asyncio
@pytest.mark.parametrize('source', ['Upstream payload','Vault','Configured'])
async def test_sources_forwarding_and_private_receipts(setup, tmp_path, monkeypatch, source):
    ctx, settings, events, done, errors = setup
    fake_worker(tmp_path, monkeypatch)
    incoming = {'original':['keep', 'identity']}
    if source != 'Upstream payload':
        ctx.inputs['input'] = incoming
    current = node(ctx, tmp_path, input_source=source, input_vault_key='question',
                   dead_drop_passthrough=True, transient_output=False,
                   vault_write=True, vault_write_key='answer',
                   details_vault_write=True, details_vault_key='usage')
    await current.execute(ctx)
    assert not errors and done[0]['data']['default'] is ctx.inputs['input']
    assert ctx.memory_bank.read_persistent('answer') == 'A useful answer'
    details, path, lines = read_record(events)
    assert ctx.memory_bank.read_persistent('usage') == details
    assert details['usage']['estimated_cost_usd'] is None
    assert details['usage']['cost_status'] == 'not_reported'
    assert details['cleanup_confirmed'] and details['tools'] == []
    assert [line['event'] for line in lines] == ['started','answer','finished']
    assert lines[0]['policy'] == POLICY
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert 'Configured question' not in path.read_text() and SECRET not in path.read_text()
    assert not list((persistence.RUN_OUTPUTS_DIR / '.ask-hermes-workers').iterdir())


@pytest.mark.asyncio
async def test_answer_and_usage_survive_disabled_vault_and_repeated_visits(setup, tmp_path, monkeypatch):
    ctx, _, events, done, errors = setup
    fake_worker(tmp_path, monkeypatch)
    current=node(ctx,tmp_path)
    await current.execute(ctx)
    await current.execute(ctx)
    assert not errors and len(done)==2
    assert done[0]['data']['default']=='A useful answer'
    assert len({data['invocation_id'] for _,data in events})==2
    assert ctx.memory_bank.read_persistent('answer') is None
    assert all(Path(data['record']['path']).exists() for _,data in events)
    raw=(tmp_path/'hermes-home/aotn/events.jsonl').read_text()
    assert raw.count('agent.ask_hermes.started')==2 and raw.count('agent.ask_hermes.completed')==2
    assert 'A useful answer' not in raw and SECRET not in raw


@pytest.mark.asyncio
@pytest.mark.parametrize('code', ['auth_failed','unsupported_runtime','agent_failed'])
async def test_safe_worker_error_without_secret_output(setup,tmp_path,monkeypatch,code):
    ctx, _, events, done, errors=setup
    fake_worker(tmp_path,monkeypatch,f'import json,sys; json.load(sys.stdin); sys.stderr.write({SECRET!r}); print(json.dumps({{"protocol":{PROTOCOL!r},"status":{code!r},"secret":{SECRET!r}}}))')
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code==code and not errors[0].retryable
    details,path,_=read_record(events)
    assert details['status']==code
    assert SECRET not in path.read_text() and SECRET not in str(errors[0].details)


@pytest.mark.asyncio
@pytest.mark.parametrize('raw', ['not json','[]','{}','{"protocol":"bad"}'])
async def test_bad_output_is_not_an_answer(setup,tmp_path,monkeypatch,raw):
    ctx, _, events, done, errors=setup
    fake_worker(tmp_path,monkeypatch,f'import sys; sys.stdin.read(); print({raw!r})')
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='invalid_response'
    assert read_record(events)[0]['status']=='invalid_response'


@pytest.mark.asyncio
@pytest.mark.parametrize('change,code', [({'tool_calls':[{'name':'shell','arguments':SECRET}]},'permission_denied'),
                                        ({'turns':2},'turn_limit'),({'policy':{}},'unsupported_runtime'),
                                        ({'usage':{'estimated_cost_usd':float('nan')}},'invalid_response'),
                                        ({'answer':'x'*(service.MAX_ANSWER+1)},'invalid_response')])
async def test_protocol_limits_checked_before_output(setup,tmp_path,monkeypatch,change,code):
    ctx, _, events, done, errors=setup
    program='''import json,sys
q=json.load(sys.stdin)
r={'protocol':q['protocol'],'status':'ok','policy':q['policy'],'tool_calls':[], 'turns':1,'answer':'ok','usage':{}}
'''+f'r.update({change!r})\nprint(json.dumps(r))'
    if 'nan' in program:
        program=program.replace('nan',"float('nan')")
    fake_worker(tmp_path,monkeypatch,program)
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code==code
    assert SECRET not in read_record(events)[1].read_text()


async def wait_pid(path):
    until=time.monotonic()+5
    while not path.exists() or not path.read_text():
        assert time.monotonic()<until
        await asyncio.sleep(.01)
    return int(path.read_text())


@pytest.mark.asyncio
@pytest.mark.parametrize('cancel', [False,True])
async def test_timeout_stop_and_detached_descendant_reaped(setup,tmp_path,monkeypatch,cancel):
    ctx, _, events, _, _=setup
    child=tmp_path/'descendant.pid'
    parent=tmp_path/'worker.pid'
    detached='import os,signal,time\nos.setsid()\nsignal.signal(signal.SIGINT,signal.SIG_IGN)\n'+f'open({str(child)!r},"w").write(str(os.getpid()))\ntime.sleep(60)'
    program='import sys,json,os,signal,subprocess,time\njson.load(sys.stdin)\nsignal.signal(signal.SIGINT,signal.SIG_IGN)\n'+f'open({str(parent)!r},"w").write(str(os.getpid()))\nsubprocess.Popen([sys.executable,"-c",{detached!r}])\ntime.sleep(60)'
    fake_worker(tmp_path,monkeypatch,program)
    task=asyncio.create_task(service.ask(ctx,'question',tmp_path,2 if not cancel else 10))
    pids=[await wait_pid(parent),await wait_pid(child)]
    if cancel:
        task.cancel()
        await asyncio.sleep(.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        with pytest.raises(NodeError) as exc:
            await task
        assert exc.value.code=='timed_out'
    assert all(not Path(f'/proc/{pid}').exists() for pid in pids)
    details,_,_=read_record(events)
    assert details['status']==('cancelled' if cancel else 'timed_out')
    assert details['cleanup_confirmed']


@pytest.mark.asyncio
async def test_natural_exit_still_reaps_detached_child(setup,tmp_path,monkeypatch):
    ctx,_,events,_,_=setup
    pidfile=tmp_path/'escaped'
    child='import os,time\nos.setsid()\n'+f'open({str(pidfile)!r},"w").write(str(os.getpid()))\ntime.sleep(60)'
    worker=f'import subprocess,sys,time\nsubprocess.Popen([sys.executable,"-c",{child!r}],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\ntime.sleep(.15)\n'
    worker+='import json\nq=json.load(sys.stdin)\nprint(json.dumps({"protocol":q["protocol"],"status":"auth_failed"}))'
    fake_worker(tmp_path,monkeypatch,worker)
    with pytest.raises(NodeError): await service.ask(ctx,'question',tmp_path,3)
    assert not Path(f'/proc/{await wait_pid(pidfile)}').exists()
    assert read_record(events)[0]['cleanup_confirmed']


@pytest.mark.asyncio
async def test_version_refused_before_import_or_inference(setup,tmp_path):
    ctx,settings,events,done,errors=setup
    root=Path(settings['hermes_installation_folder'])
    (root/'venv/bin').mkdir(parents=True)
    (root/'venv/bin/python').symlink_to(sys.executable)
    (root/'hermes_cli').mkdir()
    sentinel=tmp_path/'never-import'
    (root/'hermes_cli/__init__.py').write_text('__version__="0.14.0"\n'+f'open({str(sentinel)!r},"w").write("inference")\nraise RuntimeError("must never import")')
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='unsupported_runtime'
    assert str(errors[0])=="This Hermes version can't run with these limits."
    assert not sentinel.exists()
    assert read_record(events)[0]['status']=='unsupported_runtime'


@pytest.mark.asyncio
async def test_missing_installation_and_explicit_cost_gate(setup,tmp_path):
    ctx,settings,events,done,errors=setup
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[-1].code=='not_installed'
    settings['hermes_allow_no_budget']=False
    await node(ctx,tmp_path).execute(ctx)
    assert errors[-1].code=='node_error' and 'Options' in str(errors[-1])


@pytest.mark.asyncio
async def test_no_inference_when_intent_record_fails(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    monkeypatch.setattr(hermes_folder,'record_event',lambda **_: (_ for _ in ()).throw(OSError(SECRET)))
    monkeypatch.setattr(service,'broker_command',lambda: pytest.fail('must not spawn'))
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='record_failed' and SECRET not in str(errors[0])


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['outside','file','symlink','empty'])
async def test_folder_gate_before_worker(setup,tmp_path,monkeypatch,kind):
    ctx,settings,events,done,errors=setup
    monkeypatch.setattr(service,'broker_command',lambda: pytest.fail('must not spawn'))
    folder=tmp_path/'file'
    folder.write_text('x')
    if kind=='outside': folder=tmp_path.parent
    if kind=='empty': settings['system_node_folders']=''; folder=tmp_path
    if kind=='symlink':
        folder=tmp_path/'escape'; folder.symlink_to(tmp_path.parent,target_is_directory=True)
    await node(ctx,folder).execute(ctx)
    assert not done and errors[0].code==('folder_missing' if kind=='file' else 'not_allowed')


@pytest.mark.asyncio
async def test_abandoned_marker_blocks_new_paid_call(setup,tmp_path,monkeypatch):
    ctx,_,_,done,errors=setup
    markers=persistence.RUN_OUTPUTS_DIR/'.ask-hermes-workers'
    markers.mkdir(parents=True)
    (markers/'old.lock').write_text('cleanup unconfirmed')
    monkeypatch.setattr(service,'broker_command',lambda: pytest.fail('must not spawn'))
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='cleanup_failed'


@pytest.mark.asyncio
async def test_known_secrets_redacted_from_answer_and_records(setup,tmp_path,monkeypatch):
    from backend.secrets_manager import SecretsManager
    ctx,_,events,done,errors=setup
    ctx.secrets_manager=SecretsManager(tmp_path/'secrets')
    ctx.secrets_manager.set_secret('private',SECRET)
    fake_worker(tmp_path,monkeypatch,f'''import json,sys,os
q=json.load(sys.stdin)
assert 'UNRELATED_API_KEY' not in os.environ
assert os.getcwd()==q['folder']
print(json.dumps({{'protocol':q['protocol'],'status':'ok','policy':q['policy'], 'tool_calls':[], 'turns':1,'answer':{SECRET!r},'usage':{{}}}}))
''')
    await node(ctx,tmp_path).execute(ctx)
    assert not errors and done[0]['data']['default']=='[redacted]'
    assert SECRET not in read_record(events)[1].read_text()


@pytest.mark.asyncio
@pytest.mark.parametrize('config,code', [({'input':'x'*20001},'text_too_long'),
    ({'input_source':'Upstream payload'},'node_error'),
    ({'vault_write':True,'vault_write_key':''},'node_error'),
    ({'vault_write':True,'vault_write_key':'same','details_vault_write':True,'details_vault_key':'same'},'node_error')])
async def test_preflight_before_process(setup,tmp_path,monkeypatch,config,code):
    ctx,_,_,done,errors=setup
    ctx.inputs['input']={'not':'text'}
    monkeypatch.setattr(service,'broker_command',lambda:pytest.fail('must not spawn'))
    await node(ctx,tmp_path,**config).execute(ctx)
    assert not done and errors[0].code==code


@pytest.mark.asyncio
async def test_output_flood_is_bounded_and_reaped(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch,'import sys; sys.stdin.read(); sys.stdout.write("x"*2000000); sys.stdout.flush()')
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='invalid_response'
    assert read_record(events)[0]['cleanup_confirmed']


@pytest.mark.asyncio
async def test_record_cap_reserves_terminal_event(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    monkeypatch.setattr(service,'MAX_RECORD',1500)
    fake_worker(tmp_path,monkeypatch,'''import sys,json
q=json.load(sys.stdin)
print(json.dumps({'protocol':q['protocol'],'status':'ok','policy':q['policy'],'tool_calls':[], 'turns':1,'answer':'x'*2000,'usage':{}}))''')
    await node(ctx,tmp_path).execute(ctx)
    details,path,lines=read_record(events)
    assert not done and errors[0].code=='record_failed'
    assert details['status']=='record_failed' and lines[-1]['event']=='record_failed'
    assert path.stat().st_size<=service.MAX_RECORD+service.FINAL_RESERVE


@pytest.mark.asyncio
@pytest.mark.parametrize('fail',[False,True])
async def test_usage_in_run_result_history_and_built_execution_screen(setup,tmp_path,monkeypatch,fail):
    from backend import configuration_manager,error_handler,output_manager,run_history
    from backend.run_service import RunService
    from backend.run_policies import TerminatePolicy
    from frontend.app import AttackOfTheNodesApp
    from frontend.screens.execution import ExecutionScreen
    for module,name in [(configuration_manager,'SETTINGS_DIR'),(error_handler,'RUN_ERRORS_DIR'),
                        (output_manager,'RUN_OUTPUTS_DIR'),(run_history,'RUN_HISTORY_DIR')]:
        monkeypatch.setattr(module,name,tmp_path/name)
    if fail:
        fake_worker(tmp_path,monkeypatch,f'import json,sys; json.load(sys.stdin); print(json.dumps({{"protocol":{PROTOCOL!r},"status":"auth_failed"}}))')
    else:
        fake_worker(tmp_path,monkeypatch)
    runner=RunService.create()
    for key,value in setup[1].items(): runner.configuration.set(key,value)
    wm=runner.workflow_map
    wm.create_new('Ask test')
    start=wm.add_node('start_node')
    ask=wm.add_node('hermes_ask_node')
    end=wm.add_node('end_node')
    wm.update_node_config(ask,node(setup[0],tmp_path).config)
    wm.connect(start,'default',ask,'input'); wm.connect(ask,'default',end,'input')
    app=AttackOfTheNodesApp(runner.event_bus,wm._factory,wm,runner.master_state._memory_bank,runner.master_state)
    async with app.run_test(size=(100,32)) as pilot:
        screen=ExecutionScreen(wm,runner.master_state._memory_bank,runner.master_state)
        await app.switch_screen(screen)
        await runner.start(recovery_policy=TerminatePolicy('terminate_workflow'))
        result=await runner.wait()
        await pilot.pause()
        assert len(result.agent_usage)==1
        details=result.agent_usage[0]
        assert details['status']==('auth_failed' if fail else 'completed')
        assert result.to_dict()['agent_usage']==runner.master_state.agent_usage
        saved=json.loads((tmp_path/'RUN_HISTORY_DIR'/f'{result.run_id}.json').read_text())
        assert saved['agent_usage']==result.agent_usage
        assert saved['agent_usage_summary']==result.to_dict()['agent_usage_summary']
        assert saved['agent_usage_summary']['not_reported']==1
        assert saved['agent_usage_summary']['partial']==int(fail)
        text=screen._node_details({'node_id':ask,'depth':1}).plain
        assert 'Agent usage' in text and 'Cost not reported' in text and 'Record:' in text
        assert ('Tokens not reported' if fail else 'Tokens 15') in text
        assert not runner.master_state._memory_bank.read_persistent('usage')
        json.dumps(result.to_dict(),allow_nan=False)


def test_totals_preserve_missing_and_partial_costs():
    from backend.agent_usage import usage_summary
    assert usage_summary([{'usage':{'estimated_cost_usd':.12}},
                          {'usage':{'estimated_cost_usd':None},'partial':True}]) == {
        'estimated_cost_usd':.12,'reported':1,'not_reported':1,'partial':1}


@pytest.mark.asyncio
async def test_unconfirmed_cleanup_keeps_ownership_and_blocks_next_call(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    command=[sys.executable,'-I','-S','-c','import sys; sys.stdin.read(); print(\'{"status":"cleanup_failed","cleanup_confirmed":false}\')']
    monkeypatch.setattr(service,'broker_command',lambda:command)
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[-1].code=='cleanup_failed'
    assert not read_record(events)[0]['cleanup_confirmed']
    assert list((persistence.RUN_OUTPUTS_DIR/'.ask-hermes-workers').iterdir())
    monkeypatch.setattr(service,'broker_command',lambda:pytest.fail('must not spawn'))
    await node(ctx,tmp_path).execute(ctx)
    assert errors[-1].code=='cleanup_failed'

"""Public CLI integration; fake executables only, no provider calls."""
import asyncio
import json
import os
from pathlib import Path
import shutil
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
from backend.integrations.hermes_worker import POLICY, TOOLSETS, parse_tools, parse_answer

SECRET = 'secret-for-unrelated-provider-never-record'
TOOLS = 'Built-in toolsets (cli):\n'+''.join(f'  ✗ disabled  {name}  Test toolset\n' for name in sorted(TOOLSETS))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, 'RUN_OUTPUTS_DIR', tmp_path / 'outputs')
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'sticky-default'))
    monkeypatch.setenv('UNRELATED_API_KEY', SECRET)
    profile=tmp_path/'profile';profile.mkdir();(profile/'config.yaml').write_text('# isolated test profile\n')
    events, done, errors = [], [], []
    memory = MemoryBank(EventBus())
    memory.store_persistent('question', 'Vault question', type_tag='string')
    settings = {'system_node_folders': str(tmp_path), 'hermes_allow_no_budget': True,
                'hermes_profile_home':str(profile),'hermes_command':str(tmp_path/'fake_hermes')}
    context = NodeContext(node_id='ask', branch_id='S1', run_id='run-test',
        inputs={'input': 'Upstream question'}, memory_bank=memory, signal_done=done.append,
        signal_error=errors.append, signal_waiting_for_input=lambda _: None,
        wait_for_nodes=lambda *_: None, wait_for_merge=lambda *_: None,
        get_setting=settings.get, publish_event=lambda name, data: events.append((name, data)))
    return context, settings, events, done, errors


def fake_worker(tmp_path, monkeypatch, program=None):
    """A fake public Hermes executable, with the real broker/collector path."""
    profile=tmp_path/'profile';profile.mkdir(exist_ok=True)
    (profile/'config.yaml').write_text('# isolated test profile\n')
    (tmp_path/'tools.txt').write_text(TOOLS)
    command=tmp_path/'fake_hermes'
    program=program or "print('A useful answer');print('session_id: test-session',file=sys.stderr)"
    command.write_text(f'#!{sys.executable}\n'+f'''import os,sys,json
from pathlib import Path
assert os.environ['HERMES_HOME']=={str(profile)!r}
assert 'UNRELATED_API_KEY' not in os.environ
with open({str(tmp_path/'calls.jsonl')!r},'a') as log: log.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1:]==['tools','list','--platform','cli']:
 sys.stdout.write(Path({str(tmp_path/'tools.txt')!r}).read_text());sys.exit(0)
assert sys.argv[1]=='chat'
assert sys.argv[-6:]==['-Q','--source','tool','--max-turns','1','--ignore-rules']
'''+program+'\n')
    command.chmod(0o755)
    broker=Path(service.__file__).with_name('hermes_process.py')
    # Accelerated cleanup only in this disposable test launcher, no production
    # environment or workflow option bypasses the real limits.
    code='''import runpy,sys
original=runpy.run_path
def loaded(path,*a,**k):
 m=original(path,*a,**k)
 if str(path).endswith('_aotn_run.py'):
  m['collect'].__globals__.update(GRACE=.2,CLEANUP_WAIT=.05)
 return m
runpy.run_path=loaded
m=original(sys.argv[1]);sys.exit(m['main']())
'''
    monkeypatch.setattr(service,'broker_command',lambda:[sys.executable,'-I','-S','-u','-c',code,str(broker)])
    return command


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
async def test_sources_forwarding_and_private_receipts(setup,tmp_path,monkeypatch,source):
    ctx,settings,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch)
    if source!='Upstream payload': ctx.inputs['input']={'original':['keep','identity']}
    await node(ctx,tmp_path,input_source=source,input_vault_key='question',
        dead_drop_passthrough=True,transient_output=False,vault_write=True,vault_write_key='answer',
        details_vault_write=True,details_vault_key='usage').execute(ctx)
    assert not errors and done[0]['data']['default'] is ctx.inputs['input']
    assert ctx.memory_bank.read_persistent('answer')=='A useful answer'
    details,path,lines=read_record(events)
    assert ctx.memory_bank.read_persistent('usage')==details
    assert details['usage']['estimated_cost_usd'] is None and details['turns'] is None
    assert details['usage']['cost_status']=='not_reported'
    assert details['cleanup_confirmed'] and details['tools']==[]
    assert [line['event'] for line in lines]==['started','answer','finished']
    assert lines[0]['policy']==POLICY
    assert path.stat().st_mode & 0o777==0o600 and path.parent.stat().st_mode & 0o777==0o700
    assert 'Configured question' not in path.read_text() and SECRET not in path.read_text()
    assert not list((persistence.RUN_OUTPUTS_DIR/'.ask-hermes-workers').iterdir())
    assert os.environ['HERMES_HOME']==str(tmp_path/'sticky-default')


@pytest.mark.asyncio
async def test_preflight_every_time_even_with_same_config_mtime(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch)
    await node(ctx,tmp_path).execute(ctx)
    assert done and not errors
    (tmp_path/'tools.txt').write_text(TOOLS.replace('✗ disabled  web','✓ enabled   web'))
    await node(ctx,tmp_path).execute(ctx)
    assert len(done)==1 and errors[0].code=='permission_denied'
    assert str(errors[0])=='This Hermes profile has tools turned on.'
    calls=[json.loads(line) for line in (tmp_path/'calls.jsonl').read_text().splitlines()]
    assert [call[0] for call in calls]==['tools','chat','tools']
    assert len({data['invocation_id'] for _,data in events})==2
    assert ctx.memory_bank.read_persistent('answer') is None
    receipts=(tmp_path/'sticky-default/aotn/events.jsonl').read_text()
    assert receipts.count('agent.ask_hermes.started')==2
    assert receipts.count('agent.ask_hermes.completed')==1
    assert receipts.count('agent.ask_hermes.permission_denied')==1
    assert 'A useful answer' not in receipts and SECRET not in receipts


@pytest.mark.parametrize('listing', [TOOLS.replace('✗ disabled','✓ enabled',1),
    TOOLS+'unknown output\n',TOOLS.rsplit('\n',2)[0],TOOLS+TOOLS.splitlines()[1]+'\n',
    'Built-in toolsets (telegram):\n'+TOOLS.split('\n',1)[1],TOOLS.replace('web  Test','new_tool  Test')])
@pytest.mark.asyncio
async def test_tools_enabled_unknown_or_incomplete_refuses_before_chat(setup,tmp_path,monkeypatch,listing):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch)
    (tmp_path/'tools.txt').write_text(listing)
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='permission_denied'
    assert all(json.loads(line)[0]=='tools' for line in (tmp_path/'calls.jsonl').read_text().splitlines())


@pytest.mark.asyncio
@pytest.mark.parametrize('code,program', [('auth_failed',"print('Error: token expired (401)',file=sys.stderr);sys.exit(1)"),
    ('agent_failed',"print('backend failed',file=sys.stderr);sys.exit(1)"),
    ('auth_failed',"print('Error: please login',file=sys.stderr)")])
async def test_safe_cli_errors(setup,tmp_path,monkeypatch,code,program):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch,f'print({SECRET!r},file=sys.stderr);'+program)
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code==code and not errors[0].retryable
    if code=='auth_failed': assert str(errors[0])=='Sign in to Hermes (aotn profile)'
    assert SECRET not in read_record(events)[1].read_text() and SECRET not in str(errors[0].details)


@pytest.mark.parametrize('raw,expected', [(b'  A useful answer\n\nsession_id: test-session\n','A useful answer'),
    (b'session_id: test-session\nHello\n','Hello'),(b'line one\nline two\n','line one\nline two'),
    (b'401 is an HTTP status code\n','401 is an HTTP status code')])
def test_answer_parser(raw,expected): assert parse_answer(raw)==expected


@pytest.mark.asyncio
@pytest.mark.parametrize('raw', [b'',b'session_id: test-session\n',b'\xff',b'hello\x00world',
    b'session_id: ???\n',b'Error: backend failed',b'x'*(service.MAX_ANSWER+1)])
async def test_empty_unparseable_or_oversized_output(setup,tmp_path,monkeypatch,raw):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch,f'sys.stdout.buffer.write({raw!r})')
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='invalid_response'


@pytest.mark.asyncio
@pytest.mark.parametrize('receipt',['Session: private-session','session_id: private-session',
    'Session ID: private-session','  \x1b[2mSession: private-session\x1b[0m'])
async def test_embedded_session_receipt_never_becomes_answer(setup,tmp_path,monkeypatch,receipt):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch,f'print("answer one\\n"+{receipt!r}+"\\nanswer two")')
    await node(ctx,tmp_path,vault_write=True,vault_write_key='answer').execute(ctx)
    assert not done and errors[0].code=='invalid_response'
    assert ctx.memory_bank.read_persistent('answer') is None
    assert 'private-session' not in read_record(events)[1].read_text()


async def wait_pid(path):
    until=time.monotonic()+5
    while not path.exists() or not path.read_text():
        assert time.monotonic()<until
        await asyncio.sleep(.01)
    return int(path.read_text())


@pytest.mark.asyncio
@pytest.mark.parametrize('cancel',[False,True])
@pytest.mark.parametrize('phase',['tools','chat'])
async def test_timeout_stop_and_detached_descendant_reaped(setup,tmp_path,monkeypatch,cancel,phase):
    ctx,_,events,_,_=setup
    child=tmp_path/'descendant.pid';parent=tmp_path/'worker.pid'
    detached='import os,signal,time\nos.setsid()\nsignal.signal(signal.SIGINT,signal.SIG_IGN)\n'+f'open({str(child)!r},"w").write(str(os.getpid()))\ntime.sleep(60)'
    program='import signal,subprocess,time\nsignal.signal(signal.SIGINT,signal.SIG_IGN)\n'+f'open({str(parent)!r},"w").write(str(os.getpid()))\nsubprocess.Popen([sys.executable,"-c",{detached!r}])\ntime.sleep(60)'
    command=fake_worker(tmp_path,monkeypatch,program)
    if phase=='tools':
        source=command.read_text().replace("if sys.argv[1:]==['tools','list','--platform','cli']:\n",
            "if sys.argv[1:]==['tools','list','--platform','cli']:\n"+'\n'.join(' '+line for line in program.splitlines())+'\n')
        command.write_text(source)
    task=asyncio.create_task(service.ask(ctx,'question',tmp_path,2 if not cancel else 10))
    pids=[await wait_pid(parent),await wait_pid(child)]
    if cancel:
        task.cancel();await asyncio.sleep(.02);task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    else:
        with pytest.raises(NodeError) as exc: await task
        assert exc.value.code=='timed_out'
    assert all(not Path(f'/proc/{pid}').exists() for pid in pids)
    details,_,_=read_record(events)
    assert details['status']==('cancelled' if cancel else 'timed_out') and details['cleanup_confirmed']


@pytest.mark.asyncio
async def test_natural_exit_still_reaps_detached_child(setup,tmp_path,monkeypatch):
    ctx,_,events,_,_=setup
    pidfile=tmp_path/'escaped'
    child='import os,time\nos.setsid()\n'+f'open({str(pidfile)!r},"w").write(str(os.getpid()))\ntime.sleep(60)'
    program=f'import subprocess,time\nsubprocess.Popen([sys.executable,"-c",{child!r}],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\ntime.sleep(.15)\nprint("A useful answer")'
    fake_worker(tmp_path,monkeypatch,program)
    await node(ctx,tmp_path).execute(ctx)
    assert not Path(f'/proc/{await wait_pid(pidfile)}').exists()
    assert read_record(events)[0]['cleanup_confirmed']


@pytest.mark.asyncio
async def test_question_literal_argv_folder_and_command_without_path(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    command=fake_worker(tmp_path,monkeypatch,f'assert os.getcwd()=={str(tmp_path)!r};print("ok")')
    question='say \"hello\"; $(touch NEVER)\n--toolsets terminal'
    monkeypatch.setenv('PATH','/usr/bin:/bin')
    await node(ctx,tmp_path,input=question).execute(ctx)
    assert not errors and done[0]['data']['default']=='ok' and not (tmp_path/'NEVER').exists()
    calls=[json.loads(line) for line in (tmp_path/'calls.jsonl').read_text().splitlines()]
    assert calls[1]==['chat','--query='+question,'-Q','--source','tool','--max-turns','1','--ignore-rules']


# Mirrors installed Hermes: an early --profile/-p scan over every argv element
# (before argparse), then the chat subparser's -q/--query option.
HERMES_PARSERS = '''
import argparse
for i,arg in enumerate(sys.argv[1:]):
 if arg in {'--profile','-p'} and i+2<len(sys.argv) or arg.startswith('--profile='):
  print('profile switched');sys.exit(0)
p=argparse.ArgumentParser();p.add_argument('chat');p.add_argument('-q','--query')
p.add_argument('-Q',action='store_true');p.add_argument('--source');p.add_argument('--max-turns')
p.add_argument('--ignore-rules',action='store_true')
print(p.parse_args().query)
'''


@pytest.mark.asyncio
@pytest.mark.parametrize('question',['--profile=default','--profile default','-p default','--model=x',
    '-p','--profile','-Q','What is 2+2?','line one\n--toolsets terminal'])
async def test_option_shaped_question_stays_question_text_in_aotn_profile(setup,tmp_path,monkeypatch,question):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch,HERMES_PARSERS)
    await node(ctx,tmp_path,input=question).execute(ctx)
    assert not errors and done[0]['data']['default']==question


@pytest.mark.asyncio
@pytest.mark.parametrize('missing',['profile','config','command','executable'])
async def test_missing_profile_or_command(setup,tmp_path,monkeypatch,missing):
    ctx,settings,events,done,errors=setup
    command=fake_worker(tmp_path,monkeypatch)
    if missing=='profile': shutil.rmtree(Path(settings['hermes_profile_home']))
    elif missing=='config': (Path(settings['hermes_profile_home'])/'config.yaml').unlink()
    elif missing=='command': command.unlink()
    else: command.chmod(0o644)
    await node(ctx,tmp_path).execute(ctx)
    assert not done
    assert errors[0].code==('profile_missing' if missing in ('profile','config') else 'not_installed')
    assert str(errors[0])==('Set up the aotn Hermes profile first' if missing in ('profile','config') else 'Hermes is not installed')
    assert not (tmp_path/'calls.jsonl').exists()


@pytest.mark.asyncio
async def test_explicit_cost_gate(setup,tmp_path,monkeypatch):
    ctx,settings,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch)
    settings['hermes_allow_no_budget']=False
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='node_error' and 'Options' in str(errors[0])
    assert not (tmp_path/'calls.jsonl').exists()


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
    fake_worker(tmp_path,monkeypatch,f'print({SECRET!r})')
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
    fake_worker(tmp_path,monkeypatch,'sys.stdout.write("x"*2000000); sys.stdout.flush()')
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[0].code=='invalid_response'
    assert read_record(events)[0]['cleanup_confirmed']


@pytest.mark.asyncio
async def test_record_cap_reserves_terminal_event(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    monkeypatch.setattr(service,'MAX_RECORD',1500)
    fake_worker(tmp_path,monkeypatch,"print('x'*2000)")
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
        fake_worker(tmp_path,monkeypatch,"print('Error: login expired',file=sys.stderr);sys.exit(1)")
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
        assert 'Tokens not reported' in text
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


@pytest.mark.asyncio
async def test_changed_config_or_unknown_diagnostics_refuse(setup,tmp_path,monkeypatch):
    ctx,_,_,done,errors=setup
    command=fake_worker(tmp_path,monkeypatch)
    source=command.read_text()
    command.write_text(source.replace(' sys.stdout.write('," Path("+repr(str(tmp_path/'profile/config.yaml'))+").write_text('changed');sys.stdout.write("))
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[-1].code=='permission_denied'
    command.write_text(source.replace(' sys.stdout.write('," print('unknown warning',file=sys.stderr);sys.stdout.write("))
    await node(ctx,tmp_path).execute(ctx)
    assert not done and errors[-1].code=='permission_denied'


def test_coloured_tools_listing_is_classified():
    parse_tools(('\x1b[32m'+TOOLS+'\x1b[0m').encode())


@pytest.mark.asyncio
@pytest.mark.parametrize('character',['x','😀'])
async def test_exact_question_cap_is_accepted(setup,tmp_path,monkeypatch,character):
    ctx,_,_,done,errors=setup
    fake_worker(tmp_path,monkeypatch,'print(len(sys.argv[2].removeprefix("--query=")))')
    await node(ctx,tmp_path,input=character*service.MAX_QUESTION).execute(ctx)
    assert not errors and done[0]['data']['default']==str(service.MAX_QUESTION)


def test_answer_cap_applies_after_cli_newline_and_session_metadata():
    answer='x'*service.MAX_ANSWER
    assert parse_answer((answer+'\nsession_id: test-session\n').encode())==answer
    with pytest.raises(ValueError): parse_answer((answer+'x\n').encode())


@pytest.mark.asyncio
async def test_invalid_unicode_does_not_leave_a_broker_or_start_chat(setup,tmp_path,monkeypatch):
    ctx,_,events,done,errors=setup
    fake_worker(tmp_path,monkeypatch)
    await node(ctx,tmp_path,input='\ud800').execute(ctx)
    assert not done and errors[0].code=='agent_failed'
    assert read_record(events)[0]['cleanup_confirmed']
    assert not list((persistence.RUN_OUTPUTS_DIR/'.ask-hermes-workers').iterdir())
    calls=[json.loads(line)[0] for line in (tmp_path/'calls.jsonl').read_text().splitlines()]
    assert calls==['tools']

"""C3c filesystem protocol and real subprocesses; never real Hermes/model calls."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from tests.credential_cases import CREDENTIAL_CASES

from backend import hermes_investigations as inbox, hermes_folder
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_errors import NodeError
from backend.nodes.io.hermes_investigate_node import HermesInvestigateNode
from backend.nodes.io.hermes_investigation_result_node import HermesInvestigationResultNode
from backend.integrations import hermes_investigate as bridge
from backend.integrations.hermes_worker import TOOLSETS
from backend.secrets_manager import SecretsManager

APP=Path(__file__).resolve().parents[1]
INSTALL=APP/'integrations/hermes/install.sh'
TOOLS='Built-in toolsets (cli):\n'+''.join(f'  ✗ disabled  {t}  Test toolset\n' for t in sorted(TOOLSETS))
SECRET='private-value-for-test-only'


@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setenv('HERMES_HOME',str(tmp_path/'hermes'))
    monkeypatch.setenv('UNRELATED_API_KEY',SECRET)
    profile=tmp_path/'profile';profile.mkdir();(profile/'config.yaml').write_text('# fake profile')
    settings={inbox.DAILY_SETTING:5,inbox.PROFILE_SETTING:str(profile),'hermes_command':str(tmp_path/'fake-hermes')}
    done,errors=[],[]
    ctx=NodeContext('incident','branch','run',{},MemoryBank(EventBus()),done.append,errors.append,
        lambda _:None,lambda *_:None,lambda *_:None,get_setting=settings.get,
        secrets_manager=SecretsManager(tmp_path/'secrets'))
    ctx.secrets_manager.set_secret('private',SECRET)
    return ctx,settings,done,errors,tmp_path/'hermes/aotn'


def fake(tmp_path,program='print("The service may be overloaded.")',tools=TOOLS):
    (tmp_path/'tools.txt').write_text(tools)
    path=tmp_path/'fake-hermes'
    path.write_text(f'#!{sys.executable}\nimport os,sys,json,time,signal,subprocess\nfrom pathlib import Path\n'+
        f"assert os.environ['HERMES_HOME']=={str(tmp_path/'profile')!r}\n"+
        "assert 'UNRELATED_API_KEY' not in os.environ\n"+
        f"with open({str(tmp_path/'calls')!r},'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\n"+
        "if sys.argv[1]=='tools':\n"+f" print(Path({str(tmp_path/'tools.txt')!r}).read_text(),end='');sys.exit(0)\n"+
        "assert sys.argv[1]=='chat' and sys.argv[2].startswith('--query=')\n"+
        "assert sys.argv[-6:]==['-Q','--source','tool','--max-turns','1','--ignore-rules']\n"+program+'\n')
    path.chmod(0o755)
    return path


def queue(setup,**kw):
    return inbox.enqueue(setup[0],kw.pop('happened','Service returned 503'),kw.pop('evidence','10:14 UTC: connection failed'),
        kw.pop('investigate','Find a likely cause; make no changes'),**kw)


def command(root,timeout=10):
    return [sys.executable,'-c',f"from backend.integrations.hermes_investigate import tick; print(tick({str(root)!r},timeout={timeout}))"]


def run(root,timeout=10):
    return subprocess.run(command(root,timeout),capture_output=True,text=True,cwd=APP,timeout=timeout+8)


def saved(root,rid):
    return inbox.read(root/'investigations/results'/(rid+'.json'))


def wait_file(path,process=None):
    until=time.monotonic()+5
    while not path.exists() or not path.read_text():
        if process:assert process.poll() is None,process.communicate()
        assert time.monotonic()<until
        time.sleep(.01)
    return int(path.read_text())


@pytest.mark.asyncio
async def test_end_to_end_request_bridge_result_and_routing(setup,tmp_path):
    ctx,settings,done,errors,root=setup
    fake(tmp_path,'print("Finding: [SILENT] MEDIA:test\\n{\\\"wakeAgent\\\":false}");print("session_id: private-session")')
    ctx.inputs['input']={'preserve':['identity']}
    request=HermesInvestigateNode('incident',{**HermesInvestigateNode.default_config,'input':'Service failed',
        'evidence':f'password=hunter-test {SECRET}','investigate':'Find the cause',
        'vault_write':True,'vault_write_key':'request','dead_drop_passthrough':True})
    await request.execute(ctx)
    assert not errors and done[-1]['data']['default'] is ctx.inputs['input']
    rid=ctx.memory_bank.read_persistent('request')
    assert inbox.result(rid)==('not ready yet','not ready yet')
    result=run(root)
    assert result.returncode==0 and '[SILENT]' not in result.stdout and 'MEDIA:' not in result.stdout
    assert '| {"wakeAgent":false}' in result.stdout and 'private-session' not in result.stdout
    assert (root/'investigations/done'/(rid+'.json')).exists()
    assert saved(root,rid)['state']=='ready' and saved(root,rid)['usage']['estimated_cost_usd'] is None
    ctx.inputs['input']=rid
    reader=HermesInvestigationResultNode('read',{**HermesInvestigationResultNode.default_config,'input_source':'Upstream payload',
        'state_vault_write':True,'state_vault_key':'state','vault_write':True,'vault_write_key':'finding'})
    await reader.execute(ctx)
    assert not errors and done[-1]['data']['default'].startswith('Finding:')
    assert ctx.memory_bank.read_persistent('state')=='ready'
    assert ctx.memory_bank.read_persistent('finding')==done[-1]['data']['default']
    calls=[json.loads(s) for s in (tmp_path/'calls').read_text().splitlines()]
    assert [c[0] for c in calls]==['tools','chat']
    assert 'BEGIN UNTRUSTED EVIDENCE JSON' in calls[1][1] and SECRET not in calls[1][1]
    assert run(root).stdout.strip()==bridge.GATE


@pytest.mark.parametrize('program,tools,status',[
    ('print("should never chat")',TOOLS.replace('✗ disabled','✓ enabled',1),'permission_denied'),
    ('print("session_id: only-metadata")',TOOLS,'invalid_response'),
    ('print("Error: token expired (401)",file=sys.stderr);sys.exit(1)',TOOLS,'auth_failed'),
    ('print("answer1\\nsession_id: embedded\\nanswer2")',TOOLS,'invalid_response'),
    ('print("x"*12001)',TOOLS,'invalid_response'),
    ('print("ok")',TOOLS+'MCP enabled: surprise\n','permission_denied')])
def test_fake_failures_never_leak_and_no_retry(setup,tmp_path,program,tools,status):
    root=setup[-1];fake(tmp_path,program,tools);rid=queue(setup)
    result=run(root)
    record=saved(root,rid)
    assert result.returncode==0 and record['failure']['code']==status
    assert inbox.result(rid,root)==('failed','failed')
    assert (root/'investigations/failed'/(rid+'.json')).exists()
    assert SECRET not in result.stdout+json.dumps(record)
    if status=='permission_denied':assert all(json.loads(s)[0]=='tools' for s in (tmp_path/'calls').read_text().splitlines())
    calls=(tmp_path/'calls').read_text();assert run(root).stdout.strip()==bridge.GATE
    assert (tmp_path/'calls').read_text()==calls


@pytest.mark.parametrize('cancel',[False,True])
def test_deadline_and_stop_kill_reap_detached_descendants(setup,tmp_path,cancel):
    root=setup[-1]
    child=tmp_path/'child.pid';parent=tmp_path/'parent.pid'
    detached=f'import os,signal,time;os.setsid();signal.signal(signal.SIGINT,signal.SIG_IGN);open({str(child)!r},"w").write(str(os.getpid()));time.sleep(60)'
    program=f'signal.signal(signal.SIGINT,signal.SIG_IGN)\nPath({str(parent)!r}).write_text(str(os.getpid()))\nsubprocess.Popen([sys.executable,"-c",{detached!r}])\ntime.sleep(60)'
    fake(tmp_path,program);rid=queue(setup)
    started=time.monotonic()
    proc=subprocess.Popen(command(root,15 if cancel else 7),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=APP)
    pids=[wait_file(parent,proc),wait_file(child,proc)]
    if cancel:proc.send_signal(signal.SIGTERM)
    out,err=proc.communicate(timeout=10)
    assert proc.returncode==0 and time.monotonic()-started<9
    assert all(not Path(f'/proc/{pid}').exists() for pid in pids)
    record=saved(root,rid)
    assert record['cleanup_confirmed'] and record['failure']['code']==('cancelled' if cancel else 'timed_out')
    assert not (root/'investigations/cleanup-required.json').exists()


def test_two_bridge_claim_race_runs_exactly_once(setup,tmp_path):
    root=setup[-1];fake(tmp_path,'time.sleep(.5);print("One finding")');rid=queue(setup)
    ps=[subprocess.Popen(command(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=APP) for _ in range(2)]
    outputs=[p.communicate(timeout=15)[0].strip() for p in ps]
    assert sum(o==bridge.GATE for o in outputs)==1
    assert sum('One finding' in o for o in outputs)==1
    calls=[json.loads(s)[0] for s in (tmp_path/'calls').read_text().splitlines()]
    assert calls==['tools','chat'] and saved(root,rid)['state']=='ready'
    assert len(list((root/'investigations/attempts').iterdir()))==1


def test_repeat_window_daily_cap_and_original_id(setup,monkeypatch):
    ctx,settings,_,_,root=setup
    settings[inbox.DAILY_SETTING]=1
    rid=queue(setup,repeat_key='service:down')
    assert queue(setup,repeat_key='service:down')==rid
    with pytest.raises(NodeError,match='daily') as exc:queue(setup,repeat_key='another')
    assert exc.value.code=='daily_limit'
    old=inbox.read(root/'investigations/pending'/(rid+'.json'));old['queued_at']='2099-01-01T00:00:00Z'
    inbox.atomic(root/'investigations/pending'/(rid+'.json'),old)
    assert queue(setup,repeat_key='service:down')!=rid  # future timestamp cannot suppress
    settings[inbox.DAILY_SETTING]=0
    with pytest.raises(NodeError) as exc:queue(setup,repeat_key='new')
    assert exc.value.code=='daily_limit'


def test_no_repeat_when_zero_and_start_cap_across_days(setup,tmp_path):
    root=setup[-1];fake(tmp_path)
    first=queue(setup,minutes=0);second=queue(setup,minutes=0)
    assert first!=second
    policy=inbox.read(root/'investigations/policy.json');policy['daily_limit']=1
    inbox.atomic(root/'investigations/policy.json',policy)
    assert 'Investigation' in run(root).stdout
    assert run(root).stdout.strip()==bridge.GATE
    assert len(list((root/'investigations/pending').iterdir()))==1
    assert len((tmp_path/'calls').read_text().splitlines())==2


@pytest.mark.parametrize('phase,reboot,blocked',[('claimed',False,False),('launching',False,True),('launching',True,False)])
def test_stale_lease_fails_without_retry_or_blocks(setup,tmp_path,phase,reboot,blocked):
    root=setup[-1];fake(tmp_path);rid=queue(setup);base=root/'investigations'
    lease=dict(schema_version=1,request_id=rid,attempt_id='a_test',claimed_at='2026-01-01T00:00:00Z',
        claimed_epoch=time.time()-600,boot_id='old-boot' if reboot else bridge.boot_id(),phase=phase,cleanup_confirmed=False)
    inbox.atomic(base/'leases'/(rid+'.json'),lease);bridge.move(base,rid,'pending','working')
    result=run(root)
    assert saved(root,rid)['failure']['code']==('cleanup_failed' if blocked else 'interrupted')
    assert (base/'cleanup-required.json').exists()==blocked
    assert not (tmp_path/'calls').exists()
    queue(setup,repeat_key='new-incident')
    if blocked:
        assert 'cleanup could not be confirmed' in run(root).stdout and not (tmp_path/'calls').exists()


def test_published_result_recovers_move_without_inference(setup,tmp_path):
    root=setup[-1];fake(tmp_path);rid=queue(setup);base=root/'investigations'
    bridge.move(base,rid,'pending','working')
    inbox.atomic(base/'results'/(rid+'.json'),dict(schema_version=1,request_id=rid,state='ready',finding='Saved finding',cleanup_confirmed=True))
    assert inbox.result(rid,root)==('Saved finding','ready')
    assert run(root).stdout.strip()==bridge.GATE
    assert (base/'done'/(rid+'.json')).exists() and not (tmp_path/'calls').exists()


def test_redaction_size_caps_and_no_evidence_file_reads(setup,tmp_path):
    root=setup[-1];private=tmp_path/'evidence';private.write_text('DO NOT READ THIS')
    rid=queue(setup,evidence=f'Path {private}\nsecret={SECRET}\nAuthorization: Bearer abcdef\npassword="hidden"')
    text=(root/'investigations/pending'/(rid+'.json')).read_text()
    assert SECRET not in text and 'abcdef' not in text and 'hidden' not in text and 'DO NOT READ THIS' not in text
    assert '[redacted]' in text
    for key,value in [('happened','x'*4001),('evidence','x'*8001),('investigate','x'*4001)]:
        with pytest.raises(NodeError) as exc:queue(setup,**{key:value})
        assert exc.value.code=='request_too_large'
    for path in (root/'investigations').rglob('*'):
        assert path.stat().st_mode&0o777==(0o700 if path.is_dir() else 0o600)


@pytest.mark.parametrize('kind',['symlink','directory','unknown_schema','unknown_id'])
def test_reader_refuses_unsafe_or_invalid_records(setup,tmp_path,kind):
    root=setup[-1];rid=queue(setup);p=root/'investigations/results'/(rid+'.json')
    if kind=='symlink':p.symlink_to(tmp_path/'outside')
    elif kind=='directory':p.mkdir()
    elif kind=='unknown_schema':p.write_text('{"schema_version":99}')
    else:rid=rid[:-1]+('a' if rid[-1]!='a' else 'b')
    with pytest.raises(NodeError):inbox.result(rid,root)


def test_missing_profile_and_empty_inbox(setup,tmp_path):
    root=setup[-1]
    assert run(root).stdout.strip()==bridge.GATE
    fake(tmp_path);rid=queue(setup);(tmp_path/'profile/config.yaml').unlink()
    assert 'Set up the aotn Hermes profile first' in run(root).stdout
    assert saved(root,rid)['failure']['code']=='profile_missing' and not (tmp_path/'calls').exists()


@pytest.mark.parametrize('unsafe',['directory','symlink','fifo'])
def test_named_installer_refuses_nonregular_destinations(setup,tmp_path,unsafe):
    home=tmp_path/'install';scripts=home/'scripts';scripts.mkdir(parents=True)
    target=scripts/'aotn-investigate-home.sh'
    if unsafe=='directory':target.mkdir()
    elif unsafe=='symlink':target.symlink_to(tmp_path/'missing')
    else:os.mkfifo(target)
    p=subprocess.run(['bash',str(INSTALL),'--investigate-command','home'],env=dict(os.environ,HERMES_HOME=str(home)),capture_output=True,text=True,timeout=5)
    assert p.returncode==70 and 'not a regular file' in p.stderr


def test_named_install_check_mode_drift_and_argument_refusal(setup,tmp_path):
    home=tmp_path/'install'
    def install(*flags):return subprocess.run(['bash',str(INSTALL),*flags,'--investigate-command','home'],env=dict(os.environ,HERMES_HOME=str(home)),capture_output=True,text=True)
    assert install('--check').returncode==1
    assert install().returncode==0
    assert install('--check').returncode==0
    entry=home/'scripts/aotn-investigate-home.sh';entry.chmod(0o644)
    assert install('--check').returncode==1 and entry.stat().st_mode&0o777==0o644
    assert install().returncode==0 and entry.stat().st_mode&0o777==0o755
    assert (home/'scripts/_aotn_investigate.py').stat().st_mode&0o777==0o644
    assert subprocess.run(['bash',str(entry),'unexpected'],capture_output=True).returncode==64
    wrong=home/'scripts/wrong-name.sh';wrong.write_bytes(entry.read_bytes())
    assert subprocess.run(['bash',str(wrong)],capture_output=True).returncode==64


@pytest.mark.asyncio
@pytest.mark.parametrize('source',['Configured','Upstream payload','Vault'])
async def test_both_input_sources_and_result_forwarding(setup,source):
    ctx,_,done,errors,root=setup
    ctx.inputs={'input':'Incident from payload','evidence':'Excerpt from payload'}
    ctx.memory_bank.store_persistent('what','Incident from Vault',type_tag='string')
    ctx.memory_bank.store_persistent('proof','Excerpt from Vault',type_tag='string')
    node=HermesInvestigateNode('ask',{**HermesInvestigateNode.default_config,'input_source':source,'input':'Configured incident',
        'input_vault_key':'what','evidence_source':source,'evidence':'Configured excerpt','evidence_vault_key':'proof','investigate':'Explain it'})
    await node.execute(ctx)
    assert not errors
    rid=done[-1]['data']['default'];record=inbox.read(root/'investigations/pending'/(rid+'.json'))
    assert record['what_happened']=={'Configured':'Configured incident','Vault':'Incident from Vault','Upstream payload':'Incident from payload'}[source]
    assert record['evidence']=={'Configured':'Configured excerpt','Vault':'Excerpt from Vault','Upstream payload':'Excerpt from payload'}[source]
    original={'arbitrary':['identity']};ctx.inputs['input']=original
    reader=HermesInvestigationResultNode('read',{**HermesInvestigationResultNode.default_config,'input':rid,
        'dead_drop_passthrough':True,'transient_output':False,'vault_write':True,'vault_write_key':'finding'})
    await reader.execute(ctx)
    assert not errors and done[-1]['data']['default'] is original
    assert ctx.memory_bank.read_persistent('finding')=='not ready yet'


@pytest.mark.parametrize('change,code',[({'when':'yesterday'},'invalid_time'),({'when':'2026-10-23T10:00:00'},'invalid_time'),
    ({'happened':''},'input_missing'),({'minutes':float('nan')},'inbox_invalid'),({'minutes':1441},'inbox_invalid')])
def test_validation_leaves_no_request(setup,change,code):
    with pytest.raises(NodeError) as exc:queue(setup,**change)
    assert exc.value.code==code and not (setup[-1]/'investigations/pending').exists()


def test_timezone_normalization_and_defaults(setup):
    rid=queue(setup,when='2026-10-23T03:14:00-07:00')
    assert inbox.read(setup[-1]/'investigations/pending'/(rid+'.json'))['incident_at']=='2026-10-23T10:14:00+00:00'
    assert inbox.policy(None)['profile']==str(Path('~/.hermes/profiles/aotn').expanduser())


def test_oldest_claim_and_failed_tool_preflight_consumes_start(setup,tmp_path):
    root=setup[-1];fake(tmp_path,tools=TOOLS.replace('✗ disabled','✓ enabled',1))
    first=queue(setup,repeat_key='one');second=queue(setup,repeat_key='two')
    path=root/'investigations/pending'/(second+'.json');r=inbox.read(path);r['queued_at']='2020-01-01T00:00:00Z';inbox.atomic(path,r)
    run(root)
    assert saved(root,second)['failure']['code']=='permission_denied'
    assert (root/'investigations/pending'/(first+'.json')).exists()
    assert len(list((root/'investigations/attempts').iterdir()))==1


def test_cleanup_refusal_blocks_later_start(setup,tmp_path):
    root=setup[-1];rid=queue(setup)
    broker=[sys.executable,'-c',"import sys;sys.stdin.read();print('{\"status\":\"cleanup_failed\",\"cleanup_confirmed\":false}')"]
    program=f"from backend.integrations import hermes_investigate as b;b.broker_command=lambda:{broker!r};print(b.tick({str(root)!r}))"
    result=subprocess.run([sys.executable,'-c',program],cwd=APP,capture_output=True,text=True,timeout=15)
    assert 'stop cleanly' in result.stdout
    assert not saved(root,rid)['cleanup_confirmed']
    queue(setup,repeat_key='another')
    assert 'cleanup could not be confirmed' in run(root).stdout
    assert not (tmp_path/'calls').exists()


def test_missing_or_malformed_lease_blocks_without_touching_unrelated_pid(setup,tmp_path):
    root=setup[-1];rid=queue(setup);base=root/'investigations';bridge.move(base,rid,'pending','working')
    inbox.atomic(base/'leases'/(rid+'.json'),dict(schema_version=1,request_id=rid,claimed_epoch=0,owner_pid=os.getpid()))
    assert 'cleanup could not be confirmed' in run(root).stdout
    assert (base/'cleanup-required.json').exists()


def test_installed_helper_end_to_end_without_live_paths(setup,tmp_path):
    root=setup[-1];fake(tmp_path);rid=queue(setup)
    args=[sys.executable,str(APP/'integrations/hermes/_aotn_investigate.py'),'--project-root',str(APP.parent),
        '--data-dir',str(tmp_path/'data'),'--folder',str(root),'--name','test']
    p=subprocess.run(args,capture_output=True,text=True,cwd=tmp_path,timeout=15)
    assert p.returncode==0 and 'The service may be overloaded.' in p.stdout and not p.stderr
    assert inbox.result(rid,root)==('The service may be overloaded.','ready')


@pytest.mark.parametrize('cancel',[False,True])
def test_preflight_timeout_stop_and_detached_cleanup(setup,tmp_path,cancel):
    root=setup[-1];pidfile=tmp_path/'preflight-child.pid';parent=tmp_path/'preflight.pid'
    child=f'import os,time,signal;os.setsid();signal.signal(signal.SIGINT,signal.SIG_IGN);open({str(pidfile)!r},"w").write(str(os.getpid()));time.sleep(60)'
    program=f'signal.signal(signal.SIGINT,signal.SIG_IGN)\nPath({str(parent)!r}).write_text(str(os.getpid()))\nsubprocess.Popen([sys.executable,"-c",{child!r}])\ntime.sleep(60)'
    executable=fake(tmp_path)
    source=executable.read_text().replace("if sys.argv[1]=='tools':\n", "if sys.argv[1]=='tools':\n"+'\n'.join(' '+line for line in program.splitlines())+'\n')
    executable.write_text(source);rid=queue(setup)
    p=subprocess.Popen(command(root,15 if cancel else 7),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=APP)
    pids=[wait_file(parent,p),wait_file(pidfile,p)]
    if cancel:p.send_signal(signal.SIGTERM)
    p.communicate(timeout=10)
    assert all(not Path(f'/proc/{pid}').exists() for pid in pids)
    assert saved(root,rid)['failure']['code']==('cancelled' if cancel else 'timed_out')
    assert [json.loads(s)[0] for s in (tmp_path/'calls').read_text().splitlines()]==['tools']


def test_known_secret_redacted_from_result_and_report(setup,tmp_path):
    root=setup[-1];rid=queue(setup);fake(tmp_path,f'print({SECRET!r})')
    args=[sys.executable,str(APP/'integrations/hermes/_aotn_investigate.py'),'--project-root',str(APP.parent),
        '--data-dir',str(tmp_path),'--folder',str(root),'--name','test']
    result=subprocess.run(args,capture_output=True,text=True,cwd=tmp_path,timeout=15)
    assert SECRET not in result.stdout and saved(root,rid)['finding']=='[redacted]'


def test_wrong_id_and_naive_timestamp_fail_closed(setup):
    root=setup[-1];rid=queue(setup);p=root/'investigations/pending'/(rid+'.json');request=inbox.read(p)
    request['incident_at']='2026-01-01T00:00:00';inbox.atomic(p,request)
    with pytest.raises(NodeError) as exc:inbox.result(rid,root)
    assert exc.value.code=='record_invalid'
    request['incident_at']='2026-01-01T00:00:00Z';request['request_id']=rid[:-1]+('a' if rid[-1]!='a' else 'b');inbox.atomic(p,request)
    with pytest.raises(NodeError) as exc:inbox.result(rid,root)
    assert exc.value.code=='record_invalid'


@pytest.mark.asyncio
async def test_invalid_vault_destinations_fail_before_queue_or_read(setup):
    ctx,_,_,errors,root=setup
    node=HermesInvestigateNode('ask',{**HermesInvestigateNode.default_config,'input':'Failed','investigate':'Why',
        'vault_write':True,'vault_write_key':''})
    await node.execute(ctx)
    assert errors[-1].code=='node_error' and not root.exists()
    node=HermesInvestigationResultNode('read',{**HermesInvestigationResultNode.default_config,
        'vault_write':True,'vault_write_key':'same','state_vault_write':True,'state_vault_key':'same'})
    await node.execute(ctx)
    assert errors[-1].code=='node_error' and not root.exists()


def test_write_failure_before_claim_does_not_publish_or_infer(setup,tmp_path,monkeypatch):
    root=setup[-1];rid=queue(setup);fake(tmp_path)
    original=inbox.atomic
    def fail_lease(path,record):
        if path.parent.name=='leases':raise OSError('failed write')
        return original(path,record)
    monkeypatch.setattr(inbox,'atomic',fail_lease)
    assert bridge.tick(root)=='Investigation inbox needs checking.'
    assert not (root/'investigations/results'/(rid+'.json')).exists()
    assert (root/'investigations/pending'/(rid+'.json')).exists()
    assert not (tmp_path/'calls').exists()


@pytest.mark.parametrize('corrupt',['policy','attempt'])
def test_corrupt_accounting_refuses_before_claim_or_model(setup,tmp_path,corrupt):
    root=setup[-1];rid=queue(setup);fake(tmp_path);base=root/'investigations'
    if corrupt=='policy':inbox.atomic(base/'policy.json',dict(schema_version=1,daily_limit=5))
    else:inbox.atomic(base/'attempts/a_invalid.json',dict(schema_version=1,attempt_id='a_invalid',request_id=rid,at=''))
    assert run(root).stdout.strip()=='Investigation inbox needs checking.'
    assert (base/'pending'/(rid+'.json')).exists() and not (base/'working'/(rid+'.json')).exists()
    assert not (tmp_path/'calls').exists()


def test_unregistered_credentials_and_incomplete_private_key_are_redacted():
    value='token=unknown-token\nAuthorization: Basic dXNlcjpwYXNz\nhttps://user:password@example.test\n-----BEGIN PRIVATE KEY-----\npartial-private-key'
    safe=inbox.redact(value)
    assert all(secret not in safe for secret in ('unknown-token','dXNlcjpwYXNz','user:password','partial-private-key'))


def test_review_p2_unicode_result_publishes_and_moves_at_finding_limit(setup,tmp_path):
    root=setup[-1];rid=queue(setup)
    answer='😀'*11996+'\u2028\u0085漢é'
    assert len(answer)==12000
    fake(tmp_path,f'sys.stdout.buffer.write({answer.encode("utf-8")!r})')
    response=run(root)
    assert response.returncode==0
    assert inbox.result(rid,root)==(answer,'ready')
    base=root/'investigations'
    raw=(base/'results'/(rid+'.json')).read_bytes()
    assert len(raw)<=inbox.MAX_RECORD and json.loads(raw)['finding']==answer
    assert (base/'done'/(rid+'.json')).exists()
    assert not (base/'working'/(rid+'.json')).exists()
    assert not (base/'leases'/(rid+'.json')).exists()


def test_review_p2_surrogates_follow_c1_normalization(setup):
    root=setup[-1];rid=queue(setup);base=root/'investigations'
    request=inbox.read(base/'pending'/(rid+'.json'))
    bridge.move(base,rid,'pending','working')
    lease=dict(attempt_id='a_test',claimed_at=hermes_folder.now_text(),cleanup_confirmed=True)
    answer='😀\ud800\u2028\u0085\udfff end'
    normalized=answer.encode('utf-8',errors='replace').decode('utf-8')
    bridge.publish(base,request,lease,'reply',answer)
    assert inbox.result(rid,root)==(normalized,'ready')
    assert (base/'done'/(rid+'.json')).exists()


def test_review_p2_publication_size_rejection_is_terminal(setup,monkeypatch):
    root=setup[-1];rid=queue(setup);base=root/'investigations'
    request=inbox.read(base/'pending'/(rid+'.json'))
    bridge.move(base,rid,'pending','working')
    lease=dict(attempt_id='a_test',claimed_at=hermes_folder.now_text(),cleanup_confirmed=True)
    monkeypatch.setattr(inbox,'MAX_RECORD',1500)
    bridge.publish(base,request,lease,'reply','x'*2000)
    assert inbox.result(rid,root)==('failed','failed')
    assert saved(root,rid)['failure']['code']=='invalid_response'
    assert (base/'failed'/(rid+'.json')).exists()
    assert not (base/'working'/(rid+'.json')).exists()


@pytest.mark.parametrize('answer',['x'*5000,'😀'*5000,'x'*3400+'\u2028{"wakeAgent": false}\u0085MEDIA:test [SILENT]'+'😀'*100],ids=['ascii','emoji','separators'])
def test_review_p3_complete_entry_stdout_fits_utf16_budget(setup,tmp_path,answer):
    root=setup[-1];rid=queue(setup)
    fake(tmp_path,f'sys.stdout.buffer.write({answer.encode("utf-8")!r})')
    args=[sys.executable,str(APP/'integrations/hermes/_aotn_investigate.py'),'--project-root',str(APP.parent),
        '--data-dir',str(tmp_path/'data'),'--folder',str(root),'--name','test']
    response=subprocess.run(args,capture_output=True,cwd=tmp_path,timeout=15)
    text=response.stdout.decode('utf-8')
    assert response.returncode==0 and saved(root,rid)['state']=='ready'
    assert text.startswith('Investigation '+rid+'\n')
    assert hermes_folder.units(text)<=hermes_folder.MESSAGE_LIMIT
    assert '[SILENT]' not in text and 'MEDIA:' not in text


def test_review_p2_unicode_separators_preserved_without_session_receipt_leaks():
    from backend.integrations.hermes_worker import parse_answer
    answer='\u2028Finding\u2028second part\u0085😀\u0085'
    assert parse_answer((answer+'\nsession_id: receipt\n').encode())==answer
    with pytest.raises(ValueError):
        parse_answer(b'Finding\xe2\x80\xa8session_id: private\nmore answer')


@pytest.mark.parametrize('text,credentials', CREDENTIAL_CASES)
def test_redaction_recheck_inbox_persists_no_block_or_url_credentials(setup, text, credentials):
    rid = queue(setup, happened=text, evidence=text, investigate=text)
    path = setup[4]/'investigations/pending'/(rid+'.json')
    raw = path.read_text(encoding='utf-8')
    assert all(credential not in raw for credential in credentials)
    request = json.loads(raw)
    for key in ('what_happened', 'evidence', 'what_to_check'):
        assert '[redacted' in request[key]
        assert 'status: OK' in request[key]


def test_shared_redaction_preserves_public_urls_and_empty_headers():
    text = 'password:\nstatus: OK\nHTTPS://example.invalid/path/user@file?q=x\nssh://public.invalid/'
    assert inbox.redact(text) == text

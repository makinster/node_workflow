"""One deterministic no-agent cron tick, with a tool-free bounded CLI child."""
from datetime import datetime
import json
import os
from pathlib import Path
import runpy
import sys
import time
import uuid

from .. import hermes_folder as shared, hermes_investigations as inbox
from ..node_errors import NodeError
from .hermes_ask import broker_command, worker_env, MESSAGES
from .hermes_worker import PROTOCOL, POLICY

DEADLINE = 90
STALE_SECONDS = 300
GATE = '{"wakeAgent": false}'


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def move(base, rid, source, target):
    src = base/source/(rid+'.json')
    dst = base/target/(rid+'.json')
    inbox.regular(src)
    inbox.regular(dst)
    if dst.exists():
        raise ValueError('duplicate terminal request')
    os.rename(src,dst)
    inbox.sync_dir(src.parent)
    inbox.sync_dir(dst.parent)


def block(base, rid):
    inbox.atomic(base/'cleanup-required.json',dict(schema_version=1,request_id=rid,
                 code='cleanup_failed',message='Investigation needs checking',at=shared.now_text()))


def publish(base, request, lease, status, answer='', manager=None):
    rid = request['request_id']
    # Normalize before counting, persistence and delivery, as C1 escape does.
    finding = (inbox.redact(answer,manager).encode('utf-8', errors='replace').decode('utf-8')
               if status=='reply' else '')
    if status=='reply' and (not finding.strip() or len(finding)>inbox.MAX_FINDING):
        status, finding = 'invalid_response',''
    message = ('Stopped after 90 seconds' if status=='timed_out' else
               'Investigation stopped' if status=='cancelled' else
               'Investigation was interrupted; it will not be retried' if status=='interrupted' else
               MESSAGES.get(status,'The investigation could not finish.'))
    result = dict(schema_version=1,request_id=rid,attempt_id=lease['attempt_id'],
        state='ready' if status=='reply' else 'failed',finding=finding,
        started_at=lease['claimed_at'],finished_at=shared.now_text(),mode='report_only',tools=[],
        limits={'seconds':90,'turns':1,'budget_usd':None},
        usage={'cost_status':'not_reported','estimated_cost_usd':None,'input_tokens':None,'output_tokens':None},
        cleanup_confirmed=lease.get('cleanup_confirmed') is True,
        failure=None if status=='reply' else {'code':status,'message':message},
        notification='handoff_unknown')
    saved = base/'results'/(rid+'.json')
    if saved.exists():
        result = inbox.validate_result(inbox.read(saved),rid)
        if result.get('attempt_id') != lease['attempt_id']:
            raise ValueError('stale attempt')
    else:
        try:
            inbox.atomic(saved,result)
        except NodeError as exc:
            if exc.code!='request_too_large':
                raise
            # A completed attempt must become terminal even if its serialized
            # finding cannot fit; never leave a successful cleanup pending.
            result.update(state='failed', finding='', failure={
                'code':'invalid_response', 'message':MESSAGES['invalid_response']})
            inbox.atomic(saved,result)
    move(base,rid,'working','done' if result['state']=='ready' else 'failed')
    (base/'leases'/(rid+'.json')).unlink(missing_ok=True)
    inbox.sync_dir(base/'leases')
    report = f"Investigation {rid}\n" + (result['finding'] if result['state']=='ready' else result['failure']['message'])
    return shared.cut(shared.escape(report),3500)


def recover(root, base):
    """No retry. Only prove cleanup when no child was launched or host rebooted.

    An abandoned launching/running lease on the same boot cannot prove the
    whereabouts of detached children. Quarantine instead of guessing by PID.
    """
    for path in sorted((base/'working').iterdir()):
        if path.name.startswith('.'):
            continue
        request = inbox.read(path)
        inbox.validate_request(request)
        rid = request['request_id']
        saved = base/'results'/(rid+'.json')
        if saved.exists():
            result = inbox.validate_result(inbox.read(saved),rid)
            if result.get('cleanup_confirmed') is not True:
                block(base,rid)
                return 'Investigation needs checking: cleanup could not be confirmed.'
            move(base,rid,'working','done' if result['state']=='ready' else 'failed')
            (base/'leases'/(rid+'.json')).unlink(missing_ok=True)
            continue
        try:
            lease = inbox.read(base/'leases'/(rid+'.json'))
            if lease['request_id']!=rid:
                raise ValueError
            if (not isinstance(lease.get('boot_id'),str) or not lease['boot_id']
                    or lease.get('phase') not in ('claimed','launching','finished')
                    or type(lease.get('claimed_epoch')) not in (int,float)
                    or not isinstance(lease.get('attempt_id'),str)):
                raise ValueError
            age = time.time()-lease['claimed_epoch']
        except (OSError,ValueError,KeyError,TypeError):
            block(base,rid)
            return 'Investigation needs checking: cleanup could not be confirmed.'
        if 0 <= age < STALE_SECONDS:
            return GATE
        safe = (lease.get('phase')=='claimed' or lease.get('cleanup_confirmed') is True
                or lease.get('boot_id')!=boot_id())
        if not safe:
            block(base,rid)
            lease['cleanup_confirmed']=False
            publish(base,request,lease,'cleanup_failed')
            return 'Investigation needs checking: cleanup could not be confirmed.'
        lease['cleanup_confirmed']=True
        # Recovery reports the failure without starting another agent this tick.
        return publish(base,request,lease,'interrupted')
    return None


def tick(root, name='home', timeout=DEADLINE, manager=None):
    """Public test seam accepts a shorter budget; production always uses 90 s."""
    expires = time.monotonic()+timeout
    request = lease = None
    claimed = False
    confirmed = True
    root = Path(root)
    if sys.platform!='linux':
        return 'Investigation needs a native Linux runtime.'
    try:
        base = inbox.prepare(root)
        with inbox.lock(base/'worker.lock',wait=0):
            with inbox.lock(root/shared.LOCK):
                marker=base/'cleanup-required.json'
                if marker.exists() or marker.is_symlink():
                    return 'Investigation needs checking: cleanup could not be confirmed.'
                recovery = recover(root,base)
                if recovery is not None:
                    return recovery
                pending = [(stage,r) for stage,r in inbox.records(base) if stage=='pending']
                if not pending:
                    return GATE
                policy = inbox.read(base/'policy.json')
                cap = policy.get('daily_limit')
                if (type(cap) is not int or not 0<=cap<=50
                        or any(not isinstance(policy.get(key),str) or not Path(policy[key]).is_absolute()
                               for key in ('profile','command'))):
                    raise ValueError('invalid policy')
                day=shared.now_text()[:10]
                attempts=[]
                for path in (base/'attempts').iterdir():
                    if path.name.startswith('.'):
                        continue
                    attempt=inbox.read(path)
                    if (not isinstance(attempt.get('at'),str)
                            or not isinstance(attempt.get('attempt_id'),str)
                            or path.name!=attempt['attempt_id']+'.json'
                            or not inbox.ID.fullmatch(str(attempt.get('request_id','')))):
                        raise ValueError('invalid attempts')
                    moment=datetime.fromisoformat(attempt['at'].replace('Z','+00:00'))
                    if moment.tzinfo is None or moment.utcoffset().total_seconds()!=0:
                        raise ValueError('invalid attempts')
                    attempts.append(attempt)
                if sum(a['at'][:10]==day for a in attempts)>=cap:
                    return GATE
                request=min((r for _,r in pending),key=lambda r:(r['queued_at'],r['request_id']))
                rid=request['request_id']
                attempt='a_'+uuid.uuid4().hex
                lease=dict(schema_version=1,request_id=rid,attempt_id=attempt,claimed_at=shared.now_text(),
                    claimed_epoch=time.time(),boot_id=boot_id(),owner_pid=os.getpid(),phase='claimed',cleanup_confirmed=True)
                inbox.atomic(base/'attempts'/(attempt+'.json'),dict(schema_version=1,attempt_id=attempt,request_id=rid,at=shared.now_text()))
                inbox.atomic(base/'leases'/(rid+'.json'),lease)
                move(base,rid,'pending','working')
                claimed = True
                # Persist ambiguity BEFORE any spawn. A crash at this boundary
                # cannot cause an unsafe automatic retry or PID-based cleanup.
                lease.update(phase='launching',cleanup_confirmed=False)
                inbox.atomic(base/'leases'/(rid+'.json'),lease)
                confirmed=False
            status, answer='agent_failed',''
            # Child has only profile credentials, not the bridge/app environment.
            h0=runpy.run_path(str(Path(__file__).resolve().parents[2]/'integrations/hermes/_aotn_run.py'))
            budget=max(.01,expires-time.monotonic()-min(3,timeout/5))
            broker_request=dict(protocol=PROTOCOL,policy=POLICY,question=inbox.question(request),
                folder=str(base),profile=policy['profile'],command=policy['command'],expires_at=time.monotonic()+budget)
            code, output, diagnostic, reason, _=h0['collect'](broker_command(),str(base),deadline=budget,
                input_bytes=json.dumps(broker_request,ensure_ascii=True).encode(),env=worker_env())
            # Returning from collect proves the outer subreaper reaped all its
            # descendants, even if the nested broker was killed or crashed.
            confirmed=True
            data={}
            try:
                data=json.loads(output)
            except (ValueError,UnicodeError):
                pass
            if isinstance(data,dict) and data.get('cleanup_confirmed') is False:
                # Retain conservative worker refusal even after outer cleanup.
                confirmed=False
                status='cleanup_failed'
            elif reason=='signal':
                status='cancelled'
            elif reason=='deadline':
                status='timed_out'
            elif reason is None and code==0 and isinstance(data,dict):
                status=data.get('status','invalid_response')
                answer=data.get('answer','')
                if not isinstance(answer,str):
                    status,answer='invalid_response',''
                if status!='reply' and status not in MESSAGES and status!='cancelled':
                    status='invalid_response'
            with inbox.lock(root/shared.LOCK):
                current=inbox.read(base/'leases'/(rid+'.json'))
                if current['attempt_id']!=lease['attempt_id']:
                    raise ValueError('stale attempt')
                lease.update(phase='finished',cleanup_confirmed=confirmed)
                inbox.atomic(base/'leases'/(rid+'.json'),lease)
                if not confirmed:
                    block(base,rid)
                return publish(base,request,lease,status,answer,manager)
    except NodeError as exc:
        if exc.code=='inbox_busy':
            return GATE
        return 'Investigation inbox needs checking.'
    except BaseException:
        # No evidence, stdout/stderr, profile, traceback or credentials in errors.
        # Retain launching lease on uncertain spawn/cleanup, blocking next tick.
        if claimed and request is not None and lease is not None:
            try:
                with inbox.lock(root/shared.LOCK):
                    if not confirmed:
                        block(base,request['request_id'])
                    lease['cleanup_confirmed']=confirmed
                    return publish(base,request,lease,'agent_failed' if confirmed else 'cleanup_failed')
            except BaseException:
                pass
        return 'Investigation inbox needs checking.'

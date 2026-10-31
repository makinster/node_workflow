"""Real RunService fixtures with local execute gates, never inference/provider calls.

Gates change scheduling only. Nodes, deliveries, collector, waits, validation and
output publication use the production engine. Invalid graphs exercise its start
refusal rather than bypassing validation or injecting collector plans.
"""
import asyncio
from copy import deepcopy
from pathlib import Path

from backend.flow_behaviors import Kind, resolve_flow
from backend.output_entry import text_output_prefix
from backend.run_policies import TerminatePolicy
from backend.run_service import RunService, WorkflowValidationError
from .rules_family_two import LOCAL_TYPES


async def run_fixture(spec,case,variant,*,order='forward',stop_after=None):
    if order not in ('forward','reverse'): raise ValueError('unknown schedule')
    if any(n.get('type') not in LOCAL_TYPES for n in spec['nodes'].values()):
        raise ValueError('engine fixtures allow only the reviewed local evaluation types')
    root=Path(case['root']).resolve(); root.mkdir(parents=True,exist_ok=True)
    for filename,text in variant['files'].items():
        path=root/filename
        if path.parent!=root or path.is_symlink(): raise ValueError('fixture path escapes root')
        path.write_text(text,encoding='utf-8')
    before={p.name:p.read_bytes() for p in root.iterdir() if p.is_file()}
    service=RunService.create(); wm=service.workflow_map
    wm.create_new(spec['name'])
    ids={h:wm.add_node(n['type'],alias=n.get('alias') or h) for h,n in spec['nodes'].items()}
    handles={v:k for k,v in ids.items()}
    for h,n in spec['nodes'].items():
        # Authoring specs are overrides; the live map stores full configs.
        config={**deepcopy(service._factory.create_config_template(n['type']) or {}),
                **deepcopy(n.get('config',{}))}
        if n['type']=='wait_until_node':
            from backend.flow_behaviors import parse_targets
            config['target_node_ids']=[ids.get(t,t) for t in parse_targets(config.get('target_node_ids'))]
        wm.update_node_config(ids[h],config)
    for edge in spec['connections']:
        a,port=edge['from'].split('.',1);b,slot=edge['to'].split('.',1)
        wm.connect(ids[a],port,ids[b],slot)
    service.configuration.set('system_node_folders',str(root))
    waiting=[]; pulse=asyncio.Event(); executions=[]; publications=[]; events=[]
    factory=service._factory
    original=factory.create_node
    def create_node(kind,node_id,config=None):
        node=original(kind,node_id,config)
        if node is None: return None
        execute=node.execute
        async def gated(context):
            supervisor=service.master_state._supervisors[context.branch_id]
            row=dict(handle=handles[node_id],branch=context.branch_id,lineage=tuple(supervisor.lineage),
                     depth=supervisor.depth,kind=resolve_flow(wm.get_node_data(node_id),factory).kind,
                     permit=asyncio.Event(),done=asyncio.Event())
            waiting.append(row); pulse.set()
            await row['permit'].wait()
            original_done=context.signal_done
            def publish(payload):
                if 'default' in payload.get('data',{}):
                    publications.append(dict(handle=handles[node_id],branch=context.branch_id,
                        lineage=list(row['lineage']),depth=row['depth'],value=deepcopy(payload['data']['default'])))
                original_done(payload)
            from dataclasses import replace
            try: await execute(replace(context,signal_done=publish))
            finally: row['done'].set();pulse.set()
        node.execute=gated
        return node
    factory.create_node=create_node
    def event(e):
        events.append(dict(handle=handles.get(e.get('node_id')),status=e.get('status'),branch=e.get('branch_id')))
    service.subscribe('NODE_EXECUTION_UPDATE',event)
    done=None
    try:
        try:
            await service.start(recovery_policy=TerminatePolicy('terminate_workflow'))
        except WorkflowValidationError as exc:
            return dict(state='preflight_rejected',outputs=[],errors=exc.result['errors'],events=events,
                        executions=[],publications=[],order=order,system_node_folders=str(root))
        except Exception as exc:
            # A startup exception other than the public validation refusal is
            # evidence to report, never silently treated as an expected negative.
            return dict(state='startup_error',outputs=[],errors=[dict(code=type(exc).__name__,message=str(exc))],
                        events=events,executions=[],publications=[],order=order)
        done=asyncio.create_task(service.wait())
        async def drive():
            for _ in range(256):
                # Let sibling supervisors register their next local steps. No
                # timing sleeps or provider doubles substitute for completion.
                for _ in range(12): await asyncio.sleep(0)
                if done.done(): return
                if stop_after is not None and len(executions)>=stop_after:
                    service.stop()
                    return
                if not waiting:
                    pulse.clear()
                    if done.done(): return
                    wake=asyncio.create_task(pulse.wait())
                    await asyncio.wait([wake,done],return_when=asyncio.FIRST_COMPLETED)
                    wake.cancel(); await asyncio.gather(wake,return_exceptions=True)
                    continue
                waiting.sort(key=lambda r:(r['lineage'],r['handle']),reverse=order=='reverse')
                row=waiting.pop(0)
                executions.append({k:v for k,v in row.items() if k not in ('permit','done','kind')})
                row['permit'].set()
                # Join and Wait are allowed to park while the other paths run.
                if row['kind'] not in (Kind.JOIN,Kind.WAIT):
                    await asyncio.wait_for(row['done'].wait(),5)
            raise TimeoutError('engine fixture exceeded step bound')
        await asyncio.wait_for(drive(),10)
        run=(await asyncio.wait_for(done,5)).to_dict()
        outputs=[]
        for entry in run['outputs']:
            h=handles.get(getattr(entry,'node_id',''))
            if spec['nodes'].get(h,{}).get('type')=='end_node': continue
            config=wm.get_node_data(ids[h])['config'] if h in ids else {}
            outputs.append(str(entry).removeprefix(text_output_prefix(config.get('label','Output'))))
        after={p.name:p.read_bytes() for p in root.iterdir() if p.is_file()}
        return dict(state='cancelled' if run['final_state']=='STOPPED' else 'finished' if run['exit_code']==0 else 'failed',outputs=outputs,errors=run['errors'],
                    executions=executions,publications=publications,events=events,
                    files_preserved=before==after,order=order,system_node_folders=str(root))
    finally:
        if done is not None and not done.done():
            service.stop()
            try: await asyncio.wait_for(done,5)
            except (TimeoutError,asyncio.CancelledError): done.cancel()
        service.close()

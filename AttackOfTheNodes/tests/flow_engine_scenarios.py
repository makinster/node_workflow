"""Additional real coordinator scenarios for the reviewed Wait/flow claims."""
import asyncio
from tests.test_merge_arrival_runtime import Engine

async def own_input_and_targets(value,form,present=True):
    e=Engine();fork=e.add('branch_node',branch_count=3)
    source=e.step('source',value=value,missing=not present);one=e.step('one',hold=True,value='not the wait input')
    two=e.step('two',hold=True,value='not read either');sink=e.step('sink',sink=True)
    targets={'list':[one,two],'comma':f' {one}, ,{two},','newline':f'{one}\n{two}\n','empty':[]}[form]
    wait=e.add('wait_until_node',target_node_ids=targets,timeout_seconds=0)
    e.wire(e.start,fork);e.wire(fork,source,'path_a');e.wire(fork,one,'path_b');e.wire(fork,two,'path_c')
    e.wire(source,wait);e.wire(wait,sink)
    await e.master.start_workflow(unattended='terminate_branch')
    await e.entered['one'].wait();await e.entered['two'].wait()
    if form!='empty': assert not e.done(wait)
    else: assert e.done(wait)  # No target completion is needed.
    e.gates['two'].set();await asyncio.sleep(0)
    if form!='empty': assert not e.done(wait)
    e.gates['one'].set();await e.finish()
    assert not e.errors() and e.seen[0]['value']=={'input':value if present else ''}

async def sticky_completion_and_fresh_run():
    e=Engine();fork=e.add('branch_node',branch_count=3)
    first=e.step('first',value='one');second=e.step('second',hold=True,value='two')
    target=e.step('target',hold=True);wait=e.add('wait_until_node',target_node_ids=[target])
    sink=e.step('sink',sink=True)
    e.wire(e.start,fork);e.wire(fork,first,'path_a');e.wire(fork,second,'path_b');e.wire(fork,target,'path_c')
    e.wire(first,wait);e.wire(second,wait);e.wire(wait,sink)
    for _ in range(2):
        e.events.clear();e.seen.clear()
        e.gates['second']=asyncio.Event();e.gates['target']=asyncio.Event();e.entered['target']=asyncio.Event()
        await e.master.start_workflow(unattended='terminate_branch');await e.entered['target'].wait()
        assert not e.done(wait)
        e.gates['target'].set()
        while len(e.done(wait))<1: await asyncio.sleep(0)
        e.gates['second'].set();await e.finish()
        assert not e.errors() and len(e.done(wait))==2
        assert [r['value']['input'] for r in e.seen]==['one','two']

async def timeout_and_stop():
    for timeout in [0.01,0]:
        e=Engine();fork=e.add('branch_node');target=e.step('target',hold=True)
        wait=e.add('wait_until_node',target_node_ids=[target],timeout_seconds=timeout)
        sink=e.step('sink',sink=True)
        e.wire(e.start,fork);e.wire(fork,wait,'path_a');e.wire(fork,target,'path_b');e.wire(wait,sink)
        await e.master.start_workflow(unattended='terminate_branch');await e.entered['target'].wait()
        if timeout:
            while not e.errors(): await asyncio.sleep(0)
            assert 'Timed out waiting' in e.errors()[0]['message']
            e.gates['target'].set()
        else:e.master.stop()
        await e.finish()
        assert not e.seen and len(e.errors())==int(bool(timeout))

async def independent_services(tmp_path):
    import json
    from backend.run_service import RunService
    from tests.test_merge_plan_integration import files
    e=Engine();_,merge,_,_=files(e,tmp_path)
    path=tmp_path/'graph.json';path.write_text(json.dumps(e.wm.get_workflow_data_for_save()))
    services=[RunService.create(),RunService.create()]
    try:
        for service in services:service.load(str(path))
        await asyncio.gather(*(s.start() for s in services))
        results=await asyncio.gather(*(s.wait() for s in services))
        assert len({r.run_id for r in results})==2
        assert all(not r.errors and r.outputs==['A contents|B contents'] for r in results)
        assert services[0].master_state.memory_bank is not services[1].master_state.memory_bank
    finally:
        for service in services:service.close()

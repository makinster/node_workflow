"""Normal startup uses the shared graph proof, never fixture MergePlans."""
import asyncio
import json

import pytest

from backend.contracts import workflow_revision
from backend.flow_behaviors import MergePlanError, analyze_flow, merge_plans_from_analysis
from backend.run_service import RunService, WorkflowValidationError
from backend.save_manager import SaveManager
from backend.validator import validate_workflow
from tests.test_merge_arrival_runtime import Engine


async def start(e):
    result = validate_workflow(e.wm, e.factory)
    assert not result['errors'], result['errors']
    assert await e.master.start_workflow(unattended='terminate_branch')


def files(e, tmp_path, *, delay=False):
    fork, merge = e.add('branch_node'), e.add('merge_node')
    readers = []
    e.wire(e.start, fork)
    for index, (slot, text) in enumerate([('path_a', 'A contents'), ('path_b', 'B contents')]):
        path = tmp_path / f'{index}.txt'
        path.write_text(text)
        reader = e.add('file_reader_node', input_source='Configured', file_path=str(path))
        readers.append(reader)
        if delay and index == 0:
            gate = e.step('gate', hold=True)
            e.wire(fork, gate, slot); e.wire(gate, reader)
        else:
            e.wire(fork, reader, slot)
        e.wire(reader, merge, slot=slot)
    show = e.add('text_output_node', label='', template='{input[path_a]}|{input[path_b]}')
    end = e.add('end_node', record_line=False)
    e.wire(merge, show); e.wire(show, end)
    return fork, merge, show, end


@pytest.mark.asyncio
@pytest.mark.parametrize('reverse', [False, True])
async def test_two_file_collect_normal_startup(tmp_path, reverse):
    e = Engine()
    fork, merge, _, _ = files(e, tmp_path, delay=reverse)
    await start(e)
    if reverse:
        await e.at_merge(merge)
        assert not e.done(merge)
        e.gates['gate'].set()
    await e.finish()
    assert not e.errors()
    assert e.memory.read_transient(merge, 'default') == {'path_a': 'A contents', 'path_b': 'B contents'}
    assert e.master.run_outputs == ['A contents|B contents']
    plan = e.master.run_context.merge_plans[merge]
    assert plan.fork_node_id == fork and plan.slots['path_a'].producers == ((0,),)


@pytest.mark.asyncio
@pytest.mark.parametrize('host', ['A', 'C', 'D'])
@pytest.mark.parametrize('beacons', [False, True])
@pytest.mark.parametrize('same_slot', [False, True])
async def test_reference_normal_startup(host, beacons, same_slot):
    e = Engine()
    fork, nested = e.add('branch_node'), e.add('branch_node')
    nodes = dict(A=e.step('A', hold=True, value='slow result'),
                 B=e.step('B', hold=True), C=e.step('C', value='C'), D=e.step('D', value='D'))
    merge = e.add('merge_node', carry_forward_branch_id=nodes[host], selected_branch_id=nodes[host])
    sink = e.step('sink', sink=True)
    e.wire(e.start, fork); e.wire(fork, nodes['A'], 'path_a'); e.wire(fork, nodes['B'], 'path_b')
    e.wire(nodes['B'], nested); e.wire(nested, nodes['C'], 'path_a'); e.wire(nested, nodes['D'], 'path_b')
    for name, slot in [('A','path_a'), ('C','path_b'), ('D','path_b' if same_slot else 'path_c')]:
        source = nodes[name]
        if beacons:
            beacon = e.add('branch_end_node'); e.wire(source, beacon); source = beacon
        e.wire(source, merge, slot=slot)
    e.wire(merge, sink)
    await start(e)
    e.gates['B'].set(); await e.at_merge(merge, 2)
    assert not e.seen
    e.gates['A'].set(); await e.finish()
    expected = {'path_a':'slow result', 'path_b':['C','D']} if same_slot else {'path_a':'slow result','path_b':'C','path_c':'D'}
    assert not e.errors() and e.seen[0]['value'] == {'input':expected}
    assert e.seen[0]['depth'] == 0 and len(e.done(merge)) == 1
    assert e.master.run_context.merge_plans[merge].slots['path_b'].cardinality == ('many' if same_slot else 'one')


@pytest.mark.asyncio
@pytest.mark.parametrize('greeting,expected', [('yes','YES'), ('no','NO')])
async def test_either_or_same_slot_normal_startup(greeting, expected):
    e = Engine(); e.wm.update_node_config(e.start, {'greeting':greeting})
    fork, choice, merge = e.add('branch_node'), e.add('conditional_node', condition_type='equals', right_value='yes'), e.add('merge_node')
    a, yes, no, sink = e.step('A',value='A'),e.step('yes',value='YES'),e.step('no',value='NO'),e.step('sink',sink=True)
    e.wire(e.start,fork);e.wire(fork,a,'path_a');e.wire(a,merge,slot='path_a')
    e.wire(fork,choice,'path_b');e.wire(choice,yes,'true');e.wire(choice,no,'false')
    e.wire(yes,merge,slot='path_b');e.wire(no,merge,slot='path_b');e.wire(merge,sink)
    await start(e);await e.finish()
    assert not e.errors() and e.seen[0]['value'] == {'input':{'path_a':'A','path_b':expected}}
    slot=e.master.run_context.merge_plans[merge].slots['path_b']
    assert slot.cardinality=='one' and slot.producers==((1,),)


@pytest.mark.asyncio
@pytest.mark.parametrize('fails', [False, True])
async def test_independent_side_end_or_failure_is_excluded_from_merge(fails):
    e = Engine()
    fork, merge = e.add('branch_node',branch_count=3),e.add('merge_node')
    a,b,sink=e.step('A',hold=True,value='A'),e.step('B',value='B'),e.step('sink',sink=True)
    side=e.step('side',fail='independent failure') if fails else e.add('end_node',record_line=False)
    e.wire(e.start,fork);e.wire(fork,a,'path_a');e.wire(fork,b,'path_b');e.wire(fork,side,'path_c')
    e.wire(a,merge,slot='path_a');e.wire(b,merge,slot='path_b');e.wire(merge,sink)
    await start(e);await e.at_merge(merge)
    if fails:
        while not e.errors(): await asyncio.sleep(0)
    e.gates['A'].set();await e.finish()
    assert e.seen[0]['value']=={'input':{'path_a':'A','path_b':'B'}} and len(e.done(merge))==1
    assert len(e.errors())==int(fails) and all(x['node_id']==side for x in e.errors())
    assert all((2,) not in slot.producers for slot in e.master.run_context.merge_plans[merge].slots.values())


@pytest.mark.asyncio
async def test_saved_merge_workflow_runs_through_run_service(tmp_path):
    e=Engine();_,merge,_,_=files(e,tmp_path)
    path=tmp_path/'workflow.json';path.write_text(json.dumps(e.wm.get_workflow_data_for_save()))
    service=RunService.create()
    try:
        service.load(str(path))
        await service.start()
        result=await asyncio.wait_for(service.wait(),3)
        assert not result.errors and result.outputs==['A contents|B contents']
        assert merge in service.master_state.run_context.merge_plans
    finally: service.close()


@pytest.mark.asyncio
async def test_merge_in_subworkflow_gets_the_childs_own_graph_plan(tmp_path):
    child=Engine();_,merge,show,end=files(child,tmp_path)
    # Return the collected record itself, rather than the displayed string.
    child.wm.disconnect(merge,'default',show,'input')
    child.wm.disconnect(show,'default',end,'input')
    child.wm.delete_node(show)
    child.wire(merge,end)
    child.wm.set_callable(True)
    child.wm.update_node_config(end,dict(record_line=False,return_end=True,results=[
        dict(id='record',name='record',type='var',required=True,source='Incoming payload')]))
    SaveManager(child.wm).save_current_workflow()
    parent=Engine()
    call=parent.add('subworkflow_node',workflow_id=child.wm.workflow_id,inputs=[],
                    results=[dict(name='record',to='Vault',vault_key='record')])
    finish=parent.add('end_node',record_line=False)
    parent.wire(parent.start,call);parent.wire(call,finish)
    await start(parent);await parent.finish()
    assert not parent.errors()
    assert parent.memory.read_persistent('record')=={'path_a':'A contents','path_b':'B contents'}
    assert not parent.master.run_context.merge_plans


@pytest.mark.asyncio
async def test_two_merges_reproduce_passthrough_when_preflight_is_bypassed_then_refuse_normal_run(tmp_path):
    e=Engine();fork,first,show,end=files(e,tmp_path)
    second=e.add('merge_node')
    e.wm.disconnect(first,'default',show,'input')
    e.wire(first,second,slot='path_a');e.wire(second,show)
    report=analyze_flow(e.wm.get_all_node_data(),e.factory)
    assert report.merges[second].shape_status=='needs_review'
    with pytest.raises(MergePlanError,match='earlier Merge'):
        merge_plans_from_analysis(report)
    # Deliberate diagnostic bypass: measure the unsupported runtime behavior.
    # Only the first join has a proof, matching what can actually be declared.
    report.merges.pop(second)
    report.findings = [f for f in report.findings if f.node_id != second]
    assert await e.master.start_workflow(unattended='terminate_branch',merge_plans=merge_plans_from_analysis(report))
    await e.finish()
    expected={'path_a':'A contents','path_b':'B contents'}
    assert not e.errors() and e.memory.read_transient(first,'default')==expected
    assert e.memory.read_transient(second,'default')==expected  # NOT {'path_a': expected}
    validation=validate_workflow(e.wm,e.factory)
    assert any(x['node_id']==second and x['code']=='flow_needs_review' for x in validation['errors'])
    path=tmp_path/'two-merges.json';path.write_text(json.dumps(e.wm.get_workflow_data_for_save()))
    service=RunService.create()
    try:
        service.load(str(path))
        with pytest.raises(WorkflowValidationError): await service.start()
        assert service.current_run_id is None
    finally: service.close()


@pytest.mark.asyncio
async def test_each_start_uses_its_own_captured_workflow_revision(tmp_path):
    e=Engine();_,merge,show,_=files(e,tmp_path)
    snapshot=e.wm.get_workflow_data_for_save()
    await start(e);await e.finish()
    first=e.master.run_context
    assert first.revision==workflow_revision(snapshot)
    reader=next(c['source_node_id'] for c in e.wm.get_node_data(merge)['connections']['inputs']
                if c['target_port']=='path_b')
    e.wm.disconnect(reader,'default',merge,'path_b');e.wire(reader,merge,slot='path_a')
    e.wm.update_node_config(show,dict(label='',template='{input[path_a]}'))
    snapshot=e.wm.get_workflow_data_for_save()
    await start(e);await e.finish()
    second=e.master.run_context
    assert second.revision==workflow_revision(snapshot) and first.revision!=second.revision
    assert first.merge_plans[merge].slots['path_a'].cardinality=='one'
    assert second.merge_plans[merge].slots['path_a'].cardinality=='many'
    assert e.memory.read_transient(merge,'default')=={'path_a':['A contents','B contents']}
    assert not e.errors()


def sequential_splits(e, count):
    previous = e.start
    forks, merges = [], []
    for _ in range(count):
        fork, merge = e.add('branch_node'), e.add('merge_node')
        e.wire(previous, fork)
        for port in ['path_a', 'path_b']:
            step = e.add('no_op_node')
            e.wire(fork, step, port); e.wire(step, merge, slot=port)
        forks.append(fork); merges.append(merge); previous = merge
    show = e.add('text_output_node', label='', template='{input}')
    end = e.add('end_node', record_line=False)
    e.wire(previous, show); e.wire(show, end)
    return forks, merges, show, end


@pytest.mark.asyncio
@pytest.mark.parametrize('count,limit', [(2, 5), (3, 2), (6, 5), (8, 5), (8, 1)])
async def test_sequential_splits_open_new_groups_and_restore_opening_depth(count, limit):
    e = Engine()
    forks, merges, _, _ = sequential_splits(e, count)
    e.master._configuration_manager._settings['max_branch_depth'] = limit
    await start(e); await e.finish()
    plans = e.master.run_context.merge_plans
    assert [plans[mid].fork_node_id for mid in merges] == forks
    assert all(plan.slots['path_a'].producers == ((0,),) for plan in plans.values())
    expected = 'seed'
    for _ in range(count): expected = {'path_a':expected, 'path_b':expected}
    assert not e.errors() and e.memory.read_transient(merges[-1], 'default') == expected
    assert all(len(e.done(mid)) == 1 for mid in merges)
    assert max(r['depth'] for r in e.registered) == 1


def refused_chain(e):
    forks, merges, show, end = sequential_splits(e, 1)
    second = e.add('merge_node')
    e.wm.disconnect(merges[0], 'default', show, 'input')
    e.wire(merges[0], second, slot='path_a'); e.wire(second, show)
    return second


@pytest.mark.asyncio
async def test_merge_after_merge_without_a_new_split_is_refused_before_start():
    e = Engine(); second = refused_chain(e)
    result = validate_workflow(e.wm, e.factory)
    messages=[x['message'] for x in result['errors'] if x['code']=='flow_needs_review' and x['node_id']==second]
    assert messages and 'Connect these paths to one Merge.' in messages[0]
    assert all(word not in message.lower() for message in messages
               for word in ('family','arrival','lineage','shape needs review'))
    with pytest.raises(MergePlanError, match='earlier Merge'):
        await e.master.start_workflow(unattended='terminate_branch')
    assert e.master.current_run_id is None and not e.master._supervisor_tasks


@pytest.mark.asyncio
async def test_inner_join_cannot_feed_outer_join_before_start():
    e = Engine()
    fork, nested, inner, outer = [e.add(t) for t in ['branch_node','branch_node','merge_node','merge_node']]
    a, c, d = [e.add('no_op_node') for _ in range(3)]
    e.wire(e.start,fork);e.wire(fork,a,'path_a');e.wire(fork,nested,'path_b')
    e.wire(nested,c,'path_a');e.wire(nested,d,'path_b')
    e.wire(c,inner,slot='path_a');e.wire(d,inner,slot='path_b')
    e.wire(a,outer,slot='path_a');e.wire(inner,outer,slot='path_b')
    result=validate_workflow(e.wm,e.factory)
    assert any(x['code']=='flow_needs_review' and x['node_id']==outer for x in result['errors'])
    with pytest.raises(MergePlanError): await e.master.start_workflow(unattended='terminate_branch')
    assert e.master.current_run_id is None


@pytest.mark.asyncio
async def test_two_joins_on_separate_paths_of_one_split_are_refused():
    e = Engine(); fork = e.add('branch_node',branch_count=4)
    first, second = e.add('merge_node'),e.add('merge_node')
    e.wire(e.start,fork)
    for port,target,slot in [('path_a',first,'path_a'),('path_b',first,'path_b'),
                              ('path_c',second,'path_a'),('path_d',second,'path_b')]:
        step=e.add('no_op_node');e.wire(fork,step,port);e.wire(step,target,slot=slot)
    result=validate_workflow(e.wm,e.factory)
    assert {x['node_id'] for x in result['errors'] if x['code']=='flow_needs_review'}=={first,second}
    with pytest.raises(MergePlanError,match='different Merges'):
        await e.master.start_workflow(unattended='terminate_branch')


@pytest.mark.asyncio
async def test_app_run_shows_refusal_and_can_run_after_repair():
    from frontend.app import AttackOfTheNodesApp
    e = Engine(); second = refused_chain(e)
    app=AttackOfTheNodesApp(e.bus,e.factory,e.wm,e.memory,e.master)
    async with app.run_test(size=(100, 40), notifications=True) as pilot:
        await pilot.press('ctrl+r'); await pilot.pause(0.3)
        from frontend.screens.editor import EditorScreen
        from frontend.widgets.validation_panel import ValidationPanel
        assert isinstance(app.screen, EditorScreen)
        panel=app.screen.query_one(ValidationPanel)
        assert panel.display and panel.region.width>0
        assert any('earlier Merge' in issue['message'] for issue in panel.issues)
        assert e.master.current_run_id is None
        # Repair the refused graph and press Run again through the same app.
        incoming=e.wm.get_node_data(second)['connections']['inputs'][0]
        outgoing=e.wm.get_node_data(second)['connections']['outputs'][0]
        e.wm.disconnect(incoming['source_node_id'],incoming['source_port'],second,incoming['target_port'])
        e.wm.disconnect(second,outgoing['source_port'],outgoing['target_node_id'],outgoing['target_port'])
        e.wire(incoming['source_node_id'],outgoing['target_node_id'],slot=outgoing['target_port'])
        e.wm.delete_node(second)
        await pilot.press('ctrl+r');await pilot.pause(0.3)
        await e.finish()
        assert e.master.current_run_id is not None and not e.errors()
        assert e.master.run_outputs


@pytest.mark.asyncio
async def test_refused_subworkflow_has_a_typed_routable_error():
    child=Engine();refused_chain(child);child.wm.set_callable(True)
    SaveManager(child.wm).save_current_workflow()
    parent=Engine()
    call=parent.add('subworkflow_node',workflow_id=child.wm.workflow_id,inputs=[],results=[])
    show=parent.add('text_output_node',label='',template='{input[code]}')
    end=parent.add('end_node',record_line=False)
    parent.wire(parent.start,call);parent.wire(call,end)
    parent.wire(call,show,'error');parent.wire(show,end)
    await start(parent);await parent.finish()
    assert len(parent.errors())==1
    error=parent.errors()[0]
    assert error['node_id']==call and error['code']=='child_flow_invalid' and error['handled']
    assert 'earlier Merge' in error['message']
    assert parent.memory.read_transient(call,'error')['retryable'] is False
    assert parent.master.run_outputs==['child_flow_invalid']
    assert parent.master.call_tree.live==0


@pytest.mark.asyncio
async def test_real_nesting_beyond_default_depth_still_refuses_the_whole_batch():
    e=Engine();previous=e.start;forks=[]
    for _ in range(6):
        fork=e.add('branch_node');forks.append(fork)
        e.wire(previous,fork,'path_a' if previous!=e.start else 'default')
        end=e.add('end_node',record_line=False);e.wire(fork,end,'path_b')
        previous=fork
    last=e.add('text_output_node',label='',template='must not run');e.wire(previous,last,'path_a')
    result = validate_workflow(e.wm, e.factory)
    assert any(x['code'] == 'branch_depth_exceeded' and x['node_id'] == forks[-1]
               for x in result['errors'])
    with pytest.raises(MergePlanError, match='nesting depth 6'):
        await e.master.start_workflow(unattended='terminate_branch')
    assert not e.registered and e.master.run_context is None
    assert not e.master.run_outputs

"""Collecting Merge: actual supervisors, delivery frames and run-scoped barriers.

Slot/producer declarations are explicit graph fixtures. They deliberately do
not implement the shared graph analyser being delivered in parallel.
"""
import asyncio
from copy import deepcopy

import pytest

from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import NODE_EXECUTION_UPDATE, SUPERVISOR_REGISTER, SUPERVISOR_TERMINATING
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_base import Node
from backend.node_factory import NodeFactory
from backend.run_context import MergePlan, MergeSlot
from backend.workflow_map import WorkflowMap


class Engine:
    def __init__(self):
        self.bus = EventBus()
        self.factory = NodeFactory()
        self.wm = WorkflowMap(self.factory, self.bus)
        self.memory = MemoryBank(self.bus)
        self.master = MasterState(self.wm, self.memory, self.bus, configuration_manager=ConfigurationManager())
        self.wm.create_new('Collect arrivals')
        self.events, self.registered, self.terminated, self.seen = [], [], [], []
        self.bus.subscribe(NODE_EXECUTION_UPDATE, lambda e: self.events.append(dict(e)))
        self.bus.subscribe(SUPERVISOR_REGISTER, lambda e: self.registered.append(dict(e)))
        self.bus.subscribe(SUPERVISOR_TERMINATING, lambda e: self.terminated.append(dict(e)))
        self.entered, self.gates, self.plans = {}, {}, {}
        engine = self

        class Step(Node):
            node_type = 'merge_fixture_step'
            input_ports, output_ports = ['input'], ['default']
            default_config, config_schema = {}, {}

            async def execute(self, context):
                name = self.config['name']
                engine.entered.setdefault(name, asyncio.Event()).set()
                if self.config.get('write_first'):
                    context.memory_bank.store_transient(context.node_id, 'default', context.inputs.get('input'))
                if name in engine.gates:
                    await engine.gates[name].wait()
                if self.config.get('fail'):
                    raise ValueError(self.config['fail'])
                if self.config.get('sink'):
                    supervisor = engine.master._supervisors[context.branch_id]
                    engine.seen.append(dict(value=deepcopy(context.inputs), branch=context.branch_id,
                                            depth=supervisor.depth, lineage=supervisor.lineage))
                data = {} if self.config.get('missing') or self.config.get('write_first') else {
                    'default': self.config['value'] if 'value' in self.config else context.inputs.get('input')}
                context.signal_done({'data': data})

        self.factory._node_registry[Step.node_type] = Step
        self.start = self.add('start_node', greeting='seed')

    def add(self, kind, **config):
        node = self.wm.add_node(kind)
        if config:
            self.wm.update_node_config(node, config)
        return node

    def step(self, name, *, hold=False, **config):
        self.entered[name] = asyncio.Event()
        if hold:
            self.gates[name] = asyncio.Event()
        return self.add('merge_fixture_step', name=name, **config)

    def wire(self, source, target, port='default', slot='input'):
        self.wm.connect(source, port, target, slot)

    def plan(self, merge, fork, **slots):
        self.plans[merge] = MergePlan(fork, {slot: MergeSlot(shape, tuple(paths))
                                          for slot, (shape, paths) in slots.items()})

    async def start_run(self, **kwargs):
        assert await self.master.start_workflow(merge_plans=self.plans, unattended=kwargs.pop('unattended', 'terminate_branch'), **kwargs)

    async def finish(self):
        await asyncio.wait_for(self.master.wait_for_completion(), 3)
        assert not self.master._supervisor_tasks
        assert not self.master.run_context.merge_groups
        assert not self.master.run_context.merge_barriers
        assert not self.master.run_context.branch_groups

    async def at_merge(self, merge, count=1):
        async def ready():
            while sum(e['node_id'] == merge and e['status'] == 'running' for e in self.events) < count:
                await asyncio.sleep(0)
        await asyncio.wait_for(ready(), 2)

    def done(self, node):
        return [e for e in self.events if e['node_id'] == node and e['status'] == 'done']

    def errors(self):
        return self.master.error_handler.get_errors_for_run(self.master.current_run_id)


def flat(engine, left='A', right='B', *, missing_right=False):
    fork = engine.add('branch_node')
    a = engine.step('A', value=left, hold=True)
    b = engine.step('B', value=right, missing=missing_right, hold=True)
    merge = engine.add('merge_node')
    sink = engine.step('sink', sink=True)
    engine.wire(engine.start, fork)
    engine.wire(fork, a, 'path_a')
    engine.wire(fork, b, 'path_b')
    engine.wire(a, merge, slot='path_a')
    engine.wire(b, merge, slot='path_b')
    engine.wire(merge, sink)
    engine.plan(merge, fork, path_a=('one', ((0,),)), path_b=('one', ((1,),)))
    return fork, a, b, merge, sink


@pytest.mark.asyncio
async def test_two_real_files_collect_in_slot_order_after_reversed_arrival(tmp_path):
    e = Engine()
    fork, a, b, merge, sink = flat(e)
    for label, source, slot, text in [('a', a, 'path_a', 'A contents\n'), ('b', b, 'path_b', 'B contents\n')]:
        path = tmp_path/(label+'.txt')
        path.write_text(text)
        reader = e.add('file_reader_node', file_path=str(path), input_source='Configured')
        e.wm.disconnect(source, 'default', merge, slot)
        e.wire(source, reader)
        e.wire(reader, merge, slot=slot)
    await e.start_run()
    await e.entered['A'].wait()
    await e.entered['B'].wait()
    e.gates['B'].set()
    await e.at_merge(merge)
    assert merge not in e.master.completed_nodes and not e.seen
    # An unrelated transient value must never count as a path arrival.
    e.memory.store_transient(a, 'default', 'STALE, not the file value')
    e.gates['A'].set()
    await e.finish()
    assert e.errors() == []
    assert e.seen[0]['value'] == {'input': {'path_a': 'A contents\n', 'path_b': 'B contents\n'}}
    assert len(e.done(merge)) == len(e.done(sink)) == 1
    assert sum(t['reason'] == 'absorbed' for t in e.terminated) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('value', [None, False, 0, '', [], {}])
async def test_present_falsy_values_are_collected_and_missing_is_omitted(value):
    e = Engine()
    _, _, _, merge, _ = flat(e, left=value, missing_right=True)
    await e.start_run()
    await e.entered['A'].wait()
    e.gates['A'].set()
    e.gates['B'].set()
    await e.finish()
    assert e.errors() == []
    assert e.seen[0]['value'] == {'input': {'path_a': value}}
    assert e.memory.read_transient(merge, 'default') == {'path_a': value}


@pytest.mark.asyncio
@pytest.mark.parametrize('beacons', [False, True])
@pytest.mark.parametrize('host', ['A', 'C', 'D'])
@pytest.mark.parametrize('a_first', [False, True])
async def test_inherited_A_and_B_handoff_to_C_D_collect_and_continue_on_shallow_A(beacons, host, a_first):
    e = Engine()
    fork, nested = e.add('branch_node'), e.add('branch_node')
    a, b = e.step('A', hold=True, value='slow result'), e.step('B', hold=True, value='gathered')
    c, d = e.step('C', value='C resource'), e.step('D', value='D resource')
    merge = e.add('merge_node', selected_branch_id=host, carry_forward_branch_id=host)
    sink = e.step('sink', sink=True)
    e.wire(e.start, fork)
    e.wire(fork, a, 'path_a')
    e.wire(fork, b, 'path_b')
    e.wire(b, nested)
    e.wire(nested, c, 'path_a')
    e.wire(nested, d, 'path_b')
    for source, slot in [(a,'path_a'),(c,'path_b'),(d,'path_c')]:
        if beacons:
            beacon = e.add('branch_end_node')
            e.wire(source, beacon)
            source = beacon
        e.wire(source, merge, slot=slot)
    e.wire(merge, sink)
    e.plan(merge, fork, path_a=('one',((0,),)), path_b=('one',((1,0),)), path_c=('one',((1,1),)))
    await e.start_run()
    await e.entered['A'].wait()
    await e.entered['B'].wait()
    if a_first:
        e.gates['A'].set()
        await e.at_merge(merge)
        assert not e.done(merge) and not e.seen
        e.gates['B'].set()
    else:
        e.gates['B'].set()
        await e.at_merge(merge, 2)
        assert not e.done(merge) and not e.seen
        e.gates['A'].set()
    await e.finish()
    assert e.errors() == []
    assert len(e.seen) == 1 and e.seen[0]['depth'] == 1 and e.seen[0]['lineage'] == (0,)
    assert e.seen[0]['value'] == {'input': {'path_a':'slow result','path_b':'C resource','path_c':'D resource'}}
    assert len(e.done(merge)) == 1


@pytest.mark.asyncio
async def test_scalar_shape_is_not_guessed_without_a_graph_declaration():
    e = Engine()
    _, _, _, merge, _ = flat(e)
    e.plans.clear()
    await e.start_run()
    e.gates['A'].set()
    e.gates['B'].set()
    await e.finish()
    assert len([x for x in e.errors() if x['node_id'] == merge]) == 1
    assert e.errors()[0]['code'] == 'merge_shape_unknown'
    assert not e.seen and merge not in e.master.completed_nodes


@pytest.mark.asyncio
@pytest.mark.parametrize('left,right,missing', [(None,False,False),([1],[2],False),(0,'',False),('only',None,True)])
async def test_concurrent_same_slot_is_always_a_list_in_path_order(left,right,missing):
    e = Engine()
    fork,a,b,merge,_ = flat(e,left,right,missing_right=missing)
    e.wm.disconnect(b,'default',merge,'path_b')
    e.wire(b,merge,slot='path_a')
    e.plan(merge,fork,path_a=('many',((0,),(1,))))
    await e.start_run()
    e.memory.store_transient(b,'default','stale missing output')
    e.gates['B'].set()
    await e.at_merge(merge)
    e.gates['A'].set()
    await e.finish()
    expected = [left] if missing else [left,right]
    assert e.errors() == [] and e.seen[0]['value'] == {'input':{'path_a':expected}}


@pytest.mark.asyncio
async def test_a_many_slot_with_only_control_arrivals_is_omitted():
    e = Engine()
    fork,a,b,merge,_ = flat(e,missing_right=True)
    e.wm.update_node_config(a,dict(name='A',missing=True))
    e.wm.disconnect(b,'default',merge,'path_b')
    e.wire(b,merge,slot='path_a')
    e.plan(merge,fork,path_a=('many',((0,),(1,))))
    await e.start_run()
    e.gates['A'].set(); e.gates['B'].set()
    await e.finish()
    assert e.errors() == [] and e.seen[0]['value'] == {'input':{}}


@pytest.mark.asyncio
async def test_shared_producer_and_shared_beacon_do_not_reread_another_invocations_value():
    e = Engine()
    fork = e.add('branch_node',branch_payload_sources={'path_a':'vault:A','path_b':'vault:B'})
    shared = e.step('shared',hold=True,write_first=True)
    beacon = e.add('branch_end_node')
    merge, sink = e.add('merge_node'), e.step('sink',sink=True)
    e.wire(e.start,fork)
    e.wire(fork,shared,'path_a'); e.wire(fork,shared,'path_b')
    e.wire(shared,beacon); e.wire(beacon,merge,slot='path_a'); e.wire(merge,sink)
    e.plan(merge,fork,path_a=('many',((0,),(1,))))
    await e.start_run()
    # Initial input values, not stand-ins for a node's claimed Vault write.
    e.memory.store_persistent('A',{'name':'A'})
    e.memory.store_persistent('B',{'name':'B'})
    async def both_entered():
        while sum(x['node_id']==shared and x['status']=='running' for x in e.events)<2:
            await asyncio.sleep(0)
    await asyncio.wait_for(both_entered(),2)
    assert e.memory.read_transient(shared,'default') == {'name':'B'}
    e.gates['shared'].set()
    await e.finish()
    assert e.errors() == []
    assert e.seen[0]['value'] == {'input':{'path_a':[{'name':'A'},{'name':'B'}]}}
    assert e.memory.read_persistent('A') == {'name':'A'}


@pytest.mark.asyncio
@pytest.mark.parametrize('greeting,wanted',[('yes','Y'),('no','N')])
async def test_exclusive_routes_rejoin_one_scalar_slot_and_ignore_inactive_stale_values(greeting,wanted):
    e = Engine()
    e.wm.update_node_config(e.start,dict(greeting=greeting))
    fork, choice, merge = e.add('branch_node'), e.add('conditional_node',condition_type='equals',right_value='yes'), e.add('merge_node')
    a,y,n,sink = e.step('A',value='A'),e.step('Y',value='Y'),e.step('N',value='N'),e.step('sink',sink=True)
    e.wire(e.start,fork);e.wire(fork,a,'path_a');e.wire(a,merge,slot='path_a')
    e.wire(fork,choice,'path_b');e.wire(choice,y,'true');e.wire(choice,n,'false')
    e.wire(y,merge,slot='path_b');e.wire(n,merge,slot='path_b');e.wire(merge,sink)
    e.plan(merge,fork,path_a=('one',((0,),)),path_b=('one',((1,),)))
    await e.start_run()
    e.memory.store_transient(y if wanted=='N' else n,'default','STALE')
    await e.finish()
    assert e.errors() == [] and e.seen[0]['value'] == {'input':{'path_a':'A','path_b':wanted}}


@pytest.mark.asyncio
@pytest.mark.parametrize('port',['path_a','path_b'])
async def test_legacy_conditional_branch_registers_only_its_chosen_child(port):
    e = Engine()
    fork = e.add('branch_node',condition=port+'_only')
    # Explicit legacy config: no branch_count. Configs containing it intentionally
    # select all paths; this established behavior is not changed by this block.
    merge, sink = e.add('merge_node'),e.step('sink',sink=True)
    a,b = e.step('A',value='A'),e.step('B',value='B')
    e.wire(e.start,fork);e.wire(fork,a,'path_a');e.wire(fork,b,'path_b')
    e.wire(a,merge,slot='path_a');e.wire(b,merge,slot='path_a');e.wire(merge,sink)
    e.plan(merge,fork,path_a=('one',((0,),(1,))))
    await e.start_run();await e.finish()
    assert e.errors() == []
    assert e.seen[0]['value'] == {'input':{'path_a':'A' if port=='path_a' else 'B'}}
    assert len([r for r in e.registered if r['depth']>0]) == 1


@pytest.mark.asyncio
async def test_a_wait_on_merge_wakes_only_after_the_continuing_arrival_publishes():
    e = Engine()
    fork,a,b,merge,sink = flat(e)
    e.wm.update_node_config(fork,dict(branch_count=3))
    wait = e.add('wait_until_node',target_node_ids=[merge],timeout_seconds=0)
    reader = e.step('wait-reader',sink=True)
    e.wire(fork,wait,'path_c');e.wire(wait,reader)
    await e.start_run()
    e.gates['B'].set()
    await e.at_merge(merge)
    assert wait not in e.master.completed_nodes and not e.seen
    e.gates['A'].set();await e.finish()
    assert e.errors() == [] and len(e.done(merge))==1 and len(e.done(wait))==1
    assert e.memory.read_transient(merge,'default') == {'path_a':'A','path_b':'B'}
    done = [x['node_id'] for x in e.events if x['status']=='done']
    assert done.index(merge)<done.index(wait)
    assert (e.master.current_run_id,merge,1) in e.master.run_context.node_completions


@pytest.mark.asyncio
async def test_a_plain_end_settles_an_independent_side_path_without_a_value():
    e = Engine()
    fork,a,b,merge,_ = flat(e)
    e.wm.disconnect(b,'default',merge,'path_b')
    end = e.add('end_node')
    e.wire(b,end)
    await e.start_run()
    e.gates['A'].set();await e.at_merge(merge)
    assert not e.seen
    e.gates['B'].set();await e.finish()
    assert e.errors()==[] and e.seen[0]['value']=={'input':{'path_a':'A'}}


@pytest.mark.asyncio
async def test_stop_during_join_is_quiet_and_leaves_no_partial_output():
    e = Engine()
    _,_,_,merge,_ = flat(e)
    await e.start_run()
    run = e.master.run_context
    e.gates['A'].set();await e.at_merge(merge)
    e.master.stop();await e.finish()
    assert run.stop_requested and e.errors()==[]
    assert not e.seen and merge not in e.master.completed_nodes
    absent=object()
    assert e.memory.read_transient(merge,'default',absent) is absent
    assert not [x for x in e.events if x['node_id']==merge and x['status'] in ('done','errored','skipped')]


@pytest.mark.asyncio
@pytest.mark.parametrize('before_wait',[False,True])
async def test_a_failed_member_fails_merge_once_and_releases_peers(before_wait):
    e=Engine()
    _,_,b,merge,_=flat(e)
    e.wm.update_node_config(b,dict(name='B',fail='local resource failed'))
    await e.start_run()
    if before_wait:
        e.gates['B'].set()
        await e.entered['B'].wait()
        while not e.errors(): await asyncio.sleep(0)
        e.gates['A'].set()
    else:
        e.gates['A'].set();await e.at_merge(merge)
        e.gates['B'].set()
    await e.finish()
    failures=[x for x in e.errors() if x['node_id']==merge]
    assert len(failures)==1 and failures[0]['code']=='merge_member_failed',e.errors()
    assert 'path_b' in failures[0]['message'] and 'slot' in failures[0]['message']
    assert 'local resource failed' in failures[0]['message']
    assert not e.seen and merge not in e.master.completed_nodes
    assert len([x for x in e.events if x['node_id']==merge and x['status']=='errored'])==1


@pytest.mark.asyncio
async def test_an_error_route_that_recovers_and_arrives_is_not_a_terminal_member_failure():
    e=Engine()
    fork,a,b,merge,_=flat(e)
    e.wm.update_node_config(b,dict(name='B',fail='recover me'))
    recovered=e.step('recovered',value=False)
    e.wm.disconnect(b,'default',merge,'path_b')
    e.wire(b,recovered,'error');e.wire(recovered,merge,slot='path_b')
    await e.start_run();e.gates['A'].set();e.gates['B'].set();await e.finish()
    assert len(e.errors())==1 and e.errors()[0]['handled']
    assert e.seen[0]['value']=={'input':{'path_a':'A','path_b':False}}
    assert len(e.done(merge))==1


@pytest.mark.asyncio
async def test_depth_refusal_is_an_error_at_the_branch_and_launches_no_children():
    e=Engine()
    fork,_,_,_,_=flat(e)
    e.master._configuration_manager._settings['max_branch_depth']=0
    show=e.add('text_output_node',label='',template='{input[code]}')
    end=e.add('end_node',record_line=False)
    e.wire(fork,show,'error');e.wire(show,end)
    await e.start_run();await e.finish()
    assert len(e.registered)==1
    assert len(e.errors())==1 and e.errors()[0]['node_id']==fork
    assert e.errors()[0]['code']=='branch_depth_exceeded' and e.errors()[0]['handled']
    assert 'no paths were launched' in e.errors()[0]['message']
    assert e.memory.read_persistent('output_log')==['branch_depth_exceeded']
    assert fork not in e.master.completed_nodes


@pytest.mark.asyncio
@pytest.mark.parametrize('first', ['A', 'B', 'simultaneous'])
async def test_equal_depth_uses_first_arrival_and_simultaneous_delivery_continues_once(first):
    e = Engine()
    _, _, _, merge, _ = flat(e)
    await e.start_run()
    await e.entered['A'].wait(); await e.entered['B'].wait()
    if first == 'simultaneous':
        e.gates['A'].set(); e.gates['B'].set()
    else:
        e.gates[first].set()
        await e.at_merge(merge)
        e.gates['B' if first == 'A' else 'A'].set()
    await e.finish()
    assert not e.errors() and len(e.seen) == len(e.done(merge)) == 1
    assert e.seen[0]['lineage'] == ((1,) if first == 'B' else (0,))
    assert e.seen[0]['value'] == {'input': {'path_a': 'A', 'path_b': 'B'}}


@pytest.mark.asyncio
@pytest.mark.parametrize('before_wait', [False, True])
async def test_whole_workflow_abort_records_the_merge_failure_once(before_wait):
    e = Engine()
    _, _, b, merge, _ = flat(e)
    e.wm.update_node_config(b, dict(name='B', fail='resource unavailable'))
    await e.start_run(unattended='terminate_workflow')
    if not before_wait:
        e.gates['A'].set(); await e.at_merge(merge)
    e.gates['B'].set()
    await e.finish()
    failures = [x for x in e.errors() if x['node_id'] == merge]
    assert len(failures) == 1 and failures[0]['code'] == 'merge_member_failed'
    assert 'path_b' in failures[0]['message']
    assert not e.seen and not e.done(merge)
    assert [x['status'] for x in e.events if x['node_id'] == merge and x['status'] != 'running'] == ['errored']


@pytest.mark.asyncio
async def test_failed_merge_releases_wait_until_without_completion():
    e = Engine()
    fork, _, b, merge, _ = flat(e)
    e.wm.update_node_config(fork, dict(branch_count=3))
    e.wm.update_node_config(b, dict(name='B', fail='missing resource'))
    wait = e.add('wait_until_node', target_node_ids=[merge], timeout_seconds=0)
    e.wire(fork, wait, 'path_c')
    await e.start_run()
    e.gates['A'].set(); await e.at_merge(merge)
    e.gates['B'].set(); await e.finish()
    assert not e.done(wait) and not e.done(merge) and not e.seen
    assert len([x for x in e.errors() if x['node_id'] == wait and x['code'] == 'engine.upstream_unreachable']) == 1


@pytest.mark.asyncio
async def test_new_run_cannot_receive_a_previous_runs_arrivals_or_callbacks():
    e = Engine()
    _, _, b, merge, _ = flat(e)
    await e.start_run()
    old = e.master.run_context
    e.gates['A'].set(); await e.at_merge(merge)
    parked = next(s for s in old.live_supervisors.values() if s.current_node_id == merge)
    old_delivery, old_branch = parked.delivery, parked.branch_id
    old_key = next(iter(old.merge_groups))
    assert old_key[0] == old.run_id and old_key[2] == 1
    assert all(a.pass_number == 1 for barrier in old.merge_barriers.values() for a in barrier.arrivals.values())
    e.master.stop(); await e.finish()
    e.events.clear()
    e.gates = {'A': asyncio.Event(), 'B': asyncio.Event()}
    e.entered = {'A': asyncio.Event(), 'B': asyncio.Event()}
    e.wm.update_node_config(b, dict(name='B', value='new B'))
    await e.start_run()
    new = e.master.run_context
    assert new.run_id != old.run_id and not new.node_completions
    # These are the real previous supervisor's run-bound callbacks and events.
    assert await parked._wait_for_merge(merge, old_branch, old_delivery, 1, 0) == {'arrival_outcome': 'cancelled'}
    await parked._mark_node_completed(merge)
    parked._publish_terminating()
    parked._fail('stale callback')
    assert merge not in new.completed_nodes and e.master.state.value == 'RUNNING'
    e.gates['A'].set(); await e.at_merge(merge)
    assert next(iter(new.merge_groups)) != old_key
    assert not e.seen
    e.gates['B'].set(); await e.finish()
    assert not e.errors() and e.seen[0]['value']['input']['path_b'] == 'new B'
    assert len(e.done(merge)) == 1


@pytest.mark.asyncio
async def test_later_fork_uses_shallow_winner_depth_and_fresh_group_receipts():
    e = Engine()
    _, _, _, merge, sink = flat(e)
    fork2 = e.add('branch_node')
    c, d, merge2, sink2 = e.step('C', value='C'), e.step('D', value='D'), e.add('merge_node'), e.step('sink2', sink=True)
    e.wire(sink, fork2)
    e.wire(fork2, c, 'path_a'); e.wire(fork2, d, 'path_b')
    e.wire(c, merge2, slot='path_a'); e.wire(d, merge2, slot='path_b'); e.wire(merge2, sink2)
    e.plan(merge2, fork2, path_a=('one', ((0,),)), path_b=('one', ((1,),)))
    e.master._configuration_manager._settings['max_branch_depth'] = 2
    await e.start_run()
    e.gates['B'].set(); await e.at_merge(merge)
    e.gates['A'].set(); await e.finish()
    assert not e.errors() and len(e.seen) == 2
    assert [r['depth'] for r in e.seen] == [1, 2]
    assert e.seen[1]['value'] == {'input': {'path_a': 'C', 'path_b': 'D'}}
    assert len(e.done(merge)) == len(e.done(merge2)) == 1


@pytest.mark.asyncio
async def test_merge_slots_use_numeric_order_after_z():
    e = Engine()
    fork, a, b, merge, _ = flat(e)
    e.wm.update_node_config(merge, dict(input_slots=27))
    e.wm.disconnect(a, 'default', merge, 'path_a'); e.wire(a, merge, slot='path_z')
    e.wm.disconnect(b, 'default', merge, 'path_b'); e.wire(b, merge, slot='path_aa')
    e.plan(merge, fork, path_aa=('one', ((1,),)), path_z=('one', ((0,),)))
    await e.start_run()
    e.gates['A'].set(); e.gates['B'].set(); await e.finish()
    assert not e.errors() and list(e.seen[0]['value']['input']) == ['path_z', 'path_aa']


@pytest.mark.asyncio
@pytest.mark.parametrize('value', [None, False, 0, '', [], {}])
async def test_merge_outside_a_split_passes_through_the_actual_value(value):
    e = Engine()
    source, merge, sink = e.step('source', value=value), e.add('merge_node'), e.step('sink', sink=True)
    e.wire(e.start, source); e.wire(source, merge, slot='path_a'); e.wire(merge, sink)
    await e.start_run(); await e.finish()
    assert not e.errors() and e.seen[0]['value'] == {'input': value}


@pytest.mark.asyncio
async def test_terminal_failure_marks_merge_even_when_no_member_ever_arrives():
    e = Engine()
    _, a, b, merge, _ = flat(e)
    e.wm.update_node_config(a, dict(name='A', fail='A unavailable'))
    e.wm.update_node_config(b, dict(name='B', fail='B unavailable'))
    await e.start_run()
    e.gates['A'].set(); e.gates['B'].set(); await e.finish()
    failures = [x for x in e.errors() if x['node_id'] == merge]
    assert len(failures) == 1 and failures[0]['code'] == 'merge_member_failed'
    assert not e.seen and not e.done(merge)
    assert [x['status'] for x in e.events if x['node_id'] == merge] == ['errored']


@pytest.mark.asyncio
async def test_a_duplicate_receipt_after_continuation_cannot_continue_again():
    e = Engine()
    _, _, _, merge, sink = flat(e)
    e.gates['sink'] = asyncio.Event()
    await e.start_run()
    e.gates['A'].set(); await e.at_merge(merge)
    winner = next(s for s in e.master.run_context.live_supervisors.values() if s.current_node_id == merge)
    delivery, visit = winner.delivery, winner._visit_index
    e.gates['B'].set(); await e.entered['sink'].wait()
    duplicate = await winner._wait_for_merge(merge, winner.branch_id, delivery, visit, 0)
    assert duplicate == {'arrival_outcome': 'absorbed'}
    assert len(e.done(merge)) == 1
    e.gates['sink'].set(); await e.finish()
    assert len(e.seen) == 1 and not e.errors()


@pytest.mark.asyncio
async def test_unwired_branch_paths_still_end_without_a_depth_refusal():
    e = Engine()
    fork = e.add('branch_node')
    e.wire(e.start, fork)
    e.master._configuration_manager._settings['max_branch_depth'] = 0
    await e.start_run(); await e.finish()
    assert not e.errors() and len(e.done(fork)) == 1 and len(e.registered) == 1


@pytest.mark.asyncio
async def test_merge_outside_a_split_preserves_a_control_only_delivery_as_missing():
    e = Engine()
    source = e.step('source', missing=True, hold=True)
    merge, sink = e.add('merge_node'), e.step('sink', sink=True)
    e.wire(e.start, source); e.wire(source, merge, slot='path_a'); e.wire(merge, sink)
    await e.start_run(); await e.entered['source'].wait()
    e.memory.store_transient(source, 'default', 'stale source')
    e.memory.store_transient(merge, 'default', 'stale Merge')
    e.gates['source'].set(); await e.finish()
    assert not e.errors() and e.seen[0]['value'] == {}


@pytest.mark.asyncio
async def test_concurrent_deliveries_cannot_silently_change_a_declared_scalar_shape():
    e = Engine()
    fork, _, b, merge, _ = flat(e)
    e.wm.disconnect(b, 'default', merge, 'path_b'); e.wire(b, merge, slot='path_a')
    e.plan(merge, fork, path_a=('one', ((0,), (1,))))
    await e.start_run(); e.gates['A'].set(); e.gates['B'].set(); await e.finish()
    assert len(e.errors()) == 1 and e.errors()[0]['code'] == 'merge_shape_invalid'
    assert not e.seen and not e.done(merge)

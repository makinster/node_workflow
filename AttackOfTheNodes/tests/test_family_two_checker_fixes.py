"""Family 2 checker regressions through shared checks and automatic run plans."""
import asyncio
import json

import pytest

from backend.authoring import check_workflow_spec
from backend.branch_health import VALID, derive_branch_health
from backend.flow_behaviors import analyze_flow, MergePlanError
from backend.meta_workflow import check
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow
from tests.test_flow_behaviors import graph, wire
from tests.test_merge_arrival_runtime import Engine


def codes(report):
    return {f.code for f in report.findings if f.level == 'error'}


def loop_wait(target='wait'):
    return graph(dict(start='start_node', wait='wait_until_node', end='end_node', loop='sleep_node'),
                 [('start','default','wait','input'), ('wait','default','end','input'),
                  ('loop','default','loop','input')], {'wait': {'target_node_ids': target, 'timeout_seconds': 0}})


@pytest.mark.parametrize('target,code', [('wait','impossible_wait'), ('missing','wait_target_missing'), ('end','impossible_wait')])
def test_loop_does_not_hide_wait_errors(target, code):
    report = analyze_flow(loop_wait(target))
    assert report.back_edges
    assert code in codes(report)


def test_loop_does_not_hide_mutual_wait_or_merge_findings():
    nodes = loop_wait('other')
    nodes['other'] = dict(type='wait_until_node', config={'target_node_ids':'wait'}, connections={'inputs':[], 'outputs':[]})
    nodes['split'] = dict(type='branch_node', config={}, connections={'inputs':[], 'outputs':[]})
    nodes['start']['connections']['outputs'].clear()
    wire(nodes,'start','default','split')
    wire(nodes,'split','path_a','wait'); wire(nodes,'split','path_b','other')
    assert 'impossible_wait' in codes(analyze_flow(nodes))
    nodes['merge'] = dict(type='merge_node',config={},connections={'inputs':[],'outputs':[]})
    wire(nodes,'end','default','merge','path_a')
    assert {'impossible_wait','flow_needs_review'} <= codes(analyze_flow(nodes))


def nested_graph(count):
    nodes = graph(dict(start='start_node', end='end_node'), [])
    previous, port = 'start', 'default'
    for i in range(count):
        nid = f'fork{i}'
        nodes[nid] = dict(type='branch_node',config={'branch_count':2},connections={'inputs':[],'outputs':[]})
        wire(nodes,previous,port,nid)
        wire(nodes,nid,'path_b','end')
        previous, port = nid, 'path_a'
    wire(nodes,previous,port,'end')
    return nodes


@pytest.mark.parametrize('draft',[False,True])
def test_depth_limit_is_effective_and_shared(draft):
    assert 'branch_depth_exceeded' in codes(analyze_flow(nested_graph(3),draft=draft,max_branch_depth=2))
    assert analyze_flow(nested_graph(2),draft=draft,max_branch_depth=2).success


def merge_spec(kind='text_output_node', template='{input[path_c]}'):
    return dict(format='aotn-workflow/1',name='Merge field check',nodes={
        'start': {'type':'start_node'}, 'split': {'type':'branch_node','config':{'branch_count':2}},
        'merge': {'type':'merge_node'}, 'format': {'type':kind,'config':{'template':template}},
        'end': {'type':'end_node','config':{'record_line':False}}},connections=[
        {'from':'start.default','to':'split.input'},
        {'from':'split.path_a','to':'merge.path_a'}, {'from':'split.path_b','to':'merge.path_b'},
        {'from':'merge.default','to':'format.input'}, {'from':'format.default','to':'end.input'}])


@pytest.mark.parametrize('kind',['text_output_node','concat_node'])
def test_missing_merge_slot_is_refused_and_reaches_redraft(kind):
    spec=merge_spec(kind)
    result=check_workflow_spec(NodeFactory(),spec)
    assert not result['ok']
    assert any(d['code']=='merge_slot_unconnected' and 'path_c' in d['message'] for d in result['diagnostics'])


@pytest.mark.asyncio
async def test_plain_missing_slot_reason_reaches_check_node():
    with pytest.raises(NodeError) as caught:
        await check(NodeFactory(),json.dumps(merge_spec()),64000)
    assert 'path_c' in str(caught.value) and 'Merge' in str(caught.value)
    assert 'not connected' in str(caught.value)


def test_recovering_route_has_valid_health():
    nodes=graph(dict(start='start_node',split='branch_node',a='file_reader_node',recovery='concat_node',merge='merge_node'),
        [('start','default','split','input'), ('split','path_a','a','input'),
         ('split','path_b','merge','path_b'), ('a','default','merge','path_a'),
         ('a','error','recovery','input'), ('recovery','default','merge','path_a')])
    assert analyze_flow(nodes).success
    assert all(h.state==VALID for h in derive_branch_health(nodes))


@pytest.mark.asyncio
async def test_self_wait_with_disconnected_loop_refuses_normal_startup():
    e=Engine();wait=e.add('wait_until_node',timeout_seconds=0);end=e.add('end_node',record_line=False)
    e.wm.update_node_config(wait,dict(target_node_ids=[wait],timeout_seconds=0))
    loop=e.add('sleep_node',duration=0.001)
    e.wire(e.start,wait);e.wire(wait,end);e.wire(loop,loop)
    assert 'impossible_wait' in {x['code'] for x in validate_workflow(e.wm,e.factory)['errors']}
    with pytest.raises(MergePlanError,match='itself'):
        await e.master.start_workflow(unattended='terminate_branch')
    assert not e.registered and e.master.run_context is None


@pytest.mark.asyncio
async def test_valid_wait_still_runs_with_disconnected_loop():
    e=Engine();fork=e.add('branch_node');writer=e.step('writer',value='ready')
    wait=e.add('wait_until_node',target_node_ids=[writer],timeout_seconds=0)
    end=e.add('end_node',record_line=False);loop=e.add('sleep_node',duration=0.001)
    e.wire(e.start,fork);e.wire(fork,writer,'path_a');e.wire(writer,end)
    e.wire(fork,wait,'path_b');e.wire(wait,end);e.wire(loop,loop)
    assert not validate_workflow(e.wm,e.factory)['errors']
    await e.master.start_workflow(unattended='terminate_branch');await e.finish()
    assert not e.errors() and len(e.done(wait))==1


@pytest.mark.parametrize('template', ['{input[path_a]}', '{input[path_a][0]}', '{input[other]}',
                                      '{{input[path_c]}}', '{input}', '{input[path_c', '{input:{width}}'])
def test_slot_check_does_not_guess_other_templates(template):
    result=check_workflow_spec(NodeFactory(),merge_spec(template=template))
    assert not any(x['code']=='merge_slot_unconnected' for x in result['diagnostics'])


@pytest.mark.parametrize('mode',['vault','prompt','alternative_input','standalone'])
def test_slot_check_requires_a_proved_merge_payload(mode):
    spec=merge_spec()
    if mode=='vault':spec['nodes']['format']['config'].update(input_source='Vault',input_vault_key='other')
    if mode=='prompt':spec['nodes']['format']['config']['request_user_input']=True
    if mode=='alternative_input':
        spec['nodes']['other']={'type':'concat_node','config':{'template':'other'}}
        spec['connections'].append({'from':'other.default','to':'format.input'})
    if mode=='standalone':
        spec['connections']=[{'from':'start.default','to':'merge.path_a'},
                             {'from':'merge.default','to':'format.input'},
                             {'from':'format.default','to':'end.input'}]
    result=check_workflow_spec(NodeFactory(),spec)
    assert not any(x['code']=='merge_slot_unconnected' for x in result['diagnostics'])


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['text_output_node','concat_node'])
async def test_valid_direct_merge_templates_run(kind):
    e=Engine();fork=e.add('branch_node');merge=e.add('merge_node')
    formatter=e.add(kind,template='{input[path_a]}|{input[path_b]}',label='') if kind=='text_output_node' else e.add(kind,template='{input[path_a]}|{input[path_b]}')
    sink=e.step('sink',sink=True)
    e.wire(e.start,fork);e.wire(fork,merge,'path_a','path_a');e.wire(fork,merge,'path_b','path_b')
    e.wire(merge,formatter);e.wire(formatter,sink)
    assert not validate_workflow(e.wm,e.factory)['errors']
    await e.master.start_workflow(unattended='terminate_branch');await e.finish()
    assert not e.errors() and e.seen[0]['value']=={'input':'seed|seed'}
    assert len(e.done(merge))==1


@pytest.mark.asyncio
async def test_connected_slot_with_missing_value_is_not_statically_refused():
    e=Engine();fork=e.add('branch_node');merge=e.add('merge_node')
    missing=e.step('missing',missing=True);formatter=e.add('concat_node',template='{input[path_b]}')
    e.wire(e.start,fork);e.wire(fork,merge,'path_a','path_a');e.wire(fork,missing,'path_b')
    e.wire(missing,merge,slot='path_b');e.wire(merge,formatter)
    assert not validate_workflow(e.wm,e.factory)['errors']
    await e.master.start_workflow(unattended='terminate_branch');await e.finish()
    # Presence is a runtime question: this deliberate omission still errors there.
    assert all(x['code']!='merge_slot_unconnected' for x in e.errors())
    assert e.errors() and e.memory.read_transient(merge,'default')=={'path_a':'seed'}


@pytest.mark.asyncio
@pytest.mark.parametrize('fails',[False,True])
async def test_success_and_recovery_rejoin_with_valid_health_and_real_run(tmp_path,fails):
    e=Engine();fork=e.add('branch_node');merge=e.add('merge_node')
    path=tmp_path/'source.txt'
    if not fails:path.write_text('file value')
    reader=e.add('file_reader_node',input_source='Configured',file_path=str(path))
    recovery=e.add('concat_node',template='fallback');sink=e.step('sink',sink=True)
    e.wire(e.start,fork);e.wire(fork,reader,'path_a');e.wire(fork,merge,'path_b','path_b')
    e.wire(reader,merge,slot='path_a');e.wire(reader,recovery,'error');e.wire(recovery,merge,slot='path_a');e.wire(merge,sink)
    assert not validate_workflow(e.wm,e.factory)['errors']
    assert all(h.state==VALID for h in derive_branch_health(e.wm.get_all_node_data()))
    await e.master.start_workflow(unattended='terminate_branch');await e.finish()
    assert all(x['handled'] for x in e.errors())
    assert len(e.done(merge))==1
    assert e.seen[0]['value']['input']['path_a']==('fallback' if fails else 'file value')


@pytest.mark.asyncio
async def test_limit_boundary_real_run_and_live_service_validation():
    from backend.run_service import RunService
    e=Engine();previous=e.start
    for i in range(3):
        fork=e.add('branch_node');end=e.add('end_node',record_line=False)
        e.wire(previous,fork,'default' if previous==e.start else 'path_a');e.wire(fork,end,'path_b')
        previous=fork
    e.wire(previous,end,'path_a')
    config=e.master._configuration_manager
    config.set('max_branch_depth',3)
    service=RunService(e.master,e.wm,e.factory,e.bus,configuration_manager=config)
    assert not service.validate()['errors']
    config._settings['max_branch_depth']=2  # Unsaved live override must also apply.
    assert any(x['code']=='branch_depth_exceeded' for x in service.validate()['errors'])
    config._settings['max_branch_depth']=3
    await e.master.start_workflow(unattended='terminate_branch');await e.finish()
    assert not e.errors() and max(r['depth'] for r in e.registered)==3


@pytest.mark.asyncio
async def test_sequential_merges_reset_depth_in_analysis_and_runtime():
    e=Engine();previous=e.start
    for i in range(8):
        fork=e.add('branch_node');merge=e.add('merge_node')
        e.wire(previous,fork);e.wire(fork,merge,'path_a','path_a');e.wire(fork,merge,'path_b','path_b')
        previous=merge
    end=e.add('end_node',record_line=False);e.wire(previous,end)
    e.master._configuration_manager.set('max_branch_depth',1)
    assert not validate_workflow(e.wm,e.factory,max_branch_depth=1)['errors']
    await e.master.start_workflow(unattended='terminate_branch');await e.finish()
    assert not e.errors() and max(r['depth'] for r in e.registered)==1


@pytest.mark.asyncio
async def test_check_node_uses_live_depth_limit_and_exports_plain_repair():
    from dataclasses import replace
    from tests.test_meta_nodes import runner
    # One split needs depth 1; the live limit 0 must win over disk/default 5.
    node,context,_,done,errors=runner('check_workflow_spec_node',value=json.dumps(merge_spec(template='{input[path_a]}')))
    await node.execute(replace(context,get_setting=lambda key:0))
    assert not done and len(errors)==1
    assert 'limit is 0' in str(errors[0]) and 'Reduce the nested splits' in str(errors[0])


@pytest.mark.asyncio
@pytest.mark.parametrize('problem',['slot','depth'])
async def test_new_refusals_reach_one_structural_redraft(tmp_path,problem):
    # The SDK transport is an in-process fixture; no API/model request is made.
    from copy import deepcopy
    from tools.draft_trials import runner
    from tools.draft_trials.case_set_four import case_record, good_draft
    case=case_record(1,tmp_path/'trial/cases/1/fixtures')
    good=good_draft(1,case['root']);bad=deepcopy(good)
    if problem=='slot':
        bad['nodes']['show']['config']['template']='{input[path_c]}'
        reason='path_c is not connected'
    else:
        bad['connections']=[edge for edge in bad['connections'] if edge['from']!='split.path_a']
        previous='split'
        for i in range(5):
            name,side=f'nested{i}',f'side{i}'
            bad['nodes'][name]={'type':'branch_node','config':{'branch_count':2}}
            bad['nodes'][side]={'type':'end_node','config':{'record_line':False}}
            bad['connections'] += [{'from':previous+'.path_a','to':name+'.input'},
                                   {'from':name+'.path_b','to':side+'.input'}]
            previous=name
        bad['connections'].append({'from':previous+'.path_a','to':'a.input'})
        reason='nesting depth 6'
    report=await runner.run_case(1,tmp_path/'trial',tmp_path/'library',case_set=4,
        replies=[runner.requirements(case),bad,good,runner.meaning()])
    assert report['result']=='pass',report
    assert report['draft_retry']['attempted']==1 and report['draft_retry']['check_passed']
    prompt=json.loads((tmp_path/'trial/cases/1/calls.json').read_text())[2]['messages'][0]['content']
    assert reason in prompt


def test_unrelated_loop_cannot_hide_unreachable_or_exclusive_targets():
    nodes=loop_wait('unconnected')
    nodes['unconnected']=dict(type='sleep_node',config={},connections={'inputs':[],'outputs':[]})
    assert 'impossible_wait' in codes(analyze_flow(nodes))
    from tests.test_flow_behaviors import exclusive
    nodes=exclusive()
    nodes['A'].update(type='wait_until_node',config={'target_node_ids':'yes'})
    nodes['loop']=dict(type='sleep_node',config={},connections={'inputs':[],'outputs':[]})
    wire(nodes,'loop','default','loop')
    report=analyze_flow(nodes,draft=True)
    assert {'flow_loop','flow_needs_review','wait_target_needs_review'} <= codes(report)

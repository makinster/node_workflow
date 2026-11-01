"""Graph-only flow contracts; no nodes, models or services are executed."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from backend.authoring import FORMAT, check_workflow_spec
from backend.branch_health import VALID, derive_branch_health
from backend.flow_behaviors import Kind, analyze_flow, parse_targets, resolve_flow
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow, _reached_with_open_branch

FACTORY = NodeFactory()


def graph(types, wires, configs=None):
    nodes = {nid: dict(type=kind, alias=nid, config=(configs or {}).get(nid, {}),
                      connections=dict(inputs=[], outputs=[])) for nid, kind in types.items()}
    for source, port, target, slot in wires:
        edge = dict(source_node_id=source, source_port=port, target_node_id=target, target_port=slot)
        nodes[source]['connections']['outputs'].append(edge.copy())
        nodes[target]['connections']['inputs'].append(edge.copy())
    return nodes


def wire(nodes, source, port, target, slot='input'):
    edge = dict(source_node_id=source, source_port=port, target_node_id=target, target_port=slot)
    nodes[source]['connections']['outputs'].append(edge.copy())
    nodes[target]['connections']['inputs'].append(edge.copy())


def reference(host='A', same_slot=False, beacon=False):
    types = dict(start='start_node', split='branch_node', A='sleep_node', B='branch_node',
                 C='echo_node', D='echo_node', combine='merge_node', end='end_node')
    wires = [('start','default','split','input'), ('split','path_a','A','input'),
             ('split','path_b','B','input'), ('B','path_a','C','input'),
             ('B','path_b','D','input'), ('combine','default','end','input')]
    for source, slot in [('A','path_a'), ('C','path_b'), ('D','path_b' if same_slot else 'path_c')]:
        if beacon:
            types[source+'_beacon'] = 'branch_end_node'
            wires.extend([(source,'default',source+'_beacon','input'), (source+'_beacon','default','combine',slot)])
        else:
            wires.append((source,'default','combine',slot))
    return graph(types, wires, {'split': {'branch_count':2}, 'B': {'branch_count':2},
                                'combine': {'carry_forward_branch_id':host}})


def errors(report):
    return {f.code for f in report.findings if f.level == 'error'}


@pytest.mark.parametrize('host', ['A','C','D'])
@pytest.mark.parametrize('beacon', [False,True])
def test_owner_reference_inherits_handoff_and_shallow_continuation(host, beacon):
    nodes = reference(host, beacon=beacon)
    before = deepcopy(nodes)
    report = analyze_flow(nodes, FACTORY)
    assert report.success and nodes == before
    merge = report.merges['combine']
    assert merge.group_roots == ['split'] and merge.pass_number == 1
    assert [a.path_name for a in merge.arrivals] == ['A','C','D']
    assert [a.depth for a in merge.arrivals] == [1,2,2]
    assert merge.continuation_candidates == ['A']
    assert [h['parent'] for h in merge.handoffs] == ['B']
    assert merge.handoffs[0]['children'] == ['C','D']
    assert merge.admission_stage == report.admission_stage == 2
    assert list(merge.slots) == ['path_a','path_b','path_c']
    assert all(s['cardinality'] == 'one' for s in merge.slots.values())
    assert merge.summary == ('Merge "combine": waits for A (path_a), C (path_b), D (path_c). '
                             'B hands off to C and D. Continues as A. Output: {path_a, path_b, path_c}.')
    assert not _reached_with_open_branch(nodes, 'end')
    assert json.loads(json.dumps(report.to_dict()))['merges']['combine']['pass_number'] == 1


def test_r1_concurrent_same_slot_is_stable_many():
    merge = analyze_flow(reference(same_slot=True), FACTORY).merges['combine']
    schema = merge.slots['path_b']
    assert schema['cardinality'] == 'many'
    assert [p['path_name'] for p in schema['producers']] == ['C','D']
    assert schema['presence'] == 'possible_missing' and not schema['index_labels_certified']
    assert 'path_b: list from C, D, always in that order.' in merge.summary


def exclusive(escape=False, conditional_fork=False, separate_slots=False):
    return graph(dict(start='start_node', split='branch_node', A='echo_node',
                      choice='branch_node' if conditional_fork else 'conditional_node',
                      yes='echo_node', no='end_node' if escape else 'echo_node', combine='merge_node'),
                 [('start','default','split','input'), ('split','path_a','A','input'),
                  ('split','path_b','choice','input'), ('A','default','combine','path_a'),
                  ('choice','path_a' if conditional_fork else 'true','yes','input'),
                  ('choice','path_b' if conditional_fork else 'false','no','input'),
                  ('yes','default','combine','path_b')]
                 + ([] if escape else [('no','default','combine','path_c' if separate_slots else 'path_b')]),
                 {'split':{'branch_count':2}, 'choice':{'condition':'string_match'} if conditional_fork else {}})


@pytest.mark.parametrize('fork', [False,True])
def test_exclusive_same_slot_rejoin_is_one(fork):
    report = analyze_flow(exclusive(conditional_fork=fork), FACTORY, draft=True)
    assert report.success
    merge = report.merges['combine']
    assert merge.slots['path_b']['cardinality'] == 'one'
    assert len(merge.slots['path_b']['producers']) == 2
    assert all(a.if_it_runs for a in merge.arrivals if a.slot == 'path_b')


@pytest.mark.parametrize('fork', [False,True])
def test_required_path_cannot_escape_and_validator_exports_structure(fork):
    nodes = exclusive(escape=True, conditional_fork=fork)
    report = analyze_flow(nodes, FACTORY)
    assert 'merge_required_path_escape' in errors(report)
    issue = next(f for f in report.findings if f.code == 'merge_required_path_escape')
    assert issue.node_id == 'combine' and 'choice' in issue.message
    assert issue.slot == 'path_b' and issue.route in {'false','path_b'} and issue.repair
    result = validate_workflow(SimpleNamespace(get_all_node_data=lambda: nodes), FACTORY)
    assert 'merge_required_path_escape' in {f['code'] for f in result['errors']}
    assert result['flow_analysis']['merges']['combine']['slots']['path_b']['cardinality'] == 'one'


def test_conditional_fork_may_not_omit_required_wired_slot():
    assert 'merge_required_child_omitted' in errors(analyze_flow(exclusive(conditional_fork=True, separate_slots=True), FACTORY))


def test_independent_end_is_legal_and_equal_depth_has_no_invented_winner():
    nodes = exclusive()
    nodes['split']['config']['branch_count'] = 3
    nodes['side'] = dict(type='end_node', alias='E', config={}, connections=dict(inputs=[],outputs=[]))
    wire(nodes, 'split', 'path_c', 'side')
    report = analyze_flow(nodes, FACTORY)
    assert report.success
    assert 'E ends; supplies no Merge value.' in report.merges['combine'].summary
    assert 'path with the fewest nested splits' in report.merges['combine'].summary


def wait_graph(case):
    configs = {'split':{'branch_count':2}}
    if case == 'self': configs['a'] = {'target_node_ids':'a'}
    elif case == 'downstream': configs['a'] = {'target_node_ids':'end'}
    elif case == 'mutual': configs.update(a={'target_node_ids':'b'}, b={'target_node_ids':['a']})
    else: configs['a'] = {'target_node_ids':' b\n, b '}
    return graph(dict(start='start_node', split='branch_node', a='wait_until_node', b='wait_until_node', end='end_node'),
                 [('start','default','split','input'), ('split','path_a','a','input'),
                  ('split','path_b','b','input'), ('a','default','end','input')], configs)


@pytest.mark.parametrize('case', ['self','downstream','mutual'])
@pytest.mark.parametrize('draft', [False,True])
def test_impossible_completion_waits(case,draft):
    report = analyze_flow(wait_graph(case), FACTORY, draft=draft)
    assert 'impossible_wait' in errors(report)
    assert any(d['event'] == 'node_completed_once' and d['pass'] == 1 for d in report.dependencies)


def test_cross_path_wait_and_shared_parser():
    assert parse_targets([' a ','','b','a']) == ('a','b')
    assert parse_targets(' a,\nb ') == ('a','b')
    report = analyze_flow(wait_graph('valid'), FACTORY, draft=True)
    assert report.success and report.admission_stage == 2


def test_back_edge_precedes_deadlock_diagnosis():
    nodes = wait_graph('downstream')
    nodes['end']['type'] = 'echo_node'
    wire(nodes, 'end', 'default', 'a')
    report = analyze_flow(nodes, FACTORY, draft=True)
    assert errors(report) == {'flow_loop'}
    assert report.findings[0].message == 'loops are not supported in drafts yet'
    assert report.back_edges and report.dependencies  # Loop findings no longer suppress independent checks.
    assert analyze_flow(nodes, FACTORY).success


def test_exclusive_wait_target_needs_review():
    nodes = exclusive()
    nodes['A'].update(type='wait_until_node',config={'target_node_ids':'yes'})
    assert 'wait_target_needs_review' in errors(analyze_flow(nodes, FACTORY, draft=True))


def test_merge_completion_dependency_cycle():
    nodes = reference()
    nodes['A'].update(type='wait_until_node', config={'target_node_ids':'combine'})
    assert 'impossible_wait' in errors(analyze_flow(nodes, FACTORY))


def test_recovery_escape_errors_and_rejoining_recovery_is_valid():
    nodes = reference()
    nodes['recovery'] = dict(type='echo_node', alias='recovery',config={},connections=dict(inputs=[],outputs=[]))
    wire(nodes,'A','error','recovery')
    assert 'merge_required_path_escape' in errors(analyze_flow(nodes, FACTORY))
    wire(nodes,'recovery','default','combine','path_a')
    report = analyze_flow(nodes, FACTORY)
    assert report.success and report.merges['combine'].slots['path_a']['cardinality'] == 'one'


def test_standalone_merge_app_warning_and_authoring_error():
    nodes = graph(dict(start='start_node',combine='merge_node'), [('start','default','combine','path_a')])
    assert analyze_flow(nodes, FACTORY).success
    assert 'merge_outside_split' in errors(analyze_flow(nodes, FACTORY, draft=True))
    spec = dict(format=FORMAT,name='Standalone merge',nodes={'start':{'type':'start_node'},'combine':{'type':'merge_node'}},
                connections=[{'from':'start.default','to':'combine.path_a'}])
    report = check_workflow_spec(FACTORY,spec)
    assert not report['ok']
    assert any(d['code'] == 'merge_outside_split' and d['level'] == 'error' for d in report['diagnostics'])


def test_plain_conditional_rejoin_needs_no_merge():
    nodes = graph(dict(start='start_node',choose='conditional_node',a='echo_node',b='echo_node',end='end_node'),
                  [('start','default','choose','input'), ('choose','true','a','input'),
                   ('choose','false','b','input'), ('a','default','end','input'), ('b','default','end','input')])
    assert analyze_flow(nodes, FACTORY, draft=True).success


def test_stage_one_numeric_slot_order():
    nodes = graph(dict(start='start_node',split='branch_node',A='echo_node',B='echo_node',combine='merge_node'),
                  [('start','default','split','input'), ('split','path_a','A','input'),
                   ('split','path_b','B','input'), ('A','default','combine','path_z'), ('B','default','combine','path_aa')],
                  {'split':{'branch_count':2},'combine':{'input_slots':27}})
    report = analyze_flow(nodes, FACTORY, draft=True)
    assert report.success and report.admission_stage == 1
    assert list(report.merges['combine'].slots) == ['path_z','path_aa']


def test_legacy_branch_selection_and_debug_profiles():
    resolve = lambda config: resolve_flow({'type':'branch_node','config':config},FACTORY)
    assert resolve({'condition':'path_a_only'}).batches == (('path_a',),)
    assert resolve({'condition':'path_b_only'}).batches == (('path_b',),)
    assert resolve({'condition':'path_a_only','branch_count':2}).batches == (('path_a','path_b'),)
    assert resolve({'condition':'string_match'}).exclusive
    assert resolve({'condition':'string_match','on_match':'path_c'}).batches[0] == ('path_c',)
    assert resolve_flow({'type':'deep_branch_node'},FACTORY).kind == Kind.FORK
    assert resolve_flow({'type':'random_branch_node'},FACTORY).exclusive
    assert resolve_flow({'type':'branch_end_node'},FACTORY).kind == Kind.BEACON
    assert resolve_flow({'type':'ask_claude_node'},FACTORY).batches == (('default',),)


def test_bound_refuses_instead_of_truncating():
    assert 'flow_needs_review' in errors(analyze_flow(reference(),FACTORY,draft=True,max_states=2))


def test_existing_beacon_health_and_return_end_after_nested_join():
    nodes = reference(beacon=True)
    assert all(h.state == VALID for h in derive_branch_health(nodes))
    nodes['end']['config'] = {'return_end':True}
    result = validate_workflow(SimpleNamespace(get_all_node_data=lambda:nodes,callable=True),FACTORY)
    assert 'return_end_unmerged' not in {e['code'] for e in result['errors']}


def test_shared_router_visits_are_exclusive_per_lineage_not_globally():
    # Two concurrent supervisors both reach this saved Conditional. Their
    # independently chosen routes can concurrently feed the same Merge slot.
    nodes = graph(dict(start='start_node',split='branch_node',shared='conditional_node',combine='merge_node'),
                  [('start','default','split','input'), ('split','path_a','shared','input'),
                   ('split','path_b','shared','input'), ('shared','true','combine','path_a'),
                   ('shared','false','combine','path_a')], {'split':{'branch_count':2}})
    report = analyze_flow(nodes,FACTORY)
    assert report.success
    assert report.merges['combine'].slots['path_a']['cardinality'] == 'many'
    assert len(report.merges['combine'].arrivals) == 4


def test_concurrent_recovery_routes_remain_concurrent():
    nodes = graph(dict(start='start_node',split='branch_node',combine='merge_node',end='end_node'),
                  [('start','default','split','input'), ('split','path_a','combine','path_a'),
                   ('split','path_b','combine','path_a'), ('split','error','end','input')],
                  {'split':{'branch_count':2}})
    report = analyze_flow(nodes,FACTORY)
    assert report.merges['combine'].slots['path_a']['cardinality'] == 'many'
    assert 'merge_required_path_escape' in errors(report)


def test_disabled_legacy_branch_wire_does_not_create_pending_obligation():
    nodes = graph(dict(start='start_node',split='branch_node',a='echo_node',b='echo_node',combine='merge_node'),
                  [('start','default','split','input'), ('split','path_a','a','input'),
                   ('split','path_b','b','input'), ('a','default','combine','path_a'),
                   ('b','default','combine','path_b')], {'split':{'condition':'path_a_only'}})
    merge = analyze_flow(nodes,FACTORY).merges['combine']
    assert [a.path_name for a in merge.arrivals] == ['a']


def test_repeated_group_joins_are_preflight_errors_in_app_and_drafts():
    nodes = reference()
    nodes['second'] = dict(type='merge_node',alias='second',config={},connections=dict(inputs=[],outputs=[]))
    wire(nodes,'end','default','second','path_a')
    nodes['end']['type'] = 'echo_node'
    assert "flow_needs_review" in errors(analyze_flow(nodes,FACTORY))
    assert 'repeated_join_unsupported' in errors(analyze_flow(nodes,FACTORY,draft=True))


def test_authoring_surfaces_wait_errors_and_loop_wording():
    spec = dict(format=FORMAT,name='Invalid wait',nodes={'start':{'type':'start_node'},
        'wait':{'type':'wait_until_node','config':{'target_node_ids':['wait']}}},
        connections=[{'from':'start.default','to':'wait.input'}])
    result = check_workflow_spec(FACTORY,spec)
    assert any(d['code'] == 'impossible_wait' for d in result['diagnostics'])
    spec['connections'].append({'from':'wait.default','to':'wait.input'})
    result = check_workflow_spec(FACTORY,spec)
    assert any(d['code'] == 'flow_loop' and d['message'] == 'loops are not supported in drafts yet'
               for d in result['diagnostics'])
    assert any(d['code'] == 'impossible_wait' for d in result['diagnostics'])  # Self-wait remains certain even in a loop.


def test_existing_end_only_and_output_endpoint_workflows_remain_valid():
    for endpoint in ['end_node','text_output_node']:
        nodes = graph(dict(start='start_node',split='branch_node',a=endpoint,b=endpoint),
                      [('start','default','split','input'), ('split','path_a','a','input'),
                       ('split','path_b','b','input')], {'split':{'branch_count':2}})
        assert analyze_flow(nodes,FACTORY).success
        assert all(h.state == VALID for h in derive_branch_health(nodes))


def test_profile_policy_validation_and_graph_limit_are_explicit():
    from backend.flow_behaviors import FlowProfile
    with pytest.raises(ValueError):
        FlowProfile(pass_number=2)
    with pytest.raises(ValueError):
        FlowProfile(winner='editor_host')
    with pytest.raises(ValueError):
        FlowProfile(kind='not_a_behavior')
    nodes = graph({str(i):'echo_node' for i in range(513)}, [])
    report = analyze_flow(nodes, FACTORY, draft=True)
    assert errors(report) == {'flow_needs_review'}
    assert '512 nodes' in report.findings[0].message and not report.profiles


def test_wait_on_disconnected_target_cannot_complete():
    nodes = wait_graph('valid')
    nodes['split']['connections']['outputs'] = [e for e in nodes['split']['connections']['outputs']
                                                if e['target_node_id'] != 'b']
    assert 'impossible_wait' in errors(analyze_flow(nodes,FACTORY))


def test_branch_health_understands_safe_exclusive_routes():
    assert all(h.state == VALID for h in derive_branch_health(exclusive()))


def test_group_export_records_potential_members_and_atomic_handoffs():
    group = analyze_flow(reference(),FACTORY).groups['split']
    assert group['scope'] == 'inherited_family_in_run' and group['pass'] == 1
    assert {m['path_name'] for m in group['members']} == {'A','B','C','D'}
    assert all(h['registration'] == 'atomic_selected_batch' for h in group['handoffs'])
    conditional = analyze_flow(exclusive(conditional_fork=True),FACTORY).groups['split']
    assert all(m['if_it_runs'] for m in conditional['members'] if m['fork_node_id'] == 'choice')


def test_saved_value_router_is_exclusive_and_empty_mux_routes_are_inactive():
    changed = resolve_flow({'type':'if_changed_node'},FACTORY)
    assert changed.exclusive and changed.batches == (('changed',),('no_change',))
    mux = resolve_flow({'type':'error_mux_node','config':{'routes':[
        {'id':'empty','label':'Empty','codes':[]},
        {'id':'retry','label':'Retry','codes':['timeout']}
    ]}},FACTORY)
    assert ('empty',) not in mux.batches and ('retry',) in mux.batches


def test_authoring_keeps_repair_guidance_and_path_handles():
    spec = dict(format=FORMAT,name='Repairable wait',nodes={'start':{'type':'start_node'},
        'wait':{'type':'wait_until_node','config':{'target_node_ids':['wait']}}},
        connections=[{'from':'start.default','to':'wait.input'}])
    result = check_workflow_spec(FACTORY,spec)
    issue = next(d for d in result['diagnostics'] if d['code'] == 'impossible_wait')
    assert issue['node'] == 'wait' and issue['path'] == ['wait','wait'] and issue['repair']


def test_duplicate_path_labels_do_not_invent_equal_depth_winner():
    nodes = exclusive()
    nodes['split']['config'].update(path_a_label='same',path_b_label='same')
    merge = analyze_flow(nodes,FACTORY).merges['combine']
    assert 'Continues as same.' not in merge.summary
    assert 'path with the fewest nested splits' in merge.summary


def test_unproved_merge_shape_is_an_app_error_after_analysis_limits_or_loops():
    nodes = reference()
    bounded = analyze_flow(nodes, FACTORY, max_states=2)
    assert not bounded.success and 'flow_needs_review' in errors(bounded)
    wire(nodes, 'end', 'default', 'start')
    nodes['end']['type'] = 'echo_node'
    loop = analyze_flow(nodes, FACTORY)
    assert not loop.success and 'flow_needs_review' in errors(loop)
    oversized = graph({f'n{i}': 'no_op_node' for i in range(513)}, [])
    assert analyze_flow(oversized, FACTORY).success  # Non-collecting app graphs unchanged.
    oversized['n0']['type'] = 'merge_node'
    assert not analyze_flow(oversized, FACTORY).success

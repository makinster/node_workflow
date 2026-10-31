"""Controls beside the six pairs, not new requests or drafter examples."""
from copy import deepcopy
from .case_set_four import good_draft


def controls(stage=1):
    result=[]
    def add(name,spec,expected_engine,expected_draft,required_stage=1):
        result.append(dict(id=name,spec=spec,expected_engine=expected_engine,expected_draft=expected_draft,required_stage=required_stage))
    plain=good_draft(1)
    standalone=dict(format='aotn-workflow/1',name='Standalone Merge control',nodes={
        'start':dict(type='start_node',config={'greeting':'pass through'}),
        'join':dict(type='merge_node',config={}),
        'show':dict(type='text_output_node',config={'label':'','template':'{input}'}),
        'end':dict(type='end_node',config={'record_line':False})},
        connections=[{'from':'start.default','to':'join.path_a'}, {'from':'join.default','to':'show.input'}, {'from':'show.default','to':'end.input'}])
    add('standalone_merge',standalone,'finished','fail')
    repeated=deepcopy(plain)
    repeated['nodes']['again']=dict(type='merge_node',config={})
    for edge in repeated['connections']:
        if edge['from']=='join.default':
            edge['to']='again.path_a'
    repeated['connections'].append({'from':'again.default','to':'show.input'})
    add('second_merge_same_group',repeated,'preflight_rejected','fail')
    loop=deepcopy(plain)
    loop['connections']=[e for e in loop['connections'] if e['from']!='show.default']
    loop['connections'].append({'from':'show.default','to':'split.input'})
    del loop['nodes']['end']
    add('control_back_edge',loop,'preflight_rejected','fail')
    independent=deepcopy(plain)
    independent['nodes']['split']['config']['branch_count']=3
    independent['nodes']['side']=dict(type='end_node',config={'record_line':False})
    independent['connections'].append({'from':'split.path_c','to':'side.input'})
    add('independent_side_end',independent,'finished','pass',required_stage=2)
    race=deepcopy(plain)
    for h in ('a','b'):
        race['nodes'][h]['config'].update(vault_write=True,vault_write_key='shared')
    race['nodes']['format']=dict(type='concat_node',config={'template':'A: {input[path_a]}\nB: {input[path_b]}\nWinner: {shared}'})
    race['nodes']['show']['config']['template']='{input}'
    for edge in race['connections']:
        if edge['from']=='join.default':
            edge['to']='format.input'
    race['connections'].append({'from':'format.default','to':'show.input'})
    add('shared_vault_replacement_unordered',race,'finished','fail',required_stage=2)
    return [c for c in result if c['required_stage']<=stage]

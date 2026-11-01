"""Family 2 data. Every request and pair up to the current draft stage is in the normal run."""
from copy import deepcopy
from pathlib import Path

from backend.palette_selection import ADMISSION_VERSIONS

VERSION = 1
COUNT = 5
DRAFT_STAGE = ADMISSION_VERSIONS['draft_stage']
STAGES = {1: 1, 2: 1, 3: 2, 4: 2, 5: 2}
REQUESTS = [
    'Read ROOT/report-a.txt and ROOT/report-b.txt in parallel. Show both contents once, labelled A then B, after both reads finish.',
    'Read ROOT/value.json, ROOT/flag.json and ROOT/note.txt at the same time. From value.json take the field named value, and from flag.json the field named flag. Show both and the complete note together, labelled Value, Flag and Note, after all three are ready.',
    'Read ROOT/slow.txt on one path. On a second path read ROOT/gather.txt, then split that path in two: one makes an uppercase copy, the other a lowercase copy. When the slow.txt read and both copies have finished, show all three together once, labelled Slow, Upper and Lower.',
    'On one path read ROOT/source.txt. On a second path, wait until that read has finished, then show Ready on its own. After both paths finish, also show one combined message with the file text and Ready, labelled File and Status.',
    'Read ROOT/note.txt in parallel with ROOT/choice.txt. If choice.txt is exactly yes, make the message Approved; otherwise make the message Needs review. Show the note and whichever message was chosen together once, labelled Note and Decision.',
]
REFERENCE_NOTE = ('Run a slow step on A, such as a five-minute MCP call. On B gather resources, '
                  'then split into C and D. When A, C and D have finished, continue once with '
                  "A's slow result and both resources. Direct or Beacon wiring and Merge on A/C/D "
                  'belong to engine/editor tests; no MCP/provider task or Beacon draft is admitted.')


def case_record(number, root, *, stage=DRAFT_STAGE):
    if number not in STAGES or stage not in (1, 2):
        raise ValueError('set 4 has cases 1..5 and evaluation stages 1/2')
    root = str(Path(root).resolve())
    return dict(version=VERSION, case_set=4, id=number, key=f'F2-{number:02d}',
                root=root, request=REQUESTS[number-1].replace('ROOT', root), clarification='',
                expected_status='ready', required_stage=STAGES[number], evaluation_stage=stage,
                admitted=STAGES[number] <= DRAFT_STAGE, reference_note=REFERENCE_NOTE if number == 3 else '')


def case_ids(stage=DRAFT_STAGE):
    return [n for n in STAGES if STAGES[n] <= stage]


def fixture_variants(number):
    def field(label, value, expression):
        return dict(label=label, value=value, expression=expression)
    def v(name, files, fields, *, ready=False):
        output = '\n'.join(f"{f['label']}: {f['value']}" for f in fields)
        return dict(name=name, files=files, answers=[], writes={}, error=False,
                    fields=fields, outputs=(['Ready'] if ready else [])+[output])
    file = lambda name: ('file', name)
    if number == 1:
        return [v(name, {'report-a.txt': a, 'report-b.txt': b},
                  [field('A', a, file('report-a.txt')), field('B', b, file('report-b.txt'))])
                for name,a,b in [('plain','Alpha report','Beta report'),
                                 ('changed','Café opened','Line one\nLine two'),
                                 ('empty-b','Alpha report','')]]
    if number == 2:
        import json
        return [v(name, {'value.json': json.dumps({'value': value}),
                         'flag.json': json.dumps({'flag': flag}), 'note.txt':'Hello'},
                  [field('Value',value,('project','value',file('value.json'))),
                   field('Flag',flag,('project','flag',file('flag.json'))),
                   field('Note','Hello',file('note.txt'))])
                for name,value,flag in [('plain',42,True),('zero-false',0,False),('null',None,True),
                                        ('empty-text','',False),('list',[1,2],True),('object',{'a':1},True)]]
    if number == 3:
        return [v(name, {'slow.txt':slow,'gather.txt':gather},
                  [field('Slow',slow,file('slow.txt')),
                   field('Upper',gather.upper(),('operation','uppercase',file('gather.txt'))),
                   field('Lower',gather.lower(),('operation','lowercase',file('gather.txt')))])
                for name,slow,gather in [('plain','Slow result','Mixed Case'),('changed','Other','Ünï Code')]]
    if number == 4:
        return [v(name, {'source.txt':text}, [field('File',text,file('source.txt')),
                  field('Status','Ready',('literal','Ready'))], ready=True)
                for name,text in [('plain','Source text'),('changed','Other text')]]
    if number == 5:
        return [v(name, {'note.txt':'Hello','choice.txt':choice},
                  [field('Note','Hello',file('note.txt')),field('Decision',decision,('literal',decision))])
                for name,choice,decision in [('yes','yes','Approved'),('no','no','Needs review'),
                                             ('not-exact','not yes','Needs review'),('capital','YES','Needs review')]]
    raise ValueError('unknown set 4 case')


def good_draft(number, root='ROOT', *, same_slot=False):
    nodes, edges = {}, []
    def node(h, t, **c):
        nodes[h] = dict(type=t+'_node', config=c)
    def edge(a,b,port='default',slot='input'):
        edges.append({'from':a+'.'+port,'to':b+'.'+slot})
    def read(h, filename):
        node(h,'file_reader',file_path=root+'/'+filename,input_source='Configured')
    node('start','start',greeting='')
    node('split','branch',branch_count=3 if number == 2 else 2)
    node('join','merge')
    node('show','text_output',label='')
    node('end','end',record_line=False)
    edge('start','split')
    edge('join','show')
    edge('show','end')
    if number == 1:
        for h,filename,port in [('a','report-a.txt','path_a'),('b','report-b.txt','path_b')]:
            read(h,filename)
            edge('split',h,port)
            edge(h,'join',slot=port)
        template='A: {input[path_a]}\nB: {input[path_b]}'
    elif number == 2:
        for h,filename,port,key in [('value','value.json','path_a','value'),('flag','flag.json','path_b','flag'),('note','note.txt','path_c',None)]:
            read(h,filename)
            edge('split',h,port)
            if key:
                node(h+'_field','json_path',path=key)
                edge(h,h+'_field')
                h+='_field'
            edge(h,'join',slot=port)
        template='Value: {input[path_a]}\nFlag: {input[path_b]}\nNote: {input[path_c]}'
    elif number == 3:
        read('slow','slow.txt')
        read('gather','gather.txt')
        node('children','branch',branch_count=2)
        edge('split','slow','path_a')
        edge('split','gather','path_b')
        edge('slow','join',slot='path_a')
        edge('gather','children')
        for h,op,port,slot in [('upper','uppercase','path_a','path_b'),('lower','lowercase','path_b','path_b' if same_slot else 'path_c')]:
            node(h,'text_transform',operation=op)
            edge('children',h,port)
            edge(h,'join',slot=slot)
        template=('Slow: {input[path_a]}\nUpper: {input[path_b][0]}\nLower: {input[path_b][1]}' if same_slot else
                  'Slow: {input[path_a]}\nUpper: {input[path_b]}\nLower: {input[path_c]}')
    elif number == 4:
        read('read','source.txt')
        node('wait','wait_until',target_node_ids=['read'])
        # Show forwards its label as part of its value: blank is deliberate.
        node('ready','text_output',template='Ready',label='')
        edge('split','read','path_a')
        edge('split','wait','path_b')
        edge('read','join',slot='path_a')
        edge('wait','ready')
        edge('ready','join',slot='path_b')
        template='File: {input[path_a]}\nStatus: {input[path_b]}'
    elif number == 5:
        read('note','note.txt')
        read('choice','choice.txt')
        node('choose','conditional',condition_type='equals',right_value='yes',left_value_source='input')
        edge('split','note','path_a')
        edge('split','choice','path_b')
        edge('choice','choose')
        edge('note','join',slot='path_a')
        for h,port,text in [('yes','true','Approved'),('no','false','Needs review')]:
            node(h,'concat',template=text)
            edge('choose',h,port)
            edge(h,'join',slot='path_b')
        template='Note: {input[path_a]}\nDecision: {input[path_b]}'
    else:
        raise ValueError('unknown set 4 case')
    nodes['show']['config']['template']=template
    return dict(format='aotn-workflow/1',name=f'Family 2 case {number}',nodes=nodes,connections=edges)


def calibration_pairs(*, stage=DRAFT_STAGE):
    pairs=[]
    def pair(number,name,case,mutate,**kwargs):
        good=good_draft(case,**kwargs)
        bad=deepcopy(good)
        mutate(bad)
        pairs.append(dict(id=name,number=number,case=case,case_set=4,required_stage=STAGES[case],
                          admitted=STAGES[case]<=DRAFT_STAGE,good=good,bad=bad))
    def pick(s):
        s['nodes']['pick']=dict(type='json_path_node',config={'path':'path_a'})
        for e in s['connections']:
            if e['from']=='join.default':
                e['to']='pick.input'
        s['connections'].append({'from':'pick.default','to':'show.input'})
        s['nodes']['show']['config']['template']='{input}'
    pair(1,'collect_vs_pick_one',2,pick)
    def lost(s):
        for e in s['connections']:
            if e['from']=='lower.default':
                e['to']='end.input'
        s['nodes']['show']['config']['template']='Slow: {input[path_a]}\nUpper: {input[path_b]}'
    pair(2,'handoff_vs_lost_child',3,lost)
    def escape(s):
        for e in s['connections']:
            if e['from']=='no.default':
                e['to']='end.input'
    pair(3,'either_or_vs_escape',5,escape)
    pair(4,'gate_vs_impossible_wait',4,lambda s:s['nodes']['wait']['config'].update(target_node_ids=['show']))
    pair(5,'same_slot_list_vs_overwrite',3,lambda s:s['nodes']['show']['config'].update(
        template='Slow: {input[path_a]}\nUpper: {input[path_b]}\nLower: {input[path_b][1]}'),same_slot=True)
    def shared_end(s):
        del s['nodes']['join']
        s['connections']=[e for e in s['connections'] if not e['from'].startswith('join.') and not e['to'].startswith('join.')]
        s['nodes']['show']['config']['template']='A: {input}'
        s['nodes']['second']=dict(type='text_output_node',config=dict(label='',template='B: {input}'))
        s['connections'] += [{'from':'a.default','to':'show.input'}, {'from':'b.default','to':'second.input'}, {'from':'second.default','to':'end.input'}]
    pair(6,'join_vs_shared_end',1,shared_end)
    return [p for p in pairs if p['required_stage']<=stage]

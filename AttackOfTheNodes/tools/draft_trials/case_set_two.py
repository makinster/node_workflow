"""Frozen harder set v1: ten requests, fixtures, roles and reference drafts.

Independent of set 1. No model-generated fixtures or external data are used.
"""
from copy import deepcopy
from pathlib import Path

from .cases import role, structure

REQUESTS = [
    'Ask me for a word. If I type exactly Go, show its uppercase version. Otherwise show its lowercase version. Take only one path.',
    'Ask me for my first name, then my last name. Combine both answers and show the first name, a single space, and the last name.',
    'Read ROOT/profile.json as UTF-8 JSON. Show the value of person.nickname, not the rest of the file.',
    'Read ROOT/message.txt, trim whitespace from both ends, then uppercase the result. Save it as a new ROOT/message-clean.txt without overwriting an older file and show the actual saved path.',
    'Read my UTF-8 text file, reverse its text character by character, and show the result.',
    'Send an email to colleague@example.invalid saying the report is ready.',
    'Ask me for text each time I run it, count its words separated by whitespace, and show the number of words.',
    'Ask me for a phrase. On two parallel paths, show its uppercase version on one path; on the other, lowercase that same phrase and save it as a new ROOT/phrase.txt without overwriting an older file, then show the actual saved path. Only the second path writes a file.',
    'Open ROOT/one-line.txt, which contains just one line, copy that first line unchanged and paste it into a new ROOT/line-copy.txt. Keep any older copy and show the actual saved path.',
    'Hi there! I have a busy morning and could use something simple. When I run this, show Hello team. Thanks for helping; the morning chatter needs no action.',
]


def case_record(number, root):
    if number not in range(1, 11):
        raise ValueError('set 2 case id must be 1 through 10')
    root = str(Path(root).resolve())
    return dict(version=1, case_set=2, id=number, root=root,
                request=REQUESTS[number-1].replace('ROOT', root),
                clarification=('Use ' + root + '/reverse-source.txt.') if number == 5 else '',
                expected_first_status={5: 'clarify', 6: 'outside_scope', 7: 'needs_new_node'}.get(number, 'ready'),
                expected_status={6: 'outside_scope', 7: 'needs_new_node'}.get(number, 'ready'),
                reads={3: 'profile.json', 4: 'message.txt', 5: 'reverse-source.txt', 9: 'one-line.txt'}.get(number),
                writes={4: 'message-clean.txt', 8: 'phrase.txt', 9: 'line-copy.txt'}.get(number),
                required_operations={1: ['uppercase', 'lowercase'], 4: ['strip', 'uppercase'],
                                     5: ['reverse'], 8: ['uppercase', 'lowercase']}.get(number, []),
                required_structure=deepcopy(STRUCTURES.get(number, {})))


def fixture_variants(number):
    def v(name, files=None, answers=(), outputs=(), writes=None, error=False):
        return dict(name=name, files=files or {}, answers=list(answers), outputs=list(outputs), writes=writes or {}, error=error)
    if number == 1:
        return [v('word-'+str(i), answers=[a], outputs=[a.upper() if a == 'Go' else a.lower()])
                for i, a in enumerate(['Go', 'MiXeD', 'go', ''])]
    if number == 2:
        return [v('names-'+str(i), answers=[a,b], outputs=[a+' '+b])
                for i,(a,b) in enumerate([('Ada','Lovelace'),('René','Silva'),('Lin','Q')])]
    if number == 3:
        return [v('nickname-'+str(i), {'profile.json': text}, outputs=[wanted])
                for i,(text,wanted) in enumerate([
                    ('{"person":{"nickname":"Mira","name":"wrong"},"nickname":"also wrong"}', 'Mira'),
                    ('{"person":{"nickname":"Kai"},"other":42}', 'Kai'),
                    ('{"person":{"nickname":"Zoë"}}', 'Zoë')])]
    if number == 4:
        return [v('collision', {'message.txt':'  Call Ana\n  ', 'message-clean.txt':'KEEP OLD', 'message-clean (1).txt':'KEEP ALSO'}, outputs=['@path'], writes={'message-clean.txt':'CALL ANA'}),
                v('new', {'message.txt':'\tMixed  words\n'}, outputs=['@path'], writes={'message-clean.txt':'MIXED  WORDS'}),
                v('missing', error=True)]
    if number == 5:
        return [v('reverse-'+str(i), {'reverse-source.txt': text}, outputs=[text[::-1]])
                for i,text in enumerate(['Abc\nnext', 'été !'])] + [v('missing', error=True)]
    if number in (6, 7):
        return [v('status-only')]
    if number == 8:
        return [v('phrase-'+str(i), {'phrase.txt':'KEEP OLD'}, answers=[text], outputs=[text.upper(),'@path'], writes={'phrase.txt':text.lower()})
                for i,text in enumerate(['MiXeD Phrase', 'Été 123', ''])]
    if number == 9:
        return [v('collision', {'one-line.txt':'One complete line', 'line-copy.txt':'KEEP OLD'}, outputs=['@path'], writes={'line-copy.txt':'One complete line'}),
                v('new', {'one-line.txt':'A different line — unchanged'}, outputs=['@path'], writes={'line-copy.txt':'A different line — unchanged'}),
                v('missing', error=True)]
    return [v('greeting', outputs=['Hello team'])]


STRUCTURES = {
    1: structure({'ask':role('user_text_input'), 'choice':role('conditional'),
                  'upper':role('text_transform', config={'operation':'uppercase'}), 'lower':role('text_transform',config={'operation':'lowercase'}),
                  'yes':role('text_output',output_operation='uppercase'), 'no':role('text_output',output_operation='lowercase')},
                 data_from=[('ask','choice'),('upper','yes'),('lower','no')],
                 forks=[dict(role='choice',ports=['true','false'],work=[['upper','yes'],['lower','no']],permutable=False)]),
    2: structure({'first':role('user_text_input'), 'last':role('user_text_input'), 'combine':role('concat'), 'show':role('text_output')},
                 before=[('first','last')], data_from=[('first','combine'),('last','combine'),('combine','show')]),
    3: structure({'read':role('file_reader'), 'field':role('json_path',config={'path':'person.nickname'}), 'show':role('text_output')},
                 data_from=[('read','field'),('field','show')]),
    4: structure({'read':role('file_reader'), 'trim':role('text_transform',config={'operation':'strip'}), 'upper':role('text_transform',config={'operation':'uppercase'}),
                  'write':role('file_output'), 'show':role('text_output',output_kind='saved_path')},
                 data_from=[('read','trim'),('read','upper'),('trim','write'),('upper','write'),('write','show')]),
    5: structure({'read':role('file_reader'), 'reverse':role('text_transform',config={'operation':'reverse'}), 'show':role('text_output')},
                 data_from=[('read','reverse'),('reverse','show')]),
    8: structure({'ask':role('user_text_input'), 'split':role('branch'), 'upper':role('text_transform',config={'operation':'uppercase'}),
                  'lower':role('text_transform',config={'operation':'lowercase'}), 'write':role('file_output'),
                  'shown':role('text_output',output_operation='uppercase'), 'path':role('text_output',output_kind='saved_path')},
                 data_from=[('ask','split'),('upper','shown'),('lower','write'),('write','path')],
                 forks=[dict(role='split',ports=['path_a','path_b'],work=[['upper','shown'],['lower','write','path']],permutable=True)]),
    9: structure({'read':role('file_reader'),'write':role('file_output'),'path':role('text_output',output_kind='saved_path')},
                 data_from=[('read','write'),('write','path')]),
    10: structure({'start':role('start'),'show':role('text_output',output_literal='Hello team')},before=[('start','show')]),
}


def good_draft(number, root='ROOT'):
    if number in (6, 7):
        raise ValueError('status-only cases must not produce a draft')
    n, edges = {}, []
    def node(h,t,**config):
        n[h] = dict(type=t+'_node',config=config)
    def edge(a,b,port='default',target='input'):
        edges.append({'from':a+'.'+port,'to':b+'.'+target})
    def show(h,template='{input}'):
        node(h,'text_output',label='',template=template)
        node(h+'_end','end',record_line=False)
        edge(h,h+'_end')
    def write(source, filename, path_handle='path'):
        node('write','file_output',file_path=root+'/'+filename,write_mode='Create unique',open_after_write=False)
        edge(source,'write',target='content')
        show(path_handle,'{input[path]}')
        edge('write',path_handle)
    node('start','start',greeting='')
    if number == 1:
        node('ask','user_text_input',prompt='Enter a word:')
        edge('start','ask')
        node('choice','conditional',condition_type='equals',right_value='Go')
        edge('ask','choice')
        for port,op in [('true','uppercase'),('false','lowercase')]:
            node(op,'text_transform',operation=op)
            edge('choice',op,port)
            show('show_'+op)
            edge(op,'show_'+op)
    elif number == 2:
        node('first','user_text_input',prompt='First name?',membank_outputs=[dict(id='first_name',output='first_name',data_type='string')])
        node('last','user_text_input',prompt='Last name?')
        node('combine','concat',template='{first_name} {input}')
        edge('start','first')
        edge('first','last')
        edge('last','combine')
        show('show')
        edge('combine','show')
    elif number in (3,4,5,9):
        filename={3:'profile.json',4:'message.txt',5:'reverse-source.txt',9:'one-line.txt'}[number]
        node('read','file_reader',file_path=root+'/'+filename,input_source='Configured')
        edge('start','read')
        source='read'
        if number == 3:
            node('field','json_path',path='person.nickname')
            edge('read','field')
            source='field'
        for op in {4:['strip','uppercase'],5:['reverse']}.get(number,[]):
            node(op,'text_transform',operation=op)
            edge(source,op)
            source=op
        if number in (4,9):
            write(source,{4:'message-clean.txt',9:'line-copy.txt'}[number])
        else:
            show('show')
            edge(source,'show')
    elif number == 8:
        node('ask','user_text_input',prompt='Enter a phrase:')
        node('parallel','branch',branch_count=2)
        edge('start','ask')
        edge('ask','parallel')
        node('upper','text_transform',operation='uppercase')
        node('lower','text_transform',operation='lowercase')
        edge('parallel','upper','path_a')
        edge('parallel','lower','path_b')
        show('upper_show')
        edge('upper','upper_show')
        write('lower','phrase.txt')
    else:
        show('show','Hello team')
        edge('start','show')
    return dict(format='aotn-workflow/1',name='Set 2 case '+str(number),nodes=n,connections=edges)


def frozen_cases():
    """JSON-ready snapshot; test pins this against the checked-in artifact."""
    rows = []
    for number in range(1, 11):
        rows.append(dict(
            id=number, request=REQUESTS[number-1],
            expected_first_status={5:'clarify',6:'outside_scope',7:'needs_new_node'}.get(number,'ready'),
            expected_status={6:'outside_scope',7:'needs_new_node'}.get(number,'ready'),
            clarification='Use ROOT/reverse-source.txt.' if number==5 else '',
            fixtures=fixture_variants(number),
            required_structure=STRUCTURES.get(number),
            good=good_draft(number) if number not in (6,7) else None))
    return dict(case_set=2, version=1, cases=rows)

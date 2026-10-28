"""Bounded pure evaluator for the frozen cases. Never executes draft node code.

Unsupported forms fail with a rule id; adding equivalents requires versioning
this oracle, rather than weakening expectations after a generated failure.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from string import Formatter

from .cases import PALETTE, fixture_variants

class RuleFailure(ValueError):
    pass

@dataclass
class Value:
    data: object
    operations: tuple = ()
    origins: tuple = ()


def safe_path(raw, root):
    if not isinstance(raw,str) or not Path(raw).is_absolute() or any(c in raw for c in '{}\x00'):
        raise RuleFailure('path must be a literal absolute path')
    path=Path(raw).resolve()
    if not path.is_relative_to(Path(root).resolve()) or path==Path(root).resolve():
        raise RuleFailure('path escapes case root (including symlinks)')
    return path


def format_value(template, values):
    """Only the documented basic Python fields; never evaluate attributes/code."""
    dependencies=[]
    for _,field,fmt,conversion in Formatter().parse(template):
        if field is None:continue
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:\[[A-Za-z_0-9-]+\])*',field) or fmt or conversion:
            raise RuleFailure('unsupported format field')
        key=field.split('[')[0]
        if key not in values:raise RuleFailure('missing template value '+key)
        dependencies.append(values[key])
    rendered=template.format_map({k:v.data for k,v in values.items()})
    return Value(rendered,tuple(o for v in dependencies for o in v.operations),tuple(o for v in dependencies for o in v.origins))


def effective_nodes(spec):
    from backend.node_factory import NodeFactory
    factory=NodeFactory()
    return {h:dict(node,config={**deepcopy(factory.metadata_for_type(node['type'])['default_config']),**node.get('config',{})}) for h,node in spec['nodes'].items()}


def safety(spec,case):
    """Inspect ALL nodes, including error routes, before any target execution."""
    if spec.get('format')!='aotn-workflow/1' or spec.get('callable'):raise RuleFailure('unsupported spec/callable')
    if len(spec.get('nodes',{}))>64:raise RuleFailure('too many nodes')
    if any(n.get('type') not in PALETTE for n in spec['nodes'].values()):raise RuleFailure('outside 12-type palette')
    nodes=effective_nodes(spec);out=defaultdict(list)
    for edge in spec['connections']:out[edge['from']].append(edge['to'])
    if any(len(targets)>1 for targets in out.values()):raise RuleFailure('ordinary output fan-out')
    reads={4:'agenda.txt',5:'agenda.txt',9:'note-source.txt',10:'raw-notes.txt'}
    writes={5:'agenda-copy.txt',6:'note.txt',9:'clean-note.txt',10:'tidy-notes.txt'}
    for h,node in nodes.items():
        t=node['type'];c=node['config']
        if c.get('membank_inputs') or c.get('transient_outputs'):
            raise RuleFailure('legacy source/routing overrides need review')
        if c.get('node_errors') or c.get('breakpoint'):raise RuleFailure('unsupported recovery/breakpoint')
        if t=='start_node' and (c.get('rows') or c.get('no_inputs')):raise RuleFailure('unsupported Start contract')
        if t=='text_output_node' and c.get('request_user_input'):raise RuleFailure('legacy output prompt needs review')
        if t=='branch_node':
            if case['id']!=8 or c.get('branch_count')!=2 or c.get('branch_payload_sources') or c.get('condition','always_branch')!='always_branch':raise RuleFailure('unsupported branch behavior')
        if t=='conditional_node':
            if case['id'] not in (7,9) or c['condition_type']!='equals' or c['left_value_source']!='input' or c['right_value']!=('yes' if case['id']==7 else ''):raise RuleFailure('wrong conditional comparison/source')
        if t=='user_text_input_node':
            if case['id'] not in (3,6,7,8):raise RuleFailure('unrequested runtime prompt')
            if not re.search('continue' if case['id']==7 else 'phrase' if case['id']==8 else 'note',c['prompt'],re.I):raise RuleFailure('wrong prompt subject')
        if t=='text_transform_node' and c['operation'] not in case['required_operations']:raise RuleFailure('unrequested transform')
        if t=='file_reader_node':
            if c['input_source']!='Configured' or case['id'] not in reads:raise RuleFailure('unresolved/unrequested reader')
            path=safe_path(c['file_path'],case['root'])
            if path!=Path(case['root'])/reads[case['id']]:raise RuleFailure('wrong read path')
        if t=='file_output_node':
            if c['file_path_source']!='Configured' or case['id'] not in writes:raise RuleFailure('unresolved/unrequested writer')
            path=safe_path(c['file_path'],case['root'])
            if path!=Path(case['root'])/writes[case['id']]:raise RuleFailure('wrong write path')
            if c['write_mode']!='Create unique' or any(c.get(k) for k in ('binary_content','interpret_newlines','open_after_write','close_on_run_end','dead_drop_passthrough')) or not c['transient_output']:raise RuleFailure('unsafe writer flags')
    if case['id']==8 and not any(n['type']=='branch_node' for n in nodes.values()):raise RuleFailure('parallel node required')
    return nodes,out


def evaluate(spec,case,variant):
    nodes,out=safety(spec,case);root=Path(case['root']);vault={};outputs=[];writes=[];prompts=[];visited=[];ends=[]
    answers=iter(variant['answers']);pending=[(h,Value(''),frozenset()) for h,n in nodes.items() if n['type']=='start_node']
    if len(pending)!=1:raise RuleFailure('one Start required')
    def source(c,port,incoming,configured=None):
        mode=c.get(port+'_source','Upstream payload')
        if mode=='Vault':
            key=c.get(port+'_vault_key','')
            if key not in vault:raise RuleFailure('Vault read without preceding writer')
            return vault[key]
        if mode=='Configured':return Value(c.get(configured or port,''))
        if mode!='Upstream payload':raise RuleFailure('unknown input source')
        return incoming
    while pending:
        h,value,ancestors=pending.pop()
        if h in ancestors:raise RuleFailure('cycle')
        visited.append(h);node=nodes[h];c=node['config'];t=node['type'];port='default';ancestors=ancestors|{h}
        if len(visited)>128:raise RuleFailure('step bound exceeded')
        if t=='start_node':value=Value(c['greeting'])
        elif t in ('end_node','branch_end_node'):
            if t!='end_node':raise RuleFailure('route must end at End')
            ends.append(h);continue
        elif t=='user_text_input_node':
            try:answer=next(answers)
            except StopIteration:raise RuleFailure('extra prompt') from None
            prompts.append(c['prompt']);value=Value(answer,origins=('answer',))
        elif t=='file_reader_node':
            filename=Path(c['file_path']).name
            if filename not in variant['files']:
                return dict(outputs=outputs,writes=writes,prompts=prompts,visited=visited,error=True)
            value=Value(variant['files'][filename],origins=('file',))
        elif t=='text_transform_node':
            op=c['operation'];data=str(value.data or '')
            value=Value({'uppercase':str.upper,'lowercase':str.lower,'strip':str.strip}[op](data),value.operations+(op,),value.origins)
        elif t=='conditional_node':port='true' if str(value.data)==c['right_value'] else 'false'
        elif t=='branch_node':
            # Shared Vault writes in parallel cannot be proven race-free here.
            if any((n['config'].get('vault_write') or n['config'].get('membank_outputs')) and key not in ancestors for key,n in nodes.items()):raise RuleFailure('parallel Vault writes need review')
            for branch in ('path_a','path_b'):
                target=out.get(h+'.'+branch)
                if not target:raise RuleFailure('missing branch')
                pending.append((target[0].split('.')[0],value,ancestors))
            continue
        elif t=='concat_node':value=format_value(c['template'],dict(vault,input=value))
        elif t=='json_path_node':
            data=json.loads(value.data) if isinstance(value.data,str) else value.data
            for part in c['path'].split('.'):
                if part:data=data.get(part,c['default_value']) if isinstance(data,dict) else data[int(part)]
            value=Value(data,value.operations,value.origins)
        elif t=='text_output_node':
            value=source(c,'input',value);body=format_value(c['template'],{'input':value})
            if case['id'] in (7,9) and not body.origins:
                body=Value(body.data,value.operations,value.origins)
            outputs.append(dict(handle=h,body=body.data,operations=body.operations,origins=body.origins))
            value=Value('['+c['label']+'] '+body.data,body.operations,body.origins)
        elif t=='file_output_node':
            content=source(c,'content',value);path=str(root/(Path(c['file_path']).stem+' (trial unique)'+Path(c['file_path']).suffix))
            writes.append(dict(handle=h,path=path,requested=Path(c['file_path']).name,content=content.data,operations=content.operations,origins=content.origins))
            value=Value({'path':path,'kind':'file'},content.operations,content.origins)
        else:raise RuleFailure('unsupported type')
        if c.get('vault_write'):vault[c['vault_write_key']]=value
        for declaration in c.get('membank_outputs',[]):vault[declaration.get('output') or declaration['id']]=value
        if t=='file_reader_node' and not c['transient_output']:value=Value(None)
        target=out.get(h+'.'+port)
        if not target:raise RuleFailure('nonterminal route ends before End')
        pending.append((target[0].split('.')[0],value,ancestors))
    try:next(answers);raise RuleFailure('missing prompt')
    except StopIteration:pass
    if not ends:raise RuleFailure('no End')
    return dict(outputs=outputs,writes=writes,prompts=prompts,visited=visited,error=False)


def check_rules(spec,case):
    from backend.authoring import check_workflow_spec
    from backend.node_factory import NodeFactory
    rows=[]
    def record(rule,ok,evidence):rows.append(dict(id=str(case['id'])+'.'+rule,result='pass' if ok else 'fail',evidence=evidence))
    try:
        structural=check_workflow_spec(NodeFactory(),spec)
        record('structure',structural['ok'] and not structural['diagnostics'],structural['diagnostics'])
        safety(spec,case);record('path_type_safety',True,'All nodes, including error routes, inspected')
        for variant in fixture_variants(case['id']):
            result=evaluate(spec,case,variant);writes=result['writes'];outputs=result['outputs']
            expected=[writes[0]['path'] if x=='@path' and writes else x for x in variant['outputs']]
            ok=result['error']==variant['error'] and Counter(o['body'] for o in outputs)==Counter(expected)
            ok=ok and {w['requested']:w['content'] for w in writes}==variant['writes'] and len(writes)==len(variant['writes'])
            ok=ok and len(result['prompts'])==len(variant['answers'])
            witnesses=writes or outputs
            if not result['error']:
                actual_ops=[o for w in witnesses for o in w['operations']]
                needed=case['required_operations'] if not (case['id']==9 and not writes) else ['strip']
                ok=ok and all(op in actual_ops for op in needed)
                if case['id'] in (3,6,7,8):ok=ok and all('answer' in w['origins'] for w in witnesses)
                if case['id'] in (4,5,9,10):ok=ok and all('file' in w['origins'] for w in witnesses)
            record('semantics.'+variant['name'],ok,result)
    except (RuleFailure,ValueError,KeyError,TypeError,IndexError,AttributeError) as exc:record('bounded_evaluation',False,str(exc))
    return dict(result='pass' if rows and all(r['result']=='pass' for r in rows) else 'fail',rules=rows)

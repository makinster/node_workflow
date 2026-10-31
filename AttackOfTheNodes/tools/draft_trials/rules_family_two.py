"""Unadmitted Family 2 scorer. Shared graph proof; independent event/value model.

Only explicit offline callers reach this module. No runtime collector or node
execute methods are used by the logical scheduler. Two orders are not exhaustive.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from copy import deepcopy
import json
from pathlib import Path
import re
from string import Formatter

from backend.flow_behaviors import Kind, analyze_flow, port_order
from backend.node_factory import NodeFactory
from backend.output_entry import text_output_prefix
from .rules import NeedsReview, RuleFailure, safe_path, effective_nodes
from .case_set_four import fixture_variants

POLICY_VERSION = 'family-2-evaluator-1'
LOCAL_TYPES = frozenset('start_node end_node branch_node merge_node wait_until_node file_reader_node json_path_node concat_node text_output_node text_transform_node conditional_node context_pack_node'.split())


def graph_nodes(spec):
    """Spec adapter only. Reachability/groups/guards/cardinality belong to analyze_flow."""
    nodes = {h:dict(n, alias=n.get('alias') or h, connections=dict(inputs=[],outputs=[]))
             for h,n in spec['nodes'].items()}
    for edge in spec.get('connections',[]):
        source,port=edge['from'].split('.',1)
        target,slot=edge['to'].split('.',1)
        wire=dict(source_node_id=source,source_port=port,target_node_id=target,target_port=slot)
        if source in nodes:
            nodes[source]['connections']['outputs'].append(wire)
        if target in nodes:
            nodes[target]['connections']['inputs'].append(wire)
    return nodes


def safety(spec, case):
    if spec.get('format')!='aotn-workflow/1' or spec.get('callable'):
        raise RuleFailure('unsupported spec/callable')
    if not spec.get('nodes') or len(spec['nodes'])>64:
        raise NeedsReview('outside the bounded 64-node evaluation')
    if any(n.get('type') not in LOCAL_TYPES for n in spec['nodes'].values()):
        raise RuleFailure('outside evaluation palette / not admitted')
    nodes=effective_nodes(spec)
    analysis=analyze_flow(graph_nodes(spec),NodeFactory(),draft=True)
    if not analysis.success:
        raise RuleFailure('; '.join(f.code+': '+f.message for f in analysis.findings if f.level=='error'))
    if case['required_stage']>case.get('evaluation_stage',1) or (case.get('evaluation_stage',1)==1 and analysis.admission_stage>1):
        raise RuleFailure('outside this admission stage (evaluation only; no admission granted)')
    outgoing={}
    for edge in spec['connections']:
        if edge['from'] in outgoing:
            raise RuleFailure('ordinary output fan-out')
        source,port=edge['from'].split('.',1)
        target,slot=edge['to'].split('.',1)
        if source not in nodes or target not in nodes:
            raise RuleFailure('missing node')
        if port not in NodeFactory().node_output_ports(nodes[source]) or slot not in NodeFactory().node_input_ports(nodes[target]):
            raise RuleFailure('undeclared/hidden port')
        outgoing[edge['from']]=(target,slot)
    for h,n in nodes.items():
        c=n['config']
        t=n['type']
        if any(c.get(k) for k in ('membank_inputs','membank_outputs','transient_outputs','node_errors','breakpoint','return_end')):
            raise NeedsReview('legacy routing/recovery outside bounded evaluation')
        if t=='start_node' and (c.get('rows') or c.get('no_inputs')):
            raise NeedsReview('Start rows outside bounded evaluation')
        if t=='text_output_node' and c.get('request_user_input'):
            raise RuleFailure('unrequested runtime prompt')
        if t=='file_reader_node':
            if c.get('input_source')!='Configured':
                raise NeedsReview('dynamic file references need execution review')
            safe_path(c['file_path'],case['root'])
        if t=='context_pack_node' and (c.get('include_run') or c.get('include_errors')):
            raise NeedsReview('run-dependent Context Pack needs review')
    if case.get('evaluation_stage',1)==1 and any(m.independent_ends for m in analysis.merges.values()):
        raise RuleFailure('outside this admission stage: Stage 1 joins every path')
    from backend.authoring import check_workflow_spec
    structural=check_workflow_spec(NodeFactory(),spec)
    if not structural['ok']:
        raise RuleFailure('invalid spec: '+json.dumps(structural['diagnostics']))
    return nodes,outgoing,analysis


@dataclass
class Use:
    start: int
    end: int
    expression: tuple
    value: object


@dataclass
class Datum:
    data: object = None
    expression: tuple = ()
    children: dict = field(default_factory=dict)
    uses: list = field(default_factory=list)
    present: bool = True

    def __post_init__(self):
        if not self.expression:
            self.expression=('literal',self.data)


def project(value, key, default='', *, strict=False):
    if key in value.children:
        return value.children[key]
    if isinstance(value.data,list) and value.children:
        try:
            index=int(key)
            if -len(value.data)<=index<len(value.data):
                return value.children[str(index % len(value.data))]
        except ValueError:
            pass
    data=value.data
    if isinstance(data,str):
        data=json.loads(data)
    try:
        if isinstance(data,dict):
            result=data[key]
        elif isinstance(data,list):
            result=data[int(key)]
        else:
            if strict:
                raise RuleFailure('missing template field '+key)
            return Datum(default)
    except (KeyError,ValueError,IndexError):
        if strict:
            raise RuleFailure('missing template field '+key)
        return Datum(default)
    return Datum(result,('project',str(key),value.expression))


def render(template,values):
    text=''
    uses=[]
    fields=[]
    for literal,name,spec,conversion in Formatter().parse(template):
        text+=literal
        if name is None:
            continue
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:\[[A-Za-z_0-9-]+\])*',name) or spec or conversion:
            raise NeedsReview('format field outside bounded whole-value evaluation')
        key=name.split('[')[0]
        if key not in values or not values[key].present:
            raise RuleFailure('missing template value '+key)
        value=values[key]
        for part in re.findall(r'\[([^]]+)\]',name):
            value=project(value,part,strict=True)
        piece=str(value.data)
        start=len(text)
        text+=piece
        if value.uses and isinstance(value.data,str):
            uses.extend(Use(start+u.start,start+u.end,u.expression,u.value) for u in value.uses)
        else:
            uses.append(Use(start,len(text),value.expression,value.data))
        fields.append(value.expression)
    expr=fields[0] if len(fields)==1 and template.startswith('{') and template.endswith('}') and template.count('{')==1 else ('format',template,tuple(fields))
    if not fields:
        expr=('literal',text)
    return Datum(text,expr,uses=uses)


@dataclass
class Worker:
    id: int
    node: str
    value: Datum
    group: str | None = None
    lineage: tuple = ()
    depth: int = 0
    slot: str = 'input'
    state: str = 'ready'
    wait_targets: tuple = ()


def evaluate(spec,case,variant,*,order='forward',stop_after=None):
    nodes,outgoing,analysis=safety(spec,case)
    if order not in ('forward','reverse'):
        raise ValueError('unknown order')
    workers={}
    groups={}
    receipts=defaultdict(list)
    outputs=[]
    visits=[]
    completed=set()
    events=[]
    collected=[]
    vault={}
    sequence=0
    count=0
    def spawn(node,value,group=None,lineage=(),depth=0,slot='input'):
        nonlocal sequence
        sequence+=1
        w=Worker(sequence,node,value,group,lineage,depth,slot)
        workers[w.id]=w
        if group:
            groups[group]['active'].add(w.id)
        return w
    starts=[h for h,p in analysis.profiles.items() if p.entry]
    if len(starts)!=1:
        raise RuleFailure('one Start required')
    spawn(starts[0],Datum('',present=False))
    def source(c,incoming):
        mode=c.get('input_source','Upstream payload')
        if mode=='Vault':
            key=c.get('input_vault_key','')
            if key not in vault:
                raise RuleFailure('Vault input unavailable')
            return vault[key]
        if mode=='Configured':
            return Datum(c.get('input',''))
        return incoming
    def finish(w):
        w.state='finished'
        if w.group:
            groups[w.group]['active'].discard(w.id)
    def advance(w,value,port='default'):
        target=outgoing.get(w.node+'.'+port)
        if not target:
            finish(w)
            return
        w.node,w.slot=target
        w.value=value
        w.state='ready'
    def settle():
        for w in workers.values():
            if w.state=='wait' and set(w.wait_targets)<=completed:
                completed.add(w.node)
                events.append(dict(event='completed',node=w.node,worker=w.id))
                advance(w,w.value)
        for (gid,mid),arrivals in list(receipts.items()):
            active=groups[gid]['active']
            if not active or not all(workers[i].state=='join' and workers[i].node==mid for i in active):
                continue
            winner=min(arrivals,key=lambda a:(a['worker'].depth,a['sequence']))['worker']
            fields={}
            for slot,schema in analysis.merges[mid].slots.items():
                ordered=[tuple(tuple(p) for p in a['lineage']) for a in schema['producers']]
                present=[a for a in arrivals if a['slot']==slot and a['value'].present]
                present.sort(key=lambda a:ordered.index(a['worker'].lineage))
                if not present:
                    continue
                if schema['cardinality']=='one':
                    if len(present)!=1:
                        raise RuleFailure('multiple concurrent arrivals in scalar slot')
                    fields[slot]=present[0]['value']
                elif schema['cardinality']=='many':
                    members=[a['value'] for a in present]
                    fields[slot]=Datum([a.data for a in members],('list',tuple(a.expression for a in members)),children={str(i):a for i,a in enumerate(members)})
                else:
                    raise NeedsReview('unproved slot shape')
            value=Datum({slot:v.data for slot,v in fields.items()},('record',mid),children=fields)
            collected.append(dict(node=mid,value=deepcopy(value.data),winner=winner.id,lineage=winner.lineage,depth=winner.depth,pass_number=1))
            for arrival in arrivals:
                w=arrival['worker']
                if w is not winner:
                    finish(w)
                    events.append(dict(event='absorbed',node=mid,worker=w.id))
            active.clear()
            winner.group=None
            winner.lineage=()
            # Publish before the one completion event; absorbed paths never complete Merge.
            completed.add(mid)
            events.append(dict(event='completed',node=mid,worker=winner.id))
            advance(winner,value)
            del receipts[gid,mid]
    errors=[]
    state='finished'
    try:
        while True:
            settle()
            ready=[w for w in workers.values() if w.state=='ready']
            if not ready:
                if any(w.state in ('wait','join') for w in workers.values()):
                    raise RuleFailure('stuck: blocked obligations with no runnable work')
                break
            if stop_after is not None and count>=stop_after:
                state='cancelled'
                events.append(dict(event='cancelled'))
                break
            count+=1
            if count>256:
                raise NeedsReview('logical supervisor step bound exceeded')
            ready.sort(key=lambda w:(tuple(port_order(p) for _,p in w.lineage),w.id),reverse=order=='reverse')
            w=ready[0]
            h=w.node
            p=analysis.profiles[h]
            n=nodes[h]
            c=n['config']
            t=n['type']
            incoming=w.value
            visits.append(dict(handle=h,worker=w.id,lineage=w.lineage,depth=w.depth,group=w.group,step=count))
            events.append(dict(event='running',node=h,worker=w.id))
            value=incoming
            port='default'
            if p.kind==Kind.FINISH:
                completed.add(h)
                finish(w)
                continue
            if p.kind==Kind.FORK:
                gid=w.group or h+':'+str(w.id)
                groups.setdefault(gid,dict(root=h,active=set()))
                batch=p.batches[0]
                if p.exclusive:
                    # Legacy selected batches are known profiles, but variable
                    # string-match forks are outside the requests in this half.
                    raise NeedsReview('conditional fork selection needs review')
                children=[]
                for branch in batch:
                    target=outgoing.get(h+'.'+branch)
                    if not target:
                        raise RuleFailure('missing branch path')
                    seed=c.get('branch_payload_sources',{}).get(branch,'')
                    seed_value=incoming if incoming.present else Datum('')
                    value=vault.get(seed[6:],seed_value) if seed.startswith('vault:') else seed_value
                    children.append((target,value,w.lineage+((h,branch),)))
                # Register the entire batch before removing the handed-off parent.
                for (target,slot),payload,lineage in children:
                    spawn(target,payload,gid,lineage,w.depth+1,slot)
                finish(w)
                completed.add(h)
                events.append(dict(event='handoff',node=h,children=len(children)))
                continue
            if p.kind==Kind.JOIN:
                if not w.group:
                    advance(w,incoming)
                    completed.add(h)
                    continue
                w.state='join'
                receipts[w.group,h].append(dict(worker=w,slot=w.slot,value=incoming,sequence=count))
                continue
            if p.kind==Kind.WAIT:
                value=incoming if incoming.present else Datum('')
                if not set(p.targets)<=completed:
                    w.state='wait'
                    w.wait_targets=p.targets
                    w.value=value
                    continue
            elif t=='start_node':
                value=Datum(c.get('greeting',''))
            elif t=='file_reader_node':
                filename=safe_path(c['file_path'],case['root']).relative_to(Path(case['root'])).as_posix()
                if filename not in variant['files']:
                    raise RuleFailure('file missing')
                value=Datum(variant['files'][filename].replace('\r\n','\n').replace('\r','\n'),('file',filename))
            elif t=='json_path_node':
                value=incoming
                for segment in str(c['path']).strip().split('.'):
                    if segment:
                        value=project(value,segment,c.get('default_value',''))
            elif t=='text_transform_node':
                op=c['operation']
                fn={'uppercase':str.upper,'lowercase':str.lower,'strip':str.strip,'reverse':lambda s:s[::-1]}.get(op)
                if fn is None:
                    raise NeedsReview('transform needs review')
                value=Datum(fn(str(incoming.data or '')),('operation',op,incoming.expression))
            elif t=='conditional_node':
                left=vault.get(c.get('variable_name'),Datum('')) if c.get('left_value_source')=='variable' else incoming if incoming.present else Datum('')
                a,b=str(left.data),str(c.get('right_value',''))
                kind=c.get('condition_type','contains')
                yes=(a==b if kind=='equals' else a!=b if kind=='not_equals' else re.search(b,a) is not None if kind=='regex' else b in a)
                port='true' if yes else 'false'
                value=left
            elif t=='concat_node':
                value=render(c['template'],dict(vault,input=incoming if incoming.present else Datum('')))
            elif t=='context_pack_node':
                value=context_pack(c,incoming,vault)
            elif t=='text_output_node':
                supplied=source(c,incoming)
                if not supplied.present:
                    raise RuleFailure('Text Output required upstream input missing')
                value=render(c['template'],{'input':supplied})
                outputs.append(dict(handle=h,body=value.data,uses=value.uses,step=count,worker=w.id,lineage=w.lineage))
                prefix=text_output_prefix(c['label'])
                value=Datum(prefix+value.data,('label',c['label'],value.expression) if prefix else value.expression,
                            uses=[Use(u.start+len(prefix),u.end+len(prefix),u.expression,u.value) for u in value.uses])
            else:
                raise NeedsReview('local node semantics need review')
            if c.get('vault_write'):
                key=str(c.get('vault_write_key') or '').strip()
                if not key:
                    raise RuleFailure('missing Vault output key')
                vault[key]=value
            if c.get('dead_drop_passthrough'):
                value=incoming
            elif t in ('file_reader_node','concat_node','text_transform_node','context_pack_node','start_node') and not c.get('transient_output',True):
                value=Datum(present=False)
            completed.add(h)
            events.append(dict(event='completed',node=h,worker=w.id))
            advance(w,value,port)
    except NeedsReview:
        raise
    except (RuleFailure,ValueError,KeyError,IndexError,TypeError) as exc:
        state='failed'
        errors.append(str(exc))
        events.append(dict(event='failed',message=str(exc)))
    if state!='finished':
        receipts.clear()
        for group in groups.values():
            group['active'].clear()
    return dict(outputs=outputs,visited=[v['handle'] for v in visits],visits=visits,events=events,
                collected=collected,errors=errors,error=bool(errors),state=state,writes=[],prompts=[],
                analysis=analysis.to_dict(),policy_version=POLICY_VERSION,order=order)


def context_pack(config,incoming,vault):
    """Bounded unredacted text pack subset; unknown masking/trimming needs review."""
    from backend.context_pack import HEADER
    uses=[]
    text=HEADER
    for row in config['items']:
        source=row['source']
        value=incoming if source=='Upstream payload' else vault.get(row.get('vault_key')) if source=='Vault' else Datum(row.get('text',''))
        if value is None or not value.present:
            raise RuleFailure('Context Pack item missing')
        if not isinstance(value.data,str):
            raise NeedsReview('typed JSON Context Pack formatting needs review')
        if not value.data:
            raise NeedsReview('Context Pack marks empty text explicitly; not a lossless empty value')
        from backend.hermes_investigations import redact
        if len(value.data)>config['max_item'] or redact(value.data)!=value.data:
            raise NeedsReview('Context Pack masking/shortening needs review')
        text+='['+row['label']+']\n'
        offset=len(text)
        # Each line has '| ' framing; preserve exact whole-field spans only
        # where no line insertion changes the actual requested value.
        if '\n' in value.data:
            raise NeedsReview('multiline pack provenance needs review')
        text+='| '+value.data+'\n\n'
        uses.extend(Use(offset+2+u.start,offset+2+u.end,u.expression,u.value) for u in value.uses)
        if not value.uses:
            uses.append(Use(offset+2,offset+2+len(value.data),value.expression,value.data))
    text+='Shortened: none.'
    if len(text)>config['max_total']:
        raise NeedsReview('Context Pack shortening needs review')
    return Datum(text,('pack',),uses=uses)


def semantics(result,case,variant):
    if result['error'] or result['state']!='finished':
        return False
    outputs=result['outputs']
    expected_count=2 if case['id']==4 else 1
    if len(outputs)!=expected_count:
        return False
    final=outputs[-1]
    uses=final['uses']
    previous=-1
    for expected in variant['fields']:
        matching=[u for u in uses if json.dumps(u.expression,sort_keys=True)==json.dumps(expected['expression'],sort_keys=True) and u.value==expected['value']
                  and type(u.value)==type(expected['value'])]
        if len(matching)!=1:
            return False
        use=matching[0]
        if use.start<previous or final['body'][use.start:use.end]!=str(expected['value']):
            return False
        label=re.escape(expected['label'])
        if not re.search(r'(?:\b'+label+r'\s*:\s*|\['+label+r'\]\s*(?:\|\s*)?)$',final['body'][:use.start],re.I):
            return False
        if str(expected['value']) and final['body'].count(str(expected['value']))!=1:
            return False
        previous=use.end
    reads=[v for v in result['visits'] if result['analysis']['profiles'][v['handle']]['kind']==Kind.ROUTE
           and v['handle'] in case.get('_read_handles',{})]
    if {case['_read_handles'][v['handle']] for v in reads}!=set(variant['files']):
        return False
    def parallel(a,b):
        return any(fa==fb and pa!=pb for (fa,pa),(fb,pb) in zip(a,b))
    for i,a in enumerate(reads):
        for b in reads[i+1:]:
            if case['_read_handles'][a['handle']]!=case['_read_handles'][b['handle']] and not parallel(a['lineage'],b['lineage']):
                return False
    if not all(v['lineage'] for v in reads):
        return False
    if case['id']==4:
        reader=next((v for v in reads if case['_read_handles'][v['handle']]=='source.txt'),None)
        ready=outputs[0]
        if ready['body']!='Ready' or reader is None or reader['step']>=ready['step']:
            return False
        if not parallel(reader['lineage'],ready['lineage']):
            return False
        waits=[h for h,p in result['analysis']['profiles'].items() if p['kind']==Kind.WAIT and reader['handle'] in p['targets']]
        if not waits or not any(v['handle'] in waits and v['worker']==ready['worker'] for v in result['visits']):
            return False
    if case['id']==3 and result['collected']:
        copies=[v for v in result['visits'] if v['handle'] in case.get('_copy_handles',())]
        if len(copies)!=2 or not parallel(copies[0]['lineage'],copies[1]['lineage']):
            return False
        slow=next(v for v in reads if case['_read_handles'][v['handle']]=='slow.txt')
        if result['collected'][-1]['winner']!=slow['worker']:
            return False
    return True


def check_rules(spec,case):
    rows=[]
    try:
        nodes,_,analysis=safety(spec,case)
        c=dict(case,_read_handles={h:Path(n['config']['file_path']).name for h,n in nodes.items() if n['type']=='file_reader_node'},
               _copy_handles=[h for h,n in nodes.items() if n['type']=='text_transform_node' and n['config']['operation'] in ('uppercase','lowercase')])
        rows.append(dict(id='4.shared_flow',result='pass',evidence=[m.summary for m in analysis.merges.values()]))
        for variant in fixture_variants(case['id']):
            for order in ('forward','reverse'):
                result=evaluate(spec,c,variant,order=order)
                rows.append(dict(id=f"{case['key']}.{variant['name']}.{order}",result='pass' if semantics(result,c,variant) else 'fail',
                                 evidence=dict(outputs=[o['body'] for o in result['outputs']],errors=result['errors'],collected=result['collected'])))
    except NeedsReview as exc:
        rows.append(dict(id='4.needs_review',result='needs_review',evidence=str(exc)))
    except (RuleFailure,KeyError,ValueError,TypeError) as exc:
        rows.append(dict(id='4.safety',result='fail',evidence=str(exc)))
    verdict='fail' if any(r['result']=='fail' for r in rows) else 'needs_review' if any(r['result']=='needs_review' for r in rows) else 'pass'
    return dict(result=verdict,rules=rows,admitted=False,evaluation_stage=case.get('evaluation_stage',1),policy_version=POLICY_VERSION)

"""Bounded set-2 oracle: full-source provenance plus route and file obligations."""
from collections import defaultdict
from pathlib import Path
import re

from .cases import PALETTE
from .case_set_two import fixture_variants
from .rules import (RuleFailure, effective_nodes, safe_path, evaluate, display_matches,
                    display_outputs_match, allows_display_framing)
from .structure_rules import check_required_structure


def safety(spec, case):
    if spec.get('format') != 'aotn-workflow/1' or spec.get('callable'):
        raise RuleFailure('unsupported spec/callable')
    if len(spec.get('nodes', {})) > 64 or any(n.get('type') not in PALETTE for n in spec['nodes'].values()):
        raise RuleFailure('outside bounded palette')
    nodes, outgoing = effective_nodes(spec), defaultdict(list)
    for edge in spec['connections']:
        outgoing[edge['from']].append(edge['to'])
    if any(len(targets) != 1 for targets in outgoing.values()):
        raise RuleFailure('ordinary output fan-out')
    for node in nodes.values():
        t,c = node['type'], node['config']
        if c.get('membank_inputs') or c.get('transient_outputs') or c.get('node_errors') or c.get('breakpoint'):
            raise RuleFailure('unsupported legacy routing/recovery')
        if t == 'start_node' and (c.get('rows') or c.get('no_inputs') or not c.get('transient_output',True)):
            raise RuleFailure('unsupported Start routing')
        if t == 'end_node' and c.get('return_end'):
            raise RuleFailure('unrequested callable return')
        if t == 'branch_end_node':
            raise RuleFailure('routes must terminate at End')
        if t == 'text_output_node' and c.get('request_user_input'):
            raise RuleFailure('extra runtime prompt')
        if t == 'branch_node' and (case['id'] != 8 or c.get('branch_count',2) != 2 or c.get('branch_payload_sources') or c.get('condition','always_branch') != 'always_branch'):
            raise RuleFailure('unrequested branch behavior')
        if t == 'conditional_node' and (case['id'] != 1 or c['condition_type'] != 'equals' or c['left_value_source'] != 'input' or c['right_value'] != 'Go'):
            raise RuleFailure('wrong conditional comparison/source')
        if t == 'user_text_input_node':
            subject = {1:r'word', 2:r'first|last', 8:r'phrase'}.get(case['id'])
            if not subject or not re.search(subject,c['prompt'],re.I):
                raise RuleFailure('unrequested/wrong prompt subject')
        if t == 'text_transform_node' and c['operation'] not in case['required_operations']:
            raise RuleFailure('unrequested transform')
        if t == 'json_path_node' and not (
                (case['id'] == 3 and c['path'] == 'person.nickname') or
                # Picking "path" from the saved-file reference shows the saved path.
                (case['writes'] and c['path'] == 'path')):
            raise RuleFailure('wrong JSON field')
        if t == 'file_reader_node':
            if not case['reads'] or c['input_source'] != 'Configured' or safe_path(c['file_path'],case['root']) != Path(case['root'])/case['reads']:
                raise RuleFailure('wrong reader path/source')
        if t == 'file_output_node':
            if not case['writes'] or c['file_path_source'] != 'Configured' or safe_path(c['file_path'],case['root']) != Path(case['root'])/case['writes']:
                raise RuleFailure('wrong writer path/source')
            if c['write_mode'] != 'Create unique' or not c['transient_output'] or any(c.get(k) for k in ('binary_content','interpret_newlines','open_after_write','close_on_run_end','dead_drop_passthrough')):
                raise RuleFailure('unsafe writer flags')
    return nodes, outgoing


def file_source(expression, case):
    return len(expression) == 3 and expression[0] == 'file' and expression[1] == str(Path(case['root'])/case['reads'])


def answer_source(expression):
    return len(expression) == 2 and expression[0] == 'answer'


def chain(expression, operations, source):
    for op in reversed(operations):
        if len(expression) != 3 or expression[:2] != ('operation',op):
            return False
        expression=expression[2]
    return source(expression)


def provenance(result, case, variant, nodes):
    if result['error']:
        return True
    outputs,writes = result['outputs'],result['writes']
    number=case['id']
    if number == 1:
        op='uppercase' if variant['answers'][0] == 'Go' else 'lowercase'
        port='true' if op == 'uppercase' else 'false'
        return all(chain(o['expression'],[op],answer_source) and any(
            c['port']==port and answer_source(c['expression']) for c in o['controls']) for o in outputs)
    if number == 2:
        asks=[v['handle'] for v in result['visits'] if nodes[v['handle']]['type']=='user_text_input_node']
        if len(asks)!=2 or not re.search('first',nodes[asks[0]]['config']['prompt'],re.I) or not re.search('last',nodes[asks[1]]['config']['prompt'],re.I):
            return False
        for o in outputs:
            e=o['expression']
            if e[0]!='format' or len(e[2])!=2:
                return False
            fields=e[2]
            if e[1]!='{'+fields[0][0]+'} {'+fields[1][0]+'}' or [f[1] for f in fields]!=[('answer',a) for a in asks]:
                return False
        return True
    if number == 3:
        return all(len(o['expression'])==3 and o['expression'][:2]==('project','nickname') and
                   len(o['expression'][2])==3 and o['expression'][2][:2]==('project','person') and
                   file_source(o['expression'][2][2],case) for o in outputs)
    if number == 5:
        return all(chain(o['expression'],['reverse'],lambda e:file_source(e,case)) for o in outputs)
    if number == 10:
        return all(o['expression'][0]=='literal' and display_matches(o['expression'][1],'Hello team',o['framing']) for o in outputs)
    if len(writes)!=1:
        return False
    write=writes[0]
    operations={4:['strip','uppercase'],8:['lowercase'],9:[]}[number]
    source=answer_source if number==8 else lambda e:file_source(e,case)
    orders = [operations]
    if number == 4:
        # These two whole-text operations commute; do not invent a defect.
        orders.append(['uppercase', 'strip'])
    if not any(chain(write['expression'], order, source) for order in orders):
        return False
    path=('saved_path',write['handle'],str(Path(case['root'])/case['writes']),write['expression'])
    if number != 8:
        return all(o['expression']==path for o in outputs)
    upper=[o for o in outputs if chain(o['expression'],['uppercase'],answer_source)]
    paths=[o for o in outputs if o['expression']==path]
    return len(upper)==len(paths)==1 and upper[0]['expression'][2]==write['expression'][2]


def check_rules(spec,case):
    from backend.authoring import check_workflow_spec
    from backend.node_factory import NodeFactory
    rows=[]
    def record(rule,ok,evidence):
        rows.append(dict(id='2.'+str(case['id'])+'.'+rule,result='pass' if ok else 'fail',evidence=evidence))
    try:
        if case['expected_status']!='ready':
            raise RuleFailure('status-only request must not produce a workflow')
        structural=check_workflow_spec(NodeFactory(),spec)
        record('structure',structural['ok'] and not structural['diagnostics'],structural['diagnostics'])
        nodes,_=safety(spec,case)
        record('path_type_safety',True,'All nodes and active source/write flags inspected')
        results=[]
        for variant in fixture_variants(case['id']):
            result=evaluate(spec,case,variant)
            results.append(result)
            writes=result['writes']
            expected=[writes[0]['path'] if e=='@path' and len(writes)==1 else e for e in variant['outputs']]
            semantic=(result['error']==variant['error'] and display_outputs_match(result['outputs'],expected,allows_display_framing(case)) and
                      {w['requested']:w['content'] for w in writes}==variant['writes'] and len(writes)==len(variant['writes']) and
                      len(result['prompts'])==len(variant['answers']))
            record('provenance.'+variant['name'],provenance(result,case,variant,nodes),result)
            record('semantics.'+variant['name'],semantic,result)
        shape=check_required_structure(spec,case['required_structure'],results)
        record('required_structure',shape['result']=='pass',shape)
    except (RuleFailure,ValueError,KeyError,TypeError,IndexError,AttributeError) as exc:
        record('bounded_evaluation',False,str(exc))
    return dict(result='pass' if rows and all(r['result']=='pass' for r in rows) else 'fail',rules=rows)

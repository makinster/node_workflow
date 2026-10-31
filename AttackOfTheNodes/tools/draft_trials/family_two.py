"""Offline Family 2 evidence, not drafter or palette admission.

Usage: python -m tools.draft_trials.family_two --output /fresh/absolute/folder
Stage 1 is the default. --stage 2 explicitly includes withheld Stage 2 fixtures.
There is no inference, judge, real-calls, or admission option.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def provenance():
    from backend.palette_selection import ADMITTED
    from .rules_family_two import POLICY_VERSION
    root=Path(__file__).resolve().parents[2]
    paths=['backend/flow_behaviors.py','backend/node_metadata_review.json','backend/palette_selection.py',
           'tools/draft_trials/rules_family_two.py','tools/draft_trials/family_two_engine.py',
           'tools/draft_trials/family_two.py','tools/draft_trials/rules.py','tools/draft_trials/cases.py',
           'tools/draft_trials/rules_set_two.py','tools/draft_trials/rules_set_three.py',
           'tools/draft_trials/structure_rules.py','tools/draft_trials/fixtures/calibration.json',
           'tools/draft_trials/case_set_four.py','tools/draft_trials/family_two_controls.py',
           'tools/draft_trials/fixtures/case_set_4.json',
           'tools/draft_trials/fixtures/calibration_set_4.json']
    return dict(evaluator_policy=POLICY_VERSION,pass_number=1,admitted=sorted(ADMITTED),
                source_sha256={p:hashlib.sha256((root/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in paths},
                real_api_calls=0,admission_changed=False)


def typed_equal(a,b):
    if type(a)!=type(b):
        return False
    if isinstance(a,dict):
        return list(a)==list(b) and all(typed_equal(a[k],b[k]) for k in a)
    if isinstance(a,list):
        return len(a)==len(b) and all(typed_equal(x,y) for x,y in zip(a,b))
    return a==b


async def evidence(spec,case,variant,order):
    from .rules_family_two import evaluate,safety,RuleFailure,NeedsReview
    from .family_two_engine import run_fixture
    from backend.flow_behaviors import Kind
    try:
        logical=evaluate(spec,case,variant,order=order)
        symbolic=dict(state=logical['state'],outputs=[o['body'] for o in logical['outputs']],collected=logical['collected'],errors=logical['errors'])
    except (RuleFailure,NeedsReview) as exc:
        logical=None
        symbolic=dict(state='preflight_rejected',outputs=[],errors=[str(exc)])
    actual=await run_fixture(spec,case,variant,order=order)
    # Compare events and typed records as well as rendered output. The engine
    # is never supplied the logical evaluator's plan, values, or expected answer.
    agrees=actual['state']==symbolic['state'] and actual['outputs']==symbolic['outputs']
    facts={}
    if logical is not None and actual['state']=='finished':
        nodes,_,analysis=safety(spec,case)
        observed=[p for p in actual['publications'] if p['handle'] in analysis.merges]
        wanted=logical['collected']
        facts['collected_records']=len(observed)==len(wanted) and all(typed_equal(a['value'],b['value']) for a,b in zip(observed,wanted))
        facts['one_merge_completion']=all(sum(e['handle']==mid and e['status']=='done' for e in actual['events'])==1 for mid in analysis.merges)
        if case['id']==3 and observed:
            slow=next((h for h,n in nodes.items() if n['type']=='file_reader_node' and Path(n['config']['file_path']).name=='slow.txt'),None)
            slow_pub=next((p for p in actual['publications'] if p['handle']==slow),None)
            facts['shallow_continuation']=slow_pub is not None and observed[-1]['branch']==slow_pub['branch'] and observed[-1]['depth']==slow_pub['depth']
        if case['id']==4:
            readers={h for h,n in nodes.items() if n['type']=='file_reader_node' and Path(n['config']['file_path']).name=='source.txt'}
            ready_handles={h for h,n in nodes.items() if n['type']=='text_output_node' and n['config']['template']=='Ready'}
            completed_read=[i for i,e in enumerate(actual['events']) if e['handle'] in readers and e['status']=='done']
            ready_started=[i for i,e in enumerate(actual['events']) if e['handle'] in ready_handles and e['status']=='running']
            facts['gate_after_read']=bool(completed_read and ready_started) and min(ready_started)>max(completed_read)
        facts['files_preserved']=actual['files_preserved']
        agrees=agrees and all(facts.values())
    return dict(fixture=variant['name'],order=order,result='pass' if agrees else 'fail',
                correct_output=actual['state']=='finished' and actual['outputs']==variant['outputs'],
                facts=facts,symbolic=symbolic,engine=actual)


async def verify(output,*,stage=1):
    from .case_set_four import case_record,fixture_variants,good_draft,calibration_pairs,case_ids
    from .rules_family_two import check_rules
    output=Path(output)
    cases=[]
    pairs=[]
    for n in case_ids(stage):
        c=case_record(n,output/'fixtures'/f'F2-{n:02d}',stage=stage)
        spec=good_draft(n,c['root'])
        rules=check_rules(spec,c)
        rows=[await evidence(spec,c,v,order) for v in fixture_variants(n) for order in ('forward','reverse')]
        cases.append(dict(id=c['key'],required_stage=c['required_stage'],admitted=False,request=c['request'],
                          rules=rules,result='pass' if rules['result']=='pass' and all(r['result']=='pass' and r['correct_output'] for r in rows) else 'fail',fixtures=rows))
    for pair in calibration_pairs(stage=stage):
        c=case_record(pair['case'],output/'fixtures'/pair['id'],stage=stage)
        variants={}
        for kind in ('good','bad'):
            spec=json.loads(json.dumps(pair[kind]).replace('ROOT',c['root']))
            rules=check_rules(spec,c)
            rows=[await evidence(spec,c,v,order) for v in fixture_variants(pair['case']) for order in ('forward','reverse')]
            expected=kind=='good'
            # A wrong bad example must not be relabelled good just because it
            # completed normally. Conversely an expected preflight refusal is
            # reported as a refusal, never claimed to have executed node work.
            engine_ok=all(r['correct_output']==expected and r['result']=='pass' for r in rows)
            variants[kind]=dict(result='pass' if (rules['result']=='pass')==expected and engine_ok else 'fail',
                                expected_correct=expected,rules=rules,fixtures=rows)
        pairs.append(dict(id=pair['id'],number=pair['number'],required_stage=pair['required_stage'],
                          result='pass' if all(v['result']=='pass' for v in variants.values()) else 'fail',variants=variants))
    from .family_two_controls import controls
    from .family_two_engine import run_fixture
    control_rows=[]
    for control in controls(stage):
        c=case_record(1,output/'fixtures'/control['id'],stage=stage)
        spec=json.loads(json.dumps(control['spec']).replace('ROOT',c['root']))
        rules=check_rules(spec,c)
        runs=[await run_fixture(spec,c,fixture_variants(1)[0],order=order) for order in ('forward','reverse')]
        ok=rules['result']==control['expected_draft'] and all(r['state']==control['expected_engine'] for r in runs)
        if control['id']=='shared_vault_replacement_unordered':
            ok=ok and runs[0]['outputs']!=runs[1]['outputs']
        if control['id']=='standalone_merge':
            ok=ok and all(r['outputs']==['pass through'] for r in runs)
        control_rows.append(dict(id=control['id'],required_stage=control['required_stage'],result='pass' if ok else 'fail',
                                 rules=rules,engine=runs,expected_engine=control['expected_engine']))
    report=dict(schema_version=1,case_set=4,evaluation_only=True,stage=stage,admitted=False,
                stage_2_default=False,provenance=provenance(),
                result='pass' if all(r['result']=='pass' for r in cases+pairs+control_rows) else 'fail',cases=cases,calibration=pairs,controls=control_rows,
                limits=['Two controlled ready orders, not exhaustive interleavings.',
                        'Unsupported local formatting/masking forms require review.',
                        'No admission, judge-quality or fresh drafting-quality claim.'])
    output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Fresh absolute evidence folder')
    parser.add_argument('--stage',type=int,choices=(1,2),default=1,help='Offline evaluation stage; 2 includes withheld cases and pairs')
    args=parser.parse_args()
    # Set isolation before importing any backend modules. This command neither
    # reads the owner library nor enables the production draft palette.
    root=args.output.expanduser()
    if not root.is_absolute() or root.exists() or '..' in root.parts:
        parser.error('--output must be a fresh absolute directory')
    from .containment import checked_root
    checked_root(root)
    root.mkdir(parents=True)
    os.environ['AOTN_DATA_DIR']=str(root/'library')
    report=asyncio.run(verify(root,stage=args.stage))
    print(json.dumps(dict(result=report['result'],case_set=4,evaluation_stage=args.stage,
                          cases=len(report['cases']),pairs=len(report['calibration']),real_api_calls=0,
                          admitted=False,report=str(root/'report.json'))))
    return 0 if report['result']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())

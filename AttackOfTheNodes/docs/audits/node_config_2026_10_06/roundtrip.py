"""Save/reopen every captured schema mode and composed routing toggle.
Preview-only toggles intentionally have no persistence requirement.
"""
import asyncio,gzip,json
from capture import *
async def main():
    with gzip.open(OUT/'evidence.json.gz','rt') as f:baseline=json.load(f)
    factory=NodeFactory();records=[]
    for m in factory.get_node_types_metadata():
        typ=m['type']
        if typ=='tombstone_node':continue
        default=baseline[f'{typ}_100.json']
        variants=[x for x in default.get('states',[]) if x['control'].startswith('field-') or x['control'] in ['dead-drop-passthrough','vault-output-disabled-default','branch-count']]
        for variant in variants:
            wid=variant['control'];requested=variant['requested']
            wm,nid,mem=setup(factory,typ);s=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),mem,Secrets());results=[]
            row={'type':typ,'control':wid,'requested':requested}
            async with Harness(s,results).run_test(size=(100,24)) as p:
                await p.pause(.01);w=s.query_one('#'+wid)
                w.value=str(requested) if isinstance(w,Input) else requested
                await p.pause(.01);row['actual_before_save']=clean(w.value)
                s.action_save();await p.pause(.01)
            row['save_result']=results
            if results and isinstance(results[-1],dict):
                wm.update_node_config(nid,results[-1]['config']);r=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),mem,Secrets())
                async with Harness(r,[]).run_test(size=(100,24)) as p:
                    await p.pause(.01);w=r.query_one('#'+wid);row['reopened_value']=clean(w.value)
                    row['roundtrip_equal']=row['actual_before_save']==row['reopened_value']
            records.append(row)
        print(typ,len(variants),'roundtrips',flush=True)
    # Merge with the packed baseline rather than leaving a partial raw set.
    baseline['roundtrip.json']=records
    with gzip.open(OUT/'evidence.json.gz','wt',encoding='utf-8') as f:json.dump(baseline,f,separators=(',',':'),ensure_ascii=False)
    print('TOTAL',len(records),'mismatches',sum(not r.get('roundtrip_equal') for r in records),flush=True)
if __name__=='__main__':asyncio.run(main())

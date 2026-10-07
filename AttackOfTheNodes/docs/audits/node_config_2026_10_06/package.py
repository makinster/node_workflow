"""Validate/pack capture outputs and generate a readable control inventory."""
import gzip, json, inspect
from pathlib import Path
from capture import OUT, NodeFactory

def cell(value):
    if isinstance(value,(dict,list)): value=json.dumps(value,ensure_ascii=False,default=str)
    return str(value).replace('|','\\|').replace('\n','<br>').replace('\r','')
def state(w):
    return {k:w[k] for k in ('class','label','text','value','options','selected','display','disabled') if k in w}
def pack():
    raw={p.name:json.loads(p.read_text()) for p in OUT.glob('*.json')}
    if not raw:
        with gzip.open(OUT/'evidence.json.gz','rt') as f: raw=json.load(f)
    if 'roundtrip.json' in raw:
        assert len(raw['roundtrip.json']) == 87
        assert all(row.get('roundtrip_equal') for row in raw['roundtrip.json'])
    nodes=raw['metadata.json']['nodes']; factory=NodeFactory()
    records=[v for v in raw.values() if isinstance(v,dict) and 'stylesheet' in v]
    assert len(nodes)==35 and len(records)==102
    assert all(r['stylesheet']=='frontend/styles.tcss' for r in records)
    assert all(r['cancel_unchanged'] and r['cancel_result']==[None] for r in records if r['width']==100)
    assert all(r['second_save_equal'] and r['save_did_not_mutate'] for r in records if r['width']!=100)
    assert {r['type'] for r in records if r.get('unrelated_preserved')}=={'wait_until_node'}
    assert not any(r.get('state_errors') for r in records)
    lines=['# Mounted configuration control inventory','',
           'Generated from production-CSS mounts. Read with [the audit](../../NODE_CONFIG_UI_AUDIT.md).',
           'Each default table inventories the 100-column composition, including hidden controls,',
           'static labels, previews and buttons. Three-width regions, keyboard traces, full schemas,',
           'defaults, ports and all alternate-state snapshots are in `evidence.json.gz`.',
           'Alternate rows below show changed control state, not an assertion that execution supports it.',
           'Tab visibility is separate from a field’s own conditional display state. Blank IDs denote',
           'informational widgets. No secret values or owner workflow data were captured.','']
    for m in nodes:
        typ=m['type'];cls=factory._node_registry[typ];src=Path(inspect.getfile(cls)).relative_to(OUT.parents[2])
        spec=OUT.parents[3]/'aotn_node_helper/specs'/f'{typ}.yaml'
        lines += [f'## {m["display_name"]} — `{typ}`','',f'Source: `{src}`. Helper spec: '+(f'`aotn_node_helper/specs/{typ}.yaml`.' if spec.exists() else 'none.'),'',
                  f'Selector family/group: **{m["primary_family"]} / {m["group"] or "direct"}**.',
                  f'Ports: `{cell(m["input_ports"])}` → `{cell(m["output_ports"])}`.','',
                  'Defaults:','', '```json',json.dumps(m['default_config'],indent=2), '```','']
        if typ=='tombstone_node':
            lines+=['Intentionally no ordinary config mount: restore/replace record, excluded from selector.',''];continue
        data=raw[f'{typ}_100.json'];all_widgets=[]
        for tab,tabdata in data['default'].items():
            lines += [f'### {tabdata.get("title", "Flat form")}','',
                      '| Widget ID | Type | Label / text / choices | Initial value | Display / disabled |',
                      '|---|---|---|---|---|']
            for w in tabdata['widgets']:
                all_widgets.append(w)
                desc=w.get('label',w.get('text',''))
                if 'options' in w:desc += ' Options: '+cell(w['options'])
                lines.append('| '+ ' | '.join([cell(w.get('id') or '—'),w['class'],cell(desc),cell(w.get('value',w.get('selected',''))),f'{w["display"]} / {w["disabled"]}'])+' |')
            lines+=['',f'Navigation candidates: `{cell(tabdata["focus_order"])}`.','']
        if list(data['default'])!=['flat']:
            lines+=['### Shared dialog chrome','']
            for w in data['chrome']:
                if w['class'] in ['ContentTab','Tab','Underline']:continue
                lines += [f'- `{w.get("id") or w["class"]}`: {cell(w.get("label",w.get("text","")))}']
            lines+=['']
        baseline={w['id']:state(w) for w in all_widgets if w['id']}
        lines+=['### Alternate controls inspected','']
        for alt in data.get('states',[]):
            changed={w['id']:state(w) for w in alt['widgets'] if w['id'] and state(w)!=baseline.get(w['id'])}
            # Remove chrome and changes solely due to preview tab timing.
            changed={k:v for k,v in changed.items() if k not in ['save-node-config','cancel-node-config','alias-input'] and not k.startswith('--')}
            lines += [f'- `{alt["control"]}` → `{cell(alt["requested"])}` (actual `{cell(alt.get("actual",alt["requested"]))}`): '+cell(changed)]
        if not data.get('states'):lines+=['No selectable mode/checkbox variations in this composition.']
        roundtrips=[r for r in raw.get('roundtrip.json',[]) if r['type']==typ]
        if roundtrips:
            lines+=['', f'Additional changed mode/routing save-reopen checks: **{len(roundtrips)}**, all selected values retained.']
        lines += ['',f'Cancel unchanged: **{data["cancel_unchanged"]}**. Unknown key survives Save: **{raw[f"{typ}_60.json"]["unrelated_preserved"]}**. Second Save stable: **{raw[f"{typ}_60.json"]["second_save_equal"]}**.','']
    (OUT/'INVENTORY.md').write_text('\n'.join(lines)+'\n')
    with gzip.open(OUT/'evidence.json.gz','wt',encoding='utf-8') as f:json.dump(raw,f,separators=(',',':'),ensure_ascii=False)
    # These are this script suite's synthetic intermediate files only.
    for name in raw:
        p=OUT/name
        if p.exists() and p.suffix=='.json':p.unlink()
    print(f'Validated {len(nodes)} types, {len(records)} width records, '+str(sum(len(r.get('states',[])) for r in records))+' alternate states; packed evidence.')
if __name__=='__main__':pack()

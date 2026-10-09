"""Capture the current merged inventory; preserve the earlier pre-fix audit."""
import asyncio, gzip, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'node_config_2026_10_06'))
import capture
capture.OUT=HERE
asyncio.run(capture.main())
records={p.name:json.loads(p.read_text()) for p in HERE.glob('*.json')}
captures=[r for r in records.values() if isinstance(r,dict) and 'stylesheet' in r]
cancels=[r for r in captures if r['width']==100]
saves=[r for r in captures if r['width']!=100]
summary={'registry_count':len(records['metadata.json']['nodes']), 'mounts':len(captures),
         'cancel_unchanged':sum(r.get('cancel_unchanged',False) for r in cancels),
         'cancel_checks':len(cancels),'unrelated_preserved':sum(r.get('unrelated_preserved',False) for r in saves),
         'save_checks':len(saves),'second_save_equal':sum(r.get('second_save_equal',False) for r in saves),
         'conditional_states':sum(len(r.get('states',[])) for r in captures),
         'state_errors':[(r['type'],r['state_errors']) for r in captures if r.get('state_errors')]}
assert summary['cancel_unchanged']==len(cancels),summary
assert summary['unrelated_preserved']==len(saves),summary
assert summary['second_save_equal']==len(saves),summary
assert not summary['state_errors'],summary
with gzip.open(HERE/'evidence.json.gz','wt') as f:json.dump(records,f,separators=(',',':'),default=str)
for name in records:(HERE/name).unlink()
(HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('CURRENT_UI_VERIFICATION',json.dumps(summary),flush=True)

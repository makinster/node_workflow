"""Measure final Compact serializations from the registered node's execution."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from backend.node_factory import NodeFactory
from backend.authoring import list_node_types
from backend.node_catalogue import is_debug
from backend.node_catalogue import compact_json
from backend.node_base import NodeContext
from backend.memory_bank import MemoryBank
from backend.event_bus import EventBus

async def run(format):
    node=NodeFactory().create_node('node_catalogue_node','measure')
    node.config['format']=format
    done=[];errors=[]
    context=NodeContext(node_id='measure',branch_id='measure',run_id='measure',inputs={},
        memory_bank=MemoryBank(EventBus()),signal_done=done.append,signal_error=errors.append,
        signal_waiting_for_input=lambda _:None,wait_for_nodes=lambda *args:None,wait_for_merge=lambda *args:None)
    await node.execute(context)
    assert not errors,errors
    value=done[0]['data']['default']
    serialized=compact_json(value) if format=='JSON' else value
    return value,dict(characters=len(serialized),utf8_bytes=len(serialized.encode('utf-8')))

async def main():
    text,ts=await run('Text');record,js=await run('JSON')
    default=NodeFactory()._node_registry['node_catalogue_node'].default_config['max_chars']
    report=dict(schema_version=1,measured_at=datetime.now(timezone.utc).isoformat(),
        baseline='3f365520730493f1e1ecd24ee592befb23ca5ef5',candidate='codex/meta-nodes',
        detail='Compact',scope='All nodes',include_debug=False,matched_count=record['matched_count'],
        text=ts,json=js,default_cap=default,allowed_range=[512,64000],
        headroom_fraction=default/max(ts['characters'],js['characters'])-1,
        measurement='Complete final output, including headers/JSON envelope; JSON is compact ensure_ascii=False.',
        excluded_debug=[row['type'] for row in list_node_types(NodeFactory())
                        if is_debug(NodeFactory().metadata_for_type(row['type']))])
    out=Path(__file__).resolve().parent
    (out/'catalogue-size.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':asyncio.run(main())

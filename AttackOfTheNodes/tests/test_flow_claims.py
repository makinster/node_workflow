"""One source-bound receipt runner for real flow coordinator assertions.

AOTN_FLOW_CLAIMS_REPORT=<path> pytest -k flow_claims_receipt deliberately exports.
Instrumentation observes starts/final records; no node or wait callback is faked.
"""
import importlib
import inspect
import json
import os
from copy import deepcopy
from pathlib import Path

import pytest

from backend.master_state import MasterState
from backend.node_metadata import NODE_METADATA, content_sha256
from backend.flow_behaviors import flow_provenance
from tests.flow_claim_scenarios import SCENARIOS

ROOT=Path(__file__).parents[1]
RECEIPT=ROOT/'docs/audits/family_two_records_2026_10_31/claims.json'


def source_hashes():
    import hashlib
    paths={'tests/test_flow_claims.py','tests/flow_claim_scenarios.py','tests/flow_engine_scenarios.py',
           'tests/test_merge_arrival_runtime.py','tests/test_merge_plan_integration.py','tests/test_flow_startup_refusals.py',
           'tests/test_payload_plan_integration.py','tests/test_wait_until_reachability.py',
           'backend/flow_behaviors.py','backend/master_state.py','backend/supervisor.py',
           'backend/run_context.py','backend/wait_registry.py','backend/node_metadata.py',
           'backend/node_base.py','backend/node_errors.py','backend/memory_bank.py',
           'backend/nodes/merge_node.py','backend/nodes/wait_until_node.py','backend/nodes/branch_end_node.py'}
    return {p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sorted(paths)}


async def execute_scenario(row,tmp_path,monkeypatch):
    tmp_path.mkdir(parents=True,exist_ok=True)
    module=importlib.import_module(row['module']);function=getattr(module,row['function'])
    runs={};attempts=[]
    original_start=MasterState.start_workflow;original_record=MasterState._record_run
    async def start(master,*args,**kwargs):
        attempts.append(dict(explicit_plans=kwargs.get('merge_plans') is not None))
        try: return await original_start(master,*args,**kwargs)
        except ValueError as exc:
            attempts[-1]['refused']=type(exc).__name__
            raise
    def record(master,state):
        original_record(master,state)
        ctx=master.run_context
        if ctx is None:return
        nodes=master.workflow_map.get_all_node_data()
        handles={nid:f'{data["type"]}:{i}' for i,(nid,data) in enumerate(nodes.items())}
        outputs={}
        missing=object()
        for nid,data in nodes.items():
            if data['type'] not in ('merge_node','wait_until_node','branch_end_node'):continue
            value=master.memory_bank.read_transient(nid,'default',missing)
            outputs[handles[nid]]=dict(present=value is not missing,**({'value':deepcopy(value)} if value is not missing else {}))
        errors=master.error_handler.get_errors_for_run(ctx.run_id)
        runs[ctx.run_id]=dict(state=state,stopped=ctx.stop_requested,pass_number=1,
            outputs=outputs,completed=sorted(handles[n] for n in ctx.completed_nodes if n in handles),
            errors=[dict(node=handles.get(e.get('node_id')),code=e['code'],handled=e.get('handled',False)) for e in errors],
            groups_clean=not(ctx.branch_groups or ctx.merge_groups or ctx.merge_barriers))
    with monkeypatch.context() as patch:
        patch.setattr(MasterState,'start_workflow',start);patch.setattr(MasterState,'_record_run',record)
        params=deepcopy(row['params'])
        if 'tmp_path' in inspect.signature(function).parameters:params['tmp_path']=tmp_path
        await function(**params)
    assert attempts, 'A flow claim must attempt real coordinator execution'
    assert runs or all(a.get('refused') for a in attempts)
    assert all(run['groups_clean'] for run in runs.values())
    return dict(claim=row['claim'],assertions=row['module']+'::'+row['function'],params=row['params'],
                status='pass',start_attempts=attempts,runs=list(runs.values()))


@pytest.mark.asyncio
@pytest.mark.parametrize('row',SCENARIOS,ids=lambda r:r['id'])
async def test_real_engine_flow_claim(row,tmp_path,monkeypatch):
    await execute_scenario(row,tmp_path,monkeypatch)


@pytest.mark.asyncio
async def test_flow_claims_receipt(tmp_path,monkeypatch):
    observations=[]
    for i,row in enumerate(SCENARIOS):
        observations.append(await execute_scenario(row,tmp_path/str(i),monkeypatch))
    payload=dict(schema_version=1,base_revision='58a22999f38ba03cca443fd4aff980d749ce838d',
        provenance=flow_provenance(),sources=source_hashes(),
        records={k:content_sha256(NODE_METADATA[k]) for k in ('merge_node','wait_until_node','branch_end_node')},
        scenario_count=len(SCENARIOS),observations=observations,
        interpretation='Each source-bound assertion executed through real MasterState/RunService; no coordinator callback fakes. Export is observations, not admission or independent human review.')
    if os.getenv('AOTN_FLOW_CLAIMS_REPORT'):
        Path(os.environ['AOTN_FLOW_CLAIMS_REPORT']).write_text(json.dumps(payload,ensure_ascii=False,indent=2).replace(str(tmp_path),'$ROOT')+'\n')
    assert len(observations)==len(SCENARIOS)


def test_flow_receipt_is_current():
    receipt=json.loads(RECEIPT.read_text())
    assert receipt['sources']==source_hashes()
    assert receipt['provenance']==flow_provenance()
    assert receipt['scenario_count']==len(SCENARIOS)
    assert receipt['records']=={k:content_sha256(NODE_METADATA[k]) for k in receipt['records']}
    assert all(row['status']=='pass' for row in receipt['observations'])

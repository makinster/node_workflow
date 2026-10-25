"""The engine's per-visit snapshot: cached, immutable and scoped to this run."""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import pytest
from backend import error_handler as errors_module
from backend.error_handler import ErrorHandler
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import Node
from backend.node_factory import NodeFactory
from backend.supervisor import Supervisor
from backend.workflow_map import WorkflowMap


def test_cached_projection_no_disk_and_immutable(monkeypatch):
    handler=ErrorHandler(EventBus())
    monkeypatch.setattr(errors_module,'save_json_record',lambda *_:None)
    handler._errors_by_run.update(this=[],other=[])
    for i in range(7):
        handler.log_error(ValueError(f'message{i}'),dict(run_id='this',node_id=f'N{i}',node_alias=f'Node {i}',
            branch_id=f'S{i%2}',inputs='NEVER INCLUDED',details='RAW'),code='test_failed',handled=i%2==0)
    handler.log_error(ValueError('OTHER RUN'),dict(run_id='other'),code='private')
    def refuse(*_):raise AssertionError('snapshot must not read disk')
    monkeypatch.setattr(errors_module,'load_json_record',refuse)
    snapshot=handler.snapshot('this','2026-10-25T01:02:03Z')
    assert len(snapshot.errors)==5 and snapshot.older_errors==2
    assert [e.node_name for e in snapshot.errors]==[f'Node {i}' for i in range(2,7)]
    assert snapshot.errors[0].handled and snapshot.errors[0].code=='test_failed'
    assert 'RAW' not in repr(snapshot) and 'OTHER RUN' not in repr(snapshot)
    with pytest.raises(FrozenInstanceError):snapshot.started_at='changed'
    with pytest.raises(FrozenInstanceError):snapshot.errors[0].message='changed'
    handler.log_error(ValueError('later'),dict(run_id='this'))
    assert snapshot.errors[-1].message=='message6'
    assert handler.snapshot('empty','start').errors==()
    handler.finalize_run('this')
    assert handler.snapshot('this','start').errors==()


@pytest.mark.asyncio
async def test_supervisor_supplies_same_run_snapshot_to_each_visit(monkeypatch):
    bus=EventBus();handler=ErrorHandler(bus);factory=NodeFactory();wm=WorkflowMap(factory,bus)
    wm.create_new('Snapshot workflow');nid=wm.add_node('no_op_node')
    snapshots=[]
    class Capture(Node):
        async def execute(self,context):
            snapshots.append(context.run_snapshot)
            context.signal_done({'data':{}})
    supervisor=Supervisor(run_id='this',branch_id='S1',depth=0,start_node_id=nid,workflow_map=wm,
        memory_bank=MemoryBank(bus),event_bus=bus,error_handler=handler,run_started_at='2026-10-25T01:02:03Z')
    supervisor.current_node_id=nid
    handler._errors_by_run['this']=[]
    await supervisor._execute_node(Capture(nid),{})
    monkeypatch.setattr(errors_module,'save_json_record',lambda *_:None)
    handler.log_error(ValueError('from another branch'),dict(run_id='this',branch_id='S2'))
    await supervisor._execute_node(Capture(nid),{})
    assert snapshots[0].started_at=='2026-10-25T01:02:03Z' and snapshots[0].errors==()
    assert snapshots[1].errors[0].message=='from another branch'


@pytest.mark.asyncio
async def test_real_run_start_supplied_without_frontend(tmp_path,monkeypatch):
    from backend.run_service import RunService
    from backend import output_manager,run_history
    for module,field in ((errors_module,'RUN_ERRORS_DIR'),(output_manager,'RUN_OUTPUTS_DIR'),(run_history,'RUN_HISTORY_DIR')):
        monkeypatch.setattr(module,field,tmp_path/field)
    service=RunService.create()
    try:
        captured=[]
        class Capture(Node):
            node_type='snapshot_probe'
            display_name='Snapshot probe'
            primary_family='Utility'
            category='debug'
            input_ports=['input']
            async def execute(self,context):
                captured.append((context.workflow_name,context.run_snapshot))
                context.signal_done({'data':{'default':'ok'}})
        service._factory._node_registry['snapshot_probe']=Capture
        wm=service.workflow_map;wm.create_new('Snapshot real run')
        start=wm.add_node('start_node');probe=wm.add_node('snapshot_probe');end=wm.add_node('end_node')
        wm.connect(start,'default',probe,'input');wm.connect(probe,'default',end,'input')
        await service.start();result=await service.wait()
        assert result.exit_code==0
        assert captured[0][0]=='Snapshot real run'
        from datetime import datetime
        assert datetime.fromisoformat(captured[0][1].started_at).tzinfo is not None
        assert captured[0][1].errors==()
    finally:service.close()


def test_unpublished_input_is_distinct_from_explicit_null():
    bus=EventBus();factory=NodeFactory();wm=WorkflowMap(factory,bus);wm.create_new('Presence')
    source=wm.add_node('start_node');target=wm.add_node('no_op_node')
    wm.connect(source,'default',target,'input')
    memory=MemoryBank(bus)
    supervisor=Supervisor(run_id='run',branch_id='S1',depth=0,start_node_id=source,
        workflow_map=wm,memory_bank=memory,event_bus=bus)
    supervisor.current_node_id=target
    node=factory.create_node('no_op_node',target)
    assert supervisor._prepare_inputs(node)=={}
    memory.store_transient(source,'default',None)
    assert supervisor._prepare_inputs(node)=={'input':None}

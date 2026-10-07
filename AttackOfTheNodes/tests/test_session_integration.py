"""Regression checks for defects found while integrating the audited branches."""
import asyncio
from collections import deque
from copy import deepcopy
from pathlib import Path
import threading
from types import SimpleNamespace
import pytest
from textual.app import App
from textual.widgets import Input
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.run_session import RunSession
from backend.validator import validate_workflow
from backend.window_manager import WindowsWindowManager, FakeWindowManager
from backend.workflow_map import WorkflowMap
from frontend.app import AttackOfTheNodesApp
from frontend.execution_state import ExecutionDisplayState
from frontend.screens.node_config import NodeConfigScreen
from tests.generated.test_file_output_node import _make_node, _make_context

def test_ambiguous_discovery_never_registers_arbitrary_window():
    manager=WindowsWindowManager.__new__(WindowsWindowManager)
    manager._snapshot_windows=lambda: {101,202}
    manager._match_by_title=lambda *args: None
    assert manager._discover_window('/tmp/report.txt',set()) is None

def test_title_discovery_requires_unique_match():
    manager=WindowsWindowManager.__new__(WindowsWindowManager)
    manager._win32=(SimpleNamespace(GetWindowText=lambda hwnd:'report.txt - Editor'),None,None)
    assert manager._match_by_title({101,202},'report.txt','report') is None
    assert manager._match_by_title({101},'report.txt','report') == 101

async def test_slow_window_launch_keeps_event_loop_responsive(tmp_path):
    started=threading.Event(); release=threading.Event()
    class SlowManager(FakeWindowManager):
        def open_path(self,*args):
            started.set()
            assert release.wait(2), 'event loop did not release the adapter'
            return super().open_path(*args)
    session=RunSession('run'); session.register_resource('window_manager',SlowManager())
    node=_make_node({'content_source':'Configured','content':'written','file_path':str(tmp_path/'report.txt'),'open_after_write':True})
    context,done,errors=_make_context(run_session=session)
    task=asyncio.create_task(node.execute(context))
    try:
        for _ in range(100):
            if started.is_set(): break
            await asyncio.sleep(.01)
        assert started.is_set() and not task.done()
        release.set(); await task
        assert done and not errors
    finally:
        release.set(); await asyncio.gather(task,return_exceptions=True); session.close_all()

def test_new_write_destination_does_not_warn_as_missing_input(tmp_path):
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('writer')
    start=wm.add_node('start_node');writer=wm.add_node('file_output_node');wm.connect(start,'default',writer,'content')
    cfg=factory.create_config_template('file_output_node');cfg.update(file_path=str(tmp_path/'new.txt'));wm.update_node_config(writer,cfg)
    assert not any('not found at validation time' in w['message'] for w in validate_workflow(wm,factory)['warnings'])
    cfg['file_path']='';wm.update_node_config(writer,cfg)
    assert any('Missing file path' in e['message'] for e in validate_workflow(wm,factory)['errors'])

def test_viewer_requests_are_fifo_wait_for_input_and_reject_other_runs():
    state=ExecutionDisplayState();state.reset('run');shown=[]
    app=SimpleNamespace(execution_state=state,_file_view_requests=deque(),_file_viewer_open=False,_user_input_modal_open=True,_error_modal_open=False,push_screen=lambda screen,cb:shown.append((screen.path,cb)))
    app._show_next_file_viewer=lambda:AttackOfTheNodesApp._show_next_file_viewer(app)
    app._on_file_viewer_closed=lambda result=None:AttackOfTheNodesApp._on_file_viewer_closed(app,result)
    for run,path in [('run','a.txt'),('old','ignore.txt'),('run','b.txt')]:
        AttackOfTheNodesApp._on_file_view_requested(app,{'run_id':run,'path':path})
    assert not shown and len(app._file_view_requests)==2
    app._user_input_modal_open=False;app._show_next_file_viewer();assert [p for p,_ in shown]==['a.txt']
    shown[0][1](None);assert [p for p,_ in shown]==['a.txt','b.txt']
    shown[1][1](None);assert not app._file_viewer_open and not app._file_view_requests

class ConfigHarness(App):
    CSS_PATH=str(Path(__file__).resolve().parents[1]/'frontend/styles.tcss')
    def __init__(self,screen,result):
        super().__init__();self.target=screen;self.result=result
    def on_mount(self):self.push_screen(self.target,self.result.append)

@pytest.mark.parametrize('width',[60,100,140])
@pytest.mark.parametrize('typ,field,tab',[('wait_until_node','timeout_seconds',1),('chat_completion_node','temperature',2),('file_output_node','file_path',2)])
async def test_fields_fit_and_save_preserves_unrelated_config(width,typ,field,tab):
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('layout');nid=wm.add_node(typ)
    cfg=factory.create_config_template(typ);cfg['extension_data']={'keep':[1,2]};wm.update_node_config(nid,cfg);original=deepcopy(wm.get_node_data(nid))
    results=[];screen=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid))
    async with ConfigHarness(screen,results).run_test(size=(width,24)) as pilot:
        await pilot.pause();screen.action_jump_config_tab(tab);await pilot.pause()
        widget=screen.query_one('#field-'+field,Input);screen.app.set_focus(widget);screen._scroll_config_widget_into_view(widget);await pilot.pause()
        assert widget.region.width>=8
        assert 0<=widget.region.x<widget.region.right<=width
        screen.action_save();await pilot.pause()
    assert results[0]['config']['extension_data']=={'keep':[1,2]}
    assert wm.get_node_data(nid)==original

async def test_parallel_writer_is_visible_to_explicit_vault_reader_after_wait(tmp_path):
    from backend.events import FILE_VIEW_REQUESTED
    from tests.test_debug_nodes import _make_services
    master,wm,memory,bus=_make_services();wm.create_new('parallel_files')
    start,fork,writer,wait,viewer=[wm.add_node(t) for t in
        ('start_node','branch_node','file_output_node','wait_until_node','file_view_node')]
    cfg=wm._factory.create_config_template('file_output_node')
    cfg.update(content_source='Configured',content='completed report',
               file_path=str(tmp_path/'report.md'),vault_write=True,vault_write_key='report_file')
    wm.update_node_config(writer,cfg)
    wm.update_node_config(wait,{'target_node_ids':[writer],'timeout_seconds':0})
    cfg=wm._factory.create_config_template('file_view_node')
    cfg.update(file_source='Vault',file_vault_key='report_file');wm.update_node_config(viewer,cfg)
    for source,port,target,target_port in [(start,'default',fork,'input'),
            (fork,'path_a',writer,'content'),(fork,'path_b',wait,'input'),
            (wait,'default',viewer,'file')]:
        wm.connect(source,port,target,target_port)
    requests=[];bus.subscribe(FILE_VIEW_REQUESTED,requests.append)
    try:
        await master.start_workflow();await asyncio.wait_for(master.wait_for_completion(),3)
        assert master.state.value=='FINISHED'
        ref=memory.read_persistent('report_file')
        assert Path(ref['path']).read_text()=='completed report'
        assert len(requests)==1 and requests[0]['ref_key']==ref['ref_key']
        assert requests[0]['run_id']==master.current_run_id
        assert memory.read_transient(wait,'default')!=ref
        assert memory.read_transient(viewer,'default')==ref
    finally:
        master.stop();await asyncio.wait_for(master.wait_for_completion(),3)

"""Run uses the editor's shared checker and issue panel before screen switching."""
import pytest

from backend.validator import validate_workflow
from frontend.app import AttackOfTheNodesApp
from frontend.screens.editor import EditorScreen
from frontend.screens.execution import ExecutionScreen
from frontend.widgets.validation_panel import ValidationPanel
from tests.test_merge_arrival_runtime import Engine
from tests.test_flow_startup_refusals import refused_workflow


@pytest.mark.asyncio
@pytest.mark.parametrize('problem', ['tombstone', 'two_starts', 'flow'])
async def test_run_refuses_errors_in_editor_and_can_run_after_repair(problem):
    if problem == 'flow':
        e, _ = refused_workflow('escape', 'no')
        bad = None
        phrase = 'leads away'
    else:
        e = Engine()
        bad = e.add('tombstone_node' if problem == 'tombstone' else 'start_node')
        phrase = 'Deleted node stub' if problem == 'tombstone' else 'expected exactly 1'
    app = AttackOfTheNodesApp(e.bus, e.factory, e.wm, e.memory, e.master)
    async with app.run_test(size=(110, 42)) as pilot:
        editor = app.screen
        await pilot.press('ctrl+r'); await pilot.pause(0.2)
        assert app.screen is editor and isinstance(editor, EditorScreen)
        panel = editor.query_one(ValidationPanel)
        assert panel.display and panel.region.width > 0
        assert any(issue['level'] == 'error' and phrase in issue['message'] for issue in panel.issues)
        assert not e.master.current_run_id and not e.registered and not e.events
        assert not e.master._supervisor_tasks
        # Repair the real graph, then use Run again without leaving this app.
        if problem == 'flow':
            choice = next(n for n,d in e.wm.get_all_node_data().items() if d['type']=='conditional_node')
            merge = next(n for n,d in e.wm.get_all_node_data().items() if d['type']=='merge_node')
            edge = next(c for c in e.wm.get_node_data(choice)['connections']['outputs'] if c['source_port']=='false')
            e.wm.disconnect(choice, 'false', edge['target_node_id'], edge['target_port'])
            e.wire(choice, merge, 'false', 'path_b')
        else:
            e.wm.delete_node(bad)
        await pilot.press('ctrl+r'); await pilot.pause(0.2)
        await e.finish()
        assert isinstance(app.screen, ExecutionScreen)
        assert e.master.current_run_id and not e.errors()


@pytest.mark.asyncio
async def test_warnings_do_not_block_run():
    e = Engine()
    show = e.add('text_output_node', label='', template='{input}')
    end = e.add('end_node', record_line=False)
    e.wire(e.start, show); e.wire(show, end)
    e.add('no_op_node')  # Unreachable warning only.
    result = validate_workflow(e.wm, e.factory)
    assert not result['errors'] and result['warnings']
    app = AttackOfTheNodesApp(e.bus, e.factory, e.wm, e.memory, e.master)
    async with app.run_test(size=(110,42)) as pilot:
        await pilot.press('ctrl+r'); await pilot.pause(0.2)
        await e.finish()
        assert isinstance(app.screen, ExecutionScreen)
        assert e.master.run_outputs == ['seed'] and not e.errors()


@pytest.mark.asyncio
@pytest.mark.parametrize('writer_kind', ['start_node','set_variable_node','concat_node'])
async def test_vault_value_written_during_run_is_not_blocked(writer_kind):
    e = Engine()
    if writer_kind == 'start_node':
        e.wm.update_node_config(e.start, {'greeting':'seed','vault_write':True,'vault_write_key':'later'})
        writer = e.start
    else:
        config = {'variable_name':'later','value_source':'input'} if writer_kind=='set_variable_node' else {'template':'{input}','vault_write':True,'vault_write_key':'later'}
        writer = e.add(writer_kind, **config)
        e.wire(e.start, writer)
    show = e.add('text_output_node', label='', input_source='Vault', input_vault_key='later')
    end = e.add('end_node', record_line=False)
    e.wire(writer, show); e.wire(show, end)
    assert e.memory.read_persistent('later') is None
    assert not validate_workflow(e.wm,e.factory)['errors']
    app = AttackOfTheNodesApp(e.bus,e.factory,e.wm,e.memory,e.master)
    async with app.run_test(size=(110,42)) as pilot:
        await pilot.press('ctrl+r'); await pilot.pause(0.2); await e.finish()
        assert isinstance(app.screen,ExecutionScreen)
        assert e.master.run_outputs==['seed'] and not e.errors()


@pytest.mark.asyncio
@pytest.mark.parametrize('source',['Upstream payload','Vault','Configured'])
async def test_file_created_during_run_is_not_blocked(tmp_path,source):
    e=Engine(); path=tmp_path/'created_during_run.txt'
    writer=e.add('file_output_node',file_path=str(path),write_mode='Overwrite',
                 vault_write=True,vault_write_key='created_file')
    reader=e.add('file_reader_node',input_source=source,input_vault_key='created_file',
                 file_path=str(path) if source=='Configured' else '')
    show=e.add('text_output_node',label='');end=e.add('end_node',record_line=False)
    e.wire(e.start,writer,slot="content");e.wire(writer,reader);e.wire(reader,show);e.wire(show,end)
    assert not path.exists()
    result=validate_workflow(e.wm,e.factory)
    assert not result['errors'],result['errors']
    if source=='Configured':assert 'file_not_found' in {w['code'] for w in result['warnings']}
    app=AttackOfTheNodesApp(e.bus,e.factory,e.wm,e.memory,e.master)
    async with app.run_test(size=(110,42)) as pilot:
        await pilot.press('ctrl+r');await pilot.pause(0.2);await e.finish()
        assert path.read_text()=='seed' and e.master.run_outputs==['seed']
        assert not e.errors() and isinstance(app.screen,ExecutionScreen)


@pytest.mark.asyncio
async def test_normal_starter_validates_and_runs():
    e=Engine();e.wm.close_workflow(e.wm.workflow_id)
    # Use the app's actual fresh-session initializer rather than a separate recipe.
    app=AttackOfTheNodesApp(e.bus,e.factory,e.wm,e.memory,e.master)
    async with app.run_test(size=(110,42)) as pilot:
        assert len(e.wm.get_all_node_data())==1
        result=validate_workflow(e.wm,e.factory)
        assert not result['errors']
        await pilot.press('ctrl+r');await pilot.pause(0.2);await e.finish()
        assert e.master.current_run_id and not e.errors()


@pytest.mark.asyncio
async def test_invalid_rerun_returns_from_execution_to_editor():
    e=Engine()
    app=AttackOfTheNodesApp(e.bus,e.factory,e.wm,e.memory,e.master)
    async with app.run_test(size=(110,42)) as pilot:
        await pilot.press('ctrl+r');await pilot.pause(0.2);await e.finish()
        assert isinstance(app.screen,ExecutionScreen)
        previous=e.master.current_run_id
        e.add('tombstone_node')
        await pilot.press('ctrl+r');await pilot.pause(0.2)
        assert isinstance(app.screen,EditorScreen)
        panel=app.screen.query_one(ValidationPanel)
        assert panel.display and any('Deleted node stub' in issue['message'] for issue in panel.issues)
        assert e.master.current_run_id==previous and not e.master._supervisor_tasks

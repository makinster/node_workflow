"""Stash insertion belongs to its focused text field, never a stale neighbour."""
from copy import deepcopy
import pytest
from textual.widgets import Select, Button
from frontend.screens.stash import StashScreen
from frontend.screens.confirm import ConfirmScreen
from frontend.widgets.command_input import CommandInput
from frontend.widgets.long_text import LongTextPreview
from frontend.widgets.local_model_picker import LocalModelPicker
from tests.test_stash_insert import stash, _config_app
from tests.test_local_model_picker import discovery, server, Config, settled, Options


async def complete_old_insert_if_open(app,pilot):
    # On the broken revision this follows the real damaging path all the way
    # through the Stash selection and Replace confirmation.
    if isinstance(app.screen,StashScreen):
        await pilot.press('enter');await pilot.pause()
    if isinstance(app.screen,ConfirmScreen):
        app.screen.query_one('#confirm-yes',Button).press();await pilot.pause()


@pytest.mark.asyncio
@pytest.mark.parametrize('size', [(80, 24)])
@pytest.mark.parametrize('listing',[True,False])
async def test_model_override_stash_does_not_replace_question(stash,discovery,monkeypatch,size,listing):
    if not listing:discovery.statuses['/api/tags']=503
    stash.add_text('stashed-value',name='sample')
    shown=[];monkeypatch.setattr('frontend.notifications.notify_info',lambda app,message:shown.append(message))
    app,open_config=_config_app(stash,'ask_local_model_node',{'input':'Keep this question','context_source':'Not used'})
    app.configuration_manager=Config(discovery.url)
    async with app.run_test(size=size) as pilot:
        screen=await open_config(pilot);await pilot.press('2');await pilot.pause()
        await settled(pilot,screen.query_one(LocalModelPicker))
        question=screen.query_one('#field-input',LongTextPreview)
        question.focus();await pilot.press('s');await pilot.pause()
        assert app.focused is screen.query_one(LocalModelPicker).query_one(Select if listing else CommandInput)
        before=deepcopy(screen._get_form_values())
        await pilot.press('p');await pilot.pause()
        await complete_old_insert_if_open(app,pilot)
        assert screen._get_form_values()==before
        assert shown[-1]=="Stash text can't go into this field"
        assert app.screen is screen


@pytest.mark.asyncio
async def test_focusing_an_unrelated_control_clears_the_previous_stash_target(stash,monkeypatch):
    stash.add_text('unwanted',name='sample')
    shown=[];monkeypatch.setattr('frontend.notifications.notify_info',lambda app,message:shown.append(message))
    app,open_config=_config_app(stash,'ask_local_model_node',{'input':'Keep me'})
    async with app.run_test() as pilot:
        screen=await open_config(pilot);await pilot.press('2');await pilot.pause()
        screen.query_one('#field-input').focus();await pilot.pause()
        screen.query_one('#alias-input').focus();await pilot.pause()
        before=deepcopy(screen._get_form_values())
        await pilot.press('p');await pilot.pause();await complete_old_insert_if_open(app,pilot)
        assert screen._get_form_values()==before
        assert shown[-1]=="Stash text can't go into this field"


@pytest.mark.asyncio
async def test_all_declared_select_fields_refuse_without_editing_any_neighbour(monkeypatch):
    """Every declared picker uses the real renderer and exact dispatch guard.

    Exhaustive metadata coverage does not require mounting a 200-field form.
    The mounted test below exercises keyboard dispatch for each widget kind.
    """
    from types import SimpleNamespace
    from backend.node_factory import NodeFactory
    from backend.field_types import stash_insert_target
    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.form_generator import _widget_for_field

    def fields(schema, prefix=''):
        for name, info in schema.items():
            yield prefix + name, info
            if info.get('item_schema'):
                yield from fields(info['item_schema'], prefix + name + '__')

    shown = []
    monkeypatch.setattr('frontend.notifications.notify_info', lambda app, message: shown.append(message))
    from textual.app import App
    async with App().run_test():
        protected = CommandInput('Keep neighbour', id='field-protected')
        def forbidden(*args, **kwargs):
            raise AssertionError('A selector must not open Stash')
        host = SimpleNamespace(app=SimpleNamespace(action_stash=forbidden), node_data={'type': 'fixture'})
        host._focused_stash_widget = lambda focused: NodeConfigScreen._focused_stash_widget(host, focused)
        count = 0
        for meta in NodeFactory().get_node_types_metadata():
            for name, info in fields(meta['config_schema']):
                if not (info.get('options') or info.get('type') == 'select' or info.get('secret') or info.get('vault_type') or info.get('presentation') == 'local_model'):
                    continue
                if info.get('type') in ('object_list', 'multiselect', 'boolean'):
                    continue
                key = meta['type'] + '__' + name
                schema = {key: info, 'protected': {'type': 'string'}}
                options = info.get('options') or []
                value = (options[0][1] if isinstance(options[0], (list, tuple)) else options[0]) if options else ''
                widget = _widget_for_field(key, info.get('type', 'string'), info, value,
                    secret_key_options=[('stored-key', 'stored-key')],
                    vault_keys_by_type={str(info.get('vault_type')): [('value', 'value')]})
                assert isinstance(widget, (Select, LocalModelPicker)), key
                assert stash_insert_target(schema, key) is None, key
                host.factory = SimpleNamespace(metadata_for_type=lambda _: {'config_schema': schema})
                host.focused = protected  # establish a previously edited neighbour
                host.focused = widget
                before = protected.value, getattr(widget, 'value', None)
                NodeConfigScreen.action_stash_insert(host)
                assert (protected.value, getattr(widget, 'value', None)) == before, key
                assert shown[-1] == "Stash text can't go into this field", key
                count += 1
        assert count > 50


@pytest.mark.asyncio
async def test_select_widget_kinds_refuse_stash_through_real_keyboard(monkeypatch):
    """One small production-style screen covers all rendered Select kinds."""
    from textual.app import App
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap
    from backend.event_bus import EventBus
    from frontend.screens.node_config import NodeConfigScreen
    from types import SimpleNamespace
    from pathlib import Path
    factory = NodeFactory()
    schema = {
        'protected': {'type': 'string', 'tab': 'Parameters'},
        'plain': {'type': 'select', 'options': ['one', 'two'], 'tab': 'Parameters'},
        'options': {'type': 'string', 'options': ['one', 'two'], 'tab': 'Parameters'},
        'secret': {'type': 'string', 'secret': True, 'tab': 'Parameters'},
        'vault': {'type': 'string', 'vault_type': 'string', 'tab': 'Parameters'},
    }
    factory.metadata_for_type('ask_local_model_node')['config_schema'] = schema
    wm = WorkflowMap(factory, EventBus()); wm.create_new('Select kinds')
    node = wm.add_node('ask_local_model_node')
    wm.update_node_config(node, {'protected': 'Keep neighbour', 'plain': 'one', 'options': 'one'})
    shown = []
    monkeypatch.setattr('frontend.notifications.notify_info', lambda app, message: shown.append(message))
    class Host(App):
        CSS_PATH = str(Path(__file__).parents[1] / 'frontend/styles.tcss')
        def on_mount(self):
            self.push_screen(NodeConfigScreen(factory, wm, node, wm.get_node_data(node),
                secrets_manager=SimpleNamespace(list_keys=lambda: ['stored-key'])))
        def action_stash(self, *args, **kwargs):
            raise AssertionError('A selector must not open Stash')
    app = Host()
    async with app.run_test(size=(100, 36)) as pilot:
        await pilot.press('2'); await pilot.pause(); screen = app.screen
        await screen.query_one('.generated-form').mount(Select([('Custom', 'custom')], value='custom', id='topology-source'))
        selects = list(screen.query(Select))
        assert {'field-plain', 'field-options', 'field-secret', 'field-vault', 'topology-source'} <= {s.id for s in selects}
        for selector in selects:
            screen.query_one('#field-protected').focus(); await pilot.pause()
            selector.focus(); await pilot.pause()
            assert app.focused is selector
            before = deepcopy(screen._get_form_values()); dirty = screen._is_dirty()
            await pilot.press('p'); await pilot.pause()
            assert screen._get_form_values() == before and screen._is_dirty() == dirty
            assert shown[-1] == "Stash text can't go into this field"
        selector = screen.query_one('#field-plain', Select)
        selector.focus(); selector.expanded = True; await pilot.pause()
        before = deepcopy(screen._get_form_values()); dirty = screen._is_dirty(); count = len(shown)
        await pilot.press('p'); await pilot.pause()
        assert screen._get_form_values() == before and screen._is_dirty() == dirty
        assert len(shown) > count
        selector.expanded = False; await pilot.pause()
        screen.query_one('#stash-insert-node-config').press(); await pilot.pause()
        assert screen._get_form_values() == before and screen._is_dirty() == dirty


@pytest.mark.asyncio
async def test_options_selects_refuse_stash_without_changing_settings(discovery,monkeypatch):
    shown=[];monkeypatch.setattr('frontend.notifications.notify_info',lambda app,message:shown.append(message))
    app=Options(Config(discovery.url))
    async with app.run_test(size=(80,24)) as pilot:
        picker=app.screen.query_one(LocalModelPicker);await settled(pilot,picker)
        def values():return {w.id:w.value for w in app.screen.query(CommandInput)}|{'model':picker.value}
        for select in app.screen.query(Select):
            app.screen.query_one('#setting-local_model_server_url').focus();await pilot.pause()
            select.focus();await pilot.pause();before=values()
            await pilot.press('p');await pilot.pause()
            assert values()==before
            assert shown[-1]=="Stash text can't go into this field"
            select.expanded=True;await pilot.pause()
            await pilot.press('p');await pilot.pause()
            assert values()==before
            assert shown[-1]=="Stash text can't go into this field"
            select.expanded=False


@pytest.mark.asyncio
async def test_stash_edits_only_the_field_that_requested_it(stash):
    stash.add_text('inserted',name='sample')
    app,open_config=_config_app(stash,'ask_local_model_node',{'input':'Keep question','context_source':'Configured','context':'Keep context'})
    async with app.run_test() as pilot:
        screen=await open_config(pilot);await pilot.press('2');await pilot.pause()
        for name,other in [('input','context'),('context','input')]:
            target=screen.query_one('#field-'+name,LongTextPreview)
            before=screen.query_one('#field-'+other,LongTextPreview).value
            target.focus();await pilot.press('p');await pilot.pause()
            assert isinstance(app.screen,StashScreen)
            await complete_old_insert_if_open(app,pilot)
            assert target.value=='inserted'
            assert screen.query_one('#field-'+other,LongTextPreview).value==before


@pytest.mark.asyncio
async def test_a_delayed_stash_reply_cannot_edit_a_different_or_replaced_field(stash,monkeypatch):
    callbacks=[]
    app,open_config=_config_app(stash,'ask_local_model_node',{'input':'Keep question','context_source':'Configured','context':'Keep context'})
    monkeypatch.setattr(app,'action_stash',lambda *a,callback=None,**k:callbacks.append(callback))
    async with app.run_test() as pilot:
        screen=await open_config(pilot);await pilot.press('2');await pilot.pause()
        question=screen.query_one('#field-input');context=screen.query_one('#field-context')
        question.focus();await pilot.press('p');await pilot.pause()
        context.focus();await pilot.pause()
        before=deepcopy(screen._get_form_values())
        callbacks.pop()({'type':'string','name':'sample','value':'unwanted'})
        await pilot.pause()
        assert screen._get_form_values()==before


@pytest.mark.asyncio
async def test_options_stash_cannot_fall_through_to_a_node_behind_the_modal(stash,discovery,monkeypatch):
    from frontend.screens.settings import SettingsScreen
    shown=[];monkeypatch.setattr('frontend.notifications.notify_info',lambda app,message:shown.append(message))
    stash.add_text('unwanted',name='sample')
    app,open_config=_config_app(stash,'ask_local_model_node',{'input':'Keep question'})
    async with app.run_test() as pilot:
        node_screen=await open_config(pilot);await pilot.press('2');await pilot.pause()
        node_screen.query_one('#field-input').focus();await pilot.pause()
        before=deepcopy(node_screen._get_form_values())
        options=SettingsScreen(Config(discovery.url))
        app.push_screen(options);await pilot.pause()
        picker=options.query_one(LocalModelPicker);await settled(pilot,picker)
        picker.query_one(Select).focus();await pilot.press('p');await pilot.pause()
        assert app.screen is options
        assert node_screen._get_form_values()==before
        assert shown[-1]=="Stash text can't go into this field"


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['contract','context','subworkflow','subworkflow-result'])
async def test_row_editor_selects_and_neighbour_fields_cannot_receive_stash_text(kind,monkeypatch):
    from pathlib import Path
    from textual.app import App
    from frontend.widgets.contract_rows import ContractRowEditor, INPUT
    from frontend.widgets.context_items import ContextItemEditor
    from frontend.widgets.subworkflow_rows import SubworkflowInputEditor, SubworkflowPayloadEditor
    editors={
        'subworkflow-result':lambda:SubworkflowPayloadEditor(dict(name='answer',type='string'),None),
        'contract':lambda:ContractRowEditor(INPUT,dict(name='name',type='string',value='Keep default',to='Downstream'),[]),
        'context':lambda:ContextItemEditor(dict(id='item',label='Keep label',source='Configured text',text='Keep text'),[],[('value','value')]),
        'subworkflow':lambda:SubworkflowInputEditor(dict(name='who',type='string',required=False,value=''),dict(source='Stash',stash_entry='Keep binding')),
    }
    shown=[];monkeypatch.setattr('frontend.notifications.notify_info',lambda app,message:shown.append(message))
    calls=[]
    class Host(App):
        CSS_PATH=str(Path(__file__).parents[1]/'frontend/styles.tcss')
        def on_mount(self):self.push_screen(editors[kind]())
        def action_stash(self,*args,callback=None,**kwargs):
            calls.append(kwargs)
            if callback:callback(dict(type='string',name='picked',value='unwanted'))
    app=Host()
    async with app.run_test(size=(80,24)) as pilot:
        editor=app.screen
        def values():
            return {w.id:w.value for w in editor.query(CommandInput)}|{w.id:w.value for w in editor.query(LongTextPreview)}|{w.id:w.value for w in editor.query(Select)}
        for selector in editor.query(Select):
            # Context Pack's Vault key appears in its Vault source mode.
            if selector.id=='row-key':editor.query_one('#row-source',Select).value='Vault';await pilot.pause()
            selector.focus();await pilot.pause()
            assert app.focused is selector
            before=values();count=len(shown)
            await pilot.press('p');await pilot.pause();await complete_old_insert_if_open(app,pilot)
            assert not calls and values()==before
            assert len(shown)>count and shown[-1]=="Stash text can't go into this field"
            selector.expanded=True;await pilot.pause()
            count=len(shown);await pilot.press('p');await pilot.pause()
            assert not calls and values()==before
            assert len(shown)>count
            selector.expanded=False;await pilot.pause()
        # Typing into a neighbouring text field must not redirect P either.
        if kind in ('contract','context'):
            neighbour=editor.query_one('#row-name' if kind=='contract' else '#row-label')
            neighbour.focus();await pilot.pause();before=values()
            await pilot.press('p');await pilot.pause()
            assert not calls and values()==before


@pytest.mark.asyncio
async def test_subworkflow_binding_button_refuses_p_but_activates_its_own_picker(monkeypatch):
    from pathlib import Path
    from textual.app import App
    from frontend.widgets.subworkflow_rows import SubworkflowInputEditor
    class Host(App):
        CSS_PATH=str(Path(__file__).parents[1]/'frontend/styles.tcss')
        def on_mount(self):self.push_screen(SubworkflowInputEditor(dict(name='who',type='string',required=False,value=''),dict(source='Stash',stash_entry='old')))
        def action_stash(self,*a,callback=None,**k):callback(dict(name='picked',type='string',value='data'))
    app=Host()
    async with app.run_test() as pilot:
        editor=app.screen;binding=editor.query_one('#row-stash',Button)
        shown=[];monkeypatch.setattr('frontend.notifications.notify_info',lambda app,msg:shown.append(msg))
        binding.focus();await pilot.press('p');await pilot.pause()
        assert editor.stash_entry=='old'
        assert shown==["Stash text can't go into this field"]
        await pilot.press('enter');await pilot.pause()
        assert editor.stash_entry=='picked'
        assert editor.query_one('#row-source',Select).value=='Stash'
        assert editor.query_one('#row-value',CommandInput).value==''


@pytest.mark.asyncio
async def test_long_text_editor_stash_cannot_edit_from_a_button(monkeypatch):
    from pathlib import Path
    from textual.app import App
    from frontend.widgets.long_text import LongTextEditor
    from frontend.widgets.command_input import CommandTextArea
    shown=[];monkeypatch.setattr('frontend.notifications.notify_info',lambda app,message:shown.append(message))
    class Host(App):
        CSS_PATH=str(Path(__file__).parents[1]/'frontend/styles.tcss')
        def on_mount(self):self.push_screen(LongTextEditor('Keep text'))
        def action_stash(self,*a,**k):raise AssertionError('Unfocused area cannot open Stash')
    app=Host()
    async with app.run_test() as pilot:
        editor=app.screen;editor.query(Button).first().focus();await pilot.pause()
        editor.action_stash_insert();await pilot.pause()
        assert editor.query_one(CommandTextArea).text=='Keep text'
        assert shown[-1]=="Stash text can't go into this field"

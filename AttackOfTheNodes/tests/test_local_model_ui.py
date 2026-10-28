"""Production styles and real source pickers; no network or model execution."""
from copy import deepcopy
from pathlib import Path
import pytest
from textual.widgets import Checkbox, Select, Label
from backend.event_bus import EventBus
from backend.node_base import Node
from backend.node_factory import NodeFactory
from backend.nodes.ai.ask_local_model_node import AskLocalModelNode
from backend.workflow_map import WorkflowMap
from backend.integrations.local_model import TEXT_SOURCES
from backend.vault_declarations import typed_vault_writes
from frontend.widgets.command_input import CommandInput, CommandTextArea
from frontend.widgets.long_text import LongTextPreview, LongTextEditor
from tests.test_small_wins_ui import Host


class SecondaryTextProducer(Node):
    node_type='test_secondary_text_node'
    display_name='Secondary text producer'
    primary_family='Utility'
    input_ports=['input']
    output_ports=['default','secondary','record']
    output_port_metadata={
        'default':{'name':'Question','data_type':'string','to':['downstream','vault']},
        'secondary':{'name':'Context','data_type':'string','to':['downstream','vault']},
        'record':{'name':'Record','data_type':'var','to':['vault']}}
    default_config={'vault_write':False,'vault_write_key':'',
        'secondary_vault_write':True,'secondary_vault_key':'secondary_text',
        'record_vault_write':True,'record_vault_key':'incompatible_record'}
    async def execute(self,ctx):raise AssertionError('UI fixture must never run')


def make():
    factory=NodeFactory();factory._node_registry[SecondaryTextProducer.node_type]=SecondaryTextProducer;factory._metadata_by_type=None
    wm=WorkflowMap(factory,EventBus());wm.create_new('Local model source contract')
    start=wm.add_node('start_node');writer=wm.add_node(SecondaryTextProducer.node_type)
    node=wm.add_node('ask_local_model_node');later=wm.add_node('context_pack_node')
    wm.connect(start,'default',writer,'input');wm.connect(writer,'default',node,'input')
    wm.connect(writer,'secondary',node,'context');wm.connect(node,'default',later,'input')
    wm.update_node_config(node,{**wm.get_node_data(node)['config'],'input':'one\ntwo\nthree\nfour'})
    wm.update_node_config(later,{**wm.get_node_data(later)['config'],'vault_write':True,'vault_write_key':'downstream_text'})
    return factory,wm,node


@pytest.mark.asyncio
@pytest.mark.parametrize('size',[(80,24),(120,40)])
async def test_declared_accepted_and_ui_sources_match_including_secondary_vault(size):
    factory,wm,node=make();app=Host(factory,wm,node)
    before=deepcopy(wm.get_node_data(node)['config'])
    async with app.run_test(size=size) as pilot:
        await pilot.pause();screen=app.screen
        assert 'secondary_text' in screen._declared_vault_writer_keys()
        for port in ('input','context'):
            declared=set(AskLocalModelNode.input_port_metadata[port]['sources'])
            assert declared==set(TEXT_SOURCES.values())
            selector=screen.query_one(f'#field-{port}_source',Select)
            ui={value for _,value in selector._options}-{'Not used'}
            assert ui==set(TEXT_SOURCES), (port,selector._options)
            assert {TEXT_SOURCES[value] for value in ui}==declared
            selector.value='Vault';await pilot.pause()
            picker=screen.query_one(f'#field-{port}_vault_key',Select)
            offered={value for _,value in picker._options}
            assert 'secondary_text' in offered
            assert 'incompatible_record' not in offered and 'downstream_text' not in offered
            picker.value='secondary_text';await pilot.pause()
            values=screen._get_form_values()
            assert values[f'{port}_source']=='Vault' and values[f'{port}_vault_key']=='secondary_text'
            selector.value='Configured' if port=='input' else 'Not used';await pilot.pause()
        assert wm.get_node_data(node)['config']==before


@pytest.mark.asyncio
@pytest.mark.parametrize('size',[(80,24),(120,40)])
async def test_long_text_controls_save_cancel_and_reopen(size):
    factory,wm,node=make();app=Host(factory,wm,node)
    async with app.run_test(size=size) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause();screen=app.screen
        preview=screen.query_one('#field-input',LongTextPreview);preview.focus();await pilot.press('e');await pilot.pause()
        assert isinstance(app.screen,LongTextEditor)
        app.screen.query_one(CommandTextArea).text='Edited question\nWith facts'
        await pilot.press('ctrl+s');await pilot.pause();assert preview.value=='Edited question\nWith facts'
        for key,value in [('num_ctx','16384'),('temperature','0.4'),('max_tokens','96'),('context_limit','12000')]:
            field=screen.query_one(f'#field-{key}',CommandInput)
            assert field.display;field.value=value
        await pilot.press('3');await pilot.pause()
        assert screen.query_one('#dead-drop-passthrough',Checkbox).value is False
        assert screen.query_one('#vault-output-key-details',CommandInput)
        for key in ('#save-node-config','#cancel-node-config'):
            button=screen.query_one(key);assert button.region.height and button.region.bottom<=size[1]
        await screen.action_save_and_stay();await pilot.pause()
        saved=deepcopy(wm.get_node_data(node)['config'])
        assert saved['input']=='Edited question\nWith facts' and saved['num_ctx']==16384 and saved['max_tokens']==96
        assert saved['context_limit']==12000
    reopened=Host(factory,wm,node)
    async with reopened.run_test(size=size) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause()
        assert reopened.screen.query_one('#field-input',LongTextPreview).value==saved['input']
        assert reopened.screen.query_one('#field-context_limit',CommandInput).value=='12000'
        reopened.screen.query_one('#field-temperature',CommandInput).value='1.1'
        reopened.screen.action_cancel();await pilot.pause()
        assert wm.get_node_data(node)['config']==saved


@pytest.mark.asyncio
async def test_options_labels_and_save():
    from textual.app import App
    from backend.configuration_manager import DEFAULT_SETTINGS
    from frontend.screens.settings import SettingsScreen
    class Config:
        def get_all(self):return dict(DEFAULT_SETTINGS)
    received=[]
    class Options(App):
        CSS_PATH=str(Path(__file__).parents[1]/'frontend/styles.tcss')
        def on_mount(self):self.push_screen(SettingsScreen(Config()),received.append)
    app=Options()
    async with app.run_test(size=(100,36)) as pilot:
        await pilot.pause()
        labels=[str(label.render()) for label in app.screen.query(Label)]
        assert 'Local model server URL' in labels and 'Local default model' in labels
        assert 'Local model context limit (characters)' in labels
        limit=app.screen.query_one('#setting-local_model_context_limit', CommandInput)
        assert limit.value=='8000'
        for invalid in ['999','200001','1.5','words']:
            limit.value=invalid
            app.screen.action_save()
            assert not received and limit.value==invalid
        limit.value='12000'
        app.screen.query_one('#setting-local_model_default_model').query_one(CommandInput).value='chosen-local:latest'
        app.screen.action_save();await pilot.pause()
        assert received[0]['settings']['local_model_default_model']=='chosen-local:latest'
        assert received[0]['settings']['local_model_context_limit']==12000

@pytest.mark.asyncio
async def test_context_limit_override_blank_and_range_save():
    factory,wm,node=make();app=Host(factory,wm,node)
    async with app.run_test(size=(100,36)) as pilot:
        await pilot.pause();screen=app.screen
        field=screen.query_one('#field-context_limit',CommandInput)
        assert field.value==''
        before=deepcopy(wm.get_node_data(node)['config'])
        field.value='999'
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']==before
        assert field.value=='999'
        field.value='12000'
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['context_limit']==12000
        field.value=''
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['context_limit']==''

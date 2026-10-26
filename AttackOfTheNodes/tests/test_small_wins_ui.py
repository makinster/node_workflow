"""Real mounted forms/styles and keys, including the approved table regression."""
import asyncio
from copy import deepcopy
from pathlib import Path
import pytest
from textual.app import App
from frontend.keymap import APP, bindings_for
from frontend.keymap_runtime import KeymapScreenMixin
from textual.widgets import Button, Checkbox, Select, Static
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.command_input import CommandInput, CommandTextArea
from frontend.widgets.contract_rows import ContractRowsField
from frontend.widgets.form_generator import ObjectListField
from frontend.widgets.reply_fields import ReplyFields, ReplyFieldEditor
from frontend.widgets.long_text import LongTextPreview, LongTextEditor


def make(kind='check_reply_node',**config):
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('Small wins')
    start=wm.add_node('start_node');ask=wm.add_node('hermes_ask_node');node=wm.add_node(kind)
    wm.connect(start,'default',ask,'input');wm.connect(ask,'default',node,'input')
    wm.update_node_config(node,{**wm.get_node_data(node)['config'],**config})
    return factory,wm,node


class Host(KeymapScreenMixin, App):
    KEYMAP = APP
    BINDINGS = bindings_for(KEYMAP)
    CSS_PATH='../frontend/styles.tcss'
    def __init__(self,factory,wm,node):
        super().__init__();self.factory=factory;self.workflow_map=wm;self.node=node
    def on_mount(self):
        self.push_screen(NodeConfigScreen(self.factory,self.workflow_map,self.node,
                                          self.workflow_map.get_node_data(self.node),
                                          on_save=lambda result:self.workflow_map.update_node_config(self.node,result['config'])))
    def action_stash(self,*args,callback=None,**kwargs):
        if callback:callback({'name':'test','type':'string','value':'pasted'})


@pytest.mark.asyncio
@pytest.mark.parametrize('size',[(110,36),(80,24)])
async def test_compact_fields_table_and_keys_regression(size):
    factory,wm,node=make();app=Host(factory,wm,node)
    original=deepcopy(wm.get_node_data(node)['config'])
    async with app.run_test(size=size) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause()
        screen=app.screen;field=screen.query_one(ReplyFields)
        assert isinstance(field,ContractRowsField) and not screen.query(ObjectListField)
        assert not screen.query_one('#field-input').display
        buttons=list(field.query('.contract-row'))
        assert len(buttons)==3 and all(b.region.height==1 for b in buttons)
        assert buttons[-1].region.bottom<=size[1]-4
        assert field.region.height <= 12
        assert field.query_one('#field-expected_fields-add').region.y <= buttons[-1].region.bottom + 1
        assert screen.query_one('#save-node-config').region.bottom<=size[1]
        buttons[0].focus();await pilot.press('e');await pilot.pause()
        assert isinstance(app.screen,ReplyFieldEditor)
        app.screen.query_one('#row-name',CommandInput).value='report'
        await pilot.press('ctrl+s');await pilot.pause()
        assert field.rows[0]['name']=='report'
        assert app.focused.id=='field-expected_fields-row-0'
        await pilot.press('s','x');await pilot.pause()
        assert [r['name'] for r in field.rows]==['report','next_step']
        field.query_one('#field-expected_fields-add').focus();await pilot.press('enter');await pilot.pause()
        app.screen.query_one('#row-name',CommandInput).value='optional'
        app.screen.query_one('#row-required',Checkbox).value=False
        await pilot.press('ctrl+s');await pilot.pause()
        assert field.rows[-1]['name']=='optional' and not field.rows[-1]['required']
        # Cancel screen edits must not mutate the saved workflow.
        assert wm.get_node_data(node)['config']==original
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['expected_fields']==field.value
        assert wm.get_node_data(node)['config']['input_source']=='Upstream payload'


@pytest.mark.asyncio
async def test_row_cancel_and_invalid_setup():
    factory,wm,node=make();app=Host(factory,wm,node)
    async with app.run_test(size=(100,36)) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause()
        field=app.screen.query_one(ReplyFields)
        field.query_one('#field-expected_fields-row-0').focus();await pilot.press('enter');await pilot.pause()
        app.screen.query_one('#row-name',CommandInput).value='bad name'
        await pilot.press('ctrl+s');await pilot.pause()
        assert app.screen.query_one('#row-error').display
        await pilot.press('escape');await pilot.pause()
        assert field.rows[0]['name']=='summary'


@pytest.mark.asyncio
async def test_configured_preview_full_editor_save_cancel_and_stash():
    original='one\ntwo\nthree\nfour'
    factory,wm,node=make(input_source='Configured',input=original);app=Host(factory,wm,node)
    async with app.run_test(size=(80,24)) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause()
        screen=app.screen;preview=screen.query_one(LongTextPreview)
        assert '2 more lines' in str(preview.label) and preview.value==original
        preview.focus();await pilot.press('enter');await pilot.pause()
        assert isinstance(app.screen,LongTextEditor)
        area=app.screen.query_one(CommandTextArea)
        assert area.region.height>12 and area.editing
        await pilot.press('p');assert area.text == 'p' + original
        await pilot.press('escape','p');await pilot.pause()
        assert area.text == 'ppasted' + original
        await pilot.press('e','!','ctrl+s');await pilot.pause()
        assert preview.value == 'ppasted!' + original and app.focused is preview
        saved=preview.value
        await pilot.press('enter','x','escape','escape');await pilot.pause()
        assert app.screen.__class__.__name__=='ConfirmScreen'
        app.screen.action_confirm_yes();await pilot.pause()
        assert preview.value==saved
        preview.focus();await pilot.press('p');await pilot.pause()
        assert app.screen.__class__.__name__=='ConfirmScreen'
        app.screen.action_confirm_no();await pilot.pause()
        assert preview.value==saved
        preview.focus();await pilot.press('p');await pilot.pause();app.screen.action_confirm_yes();await pilot.pause()
        assert preview.value=='pasted'
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['input']=='pasted'


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['read_lines_node','find_lines_node','check_reply_node'])
async def test_routing_vault_preserved_and_save_reopen(kind):
    config={'vault_write':True,'vault_write_key':'own','dead_drop_passthrough':True}
    if kind=='find_lines_node':config.update(match_count_vault_write=True,match_count_vault_key='count')
    factory,wm,node=make(kind,**config);app=Host(factory,wm,node)
    async with app.run_test(size=(100,45)) as pilot:
        await pilot.pause();await pilot.press('3');await pilot.pause()
        screen=app.screen
        assert screen.query_one('#dead-drop-passthrough',Checkbox).value
        assert screen.query_one('#vault-output-key-default').value=='own'
        if kind=='find_lines_node':assert screen.query_one('#vault-output-key-match_count').value=='count'
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['vault_write_key']=='own'
        assert wm.get_node_data(node)['config']['dead_drop_passthrough']
        if kind=='find_lines_node':assert wm.get_node_data(node)['config']['match_count_vault_key']=='count'

    # A fresh screen reads the saved settings, including the independent count.
    reopened=Host(factory,wm,node)
    async with reopened.run_test(size=(100,45)) as pilot:
        await pilot.pause();await pilot.press('3');await pilot.pause()
        assert reopened.screen.query_one('#vault-output-key-default').value=='own'
        if kind=='find_lines_node':
            assert reopened.screen.query_one('#vault-output-key-match_count').value=='count'

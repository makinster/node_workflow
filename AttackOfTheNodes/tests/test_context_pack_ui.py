"""Real compact forms, keyboard editing, routing and shared solid selection."""
from copy import deepcopy
import pytest
from textual.widgets import Button, Checkbox, Select, Static
from backend.nodes.data.context_pack_node import ContextPackNode
from frontend.widgets.context_items import ContextItems, ContextItemEditor
from frontend.widgets.contract_rows import ContractRowsField
from frontend.widgets.command_input import CommandInput, CommandTextArea
from frontend.widgets.long_text import LongTextPreview, LongTextEditor
from tests.test_small_wins_ui import make, Host


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['start_node','check_reply_node','context_pack_node'])
async def test_shared_selection_uses_highlight_role_for_every_cell(kind,monkeypatch):
    from rich.color import Color
    from rich.style import Style
    from rich.text import Text
    from textual.geometry import Region
    from frontend import colors
    monkeypatch.delenv('NO_COLOR',raising=False)
    monkeypatch.setenv('TEXTUAL_COLOR_SYSTEM','truecolor')
    factory,wm,node=make(kind);app=Host(factory,wm,node)
    async with app.run_test(size=(100,36)) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause()
        row=app.screen.query('.contract-row').first()
        # A future coloured type cell/background must not punch through selection.
        row.label=Text.assemble(('Facts ',colors.NAME),
            ('[string]',Style(color=colors.TYPE,bgcolor=colors.ERROR)))
        row.focus();await pilot.pause()
        def painted():
            lines=row.render_lines(Region(0,0,row.region.width,row.region.height))
            return [segment for line in lines for segment in line if segment.text]
        for role in (colors.HIGHLIGHT,colors.MAP_BACKGROUND):
            # Read the live role after mounting; never freeze the import-time palette.
            monkeypatch.setattr(colors,'HIGHLIGHT',role)
            row.refresh();await pilot.pause()
            cells=painted()
            assert sum(len(cell.text) for cell in cells)==row.region.width
            assert all(cell.style.bgcolor==Color.parse(colors.HIGHLIGHT) for cell in cells)
            assert len({cell.style.color for cell in cells})==1
        app.screen.query_one('#save-node-config').focus();await pilot.pause()
        row.add_class('nav-highlight');await pilot.pause()
        assert all(cell.style.bgcolor==Color.parse(colors.HIGHLIGHT) for cell in painted())
        row.remove_class('nav-highlight');await pilot.pause()
        assert any(cell.style.color==Color.parse(colors.TYPE) for cell in painted())
        assert any(cell.style.bgcolor==Color.parse(colors.ERROR) for cell in painted())


@pytest.mark.asyncio
@pytest.mark.parametrize('size',[(100,36),(80,24)])
async def test_context_item_editor_preview_save_and_reopen(size):
    factory,wm,node=make('context_pack_node');app=Host(factory,wm,node)
    before=deepcopy(wm.get_node_data(node)['config'])
    async with app.run_test(size=size) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause()
        screen=app.screen;field=screen.query_one(ContextItems)
        hint=screen.query_one('#field-desc-max_total')
        assert hint.region.width<=size[0] and hint.region.height>=2
        assert str(hint.render()).endswith('The pack says what was trimmed.')
        assert len(field.rows)==1 and field.rows[0]['source']=='Upstream payload'
        field.query_one('.contract-row').focus();await pilot.press('enter');await pilot.pause()
        assert isinstance(app.screen,ContextItemEditor)
        editor=app.screen
        editor.query_one('#row-label',CommandInput).value='Service <text>'
        editor.query_one('#row-source',Select).value='Configured text';await pilot.pause()
        preview=editor.query_one(LongTextPreview)
        preview.focus();await pilot.press('enter');await pilot.pause()
        assert isinstance(app.screen,LongTextEditor)
        assert app.screen.field_title == 'Context Pack › Service <text> › Text'
        app.screen.query_one(CommandTextArea).text='first\nsecond\nthird'
        await pilot.press('ctrl+s');await pilot.pause()
        assert preview.value=='first\nsecond\nthird' and app.focused is preview
        assert editor.query_one('#confirm-row').region.height>0
        assert editor.query_one('#confirm-row').region.bottom<=size[1]
        assert editor.query_one('.modal-title').region.y>=0
        await pilot.press('ctrl+s');await pilot.pause()
        assert field.rows[0]['text']=='first\nsecond\nthird'
        assert field.rows[0]['label']=='Service <text>'
        field.query_one('#field-items-add').focus();await pilot.press('enter');await pilot.pause()
        app.screen.query_one('#row-label',CommandInput).value='Other'
        await pilot.press('ctrl+s');await pilot.pause()
        assert len(field.rows)==2
        field.query_one('#field-items-row-1').focus();await pilot.press('x');await pilot.pause()
        assert len(field.rows)==1
        assert wm.get_node_data(node)['config']==before
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['items']==field.value
    reopened=Host(factory,wm,node)
    async with reopened.run_test(size=size) as pilot:
        await pilot.pause();await pilot.press('2');await pilot.pause()
        assert reopened.screen.query_one(ContextItems).rows[0]['text']=='first\nsecond\nthird'


@pytest.mark.asyncio
async def test_context_pack_standard_forwarding_and_vault_ui():
    factory,wm,node=make('context_pack_node',vault_write=True,vault_write_key='safe_pack',dead_drop_passthrough=True)
    app=Host(factory,wm,node)
    async with app.run_test(size=(80,24)) as pilot:
        await pilot.pause();await pilot.press('3');await pilot.pause()
        screen=app.screen
        assert screen.query_one('#dead-drop-passthrough',Checkbox).value
        assert screen.query_one('#vault-output-key-default').value=='safe_pack'
        await screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['vault_write_key']=='safe_pack'
        assert wm.get_node_data(node)['config']['dead_drop_passthrough']


@pytest.mark.asyncio
async def test_ask_context_default_not_used_and_preview():
    factory,wm,node=make('hermes_ask_node');app=Host(factory,wm,node)
    async with app.run_test(size=(80,24)) as pilot:
        await pilot.pause()
        assert app.screen.query_one('#field-context_source',Select).value=='Not used'
        app.screen.query_one('#field-context_source',Select).value='Configured'
        await pilot.press('2');await pilot.pause()
        assert app.screen.query_one('#field-context',LongTextPreview).display
        await app.screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['context_source']=='Configured'

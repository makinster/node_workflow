"""Shared multiline fields: real forms, production styles, and keyboard actions."""
import pytest
from frontend.widgets.command_input import CommandTextArea
from frontend.widgets.form_generator import _widget_for_field
from frontend.widgets.long_text import LongTextPreview, LongTextEditor
from frontend.widgets.long_text_document import logical_text
from tests.test_small_wins_ui import Host, make


def test_all_multiline_fields_use_preview_without_opt_in():
    for kind in ('multiline', 'code'):
        widget = _widget_for_field('long', kind, {'type': kind}, 'full\ntext\n\n')
        assert isinstance(widget, LongTextPreview)
        assert widget.value == 'full\ntext\n\n'


@pytest.mark.asyncio
async def test_editor_save_preserves_mixed_line_endings_and_stays_in_node():
    original = 'é😀\r\ntwo\rthree\n\n'
    factory, wm, node = make(input_source='Configured', input=original)
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        screen = app.screen
        preview = screen.query_one(LongTextPreview)
        preview.focus(); await pilot.press('enter'); await pilot.pause()
        area = app.screen.query_one(CommandTextArea)
        assert area.cursor_location == (0, 0)
        assert app.screen.field_title == 'Check reply › Reply'
        assert area.text == logical_text(original)
        await pilot.press('p', 'ctrl+s'); await pilot.pause()
        assert app.screen is screen and app.focused is preview
        assert preview.value == 'p' + original
        assert wm.get_node_data(node)['config']['input'] == original


@pytest.mark.asyncio
@pytest.mark.parametrize('close', ['escape', 'ctrl+q'])
async def test_cancel_draft_safe_default_keep_discard_and_unchanged(close):
    factory, wm, node = make(input_source='Configured', input='original')
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        config = app.screen; preview = config.query_one(LongTextPreview)
        preview.focus(); await pilot.press('e'); await pilot.pause()
        editor = app.screen; area = editor.query_one(CommandTextArea)
        await pilot.press('p')
        if close == 'escape':
            await pilot.press('escape')
            assert app.screen is editor and not area.editing
        await pilot.press(close); await pilot.pause()
        assert app.screen.__class__.__name__ == 'ConfirmScreen'
        assert app.focused.id == 'confirm-no'
        from frontend.widgets.contract_rows import CompactRowButton
        assert isinstance(app.focused, CompactRowButton)
        await pilot.press('enter'); await pilot.pause()
        assert app.screen is editor and area.text == 'poriginal'
        await pilot.press(close); await pilot.pause()
        # Keep editing preserves the cursor/draft; choosing Discard restores field.
        await pilot.press('a', 'enter'); await pilot.pause()
        assert app.screen is config and app.focused is preview
        assert preview.value == 'original'
        await pilot.press('e'); await pilot.pause()
        if close == 'escape':
            await pilot.press('escape')
        await pilot.press(close); await pilot.pause()
        assert app.screen is config and app.focused is preview
        assert wm.get_node_data(node)['config']['input'] == 'original'


@pytest.mark.asyncio
async def test_keyboard_counts_stash_at_cursor_buttons_and_explicit_cancel():
    original = 'one\ntwo\n\n'
    factory, wm, node = make(input_source='Configured', input=original)
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        config = app.screen; preview = config.query_one(LongTextPreview)
        preview.focus(); await pilot.press('e'); await pilot.pause()
        editor = app.screen; area = editor.query_one(CommandTextArea)
        assert '4 lines' in str(editor.query_one('#long-text-counts').render())
        assert editor.query_one('#long-text-save').region.bottom < 24
        await pilot.press('right', 'p', 'escape', 'p'); await pilot.pause()
        assert area.text == 'oppastedne\ntwo\n\n'
        assert area.cursor_location == (0, 8)
        await pilot.press('e', '!')
        assert area.text == 'oppasted!ne\ntwo\n\n'
        assert 'Changed' in str(editor.query_one('#long-text-counts').render())
        await pilot.press('escape', 's', 'd', 'enter'); await pilot.pause()
        assert app.screen is config and preview.value == original
        assert app.focused is preview
        # Preview replacement is whole-value, with a safe default on nonempty text.
        await pilot.press('p'); await pilot.pause()
        assert app.focused.id == 'confirm-no'
        await pilot.press('enter'); await pilot.pause()
        assert preview.value == original and app.focused is preview
        await pilot.press('p'); await pilot.pause()
        await pilot.press('a', 'enter'); await pilot.pause()
        assert preview.value == 'pasted' and app.focused is preview
        preview.value = ''
        await pilot.press('p'); await pilot.pause()
        assert app.screen is config and preview.value == 'pasted'


@pytest.mark.asyncio
async def test_unbroken_line_preview_full_value_and_hidden_source_are_preserved():
    from textual.widgets import Select
    original = 'é😀' + 'x' * 500 + '\nnext\nlast\n'
    factory, wm, node = make(input_source='Configured', input=original)
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        screen = app.screen; preview = screen.query_one(LongTextPreview)
        preview.focus(); await pilot.pause()
        assert preview.content_region.height == 3
        assert preview.value == original and '2 more lines' in str(preview.label)
        await pilot.press('e'); await pilot.pause()
        area = app.screen.query_one(CommandTextArea)
        assert area.soft_wrap and area.text == original
        await pilot.press('ctrl+s'); await pilot.pause()
        await pilot.press('1'); await pilot.pause()
        screen.query_one('#field-input_source', Select).value = 'Upstream payload'
        await pilot.pause()
        assert not preview.display and preview.value == original
        screen.query_one('#field-input_source', Select).value = 'Configured'
        await pilot.press('2'); await pilot.pause()
        assert preview.display and preview.value == original


@pytest.mark.asyncio
async def test_read_only_preview_cannot_edit_or_paste():
    from textual.app import App
    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from textual.screen import Screen
    class Viewer(CommandScreenMixin, Screen):
        def compose(self):
            yield LongTextPreview('private view\n', read_only=True, id='view')
    from frontend.keymap import APP, bindings_for
    from frontend.keymap_runtime import KeymapScreenMixin
    class ViewApp(KeymapScreenMixin, App):
        KEYMAP = APP
        BINDINGS = bindings_for(KEYMAP)
        CSS_PATH = '../frontend/styles.tcss'
        def on_mount(self):
            self.push_screen(Viewer())
    app = ViewApp()
    async with app.run_test(size=(80, 24)) as pilot:
        preview = app.screen.query_one(LongTextPreview)
        preview.focus(); await pilot.press('e'); await pilot.pause()
        editor = app.screen; area = editor.query_one(CommandTextArea)
        assert area.read_only and not area.editing
        assert not editor.query('#long-text-save')
        await pilot.click(area); await pilot.pause()
        assert area.read_only and not area.editing
        await pilot.press('e', 'p', 'x', 'ctrl+s'); await pilot.pause()
        assert app.screen is editor and area.text == 'private view\n' and not area.editing
        await pilot.press('ctrl+q'); await pilot.pause()
        assert app.focused is preview and preview.value == 'private view\n'


def test_line_ending_edits_and_undo_ranges_are_exact():
    from frontend.widgets.long_text_document import LongTextDocument
    text = 'a\r\nb\rc\n\n\u2028\u0085😀'
    doc = LongTextDocument(text)
    assert doc.text == logical_text(text)
    assert doc.saved_text == text and doc.line_count == 5
    assert doc.get_text_range((0, 1), (3, 0)) == '\nb\nc\n'
    replaced = doc.replace_range((0, 1), (3, 0), 'X\nY\r\n')
    assert doc.text == 'aX\nY\n\n\u2028\u0085😀'
    assert doc.saved_text == 'aX\nY\r\n\n\u2028\u0085😀'
    doc.replace_range((0, 1), replaced.end_location, replaced.replaced_text)
    assert doc.text == logical_text(text)
    assert doc.saved_text == text


@pytest.mark.asyncio
async def test_editor_native_undo_preserves_newlines_and_unicode():
    original = 'first\r\nsecond\rthird\n\n😀\u2028'
    factory, wm, node = make(input_source='Configured', input=original)
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        preview = app.screen.query_one(LongTextPreview)
        preview.focus(); await pilot.press('e'); await pilot.pause()
        area = app.screen.query_one(CommandTextArea)
        await pilot.press('!', 'ctrl+z'); await pilot.pause()
        assert area.text == logical_text(original)
        await pilot.press('ctrl+s'); await pilot.pause()
        assert preview.value == original


def test_registered_multiline_inventory_uses_shared_widget():
    from backend.node_factory import NodeFactory
    found = []
    def fields(schema, path=''):
        for key, field in schema.items():
            name = path + key
            if field.get('type') in {'multiline', 'code'}:
                widget = _widget_for_field(key, field['type'], field, 'é\r\nfull\n\n')
                assert isinstance(widget, LongTextPreview), name
                assert widget.value == 'é\r\nfull\n\n'
                found.append(name)
            fields(field.get('item_schema', {}), name + '[].')
    types = set()
    for metadata in NodeFactory().get_node_types_metadata():
        before = len(found)
        fields(metadata.get('config_schema', {}), metadata['type'] + '.')
        if len(found) > before:
            types.add(metadata['type'])
    assert len(found) == 24 and len(types) == 12
    assert 'text_output_node.template' in found


@pytest.mark.asyncio
async def test_generic_nested_multiline_getter_and_disabled_field():
    from frontend.widgets.form_generator import ObjectListField, build_form
    from frontend.widgets.command_screen_mixin import CommandScreenMixin
    from textual.app import App
    from textual.screen import Screen
    schema = {'items': {'type': 'object_list', 'item_schema': {
        'text': {'type': 'multiline', 'label': 'Message'},
    }}, 'locked': {'type': 'multiline', 'enabled_when': {'enabled': True}},
        'enabled': {'type': 'boolean'}}
    holder = {}
    class FormScreen(CommandScreenMixin, Screen):
        def compose(self):
            form, holder['getter'] = build_form(schema, {
                'items': [{'id': 'item', 'text': 'nested\r\n\n'}], 'enabled': False,
                'locked': 'unchanged'})
            yield form
        def on_mount(self):
            from frontend.widgets.form_generator import apply_field_rules
            apply_field_rules(self, schema, holder['getter']())
    from frontend.keymap import APP, bindings_for
    from frontend.keymap_runtime import KeymapScreenMixin
    class FormApp(KeymapScreenMixin, App):
        KEYMAP = APP
        BINDINGS = bindings_for(KEYMAP)
        def on_mount(self):
            self.push_screen(FormScreen())
    app = FormApp()
    async with app.run_test(size=(80, 24)) as pilot:
        screen = app.screen
        preview = screen.query_one(ObjectListField).query_one(LongTextPreview)
        locked = screen.query_one('#field-locked', LongTextPreview)
        assert locked.disabled
        locked.press(); await pilot.pause()
        assert app.screen is screen
        preview.focus(); await pilot.press('enter'); await pilot.pause()
        await pilot.press('p', 'ctrl+s'); await pilot.pause()
        assert holder['getter']()['items'][0]['text'] == 'pnested\r\n\n'
        assert holder['getter']()['locked'] == 'unchanged'
        assert app.focused is preview


@pytest.mark.asyncio
async def test_selected_preview_paints_one_live_highlight(monkeypatch):
    from frontend import colors
    from rich.color import Color
    from textual.geometry import Region
    monkeypatch.delenv('NO_COLOR', raising=False)
    monkeypatch.setenv('TEXTUAL_COLOR_SYSTEM', 'truecolor')
    factory, wm, node = make(input_source='Configured', input='x' * 500)
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        preview = app.screen.query_one(LongTextPreview)
        preview.focus(); await pilot.pause()
        lines = preview.render_lines(Region(0, 0, preview.region.width, preview.region.height))
        assert len(lines) == 3
        assert '…' in lines[0].text and len(lines[0].text) < 80
        assert all(cell.style.bgcolor == Color.parse(colors.HIGHLIGHT)
                   for line in lines for cell in line if cell.text.strip())
        monkeypatch.setattr(colors, 'HIGHLIGHT', colors.PANEL_BACKGROUND)
        lines = preview.render_lines(Region(0, 0, preview.region.width, preview.region.height))
        assert all(cell.style.bgcolor == Color.parse(colors.PANEL_BACKGROUND)
                   for line in lines for cell in line if cell.text.strip())


@pytest.mark.asyncio
async def test_real_app_stash_picker_and_ctrl_q_do_not_close_node(tmp_path, monkeypatch):
    from backend import persistence
    from backend.stash_manager import StashManager
    from frontend.screens.stash import StashScreen
    from tests.test_stash_insert import _config_app
    monkeypatch.setattr(persistence, 'STASH_DIR', tmp_path / 'stash')
    stash = StashManager()
    stash.add_text('from stash\r\n😀\n', name='Question')
    app, open_config = _config_app(stash, 'hermes_ask_node', {
        'input_source': 'Configured', 'input': 'keep me', 'folder': str(tmp_path)})
    async with app.run_test(size=(80, 24)) as pilot:
        config = await open_config(pilot)
        await pilot.press('2'); await pilot.pause()
        preview = config.query_one('#field-input', LongTextPreview)
        preview.focus(); await pilot.press('e', 'x', 'ctrl+q'); await pilot.pause()
        assert app.focused.id == 'confirm-no'
        await pilot.press('a', 'enter'); await pilot.pause()
        assert app.screen is config and preview.value == 'keep me'
        await pilot.press('p'); await pilot.pause()
        assert isinstance(app.screen, StashScreen)
        await pilot.press('enter'); await pilot.pause()
        assert app.focused.id == 'confirm-no'
        await pilot.press('a', 'enter'); await pilot.pause()
        assert app.screen is config and preview.value == 'from stash\r\n😀\n'
        assert app.focused is preview
        await pilot.press('e', 'right', 'escape', 'p'); await pilot.pause()
        assert isinstance(app.screen, StashScreen)
        await pilot.press('enter'); await pilot.pause()
        area = app.screen.query_one(CommandTextArea)
        assert area.text == 'ffrom stash\n😀\nrom stash\n😀\n'
        assert app.screen.saved_value == 'ffrom stash\r\n😀\nrom stash\r\n😀\n'
        await pilot.press('ctrl+s'); await pilot.pause()
        assert app.screen is config and app.focused is preview
        assert config._saved_result is None
        await pilot.press('ctrl+s'); await pilot.pause()
        assert config._saved_result['config']['input'] == preview.value


@pytest.mark.asyncio
async def test_template_editor_refreshes_payload_preview_before_node_save():
    factory, wm, node = make('text_output_node', template='old {input}')
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        config = app.screen
        preview = config.query_one('#field-template', LongTextPreview)
        preview.focus(); await pilot.press('e'); await pilot.pause()
        app.screen.query_one(CommandTextArea).text = 'new {input}\nsecond line'
        await pilot.press('ctrl+s', '3'); await pilot.pause()
        rendered = str(config.query_one('#formatted-output-preview').render())
        assert 'new {input}\nsecond line' in rendered and 'old {input}' not in rendered
        assert config._saved_result is None
        assert wm.get_node_data(node)['config']['template'] == 'old {input}'


@pytest.mark.asyncio
async def test_selected_warning_confirmation_has_readable_role_text(monkeypatch):
    from frontend import colors
    from rich.color import Color
    from textual.geometry import Region
    monkeypatch.delenv('NO_COLOR', raising=False)
    monkeypatch.setenv('TEXTUAL_COLOR_SYSTEM', 'truecolor')
    factory, wm, node = make(input_source='Configured', input='keep')
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        app.screen.query_one(LongTextPreview).focus()
        await pilot.press('p', 'a'); await pilot.pause()
        button = app.focused
        assert button.id == 'confirm-yes'
        lines = button.render_lines(Region(0, 0, button.region.width, button.region.height))
        text = [segment for line in lines for segment in line if segment.text.strip()]
        assert text and all(segment.style.color == Color.parse(colors.NAME) for segment in text)
        assert all(segment.style.bgcolor == Color.parse(colors.HIGHLIGHT) for segment in text)

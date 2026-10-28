"""Review regression: native history must not turn an undone edit into a save."""
import pytest
from textual import events
from frontend.widgets.command_input import CommandTextArea
from frontend.widgets.long_text import LongTextPreview
from tests.test_small_wins_ui import Host, make


@pytest.mark.parametrize('original', ['a\r\nb', 'a\rb', 'a\rb\r\nc\nend\n'])
@pytest.mark.parametrize('size', [(80, 24)])
@pytest.mark.asyncio
async def test_enter_undo_save_is_byte_identical_and_not_dirty(original, size):
    factory, wm, node = make(input_source='Configured', input=original)
    app = Host(factory, wm, node)
    async with app.run_test(size=size) as pilot:
        await pilot.press('2'); await pilot.pause()
        config = app.screen
        preview = config.query_one(LongTextPreview)
        preview.focus(); await pilot.press('e'); await pilot.pause()
        editor = app.screen; area = editor.query_one(CommandTextArea)
        area.move_cursor((1, 0))
        lines = area.document.line_count
        await pilot.press('enter'); await pilot.pause()
        assert area.document.line_count == lines + 1
        await pilot.press('ctrl+z'); await pilot.pause()
        assert 'Changed' not in str(editor.query_one('#long-text-counts').render())
        await pilot.press('ctrl+y'); await pilot.pause()
        assert area.document.line_count == lines + 1
        await pilot.press('ctrl+z'); await pilot.pause()
        assert 'Changed' not in str(editor.query_one('#long-text-counts').render())
        await pilot.press('ctrl+s'); await pilot.pause()
        assert app.screen is config and preview.value.encode() == original.encode()
        assert not config._is_dirty()
        assert wm.get_node_data(node)['config']['input'] == original
        # Closing an undone draft must not ask to discard a nonexistent change.
        await pilot.press('e'); await pilot.pause()
        app.screen.query_one(CommandTextArea).move_cursor((1, 0))
        await pilot.press('enter', 'ctrl+z', 'escape', 'escape'); await pilot.pause()
        assert app.screen is config and not config._is_dirty()


@pytest.mark.parametrize('original', ['a\nb', 'a\r\nb', 'a\rb', 'a\rb\r\nc\nend\n'])
@pytest.mark.parametrize('method', ['paste', 'stash'])
@pytest.mark.asyncio
async def test_insert_undo_redo_and_save_respect_opened_style(original, method):
    from frontend.widgets.long_text_document import logical_text, line_ending_style
    inserted = 'X\r\nY\rZ\n'
    factory, wm, node = make(input_source='Configured', input=original)
    app = Host(factory, wm, node)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press('2'); await pilot.pause()
        config = app.screen; preview = config.query_one(LongTextPreview)
        preview.focus(); await pilot.press('e'); await pilot.pause()
        editor = app.screen; area = editor.query_one(CommandTextArea)
        area.move_cursor((1, 0)); area.history.checkpoint()
        if method == 'paste':
            app.post_message(events.Paste(inserted)); await pilot.pause()
        else:
            await pilot.press('escape')
            def stash(*args, callback, **kwargs):
                callback({'value': inserted})
            app.action_stash = stash
            await pilot.press('p'); await pilot.pause()
        expected_logical = 'a\n' + logical_text(inserted) + logical_text(original)[2:]
        assert area.text == expected_logical
        await pilot.press('ctrl+z'); await pilot.pause()
        assert area.text == logical_text(original)
        assert not editor.changed and editor.saved_value.encode() == original.encode()
        await pilot.press('ctrl+y'); await pilot.pause()
        assert area.text == expected_logical and editor.changed
        if line_ending_style(original) == 'mixed':
            expected = 'a\r' + inserted + original[2:]
        else:
            expected = expected_logical.replace('\n', line_ending_style(original))
        assert editor.saved_value == expected
        # Undo again restores the exact field and closes without confirmation.
        await pilot.press('ctrl+z', 'ctrl+s'); await pilot.pause()
        assert app.screen is config and not config._is_dirty() and preview.value == original
        # Commit a genuine edit, then reopen: the style and source-line count survive.
        await pilot.press('e'); await pilot.pause()
        editor = app.screen; area = editor.query_one(CommandTextArea)
        area.move_cursor((1, 0)); area.insert(inserted)
        await pilot.press('ctrl+s'); await pilot.pause()
        assert preview.value == expected and config._is_dirty()
        await pilot.press('e'); await pilot.pause()
        assert app.screen.query_one(CommandTextArea).text == expected_logical
        assert not app.screen.changed


def test_mixed_boundary_and_history_ranges_keep_two_breaks():
    from frontend.widgets.long_text_document import LongTextDocument
    doc = LongTextDocument('a\rb\nc')
    added = doc.replace_range((1, 0), (1, 0), '\n')
    assert doc.text == 'a\n\nb\nc' and doc.saved_text == 'a\r\r\nb\nc'
    deleted = doc.replace_range((0, 1), (2, 0), '')
    doc.replace_range((0, 1), deleted.end_location, deleted.replaced_text)
    assert doc.text == 'a\n\nb\nc'
    doc.replace_range((1, 0), added.end_location, added.replaced_text)
    assert doc.text == 'a\nb\nc' and doc.saved_text == 'a\rb\nc'

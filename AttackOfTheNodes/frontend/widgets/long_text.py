"""Shared preview-only multiline fields and their full-screen draft editor."""
from rich.text import Text
from rich.style import Style
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.document._wrapped_document import WrappedDocument
from textual.document._document_navigator import DocumentNavigator
from textual.screen import ModalScreen
from textual.message import Message
from textual.widgets import Button, Label, Static, TextArea
from frontend import colors
from frontend.keymap_runtime import screen_owns_key
from frontend.keymap import LONG_TEXT_EDITOR, TEXT_AREA, bindings_for, display_key
from frontend.widgets.command_input import CommandTextArea
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.contract_rows import CompactRowButton
from frontend.widgets.long_text_document import LongTextDocument, logical_text, line_ending_style
from frontend.widgets.status_bar import StatusBar


def _keys(profile, command_id):
    command = next(c for c in profile.commands if c.id == command_id)
    return '/'.join(display_key(key) for key in command.keys)


class LongTextPreview(CompactRowButton):
    class Changed(Message):
        """The full field value changed, independently of saving its owner."""
        def __init__(self, preview):
            self.preview = preview
            super().__init__()

    DEFAULT_CSS = '''
    LongTextPreview { width: 100%; height: 3; min-height: 3;
        text-align: left; content-align: left top; padding: 0 1;
        border: none; text-wrap: nowrap; text-overflow: ellipsis; text-style: none; }
    LongTextPreview:focus { border: none; text-style: none; }
    '''

    def __init__(self, value, *, field_label='Text', context_label=None,
                 read_only=False, language=None, placeholder=None, **kwargs):
        self._value = '' if value is None else str(value)
        self.field_label = field_label
        self.context_label = context_label
        self.read_only = read_only
        self.language = language
        self.placeholder = placeholder
        super().__init__(self._preview(), selected_foreground_role='NAME', **kwargs)
        # Production Button focus rules otherwise reserve two of the three rows.
        self.styles.border = ('none', 'transparent')
        self.styles.text_wrap = 'nowrap'
        self.styles.text_overflow = 'ellipsis'
        self.styles.text_style = 'none'

    def _preview(self):
        lines = LongTextDocument(self._value).lines
        text = '\n'.join(lines[:2])
        if len(lines) > 2:
            text += f'\n… {len(lines) - 2} more lines'
        return Text(text or '(empty — e/Enter to edit)')

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        value = str(value)
        if value != self._value:
            self._value = value
            self.label = self._preview()
            self.post_message(self.Changed(self))

    def _breadcrumb(self):
        parts = []
        for screen in reversed(self.app.screen_stack):
            node = getattr(screen, 'node_data', None)
            factory = getattr(screen, 'factory', None)
            if node and factory:
                metadata = factory.metadata_for_type(node['type']) or {}
                parts.append(node.get('alias') or metadata.get('display_name') or node['type'])
                break
        context = self.context_label() if callable(self.context_label) else self.context_label
        if context:
            parts.append(context)
        parts.append(self.field_label)
        return ' › '.join(parts)

    def press(self):
        if self.disabled:
            return self
        def done(value):
            if value is not None and not self.read_only:
                self.value = value
            self.focus()
        self.app.push_screen(LongTextEditor(self.value, title=self._breadcrumb(),
                                           read_only=self.read_only, language=self.language,
                                           placeholder=self.placeholder), done)
        return self

    def replace_from_stash(self, value, done):
        from frontend.screens.confirm import ConfirmScreen
        if self.read_only or self.disabled:
            return
        def replace(yes):
            if yes:
                self.value = value
                done()
            self.focus()
        if self.value:
            self.app.push_screen(ConfirmScreen('Replace all the text?', 'Replace', 'Cancel', initial_no=True, role_highlight=True), replace)
        else:
            replace(True)


class LongTextArea(CommandTextArea):
    """Native editing and history, with lossless form content."""
    def _set_document(self, text, language):
        previous = getattr(self, 'document', None)
        super()._set_document(text, language)
        # Textual rebuilds on language changes using its logical .text. Keep
        # separator provenance when that rebuild did not change the draft.
        self.document = (previous if isinstance(previous, LongTextDocument)
                         and logical_text(text) == previous.text else LongTextDocument(text))
        self._highlight_query = None
        self.wrapped_document = WrappedDocument(self.document, tab_width=self.indent_width)
        self.navigator = DocumentNavigator(self.wrapped_document)
        self._build_highlight_map()
        self.move_cursor((0, 0))
        self._rewrap_and_refresh_virtual_size()

    def render_line(self, y):
        # Change only the selection fill; preserve the native text theme.
        if self._theme is not None:
            self._theme.selection_style = Style(bgcolor=colors.HIGHLIGHT)
        return super().render_line(y)

    def check_consume_key(self, key, character):
        if screen_owns_key(self, key, priority_only=True):
            return False
        return super().check_consume_key(key, character)

    def on_click(self, event):
        event.prevent_default()
        if not self.screen.read_only:
            super().on_click(event)


class LongTextStatus(StatusBar):
    def _formatted(self):
        profile = LONG_TEXT_EDITOR
        if self._mode == 'edit':
            text = f'Typing · {_keys(TEXT_AREA, "text.finish_escape")}: commands'
        else:
            text = (f'Commands · {_keys(profile, "ui.activate")}: type · '
                    f'{_keys(profile, "long_text.stash")}: paste · {_keys(profile, "long_text.cancel")}: close')
        return Text(f'{text} · {_keys(profile, "long_text.save")}: save', style=colors.MUTED)


class LongTextEditor(CommandScreenMixin, ModalScreen):
    KEYMAP = LONG_TEXT_EDITOR
    BINDINGS = bindings_for(KEYMAP)
    DEFAULT_CSS = '''
    LongTextEditor { padding: 1; background: $background; }
    LongTextEditor .modal-title { height: 1; text-wrap: nowrap; text-overflow: ellipsis; }
    LongTextEditor CommandTextArea { height: 1fr; width: 100%; }
    LongTextEditor .button-row { height: 3; }
    LongTextEditor .long-text-counts, LongTextEditor .long-text-help { height: 1; }
    '''

    def __init__(self, value, *, title='Text', read_only=False, language=None, placeholder=None):
        super().__init__()
        self.original = value
        self.original_logical = logical_text(value)
        self.line_ending_style = line_ending_style(value)
        self.field_title = title
        self.placeholder = placeholder
        self.read_only = read_only
        self.language = language

    @property
    def changed(self):
        return self.query_one(CommandTextArea).text != self.original_logical

    @property
    def saved_value(self):
        area = self.query_one(CommandTextArea)
        if not self.changed:
            return self.original
        if self.line_ending_style == 'mixed':
            return area.document.saved_text
        return area.text.replace('\n', self.line_ending_style)

    def compose(self) -> ComposeResult:
        title = ('View text' if self.read_only else 'Edit text') + ' · ' + self.field_title
        heading = Label(Text(title), classes='modal-title')
        heading.tooltip = title
        yield heading
        yield LongTextArea(self.original, id='long-text-editor', soft_wrap=True, language=self.language,
                           placeholder=self.placeholder)
        yield Static('', id='long-text-counts', classes='long-text-counts')
        with Horizontal(classes='button-row'):
            if not self.read_only:
                yield CompactRowButton('Save', id='long-text-save', variant='primary', selected_foreground_role='NAME')
            yield CompactRowButton('Close' if self.read_only else 'Cancel', id='long-text-cancel', selected_foreground_role='NAME')
        yield Static('', id='long-text-help', classes='long-text-help')
        yield LongTextStatus()

    def on_mount(self):
        area = self.query_one(CommandTextArea)
        area.focus()
        if not self.read_only:
            area.begin_edit(place_cursor_at_end=False)
        self._sync_cursor_mode()

    def _sync_cursor_mode(self):
        super()._sync_cursor_mode()
        area = self.query_one(CommandTextArea)
        if self.read_only:
            self.query_one(StatusBar).update(Text(
                f'View only · {_keys(self.KEYMAP, "long_text.cancel")}: close', style=colors.MUTED))
        help_text = (f'Arrows: move · Enter: new line · p types p' if area.editing else
                     f'Tab: buttons · {_keys(self.KEYMAP, "ui.focus.up").split("/")[0]}/'
                     f'{_keys(self.KEYMAP, "ui.focus.down").split("/")[0]}: move between controls')
        help_text += f' · {_keys(self.KEYMAP, "long_text.revert")}: cancel'
        self.query_one('#long-text-help', Static).update(Text(help_text, style=colors.MUTED))
        self._update_counts()

    def _update_counts(self):
        area = self.query_one(CommandTextArea)
        row, column = area.cursor_location
        text = area.text
        count = area.document.line_count
        changed = ' · Changed' if self.changed else ''
        self.query_one('#long-text-counts', Static).update(Text(
            f'Line {row + 1}, column {column + 1} · {len(self.saved_value)} characters · '
            f'{count} {"line" if count == 1 else "lines"}{changed}', style=colors.MUTED))

    def on_text_area_changed(self, event: TextArea.Changed):
        self._update_counts()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged):
        self._update_counts()

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == 'long-text-save':
            self.action_submit()
        elif event.button.id == 'long-text-cancel':
            self.dismiss(None)

    def check_action(self, action, parameters):
        if self.read_only and action in {'submit', 'stash_insert'}:
            return False
        return super().check_action(action, parameters)

    def action_activate_focused(self):
        area = self.query_one(CommandTextArea)
        if self.app.focused is area:
            if not self.read_only:
                area.begin_edit(place_cursor_at_end=False)
        else:
            super().action_activate_focused()

    def action_submit(self):
        if not self.read_only:
            self.dismiss(self.saved_value)

    def action_cancel_draft(self):
        # Ctrl+Q owns the whole field draft, including while typing. No event
        # reaches Node Config or its own revert/save actions.
        self.query_one(CommandTextArea).end_edit()
        self.action_cancel()

    def action_cancel(self):
        from frontend.screens.confirm import ConfirmScreen
        if self.read_only or not self.changed:
            self.dismiss(None)
        else:
            self.app.push_screen(ConfirmScreen('Discard changes?', 'Discard', 'Keep editing', initial_no=True, role_highlight=True),
                                 lambda yes: self.dismiss(None) if yes else None)

    def action_stash_insert(self):
        if not self.read_only:
            self.app.action_stash('entries', insert_into={'label': 'Text', 'accepts': ['string']},
                                  callback=self._insert)

    def _insert(self, entry):
        area = self.query_one(CommandTextArea)
        if entry and not self.read_only:
            area.insert(str(entry['value']))
        area.focus()

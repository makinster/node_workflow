"""Opt-in multiline preview with a shared full-screen editor."""
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label
from frontend.keymap import CONTRACT_ROW_EDITOR, bindings_for
from frontend.widgets.command_input import CommandTextArea
from frontend.widgets.command_screen_mixin import CommandScreenMixin
from frontend.widgets.status_bar import StatusBar


class LongTextPreview(Button):
    DEFAULT_CSS = '''
    LongTextPreview { width: 100%; height: auto; min-height: 3;
        text-align: left; content-align: left middle; }
    '''

    def __init__(self, value, **kwargs):
        self._value = str(value or '')
        super().__init__(self._preview(), **kwargs)

    def _preview(self):
        lines = self._value.split('\n')
        text = '\n'.join(lines[:2])
        if len(lines) > 2:
            text += f'\n… {len(lines) - 2} more lines'
        return Text(text or '(empty — e/Enter to edit)')

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = str(value)
        self.label = self._preview()

    def press(self):
        def done(value):
            if value is not None:
                self.value = value
            self.focus()
        self.app.push_screen(LongTextEditor(self.value), done)
        return self

    def replace_from_stash(self, value, done):
        from frontend.screens.confirm import ConfirmScreen
        def replace(yes):
            if yes:
                self.value = value
                done()
            self.focus()
        if self.value:
            self.app.push_screen(ConfirmScreen('Replace all the text?', 'Replace', 'Cancel'), replace)
        else:
            replace(True)


class LongTextEditor(CommandScreenMixin, ModalScreen):
    KEYMAP = CONTRACT_ROW_EDITOR
    BINDINGS = bindings_for(KEYMAP)
    DEFAULT_CSS = '''
    LongTextEditor { padding: 1; background: $background; }
    LongTextEditor CommandTextArea { height: 1fr; width: 100%; }
    LongTextEditor .button-row { height: auto; }
    '''

    def __init__(self, value):
        super().__init__()
        self.original = value

    def compose(self) -> ComposeResult:
        yield Label('Edit full text', classes='modal-title')
        yield CommandTextArea(self.original, id='long-text-editor', soft_wrap=True)
        with Horizontal(classes='button-row'):
            yield Button('Save', id='long-text-save', variant='primary')
            yield Button('Cancel', id='long-text-cancel')
        yield StatusBar('Esc stop typing | P paste | e resume | ctrl+s save | Esc close')

    def on_mount(self):
        self.query_one(CommandTextArea).begin_edit()

    def on_button_pressed(self, event):
        if event.button.id == 'long-text-save':
            self.action_submit()
        elif event.button.id == 'long-text-cancel':
            self.dismiss(None)

    def action_submit(self):
        self.dismiss(self.query_one(CommandTextArea).text)

    def action_cancel(self):
        from frontend.screens.confirm import ConfirmScreen
        if self.query_one(CommandTextArea).text == self.original:
            self.dismiss(None)
        else:
            self.app.push_screen(ConfirmScreen('Discard changes?', 'Discard', 'Keep editing'),
                                 lambda yes: self.dismiss(None) if yes else None)

    def action_stash_insert(self):
        self.app.action_stash('entries', insert_into={'label': 'Text', 'accepts': ['string']},
                              callback=self._insert)

    def _insert(self, entry):
        if entry:
            area = self.query_one(CommandTextArea)
            area.insert(str(entry['value']))
            area.focus()

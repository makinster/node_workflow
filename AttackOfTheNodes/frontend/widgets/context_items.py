"""Ordered source rows, using the shared compact table/editor navigation."""
import uuid
from rich.text import Text
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, Select, Static
from backend.context_pack import SOURCES, items_problem
from frontend.widgets.command_input import CommandInput
from frontend.widgets.contract_rows import CompactRowButton, ContractRowEditor
from frontend.widgets.reply_fields import ReplyFields
from frontend.widgets.long_text import LongTextPreview
from frontend.widgets.status_bar import StatusBar


def short(value, cap):
    return value if len(value) <= cap else value[:cap - 1] + '…'


class ContextItems(ReplyFields):
    DEFAULT_CSS = 'ContextItems, ContextItems > Vertical { height: auto; }'

    def __init__(self, value, schema, vault_options=None, **kwargs):
        super().__init__(value, schema, **kwargs)
        self.vault_options = (vault_options or {}).get('any', [])

    def compose(self):
        yield Static(self.schema.get('hint', ''), markup=False, classes='form-description')
        yield Static(f' {"Label":<24}Source', markup=False)
        yield Vertical(*self._row_buttons(), id=f'{self.id}-rows')
        yield Button('Add item', id=f'{self.id}-add', compact=True)
        yield Static('e/Enter edit · X remove', classes='form-description')

    def _row_buttons(self):
        buttons = []
        for index, row in enumerate(self.rows):
            source = str(row.get('source', ''))
            if source == 'Vault':
                source += ' · ' + short(str(row.get('vault_key', '')), 24)
            buttons.append(CompactRowButton(Text(f'{short(str(row.get("label", "")), 23):<24}{source}'),
                                  id=f'{self.id}-row-{index}', classes='contract-row', compact=True))
        return buttons

    def _open_editor(self, index):
        if index is None and len(self.rows) >= 16:
            return
        row = dict(self.rows[index]) if index is not None else {}
        others = [r.get('label', '') for i, r in enumerate(self.rows) if i != index]
        async def done(result):
            if result is None:
                return
            if index is None:
                self.rows.append(result)
                await self._redraw(len(self.rows) - 1)
            else:
                self.rows[index] = result
                await self._redraw(index)
        self.app.push_screen(ContextItemEditor(row, others, self.vault_options), done)


class ContextItemEditor(ContractRowEditor):
    DEFAULT_CSS = '''
    ContextItemEditor #modal-card { height: 100%; max-height: 100%; overflow-y: hidden; }
    ContextItemEditor .context-item-body { height: 1fr; }
    ContextItemEditor #row-key-holder, ContextItemEditor #row-text-holder { height: auto; }
    '''

    def __init__(self, row, other_names, vault_options):
        super().__init__('context', row, other_names)
        self.vault_options = list(vault_options)
        self.other_names = {str(name).casefold() for name in other_names}

    def compose(self):
        with Vertical(id='modal-card', classes='contract-row-modal'):
            yield Label('Edit item · Context Pack' if self.row else 'New item · Context Pack', classes='modal-title')
            with VerticalScroll(classes='context-item-body'):
                yield Label('Label')
                yield CommandInput(str(self.row.get('label', '')), id='row-label')
                yield Label('Source')
                yield Select([(s, s) for s in SOURCES], value=self.row.get('source', SOURCES[0]),
                             allow_blank=False, id='row-source')
                with Vertical(id='row-key-holder'):
                    yield Label('Vault key')
                    options = self.vault_options.copy()
                    key = str(self.row.get('vault_key', ''))
                    if key and key not in [v for _, v in options]:
                        options.append((f'{key} (unavailable)', key))
                    yield Select(options, value=key or Select.NULL, allow_blank=True, id='row-key')
                with Vertical(id='row-text-holder'):
                    yield Label('Text')
                    yield LongTextPreview(self.row.get('text', ''), id='row-text', field_label='Text',
                                          context_label=lambda: self.query_one('#row-label', CommandInput).value)
                    yield Static('e/Enter: edit full text · P: replace', classes='form-description')
                yield Static('Use the single incoming value. No file is opened.', id='row-upstream', classes='form-description')
                yield Static('', id='row-error', classes='field-error', markup=False)
            with Horizontal(classes='button-row'):
                yield Button('Confirm', id='confirm-row', variant='primary')
                yield Button('Cancel', id='cancel-row')
            yield StatusBar('w/s move | e edit | P paste | ctrl+s confirm | Esc cancel')

    def on_mount(self):
        self.query_one('#row-error').display = False
        self._sync_source()
        self._focus_first()

    def _sync_vault_key(self):
        pass

    def on_select_changed(self, event):
        if event.select.id == 'row-source':
            self._sync_source()

    def _sync_source(self):
        source = self.query_one('#row-source', Select).value
        self.query_one('#row-key-holder').display = source == 'Vault'
        self.query_one('#row-text-holder').display = source == 'Configured text'
        self.query_one('#row-upstream').display = source == 'Upstream payload'

    def action_submit(self):
        for widget in self.query(CommandInput):
            if widget.editing:
                widget.end_edit()
        key = self.query_one('#row-key', Select).value
        result = dict(id=self.row.get('id') or 'item_' + uuid.uuid4().hex[:8],
                      label=self.query_one('#row-label', CommandInput).value,
                      source=str(self.query_one('#row-source', Select).value),
                      vault_key='' if key is Select.NULL else str(key),
                      text=self.query_one('#row-text', LongTextPreview).value)
        problem = items_problem([result])
        if result['label'].casefold() in self.other_names:
            problem = 'Use a different label for each item.'
        if problem:
            self.query_one('#row-error', Static).update(problem)
            self.query_one('#row-error').display = True
            return
        self.dismiss(result)

    def action_stash_insert(self):
        from frontend.widgets.stash_focus import stash_field
        preview = stash_field(self, '#row-text')
        if preview is None:
            return
        if self.query_one('#row-source', Select).value == 'Configured text':
            self.app.action_stash('entries', insert_into={'label': 'Text', 'accepts': ['string']},
                callback=lambda entry: preview.replace_from_stash(str(entry['value']), lambda: None)
                if entry and stash_field(self, '#row-text') is preview else None)

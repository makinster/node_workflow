"""Check reply fields using Start's compact row navigation/editor pattern."""
import uuid
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Label, Select, Static
from backend.reply_shape import TYPES, field_problem
from frontend.widgets.command_input import CommandInput
from frontend.widgets.contract_rows import ContractRowsField, ContractRowEditor
from frontend.widgets.status_bar import StatusBar


class ReplyFields(ContractRowsField):
    DEFAULT_CSS = "ReplyFields, ReplyFields > Vertical { height: auto; }"

    def __init__(self, value, schema, **kwargs):
        super().__init__('reply', value if isinstance(value, list) else [], **kwargs)
        self.schema = schema

    def compose(self) -> ComposeResult:
        yield Static(self.schema.get('hint', ''), markup=False, classes='form-description')
        yield Static(f' {"Field":<24}{"Type":<14}Required?', markup=False)
        yield Vertical(*self._row_buttons(), id=f'{self.id}-rows')
        yield Button('Add field', id=f'{self.id}-add', compact=True)
        yield Static('e/Enter edit · X remove', classes='form-description')

    @staticmethod
    def _shown_name(row):
        name = str(row.get("name") or "(no name)")
        return name if len(name) <= 23 else name[:22] + "…"

    def _row_buttons(self):
        return [Button(Text(f'{self._shown_name(row):<24}'
                            f'{TYPES.get(row.get("kind"), "?"):<14}'
                            f'{"yes" if row.get("required") else "no"}'),
                       id=f'{self.id}-row-{i}', classes='contract-row', compact=True)
                for i, row in enumerate(self.rows)]

    async def remove_selected(self):
        if self.rows:
            del self.rows[self.selected]
            await self._redraw(self.selected)
        if not self.rows:
            self.query_one(f'#{self.id}-add').focus()

    def _open_editor(self, index):
        if index is None and len(self.rows) >= 32:
            return
        row = dict(self.rows[index]) if index is not None else {}
        others = [r.get('name') for i, r in enumerate(self.rows) if i != index]
        async def done(result):
            if result is None:
                return
            if index is None:
                self.rows.append(result)
                await self._redraw(len(self.rows) - 1)
            else:
                self.rows[index] = result
                await self._redraw(index)
        self.app.push_screen(ReplyFieldEditor('reply', row, others), done)


class ReplyFieldEditor(ContractRowEditor):
    def __init__(self, kind, row, other_names):
        super().__init__(kind, row, other_names)
        self.other_names = set(other_names)

    def compose(self) -> ComposeResult:
        with Vertical(id='modal-card', classes='contract-row-modal'):
            yield Label('Edit field' if self.row else 'New field', classes='modal-title')
            yield Label('Field')
            yield CommandInput(value=str(self.row.get('name', '')), id='row-name')
            yield Label('Type')
            yield Select([(label, kind) for kind, label in TYPES.items()],
                         value=self.row.get('kind', 'string'), allow_blank=False, id='row-type')
            yield Checkbox('Required', value=self.row.get('required', True), id='row-required')
            yield Static('', id='row-error', classes='field-error', markup=False)
            with Horizontal(classes='button-row'):
                yield Button('Confirm', id='confirm-row', variant='primary')
                yield Button('Cancel', id='cancel-row')
            yield StatusBar('w/s move | e edit | ctrl+s confirm | esc cancel')

    def _sync_vault_key(self):
        pass  # This row editor has no routing controls.

    def on_mount(self):
        self.query_one('#row-error').display = False
        self._focus_first()

    def action_submit(self):
        for widget in self.query(CommandInput):
            if widget.editing:
                widget.end_edit()
        result = {'id': self.row.get('id') or 'field_' + uuid.uuid4().hex[:8],
                  'name': self.query_one('#row-name', CommandInput).value,
                  'kind': str(self.query_one('#row-type', Select).value),
                  'required': self.query_one('#row-required', Checkbox).value}
        problem = field_problem([result])
        if result['name'] in self.other_names:
            problem = 'Use a different name for each field.'
        if problem:
            self.query_one('#row-error', Static).update(problem)
            self.query_one('#row-error').display = True
            return
        self.dismiss(result)

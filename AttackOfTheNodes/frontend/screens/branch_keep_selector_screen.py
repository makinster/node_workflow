"""Keep/recover path picker. Legacy single-choice stubs retain their adapter."""
from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static
from frontend.keymap import BRANCH_KEEP_SELECTOR, bindings_for
from frontend.keymap_runtime import KeymapScreenMixin
from frontend.widgets.list_navigation import focus_list, move_list_highlight
from frontend.screens.confirm import ConfirmScreen


class BranchKeepSelectorScreen(KeymapScreenMixin, ModalScreen):
    KEYMAP = BRANCH_KEEP_SELECTOR
    BINDINGS = bindings_for(KEYMAP)
    DEFAULT_CSS = '''
    BranchKeepSelectorScreen #modal-card.group-delete-card {
        height: auto; max-height: 100%; width: 76; max-width: 100%;
    }
    BranchKeepSelectorScreen #branch-keep-list {
        height: auto; min-height: 1; scrollbar-gutter: stable;
    }
    BranchKeepSelectorScreen .modal-help { height: auto; }
    '''

    def __init__(self, branch_node_id, branch_label, ports, port_labels=None, *,
                 required=None, maximum=None, operation_id='', title=None,
                 prompt=None, apply_label='Apply', preview=None):
        super().__init__()
        self.branch_node_id = branch_node_id
        self.branch_label = branch_label
        self.ports = list(ports)
        self.port_labels = port_labels or {}
        self.required = required
        self.maximum = maximum if maximum is not None else required
        self.operation_id = operation_id
        self.grouped = required is not None or maximum is not None
        self.selected = set()
        self.title = title
        self.prompt = prompt
        self.apply_label = apply_label
        self.preview = preview

    def compose(self) -> ComposeResult:
        with Vertical(id='modal-card', classes='group-delete-card' if self.grouped else ''):
            yield Label(self.title or (f'Delete {self.branch_label} — keep {self.required} ' + ('path' if self.required == 1 else 'paths') if self.grouped
                                      else f'Keep which branch of: {self.branch_label}?'), classes='modal-title', markup=False)
            yield Static('', id='path-count', classes='modal-help')
            yield ListView(id='branch-keep-list')
            yield Static(self.prompt or ('Shared nodes stay. Z brings them back.' if self.grouped else
                'Other branches and their nodes will be permanently deleted.'), id='path-preview', classes='modal-help', markup=False)
            yield Static('Space/E toggle | W/S move | Enter apply | Esc cancel' if self.grouped else
                         '↑↓ navigate  ENTER keep  ESC cancel', classes='modal-help')
            with Horizontal(classes='button-row'):
                yield Button(self.apply_label if self.grouped else 'Keep', id='choose-branch-keep', variant='primary')
                yield Button('Cancel', id='cancel-branch-keep')

    async def on_mount(self):
        view = self.query_one('#branch-keep-list', ListView)
        await view.extend([ListItem(Static(self._label(port), markup=False)) for port in self.ports])
        focus_list(self.app, view, len(self.ports))
        self._update()

    def on_resize(self):
        self.call_after_refresh(self._fit_list)

    def _fit_list(self):
        """Fit short lists; reserve space for controls before capping long ones."""
        if not self.is_mounted:
            return
        card = self.query_one('#modal-card')
        view = self.query_one('#branch-keep-list', ListView)
        rows_height = sum(row.outer_size.height for row in view.children)
        # outer_size leaves out margins (the button row's top margin).
        controls_height = sum(
            child.outer_size.height + child.styles.margin.height
            for child in card.children if child is not view
        )
        available = max(
            1, self.size.height - card.styles.gutter.height - controls_height
        )
        height = min(max(1, rows_height), available)
        if view.styles.height.is_auto or view.styles.height.value != height:
            view.styles.height = height
            # Recheck after layout settles: the scrollbar can change wrapping.
            self.set_timer(0.02, self._fit_list)

    def _label(self, port):
        return (('[x] ' if port in self.selected else '[ ] ') if self.grouped else '') + self.port_labels.get(port, port)

    def _update(self):
        self.call_after_refresh(self._fit_list)
        if not self.grouped:
            return
        count = len(self.selected)
        valid = count == self.required if self.required is not None else count <= self.maximum
        self.query_one('#choose-branch-keep', Button).disabled = not valid
        self.query_one('#path-count', Static).update(
            f'Selected {count} / {self.required}' if self.required is not None else f'Picked {count} — up to {self.maximum}')
        for port, item in zip(self.ports, self.query_one(ListView).children):
            item.query_one(Static).update(self._label(port))
        if self.preview is not None:
            text = self.preview([p for p in self.ports if p in self.selected])
            self.query_one('#path-preview', Static).update(text)

    def on_list_view_selected(self, event):
        if not self.grouped:
            self._dismiss_selected(event.list_view.index)
        else:
            self._apply()

    def on_button_pressed(self, event):
        if event.button.id == 'choose-branch-keep':
            self._apply() if self.grouped else self._choose_highlighted()
        elif event.button.id == 'cancel-branch-keep':
            self.action_cancel()

    def action_choose(self):
        if isinstance(self.app.focused, Button):
            self.app.focused.press()
        elif self.grouped:
            self._apply()
        else:
            self._choose_highlighted()

    def action_toggle(self):
        if not self.grouped or isinstance(self.app.focused, Button):
            self.action_choose()
            return
        index = self.query_one(ListView).index
        if index is not None and 0 <= index < len(self.ports):
            port = self.ports[index]
            self.selected.symmetric_difference_update({port})
            self._update()

    def _apply(self):
        if not self.query_one('#choose-branch-keep', Button).disabled:
            self.dismiss({'ports': [p for p in self.ports if p in self.selected],
                          'required': self.required, 'operation_id': self.operation_id})

    def _choose_highlighted(self):
        self._dismiss_selected(self.query_one(ListView).index)

    def _dismiss_selected(self, index):
        if index is not None and 0 <= index < len(self.ports):
            self.dismiss({'kept_port': self.ports[index]})

    def action_cancel(self):
        self.dismiss(None)

    def action_cursor_up(self):
        self._move_selection(-1)

    def action_cursor_down(self):
        self._move_selection(1)

    def _move_selection(self, delta):
        view = self.query_one(ListView)
        if self.grouped and isinstance(self.app.focused, Button):
            if delta < 0:
                view.focus()
                return
            self.query_one('#cancel-branch-keep', Button).focus()
            return
        if self.grouped and delta > 0 and view.index == len(self.ports) - 1:
            button = self.query_one('#choose-branch-keep', Button)
            (self.query_one('#cancel-branch-keep', Button) if button.disabled else button).focus()
            return
        move_list_highlight(self.app, view, len(self.ports), delta)


class DeletionConfirmScreen(ConfirmScreen):
    """Keep complete repair/loss previews readable, including wrapped lines."""
    DEFAULT_CSS = """
    DeletionConfirmScreen #modal-card { max-height: 100%; overflow-y: auto; }
    DeletionConfirmScreen .modal-title { height: auto; }
    """

    def _message_label(self):
        label = Label(self._message, classes='modal-title', markup=False)
        # Production CSS gives generic modal titles one line. These previews
        # contain the repair/loss details and must keep every wrapped line.
        label.styles.height = 'auto'
        return label

    def compose(self):
        with Vertical(id='modal-card', classes='confirm-modal'):
            yield self._message_label()
            with Horizontal(classes='button-row'):
                yield Button(self._yes_label, id='confirm-yes', variant='warning')
                yield Button(self._no_label, id='confirm-no')


class BranchRecoveryPrompt(DeletionConfirmScreen):
    """Three explicit outcomes; Cancel keeps the unsaved configuration draft."""
    def compose(self):
        with Vertical(id='modal-card', classes='confirm-modal'):
            yield self._message_label()
            with Horizontal(classes='button-row'):
                yield Button('Recover', id='confirm-yes', variant='primary')
                yield Button('Leave empty', id='leave-empty')
                yield Button('Cancel', id='confirm-no')
    def on_button_pressed(self, event):
        event.stop()
        event.prevent_default()
        self.dismiss({'confirm-yes': 'recover', 'leave-empty': 'empty'}.get(event.button.id))
    def action_confirm_yes(self):
        self.dismiss('recover')
    def action_confirm_no(self):
        self.dismiss(None)


class SavedPathsScreen(DeletionConfirmScreen):
    def compose(self):
        with Vertical(id='modal-card', classes='confirm-modal'):
            yield self._message_label()
            yield Button('Close', id='confirm-no', variant='primary')

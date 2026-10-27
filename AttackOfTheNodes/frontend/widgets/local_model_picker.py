"""Installed local models, discovered read-only; editable fallback on failure."""
from textual.containers import Vertical
from textual.widgets import Select, Static
from backend.integrations.local_model import list_models
from frontend.widgets.command_input import CommandInput


class LocalModelPicker(Vertical):
    DEFAULT_CSS = 'LocalModelPicker { height: auto; }'

    def __init__(self, value='', *, url=None, default_model='', use_default=False, **kwargs):
        super().__init__(**kwargs)
        self.initial_value = str(value or '')
        self.url = url
        self.default_model = str(default_model or '')
        self.use_default = use_default
        self._revision = 0

    def compose(self):
        # Usable immediately, including Save/Cancel while discovery is pending.
        yield CommandInput(self.initial_value, id='model-value')
        yield Static('Listing installed models…', id='model-status', markup=False)

    @property
    def value(self):
        controls = self.query('#model-value')
        if not controls:
            return self.initial_value
        control = controls.first()
        return '' if control.value is Select.NULL else str(control.value)

    def on_mount(self):
        if self.url is None:
            manager = getattr(self.app, 'configuration_manager', None)
            if manager is None:
                self.query_one('#model-status', Static).update("Couldn't list models · enter a model name")
                return
            self.url = manager.get('local_model_server_url')
            self.default_model = str(manager.get('local_model_default_model') or '')
        self.refresh_models(self.url)

    def refresh_models(self, url):
        """A changed Options URL supersedes any in-flight discovery."""
        self.url = url
        self.query_one('#model-status', Static).update('Listing installed models…')
        self._revision += 1
        revision = self._revision
        self.run_worker(self._load(url, revision), group='model-list', exclusive=True)

    async def _load(self, url, revision):
        try:
            names = await list_models(url)
        except Exception:
            names = None
        # DOM replacement belongs to this widget's serial message pump, not
        # the cancellable HTTP worker. A URL edit can cancel discovery without
        # leaving an unmounted field halfway through replacement.
        self.call_next(self._show_models, names, revision)

    async def _show_models(self, names, revision):
        if revision != self._revision or not self.is_mounted:
            return
        if names is None:
            control = self.query_one('#model-value')
            if isinstance(control, Select):
                value = self.value
                self.initial_value = value
                focused = control.has_focus
                await control.remove()
                control = CommandInput(value, id='model-value')
                await self.mount(control, before=self.query_one('#model-status'))
                if focused:control.focus()
            self.query_one('#model-status', Static).update("Couldn't list models · enter a model name")
            return
        if revision != self._revision or not self.is_mounted:
            return
        control = self.query_one('#model-value')
        current = self.value
        # Don't replace a field in the middle of an edit. A URL change/reopen
        # can refresh it later; preserve what the owner is typing now.
        if isinstance(control, CommandInput) and control.editing:
            self.query_one('#model-status', Static).update('Model list ready · reopen to choose')
            return
        choices = []
        if self.use_default:
            choices.append((f'Options default ({self.default_model or "not set"})', ''))
        else:
            choices.append(('Choose an installed model', ''))
            if not current and len(names) == 1:
                current = names[0]
        choices.extend((name, name) for name in names)
        if current and current not in names:
            choices.append((f'{current} (not installed)', current))
        self.initial_value = current
        focused = control.has_focus
        if isinstance(control, Select):
            control.set_options(choices)
            control.value = current
        else:
            await control.remove()
            control = Select(choices, value=current, allow_blank=False, id='model-value')
            await self.mount(control, before=self.query_one('#model-status'))
        if focused:control.focus()
        self.query_one('#model-status', Static).update('No installed models' if not names else '')

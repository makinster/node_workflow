"""Production forms and save/reopen behavior. Discovery is stubbed, no network."""
from pathlib import Path
import pytest
from textual.app import App
from textual.widgets import Select
from backend.configuration_manager import DEFAULT_SETTINGS
from backend.integrations.claude import MODELS
from frontend.screens.settings import SettingsScreen
from frontend.widgets.command_input import CommandInput
from tests.test_small_wins_ui import Host, make

@pytest.mark.asyncio
async def test_parameters_save_reopen_cancel_and_secret_not_in_workflow():
    factory,wm,node=make('ask_claude_node',input='Question',context='Retained facts')
    app=Host(factory,wm,node)
    async with app.run_test(size=(100,35)) as pilot:
        await pilot.press('2');await pilot.pause()
        select=app.screen.query_one('#field-model',Select)
        assert [v for _,v in select._options]==['Options default',*MODELS]
        assert select.value=='Options default'
        select.value=MODELS[1]
        app.screen.query_one('#field-effort',Select).value='medium'
        app.screen.query_one('#field-context_limit',CommandInput).value='120000'
        await app.screen.action_save_and_stay();await pilot.pause()
        config=wm.get_node_data(node)['config']
        assert config['model']==MODELS[1] and config['effort']=='medium' and config['context_limit']==120000
        assert 'api_key' not in config and config['context']=='Retained facts'
    app=Host(factory,wm,node)
    async with app.run_test(size=(100,35)) as pilot:
        await pilot.pause()
        assert app.screen.query_one('#field-model',Select).value==MODELS[1]
        app.screen.query_one('#field-model',Select).value=MODELS[2]
        # Closing without saving cannot mutate the live workflow config.
    assert wm.get_node_data(node)['config']['model']==MODELS[1]

class Config:
    def get_all(self):return dict(DEFAULT_SETTINGS)
    def get(self,key):return DEFAULT_SETTINGS[key]
class Options(App):
    CSS_PATH=str(Path(__file__).parents[1]/'frontend/styles.tcss')
    def __init__(self):super().__init__();self.saved=[]
    def on_mount(self):self.push_screen(SettingsScreen(Config()),self.saved.append)

@pytest.mark.asyncio
async def test_options_choices_default_and_range(monkeypatch):
    async def no_models(*args,**kwargs):return []
    monkeypatch.setattr('frontend.widgets.local_model_picker.list_models',no_models)
    app=Options()
    async with app.run_test(size=(100,35)) as pilot:
        await pilot.pause()
        model=app.screen.query_one('#setting-claude_model',Select)
        assert [v for _,v in model._options]==list(MODELS) and model.value==MODELS[0]
        field=app.screen.query_one('#setting-claude_context_limit',CommandInput)
        assert field.value=='100000'
        for value in ['999','200001','not a number']:
            field.value=value;app.screen.action_save();await pilot.pause()
            assert not app.saved
        field.value='200000';model.value=MODELS[2]
        app.screen.action_save();await pilot.pause()
        assert app.saved[0]['settings']['claude_context_limit']==200000
        assert app.saved[0]['settings']['claude_model']==MODELS[2]

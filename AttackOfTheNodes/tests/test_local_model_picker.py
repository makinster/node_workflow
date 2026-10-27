"""Read-only picker tests; all HTTP goes to a local fake server."""
import asyncio
from pathlib import Path
from textual.app import App
from textual.widgets import Select, Static
import pytest
from backend.configuration_manager import DEFAULT_SETTINGS
from backend.integrations.local_model import list_models
from frontend.widgets.local_model_picker import LocalModelPicker
from frontend.widgets.command_input import CommandInput
from frontend.screens.settings import SettingsScreen
from tests.test_local_model import server  # canned HTTP fixture, never inference
from tests.test_local_model_ui import make
from tests.test_small_wins_ui import Host


@pytest.fixture
async def discovery(server, monkeypatch):
    monkeypatch.setattr('frontend.widgets.local_model_picker.list_models', list_models)
    return server


async def settled(pilot, picker):
    for _ in range(100):
        if 'Listing' not in str(picker.query_one('#model-status', Static).render()):
            return
        await pilot.pause(.01)
    raise AssertionError('Discovery did not finish')


class Config:
    def __init__(self, url, model=''):
        self.values = {**DEFAULT_SETTINGS, 'local_model_server_url':url, 'local_model_default_model':model}
    def get_all(self):return dict(self.values)
    def get(self, key):return self.values[key]


class Options(App):
    CSS_PATH = str(Path(__file__).parents[1]/'frontend/styles.tcss')
    def __init__(self, config):super().__init__();self.config=config;self.saved=[]
    def on_mount(self):self.push_screen(SettingsScreen(self.config), self.saved.append)


@pytest.mark.asyncio
async def test_node_options_default_override_save_and_reopen(discovery):
    discovery.tags={'models':[{'name':'installed-b:latest'},{'name':'installed-a:latest'}]}
    factory, wm, node = make()
    app=Host(factory,wm,node);app.configuration_manager=Config(discovery.url,'installed-a:latest')
    async with app.run_test() as pilot:
        picker=app.screen.query_one('#field-model', LocalModelPicker)
        await settled(pilot,picker)
        select=picker.query_one(Select)
        assert select._options==[('Options default (installed-a:latest)',''),('installed-a:latest','installed-a:latest'),('installed-b:latest','installed-b:latest')]
        assert picker.value==''
        select.value='installed-b:latest'
        await app.screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['model']=='installed-b:latest'
    app=Host(factory,wm,node);app.configuration_manager=Config(discovery.url,'installed-a:latest')
    async with app.run_test() as pilot:
        picker=app.screen.query_one('#field-model',LocalModelPicker);await settled(pilot,picker)
        assert picker.value=='installed-b:latest'
        picker.query_one(Select).value=''
        await app.screen.action_save_and_stay();await pilot.pause()
        assert wm.get_node_data(node)['config']['model']==''
    assert all(path=='/api/tags' and body is None for path,body,_ in discovery.calls)


@pytest.mark.asyncio
async def test_options_single_autofill_save_and_cancel(discovery):
    app=Options(Config(discovery.url))
    async with app.run_test() as pilot:
        picker=app.screen.query_one(LocalModelPicker);await settled(pilot,picker)
        assert picker.value==discovery.tags['models'][0]['name']
        assert app.config.get('local_model_default_model')==''  # Save is the commit
        await pilot.pause(.35)
        assert len(discovery.calls)==1  # Initial URL event isn't a second lookup
        chosen=picker.value
        app.screen.action_save();await pilot.pause()
        assert app.saved[0]['settings']['local_model_default_model']==chosen
    app=Options(Config(discovery.url))
    async with app.run_test() as pilot:
        await settled(pilot,app.screen.query_one(LocalModelPicker))
        app.screen.action_cancel();await pilot.pause()
        assert app.saved==[None] and app.config.get('local_model_default_model')==''
    assert all(path=='/api/tags' and body is None for path,body,_ in discovery.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize('names',[[],['installed-a:latest','installed-b:latest']])
async def test_options_empty_multiple_do_not_autofill_and_preserve_uninstalled(discovery,names):
    discovery.tags={'models':[{'name':n} for n in names]}
    app=Options(Config(discovery.url))
    async with app.run_test() as pilot:
        picker=app.screen.query_one(LocalModelPicker);await settled(pilot,picker)
        assert picker.value==''
    app=Options(Config(discovery.url,'previous:latest'))
    async with app.run_test() as pilot:
        picker=app.screen.query_one(LocalModelPicker);await settled(pilot,picker)
        assert picker.value=='previous:latest'
        assert ('previous:latest (not installed)','previous:latest') in picker.query_one(Select)._options


@pytest.mark.asyncio
async def test_failure_fallback_text_and_url_change_recovers(discovery):
    discovery.statuses['/api/tags']=503
    app=Options(Config(discovery.url,'previous:latest'))
    async with app.run_test() as pilot:
        picker=app.screen.query_one(LocalModelPicker);await settled(pilot,picker)
        assert "Couldn't list models" in str(picker.query_one('#model-status',Static).render())
        picker.query_one(CommandInput).value='typed:latest'
        discovery.statuses.clear()
        picker.refresh_models(discovery.url);await settled(pilot,picker);await pilot.pause(.05)
        assert picker.value=='typed:latest'
        assert picker.query_one(Select)
        app.screen.action_save();await pilot.pause()
        assert app.saved[0]['settings']['local_model_default_model']=='typed:latest'
    assert all(path=='/api/tags' and body is None for path,body,_ in discovery.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize('problem',['timeout','malformed','redirect','oversize','wrong_shape','cloud'])
async def test_discovery_bounds_and_read_only(discovery,problem):
    if problem=='timeout':discovery.delay['/api/tags']=.2
    if problem=='malformed':discovery.raw['/api/tags']=b'not json'
    if problem=='redirect':discovery.redirect=True
    if problem=='oversize':discovery.raw['/api/tags']=b'x'*(1024*1024+1)
    if problem=='wrong_shape':discovery.tags={'models':'bad'}
    if problem=='cloud':discovery.tags={'models':[{'name':'hosted:cloud'}]}
    with pytest.raises(Exception):await list_models(discovery.url,timeout=.05)
    assert len(discovery.calls)==1 and discovery.calls[0][0:2]==('/api/tags',None)


@pytest.mark.asyncio
async def test_options_changed_url_uses_new_endpoint_and_keyboard(discovery):
    app=Options(Config('http://127.0.0.1:1'))
    async with app.run_test(size=(80,24)) as pilot:
        picker=app.screen.query_one(LocalModelPicker);await settled(pilot,picker)
        app.screen.query_one('#setting-local_model_server_url',CommandInput).value=discovery.url
        await pilot.pause(.4);await settled(pilot,picker)
        select=picker.query_one(Select)
        select.scroll_visible(immediate=True);select.focus();await pilot.press('enter');await pilot.pause()
        assert select.expanded
        await pilot.press('escape');await pilot.pause()
        assert not select.expanded
        assert select in app.screen._nav_widgets()
        assert app.screen.query_one('#save-settings').region.bottom<=24
    assert discovery.calls and all(path=='/api/tags' for path,_,_ in discovery.calls)


@pytest.mark.asyncio
async def test_value_survives_async_control_replacement(discovery,monkeypatch):
    discovery.statuses['/api/tags']=503
    app=Options(Config(discovery.url))
    async with app.run_test() as pilot:
        picker=app.screen.query_one(LocalModelPicker);await settled(pilot,picker)
        picker.query_one(CommandInput).value='typed:latest'
        mounting=asyncio.Event();resume=asyncio.Event();original=picker.mount
        async def paused_mount(*args,**kwargs):
            mounting.set();await resume.wait()
            return await original(*args,**kwargs)
        monkeypatch.setattr(picker,'mount',paused_mount)
        discovery.statuses.clear();picker.refresh_models(discovery.url)
        await asyncio.wait_for(mounting.wait(),2)
        # Form getters/Save may run while Textual removes and mounts controls.
        try:
            assert picker.value=='typed:latest'
            # A URL edit cancels discovery, not an in-progress DOM replacement.
            picker.refresh_models(discovery.url+'/')
            await asyncio.sleep(.01)
        finally:
            resume.set()
        await settled(pilot,picker)
        assert picker.query_one(Select).value=='typed:latest'
    assert all(path=='/api/tags' for path,_,_ in discovery.calls)

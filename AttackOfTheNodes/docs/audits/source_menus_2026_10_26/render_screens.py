"""Before/after captures of real menus and CSS, with isolated synthetic data.

Run before editing and after, passing before/after. No node execution.
Picker discovery after the build uses only a local fake GET /api/tags server.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
DATA = tempfile.TemporaryDirectory(prefix='source-menu-captures-')
os.environ['AOTN_DATA_DIR'] = DATA.name
os.environ.pop('NO_COLOR', None)
os.environ.update(TERM='xterm-256color', COLORTERM='truecolor', TEXTUAL_COLOR_SYSTEM='truecolor')
sys.path.insert(0, str(ROOT / 'AttackOfTheNodes'))
from aiohttp import web
from textual.app import App
from textual.widgets import Select, TabbedContent
from backend.configuration_manager import DEFAULT_SETTINGS
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.settings import SettingsScreen
from tests.source_menu_fixtures import graph

async def main(phase):
    requests = []
    async def tags(request):
        requests.append(f'{request.method} {request.path}')
        return web.json_response({'models': [{'name': 'installed-a:latest'}, {'name': 'installed-b:latest'}]})
    server = web.Application(); server.router.add_get('/api/tags', tags)
    runner = web.AppRunner(server); await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
    url = f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    class Config:
        def get_all(self):return {**DEFAULT_SETTINGS, 'local_model_server_url': url, 'local_model_default_model': 'installed-a:latest'}
        def get(self, key):return self.get_all()[key]
    shots = []
    cases = [('unknown','file_reader_node'), ('collision','check_reply_node'),
             ('child','text_output_node'), ('fanin','file_view_node'),
             ('node-picker','ask_local_model_node'), ('options-picker','ask_local_model_node'),
             ('node-picker-down','ask_local_model_node'), ('options-picker-down','ask_local_model_node'),
             ('node-picker-80','ask_local_model_node'), ('options-picker-80','ask_local_model_node')]
    for name, kind in cases:
        if phase == 'before' and (name == 'fanin' or name.endswith(('-down','-80'))):continue
        factory, wm, mb, node = graph(kind, name if name in ('unknown','collision','child','fanin') else 'unknown')
        class Host(App):
            CSS_PATH = str(ROOT/'AttackOfTheNodes/frontend/styles.tcss')
            def on_mount(self):
                self.configuration_manager = Config()
                if name.endswith('-down'):
                    self.configuration_manager.get_all = lambda: {**DEFAULT_SETTINGS, 'local_model_server_url':'http://127.0.0.1:1', 'local_model_default_model':'installed-a:latest'}
                self.push_screen(SettingsScreen(self.configuration_manager) if name.startswith('options-picker')
                    else NodeConfigScreen(factory, wm, node, wm.get_node_data(node), memory_bank=mb))
        app = Host()
        async with app.run_test(size=(80,24) if name.endswith('-80') else (110,38)) as pilot:
            await pilot.pause(.2)
            if 'picker' in name:
                if name.startswith('node-picker'):
                    app.screen.query_one('#node-config-tabs',TabbedContent).active='node-config-tab-parameters'
                    target = app.screen.query_one('#field-model')
                else: target = app.screen.query_one('#setting-local_model_default_model')
                for _ in range(30):
                    if not target.query('#model-status') or 'Listing' not in str(target.query_one('#model-status').render()):break
                    await pilot.pause(.05)
                target.scroll_visible(immediate=True);await pilot.pause()
                control = target if not target.query('Select, CommandInput') else target.query('Select, CommandInput').first()
            else:
                port = 'file' if kind == 'file_view_node' else 'input'
                control = app.screen.query_one(f'#field-{port}_source',Select)
                if name != 'fanin' and 'Vault' in {value for _, value in control._options}:
                    control.value = 'Vault';await pilot.pause()
                    control = app.screen.query_one(f'#field-{port}_vault_key',Select)
            control.focus();control.scroll_visible(immediate=True);await pilot.pause()
            if isinstance(control,Select):
                control.expanded = True;await pilot.pause()
            path = app.save_screenshot(f'{phase}-{name}.svg',path=str(OUT))
            exported = Path(path)
            exported.write_text('\n'.join(line.rstrip() for line in exported.read_text().splitlines())+'\n')
            shots.append(exported.name)
    await runner.cleanup()
    manifest = {'phase':phase,'screens':shots,'requests':requests,'node_executions':0,
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'AttackOfTheNodes/frontend/screens/node_config.py', ROOT/'AttackOfTheNodes/frontend/screens/settings.py', ROOT/'AttackOfTheNodes/frontend/widgets/form_generator.py', ROOT/'AttackOfTheNodes/frontend/widgets/local_model_picker.py', ROOT/'AttackOfTheNodes/backend/integrations/local_model.py', ROOT/'AttackOfTheNodes/backend/vault_declarations.py', ROOT/'AttackOfTheNodes/backend/nodes/ai/ask_local_model_node.py']},
                'styles_sha256':hashlib.sha256((ROOT/'AttackOfTheNodes/frontend/styles.tcss').read_bytes()).hexdigest()}
    (OUT/f'{phase}-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__ == '__main__':asyncio.run(main(sys.argv[1]))

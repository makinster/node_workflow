"""Capture the registered node and production screens; no network or saves."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile

# The review shell sets NO_COLOR=1 / TERM=dumb. Capture the normal colour
# terminal, not that shell's monochrome override, using the production palette.
os.environ.pop('NO_COLOR', None)
os.environ['TERM'] = 'xterm-256color'
os.environ['COLORTERM'] = 'truecolor'
os.environ['TEXTUAL_COLOR_SYSTEM'] = 'truecolor'
APP = Path(__file__).resolve().parents[3]
os.environ['AOTN_DATA_DIR'] = tempfile.mkdtemp(prefix='pick-screens-')
sys.path.insert(0, str(APP))
from textual.app import App
from textual.widgets import Checkbox
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.editor import EditorScreen
from frontend.screens.node_selector import NodeSelectorScreen

OUT = Path(__file__).resolve().parent
FACTORY = NodeFactory()
WORKFLOW = WorkflowMap(FACTORY, EventBus())
WORKFLOW.create_new('support-router')
start = WORKFLOW.add_node('start_node', alias='Start')
pick = WORKFLOW.add_node('pick_one_node', alias='Which team?')
config = WORKFLOW.get_node_data(pick)['config']
config.update(input_source='Configured', input='Please refund the duplicate charge.',
              question='Which team should handle this message?', api_key_secret='typesafe_key',
              choices=[{'answer':'billing','description':'Payments, refunds and invoices'},
                       {'answer':'bug','description':'Something in the app is broken'},
                       {'answer':'other','description':'Anything else'}])
WORKFLOW.update_node_config(pick, config)
condition = WORKFLOW.add_node('conditional_node', alias='Billing?')
cc = WORKFLOW.get_node_data(condition)['config']
cc.update(condition_type='equals', left_value_source='input', right_value='billing')
WORKFLOW.update_node_config(condition, cc)
yes = WORKFLOW.add_node('end_node', alias='To billing')
no = WORKFLOW.add_node('end_node', alias='Other or unsure')
WORKFLOW.connect(start,'default',pick,'input')
WORKFLOW.connect(pick,'default',condition,'input')
WORKFLOW.connect(condition,'true',yes,'input')
WORKFLOW.connect(condition,'false',no,'input')

class SecretNames:
    def list_keys(self):
        return ['typesafe_key']


async def capture(name, size, mode, keys=(), reveal=None):
    class Host(App):
        CSS_PATH = str(APP / 'frontend/styles.tcss')
        def on_mount(self):
            self.factory = FACTORY
            self.workflow_map = WORKFLOW
            if mode == 'config':
                screen = NodeConfigScreen(FACTORY,WORKFLOW,pick,WORKFLOW.get_node_data(pick),
                                          secrets_manager=SecretNames())
            elif mode == 'selector':
                screen = NodeSelectorScreen(FACTORY)
            else:
                screen = EditorScreen(FACTORY,WORKFLOW)
            self.push_screen(screen)
    app = Host()
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        for key in keys:
            await pilot.press(key)
            await pilot.pause()
        if reveal:
            widget = app.screen.query_one(reveal)
            widget.focus()
            widget.scroll_visible(immediate=True)
            await pilot.pause()
        if mode == 'config':
            for selector in ('#save-node-config','#cancel-node-config'):
                widget = app.screen.query_one(selector)
                assert widget.region.height and widget.region.bottom <= size[1]
        app.save_screenshot(filename=name+'.svg',path=str(OUT))
        shot = OUT / (name + '.svg')
        shot.write_text('\n'.join(line.rstrip() for line in shot.read_text().splitlines()) + '\n')


async def main():
    await capture('parameters', (100,66), 'config', ['2'])
    await capture('parameters-80x24', (80,24), 'config', ['2'], '#field-timeout')
    await capture('source', (100,34), 'config', ['1'])
    await capture('payloads-default', (120,40), 'config', ['3'])
    enabled = WORKFLOW.get_node_data(pick)['config']
    enabled.update(vault_write=True,vault_write_key='chosen_team',
                   details_vault_write=True,details_vault_key='pick_details')
    WORKFLOW.update_node_config(pick, enabled)
    await capture('payloads-enabled', (120,48), 'config', ['3'])
    await capture('payloads-80x24', (80,24), 'config', ['3'], '#vault-output-key-details')
    await capture('selector', (110,30), 'selector', ['5','e'])
    await capture('route-map', (120,34), 'editor', ['s'])

asyncio.run(main())

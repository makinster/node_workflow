"""Registered C3c screens and production CSS; temp data, no execution/install."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.pop('NO_COLOR',None)
os.environ.update(TERM='xterm-256color',COLORTERM='truecolor',TEXTUAL_COLOR_SYSTEM='truecolor')
APP=Path(__file__).resolve().parents[3]
DATA=tempfile.TemporaryDirectory(prefix='c3c-built-screens-')
os.environ['AOTN_DATA_DIR']=DATA.name
sys.path.insert(0,str(APP))
from textual.app import App
from textual.widgets import Checkbox
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from backend.configuration_manager import ConfigurationManager
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.node_selector import NodeSelectorScreen
from frontend.screens.settings import SettingsScreen
from frontend.screens.editor import EditorScreen

OUT=Path(__file__).resolve().parent
FACTORY=NodeFactory()
RID='i_20261023_101400_8d4ae0d12cd840f3891cc7e46ac6409b'


def graph(kind):
    wm=WorkflowMap(FACTORY,EventBus());wm.create_new('Queue incident' if kind=='request' else 'Read finding later')
    start=wm.add_node('start_node')
    selected=wm.add_node('hermes_investigate_node' if kind=='request' else 'hermes_investigation_result_node')
    config=wm.get_node_data(selected)['config']
    if kind=='request':
        config.update(input='Checkout health checks keep failing.\nThe last four checks returned HTTP 503.',
            evidence='10:14 UTC: database connection failed.\nThe workflow gathered this short excerpt.\nCredential values were redacted.',
            investigate='Find the likely cause from these excerpts.\nSeparate evidence from guesses.\nSuggest the next checks without making changes.',
            repeat_key='service:checkout:unhealthy',skip_repeats_minutes=60)
    else:
        config.update(input=RID)
    wm.update_node_config(selected,config)
    wm.connect(start,'default',selected,'input')
    end=wm.add_node('end_node')
    wm.connect(selected,'default',end,'input')
    return wm,selected


MANIFEST=[]
async def capture(kind,view,size=(110,40),variant='default',reveal=None):
    wm,node=graph(kind)
    cfg=wm.get_node_data(node)['config']
    if variant in ('enabled','forwarding'):
        cfg.update(vault_write=True,vault_write_key='investigation_id' if kind=='request' else 'investigation_finding')
        if kind=='result':cfg.update(state_vault_write=True,state_vault_key='investigation_state')
    if variant=='forwarding':cfg.update(dead_drop_passthrough=True,transient_output=False)
    wm.update_node_config(node,cfg)
    original=deepcopy(cfg)
    class Host(App):
        CSS_PATH=str(APP/'frontend/styles.tcss')
        def on_mount(self):
            self.factory=FACTORY;self.workflow_map=wm
            screen=(NodeSelectorScreen(FACTORY) if view=='selector' else SettingsScreen(ConfigurationManager()) if view=='options'
                    else EditorScreen(FACTORY,wm) if view=='workflow' else NodeConfigScreen(FACTORY,wm,node,wm.get_node_data(node)))
            self.push_screen(screen)
    app=Host()
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        if view in ('source','parameters','payloads'):
            await pilot.press({'source':'1','parameters':'2','payloads':'3'}[view]);await pilot.pause()
        if view=='selector':
            await pilot.press('4' if kind=='request' else '1');await pilot.pause()
            entries=app.screen._entries
            target=next(i for i,e in enumerate(entries) if (e['kind']=='group' and e['name']=='Hermes') or (e['kind']=='node' and e['node']['type']=='hermes_investigation_result_node'))
            app.screen.query_one('#node-type-list').index=target
            app.screen.query_one('#node-type-list').focus()
            if entries[target]['kind']=='group':await pilot.press('e')
            await pilot.pause()
        if reveal:
            widget=app.screen.query_one(reveal);widget.focus();widget.scroll_visible(immediate=True);await pilot.pause()
        if view in ('source','parameters','payloads'):
            for selector in ('#save-node-config','#cancel-node-config'):
                widget=app.screen.query_one(selector);assert widget.region.height and widget.region.bottom<=size[1]
        if view=='payloads':
            forward=app.screen.query_one('#dead-drop-passthrough',Checkbox)
            assert forward.value==(variant=='forwarding')
            if variant=='forwarding':assert not app.screen.query_one('#downstream-name-row-default').display
        name=kind+'-'+view+('' if variant=='default' else '-'+variant)+('-80x24' if size==(80,24) else '')
        app.save_screenshot(filename=name+'.svg',path=str(OUT))
        p=OUT/(name+'.svg');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
        assert wm.get_node_data(node)['config']==original
        MANIFEST.append(dict(file=name+'.svg',size=list(size),node=kind,view=view,variant=variant))


async def main():
    for kind in ('request','result'):
        await capture(kind,'source')
        await capture(kind,'parameters',(110,48 if kind=='request' else 27))
        await capture(kind,'parameters',(80,24),reveal='#field-investigate' if kind=='request' else '#field-input')
        await capture(kind,'payloads',(110,42))
        await capture(kind,'payloads',(110,44),'enabled')
        await capture(kind,'payloads',(110,44),'forwarding')
        await capture(kind,'payloads',(80,24),'enabled',reveal='#vault-output-key-default' if kind=='request' else '#vault-output-key-state')
        await capture(kind,'selector',(110,30))
    await capture('request','options',(110,34),reveal='#setting-hermes_investigation_profile_home')
    (OUT/'manifest.json').write_text(json.dumps(MANIFEST,indent=2)+'\n')
    print(f'{len(MANIFEST)} real registered screen captures; routing and geometry checked')

asyncio.run(main())

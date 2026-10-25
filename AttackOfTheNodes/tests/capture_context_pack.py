"""Reproduce real built-screen screenshots; never run the example's services.

From AttackOfTheNodes: python tests/capture_context_pack.py
All application persistence goes to a temporary directory before imports.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
SCRATCH=tempfile.TemporaryDirectory(prefix='context-pack-capture-')
os.environ['AOTN_DATA_DIR']=SCRATCH.name
os.environ.pop('NO_COLOR',None)
os.environ.update(TERM='xterm-256color',COLORTERM='truecolor',TEXTUAL_COLOR_SYSTEM='truecolor')
from textual.app import App
from textual.widgets import Select
from backend import authoring
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.editor import EditorScreen
from frontend.widgets.context_items import ContextItems
from tests.test_small_wins_ui import make,Host

OUT=APP/'docs/screenshots/context-pack'

async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for kind in ('start_node','check_reply_node'):
        f,w,n=make(kind);app=Host(f,w,n)
        async with app.run_test(size=(100,32)) as p:
            await p.pause();await p.press('2');await p.pause()
            rows=list(app.screen.query('.contract-row'))
            if rows:rows[0].focus()
            await p.pause()
            app.save_screenshot(filename=kind+'-after.svg',path=str(OUT))
    factory=NodeFactory()
    spec=json.loads((APP/'examples/context_pack.json').read_text())
    report=authoring.build_workflow(factory,spec)
    assert report['ok'],report['diagnostics']
    wm=WorkflowMap(factory,EventBus());assert wm.load(report['workflow_id'])
    pack=next(n for n,d in wm.get_all_node_data().items() if d['type']=='context_pack_node')
    for view,size in [('parameters',(110,38)),('parameters-80x24',(80,24)),('limits-80x24',(80,24)),('payloads',(80,24)),
                      ('item-text',(80,24)),('workflow',(110,50)),('ask-context',(80,24))]:
        class Built(App):
            CSS_PATH=str(APP/'frontend/styles.tcss')
            def on_mount(self):
                self.factory=factory;self.workflow_map=wm
                if view=='workflow':screen=EditorScreen(factory,wm)
                else:
                    nid=pack
                    if view=='ask-context':
                        for edge in list(wm.get_node_data(pack)['connections']['outputs']):
                            wm.disconnect(pack,edge['source_port'],edge['target_node_id'],edge['target_port'])
                        nid=wm.add_node('hermes_ask_node')
                        wm.connect(pack,'default',nid,'context')
                        wm.update_node_config(nid,{**wm.get_node_data(nid)['config'],'input':'Explain these facts','context_source':'Upstream payload'})
                    screen=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid))
                self.push_screen(screen)
        app=Built()
        async with app.run_test(size=size) as p:
            await p.pause()
            if view.startswith('parameters') or view in ('item-text','limits-80x24'):
                await p.press('2');await p.pause()
                rows=list(app.screen.query('.contract-row'))
                if rows:rows[0].focus()
            if view=='limits-80x24':
                control=app.screen.query_one('#field-max_total')
                control.focus();await p.pause()
                app.screen.query_one('#field-desc-max_total').scroll_visible(animate=False,force=True)
                await p.pause()
            if view=='ask-context':
                control=app.screen.query_one('#field-context_source')
                control.focus();control.scroll_visible(animate=False);await p.pause()
            if view=='item-text':
                field=app.screen.query_one(ContextItems)
                field._open_editor(3);await p.pause()
            if view=='payloads':await p.press('3');await p.pause()
            if view=='workflow':
                from frontend.widgets.node_list import NodeList
                listing=app.screen.query_one(NodeList)
                listing.index=listing.index_for_node_id(pack)
                await p.pause()

            app.save_screenshot(filename=view+'.svg',path=str(OUT))
    if not (OUT/'README.md').exists():
        (OUT/'README.md').write_text('''# Context Pack built screens\n\nReal production screens, captured with `tests/capture_context_pack.py` using\ntemporary application data. Before captures were taken at e0f0dbe, before the solid-role correction.\nSVGs are the original Textual exports; PNGs are viewing companions.\nThe workflow is built from `examples/context_pack.json`; no live service runs.\n''')

if __name__=='__main__':
    asyncio.run(main())
    # Rich emits a whitespace-only SVG line; normalize formatting for Git.
    for screenshot in OUT.glob('*.svg'):
        screenshot.write_text('\n'.join(line.rstrip() for line in screenshot.read_text().splitlines())+'\n')

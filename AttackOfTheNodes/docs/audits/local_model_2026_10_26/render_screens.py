"""Built screen captures: production Textual screens/CSS and registered node metadata.

No execution, writes to a workflow library, live settings, or network requests.
All backend persistence is redirected before imports. No node is executed in this capture harness.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[4]
APP=ROOT/'AttackOfTheNodes'
OUT=Path(__file__).resolve().parent
DATA=tempfile.TemporaryDirectory(prefix='aotn-local-model-design-')
os.environ['AOTN_DATA_DIR']=DATA.name
os.environ.pop('NO_COLOR',None)
os.environ.update(TERM='xterm-256color',COLORTERM='truecolor',TEXTUAL_COLOR_SYSTEM='truecolor')
sys.path.insert(0,str(APP))
from textual.app import App
from textual.widgets import Checkbox
from backend.nodes.ai.ask_local_model_node import AskLocalModelNode
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from backend.event_bus import EventBus
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.node_selector import NodeSelectorScreen
from frontend.screens.editor import EditorScreen
from frontend.screens.settings import SettingsScreen
from backend.configuration_manager import ConfigurationManager
from frontend.widgets.long_text import LongTextPreview, LongTextEditor

QUESTION='''Why did the backup fail? Use only the supplied Context.
Reply as JSON with summary, cause and next_step as text.
Keep each field to one short sentence.
Do not claim that you repaired anything.'''
CONTEXT='''Nightly backup: synthetic example.
Disk free: 0 GB.
Log: ERROR no space left on device.'''

FACTORY=NodeFactory()

def graph():
    wm=WorkflowMap(FACTORY,EventBus());wm.create_new('Local answer to checked notification · BUILT SCREEN')
    def add(kind,alias,**changes):
        nid=wm.add_node(kind,alias=alias)
        cfg=wm.get_node_data(nid)['config'];cfg.update(changes);wm.update_node_config(nid,cfg)
        return nid
    start=add('start_node','Start')
    pack=add('context_pack_node','Context Pack',items=[dict(id='incident',label='Backup facts',source='Configured text',vault_key='',text=CONTEXT)],include_run=False,include_errors=False)
    ask=add('ask_local_model_node','Ask local model (JSON)',input=QUESTION,context_source='Upstream payload',reply_json=True,details_vault_write=True,details_vault_key='local_call')
    check=add('check_reply_node','Check reply',expected_fields=[dict(id=n,name=n,kind='string',required=True) for n in ['summary','cause','next_step']])
    notify=add('hermes_notify_node','Notify me',message='Local backup report: {input}',send_to='home')
    end=add('end_node','End',record_line=False)
    wm.connect(start,'default',pack,'input')
    wm.connect(pack,'default',ask,'context')
    wm.connect(ask,'default',check,'input')
    wm.connect(check,'default',notify,'input')
    wm.connect(notify,'default',end,'input')
    return wm,ask

MANIFEST=[]
async def capture(view,size=(110,38),variant='',reveal=None):
    wm,nid=graph()
    if view!='workflow':wm.update_node_alias(nid,'Ask local model')
    cfg=deepcopy(wm.get_node_data(nid)['config'])
    if variant=='configured-context':cfg.update(context_source='Configured',context=CONTEXT)
    wm.update_node_config(nid,cfg); saved=deepcopy(cfg)
    class Host(App):
        TITLE='AttackOfTheNodes · Ask local model · BUILT SCREEN'
        CSS_PATH=str(APP/'frontend/styles.tcss')
        def on_mount(self):
            self.factory=FACTORY;self.workflow_map=wm
            self.push_screen(SettingsScreen(ConfigurationManager()) if view=='options' else NodeSelectorScreen(FACTORY) if view=='selector' else EditorScreen(FACTORY,wm) if view=='workflow' else NodeConfigScreen(FACTORY,wm,nid,wm.get_node_data(nid)))
    app=Host()
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        if view in ['parameters','editor','payloads','source']:
            await pilot.press({'parameters':'2','editor':'2','payloads':'3','source':'1'}[view]);await pilot.pause()
        if view=='selector':
            await pilot.press('5');await pilot.pause()
            idx=next(i for i,e in enumerate(app.screen._entries) if e['kind']=='node' and e['node']['type']=='ask_local_model_node')
            listing=app.screen.query_one('#node-type-list');listing.index=idx;listing.focus();await pilot.pause()
        if view=='workflow':
            await pilot.press('s','s');await pilot.pause()
        if view in ['parameters','editor']:
            preview=app.screen.query_one('#field-input',LongTextPreview)
            assert preview.value==QUESTION
            preview.focus();await pilot.pause()
            if view=='editor':
                await pilot.press('e');await pilot.pause();assert isinstance(app.screen,LongTextEditor)
        if reveal:
            widget=app.screen.query_one(reveal);widget.focus();widget.scroll_visible(immediate=True,top=True);await pilot.pause()
        if view in ['parameters','payloads','source']:
            for selector in ['#save-node-config','#cancel-node-config']:
                button=app.screen.query_one(selector)
                assert button.region.height and button.region.bottom<=size[1],(view,size,selector)
        if view=='payloads':
            assert not app.screen.query_one('#dead-drop-passthrough',Checkbox).value
            assert app.screen.query_one('#vault-output-key-details').value=='local_call'
        assert wm.get_node_data(nid)['config']==saved
        name=view+('-'+variant if variant else '')+f'-{size[0]}x{size[1]}.svg'
        app.save_screenshot(filename=name,path=str(OUT))
        p=OUT/name;p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
        MANIFEST.append(dict(file=name,view=view,variant=variant,size=list(size),reveal=reveal))
        print(name,flush=True)

async def main():
    for size in [(110,38),(80,24)]:
        await capture('parameters',size)
        await capture('parameters',size,'limits',reveal='#field-reply_json')
        await capture('payloads',size)
        await capture('source',size)
    await capture('parameters',(80,24),'advanced',reveal='#field-max_tokens')
    await capture('payloads',(80,24),'details',reveal='#vault-output-key-details')
    await capture('source',(80,24),'inputs',reveal='#field-context_source')
    await capture('parameters',(110,38),'configured-context')
    await capture('editor',(80,24))
    await capture('selector',(110,34))
    await capture('workflow',(140,44))
    await capture('options',(110,38),reveal='#setting-local_model_server_url')
    await capture('options',(80,24),reveal='#setting-local_model_server_url')
    paths=['frontend/styles.tcss','frontend/colors.py','frontend/widgets/long_text.py','frontend/screens/node_config.py','frontend/screens/node_selector.py','frontend/screens/editor.py','backend/nodes/ai/ask_local_model_node.py','backend/integrations/local_model.py','frontend/screens/settings.py']
    (OUT/'manifest.json').write_text(json.dumps(dict(base='27d16bc0bd956ea0f3a6deac78915000ad0a31e8',branch='codex/ask-local-model',worktree=str(ROOT),registered_node=True,generation_calls=0,screens=MANIFEST,source_sha256={p:hashlib.sha256((APP/p).read_bytes()).hexdigest() for p in paths}),indent=2)+'\n')
    print('Production CSS/screens, real registered node, synthetic example facts. No save/execute/network calls.')
if __name__=='__main__':asyncio.run(main())

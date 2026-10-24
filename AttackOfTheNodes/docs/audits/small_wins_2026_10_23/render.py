"""Capture the built nodes with real screens and CSS; synthetic values only."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
os.environ['AOTN_DATA_DIR']=tempfile.mkdtemp(prefix='small-wins-built-')
os.environ.update(TERM='xterm-256color',COLORTERM='truecolor')
os.environ.pop('NO_COLOR',None)
from textual.app import App
from backend.node_factory import NodeFactory
from backend.event_bus import EventBus
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.node_selector import NodeSelectorScreen
from frontend.screens.editor import EditorScreen
OUT=Path(__file__).resolve().parent
MANIFEST=[]

def graph():
 factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('Latest error → checked report')
 nodes={key:wm.add_node(kind,alias=alias) for key,kind,alias in [
  ('start','start_node','Start'),('find','find_lines_node','Find lines · ERROR'),
  ('read','read_lines_node','Read lines around · last'),('build','concat_node','Build question'),
  ('ask','hermes_ask_node','Ask Hermes'),('check','check_reply_node','Check reply'),
  ('notify','hermes_notify_node','Notify me'),('end','end_node','Done')]}
 for key in ('read','find'):
  wm.update_node_config(nodes[key],{**wm.get_node_data(nodes[key])['config'],'file':'/home/makin/services/checkout/service.log'})
 cfg=wm.get_node_data(nodes['read'])['config'];wm.update_node_config(nodes['read'],{**cfg,'input_source':'Upstream payload','lines_around':True})
 cfg=wm.get_node_data(nodes['ask'])['config'];wm.update_node_config(nodes['ask'],{**cfg,'input_source':'Upstream payload','folder':'/home/makin/services/checkout'})
 cfg=wm.get_node_data(nodes['build'])['config'];wm.update_node_config(nodes['build'],{**cfg,'template':'Analyse the supplied excerpt only.\nReturn one JSON record: summary and next_step as text; cause optional.\n{input}'})
 for a,b in zip(list(nodes.values()),list(nodes.values())[1:]):wm.connect(a,'default',b,'input')
 return factory,wm,nodes

async def capture(kind,view,size=(110,36),variant=''):
 factory,wm,nodes=graph();node=nodes[kind]
 cfg=wm.get_node_data(node)['config']
 if variant=='range':cfg.update(input_source='Configured',lines_around=False)
 if variant=='configured':cfg.update(input_source='Configured',input='{\n  "summary": "The service could not reach its database.",\n  "cause": "Connection failed.",\n  "next_step": "Check database availability."\n}')
 if view=='payloads':
  cfg.update(vault_write=True,vault_write_key={'find':'matching_lines','read':'excerpt','check':'checked_reply'}[kind])
  if kind=='find':cfg.update(match_count_vault_write=True,match_count_vault_key='match_count')
 if variant=='forwarding':cfg.update(dead_drop_passthrough=True)
 wm.update_node_config(node,cfg)
 class Host(App):
  CSS_PATH=str(ROOT/'frontend/styles.tcss')
  def on_mount(self):
   self.factory=factory;self.workflow_map=wm
   self.push_screen(NodeSelectorScreen(factory) if view=='selector' else EditorScreen(factory,wm) if view=='workflow' else NodeConfigScreen(factory,wm,node,wm.get_node_data(node)))
 app=Host()
 async with app.run_test(size=size) as pilot:
  await pilot.pause()
  if view in ('parameters','payloads','source','row-editor','text-editor'):
   await pilot.press('1' if view=='source' else '3' if view=='payloads' else '2');await pilot.pause()
  if view=='payloads' and variant=='count':
   app.screen.query_one('#vault-output-key-match_count').focus();await pilot.pause()
   app.screen.query_one('#vault-output-key-match_count').scroll_visible(immediate=True);await pilot.pause()
  if view=='row-editor':
   app.screen.query_one('#field-expected_fields-row-0').focus();await pilot.press('enter');await pilot.pause()
  if view=='text-editor':
   app.screen.query_one('#field-input').focus();await pilot.press('enter');await pilot.pause()
  if view=='selector':
   await pilot.press('3' if kind=='check' else '1');await pilot.pause()
   entries=app.screen._entries
   index=next(i for i,e in enumerate(entries) if e['kind']=='group' and e['name']=='Text files') if kind!='check' else next(i for i,e in enumerate(entries) if e['kind']=='node' and e['node']['type']=='check_reply_node')
   app.screen.query_one('#node-type-list').index=index
  name=kind+'-'+view+('-'+variant if variant else '')+('-80x24' if size==(80,24) else '')+'.svg'
  app.save_screenshot(filename=name,path=str(OUT))
  p=OUT/name;p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
  MANIFEST.append({'file':name,'size':size,'node':kind,'view':view,'variant':variant})
async def main():
 for kind in ('read','find','check'):
  await capture(kind,'parameters')
  await capture(kind,'parameters',(80,24))
  await capture(kind,'payloads',(110,40))
  await capture(kind,'payloads',(110,40),'forwarding')
  await capture(kind,'selector')
 await capture('find','payloads',(110,40),'count')
 await capture('read','parameters',variant='range')
 await capture('read','source')
 await capture('check','parameters',variant='configured')
 await capture('check','row-editor',(80,24))
 await capture('check','text-editor',(80,24),'configured')
 await capture('check','workflow',(140,68))
 (OUT/'manifest.json').write_text(json.dumps(MANIFEST,indent=2)+'\n')
asyncio.run(main())

"""Real registered nodes and production screens/CSS; no execution, network or saves."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib,json,os,socket,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];APP=ROOT/'AttackOfTheNodes';OUT=Path(__file__).resolve().parent
DATA=tempfile.TemporaryDirectory(prefix='aotn-meta-samples-');os.environ['AOTN_DATA_DIR']=DATA.name
os.environ.pop('NO_COLOR',None);os.environ.update(TERM='xterm-256color',COLORTERM='truecolor',TEXTUAL_COLOR_SYSTEM='truecolor')
sys.path.insert(0,str(APP))
from textual.app import App
from textual.widgets import Checkbox,Select
from backend.node_base import Node
from backend.node_category import NodeCategory
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from backend.event_bus import EventBus
from backend import persistence
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.node_selector import NodeSelectorScreen
from frontend.screens.editor import EditorScreen
from frontend.widgets.node_list import NodeList
from frontend.widgets.long_text import LongTextPreview,LongTextEditor

def refuse(*args,**kwargs):raise AssertionError('Design renderer cannot save or use the network')
socket.socket.connect=refuse;socket.socket.connect_ex=refuse
for name in ['save_workflow','write_json_atomic','save_json_record','delete_workflow']:
 setattr(persistence,name,refuse)
now=lambda:datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
BASE='3f365520730493f1e1ecd24ee592befb23ca5ef5'
SPEC=(OUT/'valid-spec.json').read_text().strip()
REQUEST='Send me a short Ready notification when I run this workflow.'
STANDARD=dict(transient_output=True,dead_drop_passthrough=False,transient_outputs=[],vault_write=False,vault_write_key='',vault_write_description='')
FACTORY=NodeFactory()

def graph():
 wm=WorkflowMap(FACTORY,EventBus());wm.create_new('Composition designer · check only, owner builds later')
 def add(kind,alias,**changes):
  nid=wm.add_node(kind,alias=alias);cfg=wm.get_node_data(nid)['config'];cfg.update(changes);wm.update_node_config(nid,cfg);return nid
 start=add('start_node','Start')
 request=add('user_text_input_node','Request → Vault: request',prompt='What should this workflow do?',membank_outputs=[dict(id='request',output='request',data_type='string')])
 kind=add('ask_local_model_node','Ask local model · kind',input_source='Configured',input='Reply with exactly composition-only, research-needed or unsure. No other text.',context_source='Vault',context_vault_key='request',reply_json=False,vault_write=True,vault_write_key='kind')
 gate=add('conditional_node','Composition-only?',condition_type='equals',left_value_source='input',right_value='composition-only')
 needs_owner=add('end_node','Other kind → owner · stop',record_line=False)
 catalogue=add('node_catalogue_node','Node catalogue · bounded query',scope='Filtered',search='notify',vault_write=True,vault_write_key='catalogue')
 pack=add('context_pack_node','Context Pack · request + catalogue',items=[dict(id='catalogue',label='Available nodes',source='Upstream payload',vault_key='',text=''),dict(id='request',label='Request',source='Vault',vault_key='request',text=''),dict(id='kind',label='Kind',source='Vault',vault_key='kind',text='')],max_item=4000,max_total=6000,include_run=False,include_errors=False)
 draft=add('ask_local_model_node','Ask local model · draft spec JSON',input_source='Configured',input='Draft one aotn-workflow/1 spec using only the supplied contracts. Composition-only requests only.',context_source='Upstream payload',reply_json=True,vault_write=True,vault_write_key='draft_spec')
 checker=add('check_workflow_spec_node','Check workflow spec',input_source='Upstream payload',report_vault_write=True,report_vault_key='spec_check',show_error_path=True)
 end=add('end_node','Checked only · stop for owner',record_line=False)
 problems=add('text_output_node','Problems → revise / stop')
 stop=add('end_node','Stop · no build',record_line=False)
 chain=[start,request,kind]
 for a,b in zip(chain,chain[1:]):wm.connect(a,'default',b,'input')
 wm.connect(kind,'default',gate,'input');wm.connect(gate,'true',catalogue,'input');wm.connect(gate,'false',needs_owner,'input')
 wm.connect(catalogue,'default',pack,'input')
 wm.connect(pack,'default',draft,'context');wm.connect(draft,'default',checker,'input')
 wm.connect(checker,'default',end,'input')
 wm.connect(checker,'error',problems,'input');wm.connect(problems,'default',stop,'input')
 return wm,{'catalogue':catalogue,'check':checker,'draft':draft}
MANIFEST=[]
async def capture(view,size=(120,40),node='catalogue',variant='',reveal=None):
 wm,ids=graph();nid=ids[node];cfg=deepcopy(wm.get_node_data(nid)['config'])
 if view in ['parameters','payloads','source']:
  wm.update_node_alias(nid,FACTORY._node_registry['node_catalogue_node' if node=='catalogue' else 'check_workflow_spec_node'].display_name)
 if node=='check' and view=='parameters':cfg.update(input_source='Configured',input=SPEC)
 if node=='catalogue' and view=='payloads':cfg.update(format='JSON',vault_write=True,vault_write_key='node_catalogue')
 if node=='check' and view=='payloads':cfg.update(vault_write=True,vault_write_key='checked_spec',report_vault_write=True,report_vault_key='spec_check')
 wm.update_node_config(nid,cfg);snapshot=deepcopy(wm.get_all_node_data())
 class Host(App):
  TITLE='AttackOfTheNodes · meta nodes'
  CSS_PATH=str(APP/'frontend/styles.tcss')
  def on_mount(self):
   self.factory=FACTORY;self.workflow_map=wm
   screen=NodeSelectorScreen(FACTORY) if view=='selector' else EditorScreen(FACTORY,wm) if view=='map' else LongTextEditor('Workflow spec did not pass (2 problems).\n\nshow · config.misspelled_config\nUnknown config key.\n\nshow · connections[0].to\nInput port missing_port does not exist.\n\nNo workflow saved. Revise the draft, then check again.',title='Check workflow spec · proposed problem list',read_only=True) if view=='problems' else NodeConfigScreen(FACTORY,wm,nid,wm.get_node_data(nid))
   self.push_screen(screen)
 app=Host()
 async with app.run_test(size=size) as pilot:
  await pilot.pause()
  if view in ['parameters','payloads','source']:
   await pilot.press({'parameters':'2','payloads':'3','source':'1'}[view]);await pilot.pause()
  if view=='selector':
   await pilot.press('3');await pilot.pause()
   entries=app.screen._entries;index=next(i for i,e in enumerate(entries) if e['kind']=='node' and e['node']['type']==('node_catalogue_node' if node=='catalogue' else 'check_workflow_spec_node'))
   listing=app.screen.query_one('#node-type-list');listing.index=index;listing.focus();await pilot.pause()
  if view=='map':
   target=ids['check'] if variant=='gate' else ids['draft'] if variant=='draft' else next(n for n,d in wm.get_all_node_data().items() if d['alias'].startswith('Ask local model · kind'))
   listing=app.screen.query_one(NodeList);index=listing.index_for_node_id(target);assert index is not None
   listing.index=index;app.screen._select_row(listing.row_for_index(index));app.screen._refresh_details();listing.focus();await pilot.pause()
   if variant not in ['overview','']:
    listing.children[index].scroll_visible(animate=False,top=True);await pilot.pause()
   if variant=='overview':listing.scroll_home(animate=False);await pilot.pause()
  if node=='check' and view=='parameters':
   preview=app.screen.query_one('#field-input',LongTextPreview);assert preview.value==SPEC;preview.focus();await pilot.pause()
  if reveal:
   widget=app.screen.query_one(reveal);widget.focus();widget.scroll_visible(immediate=True,top=True);await pilot.pause()
  if view in ['parameters','payloads','source']:
   for selector in ['#save-node-config','#cancel-node-config']:
    button=app.screen.query_one(selector);assert button.region.height>0 and button.region.bottom<=size[1],(view,node,size,selector)
  if view=='payloads':
   assert not any(w.display for w in app.screen.query('#dead-drop-passthrough'))
  if view=='source':
   selector=app.screen.query_one('#field-input_source',Select)
   options=[v for _,v in selector._options if v is not Select.NULL]
   assert options==['Upstream payload','Vault','Configured'],options
   selector.focus();selector.expanded=True;await pilot.pause()
  assert wm.get_all_node_data()==snapshot,'A sample changed its model'
  assert not list(Path(DATA.name).rglob('*')),'Renderer created data-root entries'
  name=f'{node}-{view}'+('-'+variant if variant else '')+f'-{size[0]}x{size[1]}.svg'
  app.save_screenshot(filename=name,path=str(OUT));p=OUT/name;p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
  MANIFEST.append(dict(file=name,view=view,node=node,variant=variant,size=list(size),reveal=reveal,config_preserved=True,library_unchanged=True,config_example={k:v for k,v in cfg.items() if k in ['scope','group_filter','search','detail','format','max_chars','input_source','max_spec','vault_write_key','report_vault_key']}))
  print(name,flush=True)
async def main():
 started=now()
 contracts={t:FACTORY.metadata_for_type(t) for t in ['node_catalogue_node','check_workflow_spec_node']}
 (OUT/'built-node-contracts.json').write_text(json.dumps(dict(design_only=False,registered_in_product=True,base=BASE,nodes=contracts),indent=2)+'\n')
 for size in [(120,40),(80,24)]:
  for node in ['catalogue','check']:
   await capture('parameters',size,node)
   await capture('payloads',size,node)
   await capture('selector',size,node)
 await capture('parameters',(80,24),'catalogue','cap',reveal='#field-max_chars')
 await capture('parameters',(80,24),'catalogue','filters',reveal='#field-tag_filter')
 await capture('payloads',(80,24),'catalogue','vault',reveal='#vault-output-key-default')
 await capture('payloads',(80,24),'check','report',reveal='#vault-output-key-report')
 await capture('source',(80,24),'check')
 await capture('map',(120,40),'check')
 await capture('map',(80,24),'check','head')
 await capture('map',(80,24),'check','gate')
 await capture('map',(120,40),'check','gate')
 await capture('map',(140,110),'check','overview')
 await capture('parameters',(80,24),'catalogue','debug',reveal='#field-include_debug')
 sources=['backend/nodes/data/node_catalogue_node.py','backend/nodes/data/check_workflow_spec_node.py','backend/meta_workflow.py','backend/node_catalogue.py','frontend/styles.tcss','frontend/colors.py','frontend/screens/node_config.py','frontend/screens/node_selector.py','frontend/screens/editor.py','frontend/widgets/long_text.py','frontend/widgets/form_generator.py']
 manifest=dict(schema_version=1,base=BASE,branch='codex/meta-nodes',worktree=str(ROOT),design_only=False,started_at=started,completed_at=now(),screens=MANIFEST,source_sha256={s:hashlib.sha256((APP/s).read_bytes()).hexdigest() for s in sources},workflow_library_writes=0,workflow_executions=0,generation_calls=0,network_calls=0,notes=['Production screens/CSS and real registered product nodes.','The map stops after the checked spec for manual owner review/build; no approval or build node exists.','No styling override or product files changed. PNG conversion substitutes a local monospace font only.'])
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(f'{len(MANIFEST)} SVG samples; no network, execution, library writes or config mutation.')
if __name__=='__main__':asyncio.run(main())

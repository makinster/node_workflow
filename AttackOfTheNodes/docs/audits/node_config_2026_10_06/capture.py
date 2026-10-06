"""Read-only synthetic mounted audit. Run with repository .venv; no external calls.
Writes evidence beside this file; never loads/saves owner workflows or settings.
"""
import asyncio, copy, inspect, json, sys, platform
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from textual.app import App
from textual.widgets import Input, TextArea, Select, SelectionList, Checkbox, Button, Static, TabPane, TabbedContent
from backend.node_factory import NodeFactory
from backend.event_bus import EventBus
from backend.workflow_map import WorkflowMap
from backend.memory_bank import MemoryBank
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.node_selector import NodeSelectorScreen, TABS
import textual
OUT = Path(__file__).parent
class Secrets:
    def list_keys(self): return ['audit_api']
class Harness(App):
    CSS_PATH = str(ROOT / "frontend/styles.tcss")
    def __init__(self, screen, results):
        super().__init__(); self.target = screen; self.results = results
    def on_mount(self): self.push_screen(self.target, self.results.append)
def clean(x):
    if isinstance(x, (str,int,float,bool,type(None))): return x
    if isinstance(x, (tuple,list)): return [clean(v) for v in x]
    if isinstance(x, dict): return {str(k):clean(v) for k,v in x.items()}
    return str(x)
def inventory(screen):
    out=[]
    for w in screen.query('*'):
        if not isinstance(w,(Input,TextArea,Select,SelectionList,Checkbox,Button,Static)): continue
        if any(isinstance(a,(Select,SelectionList)) for a in w.ancestors): continue
        pane=next((a.id for a in w.ancestors if isinstance(a,TabPane)),None)
        row={'id':w.id,'class':type(w).__name__,'tab':pane,'display':w.display,
             'ancestors_visible':all(a.display for a in w.ancestors if not isinstance(a,TabPane)),
             'disabled':w.disabled,'focusable':w.can_focus,'region':list(w.region)}
        if isinstance(w,TextArea): row['value']=w.text
        elif isinstance(w,(Input,Select,Checkbox)): row['value']=clean(w.value)
        if isinstance(w,Select): row['options']=clean(w._options)
        if isinstance(w,SelectionList): row.update(selected=clean(w.selected), options=[{'prompt':str(o.prompt),'value':clean(o.value)} for o in w._options])
        if isinstance(w,(Checkbox,Button)): row['label']=str(w.label)
        elif isinstance(w,Static): row['text']=str(w.content)
        out.append(row)
    return out
async def tabs_snapshot(screen,pilot):
    panes=list(screen.query(TabPane)); result={}
    for i,pane in enumerate(panes):
        screen.action_jump_config_tab(i+1); await pilot.pause(.01)
        result[pane.id]={'title':str(pane._title),'widgets':[w for w in inventory(screen) if w['tab']==pane.id], 'focus_order':[w.id for w in screen._keyboard_focus_widgets()]}
    if not panes: result['flat']={'widgets':inventory(screen),'focus_order':[w.id for w in screen._keyboard_focus_widgets()]}
    return result
def setup(factory,typ):
    wm=WorkflowMap(factory,EventBus()); wm.create_new('synthetic_audit')
    nid=wm.add_node(typ)
    writer=wm.add_node('user_text_input_node'); wm.update_node_config(writer,{'membank_outputs':[{'id':'audit_text','output':'audit_text'}]})
    meta=next(m for m in factory.get_node_types_metadata() if m['type']==typ)
    if meta['input_ports']: wm.connect(writer,'default',nid,meta['input_ports'][0])
    after=wm.add_node('no_op_node')
    if meta['output_ports']: wm.connect(nid,meta['output_ports'][0],after,'input')
    memory=MemoryBank(EventBus())
    for key,val,tag in [('audit_text','synthetic text','string'),('audit_text2','second text','string'),('audit_file','/synthetic/path','file'),('audit_session',{'type':'ai_session','ref_key':'session'},'ai_session')]: memory.store_persistent(key,val,type_tag=tag)
    cfg=copy.deepcopy(wm.get_node_data(nid)['config']);cfg['audit_unrelated']={'retain':True};wm.update_node_config(nid,cfg)
    return wm,nid,memory
async def capture(factory,meta,width):
    typ=meta['type']; wm,nid,memory=setup(factory,typ); results=[]
    original=copy.deepcopy(wm.get_node_data(nid))
    screen=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),memory,Secrets())
    app=Harness(screen,results); data={'type':typ,'width':width,'stylesheet':'frontend/styles.tcss','navigation_method':'action_cursor_down; typing uses Pilot key events'}
    async with app.run_test(size=(width,24)) as pilot:
        await pilot.pause(.01)
        data['default']=await tabs_snapshot(screen,pilot)
        data['chrome']=[w for w in inventory(screen) if w['tab'] is None]
        data['navigation']=[]
        for i,pane in enumerate(screen.query(TabPane)):
            screen.action_jump_config_tab(i+1); await pilot.pause(.01)
            nav=screen._keyboard_focus_widgets()
            if nav:
                app.set_focus(nav[0]); trace=[]
                for _ in range(len(nav)+2):
                    trace.append(app.focused.id if app.focused else None); screen.action_cursor_down(); await pilot.pause(.001)
                data['navigation'].append({'tab':pane.id,'s_trace':trace})
        if width==100:
            data['states']=[]
            # Every schema/select option and both sides of each checkbox, one
            # factor at a time. Related combinations covered by focused suites.
            ids=[w.id for w in screen.query('Select, Checkbox') if w.id]
            for wid in ids:
                w=screen.query_one('#'+wid); before=w.value
                choices=[not before] if isinstance(w,Checkbox) else [v for _,v in w._options if v is not Select.NULL and v!=before]
                for val in choices:
                    try:
                        w.value=val; await pilot.pause(.01)
                        data['states'].append({'control':wid,'requested':clean(val),'actual':clean(w.value),'widgets':inventory(screen)})
                    except Exception as exc: data.setdefault('state_errors',[]).append([wid,clean(val),repr(exc)])
                try: w.value=before
                except Exception: pass
                await pilot.pause(.01)
            if screen.query('#branch-count'):
                screen.query_one('#branch-count',Input).value='5';await pilot.pause(.01)
                data['states'].append({'control':'branch-count','requested':5,'widgets':inventory(screen)})
            if screen.query('#membank-writes'):
                screen.query_one('#membank-writes',Checkbox).value=True
                screen.query_one('#membank-output-count',Input).value='2';await pilot.pause(.05)
                data['states'].append({'control':'membank-output-count','requested':2,'widgets':inventory(screen)})
            # Edit a real field, cancel; stored object must remain equal.
            aliases=list(screen.query('#alias-input'))
            if aliases:
                app.set_focus(aliases[0]); await pilot.press('e','w','s','a','d','2','escape')
                data['typing_value']=aliases[0].value
            screen.action_cancel(); await pilot.pause(.01)
            data['cancel_result']=clean(results)
            data['cancel_unchanged']=wm.get_node_data(nid)==original
        else:
            screen.action_save();await pilot.pause(.01)
            data['save_result']=clean(results)
            data['save_did_not_mutate']=wm.get_node_data(nid)==original
    if width!=100 and results and isinstance(results[-1],dict):
        wm.update_node_config(nid,results[-1]['config'])
        data['unrelated_preserved']=wm.get_node_data(nid)['config'].get('audit_unrelated')=={'retain':True}
        reopened=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),memory,Secrets()); reopened_results=[]
        async with Harness(reopened,reopened_results).run_test(size=(width,24)) as pilot:
            await pilot.pause(.01); data['reopened']=inventory(reopened)
            reopened.action_save();await pilot.pause(.01)
        data['second_save_equal']=bool(reopened_results and reopened_results[-1]==results[-1])
    return data
async def main():
    factory=NodeFactory(); metadata=factory.get_node_types_metadata()
    (OUT/'metadata.json').write_text(json.dumps({'python':platform.python_version(),'textual':textual.__version__,'nodes':metadata},indent=2,default=str)+'\n')
    selector=NodeSelectorScreen(factory);results=[]
    async with Harness(selector,results).run_test(size=(100,24)) as pilot:
        await pilot.pause(.01); selected={}
        for tab in TABS:
            selector._set_active_tab(tab);await pilot.pause(.01)
            selected[tab]=clean(selector._entries)
        (OUT/'selector.json').write_text(json.dumps(selected,indent=2)+'\n')
    for meta in metadata:
        if meta['type']=='tombstone_node': continue
        for width in (60,100,140):
            data=await capture(factory,meta,width)
            (OUT/f"{meta['type']}_{width}.json").write_text(json.dumps(data,indent=2,default=str)+'\n')
            print(meta['type'],width,'captured',flush=True)
if __name__ == "__main__":
    asyncio.run(main())

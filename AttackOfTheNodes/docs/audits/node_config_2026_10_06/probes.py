"""Targeted diagnostics complementing capture.py; synthetic data only."""
import asyncio, copy, json
from pathlib import Path
from capture import Harness, NodeConfigScreen, NodeFactory, WorkflowMap, EventBus, MemoryBank, Secrets, OUT, inventory, setup, Input, Checkbox, Select, SelectionList
from backend.node_base import NodeContext
async def main():
    factory=NodeFactory(); evidence={}
    for typ in ['no_op_node','random_number_node','example_file_instance_node','user_text_input_node','echo_node','repeat_counter_node']:
        memory=MemoryBank(EventBus()); done=[]; errors=[]
        cfg=factory.create_config_template(typ);cfg.update(membank_outputs=[{'id':'promised','output':'promised'}],membank_inputs=['selected_read'],vault_write=True,vault_write_key='standard_promised',file_path='/does/not/exist',file_path_source='Configured',value='IGNORED',max_visits=1)
        async def answer(prompt): return 'answer'
        context=NodeContext(node_id='audit',branch_id='branch',run_id='audit',inputs={'input':{'object':1},'file_path':'/synthetic/path'},memory_bank=memory,signal_done=done.append,signal_error=lambda e:errors.append(str(e)),signal_waiting_for_input=answer,wait_for_nodes=answer,wait_for_merge=answer)
        await factory.create_node(typ,'audit',cfg).execute(context)
        evidence[typ]={'config':cfg,'done':done,'errors':errors,'persistent':memory.get_state()['persistent']}
    for typ,field,value in [('sleep_node','duration','-5'),('random_number_node','min_value','bad'),('chat_completion_node','max_tokens','bad')]:
        wm,nid,mem=setup(factory,typ); results=[]; s=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),mem,Secrets())
        async with Harness(s,results).run_test(size=(60,24)) as p:
            await p.pause(.01);s.query_one('#field-'+field,Input).value=value;s.action_save();await p.pause(.01)
            evidence[typ+'_invalid_save']={'typed':value,'result':results}
    # Render production CSS, focused tab screenshots/text and geometry.
    for typ in ['wait_until_node','chat_completion_node','file_reader_node','sleep_node','text_output_node','example_file_instance_node']:
        for width in [60,100,140]:
            wm,nid,mem=setup(factory,typ);res=[];s=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),mem,Secrets());app=Harness(s,res)
            async with app.run_test(size=(width,24)) as p:
                await p.pause(.01)
                if typ!='wait_until_node': s.action_jump_config_tab(2)
                await p.pause(.01)
                nav=s._keyboard_focus_widgets()
                if nav: app.set_focus(nav[0]);s._scroll_config_widget_into_view(nav[0])
                await p.pause(.01)
                stem=f'render_{typ}_{width}'
                (OUT/(stem+'.svg')).write_text(app.export_screenshot())
                (OUT/(stem+'.txt')).write_text('\n'.join(strip.text for strip in s._compositor.render_strips())+'\n')
                evidence[stem]={'widgets':inventory(s)}
    # Branch seed options require selected legacy Vault declarations.
    for width in (60,100,140):
        wm,nid,mem=setup(factory,'branch_node');cfg=copy.deepcopy(wm.get_node_data(nid)['config']);cfg.update(branch_count=5,membank_inputs=['audit_text']);wm.update_node_config(nid,cfg)
        s=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),mem,Secrets());results=[]
        async with Harness(s,results).run_test(size=(width,24)) as p:
            await p.pause(.01);s.action_jump_config_tab(3);await p.pause(.01)
            sel=s.query_one('#branch-payload-source-path_a',Select)
            evidence[f'branch_vault_{width}']={'options':[(str(a),str(b)) for a,b in sel._options]}
            sel.value='vault:audit_text';await p.pause(.01);s.action_save();await p.pause(.01)
            evidence[f'branch_vault_{width}']['save']=results
    # Populated merge topology plus no-selection and selection/carry states.
    for width in (60,100,140):
        wm=WorkflowMap(factory,EventBus());wm.create_new('audit_merge');start=wm.add_node('start_node');b=wm.add_node('branch_node');m=wm.add_node('merge_node');wm.connect(start,'default',b,'input')
        for port in ['path_a','path_b']:
            n=wm.add_node('no_op_node');beacon=wm.add_node('branch_end_node');wm.connect(b,port,n,'input');wm.connect(n,'default',beacon,'input')
        results=[];s=NodeConfigScreen(factory,wm,m,wm.get_node_data(m));app=Harness(s,results)
        async with app.run_test(size=(width,24)) as p:
            await p.pause(.01);sl=s.query_one('#merge-branches-to-close',SelectionList)
            item={'empty':inventory(s)};sl.select_all();await p.pause(.01);item['selected']=inventory(s)
            app.set_focus(sl);sl.highlighted=0;await p.press('w');item['top_exit']=app.focused.id
            app.set_focus(sl);sl.highlighted=sl.option_count-1;await p.press('s');item['bottom_exit']=app.focused.id
            s.action_save();await p.pause(.01);item['save']=results;evidence[f'merge_{width}']=item
    (OUT/'probes.json').write_text(json.dumps(evidence,indent=2,default=str)+'\n')
    print('Targeted probes complete')
if __name__=='__main__':asyncio.run(main())

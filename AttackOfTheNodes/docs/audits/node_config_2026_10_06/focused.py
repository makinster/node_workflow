"""Production-CSS focus visibility and Chat Completion routing/value probes."""
import asyncio,json
from types import SimpleNamespace
from unittest.mock import patch
from capture import *
from backend.node_base import NodeContext
async def main():
    factory=NodeFactory();out={}
    for typ,field in [('wait_until_node','timeout_seconds'),('text_output_node','template'),('chat_completion_node','temperature')]:
        for width in (60,100,140):
            wm,nid,mem=setup(factory,typ);s=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),mem,Secrets());app=Harness(s,[])
            async with app.run_test(size=(width,24)) as p:
                await p.pause(.02)
                s.action_jump_config_tab(1 if typ=='wait_until_node' else 2);await p.pause(.02)
                field_widget=s.query_one('#field-'+field);app.set_focus(field_widget);s._scroll_config_widget_into_view(field_widget);await p.pause(.1)
                key=f'focus_{typ}_{width}'
                out[key]={'field':list(field_widget.region),'focus':app.focused.id,'widgets':inventory(s)}
                (OUT/(key+'.txt')).write_text('\n'.join(strip.text for strip in s._compositor.render_strips())+'\n')
                (OUT/(key+'.svg')).write_text(app.export_screenshot())
    calls=[]
    def complete(**kwargs):calls.append(kwargs);return SimpleNamespace(ok=True,text='result')
    class SecretValues:
        def get_secret(self,key):return 'synthetic'
    for inputs in [{'context_1':'context-only'}, {'prompt':'prompt-input','document':'document-input'}]:
        done=[];memory=MemoryBank(EventBus())
        async def unused(*args):pass
        cfg=factory.create_config_template('chat_completion_node');cfg.update(prompt='configured',api_key_secret='audit',temperature=0.0,dead_drop_passthrough=True,vault_write=False)
        c=NodeContext('audit','b','r',inputs,memory,done.append,lambda e:None,unused,unused,unused,secrets_manager=SecretValues())
        with patch('backend.nodes.chat_completion_node.get_client',return_value=SimpleNamespace(complete=complete)):
            await factory.create_node('chat_completion_node','audit',cfg).execute(c)
        out['chat_'+str(len(calls))]={'inputs':inputs,'configured_temperature':0.0,'sent_temperature':calls[-1]['temperature'],'done':done}
    (OUT/'focused.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    print('Focused probes complete')
if __name__=='__main__':asyncio.run(main())

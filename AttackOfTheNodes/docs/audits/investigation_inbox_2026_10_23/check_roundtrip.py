import asyncio
from copy import deepcopy
from pathlib import Path
p=Path(__file__).with_name('capture.py')
# Load capture definitions without invoking its capture main.
ns={'__file__':str(p)};exec(p.read_text().split('asyncio.run(main())')[0],ns)
App,NodeConfigScreen=ns['App'],ns['NodeConfigScreen']
async def check(kind):
 wm,node=ns['graph'](kind)
 initial=deepcopy(wm.get_node_data(node)['config']);saved=[]
 class Host(App):
  CSS_PATH=str(ns['APP']/'frontend/styles.tcss')
  def on_mount(self):
   self.push_screen(NodeConfigScreen(ns['FACTORY'],wm,node,wm.get_node_data(node),on_save=self.apply))
  def apply(self,result):
   saved.append(result);wm.update_node_config(node,result['config'])
 host=Host()
 async with host.run_test(size=(100,34)) as pilot:
  await pilot.pause();await pilot.press('3');await pilot.pause()
  checkbox=host.screen.query_one('#dead-drop-passthrough');checkbox.focus()
  await pilot.press('e');await pilot.press('ctrl+s');await pilot.pause()
  assert saved and wm.get_node_data(node)['config']['dead_drop_passthrough'] is True
  assert wm.get_node_data(node)['config'].get('input')==initial.get('input')
  await pilot.press('escape');await pilot.pause()
  host.push_screen(NodeConfigScreen(ns['FACTORY'],wm,node,wm.get_node_data(node),on_save=host.apply));await pilot.pause()
  await pilot.press('3');await pilot.pause();assert host.screen.query_one('#dead-drop-passthrough').value
  host.screen.query_one('#dead-drop-passthrough').focus();await pilot.press('e');await pilot.press('escape');await pilot.pause()
  host.screen.query_one('#unsaved-discard').focus();await pilot.press('enter');await pilot.pause()
  assert wm.get_node_data(node)['config']['dead_drop_passthrough'] is True
  assert len(saved)==1
 print(kind,'keyboard save/reopen/discard preserves input and saved forwarding')
async def main():
 await check('request');await check('result')
asyncio.run(main())

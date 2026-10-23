"""Capture a built Execution screen with a real run and fake subprocess worker."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.pop('NO_COLOR',None)
os.environ.update(TERM='xterm-256color',COLORTERM='truecolor',TEXTUAL_COLOR_SYSTEM='truecolor')
APP=Path(__file__).resolve().parents[3]
DATA=Path(tempfile.mkdtemp(prefix='ask-usage-screen-'))
os.environ['AOTN_DATA_DIR']=str(DATA)
os.environ['HERMES_HOME']=str(DATA/'hermes')
sys.path.insert(0,str(APP))
import pytest
from tests.test_hermes_ask import fake_worker
from backend.run_service import RunService
from backend.run_policies import TerminatePolicy
from frontend.app import AttackOfTheNodesApp
from frontend.screens.execution import ExecutionScreen
from frontend.widgets.node_list import NodeList


async def main():
    with pytest.MonkeyPatch.context() as patch:
        fake_worker(DATA,patch)
        runner=RunService.create()
        for key,value in {'system_node_folders':str(DATA),'hermes_allow_no_budget':True}.items():
            runner.configuration.set(key,value)
        wm=runner.workflow_map
        wm.create_new('one-question')
        start=wm.add_node('start_node',alias='Start')
        ask=wm.add_node('hermes_ask_node',alias='Ask Hermes')
        end=wm.add_node('end_node',alias='Done')
        cfg=wm.get_node_data(ask)['config']
        cfg.update(input='What should I check before release?',folder=str(DATA))
        wm.update_node_config(ask,cfg)
        wm.connect(start,'default',ask,'input');wm.connect(ask,'default',end,'input')
        master=runner.master_state
        app=AttackOfTheNodesApp(runner.event_bus,wm._factory,wm,master._memory_bank,master)
        async with app.run_test(size=(120,38)) as pilot:
            screen=ExecutionScreen(wm,master._memory_bank,master)
            await app.switch_screen(screen)
            await runner.start(recovery_policy=TerminatePolicy('terminate_workflow'))
            await runner.wait()
            await pilot.pause()
            screen.follow=False
            rows=screen.query_one(NodeList)
            rows.index=next(i for i,row in enumerate(rows._rows) if row.get('node_id')==ask)
            await pilot.pause()
            screen._refresh_details()
            app.save_screenshot(filename='usage.svg',path=str(Path(__file__).parent))
            path=Path(__file__).with_name('usage.svg')
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')

asyncio.run(main())

"""Real scheduler pause races and Merge joining obligations from shared analysis."""
import asyncio
from copy import deepcopy

import pytest

from backend.events import NODE_EXECUTION_UPDATE
from tests.test_merge_arrival_runtime import Engine
from tools.draft_trials.case_set_four import case_record, fixture_variants, good_draft
from tools.draft_trials.family_two_engine import run_fixture
from tools.draft_trials import rules_family_two as rules


async def until(predicate):
    async def wait():
        while not predicate():
            await asyncio.sleep(0)
    await asyncio.wait_for(wait(), 3)


def nested(order):
    e = Engine()
    outer = e.add('branch_node')
    inner = e.add('branch_node')
    b = e.step('B', value='B')
    c, d = e.step('C', value='C'), e.step('D', value='D')
    join = e.add('merge_node')
    sink = e.step('sink', sink=True)
    e.wire(e.start, outer)
    inner_port, b_port = ('path_a', 'path_b') if order == 'forward' else ('path_b', 'path_a')
    e.wire(outer, inner, inner_port)
    e.wire(outer, b, b_port)
    e.wire(inner, c, 'path_a'); e.wire(inner, d, 'path_b')
    e.wire(b, join, slot='path_a'); e.wire(c, join, slot='path_b'); e.wire(d, join, slot='path_c')
    e.wire(join, sink)
    e.wm.set_breakpoint(b, True)
    return e, inner, b, c, d, join


@pytest.mark.asyncio
@pytest.mark.parametrize('order', ['forward', 'reverse'])
@pytest.mark.parametrize('action', ['resume', 'stop', 'step'])
async def test_pending_nested_children_obey_breakpoint_pause(order, action):
    e, inner, b, c, d, join = nested(order)
    violations = []
    e.bus.subscribe(NODE_EXECUTION_UPDATE, lambda event: violations.append(event)
                    if event['status'] == 'running' and e.master.state.value == 'PAUSED' else None)
    if action == 'step':
        # Resume must cross B's breakpoint once, then pause at the next node.
        e.wm.set_breakpoint(join, True)
    try:
        assert await e.master.start_workflow()
        await until(lambda: e.master.state.value == 'PAUSED')
        # All scheduled tasks get a turn, including the not-yet-registered batch.
        await until(lambda: len(e.master._supervisors) == len(e.master.run_context.live_supervisors))
        await asyncio.sleep(0)
        assert not violations
        assert not e.entered['B'].is_set() and not e.entered['C'].is_set() and not e.entered['D'].is_set()
        if action == 'stop':
            e.master.stop()
        else:
            e.master.resume()
            if action == 'step':
                await until(lambda: e.master.state.value == 'PAUSED' and e.entered['B'].is_set())
                assert len(e.done(b)) == 1 and not e.done(join)
                e.wm.set_breakpoint(join, False)
                e.master.resume()
        await e.finish()
        assert not violations
        assert len(e.done(join)) == (0 if action == 'stop' else 1)
        assert len(e.seen) == (0 if action == 'stop' else 1)
        assert not e.errors()
    finally:
        e.master.stop()
        await e.master.wait_for_completion()


@pytest.mark.asyncio
@pytest.mark.parametrize('order', ['forward', 'reverse'])
@pytest.mark.parametrize('action', ['resume', 'stop'])
async def test_children_created_while_manually_paused_wait(order, action, monkeypatch):
    e, inner, b, c, d, join = nested(order)
    e.wm.set_breakpoint(b, False)
    entered, release, launched = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original = e.factory.create_node
    def create(kind, node_id, config=None):
        node = original(kind, node_id, config)
        if node_id == inner:
            execute = node.execute
            async def held(context):
                entered.set()
                await release.wait()
                await execute(context)
            node.execute = held
        return node
    monkeypatch.setattr(e.factory, 'create_node', create)
    e.bus.subscribe('SUPERVISOR_REQUEST_BRANCH', lambda event: launched.set()
                    if event['source_node_id'] == inner else None)
    violations = []
    e.bus.subscribe(NODE_EXECUTION_UPDATE, lambda event: violations.append(event)
                    if event['status'] == 'running' and e.master.state.value == 'PAUSED' else None)
    try:
        assert await e.master.start_workflow()
        await asyncio.wait_for(entered.wait(), 3)
        e.master.pause()
        release.set()
        await asyncio.wait_for(launched.wait(), 3)
        await until(lambda: len(e.master._supervisors) == len(e.master.run_context.live_supervisors))
        assert e.master.state.value == 'PAUSED' and not violations
        assert not e.entered['C'].is_set() and not e.entered['D'].is_set()
        getattr(e.master, action)()
        await e.finish()
        assert not violations
        assert len(e.done(join)) == (1 if action == 'resume' else 0)
    finally:
        e.master.stop()
        await e.master.wait_for_completion()


def independent_waiter(root):
    spec = good_draft(1, str(root))
    spec['nodes']['split']['config']['branch_count'] = 3
    spec['nodes']['after_join'] = dict(type='wait_until_node', config=dict(target_node_ids=['join']))
    spec['connections'] += [{'from': 'split.path_c', 'to': 'after_join.input'},
                            {'from': 'after_join.default', 'to': 'end.input'}]
    return spec


@pytest.mark.asyncio
@pytest.mark.parametrize('order', ['forward', 'reverse'])
async def test_independent_waiter_does_not_block_joining_paths(tmp_path, order):
    case = case_record(1, tmp_path)
    spec = independent_waiter(tmp_path)
    variant = fixture_variants(1)[0]
    actual = await run_fixture(spec, case, variant, order=order)
    logical = rules.evaluate(spec, case, variant, order=order)
    assert actual['state'] == logical['state'] == 'finished', (actual, logical)
    assert actual['outputs'] == [row['body'] for row in logical['outputs']] == variant['outputs']
    assert len(logical['collected']) == 1
    assert sum(e['handle'] == 'join' and e['status'] == 'done' for e in actual['events']) == 1
    assert rules.check_rules(spec, case)['result'] == 'pass'


@pytest.mark.parametrize('order', ['forward', 'reverse'])
async def test_required_joining_path_that_fails_still_fails(tmp_path, order):
    case = case_record(1, tmp_path)
    spec = independent_waiter(tmp_path)
    variant = deepcopy(fixture_variants(1)[0])
    # The shared obligations still require both readers, but one file is absent.
    del variant['files']['report-b.txt']
    logical = rules.evaluate(spec, case, variant, order=order)
    actual = await run_fixture(spec, case, variant, order=order)
    assert logical['state'] == 'failed' and logical['errors']
    assert actual['state'] != 'finished' or actual['errors']
    assert not logical['collected']


@pytest.mark.parametrize('order', ['forward', 'reverse'])
def test_lost_required_delivery_cannot_be_treated_as_an_independent_end(tmp_path, order, monkeypatch):
    case = case_record(1, tmp_path)
    spec = independent_waiter(tmp_path)
    original = rules.safety
    def lost_delivery(spec, case):
        nodes, outgoing, analysis = original(spec, case)
        # Fault injection after proof: a required worker ends instead of delivering.
        # The analysis still declares its Merge obligation.
        del outgoing['b.default']
        return nodes, outgoing, analysis
    monkeypatch.setattr(rules, 'safety', lost_delivery)
    result = rules.evaluate(spec, case, fixture_variants(1)[0], order=order)
    assert result['state'] == 'failed' and not result['collected']
    assert 'blocked obligations' in result['errors'][0]

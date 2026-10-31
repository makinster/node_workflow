"""App-style startup enforces shared flow errors before creating a run."""
import pytest

from backend.flow_behaviors import MergePlanError, analyze_flow, merge_plans_from_analysis
from backend.save_manager import SaveManager
from tests.test_merge_arrival_runtime import Engine


def refused_workflow(kind, greeting='yes'):
    e = Engine()
    e.wm.update_node_config(e.start, {'greeting': greeting})
    if kind in ('escape', 'omitted'):
        fork = e.add('branch_node')
        choice = e.add('conditional_node', condition_type='equals', right_value='yes') if kind == 'escape' else e.add('branch_node', condition='string_match', match_value='yes')
        merge = e.add('merge_node')
        a, yes = e.add('echo_node'), e.add('echo_node')
        no = e.add('end_node', record_line=False) if kind == 'escape' else e.add('echo_node')
        show = e.add('text_output_node', label='', template='{input}')
        end = e.add('end_node', record_line=False)
        e.wire(e.start, fork); e.wire(fork, a, 'path_a'); e.wire(a, merge, slot='path_a')
        e.wire(fork, choice, 'path_b')
        e.wire(choice, yes, 'true' if kind == 'escape' else 'path_a')
        e.wire(choice, no, 'false' if kind == 'escape' else 'path_b')
        e.wire(yes, merge, slot='path_b')
        if kind == 'omitted': e.wire(no, merge, slot='path_c')
        e.wire(merge, show); e.wire(show, end)
        code = 'merge_required_path_escape' if kind == 'escape' else 'merge_required_child_omitted'
    else:
        wait = e.add('wait_until_node')
        end = e.add('end_node', record_line=False)
        e.wire(e.start, wait); e.wire(wait, end)
        e.wm.update_node_config(wait, {'target_node_ids': [end if kind == 'impossible' else 'missing-step']})
        code = 'impossible_wait' if kind == 'impossible' else 'wait_target_missing'
    return e, code


@pytest.mark.asyncio
@pytest.mark.parametrize('kind,greeting', [('escape','yes'), ('escape','no'), ('omitted','yes'), ('omitted','no'), ('impossible','yes'), ('missing','yes')])
async def test_app_style_start_refuses_flow_error_without_a_run(kind, greeting):
    e, code = refused_workflow(kind, greeting)
    report = analyze_flow(e.wm.get_all_node_data(), e.factory)
    assert code in {f.code for f in report.findings if f.level == 'error'}
    first = next(f for f in report.findings if f.level == 'error')
    # Exactly the entry point used by App Run: no validator or handwritten plans.
    with pytest.raises(MergePlanError) as caught:
        await e.master.start_workflow(unattended='terminate_branch')
    assert first.message in str(caught.value)
    assert not any(word in str(caught.value).lower() for word in ('lineage', 'shape needs review', 'family'))
    assert e.master.current_run_id is None and e.master.run_context is None
    assert not e.registered and not e.events and not e.master._supervisor_tasks
    assert not e.master.run_outputs and not e.errors()


@pytest.mark.asyncio
async def test_app_run_shows_escape_refusal():
    from frontend.app import AttackOfTheNodesApp
    e, _ = refused_workflow('escape', 'no')
    app = AttackOfTheNodesApp(e.bus, e.factory, e.wm, e.memory, e.master)
    async with app.run_test(size=(100,40), notifications=True) as pilot:
        await pilot.press('ctrl+r'); await pilot.pause(0.3)
        toasts = [t for t in app.screen.query('Toast') if "Can't start:" in t._notification.message]
        assert len(toasts) == 1 and toasts[0].region.width > 0
        assert 'leads away' in toasts[0]._notification.message
        assert e.master.current_run_id is None and not e.registered


@pytest.mark.asyncio
async def test_escaping_child_is_a_typed_subworkflow_error():
    child, _ = refused_workflow('escape', 'no')
    child.wm.set_callable(True)
    SaveManager(child.wm).save_current_workflow()
    parent = Engine()
    call = parent.add('subworkflow_node', workflow_id=child.wm.workflow_id, inputs=[], results=[])
    show = parent.add('text_output_node', label='', template='{input[code]}')
    end = parent.add('end_node', record_line=False)
    parent.wire(parent.start, call); parent.wire(call, end)
    parent.wire(call, show, 'error'); parent.wire(show, end)
    assert await parent.master.start_workflow(unattended='terminate_branch')
    await parent.finish()
    assert len(parent.errors()) == 1
    error = parent.errors()[0]
    assert error['code'] == 'child_flow_invalid' and error['handled']
    assert 'leads away' in error['message']
    assert parent.memory.read_transient(call, 'error')['retryable'] is False
    assert parent.master.run_outputs == ['child_flow_invalid']
    assert parent.master.call_tree.live == 0


def test_adapter_refuses_every_error_code_but_keeps_warnings():
    from backend.flow_behaviors import Finding, FlowAnalysis
    codes = ['flow_needs_review', 'merge_required_path_escape', 'merge_required_child_omitted',
             'repeated_join_unsupported', 'impossible_wait', 'wait_target_missing', 'future_flow_error']
    for code in codes:
        report = FlowAnalysis({}, {}, [Finding('error', code, '', 'Reconnect the missing path.')], [], [])
        with pytest.raises(MergePlanError, match='Reconnect the missing path'):
            merge_plans_from_analysis(report)
        report.findings[0] = Finding('warning', code, '', 'Warning only.')
        assert merge_plans_from_analysis(report) == {}

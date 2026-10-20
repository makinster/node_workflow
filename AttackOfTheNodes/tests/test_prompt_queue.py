"""C19: prompts queue and show one at a time, in arrival order.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_prompt_queue.py -v
"""

from backend.events import USER_INPUT_NEEDED
from frontend.screens.user_input import UserInputScreen
from tests.test_execution_screen import run_screen
from tests.test_execution_status import until


def two_askers(wm):
    """Start → Fan out; Branch 1: Ask A → End A; Branch 2: Ask B → End B."""
    ids = {}
    for name, kind in [("Start", "start_node"), ("Fan out", "branch_node"), ("Ask A", "user_text_input_node"),
                       ("Ask B", "user_text_input_node"), ("End A", "end_node"), ("End B", "end_node")]:
        ids[name] = wm.add_node(kind, alias=name)
    for name in ("Ask A", "Ask B"):
        wm.update_node_config(ids[name], {**wm.get_node_data(ids[name])["config"], "prompt": f"{name}?"})
    for source, port, target in [("Start", "default", "Fan out"), ("Fan out", "path_a", "Ask A"),
                                 ("Ask A", "default", "End A"), ("Fan out", "path_b", "Ask B"),
                                 ("Ask B", "default", "End B")]:
        wm.connect(ids[source], port, ids[target], "input")
    return ids


def asked(master):
    """Prompts in the order the backend asked them."""
    order = []
    master._event_bus.subscribe(USER_INPUT_NEEDED, lambda payload: order.append(payload["prompt"]))
    return order


def test_parallel_prompts_are_shown_one_after_another_in_arrival_order():
    async def steps(app, screen, pilot, master, ids):
        order = asked(master)
        await master.start_workflow()
        await until(lambda: len(order) == 2)
        shown = []
        for answer in ("one", "two"):
            await until(lambda: isinstance(app.screen, UserInputScreen))
            prompt = app.screen
            shown.append(prompt.prompt)
            prompt.dismiss({"branch_id": prompt.branch_id, "value": answer})
            await pilot.pause(0.05)
        await master.wait_for_completion()
        await pilot.pause(0.05)
        return order, shown, isinstance(app.screen, UserInputScreen), master.state.value

    order, shown, still_asking, final = run_screen(two_askers, steps)
    assert sorted(order) == ["Ask A?", "Ask B?"]
    assert shown == order
    assert not still_asking and final == "FINISHED"


def test_a_stopped_runs_queued_prompt_is_not_shown():
    async def steps(app, screen, pilot, master, ids):
        order = asked(master)
        await master.start_workflow()
        await until(lambda: len(order) == 2)
        await until(lambda: isinstance(app.screen, UserInputScreen))
        prompt = app.screen
        master.stop()
        await master.wait_for_completion()
        prompt.dismiss({"branch_id": prompt.branch_id, "value": "late"})
        await pilot.pause(0.05)
        return isinstance(app.screen, UserInputScreen), list(app._user_input_requests)

    still_asking, queued = run_screen(two_askers, steps)
    assert not still_asking and queued == []


def test_a_new_run_drops_prompts_queued_by_the_last_one():
    async def steps(app, screen, pilot, master, ids):
        order = asked(master)
        await master.start_workflow()
        await until(lambda: len(order) == 2)
        queued = len(app._user_input_requests)
        app._reset_run_display_state()
        return queued, list(app._user_input_requests)

    queued, after = run_screen(two_askers, steps)
    assert queued == 1 and after == []

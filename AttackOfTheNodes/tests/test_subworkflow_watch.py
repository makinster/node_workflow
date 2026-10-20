"""Step 4c-2: watching a running subworkflow from the Execution screen, and
prompts that say who asks (owner-approved samples, 2026-10-20).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_subworkflow_watch.py -v
"""

from backend.events import (
    NODE_EXECUTION_UPDATE,
    SUBWORKFLOW_RUN_ENDED,
    SUBWORKFLOW_RUN_UPDATE,
    WORKFLOW_STATE_UPDATE,
)
from frontend.child_runs import ChildRuns
from frontend.screens.execution import ExecutionScreen
from frontend.screens.user_input import UserInputScreen
from frontend.widgets.node_list import NodeList
from frontend.widgets.status_bar import StatusBar
from tests.test_execution_screen import card_for, run_screen
from tests.test_execution_status import until
from tests.test_subworkflow_calls import Flow, _isolated, row  # noqa: F401


def greeter():
    return (Flow("Greeter", callable_=True)
            .node("start", "start_node", rows=[row("who", value="Kim", to="Downstream")])
            .node("ask", "user_text_input_node", alias="Ask name", prompt="Who is this greeting for?")
            .node("end", "end_node", return_end=True, results=[])
            .link("start", "ask", "end").save())


def calling(child_id):
    def build(wm):
        ids = {"start": wm.add_node("start_node", alias="Start"),
               "greet": wm.add_node("subworkflow_node", alias="Greet"),
               "end": wm.add_node("end_node", alias="Done")}
        wm.update_node_config(ids["greet"], {**wm.get_node_data(ids["greet"])["config"], "workflow_id": child_id})
        wm.connect(ids["start"], "default", ids["greet"], "input")
        wm.connect(ids["greet"], "default", ids["end"], "input")
        return ids
    return build


def hint(screen):
    return str(screen.query_one(StatusBar).render()).strip()


# -- the backend forwards a call's run events, then says it ended ------------------------

def test_child_runs_follow_forwarded_events_and_drop_ended_calls():
    calls = ChildRuns()
    wrap = {"invocation_id": "call_1", "parent_run_id": "root_run", "call_site_node_id": "greet",
            "call_path": ["Main", "Greet", "Greeter"]}
    calls.update({**wrap, "event": WORKFLOW_STATE_UPDATE, "payload": {"run_id": "child", "state": "RUNNING"}})
    calls.update({**wrap, "event": NODE_EXECUTION_UPDATE, "payload": {
        "run_id": "child", "branch_id": "b1", "node_id": "ask", "visit_index": 1, "attempt_index": 1,
        "status": "waiting"}})
    assert [c.node_statuses for c in calls.at("root_run", "greet")] == [{"ask": "waiting"}]
    assert calls.at("other_run", "greet") == []
    calls.ended({"invocation_id": "call_1"})
    assert calls.calls == {}


# -- on screen -------------------------------------------------------------------------------

def test_open_a_waiting_subworkflow_see_who_asks_and_go_back():
    child_id = greeter()

    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow()
        await until(lambda: any(call.waiting for call in app.child_runs.calls.values()))
        await until(lambda: isinstance(app.screen, UserInputScreen))
        prompt = app.screen
        asked = (str(prompt.query_one(".modal-title").render()), str(prompt.query_one("#user-input-from").render()))
        branch_id = prompt.branch_id
        app.pop_screen()
        app._user_input_modal_open = False
        await pilot.pause(0.05)
        app.flush_refresh()
        await pilot.pause(0.05)
        node_list = screen.query_one(NodeList)
        node_list.index = node_list.index_for_node_id(ids["greet"])
        node_list.focus()
        screen.follow = False
        screen.refresh_from_backend()
        await pilot.pause(0.05)
        parent = (card_for(screen, ids["greet"]).display_text, str(screen.query_one("#execution-details").render()),
                  hint(screen))
        await pilot.press("enter")
        await pilot.pause(0.1)
        inside = app.screen
        child_view = (isinstance(inside, ExecutionScreen) and inside.call is not None,
                      str(inside.query_one("#execution-title").render()), hint(inside))
        ask_id = inside.workflow_map.find_node_by_alias("Ask name") if hasattr(
            inside.workflow_map, "find_node_by_alias") else next(
            nid for nid, n in inside.workflow_map.get_all_node_data().items() if n.get("alias") == "Ask name")
        child_card = card_for(inside, ask_id).display_text
        await pilot.press("escape")
        await pilot.pause(0.05)
        back = app.screen is screen
        master.submit_user_input(branch_id, "Kim")
        await master.wait_for_completion()
        await pilot.pause(0.05)
        return asked, parent, child_view, child_card, back, dict(app.child_runs.calls), master.state.value

    asked, parent, child_view, child_card, back, live, final = run_screen(calling(child_id), steps)
    assert asked == ("Greeter asks", "From execution_status › Greet › Greeter › Ask name")
    card, details, parent_hint = parent
    assert "⏸ waiting for you" in card
    assert "⏸ Greeter is waiting for you at Ask name" in details and "e/enter  open it" in details
    assert parent_hint.startswith("e/enter open subworkflow")
    is_call, title, child_hint = child_view
    assert is_call and title.startswith("execution_status › Greet › Greeter")
    assert child_hint.startswith("esc back to execution_status (the run keeps going)") and "x stop all" in child_hint
    assert "⏸ waiting for you" in child_card
    assert back and live == {} and final == "FINISHED"


def test_e_shows_errors_away_from_a_subworkflow_card():
    shown = []

    async def steps(app, screen, pilot, master, ids):
        screen.action_errors = lambda: shown.append("errors")
        node_list = screen.query_one(NodeList)
        node_list.index = node_list.index_for_node_id(ids["start"])
        await pilot.press("e")
        await pilot.press("enter")
        return app.screen is screen

    assert run_screen(calling("missing"), steps) and shown == ["errors"]


def test_a_long_breadcrumb_is_shortened_to_fit():
    from frontend.child_runs import ChildRun

    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen.call = ChildRun("call_1", "r", "n", ["Monthly finance report", "Gather invoices", "Invoice collector",
                                               "Parse each invoice", "Invoice parser", "Clean fields", "Tidy text"])
    short = screen._breadcrumbs(60).plain
    assert short.startswith("Monthly finance report › … ›") and short.endswith("Tidy text   (level 3)")
    assert len(short) <= 60
    assert screen._breadcrumbs(400).plain.count(" › ") == 6


def test_forwarded_events_reach_the_root_bus():
    from tests.test_subworkflow_calls import caller, configured, run, slow_greeter

    seen = []

    async def watch(service):
        service.subscribe(SUBWORKFLOW_RUN_UPDATE, lambda p: seen.append(("update", p["event"], p["invocation_id"])))
        service.subscribe(SUBWORKFLOW_RUN_ENDED, lambda p: seen.append(("ended", None, p["invocation_id"])))

    result, _ = run(caller(slow_greeter(0.05), [configured("who", "Kim")]), during=watch)
    assert result.final_state == "FINISHED"
    events = {event for kind, event, _ in seen if kind == "update"}
    assert {WORKFLOW_STATE_UPDATE, NODE_EXECUTION_UPDATE} <= events
    assert seen[-1][0] == "ended" and len({inv for _, _, inv in seen}) == 1


# -- #94 review fixes (2026-10-20) -------------------------------------------------------------

def _call(calls, invocation, run_id, parent_run_id, node_id, path, waiting=False):
    wrap = {"invocation_id": invocation, "parent_run_id": parent_run_id, "call_site_node_id": node_id,
            "call_path": path}
    calls.update({**wrap, "event": WORKFLOW_STATE_UPDATE, "payload": {"run_id": run_id, "state": "RUNNING"}})
    if waiting:
        from backend.events import SUPERVISOR_STATE_UPDATE

        calls.update({**wrap, "event": SUPERVISOR_STATE_UPDATE, "payload": {
            "run_id": run_id, "branch_id": f"b_{run_id}", "state": "WAITING_FOR_INPUT", "current_node_id": "ask"}})
    return calls.calls[invocation]


def test_waiting_follows_run_ids_through_two_levels_and_parallel_calls():
    calls = ChildRuns()
    outer_1 = _call(calls, "i1", "run_o1", "root", "call_a", ["Main", "Call", "Outer"])
    outer_2 = _call(calls, "i2", "run_o2", "root", "call_b", ["Main", "Call", "Outer"])
    greeter = _call(calls, "i3", "run_g2", "run_o2", "inner", ["Main", "Call", "Outer", "Inner", "Greeter"],
                    waiting=True)
    assert calls.waiting_inside(outer_2) is greeter      # two levels down
    assert calls.waiting_inside(outer_1) is None         # same names, different run: not waiting
    assert [c.invocation_id for c in calls.children_of("root")] == ["i1", "i2"]


def test_enter_on_a_focused_error_panel_button_still_presses_it():
    from tests.test_execution_screen import fan_with_failure

    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow()
        await until(lambda: bool(screen.pending_recoveries))
        app.flush_refresh()
        await pilot.pause(0.05)
        screen.query_one("#recover-SKIP").focus()
        await pilot.press("enter")
        await master.wait_for_completion()
        return screen.pending_recoveries

    assert run_screen(fan_with_failure, steps) == []


def test_e_shows_errors_on_a_subworkflow_card_whose_call_is_not_running():
    shown = []

    async def steps(app, screen, pilot, master, ids):
        screen.action_errors = lambda: shown.append("errors")
        node_list = screen.query_one(NodeList)
        node_list.index = node_list.index_for_node_id(ids["greet"])
        screen._selected = ("node", ids["greet"])
        await pilot.pause(0.05)
        await pilot.press("e")
        return True

    assert run_screen(calling("missing"), steps) and shown == ["errors"]


def test_a_breadcrumb_that_cannot_fit_shortens_its_names():
    from frontend.child_runs import ChildRun

    screen = ExecutionScreen.__new__(ExecutionScreen)
    screen.call = ChildRun("call_1", "r", "n", ["A very long monthly finance report workflow name", "Call",
                                               "An equally long invoice parser subworkflow name"])
    short = screen._breadcrumbs(40)
    assert short.cell_len <= 40 and "(level 1)" in short.plain and "…" in short.plain

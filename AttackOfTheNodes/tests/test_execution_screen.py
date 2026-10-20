"""EX: the Execution screen overhaul (owner-approved samples, 2026-10-19).

The run on the editor's map with a status line per card; the highlighted
node's details; following the run; A/D; the error panel (V, Go to node);
Stop on X; the Vault log with who wrote each value.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_execution_screen.py -v
"""

import asyncio

from backend.memory_bank import MemoryBank
from backend.event_bus import EventBus
from frontend.screens.execution import ExecutionScreen
from frontend.screens.vault_log import VaultEntryScreen, VaultLogScreen, shorten
from frontend.widgets.node_card import NodeCard
from frontend.widgets.node_list import NodeList
from tests.test_execution_status import make_app, until


def fan_with_failure(wm, pause=0.4):
    """Start → Fan out; Branch 1: Keep → Pause → End A; Branch 2: Boom → End B."""
    ids = {}
    for name, kind in [("Start", "start_node"), ("Fan out", "branch_node"), ("Keep", "set_variable_node"),
                       ("Pause", "sleep_node"), ("Boom", "error_node"), ("End A", "end_node"),
                       ("End B", "end_node")]:
        ids[name] = wm.add_node(kind, alias=name)
    wm.update_node_config(ids["Keep"], {**wm.get_node_data(ids["Keep"])["config"], "variable_name": "kept"})
    wm.update_node_config(ids["Pause"], {"duration": pause})
    for source, port, target in [("Start", "default", "Fan out"), ("Fan out", "path_a", "Keep"),
                                 ("Keep", "default", "Pause"), ("Pause", "default", "End A"),
                                 ("Fan out", "path_b", "Boom"), ("Boom", "default", "End B")]:
        wm.connect(ids[source], port, ids[target], "input")
    return ids


def run_screen(build, steps, size=(110, 34)):
    async def go():
        app, master, wm, memory, bus = make_app()
        ids = build(wm)
        async with app.run_test(size=size) as pilot:
            screen = ExecutionScreen(wm, memory, master)
            await app.switch_screen(screen)
            await pilot.pause()
            return await steps(app, screen, pilot, master, ids)
    return asyncio.run(asyncio.wait_for(go(), timeout=20))


def card_for(screen, node_id):
    return next((c for c in screen.query(NodeCard) if c.node_id == node_id), None)


# -- the Vault knows who wrote each value -----------------------------------------------

def test_vault_writes_name_their_node_branch_and_visit():
    def build(wm):
        return fan_with_failure(wm, pause=0.01)

    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow(unattended="terminate_branch")
        await master.wait_for_completion()
        return [w for w in screen.memory_bank.writes()], ids

    writes, ids = run_screen(build, steps)
    assert [(w["key"], w["value"], w["node_id"]) for w in writes] == [("kept", "Workflow started", ids["Keep"])]
    assert writes[0]["branch_id"] and writes[0]["visit"] == 1


def test_vault_log_keeps_each_write_as_written_and_clears_with_the_run():
    bank = MemoryBank(EventBus())
    value = {"n": 1}
    bank.store_persistent("x", value)
    value["n"] = 2
    bank.store_persistent("output_log", ["line"])
    assert [(w["key"], w["value"], w["node_id"]) for w in bank.writes()] == [("x", {"n": 1}, None)]
    bank.clear()
    assert bank.writes() == []


# -- the map, details and follow ------------------------------------------------------------

def test_cards_show_the_run_status_and_the_highlight_follows_the_running_node():
    def build(wm):
        ids = fan_with_failure(wm)
        wm.disconnect(ids["Fan out"], "path_b", ids["Boom"], "input")
        return ids

    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow(unattended="terminate_branch")
        await until(lambda: app.node_statuses.get(ids["Pause"]) == "running")
        app.flush_refresh()
        await pilot.pause(0.05)
        node_list = screen.query_one(NodeList)
        followed = node_list.node_id_for_index(node_list.index)
        running_text = card_for(screen, ids["Pause"]).display_text
        details = str(screen.query_one("#execution-details").render())
        await pilot.press("w")
        moved = node_list.node_id_for_index(node_list.index)
        following_after_move = screen.follow
        await master.wait_for_completion()
        app.flush_refresh()
        await pilot.pause(0.05)
        done_text = card_for(screen, ids["Keep"]).display_text
        return ids, followed, running_text, details, moved, following_after_move, done_text

    ids, followed, running_text, details, moved, following, done_text = run_screen(build, steps)
    assert followed == ids["Pause"]
    assert "▶ running" in running_text
    assert details.startswith("Pause · step 3 · Branch 1")
    assert "Received from the previous node" in details and "Sent to the next node" in details
    assert "Saved to the Vault" in details
    assert moved == ids["Keep"] and following is False
    assert "✓ done" in done_text


def test_a_d_switch_the_path_shown_at_the_branch_above():
    async def steps(app, screen, pilot, master, ids):
        node_list = screen.query_one(NodeList)
        shown_before = ids["Keep"] in [r.get("node_id") for r in node_list._rows]
        node_list.index = node_list.index_for_node_id(ids["Keep"])
        await pilot.press("d")
        await pilot.pause(0.05)
        rows = [r.get("node_id") for r in screen.query_one(NodeList)._rows]
        return shown_before, ids["Boom"] in rows, ids["Keep"] in rows

    assert run_screen(fan_with_failure, steps) == (True, True, False)


def test_x_stops_and_s_moves_down():
    calls = []

    async def steps(app, screen, pilot, master, ids):
        screen.action_stop = lambda: calls.append("stop")
        node_list = screen.query_one(NodeList)
        node_list.index = 0
        await pilot.press("s")
        moved = node_list.index > 0
        await pilot.press("x")
        return moved

    assert run_screen(fan_with_failure, steps) is True
    assert calls == ["stop"]


def test_narrow_terminals_stack_the_details_under_the_map():
    async def steps(app, screen, pilot, master, ids):
        return screen.has_class("narrow")

    assert run_screen(fan_with_failure, steps, size=(70, 30)) is True
    assert run_screen(fan_with_failure, steps, size=(110, 30)) is False


# -- the error panel -------------------------------------------------------------------------

def test_a_failure_opens_the_panel_v_hides_it_and_go_to_node_finds_it():
    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow()
        await until(lambda: bool(screen.pending_recoveries))
        app.flush_refresh()
        await pilot.pause(0.05)
        panel = screen.query_one("#execution-error")
        shown = panel.display
        title = str(screen.query_one("#execution-title").render())
        await pilot.press("v")
        hidden = not panel.display
        hidden_title = str(screen.query_one("#execution-title").render())
        await pilot.press("v")
        screen.query_one("#recover-goto").press()
        await pilot.pause(0.05)
        node_list = screen.query_one(NodeList)
        highlighted = node_list.node_id_for_index(node_list.index)
        after_goto = panel.display
        await pilot.press("v")
        screen.query_one("#recover-SKIP").press()
        await master.wait_for_completion()
        return ids, shown, title, hidden, hidden_title, highlighted, after_goto, screen.pending_recoveries

    ids, shown, title, hidden, hidden_title, highlighted, after_goto, pending = run_screen(fan_with_failure, steps)
    assert shown and "needs you" in title
    assert hidden and "1 error waiting · v to choose" in hidden_title
    assert highlighted == ids["Boom"] and after_goto is False
    assert pending == []  # Skip answered it


def test_off_the_execution_screen_a_failure_still_opens_the_pop_up():
    async def go():
        from frontend.screens.error_details import ErrorDetailsScreen

        app, master, wm, memory, bus = make_app()
        fan_with_failure(wm)
        async with app.run_test() as pilot:
            await pilot.pause()
            await master.start_workflow()
            await until(lambda: isinstance(app.screen, ErrorDetailsScreen))
            master.stop()
            return True
    assert asyncio.run(asyncio.wait_for(go(), timeout=20))


# -- the Vault log ----------------------------------------------------------------------------

def test_the_vault_log_names_the_source_and_opens_an_entry():
    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow(unattended="terminate_branch")
        await master.wait_for_completion()
        app.flush_refresh()
        await pilot.pause(0.05)
        await pilot.press("m")
        await pilot.pause(0.1)
        log = app.screen
        table = log.query_one("#vault-table")
        first = [str(cell) for cell in table.get_row_at(0)]
        await pilot.press("e")
        await pilot.pause(0.1)
        entry = app.screen
        text = str(entry.query_one("#vault-entry").render())
        return isinstance(log, VaultLogScreen), first, isinstance(entry, VaultEntryScreen), text

    is_log, first, is_entry, text = run_screen(fan_with_failure, steps)
    assert is_log and is_entry
    assert first == ["0:00", "kept", "[string]", '"Workflow started"', "S2B1 Keep"]
    assert "Written: 0:00 by S2B1 Keep" in text and "Workflow started" in text


def test_long_values_are_shortened_and_keep_their_quote():
    assert shorten('"' + "x" * 50 + '"', 12) == '"xxxxxxxxx…"'
    assert len(shorten("y" * 50, 12)) == 12


# -- review fixes (#89 review, 2026-10-20) ------------------------------------------------------

def two_paths(wm, first="sleep_node", second="sleep_node"):
    """Start → Fan out; path A: A → End A; path B: B → End B."""
    ids = {}
    for name, kind in [("Start", "start_node"), ("Fan out", "branch_node"), ("A", first), ("B", second),
                       ("End A", "end_node"), ("End B", "end_node")]:
        ids[name] = wm.add_node(kind, alias=name)
    for name, kind in (("A", first), ("B", second)):
        if kind == "sleep_node":
            wm.update_node_config(ids[name], {"duration": 0.6})
    for source, port, target in [("Start", "default", "Fan out"), ("Fan out", "path_a", "A"),
                                 ("A", "default", "End A"), ("Fan out", "path_b", "B"),
                                 ("B", "default", "End B")]:
        wm.connect(ids[source], port, ids[target], "input")
    return ids


def test_vault_cells_show_markup_like_text_as_written():
    async def steps(app, screen, pilot, master, ids):
        writes = [{"seconds": 0, "key": "[b]answer", "type": "string", "value": "[/red]", "node_id": None}]
        await app.push_screen(VaultLogScreen(writes, lambda write: "[i]me"))
        await pilot.pause(0.1)
        return [str(cell) for cell in app.screen.query_one("#vault-table").get_row_at(0)]

    assert run_screen(fan_with_failure, steps) == ["0:00", "[b]answer", "[string]", '"[/red]"', "[i]me"]


def test_narrow_error_panel_keeps_its_buttons_on_screen():
    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow()
        await until(lambda: bool(screen.pending_recoveries))
        app.flush_refresh()
        await pilot.pause(0.1)
        side = screen.query_one("#execution-side").region
        inside = all(side.contains_region(screen.query_one(f"#recover-{name}").region)
                     for name in ("RETRY", "SKIP", "TERMINATE_BRANCH", "goto", "TERMINATE_WORKFLOW", "details"))
        clicked = await pilot.click("#recover-goto")
        await pilot.pause(0.05)
        node_list = screen.query_one(NodeList)
        highlighted = node_list.node_id_for_index(node_list.index)
        master.stop()
        return ids, inside, clicked, highlighted

    ids, inside, clicked, highlighted = run_screen(fan_with_failure, steps, size=(70, 24))
    assert inside and clicked and highlighted == ids["Boom"]


def test_go_to_node_takes_one_route_through_a_loop():
    def build(wm):
        ids = {name: wm.add_node(kind, alias=name) for name, kind in
               [("Start", "start_node"), ("Check", "conditional_node"), ("Boom", "error_node"),
                ("Again", "no_op_node")]}
        for source, port, target in [("Start", "default", "Check"), ("Check", "true", "Boom"),
                                     ("Check", "false", "Again"), ("Again", "default", "Check")]:
            wm.connect(ids[source], port, ids[target], "input")
        return ids

    async def steps(app, screen, pilot, master, ids):
        screen._map.active_branch_ports[ids["Check"]] = "false"
        screen.go_to_node(ids["Boom"])
        node_list = screen.query_one(NodeList)
        return ids, screen._map.active_branch_ports[ids["Check"]], node_list.node_id_for_index(node_list.index)

    ids, port, highlighted = run_screen(build, steps)
    assert port == "true" and highlighted == ids["Boom"]


def test_f_follows_a_running_node_on_a_path_not_shown():
    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow(unattended="terminate_branch")
        await until(lambda: {app.node_statuses.get(ids["A"]), app.node_statuses.get(ids["B"])} == {"running"})
        app.flush_refresh()
        await pilot.pause(0.05)
        node_list = screen.query_one(NodeList)
        followed = node_list.node_id_for_index(node_list.index)
        await pilot.press("d")
        await pilot.pause(0.05)
        hidden = followed not in [r.get("node_id") for r in node_list._rows]
        await pilot.press("f")
        await pilot.pause(0.05)
        after = node_list.node_id_for_index(node_list.index)
        master.stop()
        return followed, hidden, after, app.node_statuses.get(after)

    followed, hidden, after, status = run_screen(two_paths, steps)
    assert hidden and after == followed and status == "running"


def test_live_selector_and_saved_paths_row_keep_separate_highlights():
    screen = ExecutionScreen.__new__(ExecutionScreen)
    live = {"kind": "branch_select", "branch_node_id": "b1", "active_port": "path_a"}
    saved = {"kind": "branch_select", "branch_node_id": "b1", "active_port": "__saved_paths__", "saved_paths": True}
    pending = dict(saved, active_port="__unrestored__")
    assert len({screen._row_key(live), screen._row_key(saved), screen._row_key(pending)}) == 3
    assert screen._row_key(dict(live, active_port="path_b")) == screen._row_key(live)


def test_stop_run_clears_every_waiting_choice():
    async def steps(app, screen, pilot, master, ids):
        await master.start_workflow()
        await until(lambda: len(screen.pending_recoveries) == 2)
        app.flush_refresh()
        await pilot.pause(0.05)
        screen.query_one("#recover-TERMINATE_WORKFLOW").press()
        await master.wait_for_completion()
        app.flush_refresh()
        await pilot.pause(0.05)
        return screen.pending_recoveries, str(screen.query_one("#execution-title").render())

    pending, title = run_screen(lambda wm: two_paths(wm, "error_node", "error_node"), steps)
    assert pending == [] and "needs you" not in title

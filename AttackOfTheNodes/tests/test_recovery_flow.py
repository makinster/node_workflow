"""UX4: recovery flow from the originating node (U1, U2, U4, U6–U8)."""

from __future__ import annotations

import asyncio
import json
import os

import pytest

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()
CSS = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.tcss")


def _map():
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("ux4")
    return workflow_map


def _line():
    """start -> HTTP Request -> No Op."""
    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    http = workflow_map.add_node("http_request_node", alias="Fetch")
    after = workflow_map.add_node("no_op_node", alias="After")
    workflow_map.connect(start, "default", http, "input")
    workflow_map.connect(http, "default", after, "input")
    return workflow_map, start, http, after


def _edges(workflow_map):
    edges = set()
    for node_id, node in workflow_map.get_all_node_data().items():
        for conn in node["connections"]["outputs"]:
            edges.add((node_id, conn["source_port"], conn["target_node_id"], conn["target_port"]))
    return edges


def _graph(workflow_map):
    """Nodes (without connection order) and the edge set."""
    nodes = {
        node_id: {k: v for k, v in node.items() if k != "connections"}
        for node_id, node in workflow_map.get_all_node_data().items()
    }
    return json.loads(json.dumps(nodes, sort_keys=True)), _edges(workflow_map)


async def _with_editor(workflow_map, check):
    from textual.app import App

    from frontend.screens.editor import EditorScreen

    editor = EditorScreen(FACTORY, workflow_map)

    class EditorApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(editor)

    app = EditorApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await check(app, editor, pilot)


def _muxes(workflow_map):
    return [n for n, d in workflow_map.get_all_node_data().items() if d["type"] == "error_mux_node"]


# --- Insert, cancel, reopen -------------------------------------------------


def test_catch_errors_inserts_a_mux_inline_and_keeps_the_downstream_on_no_error():
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, start, http, after = _line()

    async def check(app, editor, pilot):
        editor._catch_errors_for(http)
        await pilot.pause()
        [mux] = _muxes(workflow_map)
        assert isinstance(app.screen, NodeConfigScreen) and app.screen.node_id == mux
        assert (http, "default", mux, "input") in _edges(workflow_map)
        assert (mux, "default", after, "input") in _edges(workflow_map)
        assert (http, "default", after, "input") not in _edges(workflow_map)
        # U2: the editor stays on the originating node and the normal path.
        assert editor.selected_node_id == http
        assert editor.active_branch_ports[mux] == "default"

    asyncio.run(_with_editor(workflow_map, check))


def test_cancelling_a_fresh_insertion_leaves_the_graph_identical():
    workflow_map, start, http, after = _line()
    before = _graph(workflow_map)

    async def check(app, editor, pilot):
        editor._catch_errors_for(http)
        await pilot.pause()
        app.screen.action_cancel()
        await pilot.pause()
        assert _graph(workflow_map) == before
        assert editor.selected_node_id == http

    asyncio.run(_with_editor(workflow_map, check))


def test_saving_the_new_mux_keeps_it_and_reopening_finds_the_same_mux():
    from textual.widgets import SelectionList

    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, start, http, after = _line()

    async def check(app, editor, pilot):
        editor._catch_errors_for(http)
        await pilot.pause()
        [mux] = _muxes(workflow_map)
        app.screen.query_one("#mux-recover-from", SelectionList).select("timeout")
        await pilot.pause()
        await pilot.pause()
        app.screen.action_save()
        await pilot.pause()
        config = workflow_map.get_node_data(mux)["config"]
        assert [route["codes"] for route in config["routes"]] == [["timeout"]]

        editor._catch_errors_for(http)
        await pilot.pause()
        assert _muxes(workflow_map) == [mux]
        assert isinstance(app.screen, NodeConfigScreen) and app.screen.node_id == mux
        # Cancelling an existing mux's editor removes nothing.
        app.screen.action_cancel()
        await pilot.pause()
        assert _muxes(workflow_map) == [mux]
        assert (mux, "default", after, "input") in _edges(workflow_map)

    asyncio.run(_with_editor(workflow_map, check))


def test_an_existing_inline_mux_is_reused_only_when_fed_directly():
    from frontend.error_mux_ui import inline_mux_for

    workflow_map, start, http, after = _line()
    assert inline_mux_for(workflow_map, http) is None
    mux = workflow_map.add_node("error_mux_node")
    # Fed through another node: not this node's mux (U7).
    workflow_map.connect(after, "default", mux, "input")
    assert inline_mux_for(workflow_map, http) is None
    assert inline_mux_for(workflow_map, after) == mux


# --- The Errors section widget (U4) -------------------------------------------


async def _config_screen(workflow_map, node_id, check):
    from textual.app import App

    from frontend.screens.node_config import NodeConfigScreen

    screen = NodeConfigScreen(FACTORY, workflow_map, node_id, workflow_map.get_node_data(node_id))

    class ConfigApp(App):
        CSS_PATH = CSS
        result = "unset"

        def on_mount(self):
            self.push_screen(screen, lambda value: setattr(self, "result", value))

    app = ConfigApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await check(app, screen, pilot)
    return app.result


def test_errors_section_lists_friendly_errors_and_offers_to_catch_them():
    workflow_map, start, http, after = _line()

    async def check(app, screen, pilot):
        assert not screen.query("#show-error-path")
        button = screen.query_one("#catch-errors")
        assert str(button.label) == "Add Error Resolver Node"
        assert button.focusable
        listing = str(screen.query_one("#error-definitions").render())
        assert "• [timeout] The server did not answer within the timeout." in listing
        assert "• [http_status] The server answered" in listing
        button.press()
        await pilot.pause()

    result = asyncio.run(_config_screen(workflow_map, http, check))
    assert result["then"] == "catch_errors"
    assert result["config"] == workflow_map.get_node_data(http)["config"]


def test_errors_widget_shows_the_mux_that_catches_the_node():
    workflow_map, start, http, after = _line()
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "a", "label": "A", "codes": ["timeout", "network"]}], "unmatched_route": True})
    workflow_map.disconnect(http, "default", after, "input")
    workflow_map.connect(http, "default", mux, "input")

    async def check(app, screen, pilot):
        button = screen.query_one("#catch-errors")
        assert str(button.label) == "Open Error Resolver Node (3 caught)"
        app.screen.action_cancel()

    asyncio.run(_config_screen(workflow_map, http, check))


def test_a_stored_show_error_path_still_shows_its_path_and_survives_a_save():
    from frontend.error_paths import editor_output_ports

    workflow_map, start, http, after = _line()
    noop = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(noop, {"show_error_path": True})
    assert "error" in editor_output_ports(FACTORY, workflow_map.get_node_data(noop))

    async def check(app, screen, pilot):
        screen.action_save()
        await pilot.pause()

    result = asyncio.run(_config_screen(workflow_map, noop, check))
    assert result["config"]["show_error_path"] is True


def test_error_mux_and_nodes_without_outputs_have_no_catch_widget():
    workflow_map, start, http, after = _line()
    mux = workflow_map.add_node("error_mux_node")
    end = workflow_map.add_node("end_node")

    for node_id in (mux, end):
        async def check(app, screen, pilot):
            assert not screen.query("#catch-errors")
            app.screen.action_cancel()

        asyncio.run(_config_screen(workflow_map, node_id, check))


# --- UX1 Merge identity still holds with an inserted mux ----------------------


def test_merge_keeps_its_branch_after_a_mux_is_inserted_inside_the_branch():
    from frontend.screens.node_config import merge_input_options

    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    merge = workflow_map.add_node("merge_node")
    http = workflow_map.add_node("http_request_node")
    beacon = workflow_map.add_node("branch_end_node")
    workflow_map.connect(start, "default", branch, "input")
    workflow_map.connect(branch, "path_a", merge, "path_a")
    workflow_map.connect(branch, "path_b", http, "input")
    workflow_map.connect(http, "default", beacon, "input")
    workflow_map.connect(beacon, "default", merge, "path_b")
    closure = f"{branch}:path_b"
    workflow_map.update_node_config(merge, {
        "branches_to_close": [closure], "carry_forward_branch_id": closure})

    async def check(app, editor, pilot):
        editor._catch_errors_for(http)
        await pilot.pause()
        app.screen.action_save()
        await pilot.pause()
        [mux] = _muxes(workflow_map)
        assert (mux, "default", beacon, "input") in _edges(workflow_map)
        options = [f"{o['branch_id']}:{o['branch_port']}" for o in merge_input_options(workflow_map, merge)]
        assert options == [closure]
        editor.selected_node_id = merge
        editor._apply_node_config_result(merge, {
            "alias": "Merge", "config": workflow_map.get_node_data(merge)["config"]})
        assert (beacon, "default", merge, "path_b") in _edges(workflow_map)

    asyncio.run(_with_editor(workflow_map, check))


# --- Unpick confirmation (U1, Q6) ---------------------------------------------


def _mux_with_branch():
    """start -> HTTP -> mux; mux.default -> After; mux.slow -> H1 -> H2."""
    workflow_map, start, http, after = _line()
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "slow", "label": "Slow", "codes": ["timeout"], "forward": "failed_input"}]})
    workflow_map.disconnect(http, "default", after, "input")
    workflow_map.connect(http, "default", mux, "input")
    workflow_map.connect(mux, "default", after, "input")
    h1 = workflow_map.add_node("no_op_node", alias="Retry")
    h2 = workflow_map.add_node("no_op_node", alias="Notify")
    workflow_map.connect(mux, "slow", h1, "input")
    workflow_map.connect(h1, "default", h2, "input")
    return workflow_map, http, mux, after, h1, h2


def _unpick_and_choose(choice_button):
    from textual.widgets import SelectionList

    from frontend.screens.recovery_branch_unpick import RecoveryBranchUnpickScreen

    workflow_map, http, mux, after, h1, h2 = _mux_with_branch()
    seen = {}

    async def check(app, editor, pilot):
        editor._catch_errors_for(http)
        await pilot.pause()
        config_screen = app.screen
        config_screen.query_one("#mux-recover-from", SelectionList).deselect("timeout")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, RecoveryBranchUnpickScreen)
        seen["listed"] = str(app.screen.query_one("#unpick-branch-nodes").render())
        app.screen.query_one(choice_button).press()
        await pilot.pause()
        await pilot.pause()
        assert app.screen is config_screen
        seen["picked"] = list(config_screen.query_one("#mux-recover-from", SelectionList).selected)
        seen["rows"] = [row["id"] for row in config_screen._mux_rows]
        config_screen.action_save()
        await pilot.pause()
        seen["placeholders"] = {n for n in (h1, h2) if editor.workflow_adapter.is_placeholder(n)}
        seen["adapter"] = editor.workflow_adapter

    asyncio.run(_with_editor(workflow_map, check))
    return workflow_map, mux, h1, h2, seen


def test_unpick_lists_the_branch_nodes_then_leave_unlinked_keeps_them():
    workflow_map, mux, h1, h2, seen = _unpick_and_choose("#unpick-leave")
    assert "Retry" in seen["listed"] and "Notify" in seen["listed"]
    assert workflow_map.get_node_data(mux)["config"]["routes"] == []
    assert (mux, "slow", h1, "input") not in _edges(workflow_map)
    assert workflow_map.get_node_data(h1) is not None and seen["placeholders"] == set()
    assert (h1, "default", h2, "input") in _edges(workflow_map)


def test_unpick_delete_branch_tombstones_the_nodes_and_undo_works():
    workflow_map, mux, h1, h2, seen = _unpick_and_choose("#unpick-delete")
    assert seen["placeholders"] == {h1, h2}
    assert (mux, "slow", h1, "input") not in _edges(workflow_map)
    assert seen["adapter"].undo_placeholder(h1)


def test_unpick_cancel_picks_the_error_again():
    workflow_map, mux, h1, h2, seen = _unpick_and_choose("#unpick-cancel")
    assert seen["picked"] == ["timeout"]
    assert seen["rows"] == ["slow"]
    route = workflow_map.get_node_data(mux)["config"]["routes"][0]
    assert route == {"id": "slow", "label": "Slow", "codes": ["timeout"], "forward": "failed_input"}
    assert (mux, "slow", h1, "input") in _edges(workflow_map)


def test_delete_branch_stops_at_a_merge_and_at_shared_nodes():
    from frontend.error_mux_ui import branch_nodes_for_port

    workflow_map, http, mux, after, h1, h2 = _mux_with_branch()
    merge = workflow_map.add_node("merge_node")
    shared = workflow_map.add_node("file_output_node")
    beyond = workflow_map.add_node("no_op_node")
    workflow_map.connect(h2, "default", merge, "path_a")
    workflow_map.connect(merge, "default", beyond, "input")
    # `shared` is also reached on the normal path (After -> shared).
    workflow_map.connect(h1, "default", shared, "file_path")
    workflow_map.connect(after, "default", shared, "content")
    assert branch_nodes_for_port(workflow_map, mux, "slow") == [h1, h2]


def test_an_older_any_other_error_branch_shows_ticked_and_can_be_unpicked():
    from frontend.error_mux_ui import ANY_OTHER_ERROR

    workflow_map, http, mux, after, h1, h2 = _mux_with_branch()
    workflow_map.update_node_config(mux, {**workflow_map.get_node_data(mux)["config"],
                                          "unmatched_route": True})
    seen = {}

    async def unpick(screen, pilot):
        from textual.widgets import SelectionList

        picker = screen.query_one("#mux-recover-from", SelectionList)
        seen["options"] = [o.value for o in picker._options]
        seen["selected"] = list(picker.selected)
        picker.deselect(ANY_OTHER_ERROR)
        await pilot.pause()
        await pilot.pause()
        screen.action_save()
        await pilot.pause()

    result = asyncio.run(_config_screen(workflow_map, mux, lambda app, s, p: unpick(s, p)))
    assert seen["options"][-1] == ANY_OTHER_ERROR
    assert ANY_OTHER_ERROR in seen["selected"]
    assert result["config"]["unmatched_route"] is False


def test_mux_picker_shows_code_first_lines_with_brackets_intact():
    from textual.widgets import SelectionList

    workflow_map, start, http, after = _line()
    mux = workflow_map.add_node("error_mux_node")
    workflow_map.disconnect(http, "default", after, "input")
    workflow_map.connect(http, "default", mux, "input")
    seen = {}

    async def check(app, screen, pilot):
        picker = screen.query_one("#mux-recover-from", SelectionList)
        seen["lines"] = [str(picker.get_option_at_index(i).prompt)
                         for i in range(picker.option_count)]
        app.screen.action_cancel()

    asyncio.run(_config_screen(workflow_map, mux, check))
    assert seen["lines"][0] == "[node_error] Any failure the node does not declare more precisely."
    assert "[timeout] The server did not answer within the timeout." in seen["lines"]
    assert not any("Any other error" in line for line in seen["lines"])


# --- a/d cycling skips error recovery (owner, 2026-10-13) ---------------------


def _resolver_with_branches():
    """start -> HTTP -> resolver; No error -> Branch(2) -> A / B;
    recovery 'slow' -> Branch(2) -> R1 / R2."""
    workflow_map, http, mux, after, h1, h2 = _mux_with_branch()
    normal_branch = workflow_map.add_node("branch_node")
    workflow_map.connect(after, "default", normal_branch, "input")
    for port in ("path_a", "path_b"):
        workflow_map.connect(normal_branch, port, workflow_map.add_node("no_op_node"), "input")
    recovery_branch = workflow_map.add_node("branch_node")
    workflow_map.connect(h2, "default", recovery_branch, "input")
    for port in ("path_a", "path_b"):
        workflow_map.connect(recovery_branch, port, workflow_map.add_node("no_op_node"), "input")
    return workflow_map, http, mux, normal_branch, recovery_branch


def test_a_d_cycling_skips_error_paths_and_resolver_recovery_branches():
    from frontend.screens.editor import EditorScreen

    workflow_map, http, mux, normal_branch, recovery_branch = _resolver_with_branches()
    editor = EditorScreen(FACTORY, workflow_map)
    candidates = [(c["branch_node_id"], c["port"]) for c in editor._branch_view_candidates()]
    assert candidates == [(normal_branch, "path_a"), (normal_branch, "path_b")]


def test_a_d_never_switches_the_resolver_and_e_opens_its_branches():
    from frontend.screens.branch_selector import BranchSelectorScreen

    workflow_map, http, mux, normal_branch, recovery_branch = _resolver_with_branches()

    async def check(app, editor, pilot):
        for _ in range(4):
            await pilot.press("d")
            await pilot.pause()
            assert editor.active_branch_ports.get(mux, "default") == "default"
        rows = editor._build_visible_rows()
        [mux_row] = [r for r in rows if r["kind"] == "branch_select" and r["branch_node_id"] == mux]
        editor._open_branch_selector(mux_row)
        await pilot.pause()
        assert isinstance(app.screen, BranchSelectorScreen)
        assert "slow" in app.screen.output_ports
        app.screen.dismiss({"branch_node_id": mux, "branch_port": "slow"})
        await pilot.pause()
        assert editor.active_branch_ports[mux] == "slow"

    asyncio.run(_with_editor(workflow_map, check))


def test_a_d_on_the_resolvers_branch_select_row_cycles_its_branches():
    """Owner, 2026-10-14: with the highlight on a branch-select row, A/D step
    through that node's branches, recovery ones included; E still opens the
    selector (previous test)."""
    workflow_map, http, mux, normal_branch, recovery_branch = _resolver_with_branches()

    async def check(app, editor, pilot):
        rows = editor._build_visible_rows()
        [mux_row] = [r for r in rows if r["kind"] == "branch_select" and r["branch_node_id"] == mux]
        ports = list(mux_row["output_ports"])
        assert "slow" in ports and mux_row["active_port"] == "default"
        editor.selected_node_id = None
        editor.selected_row = {"kind": "branch_select", "branch_node_id": mux,
                               "active_port": "default"}
        editor.refresh_from_backend()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        expected = ports[(ports.index("default") + 1) % len(ports)]
        assert editor.active_branch_ports[mux] == expected
        assert editor.selected_row["kind"] == "branch_select"
        assert editor.selected_row["branch_node_id"] == mux
        await pilot.press("a")
        await pilot.pause()
        assert editor.active_branch_ports[mux] == "default"

    asyncio.run(_with_editor(workflow_map, check))

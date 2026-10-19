"""Owner bug report 2026-10-18 (Test Bench - C1/C2 checks).

1. Inserting a node after Dice lost everything below it: the next node (Pause)
   also had a second parent, so its input looked "occupied" and the insert
   never reconnected it.
2. HTTP Request and JSON Path showed an error path as soon as they were
   added. Errors go to the default handler until the user picks one to
   handle in the node's Errors tab.
3. A node's error path re-coloured the normal path below it.
"""

from __future__ import annotations

import asyncio

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.error_paths import SHOW_ERROR_PATH, editor_output_ports


def _map():
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new("Insert fan-in")
    return factory, workflow_map


def _targets(workflow_map, node_id, port="default"):
    node = workflow_map.get_node_data(node_id) or {}
    return [
        conn["target_node_id"]
        for conn in node["connections"]["outputs"]
        if conn["source_port"] == port
    ]


def test_insert_before_a_node_with_two_parents_keeps_it_downstream():
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    dice = workflow_map.add_node("random_number_node")
    note = workflow_map.add_node("no_op_node")
    pause = workflow_map.add_node("sleep_node")
    workflow_map.connect(dice, "default", pause, "input")
    workflow_map.connect(note, "default", pause, "input")
    http = workflow_map.add_node("http_request_node")
    editor = EditorScreen(factory, workflow_map)

    editor._connect_new_node(dice, "default", http)

    assert _targets(workflow_map, dice) == [http]
    assert _targets(workflow_map, http) == [pause]
    # The other parent is untouched.
    assert _targets(workflow_map, note) == [pause]


def test_http_request_and_json_path_show_no_error_path_until_asked():
    factory, workflow_map = _map()
    for node_type in ("http_request_node", "json_path_node"):
        node_id = workflow_map.add_node(node_type)
        node = workflow_map.get_node_data(node_id)
        assert factory.node_output_ports(node) == ["default"]
        assert editor_output_ports(factory, node) == ["default"]
        workflow_map.update_node_config(node_id, {**node["config"], SHOW_ERROR_PATH: True})
        assert editor_output_ports(factory, workflow_map.get_node_data(node_id)) == [
            "default", "error"]


def _run(node_type, config, inputs=None):
    factory = NodeFactory()
    node = factory.create_node(node_type, "n1")
    node.config.update(config)
    done, errors = [], []
    context = NodeContext(
        node_id="n1", branch_id="b", run_id="r",
        inputs=inputs or {"input": ""}, memory_bank=MemoryBank(EventBus()),
        signal_done=done.append, signal_error=errors.append,
        signal_waiting_for_input=lambda p: None,
        wait_for_nodes=lambda t, timeout: None,
        wait_for_merge=lambda n, b, p, i, timeout: None,
    )
    asyncio.run(node.execute(context))
    return done, errors


def test_http_request_failures_are_coded_node_errors():
    done, errors = _run("http_request_node", {"url": ""})
    assert done == []
    assert isinstance(errors[0], NodeError) and errors[0].code == "missing_url"


def test_json_path_invalid_json_is_a_coded_node_error():
    done, errors = _run("json_path_node", {"path": "a"}, {"input": "{nope"})
    assert done == []
    assert isinstance(errors[0], NodeError) and errors[0].code == "invalid_json"


def test_error_path_keeps_the_normal_path_colour():
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    fan = workflow_map.add_node("branch_node")
    logger = workflow_map.add_node("logger_node")
    after = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", fan, "input")
    workflow_map.connect(fan, "path_a", logger, "input")
    workflow_map.connect(logger, "default", after, "input")
    workflow_map.update_node_config(
        logger, {**workflow_map.get_node_data(logger)["config"], SHOW_ERROR_PATH: True})
    editor = EditorScreen(factory, workflow_map)

    rows = editor._build_visible_rows()
    keys = {row["node_id"]: row["node"].get("_editor_branch_color_key")
            for row in rows if row["kind"] == "node"}
    assert keys[after] == keys[logger]
    selectors = [row for row in rows if row["kind"] == "branch_select"]
    assert selectors[-1]["branch_node_id"] == logger
    assert selectors[-1]["active_color_key"] == keys[logger]

    # The error path itself still gets its own colour.
    editor.active_branch_ports[logger] = "error"
    rows = editor._build_visible_rows()
    error_row = [row for row in rows if row["kind"] == "branch_select"][-1]
    assert error_row["active_color_key"] != keys[logger]


def test_error_mux_no_error_path_keeps_the_normal_path_colour():
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    fan = workflow_map.add_node("branch_node")
    http = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    after = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "r_timeout", "label": "Timeout", "codes": ["timeout"]}]})
    workflow_map.connect(start, "default", fan, "input")
    workflow_map.connect(fan, "path_a", http, "input")
    workflow_map.connect(http, "default", mux, "input")
    workflow_map.connect(mux, "default", after, "input")
    editor = EditorScreen(factory, workflow_map)

    rows = editor._build_visible_rows()
    keys = {row["node_id"]: row["node"].get("_editor_branch_color_key")
            for row in rows if row["kind"] == "node"}
    assert keys[after] == keys[http] == keys[mux]
    editor.active_branch_ports[mux] = "r_timeout"
    error_row = [row for row in editor._build_visible_rows()
                 if row["kind"] == "branch_select"][-1]
    assert error_row["active_color_key"] != keys[http]


def _handled_http():
    """Start → HTTP → Mux; No error → After → End; Timeout → Fix → Fix End."""
    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    http = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    after = workflow_map.add_node("no_op_node")
    end = workflow_map.add_node("end_node")
    fix = workflow_map.add_node("logger_node")
    fix_end = workflow_map.add_node("end_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "r_timeout", "label": "Timeout", "codes": ["timeout"]}]})
    workflow_map.connect(start, "default", http, "input")
    workflow_map.connect(http, "default", mux, "input")
    workflow_map.connect(mux, "default", after, "input")
    workflow_map.connect(after, "default", end, "input")
    workflow_map.connect(mux, "r_timeout", fix, "input")
    workflow_map.connect(fix, "default", fix_end, "input")
    return factory, workflow_map, dict(
        start=start, http=http, mux=mux, after=after, end=end, fix=fix, fix_end=fix_end)


def _delete_in_editor(factory, workflow_map, node_id, button):
    from textual.app import App

    from frontend.screens.confirm import ConfirmScreen
    from frontend.screens.editor import EditorScreen

    class EditorApp(App):
        def compose(self):
            yield EditorScreen(factory, workflow_map)

    async def run():
        app = EditorApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            editor = app.query_one(EditorScreen)
            editor.selected_node_id = node_id
            editor.selected_row = {"kind": "node", "node_id": node_id}
            editor.action_delete_selected()
            await pilot.pause(0.03)
            asked = isinstance(app.screen, ConfirmScreen)
            message = str(app.screen._message) if asked else ""
            if asked:
                await pilot.click(button)
                await pilot.pause(0.03)
            return asked, message, editor.workflow_adapter.is_placeholder(node_id)

    return asyncio.run(run())


def test_deleting_a_node_with_an_error_handler_asks_and_takes_it_along():
    factory, workflow_map, ids = _handled_http()

    asked, message, deleted = _delete_in_editor(factory, workflow_map, ids["http"], "#confirm-yes")

    assert asked and "Error Resolver" in message and "No error continues" in message
    assert deleted
    for gone in ("mux", "fix", "fix_end"):
        assert workflow_map.get_node_data(ids[gone]) is None, gone
    # The blocking group stores its one continuation; it is not a live wire.
    assert _targets(workflow_map, ids["http"]) == []
    group = workflow_map.get_node_data(ids["http"])["config"]["delete_group"]
    assert [c["target_node_id"] for c in group["keep"]] == [ids["after"]]
    assert _targets(workflow_map, ids["after"]) == [ids["end"]]


def test_cancelling_the_delete_keeps_the_node_and_its_handler():
    factory, workflow_map, ids = _handled_http()

    asked, _, deleted = _delete_in_editor(factory, workflow_map, ids["http"], "#confirm-no")

    assert asked and not deleted
    for kept in ("mux", "fix", "fix_end"):
        assert workflow_map.get_node_data(ids[kept]) is not None, kept


def test_deleting_a_node_without_an_error_handler_does_not_ask():
    factory, workflow_map, ids = _handled_http()

    asked, _, deleted = _delete_in_editor(factory, workflow_map, ids["after"], "#confirm-yes")

    assert not asked and deleted


def test_a_wired_error_path_is_deleted_with_its_node():
    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    logger = workflow_map.add_node("logger_node")
    after = workflow_map.add_node("no_op_node")
    handler = workflow_map.add_node("no_op_node")
    workflow_map.connect(start, "default", logger, "input")
    workflow_map.connect(logger, "default", after, "input")
    workflow_map.connect(logger, "error", handler, "input")

    asked, _, deleted = _delete_in_editor(factory, workflow_map, logger, "#confirm-yes")

    assert asked and deleted
    assert workflow_map.get_node_data(handler) is None
    assert workflow_map.get_node_data(after) is not None


def _deleted_text_output_then_resolver():
    """Start → HTTP → Text → Pause (Pause also fed by Note). Text Output is
    deleted, an Error Resolver is added after HTTP, and the workflow saved."""
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    http = workflow_map.add_node("http_request_node")
    text = workflow_map.add_node("text_output_node")
    note = workflow_map.add_node("no_op_node")
    pause = workflow_map.add_node("sleep_node")
    workflow_map.connect(start, "default", http, "input")
    workflow_map.connect(http, "default", text, "input")
    workflow_map.connect(text, "default", pause, "input")
    workflow_map.connect(note, "default", pause, "input")
    editor = EditorScreen(factory, workflow_map)
    editor.workflow_adapter.replace_with_placeholder(text)
    mux = editor._insert_error_mux_after(http)["mux_id"]
    editor.workflow_adapter.materialize_deleted_nodes()
    return factory, workflow_map, editor, dict(
        http=http, text=text, note=note, pause=pause, mux=mux)


def test_undo_after_save_never_gives_an_output_a_second_target():
    """Owner report: the Error Resolver vanished from the editor because
    HTTP's output led to both the Resolver and a restored Text Output."""
    from backend.validator import validate_workflow

    factory, workflow_map, editor, ids = _deleted_text_output_then_resolver()

    report = editor.workflow_adapter.restore_tombstone(ids["text"])

    assert report.restored and not report.input_errors and not report.output_errors
    assert _targets(workflow_map, ids["http"]) == [ids["mux"]]
    assert _targets(workflow_map, ids["mux"]) == [ids["text"]]
    # Two parents may share Pause's input again, as before the delete.
    assert _targets(workflow_map, ids["text"]) == [ids["pause"]]
    assert _targets(workflow_map, ids["note"]) == [ids["pause"]]
    rows = [row["node_id"] for row in editor._build_visible_rows() if row["kind"] == "node"]
    assert rows.index(ids["http"]) < rows.index(ids["mux"]) < rows.index(ids["text"])
    result = validate_workflow(workflow_map, factory)
    assert not [w for w in result["warnings"] if w.get("code") == "ignored_fan_out"]


def test_undo_reports_an_input_it_cannot_put_back():
    factory, workflow_map = _map()
    from frontend.screens.editor import EditorScreen

    start = workflow_map.add_node("start_node")
    first = workflow_map.add_node("no_op_node")
    later = workflow_map.add_node("logger_node")
    workflow_map.connect(start, "default", first, "input")
    editor = EditorScreen(factory, workflow_map)
    editor.workflow_adapter.replace_with_placeholder(first)
    editor.workflow_adapter.materialize_deleted_nodes()
    # Start's output now leads somewhere else.
    workflow_map.disconnect(start, "default", first, "input")
    workflow_map.connect(start, "default", later, "input")

    report = editor.workflow_adapter.restore_tombstone(first)

    assert [error["reason"] for error in report.input_errors] == ["source_port_taken"]
    assert _targets(workflow_map, start) == [later]


def test_validator_warns_when_a_resolvers_no_error_path_never_runs():
    """The owner's saved shape: HTTP → Text Output and HTTP → Resolver →
    Pause. Only Text Output runs after a success."""
    from backend.validator import validate_workflow

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    http = workflow_map.add_node("http_request_node")
    text = workflow_map.add_node("text_output_node")
    mux = workflow_map.add_node("error_mux_node")
    pause = workflow_map.add_node("sleep_node")
    workflow_map.connect(start, "default", http, "input")
    workflow_map.connect(http, "default", text, "input")
    workflow_map.connect(http, "default", mux, "input")
    workflow_map.connect(mux, "default", pause, "input")

    result = validate_workflow(workflow_map, factory)
    fan_out = [w for w in result["warnings"] if w.get("code") == "ignored_fan_out"]
    assert [w["node_id"] for w in fan_out] == [http]

    # A catch-only Resolver beside the next node is still fine.
    workflow_map.disconnect(mux, "default", pause, "input")
    result = validate_workflow(workflow_map, factory)
    assert not [w for w in result["warnings"] if w.get("code") == "ignored_fan_out"]


# -- Removing a deleted node's stub (owner "user test" report, 2026-10-18):
# removing a Resolver's stub joined HTTP to every path after it, so a
# successful run went down the old error branch.

def _resolver_with_branches(shared=False):
    """Start → HTTP → Resolver; No error → Ask → Done;
    Missing URL → Note → Note end (or → Done when ``shared``)."""
    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    http = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    ask = workflow_map.add_node("no_op_node")
    done = workflow_map.add_node("end_node")
    note = workflow_map.add_node("text_output_node")
    note_end = workflow_map.add_node("end_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "r_url", "label": "Missing URL", "codes": ["missing_url"]}]})
    workflow_map.connect(start, "default", http, "input")
    workflow_map.connect(http, "default", mux, "input")
    workflow_map.connect(mux, "default", ask, "input")
    workflow_map.connect(ask, "default", done, "input")
    workflow_map.connect(mux, "r_url", note, "input")
    if shared:
        workflow_map.connect(note, "default", ask, "input")
    else:
        workflow_map.connect(note, "default", note_end, "input")
    return factory, workflow_map, dict(
        start=start, http=http, mux=mux, ask=ask, done=done, note=note, note_end=note_end)


def _remove_stub_in_editor(factory, workflow_map, node_id, button="#confirm-yes", save=False):
    """Delete the node, optionally save, then delete its stub."""
    from textual.app import App

    from frontend.screens.confirm import ConfirmScreen
    from frontend.screens.branch_keep_selector_screen import BranchKeepSelectorScreen
    from frontend.screens.editor import EditorScreen

    class EditorApp(App):
        def compose(self):
            yield EditorScreen(factory, workflow_map)

    async def run():
        app = EditorApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.03)
            editor = app.query_one(EditorScreen)
            asked = []
            for step in range(2):
                editor.selected_node_id = node_id
                editor.selected_row = {"kind": "node", "node_id": node_id}
                editor.action_delete_selected()
                await pilot.pause(0.03)
                if isinstance(app.screen, ConfirmScreen):
                    asked.append(str(app.screen._message))
                    await pilot.click("#confirm-yes" if step == 0 else button)
                    await pilot.pause(0.03)
                elif isinstance(app.screen, BranchKeepSelectorScreen):
                    await pilot.press('e', 'enter')
                    await pilot.pause(0.03)
                if step == 0 and save:
                    editor.workflow_adapter.materialize_deleted_nodes()
            return asked

    return asyncio.run(run())


def test_removing_a_resolver_stub_keeps_only_the_no_error_path():
    for save in (False, True):
        factory, workflow_map, ids = _resolver_with_branches()

        asked = _remove_stub_in_editor(factory, workflow_map, ids["mux"], save=save)

        assert len(asked) == 2 and "No error continues" in asked[0] and "cannot be undone" in asked[1], save
        assert workflow_map.get_node_data(ids["mux"]) is None
        assert _targets(workflow_map, ids["http"]) == [ids["ask"]], save
        for gone in ("note", "note_end"):
            assert workflow_map.get_node_data(ids[gone]) is None, (save, gone)
        assert _targets(workflow_map, ids["ask"]) == [ids["done"]]


def test_cancelling_the_resolver_stub_removal_keeps_everything():
    from copy import deepcopy
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter
    factory, workflow_map, ids = _resolver_with_branches()
    before = deepcopy(workflow_map.get_all_node_data())
    asked = _remove_stub_in_editor(factory, workflow_map, ids["mux"], button="#confirm-no")
    assert len(asked) == 2
    stub = workflow_map.get_node_data(ids['mux'])
    assert stub['type'] == 'tombstone_node'
    assert ids['note'] in stub['config']['delete_group']['before']
    assert workflow_map.get_node_data(ids['note']) is None
    # Cancel preserved the whole archived group, including its original wiring.
    EditorWorkflowAdapter(workflow_map, factory).undo_placeholder(ids['mux'])
    assert workflow_map.get_all_node_data() == before


def test_a_node_the_no_error_path_also_reaches_is_kept():
    factory, workflow_map, ids = _resolver_with_branches(shared=True)

    _remove_stub_in_editor(factory, workflow_map, ids["mux"])

    assert workflow_map.get_node_data(ids["note"]) is None
    assert workflow_map.get_node_data(ids["ask"]) is not None
    assert _targets(workflow_map, ids["http"]) == [ids["ask"]]


def test_removing_a_conditional_stub_never_gives_an_output_two_targets():
    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    check = workflow_map.add_node("conditional_node")
    yes = workflow_map.add_node("no_op_node")
    no = workflow_map.add_node("logger_node")
    workflow_map.connect(start, "default", check, "input")
    workflow_map.connect(check, "true", yes, "input")
    workflow_map.connect(check, "false", no, "input")

    asked = _remove_stub_in_editor(factory, workflow_map, check)

    assert len(asked) == 1  # the keep picker, then final-removal confirmation
    assert _targets(workflow_map, start) == [yes]
    assert workflow_map.get_node_data(no) is None


# -- Review of #82 at 47e7580.

def test_deleting_one_node_keeps_a_resolver_another_node_still_uses():
    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    fan = workflow_map.add_node("branch_node")
    first = workflow_map.add_node("http_request_node")
    second = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    after = workflow_map.add_node("no_op_node")
    fix = workflow_map.add_node("logger_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "r_url", "label": "Missing URL", "codes": ["missing_url"]}]})
    workflow_map.connect(start, "default", fan, "input")
    workflow_map.connect(fan, "path_a", first, "input")
    workflow_map.connect(fan, "path_b", second, "input")
    workflow_map.connect(first, "default", mux, "input")
    workflow_map.connect(second, "default", mux, "input")
    workflow_map.connect(mux, "default", after, "input")
    workflow_map.connect(mux, "r_url", fix, "input")

    asked, message, deleted = _delete_in_editor(factory, workflow_map, first, "#confirm-yes")

    assert deleted and asked
    assert "another node uses it" in message
    for kept in (mux, fix, after):
        assert workflow_map.get_node_data(kept) is not None, kept
    assert _targets(workflow_map, second) == [mux]


def test_error_routes_that_share_a_tail_are_deleted_together():
    factory, workflow_map, ids = _handled_http()
    mux, fix, fix_end = ids["mux"], ids["fix"], ids["fix_end"]
    other = workflow_map.add_node("logger_node")
    workflow_map.update_node_config(mux, {"routes": [
        {"id": "r_timeout", "label": "Timeout", "codes": ["timeout"]},
        {"id": "r_url", "label": "Missing URL", "codes": ["missing_url"]}]})
    workflow_map.connect(mux, "r_url", other, "input")
    workflow_map.connect(other, "default", fix_end, "input")  # both routes end at fix_end

    asked, _, deleted = _delete_in_editor(factory, workflow_map, ids["http"], "#confirm-yes")

    assert asked and deleted
    for gone in (mux, fix, other, fix_end):
        assert workflow_map.get_node_data(gone) is None, gone
    assert _targets(workflow_map, ids["http"]) == []
    group = workflow_map.get_node_data(ids['http'])['config']['delete_group']
    assert [c['target_node_id'] for c in group['keep']] == [ids['after']]
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter
    EditorWorkflowAdapter(workflow_map, factory).undo_placeholder(ids['http'])
    for restored in (mux, fix, other, fix_end):
        assert workflow_map.get_node_data(restored) is not None
    assert _targets(workflow_map, ids['http']) == [mux]


def test_undo_drops_an_input_from_a_path_that_no_longer_exists():
    from frontend.screens.editor import EditorScreen

    factory, workflow_map = _map()
    start = workflow_map.add_node("start_node")
    fan = workflow_map.add_node("branch_node")
    third = workflow_map.add_node("logger_node")
    workflow_map.update_node_config(fan, {"branch_count": 3})
    workflow_map.connect(start, "default", fan, "input")
    workflow_map.connect(fan, "path_c", third, "input")
    editor = EditorScreen(factory, workflow_map)
    editor.workflow_adapter.replace_with_placeholder(third)
    editor.workflow_adapter.materialize_deleted_nodes()
    config = dict(workflow_map.get_node_data(fan)["config"], branch_count=2)
    editor._apply_node_config_result(fan, {"alias": "", "config": config})

    report = editor.workflow_adapter.restore_tombstone(third)

    assert [error["reason"] for error in report.input_errors] == ["source_port_missing"]
    assert workflow_map.get_node_data(third)["connections"]["inputs"] == []
    assert third not in _targets(workflow_map, fan, "path_c")

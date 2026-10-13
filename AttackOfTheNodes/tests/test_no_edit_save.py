"""UX2: Error Mux legacy pass-along, the route draft record, and the
no-edit-save invariant (opening a node's config and saving without edits
changes neither its config nor any connection)."""

from __future__ import annotations

import asyncio
import json
import os
from copy import deepcopy

import pytest

from backend.config_migrations import normalize_node_config
from backend.event_bus import EventBus
from backend.node_errors import UNMATCHED_ROUTE, mux_forward_for
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()


def _map():
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("ux2")
    return workflow_map


def _snapshot(workflow_map):
    return json.loads(json.dumps(workflow_map.get_all_node_data(), sort_keys=True))


async def _open_and_save(workflow_map, node_id, edit=None):
    """Open NodeConfigScreen, optionally run ``edit(screen)``, then save."""
    from textual.app import App

    from frontend.screens.node_config import NodeConfigScreen

    screen = NodeConfigScreen(FACTORY, workflow_map, node_id, workflow_map.get_node_data(node_id))

    class ConfigApp(App):
        CSS_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.tcss")
        saved = None

        def on_mount(self):
            self.push_screen(screen, lambda result: setattr(self, "saved", result))

    app = ConfigApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await pilot.pause()
        if edit is not None:
            await edit(screen, pilot)
        screen.action_save()
        await pilot.pause()
    return app.saved


def _apply(workflow_map, node_id, saved):
    from frontend.screens.editor import EditorScreen

    EditorScreen(FACTORY, workflow_map)._apply_node_config_result(node_id, saved)


# --- No-edit invariant ------------------------------------------------------

# Representative non-default configs, on top of every type's default config.
REPRESENTATIVE = {
    "branch_node": {"branch_count": 3, "path_a_label": "Fast", "path_c_label": "Slow"},
    "error_mux_node": {
        "routes": [
            {"id": "both", "label": "Both", "codes": ["timeout", "network"], "forward": "failed_input"},
            {"id": "status", "label": "Status", "codes": ["http_status"], "forward": "error"},
        ],
        "unmatched_route": True,
        "unmatched_label": "Other",
        "unmatched_forward": "failed_input",
    },
    "http_request_node": {"url": "http://example.test/x", "timeout_seconds": 5},
    "no_op_node": {"show_error_path": True},
    "text_output_node": {"text": "hello"},
    "conditional_node": {"true_label": "Yes"},
}


def _cases():
    cases = [(node_type, None) for node_type in sorted(FACTORY.get_registered_types())]
    cases += [(node_type, config) for node_type, config in sorted(REPRESENTATIVE.items())]
    return cases


def _line_with(node_type, config):
    """start → (HTTP Request when the node is a mux) → node → No Op."""
    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    if node_type == "start_node":
        node = start
    else:
        source, port = start, "default"
        if node_type == "error_mux_node":
            source = workflow_map.add_node("http_request_node")
            workflow_map.connect(start, "default", source, "input")
        node = workflow_map.add_node(node_type)
        inputs = FACTORY.declared_input_ports(node_type)
        if inputs:
            workflow_map.connect(source, port, node, inputs[0])
    if config is not None:
        workflow_map.update_node_config(node, config)
    outputs = FACTORY.node_output_ports(workflow_map.get_node_data(node))
    if outputs and node_type not in {"branch_end_node", "end_node"}:
        after = workflow_map.add_node("no_op_node")
        workflow_map.connect(node, outputs[0], after, "input")
    return workflow_map, node


@pytest.mark.parametrize(
    "node_type,config", _cases(),
    ids=[f"{t}{'-rep' if c else ''}" for t, c in _cases()],
)
def test_saving_without_edits_changes_nothing(node_type, config):
    workflow_map, node = _line_with(node_type, config)
    before = _snapshot(workflow_map)
    saved = asyncio.run(_open_and_save(workflow_map, node))
    assert saved is not None, "the screen refused a no-edit save"
    assert saved["config"] == before[node]["config"]
    _apply(workflow_map, node, saved)
    assert _snapshot(workflow_map) == before


def test_edits_are_still_saved_and_an_undone_edit_is_not():
    # (UX4 removed the Show error path checkbox this test used to edit; a
    # text field is edited instead.)
    workflow_map, node = _line_with("http_request_node", None)
    original_url = workflow_map.get_node_data(node)["config"].get("url", "")

    async def edit(screen, pilot):
        screen.query_one("#field-url").value = "http://example.test/edited"
        await pilot.pause()

    async def edit_and_undo(screen, pilot):
        await edit(screen, pilot)
        screen.query_one("#field-url").value = original_url
        await pilot.pause()

    before = deepcopy(workflow_map.get_node_data(node)["config"])
    saved = asyncio.run(_open_and_save(workflow_map, node, edit))
    assert saved["config"]["url"] == "http://example.test/edited"
    # An edited save is written as collected, as before UX2.
    assert "transient_outputs" in saved["config"] and "transient_outputs" not in before
    saved = asyncio.run(_open_and_save(workflow_map, node, edit_and_undo))
    assert saved["config"] == before


# --- Legacy pass-along (error_mux_forward_v1) -------------------------------


def test_node_wide_forward_moves_onto_every_branch():
    legacy = {
        "forward": "failed_input",
        "routes": [
            {"id": "a", "label": "A", "codes": ["timeout"]},
            {"id": "b", "label": "B", "codes": ["network"], "forward": "error"},
            {"id": "c", "label": "C", "codes": ["x"], "forward": "bogus"},
        ],
        "unmatched_route": True,
    }
    migrated = normalize_node_config("error_mux_node", legacy)
    assert "forward" not in migrated
    assert [route.get("forward") for route in migrated["routes"]] == [
        "failed_input", "error", "failed_input"]
    assert migrated["unmatched_forward"] == "failed_input"
    assert migrated["_config_migrations"]["error_mux_forward_v1"] == {"forward": "failed_input"}
    assert normalize_node_config("error_mux_node", migrated) == migrated
    # Effective pass-along per branch matches the pre-P4 fallback rule.
    for port, old in (("a", "failed_input"), ("b", "error"), ("c", "failed_input"),
                      (UNMATCHED_ROUTE, "failed_input")):
        assert mux_forward_for(migrated, port) == old


def test_a_branch_or_catch_all_choice_wins_over_node_wide_forward():
    migrated = normalize_node_config(
        "error_mux_node",
        {"forward": "failed_input", "unmatched_forward": "error",
         "routes": [{"id": "a", "codes": ["t"], "forward": "error"}]},
    )
    assert migrated["unmatched_forward"] == "error"
    assert migrated["routes"][0]["forward"] == "error"


def test_mux_without_node_wide_forward_is_untouched():
    config = {"routes": [{"id": "a", "label": "A", "codes": ["t"]}]}
    assert normalize_node_config("error_mux_node", config) == config


def test_legacy_mux_no_edit_save_keeps_each_branch_forward():
    workflow_map, mux = _line_with("error_mux_node", {
        "forward": "failed_input",
        "routes": [{"id": "old", "label": "Retry", "codes": ["timeout"]}],
        "unmatched_route": True,
    })
    saved = asyncio.run(_open_and_save(workflow_map, mux))
    config = normalize_node_config("error_mux_node", saved["config"])
    assert mux_forward_for(config, "old") == "failed_input"
    assert mux_forward_for(config, UNMATCHED_ROUTE) == "failed_input"


# --- Route draft record -------------------------------------------------------


def test_draft_reselect_restores_grouped_branch():
    from frontend.error_mux_ui import MuxRouteDraft

    draft = MuxRouteDraft({"routes": [
        {"id": "both", "label": "Both", "codes": ["timeout", "network"], "forward": "failed_input"}]})
    assert draft.rows(["network"]) == [
        {"id": "both", "label": "Both", "forward": "failed_input", "codes": ["network"]}]
    assert draft.rows([]) == []
    assert draft.rows(["timeout", "network"]) == [
        {"id": "both", "label": "Both", "forward": "failed_input", "codes": ["timeout", "network"]}]


def test_draft_keeps_the_latest_edit_and_new_codes_get_their_own_branch():
    from frontend.error_mux_ui import MuxRouteDraft

    draft = MuxRouteDraft({"routes": [{"id": "r", "label": "Old", "codes": ["timeout"]}]})
    rows = draft.rows(["timeout"])
    rows[0]["label"] = "First"
    draft.record(rows)
    rows = draft.rows(["timeout"])
    rows[0]["label"] = "Revised"
    rows[0]["forward"] = "failed_input"
    draft.record(rows)
    assert draft.rows([]) == []
    assert draft.rows(["timeout"]) == [
        {"id": "r", "label": "Revised", "forward": "failed_input", "codes": ["timeout"]}]
    fresh = draft.rows(["timeout", "network"])[1]
    assert fresh["id"].startswith("route_") and fresh["codes"] == ["network"]
    # The new branch is remembered too.
    assert draft.rows(["network"])[0]["id"] == fresh["id"]


def test_mounted_reselect_keeps_grouped_branch_and_latest_name():
    from textual.widgets import SelectionList

    workflow_map, mux = _line_with("error_mux_node", {"routes": [
        {"id": "both", "label": "Both", "codes": ["timeout", "network"], "forward": "failed_input"}]})

    async def churn(screen, pilot):
        picker = screen.query_one("#mux-recover-from", SelectionList)
        picker.deselect("timeout")
        await pilot.pause()
        picker.select("timeout")
        await pilot.pause()
        assert screen._error_mux_config_values()["routes"] == [
            {"id": "both", "label": "Both", "codes": ["timeout", "network"], "forward": "failed_input"}]
        picker.deselect("timeout")
        picker.deselect("network")
        await pilot.pause()
        picker.select("timeout")
        await pilot.pause()
        screen.query_one("#mux-route-label-both").value = "Revised"
        await pilot.pause()
        picker.deselect("timeout")
        await pilot.pause()
        picker.select("timeout")
        await pilot.pause()

    saved = asyncio.run(_open_and_save(workflow_map, mux, churn))
    assert saved["config"]["routes"] == [
        {"id": "both", "label": "Revised", "codes": ["timeout"], "forward": "failed_input"}]


def test_mux_connections_summary_follows_the_picks():
    from textual.widgets import SelectionList

    workflow_map, mux = _line_with("error_mux_node", {"routes": [
        {"id": "slow", "label": "Slow", "codes": ["timeout"], "forward": "error"}]})
    handler = workflow_map.add_node("no_op_node")
    workflow_map.connect(mux, "slow", handler, "input")
    seen = {}

    async def unpick(screen, pilot):
        summary = lambda: str(screen.query_one("#connection-summary").render())
        seen["before"] = summary()
        screen.query_one("#mux-recover-from", SelectionList).deselect("timeout")
        await pilot.pause()
        await pilot.pause()
        seen["after"] = summary()

    asyncio.run(_open_and_save(workflow_map, mux, unpick))
    assert "slow ->" in seen["before"] and "removed on save" not in seen["before"]
    assert "slow ->" in seen["after"] and "removed on save" in seen["after"]

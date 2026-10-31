"""UX1: Merge branch identity and the never-silently-drop backstop.

Only nodes that spawn branch supervisors (``spawns_branches``) start a new
branch context. Before UX1 any node with more than one output did, so a node
inside a Branch path that shows an error path (HTTP Request then listed it),
routes errors (Error Mux) or chooses a path (Conditional) changed the Merge
option from ``<branch>:path_b`` to ``<node>:<port>``; a no-edit Merge save then
emptied ``branches_to_close`` and the editor disconnected the Merge Beacon.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap


def _make_map():
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new("ux1")
    return factory, workflow_map


def _option_values(workflow_map, merge_id):
    from frontend.screens.node_config import merge_input_options

    return [
        f"{option['branch_id']}:{option['branch_port']}"
        for option in merge_input_options(workflow_map, merge_id)
    ]


# Each case puts one multi-output, non-spawning node on Branch path_b.
# (node type, config, input port, output port feeding the beacon)
PATH_NODES = {
    "error_path_toggle": ("no_op_node", {"show_error_path": True}, "input", "default"),
    "http_request": ("http_request_node", {"show_error_path": True}, "input", "default"),
    "error_mux": (
        "error_mux_node",
        {
            "routes": [
                {"id": "r_timeout", "label": "Timeout", "codes": ["timeout"]},
                {"id": "r_network", "label": "Network", "codes": ["network"]},
            ]
        },
        "error",
        "r_timeout",
    ),
    "conditional": ("conditional_node", {}, "input", "true"),
    "random_branch": ("random_branch_node", {}, "input", "path_a"),
}


def _branch_with_path_node(case):
    """Start → Branch; path_a → Merge; path_b → <node> → Beacon → Merge."""
    node_type, config, input_port, output_port = PATH_NODES[case]
    factory, wm = _make_map()
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    merge = wm.add_node("merge_node")
    node = wm.add_node(node_type)
    beacon = wm.add_node("branch_end_node")
    if config:
        wm.update_node_config(node, config)
    assert len(factory.node_output_ports(wm.get_node_data(node))) > 1 or "show_error_path" in config
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", merge, "path_a")
    wm.connect(branch, "path_b", node, input_port)
    wm.connect(node, output_port, beacon, "input")
    wm.connect(beacon, "default", merge, "path_b")
    closure = f"{branch}:path_b"
    wm.update_node_config(
        merge,
        {
            "branches_to_close": [closure],
            "carry_forward_branch_id": closure,
        },
    )
    return factory, wm, merge, beacon, closure


async def _no_edit_save(factory, wm, node_id):
    from textual.app import App

    from frontend.screens.node_config import NodeConfigScreen

    screen = NodeConfigScreen(factory, wm, node_id, wm.get_node_data(node_id))

    class ConfigApp(App):
        saved = None

        def on_mount(self):
            self.push_screen(screen, lambda result: setattr(self, "saved", result))

    app = ConfigApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        warning = [str(widget.render()) for widget in app.screen.query("#merge-unmatched-warning")]
        screen.action_save()
        await pilot.pause()
    return app.saved, warning


def _apply_save(factory, wm, merge, saved):
    from frontend.screens.editor import EditorScreen

    wm.update_node_config(merge, saved["config"])
    EditorScreen(factory, wm)._sync_merge_branch_end_connections(
        merge, saved["config"], reconcile_unselected=True
    )


@pytest.mark.parametrize("case", sorted(PATH_NODES))
def test_multi_output_node_inside_a_branch_keeps_the_branch_identity(case):
    _, wm, merge, _, closure = _branch_with_path_node(case)
    assert _option_values(wm, merge) == [closure]


@pytest.mark.parametrize("case", sorted(PATH_NODES))
def test_no_edit_merge_save_keeps_closure_carry_forward_and_beacon(case):
    factory, wm, merge, beacon, closure = _branch_with_path_node(case)
    saved, warning = asyncio.run(_no_edit_save(factory, wm, merge))
    config = saved["config"]
    assert config["branches_to_close"] == [closure]
    assert config["carry_forward_branch_id"] == closure
    assert "selected_input_port" not in config
    assert warning == []
    _apply_save(factory, wm, merge, saved)
    assert wm.get_node_data(beacon)["connections"]["outputs"] == [
        {"source_port": "default", "target_node_id": merge, "target_port": "path_b"}
    ]


def test_nested_branch_still_starts_its_own_contexts():
    _, wm = _make_map()
    start = wm.add_node("start_node")
    outer = wm.add_node("branch_node")
    inner = wm.add_node("branch_node")
    merge = wm.add_node("merge_node")
    beacon_a = wm.add_node("branch_end_node")
    beacon_b = wm.add_node("branch_end_node")
    wm.connect(start, "default", outer, "input")
    wm.connect(outer, "path_a", merge, "path_a")
    wm.connect(outer, "path_b", inner, "input")
    wm.connect(inner, "path_a", beacon_a, "input")
    wm.connect(inner, "path_b", beacon_b, "input")
    assert sorted(_option_values(wm, merge)) == [f"{inner}:path_a", f"{inner}:path_b"]


def test_spawns_branches_flags_only_the_spawning_types():
    factory = NodeFactory()
    flagged = {
        node_type
        for node_type in factory.get_registered_types()
        if factory.spawns_branches(node_type)
    }
    assert flagged == {"branch_node", "deep_branch_node"}
    metadata = {item["type"]: item for item in factory.get_node_types_metadata()}
    assert metadata["branch_node"]["spawns_branches"] is True
    assert metadata["http_request_node"]["spawns_branches"] is False
    assert factory.spawns_branches("not_a_type") is False


def test_every_node_that_signals_branches_declares_spawns_branches():
    factory = NodeFactory()
    for node_type in factory.get_registered_types():
        node_class = factory._node_registry[node_type]
        source = inspect.getsource(node_class)
        signals = '"branches"' in source or "'branches'" in source
        assert signals == node_class.spawns_branches, node_type


# --- Backstop: unmatched saved values are kept, never dropped -------------


def _merge_with_stale_values():
    factory, wm, merge, beacon, closure = _branch_with_path_node("error_path_toggle")
    ghost = "node_gone:path_b"
    wm.update_node_config(
        merge,
        {
            "branches_to_close": [closure, ghost],
            "carry_forward_branch_id": ghost,
            "selected_branch_id": ghost,
        },
    )
    return factory, wm, merge, beacon, closure, ghost


def test_unmatched_merge_values_reports_closures_and_carry():
    from frontend.screens.node_config import unmatched_merge_values

    options = [{"branch_id": "b", "branch_port": "path_a"}]
    assert unmatched_merge_values(
        options,
        {"branches_to_close": ["b:path_a", "x:path_b"], "carry_forward_branch_id": "x:path_b"},
    ) == (["x:path_b"], "x:path_b")
    assert unmatched_merge_values(options, {"branches_to_close": ["b:path_a"]}) == ([], "")
    # Legacy single-branch configs keep their closure too.
    assert unmatched_merge_values(options, {"selected_branch_id": "x:path_b"}) == (
        ["x:path_b"],
        "x:path_b",
    )
    # Home carry-forward is judged only against known home inputs.
    home = {"carry_forward_branch_id": "home:path_a"}
    assert unmatched_merge_values(options, home) == ([], "")
    assert unmatched_merge_values(options, home, {"path_a"}) == ([], "")
    assert unmatched_merge_values(options, home, set()) == ([], "home:path_a")


def test_no_edit_save_keeps_unmatched_values_and_warns():
    factory, wm, merge, beacon, closure, ghost = _merge_with_stale_values()
    saved, warning = asyncio.run(_no_edit_save(factory, wm, merge))
    config = saved["config"]
    assert config["branches_to_close"] == sorted([closure, ghost])
    assert config["carry_forward_branch_id"] == ghost
    assert config["selected_branch_id"] == ghost
    assert "selected_input_port" not in config
    assert len(warning) == 1 and ghost in warning[0]


def test_editor_sync_never_disconnects_a_beacon_while_a_closure_is_unmatched():
    from frontend.screens.editor import EditorScreen

    factory, wm, merge, beacon, closure, ghost = _merge_with_stale_values()
    # The live option is not selected, but an unmatched closure remains:
    # it may be this beacon's closure under an older identity.
    config = {"branches_to_close": [ghost], "carry_forward_branch_id": ghost}
    wm.update_node_config(merge, config)
    EditorScreen(factory, wm)._sync_merge_branch_end_connections(
        merge, config, reconcile_unselected=True
    )
    assert wm.get_node_data(beacon)["connections"]["outputs"] == [
        {"source_port": "default", "target_node_id": merge, "target_port": "path_b"}
    ]


def test_editor_sync_still_disconnects_an_explicitly_unselected_beacon():
    from frontend.screens.editor import EditorScreen

    factory, wm, merge, beacon, closure = _branch_with_path_node("http_request")
    config = {"branches_to_close": [], "carry_forward_branch_id": ""}
    wm.update_node_config(merge, config)
    EditorScreen(factory, wm)._sync_merge_branch_end_connections(
        merge, config, reconcile_unselected=True
    )
    assert wm.get_node_data(beacon)["connections"]["outputs"] == []


def test_unchecking_a_kept_closure_drops_it():
    asyncio.run(_test_unchecking_a_kept_closure_drops_it())


async def _test_unchecking_a_kept_closure_drops_it():
    from textual.app import App
    from textual.widgets import Select, SelectionList

    from frontend.screens.node_config import NodeConfigScreen

    factory, wm, merge, beacon, closure, ghost = _merge_with_stale_values()
    screen = NodeConfigScreen(factory, wm, merge, wm.get_node_data(merge))

    class ConfigApp(App):
        def on_mount(self):
            self.push_screen(screen)

    app = ConfigApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        selector = app.screen.query_one("#merge-branches-to-close", SelectionList)
        carry = app.screen.query_one("#merge-carry-forward-selector", Select)
        assert set(selector.selected) == {closure, ghost}
        assert carry.value == ghost
        selector.deselect(ghost)
        carry.value = closure
        await pilot.pause()
        values = screen._merge_config_values()
    assert values["branches_to_close"] == [closure]
    assert values["carry_forward_branch_id"] == closure
    assert "selected_input_port" not in values

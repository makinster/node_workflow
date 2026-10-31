"""Branch paths beyond five and Merge input slots to match (port model P3).

Branch outputs and Merge inputs share one naming scheme (``path_a`` ...
``path_z``, ``path_aa`` ...). A Branch has ``branch_count`` paths; a Merge
has ``input_slots`` slots, five unless the editor raises it.
"""

from __future__ import annotations

import asyncio

import pytest

from backend.branch_paths import (
    ALL_PATH_PORTS,
    DEFAULT_MERGE_SLOTS,
    MAX_BRANCH_COUNT,
    merge_slot_count,
    path_index,
    path_port,
    path_ports,
    slots_covering,
)
from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import NODE_EXECUTION_UPDATE
from backend.run_context import MergePlan, MergeSlot
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.output_manager import OutputManager
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap


@pytest.fixture(autouse=True)
def _run_records_in_tmp(tmp_path, monkeypatch):
    from backend import error_handler, output_manager, run_history

    monkeypatch.setattr(error_handler, "RUN_ERRORS_DIR", tmp_path / "run_errors")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history")
    monkeypatch.setattr(output_manager, "RUN_OUTPUTS_DIR", tmp_path / "run_outputs")


def _services():
    bus = EventBus()
    factory = NodeFactory()
    workflow_map = WorkflowMap(factory, bus)
    master = MasterState(workflow_map, MemoryBank(bus), bus,
                         output_manager=OutputManager(),
                         configuration_manager=ConfigurationManager())
    workflow_map.create_new("Wide branch")
    return bus, factory, workflow_map, master


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("index,name", [
    (0, "path_a"), (4, "path_e"), (25, "path_z"), (26, "path_aa"),
    (27, "path_ab"), (51, "path_az"), (52, "path_ba"), (63, "path_bl"),
])
def test_path_names_continue_past_z(index, name):
    assert path_port(index) == name
    assert path_index(name) == index


def test_path_lists_and_lookups():
    assert path_ports(5) == ["path_a", "path_b", "path_c", "path_d", "path_e"]
    assert len(ALL_PATH_PORTS) == MAX_BRANCH_COUNT == len(set(ALL_PATH_PORTS))
    assert path_index("default") is None
    assert path_index("path_zz") is None
    assert slots_covering(["path_a", "path_g", "default", None]) == 7
    assert slots_covering([]) == 0
    with pytest.raises(ValueError):
        path_port(-1)


@pytest.mark.parametrize("config,slots", [
    ({}, DEFAULT_MERGE_SLOTS), ({"input_slots": 3}, DEFAULT_MERGE_SLOTS),
    ({"input_slots": 9}, 9), ({"input_slots": "12"}, 12),
    ({"input_slots": 999}, MAX_BRANCH_COUNT), ({"input_slots": "x"}, DEFAULT_MERGE_SLOTS),
])
def test_merge_slot_count_never_drops_below_the_old_five(config, slots):
    factory = NodeFactory()
    assert merge_slot_count(config) == slots
    assert factory.input_ports_for("merge_node", config) == path_ports(slots)


def test_fixed_nodes_resolve_inputs_to_their_class_list():
    factory = NodeFactory()
    for meta in factory.get_node_types_metadata():
        if meta["type"] == "merge_node":
            continue
        assert factory.input_ports_for(meta["type"], meta["default_config"]) == list(meta["input_ports"])
    assert factory.node_input_ports(None) == []
    assert factory.declared_input_ports("merge_node") == ALL_PATH_PORTS


# ---------------------------------------------------------------------------
# Engine: an 8-way Branch closed by one Merge with 8 slots
# ---------------------------------------------------------------------------


def _wide_workflow(workflow_map, paths=8, slots=8):
    start = workflow_map.add_node("start_node")
    fork = workflow_map.add_node("branch_node")
    merge = workflow_map.add_node("merge_node")
    end = workflow_map.add_node("no_op_node")
    workflow_map.update_node_config(start, {"greeting": "hello"})
    workflow_map.update_node_config(fork, {"branch_count": paths})
    workflow_map.update_node_config(merge, {"input_slots": slots})
    workflow_map.connect(start, "default", fork, "input")
    steps = {}
    for port in path_ports(paths):
        steps[port] = workflow_map.add_node("no_op_node")
        workflow_map.connect(fork, port, steps[port], "input")
        workflow_map.connect(steps[port], "default", merge, port)
    workflow_map.connect(merge, "default", end, "input")
    return fork, merge, end, steps


def test_an_eight_way_branch_runs_every_path_and_merges_once():
    bus, factory, workflow_map, master = _services()
    events = []
    bus.subscribe(NODE_EXECUTION_UPDATE, events.append)
    fork, merge, end, steps = _wide_workflow(workflow_map)

    result = validate_workflow(workflow_map, factory)
    assert result["errors"] == []
    assert not [w for w in result["warnings"] if "hidden" in w["message"]]

    async def run():
        assert await master.start_workflow(merge_plans={merge: MergePlan(fork, {
            port: MergeSlot("one", ((i,),)) for i, port in enumerate(path_ports(8))})})
        await asyncio.wait_for(master.wait_for_completion(), timeout=5)
    asyncio.run(run())

    done = [e["node_id"] for e in events if e["status"] == "done"]
    assert all(steps[port] in done for port in path_ports(8))
    assert done.count(end) == 1
    assert master.state.value == "FINISHED"


def test_a_slot_above_input_slots_is_a_hidden_input_warning():
    bus, factory, workflow_map, master = _services()
    fork, merge, end, steps = _wide_workflow(workflow_map, paths=6, slots=5)

    result = validate_workflow(workflow_map, factory)
    warnings = [w["message"] for w in result["warnings"] if w.get("node_id") == merge]

    assert any("hidden input 'path_f' is never read" in m for m in warnings)
    assert not [e for e in result["errors"] if e.get("node_id") == merge]
    assert workflow_map.input_ports(merge) == path_ports(5)
    assert workflow_map.get_node_instance(merge).get_input_ports() == path_ports(5)


def test_a_port_merge_never_had_is_still_an_error():
    bus, factory, workflow_map, master = _services()
    merge = workflow_map.add_node("merge_node")
    source = workflow_map.add_node("no_op_node")
    workflow_map.connect(source, "default", merge, "not_a_slot")

    result = validate_workflow(workflow_map, factory)

    assert any("not_a_slot" in e["message"] for e in result["errors"] if e.get("node_id") == merge)


# ---------------------------------------------------------------------------
# Editor and node config
# ---------------------------------------------------------------------------


def test_editor_raises_input_slots_to_cover_connected_slots():
    from frontend.screens.editor import EditorScreen

    bus, factory, workflow_map, master = _services()
    fork, merge, end, steps = _wide_workflow(workflow_map, paths=7, slots=5)
    editor = EditorScreen(factory, workflow_map)

    editor._ensure_merge_input_slots(merge)

    assert workflow_map.get_node_data(merge)["config"]["input_slots"] == 7
    assert workflow_map.input_ports(merge) == path_ports(7)
    editor._ensure_merge_input_slots(merge)  # idempotent, never lowers
    assert workflow_map.get_node_data(merge)["config"]["input_slots"] == 7


def test_merge_slot_allocation_is_not_capped_at_five():
    from frontend.screens.node_config import selected_merge_ports

    bus, factory, workflow_map, master = _services()
    merge = workflow_map.add_node("merge_node")
    options = [
        {"branch_id": f"b{index}", "branch_port": port, "port": port}
        for index, port in enumerate(path_ports(7))
    ]
    selected = {f"b{index}:{port}" for index, port in enumerate(path_ports(7))}

    assignments = selected_merge_ports(workflow_map, merge, options, selected)

    assert sorted(assignments.values()) == path_ports(7)


def test_node_card_colors_follow_the_path_index():
    from frontend.widgets.node_card import branch_path_port_index

    assert branch_path_port_index("path_a") == 0
    assert branch_path_port_index("path_h") == 7
    assert branch_path_port_index("default") == 0


def test_branch_config_rows_grow_with_the_count_and_save_their_labels():
    from textual.app import App

    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.command_input import CommandInput

    bus, factory, workflow_map, master = _services()
    branch = workflow_map.add_node("branch_node")
    workflow_map.update_node_config(branch, {"branch_count": 7, "path_g_label": "Seventh"})
    screen = NodeConfigScreen(factory, workflow_map, branch, workflow_map.get_node_data(branch))

    class ConfigApp(App):
        def compose(self):
            yield screen

    async def check():
        app = ConfigApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            rows = list(app.query(".branch-payload-row"))
            assert [row.id for row in rows] == [f"branch-payload-row-{p}" for p in path_ports(7)]
            assert all(row.display for row in rows)
            assert app.query_one("#branch-label-path_g", CommandInput).value == "Seventh"

            app.query_one("#branch-count", CommandInput).value = "9"
            screen._sync_branch_payload_rows()
            await pilot.pause()
            assert len(app.query(".branch-payload-row")) == 9
            app.query_one("#branch-label-path_i", CommandInput).value = "Ninth"
            values = screen._branch_config_values()
            assert values["branch_count"] == 9
            assert values["path_g_label"] == "Seventh"
            assert values["path_i_label"] == "Ninth"
            assert set(values["branch_payload_sources"]) == set(path_ports(9))

            app.query_one("#branch-count", CommandInput).value = "3"
            screen._sync_branch_payload_rows()
            await pilot.pause()
            shown = [row for row in app.query(".branch-payload-row") if row.display]
            assert len(shown) == 3
            values = screen._branch_config_values()
            # Hidden paths keep their names for when the count grows again.
            assert values["path_i_label"] == "Ninth"
            assert set(values["branch_payload_sources"]) == set(path_ports(3))

    asyncio.run(check())

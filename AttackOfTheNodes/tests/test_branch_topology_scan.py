"""UX3: the Merge topology scan visits each (node, branch context) once.

``_reference_contexts`` is the pre-UX3 scan (a copy of ``seen`` per edge),
kept here only to prove the new scan returns identical results.
"""

from __future__ import annotations

import random
import time
from typing import Dict, Optional

import pytest

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
import frontend.screens.node_config as nc

FACTORY = NodeFactory()


def _reference_contexts(workflow_map) -> Dict[str, list[Dict[str, str]]]:
    contexts: Dict[str, list[Dict[str, str]]] = {}
    start_id = workflow_map.find_start_node_id()
    if not start_id:
        return contexts

    def add_context(node_id, context):
        if not context:
            return
        existing = contexts.setdefault(node_id, [])
        key = (context["branch_id"], context["branch_port"])
        if all((item["branch_id"], item["branch_port"]) != key for item in existing):
            existing.append(context)

    def follow(node_id, context: Optional[Dict[str, str]], seen):
        node = workflow_map.get_node_data(node_id) or {}
        if not node:
            return
        state = (node_id, context["branch_id"] if context else "",
                 context["branch_port"] if context else "")
        if state in seen:
            return
        seen.add(state)
        add_context(node_id, context)
        if node.get("type") == nc.BRANCH_END_NODE_TYPE:
            return
        outputs = node.get("connections", {}).get("outputs", [])
        if nc._node_spawns_branches(workflow_map, node):
            for output_port in nc._node_output_ports(workflow_map, node):
                target_id = nc._target_for_output(node, output_port)
                if not target_id:
                    continue
                next_context = {"branch_id": node_id, "branch_port": output_port,
                                "branch_label": nc._branch_label(node, output_port)}
                next_context["branch_path"] = nc._branch_path_label(
                    context, next_context["branch_label"])
                follow(target_id, next_context, set(seen))
            return
        for conn in outputs:
            target_id = str(conn.get("target_node_id") or "")
            if target_id:
                follow(target_id, context, set(seen))

    follow(start_id, None, set())
    return contexts


def _map():
    from backend.workflow_map import WorkflowMap

    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("ux3")
    return workflow_map


def _diamonds(depth):
    workflow_map = _map()
    previous = workflow_map.add_node("start_node")
    for _ in range(depth):
        branch = workflow_map.add_node("branch_node")
        merge = workflow_map.add_node("merge_node")
        workflow_map.connect(previous, "default", branch, "input")
        for port in ("path_a", "path_b"):
            node = workflow_map.add_node("no_op_node")
            workflow_map.connect(branch, port, node, "input")
            workflow_map.connect(node, "default", merge, port)
        previous = merge
    return workflow_map


def _random_graph(seed):
    """Branches, Conditionals, beacons and plain nodes, wired at random,
    including back edges (cycles) and rejoins."""
    rng = random.Random(seed)
    workflow_map = _map()
    nodes = [workflow_map.add_node("start_node")]
    kinds = ["no_op_node", "no_op_node", "branch_node", "conditional_node",
             "branch_end_node", "merge_node", "http_request_node"]
    for _ in range(rng.randint(6, 18)):
        kind = rng.choice(kinds)
        node = workflow_map.add_node(kind)
        if kind == "branch_node":
            workflow_map.update_node_config(node, {"branch_count": rng.randint(2, 4)})
        nodes.append(node)
    for source in nodes:
        data = workflow_map.get_node_data(source)
        for port in FACTORY.node_output_ports(data):
            for _ in range(rng.choice([0, 1, 1, 2])):
                target = rng.choice(nodes[1:])
                inputs = FACTORY.node_input_ports(workflow_map.get_node_data(target))
                if inputs:
                    workflow_map.connect(source, port, target, rng.choice(inputs))
    return workflow_map


@pytest.mark.parametrize("depth", [1, 4, 8])
def test_scan_matches_the_reference_on_fork_rejoin_chains(depth):
    workflow_map = _diamonds(depth)
    assert nc._branch_contexts_by_node(workflow_map) == _reference_contexts(workflow_map)


@pytest.mark.parametrize("seed", range(60))
def test_scan_matches_the_reference_on_random_graphs(seed):
    workflow_map = _random_graph(seed)
    assert nc._branch_contexts_by_node(workflow_map) == _reference_contexts(workflow_map)


def test_twelve_fork_rejoin_pairs_scan_in_under_5_ms():
    workflow_map = _diamonds(12)
    best = min(_timed(nc._branch_contexts_by_node, workflow_map) for _ in range(5))
    assert best < 0.005, best


def _timed(function, *args):
    started = time.perf_counter()
    function(*args)
    return time.perf_counter() - started


# --- Branch config rows (UX3 part 1) ----------------------------------------


def _branch_screen(count):
    workflow_map = _map()
    start = workflow_map.add_node("start_node")
    branch = workflow_map.add_node("branch_node")
    workflow_map.connect(start, "default", branch, "input")
    workflow_map.update_node_config(branch, {"branch_count": count})
    return nc.NodeConfigScreen(FACTORY, workflow_map, branch, workflow_map.get_node_data(branch))


async def _with_screen(screen, check):
    from textual.app import App

    class ConfigApp(App):
        def on_mount(self):
            self.push_screen(screen)

    async with ConfigApp().run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await check(pilot)


def test_branch_row_sync_uses_its_row_map_and_skips_unchanged_options(monkeypatch):
    import asyncio

    from textual.widgets import Select

    screen = _branch_screen(64)

    async def check(pilot):
        assert len(screen._branch_rows) == 64
        queries, set_options = [], []
        original_query = type(screen).query
        original_set_options = Select.set_options
        monkeypatch.setattr(type(screen), "query",
                            lambda self, *a, **k: queries.append(a) or original_query(self, *a, **k))
        monkeypatch.setattr(Select, "set_options",
                            lambda self, options: set_options.append(self.id) or original_set_options(self, options))
        screen._sync_branch_payload_rows()
        monkeypatch.undo()
        # A handful of fixed lookups (count, container, Vault reads), never
        # one per row; options unchanged, so no Select is rebuilt.
        assert len(queries) <= 6, queries
        assert set_options == []

    asyncio.run(_with_screen(screen, check))


def test_branch_count_typing_is_debounced_then_rows_follow():
    import asyncio

    from frontend.widgets.command_input import CommandInput

    screen = _branch_screen(2)

    async def check(pilot):
        count = screen.query_one("#branch-count", CommandInput)
        count.value = "1"
        count.value = "12"
        await pilot.pause()
        assert len(screen._branch_rows) == nc.COMPOSED_BRANCH_ROWS
        await pilot.pause(nc.BRANCH_COUNT_DEBOUNCE_SECONDS * 3)
        await pilot.pause()
        assert len(screen._branch_rows) == 12
        shown = [port for port, (row, _, _) in screen._branch_rows.items() if row.display]
        assert len(shown) == 12
        assert len(screen.query(".branch-payload-row")) == 12

    asyncio.run(_with_screen(screen, check))


# --- Factory metadata lookup (UX3 part 3) -------------------------------------


def test_metadata_for_type_is_built_once_and_matches_the_full_list(monkeypatch):
    from frontend.node_io_display import metadata_for_type

    factory = NodeFactory()
    full = {item["type"]: item for item in factory.get_node_types_metadata()}
    calls = []
    original = NodeFactory.get_node_types_metadata
    monkeypatch.setattr(NodeFactory, "get_node_types_metadata",
                        lambda self: calls.append(1) or original(self))
    for _ in range(3):
        for node_type in full:
            assert metadata_for_type(factory, node_type) == full[node_type]
    assert metadata_for_type(factory, "not_a_type") is None
    assert len(calls) == 1
    # The list API still hands out fresh copies callers may change.
    first = factory.get_node_types_metadata()
    first[0]["display_name"] = "changed"
    assert factory.get_node_types_metadata()[0]["display_name"] != "changed"

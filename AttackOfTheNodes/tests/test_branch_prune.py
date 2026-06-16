"""Tests for prune_branch_tombstone: branch keep selection on tombstone deletion.

Tests cover both the soft-deleted (in-session) and materialized (tombstone_node)
cases, upstream rewiring, downstream pruning, and edge cases.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_branch_prune.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_wm():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap

    bus = EventBus()
    factory = NodeFactory()
    return WorkflowMap(factory, bus), factory


def _build_branch_workflow(wm):
    """Build: start → branch_node(path_a→logger_a, path_b→logger_b).

    Returns (start_id, branch_id, logger_a_id, logger_b_id).
    """
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node", alias="My Branch")
    wm.update_node_config(branch, {
        "branch_count": 2,
        "path_a_label": "Branch 1",
        "path_b_label": "Branch 2",
    })
    logger_a = wm.add_node("logger_node", alias="Logger A")
    logger_b = wm.add_node("logger_node", alias="Logger B")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", logger_a, "input")
    wm.connect(branch, "path_b", logger_b, "input")
    return start, branch, logger_a, logger_b


def _adapter(wm, factory):
    from frontend.editor_workflow_adapter import EditorWorkflowAdapter
    return EditorWorkflowAdapter(wm, factory)


# ---------------------------------------------------------------------------
# Soft-deleted (in-session) tombstone
# ---------------------------------------------------------------------------

def test_prune_soft_tombstone_keeps_path_a():
    wm, factory = _make_wm()
    wm.create_new("prune_soft_a")
    start, branch, logger_a, logger_b = _build_branch_workflow(wm)

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)

    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 1, f"expected 1 pruned node, got {pruned}"
    assert wm.get_node_data(branch) is None, "branch tombstone should be removed"
    assert wm.get_node_data(logger_a) is not None, "kept branch node must survive"
    assert wm.get_node_data(logger_b) is None, "path_b node must be pruned"


def test_prune_soft_tombstone_keeps_path_b():
    wm, factory = _make_wm()
    wm.create_new("prune_soft_b")
    start, branch, logger_a, logger_b = _build_branch_workflow(wm)

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)

    pruned = adapter.prune_branch_tombstone(branch, "path_b")

    assert pruned == 1
    assert wm.get_node_data(logger_b) is not None
    assert wm.get_node_data(logger_a) is None


def test_prune_rewires_upstream_to_kept_head():
    wm, factory = _make_wm()
    wm.create_new("prune_rewire")
    start, branch, logger_a, logger_b = _build_branch_workflow(wm)

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    adapter.prune_branch_tombstone(branch, "path_a")

    start_data = wm.get_node_data(start)
    outputs = start_data.get("connections", {}).get("outputs", [])
    assert any(c.get("target_node_id") == logger_a for c in outputs), \
        "start should now connect directly to logger_a"

    logger_a_data = wm.get_node_data(logger_a)
    inputs = logger_a_data.get("connections", {}).get("inputs", [])
    assert any(c.get("source_node_id") == start for c in inputs), \
        "logger_a should receive input from start"


def test_prune_three_branches_keeps_middle():
    wm, factory = _make_wm()
    wm.create_new("prune_three")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(branch, {"branch_count": 3})
    node_a = wm.add_node("logger_node", alias="A")
    node_b = wm.add_node("logger_node", alias="B")
    node_c = wm.add_node("logger_node", alias="C")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", node_a, "input")
    wm.connect(branch, "path_b", node_b, "input")
    wm.connect(branch, "path_c", node_c, "input")

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    pruned = adapter.prune_branch_tombstone(branch, "path_b")

    assert pruned == 2
    assert wm.get_node_data(node_b) is not None
    assert wm.get_node_data(node_a) is None
    assert wm.get_node_data(node_c) is None


def test_prune_multi_hop_path_removes_chain():
    """Non-kept branch has two chained nodes — both should be pruned."""
    wm, factory = _make_wm()
    wm.create_new("prune_chain")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(branch, {"branch_count": 2})
    keeper = wm.add_node("logger_node", alias="Keep")
    first = wm.add_node("logger_node", alias="First")
    second = wm.add_node("logger_node", alias="Second")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", keeper, "input")
    wm.connect(branch, "path_b", first, "input")
    wm.connect(first, "default", second, "input")

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 2
    assert wm.get_node_data(keeper) is not None
    assert wm.get_node_data(first) is None
    assert wm.get_node_data(second) is None


# ---------------------------------------------------------------------------
# Materialized tombstone (saved and reloaded)
# ---------------------------------------------------------------------------

def test_prune_materialized_tombstone():
    wm, factory = _make_wm()
    wm.create_new("prune_mat")
    start, branch, logger_a, logger_b = _build_branch_workflow(wm)

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    adapter.materialize_deleted_nodes()  # converts to tombstone_node

    tombstone = wm.get_node_data(branch)
    assert tombstone["type"] == "tombstone_node"

    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 1
    assert wm.get_node_data(branch) is None
    assert wm.get_node_data(logger_a) is not None
    assert wm.get_node_data(logger_b) is None


def test_prune_materialized_rewires_upstream():
    wm, factory = _make_wm()
    wm.create_new("prune_mat_rewire")
    start, branch, logger_a, logger_b = _build_branch_workflow(wm)

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    adapter.materialize_deleted_nodes()
    adapter.prune_branch_tombstone(branch, "path_a")

    start_data = wm.get_node_data(start)
    outputs = start_data.get("connections", {}).get("outputs", [])
    assert any(c.get("target_node_id") == logger_a for c in outputs)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_prune_returns_minus_one_for_non_placeholder():
    wm, factory = _make_wm()
    wm.create_new("prune_bad")
    start = wm.add_node("start_node")

    adapter = _adapter(wm, factory)
    result = adapter.prune_branch_tombstone(start, "path_a")
    assert result == -1


def test_prune_returns_minus_one_for_non_branch_tombstone():
    wm, factory = _make_wm()
    wm.create_new("prune_bad2")
    logger = wm.add_node("logger_node")

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(logger)
    result = adapter.prune_branch_tombstone(logger, "path_a")
    assert result == -1


def test_prune_empty_branch_no_crash():
    """path_b has no connected downstream — should still remove tombstone cleanly."""
    wm, factory = _make_wm()
    wm.create_new("prune_empty")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(branch, {"branch_count": 2})
    keeper = wm.add_node("logger_node", alias="Keep")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", keeper, "input")
    # path_b intentionally left unconnected

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 0
    assert wm.get_node_data(branch) is None
    assert wm.get_node_data(keeper) is not None


def test_prune_merge_node_not_deleted():
    """A merge_node with another live feed (node_a/keeper, outside this
    prune) is a true stop: only the pruned-branch chain is removed."""
    wm, factory = _make_wm()
    wm.create_new("prune_merge_stop")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(branch, {"branch_count": 2})
    node_a = wm.add_node("logger_node", alias="A")
    node_b = wm.add_node("logger_node", alias="B")
    merge = wm.add_node("merge_node", alias="Merge")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", node_a, "input")
    wm.connect(branch, "path_b", node_b, "input")
    wm.connect(node_a, "default", merge, "path_a")
    wm.connect(node_b, "default", merge, "path_b")

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 1, "only node_b should be pruned, not the merge_node"
    assert wm.get_node_data(merge) is not None
    assert wm.get_node_data(node_b) is None


def test_prune_pruned_branch_merge_beacon_is_deleted_not_orphaned():
    """A Merge Beacon belongs to the one branch it closes — pruning that
    branch must delete the beacon too, not leave it dangling with zero
    connections. merge_node (still fed by the surviving kept branch via
    its own path into the merge) must survive."""
    wm, factory = _make_wm()
    wm.create_new("prune_beacon_owned")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(branch, {"branch_count": 2})
    keeper = wm.add_node("logger_node", alias="Keep")
    merge = wm.add_node("merge_node", alias="Merge")
    beacon = wm.add_node("branch_end_node", alias="Merge Beacon")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", keeper, "input")
    wm.connect(branch, "path_b", beacon, "input")
    wm.connect(keeper, "default", merge, "path_a")
    wm.connect(beacon, "default", merge, "path_b")

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 1, "the beacon on the pruned path_b branch should be pruned"
    assert wm.get_node_data(beacon) is None
    assert wm.get_node_data(merge) is not None
    assert wm.get_node_data(keeper) is not None


def test_prune_orphaned_merge_node_with_no_other_feed_is_also_pruned():
    """If the pruned branch was a merge_node's ONLY input, the merge_node has
    nothing left to merge and must be pruned too (cascading into its own
    downstream), instead of being left behind as a disconnected orphan that
    the validator flags as unreachable."""
    wm, factory = _make_wm()
    wm.create_new("prune_orphan_merge")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(branch, {"branch_count": 2})
    keeper = wm.add_node("logger_node", alias="Keep")
    merge = wm.add_node("merge_node", alias="Merge")
    after_merge = wm.add_node("logger_node", alias="AfterMerge")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", keeper, "input")
    wm.connect(branch, "path_b", merge, "path_a")
    wm.connect(merge, "default", after_merge, "input")

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 2, "merge_node and after_merge should both be pruned"
    assert wm.get_node_data(merge) is None
    assert wm.get_node_data(after_merge) is None
    assert wm.get_node_data(keeper) is not None


def test_prune_merge_node_survives_when_another_branch_still_feeds_it():
    """A merge_node fed by a surviving branch (outside this prune entirely)
    must not be pruned even though this branch's path into it is removed."""
    wm, factory = _make_wm()
    wm.create_new("prune_merge_survives")
    start = wm.add_node("start_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(branch, {"branch_count": 2})
    keeper = wm.add_node("logger_node", alias="Keep")
    merge = wm.add_node("merge_node", alias="Merge")
    other_feed = wm.add_node("logger_node", alias="OtherFeed")
    wm.connect(start, "default", branch, "input")
    wm.connect(branch, "path_a", keeper, "input")
    wm.connect(branch, "path_b", merge, "path_a")
    wm.connect(other_feed, "default", merge, "path_b")

    adapter = _adapter(wm, factory)
    adapter.replace_with_placeholder(branch)
    pruned = adapter.prune_branch_tombstone(branch, "path_a")

    assert pruned == 0, "merge_node still has a surviving feed; nothing to prune"
    assert wm.get_node_data(merge) is not None
    assert wm.get_node_data(other_feed) is not None
    assert wm.get_node_data(keeper) is not None

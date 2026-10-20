"""Approved deletion groups: topology, durable recovery and modal cancellation."""

from copy import deepcopy
import json

import pytest

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from backend.validator import validate_workflow
from frontend.editor_workflow_adapter import EditorWorkflowAdapter


class Graph:
    def __init__(self):
        self.factory = NodeFactory()
        self.map = WorkflowMap(self.factory, EventBus())
        self.map.create_new("Delete tests")
        self.adapter = EditorWorkflowAdapter(self.map, self.factory)
        self.ids = {}
        self.add("start", "start_node")

    def add(self, name, kind="echo_node", **config):
        nid = self.map.add_node(kind, alias=name)
        self.ids[name] = nid
        if config:
            self.map.update_node_config(
                nid, {**self.map.get_node_data(nid)["config"], **config}
            )
        return nid

    def wire(self, a, b, port="default", target="input"):
        self.map.connect(self.ids[a], port, self.ids[b], target)
        return self

    def snapshot(self):
        return deepcopy(self.map.get_all_node_data())

    def delete(self, name, keep=None):
        p = self.adapter.plan_deletion(self.ids[name], keep)
        self.adapter.apply_plan(p)
        return p

    def restore(self, name):
        p = self.adapter.plan_restore(self.ids[name])
        self.adapter.apply_plan(p)
        return p

    def reload(self):
        self.map.load_data(
            json.loads(json.dumps(self.map.get_workflow_data_for_save()))
        )
        self.adapter = EditorWorkflowAdapter(self.map, self.factory)


def fan(count=4):
    g = Graph()
    g.add(
        "fan",
        "branch_node",
        branch_count=count,
        **{f"path_{chr(97+i)}_label": f"Path {i}" for i in range(count)},
        branch_payload_sources={f"path_{chr(97+i)}": f"key{i}" for i in range(count)},
    )
    g.wire("start", "fan")
    for i in range(count):
        n = chr(97 + i)
        g.add(n)
        g.add(n + "end", "end_node")
        g.wire("fan", n, "path_" + n).wire(n, n + "end")
    return g


@pytest.mark.parametrize("reload", [False, True])
def test_branch_delete_is_one_blocking_group_and_restores_all_members(reload):
    g = fan()
    before = g.snapshot()
    p = g.adapter.plan_deletion(g.ids["fan"], "path_d")
    assert g.snapshot() == before
    g.adapter.apply_plan(p)
    assert g.map.get_node_data(g.ids["fan"])["type"] == "tombstone_node"
    assert set(p["removed"]) == {
        g.ids[n] for n in ("a", "aend", "b", "bend", "c", "cend")
    }
    assert not validate_workflow(g.map, g.factory)["success"]
    if reload:
        g.reload()
    g.restore("fan")
    assert g.snapshot() == before


def test_disconnected_external_parent_protects_shared_descendants():
    g = fan(2)
    g.add("outside")
    g.wire("outside", "b")
    g.delete("fan", "path_a")
    assert g.map.get_node_data(g.ids["b"]) and g.map.get_node_data(g.ids["bend"])
    assert g.map.find_next_node_id(g.ids["outside"]) == g.ids["b"]


def test_two_dropped_paths_share_tail_but_end_is_a_boundary():
    g = fan()
    g.add("tail")
    g.add("beyond")
    g.wire("b", "tail").wire("c", "tail").wire("bend", "beyond")
    p = g.delete("fan", "path_a")
    assert g.ids["tail"] in p["removed"]
    assert g.map.get_node_data(g.ids["beyond"])
    restored = g.restore("fan")
    # The intentionally malformed End output is archived, but cannot be revived.
    assert restored["conflicts"]
    assert g.map.find_next_node_id(g.ids["bend"]) is None


def test_resolver_group_keeps_no_error_and_restores_shared_tail():
    g = Graph()
    g.add(
        "mux",
        "error_mux_node",
        routes=[{"id": "r1", "codes": ["one"]}, {"id": "r2", "codes": ["two"]}],
    )
    for n in ("ok", "bad1", "bad2", "tail"):
        g.add(n)
    g.wire("start", "mux").wire("mux", "ok").wire("mux", "bad1", "r1").wire(
        "mux", "bad2", "r2"
    )
    g.wire("bad1", "tail").wire("bad2", "tail")
    before = g.snapshot()
    p = g.delete("mux")
    assert set(p["removed"]) == {g.ids[n] for n in ("bad1", "bad2", "tail")}
    g.restore("mux")
    assert g.snapshot() == before


@pytest.mark.parametrize("reload", [False, True])
def test_beacon_removal_never_bypasses_into_merge(reload):
    g = Graph()
    g.add("beacon", "branch_end_node")
    g.add("merge", "merge_node")
    g.wire("start", "beacon").wire("beacon", "merge", target="path_a")
    g.delete("beacon")
    if reload:
        g.reload()
    g.adapter.apply_plan(g.adapter.plan_remove_group(g.ids["beacon"]))
    assert g.map.find_next_node_id(g.ids["start"]) is None
    assert not g.map.get_node_data(g.ids["merge"])["connections"]["inputs"]


def test_merge_delete_resets_all_beacons_including_other_targets():
    g = Graph()
    for n, t in [
        ("merge", "merge_node"),
        ("other", "merge_node"),
        ("beacon", "branch_end_node"),
        ("out", "end_node"),
    ]:
        g.add(n, t)
    g.wire("start", "merge", target="path_a").wire("merge", "out")
    g.wire("beacon", "merge", target="path_b").wire("beacon", "other", target="path_a")
    before = g.snapshot()
    g.delete("merge")
    assert not g.map.get_node_data(g.ids["beacon"])["connections"]["outputs"]
    assert not g.map.get_node_data(g.ids["other"])["connections"]["inputs"]
    g.restore("merge")
    assert g.snapshot() == before


def test_partial_restore_preserves_new_wiring_and_keeps_pending_record():
    g = fan(2)
    g.delete("fan", "path_a")
    g.add("replacement")
    g.map.disconnect(g.ids["start"], "default", g.ids["fan"], "input")
    g.wire("start", "replacement")
    p = g.adapter.plan_restore(g.ids["fan"])
    assert p["conflicts"]
    g.adapter.apply_plan(p)
    assert g.map.find_next_node_id(g.ids["start"]) == g.ids["replacement"]
    assert g.map.get_node_data(g.ids["b"])
    assert g.map.get_node_data(g.ids["fan"])["config"]["delete_recovery"]


def test_stale_plan_and_future_versions_do_not_change_graph():
    g = fan(2)
    p = g.adapter.plan_deletion(g.ids["fan"], "path_a")
    g.add("new")
    before = g.snapshot()
    with pytest.raises(ValueError, match="changed"):
        g.adapter.apply_plan(p)
    assert g.snapshot() == before
    g.delete("fan", "path_a")
    g.map.get_node_data(g.ids["fan"])["config"]["delete_group"]["version"] = 999
    before = g.snapshot()
    with pytest.raises(ValueError, match="version"):
        g.adapter.plan_restore(g.ids["fan"])
    assert g.snapshot() == before


def reduced(g):
    result = {
        "alias": "Renamed",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 2},
    }
    g.adapter.apply_plan(
        g.adapter.plan_branch_count(g.ids["fan"], result, ["path_a", "path_d"])
    )


def test_reduction_archives_paths_preserving_arbitrary_labels_and_payloads():
    g = fan()
    reduced(g)
    n = g.map.get_node_data(g.ids["fan"])
    assert n["alias"] == "Renamed" and n["config"]["path_b_label"] == "Path 3"
    assert n["config"]["branch_payload_sources"]["path_b"] == "key3"
    assert g.map.find_next_node_id(g.ids["fan"], "path_b") == g.ids["d"]
    assert g.map.get_node_data(g.ids["b"]) is None
    g.reload()
    entries = g.adapter.saved_paths(g.ids["fan"])
    assert [e["label"] for e in entries] == ["Path 1", "Path 2"]
    assert g.map.get_node_data(g.ids["fan"])["type"] == "branch_node"
    result = {
        "alias": "Renamed",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 3},
    }
    g.adapter.apply_plan(
        g.adapter.plan_recover_paths(g.ids["fan"], result, [entries[1]["id"]])
    )
    assert g.map.find_next_node_id(g.ids["fan"], "path_c") == g.ids["c"]
    assert g.map.get_node_data(g.ids["cend"])
    assert [e["id"] for e in g.adapter.saved_paths(g.ids["fan"])] == [entries[0]["id"]]


def test_recovery_may_leave_new_paths_empty_and_preserves_unselected_entries():
    g = fan()
    reduced(g)
    entries = deepcopy(g.adapter.saved_paths(g.ids["fan"]))
    result = {
        "alias": "Renamed",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 3},
    }
    g.adapter.apply_plan(g.adapter.plan_recover_paths(g.ids["fan"], result, []))
    assert g.adapter.saved_paths(g.ids["fan"]) == entries
    assert g.map.find_next_node_id(g.ids["fan"], "path_c") is None


def test_final_remove_uses_stored_route_without_rewalking_live_nodes():
    g = fan(2)
    g.delete("fan", "path_a")
    g.add("new")
    g.wire("a", "new")
    g.adapter.apply_plan(g.adapter.plan_remove_group(g.ids["fan"]))
    assert g.map.get_node_data(g.ids["new"])
    assert g.map.find_next_node_id(g.ids["start"]) == g.ids["a"]


def test_group_serialization_helpers_keep_versioned_record():
    from frontend.editor_workflow_adapter import (
        tombstone_config_from_metadata,
        metadata_from_tombstone_config,
    )

    record = {"version": 1, "before": {}, "after": {}}
    metadata = {"original_type": "echo_node", "delete_group": record}
    assert (
        metadata_from_tombstone_config(tombstone_config_from_metadata(metadata))[
            "delete_group"
        ]
        == record
    )


def test_ordinary_node_delete_and_original_replacement_restore_whole_handler_group():
    g = Graph()
    g.add("work")
    g.add("mux", "error_mux_node", routes=[{"id": "r1", "codes": ["one"]}])
    g.add("bad")
    g.add("ok")
    g.wire("start", "work").wire("work", "mux").wire("mux", "bad", "r1").wire(
        "mux", "ok"
    )
    before = g.snapshot()
    g.delete("work")
    assert g.map.get_node_data(g.ids["bad"]) is None
    result = g.adapter.replace_placeholder(g.ids["work"], "echo_node")
    assert result["restored_original"]
    assert g.snapshot() == before


def test_soft_deleted_nested_member_returns_as_pending_tombstone():
    g = fan(2)
    g.adapter.replace_with_placeholder(g.ids["b"])
    g.delete("fan", "path_a")
    g.reload()
    g.restore("fan")
    assert g.adapter.is_placeholder(g.ids["b"])
    assert g.map.get_node_data(g.ids["b"])["config"]["original_type"] == "echo_node"


def test_legacy_selected_stub_restore_keeps_group_members():
    g = fan(2)
    before = g.snapshot()
    g.delete("fan", "path_a")
    assert g.adapter.undo_placeholder(g.ids["fan"])
    assert g.snapshot() == before


def test_recover_low_numbered_old_path_into_new_port_without_duplicate_old_link():
    g = fan()
    reduced(g)
    entries = g.adapter.saved_paths(g.ids["fan"])
    result = {
        "alias": "fan",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 3},
    }
    plan = g.adapter.plan_recover_paths(g.ids["fan"], result, [entries[0]["id"]])
    assert not plan["conflicts"]
    g.adapter.apply_plan(plan)
    assert g.map.find_next_node_id(g.ids["fan"], "path_b") == g.ids["d"]
    assert g.map.find_next_node_id(g.ids["fan"], "path_c") == g.ids["b"]
    assert len(g.adapter.saved_paths(g.ids["fan"])) == 1


def test_occupied_saved_member_is_never_wired_into_the_restored_group():
    g = fan(2)
    g.delete("fan", "path_a")
    payload = g.map.get_workflow_data_for_save()
    payload["nodes"][g.ids["b"]] = {
        "type": "echo_node",
        "alias": "Replacement",
        "config": {"message": "new"},
        "connections": {"inputs": [], "outputs": []},
    }
    g.map.load_data(payload)
    plan = g.adapter.plan_restore(g.ids["fan"])
    assert plan["conflicts"]
    g.adapter.apply_plan(plan)
    assert g.map.find_next_node_id(g.ids["fan"], "path_b") is None
    assert g.map.get_node_data(g.ids["b"])["alias"] == "Replacement"


def test_second_reduction_keeps_prior_archive_without_nesting_it_in_new_group():
    g = fan()
    reduced(g)
    result = {
        "alias": "fan",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 4},
    }
    g.adapter.apply_plan(g.adapter.plan_recover_paths(g.ids["fan"], result, []))
    result["config"] = {
        **g.map.get_node_data(g.ids["fan"])["config"],
        "branch_count": 2,
    }
    g.adapter.apply_plan(
        g.adapter.plan_branch_count(g.ids["fan"], result, ["path_a", "path_b"])
    )
    archive = g.map.get_node_data(g.ids["fan"])["config"]["branch_recovery"]
    assert len(archive["entries"]) == 4
    for record in archive["groups"].values():
        assert "branch_recovery" not in record["before"][g.ids["fan"]]["config"]


def test_group_replacement_discards_archive_only_after_a_checked_plan():
    g = fan(2)
    g.delete("fan", "path_a")
    before = g.snapshot()
    p = g.adapter.plan_replace_group(g.ids["fan"], "echo_node")
    assert g.snapshot() == before
    g.adapter.apply_plan(p)
    assert g.map.get_node_data(g.ids["fan"])["type"] == "echo_node"
    assert "delete_group" not in g.map.get_node_data(g.ids["fan"])["config"]
    assert g.map.find_next_node_id(g.ids["fan"]) == g.ids["a"]
    assert g.map.get_node_data(g.ids["b"]) is None


def test_dropped_beacons_prune_an_orphan_merge_and_its_downstream_as_one_group():
    g = fan(3)
    for n in ("b", "c"):
        g.map.delete_node(g.ids[n + "end"])
        g.add(n + "beacon", "branch_end_node")
        g.wire(n, n + "beacon")
    g.add("merge", "merge_node")
    g.add("tail")
    g.wire("bbeacon", "merge", target="path_a").wire(
        "cbeacon", "merge", target="path_b"
    ).wire("merge", "tail")
    before = g.snapshot()
    p = g.delete("fan", "path_a")
    assert {g.ids["merge"], g.ids["tail"]} <= set(p["removed"])
    g.restore("fan")
    assert g.snapshot() == before


def test_group_operation_preserves_unrelated_invalid_edges_for_validation():
    g = fan(2)
    g.add("outside")
    g.map.get_node_data(g.ids["outside"])["connections"]["outputs"].append(
        {
            "source_port": "missing",
            "target_node_id": "missing-node",
            "target_port": "input",
        }
    )
    before = deepcopy(g.map.get_node_data(g.ids["outside"]))
    g.delete("fan", "path_a")
    assert g.map.get_node_data(g.ids["outside"]) == before
    g.restore("fan")
    assert g.map.get_node_data(g.ids["outside"]) == before


def test_recovery_reinstates_merge_selection_for_only_the_chosen_saved_path():
    g = fan()
    for n in ("b", "c"):
        g.map.delete_node(g.ids[n + "end"])
        g.add(n + "beacon", "branch_end_node")
        g.wire(n, n + "beacon")
    g.add(
        "merge",
        "merge_node",
        branches_to_close=[g.ids["fan"] + ":path_b", g.ids["fan"] + ":path_c"],
    )
    g.add("outside")
    g.wire("outside", "merge", target="path_a")
    g.wire("bbeacon", "merge", target="path_b").wire(
        "cbeacon", "merge", target="path_c"
    )
    reduced(g)
    entries = g.adapter.saved_paths(g.ids["fan"])
    result = {
        "alias": "fan",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 3},
    }
    g.adapter.apply_plan(
        g.adapter.plan_recover_paths(g.ids["fan"], result, [entries[0]["id"]])
    )
    assert g.map.get_node_data(g.ids["merge"])["config"]["branches_to_close"] == [
        g.ids["fan"] + ":path_c"
    ]


def test_partial_path_recovery_does_not_offer_the_same_head_twice():
    g = fan()
    reduced(g)
    entry = g.adapter.saved_paths(g.ids["fan"])[0]
    payload = g.map.get_workflow_data_for_save()
    payload["nodes"][g.ids["bend"]] = {
        "type": "echo_node",
        "alias": "Replacement",
        "config": {},
        "connections": {"inputs": [], "outputs": []},
    }
    g.map.load_data(payload)
    result = {
        "alias": "fan",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 3},
    }
    plan = g.adapter.plan_recover_paths(g.ids["fan"], result, [entry["id"]])
    assert plan["conflicts"]
    g.adapter.apply_plan(plan)
    assert g.map.find_next_node_id(g.ids["fan"], "path_c") == g.ids["b"]
    assert len(g.adapter.saved_paths(g.ids["fan"])) == 1
    assert g.map.get_node_data(g.ids["fan"])["config"]["delete_recovery"]


def test_recovering_loop_keeps_back_edge_and_does_not_walk_forever():
    g = fan()
    g.map.get_node_data(g.ids["bend"])["type"] = "echo_node"
    g.wire("bend", "fan")
    reduced(g)
    entry = g.adapter.saved_paths(g.ids["fan"])[0]
    result = {
        "alias": "fan",
        "config": {**g.map.get_node_data(g.ids["fan"])["config"], "branch_count": 3},
    }
    plan = g.adapter.plan_recover_paths(g.ids["fan"], result, [entry["id"]])
    g.adapter.apply_plan(plan)
    assert g.map.find_next_node_id(g.ids["fan"], "path_c") == g.ids["b"]
    assert g.map.find_next_node_id(g.ids["bend"]) == g.ids["fan"]


def test_missing_payload_source_uses_the_standard_dead_drop_value():
    g = fan()
    config = g.map.get_node_data(g.ids["fan"])["config"]
    config["branch_payload_sources"] = {}
    reduced(g)
    assert set(
        g.map.get_node_data(g.ids["fan"])["config"]["branch_payload_sources"].values()
    ) == {"dead_drop:input"}


def test_partial_restore_can_finish_after_conflict_is_repaired_and_reloaded():
    g = fan(2)
    original = g.snapshot()
    g.delete("fan", "path_a")
    g.add("replacement")
    g.map.disconnect(g.ids["start"], "default", g.ids["fan"], "input")
    g.wire("start", "replacement")
    g.adapter.apply_plan(g.adapter.plan_restore(g.ids["fan"]))
    g.reload()
    g.map.disconnect(g.ids["start"], "default", g.ids["replacement"], "input")
    plan = g.adapter.plan_restore(g.ids["fan"])
    assert not plan["conflicts"]
    g.adapter.apply_plan(plan)
    assert g.map.find_next_node_id(g.ids["start"]) == g.ids["fan"]
    assert g.map.get_node_data(g.ids["b"]) == original[g.ids["b"]]
    assert "delete_recovery" not in g.map.get_node_data(g.ids["fan"])["config"]

"""C2: saved values, the persistent store built on the Stash's (owner, 2026-10-21).

Remember, Recall and If changed keep values between runs in
``<data dir>/stash/saved.json``. Every test points the Stash folder at its own
temporary folder, never the owner's.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_saved_values.py -v
"""

import asyncio
import io
import json
import multiprocessing
from datetime import datetime, timedelta, timezone

import pytest

from backend import persistence
from backend import saved_values as saved
from backend.event_bus import EventBus
from backend.file_refs import file_reference
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_factory import NodeFactory
from tests.test_subworkflow_calls import Flow, _isolated, run  # noqa: F401

FACTORY = NodeFactory()


@pytest.fixture(autouse=True)
def _stash_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "STASH_DIR", tmp_path / "stash")
    monkeypatch.setattr(saved, "RUN_FROM", "app")
    return tmp_path / "stash"


def execute(node_type, inputs=None, vault=None, workflow="Release watch", **config):
    """Run one node outside a run; return (done payloads, errors, memory)."""
    node = FACTORY.create_node(node_type, "n1")
    node.config.update(config)
    memory = MemoryBank(EventBus())
    for key, value in (vault or {}).items():
        memory.store_persistent(key, value)
    done, errors = [], []
    context = NodeContext(
        node_id="n1", branch_id="S1", run_id="run_1", inputs=inputs if inputs is not None else {},
        memory_bank=memory, signal_done=done.append, signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None, wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda *args: None, workflow_name=workflow, node_alias="Keep it",
    )
    asyncio.run(node.execute(context))
    return done, errors, memory


def here(workflow="Release watch"):
    return saved.workflow_place(workflow)


# -- the store -------------------------------------------------------------------------------

def test_a_saved_value_records_its_type_place_and_who_saved_it(_stash_dir):
    store = saved.SavedValues()
    record = store.save(here(), "last_version", "v0.14.2",
                        {"node": "New version?", "node_id": "n9", "run_id": "r1", "from": "command line"})
    data = json.loads((_stash_dir / "saved.json").read_text())
    assert data["format"] == "aotn-saved/1"
    [stored] = data["values"]
    assert stored == record
    assert stored["id"].startswith("saved_") and stored["type"] == "string"
    assert stored["place"] == {"kind": "workflow", "workflow": "Release watch"}
    assert stored["saved_by"]["from"] == "command line"
    assert stored["created"] == stored["updated"]


@pytest.mark.parametrize("value, kind", [
    ("text", "string"), (3, "number"), (2.5, "number"), (True, "bool"), ([1, 2], "var"),
    ({"a": 1}, "var"), (None, "var"), (file_reference("/tmp/x.csv"), "file"),
])
def test_types_come_from_the_value(value, kind):
    assert saved.type_of(value) == kind


def test_names_ignore_case_and_places_are_separate():
    store = saved.SavedValues()
    store.save(here(), "Count", 1)
    store.save(here(), "count", 2)
    store.save(here("Other"), "count", 3)
    store.save(saved.all_place(), "count", 4)
    assert len(store.list_values()) == 3
    assert store.get(here(), "COUNT")["value"] == 2
    assert store.get(here("Other"), "count")["value"] == 3
    assert store.get(saved.all_place(), "count")["value"] == 4
    # All workflows first, then each workflow by name.
    assert [saved.place_label(r["place"]) for r in store.list_values()] == [
        "All workflows", "Other", "Release watch"]


def test_blank_names_and_big_values_are_refused():
    store = saved.SavedValues()
    with pytest.raises(saved.SavedValuesError):
        store.save(here(), "  ", 1)
    with pytest.raises(saved.SavedValuesError) as big:
        store.save(here(), "big", "x" * (saved.MAX_BYTES + 1))
    assert big.value.code == "too_big"
    with pytest.raises(saved.SavedValuesError) as odd:
        store.save(here(), "odd", object())
    assert odd.value.code == "too_big"


def test_an_unreadable_file_is_never_overwritten(_stash_dir):
    _stash_dir.mkdir(parents=True)
    (_stash_dir / "saved.json").write_text("{not json")
    store = saved.SavedValues()
    with pytest.raises(saved.SavedValuesError) as exc:
        store.save(here(), "x", 1)
    assert exc.value.code == "store_unreadable"
    assert (_stash_dir / "saved.json").read_text() == "{not json"


def test_add_counts_from_zero_and_refuses_text():
    store = saved.SavedValues()
    assert store.add(here(), "runs", 1)["value"] == 1
    assert store.add(here(), "runs", 2.5)["value"] == 3.5
    store.save(here(), "word", "hello")
    with pytest.raises(saved.SavedValuesError) as exc:
        store.add(here(), "word", 1)
    assert exc.value.code == "not_a_number"


def test_check_and_save_reports_first_run_changes_and_no_change():
    store = saved.SavedValues()
    assert store.check_and_save(here(), "v", "1.0")[0] is None
    assert store.check_and_save(here(), "v", "1.0")[0] is False
    changed, previous = store.check_and_save(here(), "v", "1.1")
    assert changed is True and previous["value"] == "1.0"
    assert store.get(here(), "v")["value"] == "1.1"
    # Loosely: spaces and capitals don't count.
    assert store.check_and_save(here(), "v", " 1.1 ", loosely=True)[0] is False
    assert store.check_and_save(here(), "t", "Hello World")[0] is None
    assert store.check_and_save(here(), "t", "helloworld", loosely=True)[0] is False
    # The new value is saved even when it counts as no change.
    assert store.get(here(), "t")["value"] == "helloworld"
    assert store.check_and_save(here(), "t", "HelloWorld")[0] is True
    # Exactly compares types too: 1 and "1" differ.
    store.save(here(), "n", 1)
    assert store.check_and_save(here(), "n", "1")[0] is True


def test_every_call_reads_the_file_so_another_process_is_seen(_stash_dir):
    first, second = saved.SavedValues(), saved.SavedValues()
    first.save(here(), "a", 1)
    assert second.get(here(), "a")["value"] == 1
    second.save(here(), "b", 2)
    first.save(here(), "a", 3)
    assert {r["name"]: r["value"] for r in saved.SavedValues().list_values()} == {"a": 3, "b": 2}


def _count(folder, times, windows_lock=False):
    # Spawn never inherits a parent's monkeypatches or live UI/logger threads.
    if windows_lock:
        saved.fcntl = None
        saved.msvcrt = _FcntlBackedMsvcrt()
    store = saved.SavedValues(folder)
    for _ in range(times):
        store.add(saved.all_place(), "runs", 1)
        store.save(saved.all_place(), f"own_{multiprocessing.current_process().name}", 1)


def test_two_processes_at_once_lose_no_counts_or_names(_stash_dir):
    # Cron and the app at the same moment: each change is one locked step.
    context = multiprocessing.get_context("spawn")
    workers = [context.Process(target=_count, args=(_stash_dir, 40), name=f"w{i}") for i in range(3)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(30)
        assert worker.exitcode == 0
    values = {r["name"]: r["value"] for r in saved.SavedValues(_stash_dir).list_values()}
    assert values["runs"] == 120
    assert {"own_w0", "own_w1", "own_w2"} <= set(values)


def test_move_workflow_takes_values_along_but_never_overwrites(_stash_dir):
    store = saved.SavedValues()
    store.save(here("Old"), "a", 1)
    store.save(here("Old"), "b", 2)
    store.save(here("New"), "b", 99)
    assert store.move_workflow("Old", "New") == 1
    assert store.get(here("New"), "a")["value"] == 1
    assert store.get(here("New"), "b")["value"] == 99
    assert store.get(here("Old"), "b")["value"] == 2


def test_move_workflow_leaves_the_file_alone_when_nothing_matches(_stash_dir):
    store = saved.SavedValues()
    store.save(here("Other"), "a", 1)
    before = (_stash_dir / "saved.json").stat().st_mtime_ns
    assert store.move_workflow("Nope", "Still nope") == 0
    assert (_stash_dir / "saved.json").stat().st_mtime_ns == before


@pytest.mark.parametrize("text, kind, value", [
    ("12", "number", 12), ("1.5", "number", 1.5), ("yes", "bool", True), ("false", "bool", False),
    ("[1, 2]", "var", [1, 2]), ("hi there", "string", "hi there"),
])
def test_typed_text_parses_by_type(text, kind, value):
    assert saved.parse_typed(text, kind) == value


@pytest.mark.parametrize("text, kind", [("twelve", "number"), ("maybe", "bool"), ("[1,", "var"),
                                        ('"x"', "file")])
def test_typed_text_refuses_the_wrong_type(text, kind):
    with pytest.raises(saved.SavedValuesError):
        saved.parse_typed(text, kind)


# -- Remember --------------------------------------------------------------------------------

def test_remember_saves_the_incoming_value_and_sends_it_on():
    done, errors, _ = execute("remember_node", {"input": {"price": 41.2}}, name="last")
    assert not errors
    assert done[0]["data"] == {"default": {"price": 41.2}}
    record = saved.SavedValues().get(here(), "last")
    assert record["type"] == "var"
    assert record["saved_by"] == {"node": "Keep it", "node_id": "n1", "run_id": "run_1", "from": "app"}


def test_remember_add_counts_runs_with_a_configured_number():
    for expected in (1, 2, 3):
        done, errors, _ = execute("remember_node", name="runs", how="Add",
                                  input_source="Configured", value="1")
        assert not errors and done[0]["data"]["default"] == expected


def test_remember_add_refuses_text_with_not_a_number():
    _, errors, _ = execute("remember_node", {"input": "lots"}, name="runs", how="Add")
    assert errors[0].code == "not_a_number"


def test_remember_kept_for_all_workflows_is_shared():
    execute("remember_node", {"input": "shared"}, name="note", keep_for="All workflows", workflow="A")
    done, _, _ = execute("recall_node", name="note", keep_for="All workflows", workflow="B")
    assert done[0]["data"]["default"] == "shared"
    done, _, _ = execute("recall_node", name="note", workflow="B")
    assert done[0]["data"]["default"] == ""  # B's own value: nothing saved, starting value


def test_remember_reads_a_vault_key_and_writes_a_vault_copy():
    done, errors, memory = execute("remember_node", vault={"seen": 7}, name="seen",
                                   input_source="Vault", input_vault_key="seen",
                                   vault_write=True, vault_write_key="copy")
    assert not errors
    assert memory.read_persistent("copy") == 7


def test_remember_stops_or_carries_on_when_it_cannot_save(_stash_dir):
    _stash_dir.mkdir(parents=True)
    (_stash_dir / "saved.json").write_text("broken")
    _, errors, _ = execute("remember_node", {"input": 1}, name="x")
    assert errors[0].code == "store_unreadable" and errors[0].retryable
    done, errors, _ = execute("remember_node", {"input": 1}, name="x", if_not_saved="Carry on")
    assert not errors and done[0]["data"]["default"] == 1


# -- Recall ----------------------------------------------------------------------------------

def test_recall_uses_the_starting_value_by_type_until_something_is_saved():
    done, errors, _ = execute("recall_node", name="runs", expect="number", starting_value="")
    assert not errors and done[0]["data"]["default"] == 0
    done, _, _ = execute("recall_node", name="runs", expect="number", starting_value="5")
    assert done[0]["data"]["default"] == 5
    done, _, _ = execute("recall_node", name="on", expect="bool")
    assert done[0]["data"]["default"] is False
    _, errors, _ = execute("recall_node", name="runs", expect="number", starting_value="five")
    assert errors[0].code == "wrong_type"


def test_recall_can_stop_when_nothing_is_saved():
    _, errors, _ = execute("recall_node", name="runs", if_missing="Stop with an error")
    assert errors[0].code == "not_saved"


def test_recall_is_strict_about_the_type():
    saved.SavedValues().save(here(), "v", "12")
    _, errors, _ = execute("recall_node", name="v", expect="number")
    assert errors[0].code == "wrong_type"
    done, errors, _ = execute("recall_node", name="v", expect="any")
    assert not errors and done[0]["data"]["default"] == "12"


def test_recall_output_type_follows_the_chosen_type():
    data = {"type": "recall_node", "config": {"expect": "number"}}
    assert FACTORY.node_output_port_metadata(data)["default"]["data_type"] == "number"
    data["config"]["expect"] = "any"
    assert FACTORY.node_output_port_metadata(data)["default"]["data_type"] == "any"


def test_recall_vault_copy_carries_the_type():
    saved.SavedValues().save(here(), "price", 41.2)
    _, errors, memory = execute("recall_node", name="price", expect="number",
                                vault_write=True, vault_write_key="price")
    assert not errors and memory.read_persistent("price") == 41.2


# -- If changed ------------------------------------------------------------------------------

def test_if_changed_first_run_is_no_change_by_default_then_reports_changes():
    def path(value, **config):
        done, errors, _ = execute("if_changed_node", {"input": value}, name="version", **config)
        assert not errors
        assert list(done[0]["data"]) == [done[0]["output_port"]]
        return done[0]["output_port"], done[0]["data"][done[0]["output_port"]]

    assert path("v1") == ("no_change", "v1")
    assert path("v1") == ("no_change", "v1")
    assert path("v2") == ("changed", "v2")
    assert path("v2") == ("no_change", "v2")


def test_if_changed_first_run_can_count_as_changed():
    done, _, _ = execute("if_changed_node", {"input": "v1"}, name="version", first_time="Changed")
    assert done[0]["output_port"] == "changed"


def test_if_changed_loosely_ignores_spaces_and_capitals():
    execute("if_changed_node", {"input": "Build OK"}, name="status", compare="Loosely")
    done, _, _ = execute("if_changed_node", {"input": "build ok "}, name="status", compare="Loosely")
    assert done[0]["output_port"] == "no_change"


def test_if_changed_stops_or_takes_no_change_when_it_cannot_save(_stash_dir):
    _stash_dir.mkdir(parents=True)
    (_stash_dir / "saved.json").write_text("broken")
    _, errors, _ = execute("if_changed_node", {"input": 1}, name="x")
    assert errors[0].code == "store_unreadable"
    done, errors, _ = execute("if_changed_node", {"input": 1}, name="x", if_not_saved="Carry on")
    assert not errors and done[0]["output_port"] == "no_change"


def test_if_changed_path_names_are_plain_fields():
    schema = FACTORY.get_node_class("if_changed_node").config_schema if hasattr(
        FACTORY, "get_node_class") else None
    metadata = {m["type"]: m for m in FACTORY.get_node_types_metadata()}["if_changed_node"]
    schema = schema or metadata["config_schema"]
    assert schema["changed_label"]["label"] == "Changed path name"
    assert schema["no_change_label"]["label"] == "No change path name"
    assert metadata["output_ports"] == ["changed", "no_change"]
    assert [metadata["output_port_metadata"][p]["name"] for p in ("changed", "no_change")] == [
        "Changed", "No change"]


def test_the_selector_groups_all_three_under_saved_values_in_utility():
    metadata = {m["type"]: m for m in FACTORY.get_node_types_metadata()}
    for node_type in ("remember_node", "recall_node", "if_changed_node"):
        assert metadata[node_type]["group"] == "Saved values"
        assert metadata[node_type]["primary_family"] == "Utility"


# -- whole runs ------------------------------------------------------------------------------

def _h3(first_time="No change"):
    """H3: Start → If changed → Changed: Remember went=changed / No change: Remember went=same."""
    flow = (Flow("Release watch").node("start", "start_node")
            .node("check", "if_changed_node", alias="New version?", name="version",
                  input_source="Vault", input_vault_key="version", first_time=first_time)
            .node("yes", "remember_node", name="went", input_source="Configured", value="changed")
            .node("no", "remember_node", name="went", input_source="Configured", value="same"))
    flow.link("start", "check")
    flow.link("check", "yes", port="changed")
    flow.link("check", "no", port="no_change")
    return flow


def test_h3_change_detector_runs_end_to_end():
    flow = _h3()
    start = flow.map.get_node_data(flow.ids["start"])
    flow.map.update_node_config(flow.ids["start"], {**start["config"], "rows": [
        {"id": "version", "name": "version", "type": "string", "value": "v1", "required": False,
         "to": "Vault"}]})
    workflow_id = flow.save()
    store = saved.SavedValues()

    def went(version):
        result, _ = run(workflow_id, inputs={"version": version})
        assert result.errors == []
        return store.get(here(), "went")["value"]

    assert went("v1") == "same"
    assert went("v1") == "same"
    assert went("v2") == "changed"
    record = store.get(here(), "version")
    assert record["value"] == "v2" and record["saved_by"]["node"] == "New version?"


def test_renaming_a_workflow_moves_its_values():
    from backend.save_manager import SaveManager

    flow = Flow("Release watch").node("start", "start_node")
    workflow_id = flow.save()
    saved.SavedValues().save(here("Release watch"), "version", "v2")
    assert SaveManager(flow.map).rename_workflow(workflow_id, "Hermes releases") is None
    assert saved.SavedValues().get(here("Hermes releases"), "version")["value"] == "v2"
    assert saved.SavedValues().get(here("Release watch"), "version") is None


# -- the CLI ---------------------------------------------------------------------------------

def cli(*argv):
    import aotn_stash

    out = io.StringIO()
    code = aotn_stash.main(["saved", *argv], stdout=out)
    return code, out.getvalue()


def test_cli_lists_shows_sets_and_forgets():
    assert cli("list") == (0, "Nothing is saved yet.\n")
    code, text = cli("set", "runs", "3", "--type", "number", "--workflow", "Release watch")
    assert code == 0 and "Saved 'runs' in Release watch" in text
    code, text = cli("set", "runs", "4", "--workflow", "Release watch")  # keeps the type
    assert saved.SavedValues().get(here(), "runs")["value"] == 4
    assert saved.SavedValues().get(here(), "runs")["saved_by"]["from"] == "command line"
    code, text = cli("list")
    assert code == 0 and "Release watch" in text and "runs" in text and "[number]" in text
    code, text = cli("show", "runs", "--workflow", "Release watch")
    assert code == 0 and json.loads(text)["value"] == 4
    assert cli("forget", "runs", "--workflow", "Release watch")[0] == 0
    code, text = cli("show", "runs", "--workflow", "Release watch")
    assert code == 1 and "Nothing is saved" in text


def test_cli_refuses_a_value_of_the_wrong_type():
    cli("set", "runs", "3", "--type", "number", "--all")
    code, text = cli("set", "runs", "three", "--all")
    assert code == 1 and "not a number" in text


def test_main_opens_the_app_on_another_data_folder(monkeypatch, tmp_path):
    import main

    seen = {}
    monkeypatch.setattr(main, "run_tui", lambda: seen.setdefault("dir", __import__("os").environ["AOTN_DATA_DIR"]))
    monkeypatch.delenv("AOTN_DATA_DIR", raising=False)
    main.main(["--data-dir", str(tmp_path / "cron")])
    assert seen["dir"] == str(tmp_path / "cron")
    assert main.main(["--data-dir"]) == 2


# -- the Stash screen, tab 3 -----------------------------------------------------------------

def test_when_reads_like_words():
    now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc).astimezone()
    from frontend.screens.stash import when

    stamp = lambda delta: (now - delta).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: E731
    assert when(stamp(timedelta(seconds=20)), now) == "just now"
    assert when(stamp(timedelta(minutes=2)), now) == "2 min ago"
    assert when(stamp(timedelta(days=1)), now) == "yesterday"
    assert when(stamp(timedelta(days=9)), now) == f"{(now - timedelta(days=9)):%Y-%m-%d}"
    assert when("not a time", now) == ""


def _stash_app(seen, steps):
    from textual.app import App

    from frontend.screens.stash import StashScreen

    class StashApp(App):
        def on_mount(self):
            self.push_screen(StashScreen(initial_tab="saved"))

    async def go():
        app = StashApp()
        async with app.run_test(size=(110, 34)) as pilot:
            await pilot.pause()
            for step in steps:
                await step(app, pilot, seen)
                await pilot.pause()

    asyncio.run(go())


def test_stash_tab_3_lists_values_under_their_places_and_skips_headings():
    store = saved.SavedValues()
    store.save(here("Price watch"), "last_price", 41.2,
               {"node": "Remember price", "node_id": "n", "run_id": "r", "from": "command line"})
    store.save(saved.all_place(), "runs_today", 7)
    seen = {}

    async def look(app, pilot, seen):
        screen = app.screen
        seen["rows"] = [r["name"] if r else None for r in screen.saved_shown]
        seen["highlighted"] = screen._saved_highlighted()["name"]
        await pilot.press("s")
        seen["after_s"] = screen._saved_highlighted()["name"]
        seen["detail"] = str(screen.query_one("#stash-saved-detail").render())
        seen["count"] = str(screen.query_one("#stash-saved-count").render())

    _stash_app(seen, [look])
    assert seen["rows"] == [None, "runs_today", None, "last_price"]
    assert seen["highlighted"] == "runs_today"
    assert seen["after_s"] == "last_price"  # the heading is skipped
    assert "saved by Remember price in Price watch" in seen["detail"]
    assert "from the command line" in seen["detail"]
    assert seen["count"] == "2 saved values in 2 places"


def test_stash_tab_3_changes_and_forgets_a_value():
    saved.SavedValues().save(here(), "version", "v1")

    async def change(app, pilot, seen):
        await pilot.press("e")
        await pilot.pause()
        prompt = app.screen
        field = prompt.query_one("#name-input")
        field.value = "v0"
        prompt.action_submit()

    async def forget(app, pilot, seen):
        seen["after_change"] = saved.SavedValues().get(here(), "version")
        await pilot.press("x")
        await pilot.pause()
        app.screen.dismiss(True)

    seen = {}
    _stash_app(seen, [change, forget])
    assert seen["after_change"]["value"] == "v0"
    assert seen["after_change"]["saved_by"]["from"] == "app"
    assert saved.SavedValues().get(here(), "version") is None


def test_stash_insert_mode_has_no_saved_values_tab():
    from textual.app import App
    from textual.widgets import TabPane

    from frontend.screens.stash import StashScreen

    seen = {}

    class InsertApp(App):
        def on_mount(self):
            self.push_screen(StashScreen(initial_tab="entries",
                                         insert_into={"label": "Path", "accepts": {"file"}}))

    async def go():
        app = InsertApp()
        async with app.run_test(size=(110, 34)) as pilot:
            await pilot.pause()
            seen["tabs"] = [pane.id for pane in app.screen.query(TabPane)]
            await pilot.press("3")
            seen["active"] = app.screen._active_tab()

    asyncio.run(go())
    assert "stash-tab-saved" not in seen["tabs"]
    assert seen["active"] == "stash-tab-entries"


def test_recall_payloads_tab_shows_the_chosen_type():
    from textual.app import App

    from backend.workflow_map import WorkflowMap
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("Types")
    node_id = workflow_map.add_node("recall_node")
    workflow_map.update_node_config(node_id, {**workflow_map.get_node_data(node_id)["config"],
                                              "name": "runs", "expect": "number"})
    seen = {}

    class ConfigApp(App):
        def on_mount(self):
            self.push_screen(NodeConfigScreen(FACTORY, workflow_map, node_id,
                                              workflow_map.get_node_data(node_id)))

    async def check():
        app = ConfigApp()
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            seen["header"] = str(app.screen.query_one("#downstream-header-default").render())

    asyncio.run(check())
    assert seen["header"] == "Saved value  [number]"


def test_a_blank_saved_as_is_a_validation_error():
    from backend.validator import validate_workflow

    flow = (Flow("Blank").node("start", "start_node").node("keep", "remember_node")
            .node("look", "recall_node", name="runs"))
    flow.link("start", "keep", "look")
    result = validate_workflow(flow.map, FACTORY)
    problems = [(e["node_id"], e["code"]) for e in result["errors"]]
    assert (flow.ids["keep"], "saved_name_missing") in problems
    assert (flow.ids["look"], "saved_name_missing") not in problems


# -- review of a308fa8 (Codex, #110): one regression test per finding ------------------------

class _FcntlBackedMsvcrt:
    """msvcrt.locking's interface, backed by a real lock, so the Windows path
    can be run (and raced) on Linux."""

    LK_NBLCK, LK_UNLCK = 2, 0

    def __init__(self):
        import fcntl as real

        self.real, self.calls = real, []

    def locking(self, fd, mode, nbytes):
        self.calls.append(mode)
        if mode == self.LK_NBLCK:
            self.real.flock(fd, self.real.LOCK_EX | self.real.LOCK_NB)  # OSError when held
        else:
            self.real.flock(fd, self.real.LOCK_UN)


def test_finding_1_no_lock_available_refuses_the_change(monkeypatch, _stash_dir):
    monkeypatch.setattr(saved, "fcntl", None)
    monkeypatch.setattr(saved, "msvcrt", None)
    with pytest.raises(saved.SavedValuesError) as exc:
        saved.SavedValues().save(here(), "a", 1)
    assert "no file lock" in str(exc.value)
    assert not (_stash_dir / "saved.json").exists()


def test_finding_1_windows_lock_is_taken_and_released(monkeypatch):
    fake = _FcntlBackedMsvcrt()
    monkeypatch.setattr(saved, "fcntl", None)
    monkeypatch.setattr(saved, "msvcrt", fake)
    saved.SavedValues().add(here(), "runs", 1)
    assert fake.calls == [fake.LK_NBLCK, fake.LK_UNLCK]


def test_finding_1_a_busy_windows_lock_times_out_without_writing(monkeypatch, _stash_dir):
    class Busy(_FcntlBackedMsvcrt):
        def locking(self, fd, mode, nbytes):
            raise OSError("locked")

    monkeypatch.setattr(saved, "fcntl", None)
    monkeypatch.setattr(saved, "msvcrt", Busy())
    monkeypatch.setattr(saved, "LOCK_WAIT", 0.1)
    with pytest.raises(saved.SavedValuesError) as exc:
        saved.SavedValues().save(here(), "a", 1)
    assert "busy" in str(exc.value) and exc.value.code == "store_unwritable"
    assert not (_stash_dir / "saved.json").exists()


def test_finding_1_two_processes_on_the_windows_lock_lose_no_counts(monkeypatch, _stash_dir):
    monkeypatch.setattr(saved, "fcntl", None)
    monkeypatch.setattr(saved, "msvcrt", _FcntlBackedMsvcrt())
    context = multiprocessing.get_context("spawn")
    workers = [context.Process(target=_count, args=(_stash_dir, 30, True), name=f"m{i}") for i in range(3)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(30)
        assert worker.exitcode == 0
    assert saved.SavedValues(_stash_dir).get(saved.all_place(), "runs")["value"] == 90


def _write_store(folder, values):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "saved.json").write_text(json.dumps({"format": saved.FORMAT, "values": values}))
    return (folder / "saved.json").read_bytes()


def _good(name="kept", value="v1", kind="string"):
    return {"id": f"saved_{name}", "name": name, "place": {"kind": "workflow", "workflow": "Release watch"},
            "type": kind, "value": value, "created": "2026-10-21T00:00:00Z",
            "updated": "2026-10-21T00:00:00Z", "saved_by": {"from": "app"}}


@pytest.mark.parametrize("damage", [
    lambda r: r.update(id="broken"),
    lambda r: r.pop("updated"),
    lambda r: r.update(type="number"),  # the value is text
    lambda r: r.update(place={"kind": "workflow"}),
])
def test_finding_2_a_damaged_record_is_refused_and_never_dropped(_stash_dir, damage):
    bad = _good("bad")
    damage(bad)
    before = _write_store(_stash_dir, [_good(), bad])
    with pytest.raises(saved.SavedValuesError) as exc:
        saved.SavedValues().save(here(), "other", 1)
    assert exc.value.code == "store_unreadable" and "damaged" in str(exc.value)
    assert (_stash_dir / "saved.json").read_bytes() == before


def test_finding_2_recall_never_trusts_a_wrong_type_tag(_stash_dir):
    _write_store(_stash_dir, [_good("runs", "12", "number")])
    done, errors, _ = execute("recall_node", name="runs", expect="number")
    assert not done and errors[0].code == "store_unreadable"


def test_finding_2_two_records_for_one_name_and_place_are_damage(_stash_dir):
    twin = _good()
    twin["id"] = "saved_twin"
    _write_store(_stash_dir, [_good(), twin])
    with pytest.raises(saved.SavedValuesError):
        saved.SavedValues().list_values()


def test_finding_3_renaming_a_subworkflow_leaves_values_its_namesake_still_uses():
    from backend.save_manager import SaveManager

    Flow("Watch").node("start", "start_node").save()
    child = Flow("Watch", callable_=True).node("start", "start_node")
    child_id = child.save()
    saved.SavedValues().save(here("Watch"), "version", "v2")
    assert SaveManager(child.map).rename_workflow(child_id, "Watch child") is None
    assert saved.SavedValues().get(here("Watch"), "version")["value"] == "v2"
    assert saved.SavedValues().get(here("Watch child"), "version") is None


def test_finding_3_renaming_the_open_workflow_checks_namesakes_too():
    from backend.save_manager import SaveManager

    Flow("Watch", callable_=True).node("start", "start_node").save()
    regular = Flow("Watch").node("start", "start_node")
    regular.save()
    saved.SavedValues().save(here("Watch"), "version", "v2")
    assert SaveManager(regular.map).rename_current_workflow("Watch 2")
    assert saved.SavedValues().get(here("Watch"), "version")["value"] == "v2"


def test_finding_4_markup_in_names_is_shown_as_text_in_change_and_forget():
    from textual.widgets import Label

    saved.SavedValues().save(here("Odd [/] flow"), "a[/]b [bold]x", "v")

    async def change(app, pilot, seen):
        await pilot.press("e")
        await pilot.pause()
        seen["change"] = str(app.screen.query(Label).first().render())
        app.screen.action_cancel()

    async def forget(app, pilot, seen):
        await pilot.press("x")
        await pilot.pause()
        seen["forget"] = str(app.screen.query(Label).first().render())
        app.screen.dismiss(False)

    seen = {}
    _stash_app(seen, [change, forget])
    assert seen["change"] == "Change 'a[/]b [bold]x' [string]"
    assert seen["forget"].startswith("Forget 'a[/]b [bold]x' (Odd [/] flow)?")


def test_finding_5_confirming_an_unchanged_value_keeps_it_exactly():
    saved.SavedValues().save(here(), "spaced", "  value with spaces  ")

    async def change(app, pilot, seen):
        await pilot.press("e")
        await pilot.pause()
        app.screen.action_submit()

    _stash_app({}, [change])
    assert saved.SavedValues().get(here(), "spaced")["value"] == "  value with spaces  "


@pytest.mark.parametrize("text", ["42", '"text"', "true"])
def test_finding_6_var_must_be_a_list_or_record(text):
    with pytest.raises(saved.SavedValuesError):
        saved.parse_typed(text, "var")


def test_finding_6_cli_and_recall_check_var_the_same_way():
    code, text = cli("set", "record", "42", "--type", "var", "--workflow", "Watch")
    assert code == 1 and saved.SavedValues().get(here("Watch"), "record") is None
    _, errors, _ = execute("recall_node", name="record", expect="var", starting_value="42")
    assert errors[0].code == "wrong_type"
    done, errors, _ = execute("recall_node", name="record", expect="var", starting_value='{"a": 1}')
    assert not errors and done[0]["data"]["default"] == {"a": 1}


def test_finding_6_numbers_must_be_finite():
    with pytest.raises(saved.SavedValuesError):
        saved.parse_typed("nan", "number")


def test_finding_7_invalid_utf8_is_unreadable_and_left_alone(_stash_dir):
    _stash_dir.mkdir(parents=True)
    (_stash_dir / "saved.json").write_bytes(b'{"format": "\xff"}')
    with pytest.raises(saved.SavedValuesError) as exc:
        saved.SavedValues().save(here(), "a", 1)
    assert exc.value.code == "store_unreadable"
    code, text = cli("list")
    assert code == 1 and "Refused" in text
    assert (_stash_dir / "saved.json").read_bytes() == b'{"format": "\xff"}'

    async def look(app, pilot, seen):
        seen["rows"] = list(app.screen.saved_shown)
        seen["listed"] = str(app.screen.query_one("#stash-saved").children[0].query_one(
            "Static").render())

    seen = {}
    _stash_app(seen, [look])  # the Stash still opens
    assert seen["rows"] == [] and "Cannot read" in seen["listed"]


def test_finding_8_a_workflow_named_all_workflows_is_its_own_place():
    store = saved.SavedValues()
    store.save(saved.all_place(), "key", "global")
    store.save(here("All workflows"), "key", "private")
    code, text = cli("list", "--workflow", "All workflows")
    assert code == 0 and "private" in text and "global" not in text
    assert "All workflows (workflow)" in text
    code, text = cli("list", "--all")
    assert "global" in text and "private" not in text

    async def look(app, pilot, seen):
        seen["rows"] = [saved.place_label(r["place"]) if r else None for r in app.screen.saved_shown]

    seen = {}
    _stash_app(seen, [look])
    assert seen["rows"] == [None, "All workflows", None, "All workflows (workflow)"]


# -- re-check of a685821 (Codex, #110): nothing written may be unreadable later -------------

def test_recheck_an_overflowing_add_is_refused_and_the_store_stays_readable(_stash_dir):
    store = saved.SavedValues()
    store.save(here(), "other", "kept")
    store.add(here(), "count", 1e308)
    before = (_stash_dir / "saved.json").read_bytes()
    with pytest.raises(saved.SavedValuesError) as exc:
        store.add(here(), "count", 1e308)
    assert exc.value.code == "not_a_number"
    assert (_stash_dir / "saved.json").read_bytes() == before
    assert {r["name"] for r in store.list_values()} == {"other", "count"}


@pytest.mark.parametrize("value", [float("inf"), float("nan"), [1, float("inf")], {"a": {"b": float("nan")}}])
def test_recheck_non_finite_numbers_are_never_written(_stash_dir, value):
    with pytest.raises(saved.SavedValuesError):
        saved.SavedValues().save(here(), "bad", value)
    assert not (_stash_dir / "saved.json").exists()
    done, errors, _ = execute("remember_node", {"input": value}, name="bad")
    assert errors and not (_stash_dir / "saved.json").exists()


def test_recheck_reading_applies_the_same_rule_to_nested_numbers(_stash_dir):
    _stash_dir.mkdir(parents=True)
    record = _good("deep", [1], "var")
    text = json.dumps({"format": saved.FORMAT, "values": [record]}).replace("[1]", "[Infinity]")
    (_stash_dir / "saved.json").write_text(text)
    with pytest.raises(saved.SavedValuesError) as exc:
        saved.SavedValues().list_values()
    assert exc.value.code == "store_unreadable"


@pytest.mark.parametrize("amount", [10 ** 400 + 1, 10 ** 400])
def test_recheck_p3_add_refuses_integers_too_large_for_a_number(_stash_dir, amount):
    store = saved.SavedValues()
    store.add(here(), "count", 1)
    before = (_stash_dir / "saved.json").read_bytes()
    with pytest.raises(saved.SavedValuesError) as exc:
        store.add(here(), "count", amount)
    assert exc.value.code == "not_a_number"
    assert (_stash_dir / "saved.json").read_bytes() == before
    with pytest.raises(saved.SavedValuesError):
        store.save(here(), "big", amount)
    _, errors, _ = execute("remember_node", name="count", how="Add",
                           input_source="Configured", value=str(amount))
    assert errors[0].code == "not_a_number"
    assert store.get(here(), "count")["value"] == 1


# -- Forward incoming payload unchanged (owner, 2026-10-22: as Notify me and Pick one) -------

@pytest.mark.parametrize("node_type, config, own", [
    ("remember_node", {"name": "runs", "how": "Add", "input_source": "Configured", "value": "1"}, 1),
    ("recall_node", {"name": "runs", "expect": "number", "starting_value": "5"}, 5),
])
def test_forwarding_sends_the_incoming_payload_and_the_vault_still_gets_the_value(node_type, config, own):
    incoming = {"report": ["keep", "this"]}
    done, errors, memory = execute(node_type, {"input": incoming}, dead_drop_passthrough=True,
                                   transient_output=False, vault_write=True, vault_write_key="own", **config)
    assert not errors and done[0]["data"] == {"default": incoming}
    assert memory.read_persistent("own") == own
    done, _, _ = execute(node_type, {"input": incoming}, **{**config, "name": "fresh"})
    assert done[0]["data"] == {"default": own}  # unchecked (the default): its own value


@pytest.mark.parametrize("node_type", ["remember_node", "recall_node"])
def test_forwarding_checkbox_toggles_saves_and_reopens(node_type):
    from textual.app import App
    from textual.widgets import Checkbox

    from backend.workflow_map import WorkflowMap
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("Forward")
    node_id = workflow_map.add_node(node_type)
    seen = {}

    class Host(App):
        def on_mount(self):
            self.push_screen(NodeConfigScreen(FACTORY, workflow_map, node_id,
                                              workflow_map.get_node_data(node_id)))

    async def check():
        async with Host().run_test(size=(100, 40)) as pilot:
            await pilot.press("3")
            await pilot.pause()
            screen = pilot.app.screen
            seen["publish"] = len(screen.query("#publish-downstream"))
            forward = screen.query_one("#dead-drop-passthrough", Checkbox)
            seen["label"], seen["start"] = str(forward.label), forward.value
            forward.focus()
            await pilot.press("space")
            await pilot.pause()
            seen["name_disabled"] = screen.query_one("#transient-output-name-default").disabled
            saved_config = screen._save_result()["config"]
            seen["saved"] = (saved_config["dead_drop_passthrough"], saved_config["transient_output"])
            workflow_map.update_node_config(node_id, saved_config)
            pilot.app.push_screen(NodeConfigScreen(FACTORY, workflow_map, node_id,
                                                   workflow_map.get_node_data(node_id)))
            await pilot.pause()
            await pilot.press("3")
            await pilot.pause()
            reopened = pilot.app.screen
            box = reopened.query_one("#dead-drop-passthrough", Checkbox)
            seen["reopened"] = box.value
            box.focus()
            await pilot.press("space")
            await pilot.pause()
            again = reopened._save_result()["config"]
            seen["unchecked"] = (again["dead_drop_passthrough"], again["transient_output"])

    asyncio.run(check())
    assert seen["publish"] == 0
    assert seen["label"] == "Forward incoming payload unchanged" and seen["start"] is False
    assert seen["name_disabled"] is True
    assert seen["saved"] == (True, False)
    assert seen["reopened"] is True
    assert seen["unchecked"] == (False, True)

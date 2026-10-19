"""Step 4a-2: the File window's Workflows and Subworkflows tabs (owner,
2026-10-18), copying a workflow to Subworkflows, and names unique per tab.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_subworkflow_library.py -v
"""

import asyncio

import pytest

from backend import persistence
from backend.run_service import resolve_workflow_data
from backend.save_manager import SaveManager
from backend.workflow_names import name_problem, unused_name
from tests.test_debug_nodes import _make_services


@pytest.fixture(autouse=True)
def _isolated_workflows(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    yield tmp_path / "workflows"


def _saved(name, callable_=False, ends=1):
    """Save Start → End (or Start alone when ``ends`` is 0)."""
    _, workflow_map, _, _ = _make_services()
    workflow_id = workflow_map.create_new(name)
    start = workflow_map.add_node("start_node")
    for _ in range(ends):
        end = workflow_map.add_node("end_node")
        workflow_map.connect(start, "default", end, "input")
    if callable_:
        workflow_map.set_callable(True)
    manager = SaveManager(workflow_map)
    manager.save_current_workflow()
    return manager, workflow_map, workflow_id


# -- names ------------------------------------------------------------------

def test_names_are_unique_per_tab():
    _saved("Report")
    assert name_problem("report") == "A saved workflow is already named 'report'"
    assert name_problem("Report", callable_=True) is None
    _saved("Report", callable_=True)
    assert name_problem("Report", callable_=True) == "A saved subworkflow is already named 'Report'"
    assert unused_name("Report", callable_=True) == "Report 2"


def test_a_name_cannot_end_with_the_sub_marker():
    assert "[sub]" in name_problem("Report [sub]")


def test_list_workflows_says_which_are_subworkflows():
    _saved("Plain")
    _saved("Called", callable_=True)
    kinds = {w["name"]: w["callable"] for w in persistence.list_workflows()}
    assert kinds == {"Plain": False, "Called": True}


# -- copy to Subworkflows -------------------------------------------------------

def test_copy_keeps_the_name_and_leaves_the_original_alone():
    manager, _, original = _saved("Fetch")
    before = persistence.load_workflow(original)

    copied = manager.copy_as_subworkflow(original)

    assert copied["name"] == "Fetch" and copied["renamed"] is False and copied["ends"] == 1
    assert persistence.load_workflow(original) == before
    copy = persistence.load_workflow(copied["id"])
    assert copy["callable"] is True and copy["name"] == "Fetch"
    # Its single End sends the results back (C27).
    ends = [n for n in copy["nodes"].values() if n["type"] == "end_node"]
    assert ends[0]["config"]["return_end"] is True


def test_a_repeat_copy_is_numbered():
    manager, _, original = _saved("Fetch")
    manager.copy_as_subworkflow(original)
    second = manager.copy_as_subworkflow(original)
    third = manager.copy_as_subworkflow(original)
    assert (second["name"], second["renamed"]) == ("Fetch (2)", True)
    assert third["name"] == "Fetch (3)"


def test_several_ends_are_left_for_the_owner_to_pick():
    manager, _, original = _saved("Branchy", ends=2)
    copied = manager.copy_as_subworkflow(original)
    copy = persistence.load_workflow(copied["id"])
    assert copied["ends"] == 2
    assert not any(n["config"].get("return_end") for n in copy["nodes"].values()
                   if n["type"] == "end_node")


def test_duplicate_stays_on_its_own_tab():
    manager, _, sub = _saved("Called", callable_=True)
    duplicate = persistence.load_workflow(manager.duplicate_workflow(sub))
    assert duplicate["callable"] is True and duplicate["name"] == "Called (Copy)"


def test_rename_checks_names_on_the_workflows_own_tab():
    manager, _, _ = _saved("Report")
    _, _, sub = _saved("Other", callable_=True)
    assert manager.rename_workflow(sub, "Report") is None
    assert persistence.load_workflow(sub)["name"] == "Report"


def test_cli_name_picks_the_workflow_and_sub_marker_picks_the_copy():
    manager, _, original = _saved("Fetch")
    copied = manager.copy_as_subworkflow(original)
    assert resolve_workflow_data("fetch")["id"] == original
    assert resolve_workflow_data("Fetch [sub]")["id"] == copied["id"]


# -- the File window -------------------------------------------------------------

def _library(keys, current=None):
    from textual.app import App

    from frontend.screens.workflow_library import WorkflowLibraryScreen

    results, seen = [], {}

    class LibraryApp(App):
        def on_mount(self):
            self.push_screen(WorkflowLibraryScreen(current), results.append)

    async def run():
        app = LibraryApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.05)
            screen = app.screen
            seen["tab"] = screen.query_one("#library-tabs").active
            seen["rows"] = {
                list_id: [item.query_one("Static").display_text
                          for item in screen.query_one(f"#{list_id}").children
                          if hasattr(item.query_one("Static"), "display_text")]
                for list_id in ("workflow-list", "subworkflow-list")
            }
            await pilot.press(*keys)
            await pilot.pause(0.05)
            seen["status"] = str(screen.query_one("StatusBar")._binding_text) if screen.is_attached else ""

    asyncio.run(run())
    return results, seen


def test_the_tabs_split_workflows_from_subworkflows():
    _, _, plain = _saved("Plain")
    _, _, called = _saved("Called", callable_=True)

    results, seen = _library(["2", "e"])

    assert seen["rows"] == {"workflow-list": ["Plain"], "subworkflow-list": ["Called"]}
    assert seen["tab"] == "library-tab-workflows"
    assert results == [{"action": "load", "workflow_id": called,
                        "workflow_name": "Called", "callable": True}]


def test_the_library_opens_on_the_loaded_workflows_tab():
    _, _, called = _saved("Called", callable_=True)
    _, seen = _library([], current=called)
    assert seen["tab"] == "library-tab-subworkflows"


def test_c_copies_from_the_workflows_tab_only():
    _, _, plain = _saved("Plain")
    _saved("Called", callable_=True)

    results, _ = _library(["c"])
    assert results == [{"action": "copy_to_subworkflows", "workflow_id": plain,
                        "workflow_name": "Plain"}]
    results, _ = _library(["2", "c", "escape"])
    assert results == [None]


def test_n_on_the_subworkflows_tab_makes_a_subworkflow():
    _saved("Plain")
    results, _ = _library(["2", "n"])
    assert results == [{"action": "new", "callable": True}]
    results, _ = _library(["n"])
    assert results == [{"action": "new"}]


def test_copy_flow_asks_then_notifies_and_reopens_the_library():
    asyncio.run(_test_copy_flow())


async def _test_copy_flow():
    from frontend.app import AttackOfTheNodesApp
    from frontend.screens.confirm import ConfirmScreen
    from frontend.screens.workflow_library import WorkflowLibraryScreen

    _saved("Fetch")
    master, workflow_map, memory_bank, bus = _make_services()
    workflow_map.create_new("Open one")
    workflow_map.mark_saved()
    app = AttackOfTheNodesApp(bus, workflow_map._factory, workflow_map, memory_bank, master,
                              save_manager=SaveManager(workflow_map))
    notes = []
    app.notify = lambda message, **kwargs: notes.append((message, kwargs.get("severity")))
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        for _ in range(2):
            app.action_workflow_library()
            await pilot.pause(0.05)
            await pilot.press("c")
            await pilot.pause(0.05)
            assert isinstance(app.screen, ConfirmScreen)
            assert "The original stays unchanged." in app.screen._message
            await pilot.click("#confirm-yes")
            await pilot.pause(0.05)
            assert isinstance(app.screen, WorkflowLibraryScreen)
            assert app.screen.query_one("#library-tabs").active == "library-tab-workflows"
            app.screen.dismiss(None)
            await pilot.pause(0.05)
    assert notes[-2:] == [
        ("Copied to Subworkflows", None),
        ('Subworkflow "Fetch" already exists. Saved as "Fetch (2)".', "warning"),
    ]
    names = sorted(w["name"] for w in persistence.list_workflows() if w["callable"])
    assert names == ["Fetch", "Fetch (2)"]

"""Workflow naming: rename in the library, a name prompt on New.

One rule (backend.workflow_names) for the library, New, Duplicate and
`aotn build`: trimmed, not blank, and no other saved workflow with the same
name ignoring case.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_workflow_naming.py -v
"""

import asyncio

import pytest

from backend import persistence
from backend.save_manager import SaveManager
from backend.workflow_names import name_problem, unused_name
from tests.test_debug_nodes import _make_services


@pytest.fixture(autouse=True)
def _isolated_workflows(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    yield tmp_path / "workflows"


def _saved(name):
    """Save a one-node workflow called ``name``; return (manager, map, id)."""
    _, workflow_map, _, _ = _make_services()
    workflow_id = workflow_map.create_new(name)
    workflow_map.add_node("start_node")
    manager = SaveManager(workflow_map)
    manager.save_current_workflow()
    return manager, workflow_map, workflow_id


def _name_on_disk(workflow_id):
    return persistence.load_workflow(workflow_id)["name"]


# -- the rule -----------------------------------------------------------------

def test_name_rule():
    _, _, first = _saved("Daily Report")
    assert name_problem("   ") == "Name can't be blank"
    assert name_problem(" daily REPORT ") == "A saved workflow is already named 'daily REPORT'"
    assert name_problem("Daily Report", exclude_id=first) is None
    assert name_problem("Weekly Report") is None


def test_unused_name_counts_up():
    assert unused_name() == "Untitled Workflow"
    _saved("Untitled Workflow")
    _saved("Untitled Workflow 2")
    assert unused_name() == "Untitled Workflow 3"


def test_duplicate_never_collides():
    manager, _, workflow_id = _saved("Report")
    first = manager.duplicate_workflow(workflow_id)
    second = manager.duplicate_workflow(workflow_id)
    assert _name_on_disk(first) == "Report (Copy)"
    assert _name_on_disk(second) == "Report (Copy) 2"


# -- SaveManager.rename_workflow ---------------------------------------------

def test_rename_a_saved_workflow_that_is_not_open():
    manager, workflow_map, other = _saved("Old name")
    workflow_map.create_new("Something else")
    assert manager.rename_workflow(other, "  New name ") is None
    assert _name_on_disk(other) == "New name"


def test_rename_refuses_a_taken_name_and_changes_nothing():
    _saved("Taken")
    manager, workflow_map, workflow_id = _saved("Mine")
    assert manager.rename_workflow(workflow_id, "TAKEN") == "A saved workflow is already named 'TAKEN'"
    assert _name_on_disk(workflow_id) == "Mine"
    assert workflow_map.workflow_name == "Mine"


def test_rename_the_open_workflow_keeps_it_clean():
    manager, workflow_map, workflow_id = _saved("Before")
    assert manager.rename_workflow(workflow_id, "After") is None
    assert workflow_map.workflow_name == "After"
    assert not workflow_map.is_dirty
    assert _name_on_disk(workflow_id) == "After"


def test_rename_does_not_save_unsaved_edits():
    manager, workflow_map, workflow_id = _saved("Before")
    workflow_map.add_node("end_node")
    assert manager.rename_workflow(workflow_id, "After") is None
    assert workflow_map.is_dirty
    assert len(persistence.load_workflow(workflow_id)["nodes"]) == 1
    manager.save_current_workflow()
    saved = persistence.load_workflow(workflow_id)
    assert (saved["name"], len(saved["nodes"])) == ("After", 2)


def test_rename_updates_a_cached_open_workflow():
    manager, workflow_map, first = _saved("First")
    workflow_map.create_new("Second")
    assert manager.rename_workflow(first, "Renamed") is None
    names = {w["id"]: w["name"] for w in workflow_map.get_open_workflows()}
    assert names[first] == "Renamed"


# -- the UI ------------------------------------------------------------------

def test_name_prompt_keeps_a_rejected_name_open():
    asyncio.run(_test_name_prompt_keeps_a_rejected_name_open())


async def _test_name_prompt_keeps_a_rejected_name_open():
    from textual.app import App
    from textual.widgets import Static

    from frontend.screens.workflow_library import NamePromptScreen
    from frontend.widgets.command_input import CommandInput

    results = []

    class PromptApp(App):
        def on_mount(self):
            self.push_screen(NamePromptScreen("New workflow", "", name_problem), results.append)

    app = PromptApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        await pilot.press("enter")
        await pilot.pause(0.03)
        error = app.screen.query_one("#name-error", Static)
        assert error.display and str(error.render()) == "Name can't be blank"
        assert results == []
        name_input = app.screen.query_one("#name-input", CommandInput)
        assert name_input.editing
        await pilot.press(*"  Plan A ", "enter")
        await pilot.pause(0.03)
    assert results == ["Plan A"]


def test_library_r_asks_to_rename_the_highlighted_workflow():
    asyncio.run(_test_library_r_asks_to_rename_the_highlighted_workflow())


async def _test_library_r_asks_to_rename_the_highlighted_workflow():
    from textual.app import App

    from frontend.screens.workflow_library import WorkflowLibraryScreen

    _, _, first = _saved("Alpha")
    _, _, second = _saved("Beta")
    results = []

    class LibraryApp(App):
        def on_mount(self):
            self.push_screen(WorkflowLibraryScreen(), results.append)

    app = LibraryApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        await pilot.press("s", "r")
        await pilot.pause(0.03)
    assert results == [{"action": "rename", "workflow_id": second, "workflow_name": "Beta"}]


def test_new_asks_for_a_name_and_esc_creates_nothing():
    asyncio.run(_test_new_asks_for_a_name_and_esc_creates_nothing())


async def _test_new_asks_for_a_name_and_esc_creates_nothing():
    from frontend.app import AttackOfTheNodesApp
    from frontend.screens.workflow_library import NamePromptScreen
    from frontend.widgets.command_input import CommandInput

    _saved("Untitled Workflow")
    master, workflow_map, memory_bank, bus = _make_services()
    original = workflow_map.create_new("Existing")
    workflow_map.mark_saved()
    app = AttackOfTheNodesApp(bus, workflow_map._factory, workflow_map, memory_bank, master)
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        app.action_new_workflow()
        await pilot.pause(0.03)
        assert isinstance(app.screen, NamePromptScreen)
        # The default never collides with a saved name.
        assert app.screen.query_one("#name-input", CommandInput).value == "Untitled Workflow 2"
        await pilot.press("escape", "escape")
        await pilot.pause(0.03)
        assert not isinstance(app.screen, NamePromptScreen)
        assert workflow_map.workflow_id == original

        app.action_new_workflow()
        await pilot.pause(0.03)
        app.screen.query_one("#name-input", CommandInput).value = "Fresh"
        await pilot.press("enter")
        await pilot.pause(0.03)
        assert workflow_map.workflow_id != original
        assert workflow_map.workflow_name == "Fresh"


def test_rename_from_the_library_returns_to_it():
    asyncio.run(_test_rename_from_the_library_returns_to_it())


async def _test_rename_from_the_library_returns_to_it():
    from frontend.app import AttackOfTheNodesApp
    from frontend.screens.workflow_library import WorkflowLibraryScreen
    from frontend.widgets.command_input import CommandInput

    master, workflow_map, memory_bank, bus = _make_services()
    workflow_id = workflow_map.create_new("Before")
    workflow_map.add_node("start_node")
    manager = SaveManager(workflow_map)
    manager.save_current_workflow()
    app = AttackOfTheNodesApp(bus, workflow_map._factory, workflow_map, memory_bank, master, manager)
    async with app.run_test() as pilot:
        await pilot.pause(0.03)
        app._handle_workflow_library_action(
            {"action": "rename", "workflow_id": workflow_id, "workflow_name": "Before"})
        await pilot.pause(0.03)
        app.screen.query_one("#name-input", CommandInput).value = "After"
        await pilot.press("enter")
        await pilot.pause(0.05)
        assert isinstance(app.screen, WorkflowLibraryScreen)
    assert _name_on_disk(workflow_id) == "After"
    assert workflow_map.workflow_name == "After"

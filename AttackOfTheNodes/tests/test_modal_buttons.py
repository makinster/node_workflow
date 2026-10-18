"""Every modal offers its main action and a way out as buttons (mouse use).

Owner, 2026-10-17: "a save/okay/enter/etc and a close button for mouse
support in all UI". Each case clicks the primary button and checks it does
what Enter does; the close button dismisses with nothing.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_modal_buttons.py -v
"""

import asyncio

import pytest
from textual.app import App
from textual.widgets import Button


def _run(screen_factory, button_id):
    """Push the screen, click ``button_id``; return what it dismissed with."""
    results = []

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(screen_factory(), results.append)

    async def go():
        app = Host()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            ids = [b.id for b in app.screen.query(Button)]
            assert button_id in ids, ids
            assert await pilot.click(f"#{button_id}"), f"#{button_id} not clickable"
            await pilot.pause(0.05)
    asyncio.run(go())
    return results


def _branch_selector():
    from frontend.screens.branch_selector import BranchSelectorScreen
    return BranchSelectorScreen("b1", "Branch", ["path_a", "path_b"], "path_b")


def _merge_beacon():
    from frontend.screens.merge_beacon_selector import MergeBeaconSelectorScreen
    return MergeBeaconSelectorScreen("beacon", [{"merge_node_id": "m1", "label": "Merge 1"}], "m1")


def _branch_keep():
    from frontend.screens.branch_keep_selector_screen import BranchKeepSelectorScreen
    return BranchKeepSelectorScreen("b1", "Branch", ["path_a", "path_b"])


def _group_picker():
    from frontend.screens.group_picker import GroupPickerScreen
    return GroupPickerScreen("Logging", [{"type": "logger_node", "display_name": "Logger",
                                          "description": "Logs"}])


def _name_prompt():
    from frontend.screens.workflow_library import NamePromptScreen
    return NamePromptScreen("Name", "  Plan A ", lambda name: None)


@pytest.mark.parametrize("factory, confirm, close, chosen", [
    (_branch_selector, "choose-branch-select", "cancel-branch-select",
     {"branch_node_id": "b1", "branch_port": "path_b"}),
    (_merge_beacon, "choose-merge-beacon", "cancel-merge-beacon",
     {"beacon_node_id": "beacon", "merge_node_id": "m1"}),
    (_branch_keep, "choose-branch-keep", "cancel-branch-keep", {"kept_port": "path_a"}),
    (_group_picker, "add-group-member", "back-group-picker", "logger_node"),
    (_name_prompt, "confirm-name", "cancel-name", "Plan A"),
], ids=["branch", "merge-beacon", "branch-keep", "group-picker", "name-prompt"])
def test_confirm_and_close_buttons(factory, confirm, close, chosen):
    assert _run(factory, confirm) == [chosen]
    assert _run(factory, close) == [None]


def test_name_prompt_confirm_button_respects_the_check():
    from frontend.screens.workflow_library import NamePromptScreen

    results = _run(lambda: NamePromptScreen("Name", "", lambda n: "Name can't be blank"
                                            if not n.strip() else None), "confirm-name")
    assert results == []  # refused: the prompt stays open


def test_workflow_library_load_button(monkeypatch):
    import frontend.screens.workflow_library as library
    monkeypatch.setattr(library, "list_workflows",
                        lambda: [{"id": "wf-1", "name": "Alpha"}, {"id": "wf-2", "name": "Beta"}])
    assert _run(lambda: library.WorkflowLibraryScreen(), "load-workflow-library") == [
        {"action": "load", "workflow_id": "wf-1", "workflow_name": "Alpha"}]
    assert _run(lambda: library.WorkflowLibraryScreen(), "cancel-workflow-library") == [None]


def test_help_closes_with_close():
    from frontend.screens.help import HelpScreen
    assert _run(lambda: HelpScreen("editor"), "close-help") == [None]


def test_node_selector_add_button_adds_the_highlighted_node():
    from backend.node_factory import NodeFactory
    from frontend.screens.node_selector import NodeSelectorScreen

    results = []

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(NodeSelectorScreen(NodeFactory()), results.append)

    async def go():
        app = Host()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.1)
            screen = app.screen
            # Highlight a plain node (not a group header), then click Add.
            target = next(i for i, e in enumerate(screen._entries) if e["kind"] == "node")
            screen.query_one("#node-type-list").index = target
            expected = screen._entries[target]["node"]["type"]
            assert await pilot.click("#add-node-select")
            await pilot.pause(0.1)
            assert results == [expected]
    asyncio.run(go())


# -- review of #73 ------------------------------------------------------------------

def _press_on(screen_factory, button_id, *keys):
    """Focus ``button_id`` and press ``keys``; return what the screen dismissed with."""
    results = []

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(screen_factory(), results.append)

    async def go():
        app = Host()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.05)
            app.set_focus(app.screen.query_one(f"#{button_id}", Button))
            await pilot.pause(0.05)
            await pilot.press(*keys)
            await pilot.pause(0.05)
    asyncio.run(go())
    return results


@pytest.mark.parametrize("factory, cancel_id", [
    (_group_picker, "back-group-picker"),
    (_branch_selector, "cancel-branch-select"),
    (_merge_beacon, "cancel-merge-beacon"),
    (_branch_keep, "cancel-branch-keep"),
], ids=["group-picker", "branch", "merge-beacon", "branch-keep"])
def test_e_on_a_focused_close_button_closes(factory, cancel_id):
    assert _press_on(factory, cancel_id, "e") == [None]


def test_node_selector_add_after_leaving_the_quick_list_adds_the_main_list_node():
    from backend.node_factory import NodeFactory
    from frontend.screens.node_selector import NodeSelectorScreen

    results = []

    class Host(App):
        CSS_PATH = "../frontend/styles.tcss"

        def on_mount(self):
            self.push_screen(NodeSelectorScreen(NodeFactory()), results.append)

    async def go():
        app = Host()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.1)
            screen = app.screen
            node_list = screen.query_one("#node-type-list")
            group = next((i for i, e in enumerate(screen._entries) if e["kind"] == "group"), None)
            if group is None:  # find a tab with a group
                for number in "2345":
                    await pilot.press(number)
                    await pilot.pause(0.05)
                    group = next((i for i, e in enumerate(screen._entries) if e["kind"] == "group"), None)
                    if group is not None:
                        break
            assert group is not None, "no tab has a group"
            node_list.index = group
            app.set_focus(node_list)
            await pilot.press("d")  # drill into the group's quick list
            await pilot.pause(0.05)
            assert screen._drilled_in
            app.set_focus(node_list)  # back to the main list (Tab in the app)
            await pilot.pause(0.05)
            target = next(i for i, e in enumerate(screen._entries) if e["kind"] == "node")
            node_list.index = target
            expected = screen._entries[target]["node"]["type"]
            assert await pilot.click("#add-node-select")
            await pilot.pause(0.1)
            assert results == [expected]
    asyncio.run(go())

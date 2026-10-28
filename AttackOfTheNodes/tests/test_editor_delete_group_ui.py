"""Mounted deletion flows use production CSS and actual keyboard input."""

import asyncio
from pathlib import Path

import pytest
from tests.ui_sizes import LAYOUT_WIDTHS
from textual.app import App
from textual.widgets import Button, Label, ListView

from frontend.screens.editor import EditorScreen
from frontend.screens.node_config import NodeConfigScreen
from frontend.screens.branch_keep_selector_screen import BranchKeepSelectorScreen

from .test_editor_delete_groups import fan, reduced

CSS = str(Path(__file__).resolve().parents[1] / "frontend/styles.tcss")


class Host(App, inherit_bindings=False):
    CSS_PATH = CSS

    def __init__(self, g, screen=None):
        super().__init__()
        self.g = g
        self.initial = screen

    def on_mount(self):
        self.editor = EditorScreen(self.g.factory, self.g.map)
        self.push_screen(self.initial or self.editor)


@pytest.mark.parametrize("callable_", [False, True])
def test_editor_header_marks_only_callable_workflows(callable_):
    async def check():
        g = fan()
        g.map.set_callable(callable_)
        app = Host(g)
        async with app.run_test() as pilot:
            await pilot.pause()
            text = str(app.editor.query_one("#workflow-title", Label).render())
            assert (" [sub]" in text) == callable_

    asyncio.run(check())


@pytest.mark.parametrize('width', [100])
def test_exact_count_picker_requires_selection_and_never_auto_applies(width):
    async def check():
        g = fan()
        result = []
        picker = BranchKeepSelectorScreen(
            g.ids["fan"],
            "Dispatch",
            [f"path_{i}" for i in range(64)],
            required=2,
            operation_id="op",
        )
        app = Host(g)
        async with app.run_test(size=(width, 34)) as pilot:
            app.push_screen(picker, result.append)
            await pilot.pause()
            assert picker.query_one("#choose-branch-keep", Button).disabled
            await pilot.press("e", "s", "space")
            await pilot.pause()
            assert not picker.query_one("#choose-branch-keep", Button).disabled
            assert app.screen is picker
            await pilot.press("enter")
            await pilot.pause()
            assert result == [
                {"ports": ["path_0", "path_1"], "required": 2, "operation_id": "op"}
            ]

    asyncio.run(check())


def test_picker_enter_on_cancel_and_optional_zero_picks():
    async def check():
        g = fan()
        app = Host(g)
        results = []
        async with app.run_test() as pilot:
            picker = BranchKeepSelectorScreen(
                "fan", "Dispatch", ["one", "two"], maximum=1
            )
            app.push_screen(picker, results.append)
            await pilot.pause()
            picker.query_one("#cancel-branch-keep", Button).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert results == [None]
            picker = BranchKeepSelectorScreen(
                "fan", "Dispatch", ["one", "two"], maximum=1
            )
            app.push_screen(picker, results.append)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert results[-1]["ports"] == []

    asyncio.run(check())


def test_first_branch_delete_opens_picker_and_cancel_keeps_everything():
    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test() as pilot:
            await pilot.pause()
            editor = app.editor
            editor.selected_node_id = g.ids["fan"]
            editor.selected_row = {"kind": "node", "node_id": g.ids["fan"]}
            before = g.snapshot()
            editor.action_delete_selected()
            await pilot.pause()
            assert isinstance(app.screen, BranchKeepSelectorScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert g.snapshot() == before

    asyncio.run(check())


@pytest.mark.parametrize("save_key", ["ctrl+s", "ctrl+enter"])
def test_count_save_and_stay_cancel_keeps_draft_dirty(save_key):
    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            app.editor._open_node_config(g.ids["fan"])
            await pilot.pause()
            screen = app.screen
            screen.query_one("#branch-count").value = "2"
            await pilot.pause(0.15)
            before = g.snapshot()
            await pilot.press(save_key)
            await pilot.pause()
            assert isinstance(app.screen, BranchKeepSelectorScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is screen and screen._is_dirty()
            assert g.snapshot() == before

    asyncio.run(check())


def test_count_save_commit_reopens_form_with_remapped_values_and_saved_row():
    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            app.editor.active_branch_ports[g.ids["fan"]] = "path_d"
            app.editor._open_node_config(g.ids["fan"])
            await pilot.pause()
            app.screen.query_one("#branch-count").value = "2"
            await pilot.pause(0.15)
            await pilot.press("ctrl+s")
            await pilot.pause()
            await pilot.press("e", "s", "s", "s", "e")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause(0.2)
            assert isinstance(app.screen, NodeConfigScreen)
            assert not app.screen._is_dirty()
            assert app.screen.query_one("#branch-count").value == "2"
            assert g.map.find_next_node_id(g.ids["fan"], "path_b") == g.ids["d"]
            assert app.editor.active_branch_ports[g.ids["fan"]] == "path_b"
            assert any(
                row.get("saved_paths") for row in app.editor._build_visible_rows()
            )

    asyncio.run(check())


def test_reloaded_group_shows_only_its_selected_continuation():
    g = fan()
    g.delete("fan", "path_d")
    g.reload()
    editor = EditorScreen(g.factory, g.map)
    rows = editor._build_visible_rows()
    node_ids = {row.get("node_id") for row in rows}
    assert g.ids["d"] in node_ids and g.ids["a"] not in node_ids
    assert not any(
        row["kind"] == "branch_select" and row["branch_node_id"] == g.ids["fan"]
        for row in rows
    )


def test_kept_path_keeps_pending_name_and_payload_source_edits():
    from textual.widgets import Select

    async def check():
        g = fan()
        g.add(
            "writer",
            "logger_node",
            membank_outputs=[{"id": "new", "description": "New"}],
        )
        g.map.get_node_data(g.ids["fan"])["config"]["membank_inputs"] = ["new"]
        app = Host(g)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            app.editor._open_node_config(g.ids["fan"])
            await pilot.pause()
            screen = app.screen
            source = screen.query_one("#branch-payload-source-path_d", Select)
            source.value = "vault:new"  # A real selected Vault input survives the count-row rebuild.
            screen.query_one("#branch-label-path_d").value = "Edited"
            screen.query_one("#branch-count").value = "2"
            await pilot.pause(0.15)
            await pilot.press("ctrl+s")
            await pilot.pause()
            await pilot.press("e", "s", "s", "s", "e", "enter")
            await pilot.pause(0.2)
            config = g.map.get_node_data(g.ids["fan"])["config"]
            assert config["path_b_label"] == "Edited"
            assert config["branch_payload_sources"]["path_b"] == "vault:new"

    asyncio.run(check())


@pytest.mark.parametrize("width", LAYOUT_WIDTHS)
def test_picker_scrolls_to_last_path_and_buttons_stay_visible(width):
    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test(size=(width, 34)) as pilot:
            picker = BranchKeepSelectorScreen(
                "fan", "Dispatch", [str(i) for i in range(64)], required=1
            )
            app.push_screen(picker)
            await pilot.pause()
            await pilot.press(*(["s"] * 63))
            await pilot.press("e")
            await pilot.pause()
            view = picker.query_one(ListView)
            assert view.index == 63 and picker.selected == {"63"}
            assert view.region.y <= view.children[63].region.y < view.region.bottom
            button = picker.query_one("#choose-branch-keep", Button)
            assert button.region.bottom <= 34 and button.region.y >= view.region.bottom
            await pilot.press("s")
            assert app.focused is button
            await pilot.press("s", "enter")
            await pilot.pause()
            assert app.screen is app.editor

    asyncio.run(check())


def test_saved_recovery_row_cannot_be_used_as_a_graph_output_for_insert():
    from .test_editor_delete_groups import reduced

    async def check():
        g = fan()
        reduced(g)
        app = Host(g)
        async with app.run_test() as pilot:
            await pilot.pause()
            row = next(
                r for r in app.editor._build_visible_rows() if r.get("saved_paths")
            )
            app.editor._select_row(row)
            before = g.snapshot()
            app.editor.action_insert_node()
            await pilot.pause()
            assert app.screen is app.editor
            assert g.snapshot() == before

    asyncio.run(check())


def test_save_close_can_cancel_without_losing_the_form_draft():
    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            app.editor._open_node_config(g.ids["fan"])
            await pilot.pause()
            form = app.screen
            form.query_one("#branch-count").value = "2"
            await pilot.pause(0.15)
            before = g.snapshot()
            await pilot.click("#save-node-config")
            await pilot.pause()
            assert isinstance(app.screen, BranchKeepSelectorScreen)
            await pilot.press("ctrl+q")
            await pilot.pause()
            assert app.screen is form and form._is_dirty() and g.snapshot() == before

    asyncio.run(check())


@pytest.mark.parametrize("choice", ["unsaved-save", "unsaved-discard", "unsaved-stay"])
def test_count_draft_unsaved_exit_choices(choice):
    from frontend.screens.unsaved_changes import UnsavedChangesScreen

    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            app.editor._open_node_config(g.ids["fan"])
            await pilot.pause()
            form = app.screen
            form.query_one("#branch-count").value = "2"
            await pilot.pause(0.15)
            before = g.snapshot()
            await pilot.click("#cancel-node-config")
            await pilot.pause()
            assert isinstance(app.screen, UnsavedChangesScreen)
            await pilot.click("#" + choice)
            await pilot.pause()
            if choice == "unsaved-save":
                assert isinstance(app.screen, BranchKeepSelectorScreen)
                await pilot.press("escape")
                await pilot.pause()
                assert app.screen is form and form._is_dirty()
            elif choice == "unsaved-stay":
                assert app.screen is form and form._is_dirty()
            else:
                assert app.screen is app.editor
            assert g.snapshot() == before

    asyncio.run(check())


@pytest.mark.parametrize("choice", ["recover", "empty", "cancel"])
def test_count_increase_prompt_and_optional_picker(choice):
    from .test_editor_delete_groups import reduced
    from frontend.screens.branch_keep_selector_screen import BranchRecoveryPrompt

    async def check():
        g = fan()
        reduced(g)
        entries = g.adapter.saved_paths(g.ids["fan"])
        app = Host(g)
        async with app.run_test(size=(100, 50)) as pilot:
            await pilot.pause()
            app.editor._open_node_config(g.ids["fan"])
            await pilot.pause()
            form = app.screen
            form.query_one("#branch-count").value = "3"
            await pilot.pause(0.15)
            before = g.snapshot()
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert isinstance(app.screen, BranchRecoveryPrompt)
            if choice == "cancel":
                await pilot.press("escape")
                await pilot.pause()
                assert (
                    app.screen is form and form._is_dirty() and g.snapshot() == before
                )
                return
            await pilot.click("#confirm-yes" if choice == "recover" else "#leave-empty")
            await pilot.pause()
            if choice == "recover":
                assert isinstance(app.screen, BranchKeepSelectorScreen)
                await pilot.press("s", "e", "enter")
                await pilot.pause(0.2)
                assert g.map.find_next_node_id(g.ids["fan"], "path_c") == g.ids["c"]
                assert [e["id"] for e in g.adapter.saved_paths(g.ids["fan"])] == [
                    entries[0]["id"]
                ]
            else:
                assert g.map.find_next_node_id(g.ids["fan"], "path_c") is None
                assert g.adapter.saved_paths(g.ids["fan"]) == entries
            assert (
                isinstance(app.screen, NodeConfigScreen) and not app.screen._is_dirty()
            )
            archive = g.adapter.saved_paths(g.ids["fan"])
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert (
                g.adapter.saved_paths(g.ids["fan"]) == archive
            )  # Ordinary config saves preserve recovery data.

    asyncio.run(check())


@pytest.mark.parametrize("width", LAYOUT_WIDTHS)
def test_recovery_prompt_renders_the_question_and_all_three_buttons(width):
    from frontend.screens.branch_keep_selector_screen import BranchRecoveryPrompt

    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test(size=(width, 34)) as pilot:
            prompt = BranchRecoveryPrompt(
                "Dispatch: 2 paths → 3\n2 saved paths. Recover any for the new paths?"
            )
            app.push_screen(prompt)
            await pilot.pause()
            title = prompt.query_one(".modal-title", Label)
            assert title.content_size.height >= 2
            assert all(button.region.bottom <= 34 for button in prompt.query(Button))

    asyncio.run(check())


def test_saved_paths_and_unrestored_changes_have_separate_editor_rows():
    async def check():
        g = fan()
        reduced(g)
        node = g.map.get_node_data(g.ids["fan"])
        config = node["config"]
        record = next(iter(config["branch_recovery"]["groups"].values()))
        g.map.update_node_config(g.ids["fan"], {**config, "delete_recovery": record})
        app = Host(g)
        async with app.run_test() as pilot:
            await pilot.pause()
            rows = [r for r in app.editor._build_visible_rows() if r.get("saved_paths")]
            assert len(rows) == 2
            saved = next(r for r in rows if not r.get("pending_restore"))
            pending = next(r for r in rows if r.get("pending_restore"))
            assert saved["active_label"] == "Saved paths (2)"
            assert pending["active_label"] == "Unrestored changes"
            for row in rows:
                assert (
                    app.editor._matching_visible_row(
                        row, app.editor._build_visible_rows()
                    )
                    == row
                )
            live = next(
                r
                for r in app.editor._build_visible_rows()
                if r["kind"] == "branch_select" and not r.get("saved_paths")
            )
            assert (
                app.editor._matching_visible_row(live, app.editor._build_visible_rows())
                == live
            )
            app.editor._select_row(live)
            app.editor._cycle_selected_branch_select(1)
            assert app.editor.active_branch_ports[g.ids["fan"]] == "path_b"

    asyncio.run(check())


@pytest.mark.parametrize("width", LAYOUT_WIDTHS)
@pytest.mark.parametrize("mode", ["keep", "recover"])
def test_short_picker_fits_its_rows_and_keeps_controls_together(width, mode):
    async def check():
        app = Host(fan())
        options = {"required": 1} if mode == "keep" else {"maximum": 1}
        picker = BranchKeepSelectorScreen("fan", "Dispatch", ["one", "two"], **options)
        async with app.run_test(size=(width, 34)) as pilot:
            app.push_screen(picker)
            await pilot.pause()
            view = picker.query_one(ListView)
            rows_height = sum(row.outer_size.height for row in view.children)
            assert view.region.height == rows_height
            preview = picker.query_one("#path-preview")
            assert preview.region.y == view.region.bottom
            buttons = picker.query_one(".button-row")
            assert buttons.region.y <= preview.region.bottom + 3
            assert buttons.region.bottom <= 34

    asyncio.run(check())


def test_picker_refits_wrapped_rows_after_terminal_resize():
    async def check():
        app = Host(fan())
        picker = BranchKeepSelectorScreen(
            "fan",
            "Dispatch",
            ["one", "two"],
            {
                "one": "A long path name that wraps at narrow widths " * 2,
                "two": "Short",
            },
            maximum=1,
        )
        async with app.run_test(size=(140, 34)) as pilot:
            app.push_screen(picker)
            await pilot.pause()
            await pilot.resize_terminal(60, 34)
            await pilot.pause()
            view = picker.query_one(ListView)
            assert view.region.height == sum(
                row.outer_size.height for row in view.children
            )
            assert picker.query_one("#path-preview").region.y == view.region.bottom
            assert picker.query_one(".button-row").region.bottom <= 34

    asyncio.run(check())


def test_first_delete_preview_uses_plain_wording():
    async def check():
        g = fan()
        app = Host(g)
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.pause()
            app.editor.selected_node_id = g.ids["fan"]
            app.editor.selected_row = {"kind": "node", "node_id": g.ids["fan"]}
            before = g.snapshot()
            app.editor.action_delete_selected()
            await pilot.pause()
            await pilot.press("e")
            await pilot.pause()
            assert str(app.screen.query_one("#path-preview").render()) == (
                "Deletes 6 nodes. Shared nodes stay. Z brings them back."
            )
            await pilot.press("escape")
            await pilot.pause()
            assert g.snapshot() == before

    asyncio.run(check())

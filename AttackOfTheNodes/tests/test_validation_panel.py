"""Editor Validation panel (owner, 2026-10-19; samples 2026-10-20): V opens
and closes it, Run validation lists the issues errors first, and Go to node
(E) hides the panel and highlights the node."""

import asyncio

from textual.widgets import ListView

from frontend.screens.editor import EditorScreen
from frontend.widgets.node_list import NodeList
from frontend.widgets.status_bar import StatusBar
from frontend.widgets.validation_panel import ValidationPanel

from .test_editor_delete_group_ui import Host
from .test_editor_delete_groups import Graph


def chain():
    g = Graph()
    g.add("a")
    g.add("aend", "end_node")
    g.wire("start", "a").wire("a", "aend")
    return g


def broken():
    g = chain()
    g.add("loose")  # not reachable from start: a warning
    g.add("reader", "file_reader_node")  # no file path: an error
    g.wire("a", "reader")
    return g


def run(g, steps, width=110):
    async def check():
        app = Host(g)
        async with app.run_test(size=(width, 34)) as pilot:
            await pilot.pause()
            await steps(app.editor, pilot)
    asyncio.run(check())


def hint(editor):
    return editor.query_one(StatusBar)._binding_text


def test_v_opens_and_closes_the_panel_and_esc_closes_it():
    async def steps(editor, pilot):
        panel = editor.query_one(ValidationPanel)
        assert not panel.display
        await pilot.press("v")
        assert panel.display
        assert editor.focused.id == "validation-run"
        assert hint(editor) == "w/s move | e go to node / run | r run | v close"
        await pilot.press("v")
        assert not panel.display
        assert isinstance(editor.focused, NodeList)
        await pilot.press("v", "escape")
        assert not panel.display
    run(chain(), steps)


def test_opening_the_panel_does_not_run_validation():
    async def steps(editor, pilot):
        await pilot.press("v")
        assert editor.query_one(ValidationPanel).issues is None
    run(broken(), steps)


def test_run_lists_errors_first_and_highlights_the_first_issue():
    async def steps(editor, pilot):
        await pilot.press("v", "e")
        await pilot.pause()
        panel = editor.query_one(ValidationPanel)
        levels = [issue["level"] for issue in panel.issues]
        assert levels == sorted(levels)  # "error" before "warning"
        assert "error" in levels and "warning" in levels
        assert panel.selected_issue == panel.issues[0]
        await pilot.press("s")
        assert panel.selected_issue == panel.issues[1]
        await pilot.press("w", "w")
        assert editor.focused.id == "validation-run"
        assert panel.selected_issue is None
    run(broken(), steps)


def test_r_runs_validation_only_while_the_panel_is_open():
    async def steps(editor, pilot):
        panel = editor.query_one(ValidationPanel)
        await pilot.press("r")
        assert panel.issues is None
        await pilot.press("v", "r")
        assert panel.issues
    run(broken(), steps)


def test_go_to_node_hides_the_panel_and_highlights_the_node():
    g = broken()
    async def steps(editor, pilot):
        panel = editor.query_one(ValidationPanel)
        await pilot.press("v", "r")
        loose = next(i for i, issue in enumerate(panel.issues) if issue["node_id"] == g.ids["loose"])
        panel.list_view.index = loose
        await pilot.press("e")
        await pilot.pause()
        assert not panel.display
        assert editor.selected_node_id == g.ids["loose"]
        assert isinstance(editor.focused, NodeList)
        assert hint(editor).startswith("! loose: ")
        assert hint(editor).endswith("| v validation")
        await pilot.press("v")
        assert panel.display and panel.issues  # the last run is kept
        await pilot.press("v", "w")
        assert not hint(editor).startswith("! loose")
    run(g, steps)


def test_a_clean_workflow_shows_no_issues():
    async def steps(editor, pilot):
        await pilot.press("v", "r")
        await pilot.pause()
        panel = editor.query_one(ValidationPanel)
        assert panel.issues == []
        assert "no issues" in str(panel.query_one("#validation-summary").render())
        assert not panel.query_one(ListView).display
    run(chain(), steps)


def test_rows_fit_on_one_line_at_80_columns():
    async def steps(editor, pilot):
        await pilot.press("v", "r")
        await pilot.pause()
        for item in editor.query_one(ValidationPanel).list_view.children:
            assert item.size.height == 1
    run(broken(), steps, width=80)

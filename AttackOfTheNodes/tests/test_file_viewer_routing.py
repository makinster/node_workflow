"""File Viewer reference routing, Vault controls, and editor wiring."""

from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Checkbox

from backend.events import FILE_VIEW_REQUESTED
from backend.file_refs import file_reference
from frontend.screens.editor import EditorScreen
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.command_input import CommandInput
from tests.generated.test_file_view_node import _make_node, _make_context
from tests.test_debug_nodes import _make_services


@pytest.mark.parametrize("forward", [False, True])
@pytest.mark.parametrize("vault", [False, True])
async def test_viewer_vault_reference_is_independent_of_forwarding(tmp_path, forward, vault):
    target = tmp_path / "viewed.md"
    target.write_text("# file", encoding="utf-8")
    incoming = "a different incoming payload"
    node = _make_node({"file_source": "Configured", "file": str(target),
                       "dead_drop_passthrough": forward, "transient_output": not forward, "vault_write": vault,
                       "vault_write_key": "shared_file"})
    context, done, errors, events = _make_context(inputs={"file": incoming})
    await node.execute(context)
    assert not errors
    ref = file_reference(str(target.resolve()))
    assert done[0]["data"]["default"] == (incoming if forward else ref)
    assert context.memory_bank.read_persistent_by_type("file") == ({"shared_file": ref} if vault else {})


async def test_editor_connects_viewer_reference_to_writer_path_and_runs(tmp_path):
    master, wm, mb, _ = _make_services()
    wm.create_new("viewer_writer_wiring")
    target = tmp_path / "same-file.md"
    target.write_text("old content", encoding="utf-8")
    start = wm.add_node("start_node")
    viewer = wm.add_node("file_view_node")
    writer = wm.add_node("file_output_node")
    wm.update_node_config(viewer, {"file_source": "Configured", "file": str(target)})
    wm.update_node_config(writer, {"content_source": "Configured", "content": "new content"})
    wm.connect(start, "default", viewer, "file")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(EditorScreen)
        editor._connect_new_node(viewer, "default", writer)
        assert wm.find_input_source(writer, "file_path")["source_node_id"] == viewer
        assert wm.find_input_source(writer, "content") is None
        assert wm.get_node_data(writer)["config"]["file_path_source"] == "Upstream payload"
        assert await master.start_workflow()
        await master.wait_for_completion()
        assert master.state.value == "FINISHED"
        assert target.read_text(encoding="utf-8") == "new content"


async def test_editor_save_reassigns_unused_content_connection_to_path(tmp_path):
    master, wm, mb, _ = _make_services()
    wm.create_new("existing_viewer_writer_wiring")
    target = tmp_path / "same-file.md"
    target.write_text("original", encoding="utf-8")
    start = wm.add_node("start_node")
    viewer = wm.add_node("file_view_node")
    writer = wm.add_node("file_output_node")
    wm.update_node_config(viewer, {"file_source": "Configured", "file": str(target)})
    wm.connect(start, "default", viewer, "file")
    wm.connect(viewer, "default", writer, "content")

    class EditorApp(App):
        def compose(self) -> ComposeResult:
            yield EditorScreen(wm._factory, wm)

    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(EditorScreen)
        editor.selected_node_id = writer
        editor._save_node_config_from_modal({"alias": "Writer", "config": {
            "content_source": "Configured", "content": "fixed wiring",
            "file_path_source": "Upstream payload",
        }})
        assert wm.find_input_source(writer, "content") is None
        assert wm.find_input_source(writer, "file_path")["source_node_id"] == viewer
        assert wm.get_node_data(viewer)["connections"]["outputs"][0]["target_port"] == "file_path"
        assert await master.start_workflow()
        await master.wait_for_completion()
        assert master.state.value == "FINISHED"
        assert target.read_text(encoding="utf-8") == "fixed wiring"


async def test_editor_preserves_active_content_and_configured_path_connections():
    _, wm, _, _ = _make_services()
    wm.create_new("preserve_explicit_connections")
    viewer = wm.add_node("file_view_node")
    writer = wm.add_node("file_output_node")
    wm.connect(viewer, "default", writer, "content")
    editor = EditorScreen(wm._factory, wm)
    for config in (
        {"content_source": "Upstream payload", "file_path_source": "Upstream payload"},
        {"content_source": "Configured", "file_path_source": "Configured"},
    ):
        wm.update_node_config(writer, config)
        editor._reassign_inactive_input_connections(writer)
        assert wm.find_input_source(writer, "content")["source_node_id"] == viewer
        assert wm.find_input_source(writer, "file_path") is None


def test_insert_between_preserves_an_existing_file_path_connection():
    _, wm, _, _ = _make_services()
    wm.create_new("preserve_occupied_writer_path")
    source = wm.add_node("logger_node")
    path_source = wm.add_node("file_view_node")
    inserted = wm.add_node("file_view_node")
    writer = wm.add_node("file_output_node")
    wm.connect(source, "default", writer, "content")
    wm.connect(path_source, "default", writer, "file_path")
    editor = EditorScreen(wm._factory, wm)
    editor._connect_new_node(source, "default", inserted)
    assert wm.find_input_source(writer, "file_path")["source_node_id"] == path_source
    assert wm.find_input_source(writer, "content")["source_node_id"] == inserted
    assert len(wm.get_node_data(writer)["connections"]["inputs"]) == 2


@pytest.mark.parametrize("forward", [False, True])
async def test_viewer_payload_ui_saves_vault_option_with_or_without_forwarding(forward):
    _, wm, mb, _ = _make_services()
    wm.create_new("viewer_vault_controls")
    viewer = wm.add_node("file_view_node")
    results = []

    class ConfigApp(App):
        CSS_PATH = str(Path(__file__).parent.parent / "frontend" / "styles.tcss")

        async def on_mount(self):
            await self.push_screen(NodeConfigScreen(wm._factory, wm, viewer,
                                  wm.get_node_data(viewer), memory_bank=mb), results.append)

    async with ConfigApp().run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        screen = pilot.app.screen
        screen.query_one("#dead-drop-passthrough", Checkbox).value = forward
        disabled = screen.query_one("#vault-output-disabled-default", Checkbox)
        assert disabled.value  # Vault output starts off.
        disabled.value = False
        await pilot.pause()
        key = screen.query_one("#vault-output-key-default", CommandInput)
        assert key.display and not key.disabled
        key.value = "shared_file"
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert results[0]["config"]["vault_write"]
        assert results[0]["config"]["vault_write_key"] == "shared_file"
        assert results[0]["config"]["dead_drop_passthrough"] is forward
        assert results[0]["config"]["transient_output"] is (not forward)
        wm.update_node_config(viewer, results[0]["config"])
        writer = wm.add_node("file_output_node")
        writer_screen = NodeConfigScreen(wm._factory, wm, writer, wm.get_node_data(writer), memory_bank=mb)
        assert writer_screen._declared_vault_writer_keys()["shared_file"]["tag"] == "file"


async def test_viewer_vault_reference_is_accessible_in_parallel_branches(tmp_path):
    master, wm, mb, bus = _make_services()
    wm.create_new("viewer_vault_parallel")
    target = tmp_path / "shared.md"
    target.write_text("# shared", encoding="utf-8")
    start = wm.add_node("start_node")
    viewer = wm.add_node("file_view_node")
    branch = wm.add_node("branch_node")
    wm.update_node_config(viewer, {"file_source": "Configured", "file": str(target),
                                  "vault_write": True, "vault_write_key": "shared_file"})
    wm.connect(start, "default", viewer, "file")
    wm.connect(viewer, "default", branch, "input")
    events = []
    bus.subscribe(FILE_VIEW_REQUESTED, events.append)
    for port in ("path_a", "path_b"):
        child = wm.add_node("file_view_node")
        wm.update_node_config(child, {"file_source": "Vault", "file_vault_key": "shared_file"})
        wm.connect(branch, port, child, "file")
    assert await master.start_workflow()
    await master.wait_for_completion()
    assert master.state.value == "FINISHED"
    assert len(events) == 3
    assert all(event["path"] == str(target.resolve()) for event in events)
    assert mb.read_persistent_by_type("file")["shared_file"] == file_reference(str(target.resolve()))

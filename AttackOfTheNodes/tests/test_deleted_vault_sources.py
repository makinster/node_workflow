"""Deleted Vault producers must not appear as usable input sources."""

from pathlib import Path
import json

import pytest
from textual.app import App
from textual.widgets import Select

from backend.file_refs import file_reference
from frontend.editor_workflow_adapter import EditorWorkflowAdapter
from frontend.screens.editor import EditorScreen
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.node_list import NodeList
from tests.test_debug_nodes import _make_services


def configure_writer(wm, node_id, key):
    config = dict(wm.get_node_data(node_id)["config"])
    config.update(vault_write=True, vault_write_key=key)
    wm.update_node_config(node_id, config)


def options(wm, mb, consumer, adapter=None):
    screen = NodeConfigScreen(wm._factory, wm, consumer, wm.get_node_data(consumer),
                              memory_bank=mb, workflow_adapter=adapter)
    return screen._vault_key_options({"file": {"vault_type": "file"},
                                      "payload": {"vault_type": "any"}})


@pytest.mark.parametrize("producer_type", ["file_output_node", "file_view_node"])
@pytest.mark.parametrize("persisted", [False, True])
def test_file_vault_choices_follow_delete_restore_reload_and_removal(producer_type, persisted):
    _, wm, mb, _ = _make_services()
    wm.create_new("deleted_vault_lifecycle")
    producer = wm.add_node(producer_type)
    consumer = wm.add_node("file_output_node")
    configure_writer(wm, producer, "the_file")
    ref = file_reference("/tmp/the-file.txt")
    if persisted:
        mb.store_persistent("the_file", ref, type_tag="file")
    adapter = EditorWorkflowAdapter(wm, wm._factory)
    assert options(wm, mb, consumer, adapter)["file"] == [("the_file [file]", "the_file")]

    assert adapter.replace_with_placeholder(producer)
    assert options(wm, mb, consumer, adapter) == {"file": [], "any": []}
    # Soft deletion keeps backend config and data intact for undo.
    assert wm.get_node_data(producer)["type"] == producer_type
    assert adapter.undo_placeholder(producer)
    assert options(wm, mb, consumer, adapter)["file"]

    adapter.replace_with_placeholder(producer)
    adapter.materialize_deleted_nodes()
    snapshot = json.loads(json.dumps(wm.get_workflow_data_for_save()))
    mb.load_state(json.loads(json.dumps(mb.get_state())))
    wm.load_data(snapshot)
    adapter = EditorWorkflowAdapter(wm, wm._factory)  # No in-memory deletion overlay.
    assert options(wm, mb, consumer, adapter) == {"file": [], "any": []}
    assert adapter.undo_placeholder(producer)
    assert options(wm, mb, consumer, adapter)["file"]

    adapter.replace_with_placeholder(producer)
    assert adapter.remove_placeholder(producer)
    assert options(wm, mb, consumer, adapter) == {"file": [], "any": []}
    if persisted:
        assert mb.read_persistent("the_file") == ref


def test_remaining_parallel_writer_keeps_shared_file_key_available():
    _, wm, mb, _ = _make_services()
    wm.create_new("shared_vault_writer")
    first = wm.add_node("file_view_node")
    second = wm.add_node("file_output_node")
    consumer = wm.add_node("window_control_node")
    for node in (first, second):
        configure_writer(wm, node, "shared")
    mb.store_persistent("shared", file_reference("/tmp/shared.txt"), type_tag="file")
    adapter = EditorWorkflowAdapter(wm, wm._factory)
    adapter.replace_with_placeholder(first)
    assert options(wm, mb, consumer, adapter)["file"] == [("shared [file]", "shared")]
    adapter.replace_with_placeholder(second)
    assert not options(wm, mb, consumer, adapter)["file"]


def test_replaced_producer_does_not_reoffer_old_file_key():
    _, wm, mb, _ = _make_services()
    wm.create_new("replaced_file_writer")
    producer = wm.add_node("file_view_node")
    consumer = wm.add_node("file_output_node")
    configure_writer(wm, producer, "old_file")
    mb.store_persistent("old_file", file_reference("/tmp/old.txt"), type_tag="file")
    adapter = EditorWorkflowAdapter(wm, wm._factory)
    adapter.replace_with_placeholder(producer)
    assert adapter.replace_placeholder(producer, "logger_node")["replaced"]
    assert options(wm, mb, consumer, adapter) == {"file": [], "any": []}


def test_external_nonfile_vault_entries_remain_selectable():
    _, wm, mb, _ = _make_services()
    wm.create_new("external_vault_entries")
    consumer = wm.add_node("file_output_node")
    mb.store_persistent("text", "hello")
    mb.store_persistent("session", {"type": "ai_session", "ref_key": "session"},
                        type_tag="ai_session")
    assert {key for _, key in options(wm, mb, consumer)["any"]} == {"text", "session"}


@pytest.mark.parametrize("remaining_writer", ["self", "downstream"])
def test_deleted_parallel_writer_does_not_bypass_other_writer_restrictions(remaining_writer):
    _, wm, mb, _ = _make_services()
    wm.create_new("deleted_parallel_writer")
    deleted = wm.add_node("file_view_node")
    consumer = wm.add_node("file_output_node")
    remaining = consumer if remaining_writer == "self" else wm.add_node("file_view_node")
    if remaining_writer == "downstream":
        wm.connect(consumer, "default", remaining, "file")
    for node in (deleted, remaining):
        configure_writer(wm, node, "shared")
    mb.store_persistent("shared", file_reference("/tmp/shared.txt"), type_tag="file")
    adapter = EditorWorkflowAdapter(wm, wm._factory)
    adapter.replace_with_placeholder(deleted)
    assert not options(wm, mb, consumer, adapter)["file"]


@pytest.mark.parametrize("consumer_type,source_field,key_field", [
    ("file_output_node", "file_path_source", "file_path_vault_key"),
    ("file_view_node", "file_source", "file_vault_key"),
    ("window_control_node", "file_source", "file_vault_key"),
])
@pytest.mark.parametrize("saved_selection", [False, True])
async def test_editor_opens_file_picker_with_shared_deletion_state(
    consumer_type, source_field, key_field, saved_selection,
):
    _, wm, mb, _ = _make_services()
    wm.create_new("editor_deleted_vault_picker")
    start = wm.add_node("start_node")
    producer = wm.add_node("file_view_node")
    consumer = wm.add_node(consumer_type)
    wm.connect(start, "default", producer, "file")
    wm.connect(producer, "default", consumer,
               "file_path" if consumer_type == "file_output_node" else "file")
    configure_writer(wm, producer, "deleted_file")
    mb.store_persistent("deleted_file", file_reference("/tmp/deleted.txt"), type_tag="file")
    if saved_selection:
        config = dict(wm.get_node_data(consumer)["config"])
        config.update({source_field: "Vault", key_field: "deleted_file"})
        wm.update_node_config(consumer, config)
    editor = EditorScreen(wm._factory, wm)

    class EditorApp(App):
        CSS_PATH = str(Path(__file__).parent.parent / "frontend" / "styles.tcss")

        def __init__(self):
            super().__init__()
            self.memory_bank = mb

        async def on_mount(self):
            await self.push_screen(editor)

    async with EditorApp().run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        editor.workflow_adapter.replace_with_placeholder(producer)
        editor.refresh_from_backend()
        await pilot.pause()
        rows = editor.query_one(NodeList)._rows
        editor._select_row(next(row for row in rows if row.get("node_id") == consumer))
        editor.action_edit_selected()
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, NodeConfigScreen)
        assert screen._vault_key_options({"file": {"vault_type": "file"}}) == {"file": []}
        source = screen.query_one(f"#field-{source_field}", Select)
        key = screen.query_one(f"#field-{key_field}", Select)
        if saved_selection:
            # Keep an already saved invalid selection visible for repair.
            assert source.value == "Vault"
            assert key.value == "deleted_file"
            assert any("not declared" in str(label) for label, value in key._options
                       if value == "deleted_file")
        else:
            assert "Vault" not in {value for _, value in source._options}
            assert "deleted_file" not in {value for _, value in key._options}

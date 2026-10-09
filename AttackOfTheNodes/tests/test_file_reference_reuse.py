"""Same-file reference reuse and clear output configuration."""

from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Checkbox, Label, Static

from backend.run_session import RunSession
from frontend.screens.node_config import NodeConfigScreen
from tests.generated.test_file_output_node import _make_node, _make_context
from tests.test_debug_nodes import _make_services


@pytest.mark.parametrize("source", ["Upstream payload", "Vault"])
@pytest.mark.parametrize("mode", ["Overwrite", "Append"])
@pytest.mark.parametrize("forward", [False, True])
@pytest.mark.parametrize("session_enabled", [False, True])
async def test_writer_reuses_existing_reference_and_vault_identity(
    tmp_path, source, mode, forward, session_enabled,
):
    target = tmp_path / "same-file.txt"
    target.write_text("old", encoding="utf-8")
    ref = {"type": "file", "path": str(target), "ref_key": "file:existing-identity"}
    node = _make_node({"file_path_source": source, "file_path_vault_key": "source_file",
                       "write_mode": mode, "vault_write": True,
                       "vault_write_key": "another_name", "dead_drop_passthrough": forward, "transient_output": not forward})
    session = RunSession("same-file") if session_enabled else None
    context, done, errors = _make_context(inputs={"file_path": ref, "content": "new"}, run_session=session)
    context.memory_bank.store_persistent("source_file", ref, type_tag="file")
    try:
        await node.execute(context)
        await node.execute(context)
        assert not errors
        assert target.read_text(encoding="utf-8") == ("oldnewnew" if mode == "Append" else "new")
        assert [item["data"]["default"] for item in done] == (["new"] * 2 if forward else [ref] * 2)
        assert context.memory_bank.read_persistent_by_type("file") == {
            "source_file": ref, "another_name": ref,
        }
        if session:
            handle = session.get_resource(ref["ref_key"])
            assert handle is not None
            assert str(Path(handle.name).resolve()) == str(target.resolve())
    finally:
        if session:
            session.close_all()


async def test_create_unique_returns_reference_to_different_file(tmp_path):
    target = tmp_path / "existing.txt"
    target.write_text("preserved", encoding="utf-8")
    ref = {"type": "file", "path": str(target), "ref_key": "file:original"}
    node = _make_node({"file_path_source": "Upstream payload", "write_mode": "Create unique",
                       "vault_write": True, "vault_write_key": "created_file"})
    context, done, errors = _make_context(inputs={"file_path": ref, "content": "different"})
    await node.execute(context)
    assert not errors
    created = done[0]["data"]["default"]
    assert created["path"] != ref["path"]
    assert created["ref_key"] != ref["ref_key"]
    assert Path(created["path"]).read_text(encoding="utf-8") == "different"
    assert target.read_text(encoding="utf-8") == "preserved"
    assert context.memory_bank.read_persistent_by_type("file")["created_file"] == created


@pytest.mark.parametrize("node_type", ["file_output_node", "file_view_node"])
async def test_file_output_ui_explains_reference_reuse(node_type):
    _, wm, mb, _ = _make_services()
    wm.create_new("file_reference_output_copy")
    node_id = wm.add_node(node_type)

    class ConfigApp(App):
        CSS_PATH = str(Path(__file__).parent.parent / "frontend" / "styles.tcss")

        async def on_mount(self):
            await self.push_screen(NodeConfigScreen(wm._factory, wm, node_id,
                                  wm.get_node_data(node_id), memory_bank=mb))

    async with ConfigApp().run_test(size=(60, 24)) as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        screen = pilot.app.screen
        note = screen.query_one("#file-reference-output-note", Static)
        assert "same file keeps the same reference" in str(note.content)
        assert note.content_region.height >= 3
        assert any(str(label.content) == "Display name:" for label in screen.query(Label))
        forwarding = screen.query_one("#dead-drop-passthrough", Checkbox)
        if node_type == "file_output_node":
            assert str(forwarding.label) == "Forward incoming payload unchanged"
        forwarding.value = True
        await pilot.pause()
        assert note.display
        # An extra Vault name remains optional and independent of forwarding.
        assert screen.query_one("#vault-output-disabled-default", Checkbox).value


async def test_writer_reconstructs_reference_when_input_has_no_identity_key(tmp_path):
    target = tmp_path / "partial-reference.txt"
    session = RunSession("partial-reference")
    node = _make_node({"file_path_source": "Upstream payload"})
    context, done, errors = _make_context(
        inputs={"file_path": {"type": "file", "path": str(target)}, "content": "body"},
        run_session=session,
    )
    try:
        await node.execute(context)
        assert not errors
        ref = done[0]["data"]["default"]
        assert ref["ref_key"] == f"file:{target.resolve()}"
        assert session.get_resource(ref["ref_key"]) is not None
    finally:
        session.close_all()

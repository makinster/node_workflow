"""Exercise the shared source contract across real file and branch execution."""

import asyncio
import json

import pytest

from backend.events import FILE_VIEW_REQUESTED, RECOVERY_OPTIONS_AVAILABLE
from backend.validator import validate_workflow
from frontend.editor_workflow_adapter import EditorWorkflowAdapter
from frontend.screens.node_config import NodeConfigScreen
from tests.test_debug_nodes import _make_services


@pytest.mark.parametrize("selected_port,expected", [("path_a", "first\n"), ("path_b", "second\n")])
async def test_manager_reader_writer_parallel_merge_and_end_branch(tmp_path, selected_port, expected):
    master, wm, mb, bus = _make_services()
    wm.create_new("payload_plan")
    first, second = tmp_path / "first.txt", tmp_path / "second.txt"
    first.write_text("first\n", encoding="utf-8")
    second.write_text("second\n", encoding="utf-8")
    node_types = {"start": "start_node", "manager": "file_view_node", "branch": "branch_node",
                  "reader_a": "file_reader_node", "writer": "file_output_node",
                  "reader_b": "file_reader_node", "beacon": "branch_end_node",
                  "merge": "merge_node", "output": "text_output_node", "end": "end_node"}
    nodes = {name: wm.add_node(node_type) for name, node_type in node_types.items()}

    def configure(name, **values):
        config = dict(wm.get_node_data(nodes[name])["config"])
        config.update(values)
        wm.update_node_config(nodes[name], config)

    configure("start", greeting="incoming greeting", vault_write=True, vault_write_key="greeting")
    configure("manager", file_source="Configured", file=str(first), vault_write=True,
              vault_write_key="first_file", dead_drop_passthrough=True,
              additional_files=[{"id": "second", "path": str(second), "vault_key": "second_file"}],
              downstream_file_id="primary")
    configure("reader_a", input_source="Vault", input_vault_key="first_file",
              vault_write=True, vault_write_key="first_text")
    configure("reader_b", input_source="Vault", input_vault_key="second_file")
    configure("writer", content_source="Upstream payload", file_path_source="Vault",
              file_path_vault_key="first_file", write_mode="Append", dead_drop_passthrough=True)
    configure("merge", selected_input_port=selected_port)
    configure("output", label="Merged", input_source="Upstream payload")

    for source, port, target, input_port in [
        ("start", "default", "manager", "file"), ("manager", "default", "branch", "input"),
        ("branch", "path_a", "reader_a", "input"), ("reader_a", "default", "writer", "content"),
        ("writer", "default", "merge", "path_a"), ("branch", "path_b", "reader_b", "input"),
        ("reader_b", "default", "beacon", "input"), ("beacon", "default", "merge", "path_b"),
        ("merge", "default", "output", "input"), ("output", "default", "end", "input"),
    ]:
        wm.connect(nodes[source], port, nodes[target], input_port)

    wm.load_data(json.loads(json.dumps(wm.get_workflow_data_for_save())))
    # File and text keys are discoverable before execution and filtered by type.
    screen = NodeConfigScreen(wm._factory, wm, nodes["reader_b"], wm.get_node_data(nodes["reader_b"]), memory_bank=mb)
    choices = screen._vault_key_options({"file": {"vault_type": "file"}, "text": {"vault_type": "string"}})
    assert {key for _, key in choices["file"]} == {"first_file", "second_file"}
    assert "greeting" in {key for _, key in choices["string"]}
    assert "first_file" not in {key for _, key in choices["string"]}
    assert not validate_workflow(wm, wm._factory)["errors"]

    displays, recovery = [], []
    bus.subscribe(FILE_VIEW_REQUESTED, displays.append)
    def stop_on_error(event):
        recovery.append(event)
        master.submit_recovery_action(event["branch_id"], "TERMINATE_WORKFLOW")
    bus.subscribe(RECOVERY_OPTIONS_AVAILABLE, stop_on_error)
    assert await master.start_workflow()
    await asyncio.wait_for(master.wait_for_completion(), timeout=5)
    assert not recovery
    assert master.state.value == "FINISHED"
    assert [event["path"] for event in displays] == [str(first), str(second)]
    assert all(event["run_id"] and event["node_id"] == nodes["manager"] for event in displays)
    assert mb.read_transient(nodes["manager"], "default") == "incoming greeting"
    assert mb.read_persistent("first_text") == "first\n"
    assert first.read_text(encoding="utf-8") == "first\nfirst\n"
    assert second.read_text(encoding="utf-8") == "second\n"
    assert mb.read_transient(nodes["merge"], "default") == expected
    assert mb.read_transient(nodes["output"], "default") == f"[Merged] {expected}"
    assert mb.read_persistent("output_log") == [f"[Merged] {expected}", f"[END] Branch completed (received: [Merged] {expected})"]
    assert nodes["end"] in master.completed_nodes

    # Deleting/restoring the Manager hides/restores all of its declared refs.
    adapter = EditorWorkflowAdapter(wm, wm._factory)
    screen.workflow_adapter = adapter
    adapter.replace_with_placeholder(nodes["manager"])
    assert not screen._vault_key_options({"file": {"vault_type": "file"}})["file"]
    assert adapter.undo_placeholder(nodes["manager"])
    assert len(screen._vault_key_options({"file": {"vault_type": "file"}})["file"]) == 2

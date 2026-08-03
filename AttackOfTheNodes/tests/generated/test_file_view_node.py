"""Focused tests for file_view_node (FO3, docs/FILE_OUTPUT_BUILD_PLAN.md).

Backend-only coverage: FILE_VIEW_REQUESTED emission, render hints, reference
forwarding, and error paths. The frontend viewer-screen flow is covered by
the file_view pilot tests in tests/test_debug_nodes.py.
"""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.events import FILE_VIEW_REQUESTED
from backend.file_refs import file_reference
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("file_view_node")]


def _make_node(config_overrides=None):
    factory = NodeFactory()
    node = factory.create_node("file_view_node", "fv1")
    if config_overrides:
        node.config.update(config_overrides)
    return node


def _make_context(inputs=None, wire_bus=True):
    memory = MemoryBank(EventBus())
    done = []
    errors = []
    events = []
    context = NodeContext(
        node_id="fv1",
        branch_id="branch",
        run_id="run",
        inputs=inputs or {},
        memory_bank=memory,
        signal_done=done.append,
        signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
        publish_event=(lambda name, payload: events.append((name, payload)))
        if wire_bus
        else None,
    )
    return context, done, errors, events


def test_file_view_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("file_view_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "file_view_node")
    assert metadata["display_name"] == 'File Viewer'
    assert metadata["input_ports"] == ['file']
    assert metadata["output_ports"] == ['default']
    assert metadata["input_port_metadata"]["file"]["data_type"] == "file"
    out = metadata["output_port_metadata"]["default"]
    assert out["data_type"] == "file"
    assert out["pass_through"] is True


async def test_view_emits_event_and_forwards_reference(tmp_path):
    target = tmp_path / "notes.md"
    target.write_text("# hi\n", encoding="utf-8")
    node = _make_node()
    upstream_ref = file_reference(str(target))
    context, done, errors, events = _make_context(inputs={"file": upstream_ref})

    await node.execute(context)

    assert not errors
    assert events == [
        (
            FILE_VIEW_REQUESTED,
            {
                "path": str(target.resolve()),
                "ref_key": upstream_ref["ref_key"],
                "render": "markdown",
            },
        )
    ]
    # The incoming reference forwards downstream so later nodes (window
    # control, more writes) keep targeting the same file identity.
    assert done[0]["data"]["default"] == upstream_ref


async def test_configured_path_derives_reference_and_render_hint(tmp_path):
    target = tmp_path / "log.txt"
    target.write_text("plain body", encoding="utf-8")
    node = _make_node({"file_source": "Configured", "file": str(target)})
    context, done, errors, events = _make_context()

    await node.execute(context)

    assert not errors
    _, payload = events[0]
    assert payload["render"] == "plain"
    assert done[0]["data"]["default"]["type"] == "file"
    assert done[0]["data"]["default"]["path"] == str(target.resolve())


async def test_render_override_beats_extension(tmp_path):
    target = tmp_path / "notes.txt"
    target.write_text("# still markdown\n", encoding="utf-8")
    node = _make_node(
        {"file_source": "Configured", "file": str(target), "render": "Markdown"}
    )
    context, _, errors, events = _make_context()

    await node.execute(context)

    assert not errors
    assert events[0][1]["render"] == "markdown"


async def test_vault_reference_resolves(tmp_path):
    target = tmp_path / "vaulted.md"
    target.write_text("body", encoding="utf-8")
    node = _make_node({"file_source": "Vault", "file_vault_key": "report"})
    context, done, errors, events = _make_context()
    context.memory_bank.store_persistent(
        "report", file_reference(str(target)), type_tag="file"
    )

    await node.execute(context)

    assert not errors
    assert events[0][1]["path"] == str(target.resolve())


async def test_missing_file_is_a_node_error(tmp_path):
    node = _make_node(
        {"file_source": "Configured", "file": str(tmp_path / "gone.md")}
    )
    context, done, errors, events = _make_context()

    await node.execute(context)

    assert errors and "not found" in str(errors[0]).lower()
    assert not events
    assert not done


async def test_empty_file_input_is_a_node_error():
    node = _make_node()
    context, done, errors, events = _make_context(inputs={})

    await node.execute(context)

    assert errors and "file" in str(errors[0]).lower()
    assert not events


async def test_headless_context_is_inert_not_an_error(tmp_path):
    # No publish_event wired (headless / no-frontend run): the view request
    # goes nowhere, but the node still succeeds and forwards its reference.
    target = tmp_path / "quiet.md"
    target.write_text("x", encoding="utf-8")
    node = _make_node({"file_source": "Configured", "file": str(target)})
    context, done, errors, _ = _make_context(wire_bus=False)

    await node.execute(context)

    assert not errors
    assert done and done[0]["data"]["default"]["type"] == "file"


async def test_terminate_branch_flag_rides_the_done_payload(tmp_path):
    target = tmp_path / "end.md"
    target.write_text("x", encoding="utf-8")
    node = _make_node(
        {"file_source": "Configured", "file": str(target), "terminate_branch": True}
    )
    context, done, errors, _ = _make_context()

    await node.execute(context)

    assert not errors
    assert done[0].get("terminate_branch") is True

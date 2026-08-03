"""Focused tests for file_output_node (FO1, docs/FILE_OUTPUT_BUILD_PLAN.md).

Round-trips text and binary content through the node, checks the typed
`file` reference contract (D2), RunSession registration + run-end close,
write modes, routing (vault / dead-drop / terminate), and error paths.
"""

from __future__ import annotations

import base64

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext
from backend.run_session import RunSession


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("file_output_node")]


def _make_node(config_overrides=None):
    factory = NodeFactory()
    node = factory.create_node("file_output_node", "fo1")
    if config_overrides:
        node.config.update(config_overrides)
    return node


def _make_context(inputs=None, run_session=None):
    memory = MemoryBank(EventBus())
    done = []
    errors = []
    context = NodeContext(
        node_id="fo1",
        branch_id="branch",
        run_id="run",
        inputs=inputs or {},
        memory_bank=memory,
        signal_done=done.append,
        signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
        run_session=run_session,
    )
    return context, done, errors


def test_file_output_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("file_output_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "file_output_node")
    assert metadata["display_name"] == 'File Write'
    assert metadata["default_alias"] == 'File Write'
    assert metadata["input_ports"] == ['content', 'file_path']
    assert metadata["output_ports"] == ['default']
    # Every declared port exposes the per-port I/O contract (handoff §4/§6):
    # data_type defaults to "any", required defaults to False.
    for direction in ("input_port_metadata", "output_port_metadata"):
        for info in metadata[direction].values():
            assert info["data_type"] in {
                "string", "number", "bool", "var", "file", "ai_session", "any",
            }
            assert isinstance(info["required"], bool)


def test_unified_output_contract_survives_factory_exposure():
    # file_output_node is the unified inputs:/outputs: reference node
    # (absorbed from the retired example_file_instance_node): its outputs:
    # block declares name + data_type + required + to, and the factory must
    # surface all of it, not just fill defaults.
    factory = NodeFactory()
    meta = next(
        m for m in factory.get_node_types_metadata() if m["type"] == "file_output_node"
    )
    out = meta["output_port_metadata"]["default"]
    assert out["name"] == "File Reference"
    assert out["data_type"] == "file"
    assert out["required"] is True
    assert out["to"] == ["downstream", "vault"]
    assert out["pass_through"] is True
    path_in = meta["input_port_metadata"]["file_path"]
    assert path_in["data_type"] == "file"
    assert path_in["required"] is True


async def test_text_write_emits_resolvable_file_reference(tmp_path):
    target = tmp_path / "out.md"
    session = RunSession("run")
    node = _make_node({"file_path": str(target)})
    context, done, errors = _make_context(
        inputs={"content": "# Hello\n"}, run_session=session
    )

    await node.execute(context)

    assert not errors
    assert target.read_text(encoding="utf-8") == "# Hello\n"
    ref = done[0]["data"]["default"]
    assert ref["type"] == "file"
    assert ref["path"] == str(target.resolve())
    # The reference resolves to the registered RunSession handle (D2)...
    handle = session.get_resource(ref["ref_key"])
    assert handle is not None
    # ...and the handle dies with the run.
    session.close_all()
    assert handle.closed


async def test_binary_write_decodes_base64(tmp_path):
    target = tmp_path / "img.bin"
    payload = bytes(range(256))
    node = _make_node(
        {"file_path": str(target), "binary_content": True}
    )
    context, done, errors = _make_context(
        inputs={"content": base64.b64encode(payload).decode("ascii")},
        run_session=RunSession("run"),
    )

    await node.execute(context)

    assert not errors
    assert target.read_bytes() == payload


async def test_invalid_base64_is_a_node_error(tmp_path):
    node = _make_node(
        {"file_path": str(tmp_path / "img.bin"), "binary_content": True}
    )
    context, done, errors = _make_context(inputs={"content": "not base64!!"})

    await node.execute(context)

    assert errors and "Base64" in str(errors[0])
    assert not done


async def test_append_mode_accumulates_within_a_run(tmp_path):
    target = tmp_path / "log.txt"
    session = RunSession("run")
    node = _make_node({"file_path": str(target), "write_mode": "Append"})

    for chunk in ("one\n", "two\n"):
        context, _, errors = _make_context(
            inputs={"content": chunk}, run_session=session
        )
        await node.execute(context)
        assert not errors

    session.close_all()
    assert target.read_text(encoding="utf-8") == "one\ntwo\n"


async def test_overwrite_mode_replaces_content(tmp_path):
    target = tmp_path / "report.txt"
    session = RunSession("run")
    node = _make_node({"file_path": str(target)})

    for body in ("first, longer body", "second"):
        context, _, errors = _make_context(
            inputs={"content": body}, run_session=session
        )
        await node.execute(context)
        assert not errors

    session.close_all()
    assert target.read_text(encoding="utf-8") == "second"


async def test_create_unique_mode_never_replaces(tmp_path):
    target = tmp_path / "note.md"
    target.write_text("original", encoding="utf-8")
    node = _make_node({"file_path": str(target), "write_mode": "Create unique"})
    context, done, errors = _make_context(
        inputs={"content": "fresh"}, run_session=RunSession("run")
    )

    await node.execute(context)

    assert not errors
    assert target.read_text(encoding="utf-8") == "original"
    unique = tmp_path / "note (1).md"
    assert unique.read_text(encoding="utf-8") == "fresh"
    assert done[0]["data"]["default"]["path"] == str(unique.resolve())


async def test_write_works_without_run_session(tmp_path):
    target = tmp_path / "solo.txt"
    node = _make_node({"file_path": str(target)})
    context, done, errors = _make_context(inputs={"content": "no session"})

    await node.execute(context)

    assert not errors
    assert target.read_text(encoding="utf-8") == "no session"
    ref = done[0]["data"]["default"]
    assert ref["type"] == "file"
    assert ref["path"] == str(target.resolve())


async def test_parent_directories_are_created(tmp_path):
    target = tmp_path / "nested" / "deeper" / "out.txt"
    node = _make_node({"file_path": str(target)})
    context, _, errors = _make_context(
        inputs={"content": "x"}, run_session=RunSession("run")
    )

    await node.execute(context)

    assert not errors
    assert target.read_text(encoding="utf-8") == "x"


async def test_vault_write_stores_typed_file_reference(tmp_path):
    target = tmp_path / "vaulted.txt"
    node = _make_node(
        {
            "file_path": str(target),
            "vault_write": True,
            "vault_write_key": "report_file",
        }
    )
    context, done, errors = _make_context(
        inputs={"content": "body"}, run_session=RunSession("run")
    )

    await node.execute(context)

    assert not errors
    entry = context.memory_bank.read_persistent("report_file")
    assert entry == done[0]["data"]["default"]
    assert context.memory_bank.read_persistent_by_type("file") == {
        "report_file": entry
    }


async def test_dead_drop_forwards_incoming_content(tmp_path):
    target = tmp_path / "side_effect.txt"
    node = _make_node(
        {"file_path": str(target), "dead_drop_passthrough": True}
    )
    context, done, errors = _make_context(
        inputs={"content": "payload travels on"}, run_session=RunSession("run")
    )

    await node.execute(context)

    assert not errors
    assert target.read_text(encoding="utf-8") == "payload travels on"
    assert done[0]["data"]["default"] == "payload travels on"


async def test_terminate_branch_flag_rides_the_done_payload(tmp_path):
    node = _make_node(
        {"file_path": str(tmp_path / "last.txt"), "terminate_branch": True}
    )
    context, done, errors = _make_context(
        inputs={"content": "end"}, run_session=RunSession("run")
    )

    await node.execute(context)

    assert not errors
    assert done[0].get("terminate_branch") is True


async def test_upstream_file_reference_resolves_to_its_path(tmp_path):
    target = tmp_path / "from_ref.txt"
    node = _make_node({"file_path_source": "Upstream payload"})
    upstream_ref = {
        "type": "file",
        "ref_key": f"file:{target}",
        "path": str(target),
    }
    context, done, errors = _make_context(
        inputs={"content": "via reference", "file_path": upstream_ref},
        run_session=RunSession("run"),
    )

    await node.execute(context)

    assert not errors
    assert target.read_text(encoding="utf-8") == "via reference"


async def test_vault_sourced_content_and_path(tmp_path):
    target = tmp_path / "from_vault.txt"
    node = _make_node(
        {
            "content_source": "Vault",
            "content_vault_key": "body_key",
            "file_path_source": "Vault",
            "file_path_vault_key": "path_key",
        }
    )
    context, done, errors = _make_context(run_session=RunSession("run"))
    context.memory_bank.store_persistent("body_key", "vault body")
    context.memory_bank.store_persistent(
        "path_key", {"type": "file", "ref_key": "file:x", "path": str(target)},
        type_tag="file",
    )

    await node.execute(context)

    assert not errors
    assert target.read_text(encoding="utf-8") == "vault body"


async def test_empty_path_is_a_node_error():
    node = _make_node()
    context, done, errors = _make_context(inputs={"content": "x"})

    await node.execute(context)

    assert errors and "path" in str(errors[0]).lower()
    assert not done


async def test_missing_upstream_content_is_a_node_error(tmp_path):
    node = _make_node({"file_path": str(tmp_path / "never.txt")})
    context, done, errors = _make_context(inputs={})

    await node.execute(context)

    assert errors and "content" in str(errors[0]).lower()
    assert not done
    assert not (tmp_path / "never.txt").exists()


# ---------------------------------------------------------------------------
# FO5: open after write + placement (FakeWindowManager)
# ---------------------------------------------------------------------------

def _session_with_fake_manager(fake):
    from backend.nodes.io.window_support import WINDOW_MANAGER_RESOURCE

    session = RunSession("run")
    session.register_resource(WINDOW_MANAGER_RESOURCE, fake)
    return session


async def test_open_after_write_opens_places_and_registers(tmp_path):
    from backend.window_manager import FakeWindowManager

    target = tmp_path / "opened.md"
    fake = FakeWindowManager()
    session = _session_with_fake_manager(fake)
    node = _make_node(
        {
            "file_path": str(target),
            "open_after_write": True,
            "window_placement": "Right of AOTN",
        }
    )
    context, done, errors = _make_context(
        inputs={"content": "body"}, run_session=session
    )

    await node.execute(context)

    assert not errors
    resolved = str(target.resolve())
    assert fake.opened == [(resolved, "Right of AOTN")]
    window = session.get_resource(f"window:file:{resolved}")
    assert window is not None and window.path == resolved

    # Default (close_on_run_end off, D12): run end must NOT close the window.
    session.close_all()
    assert fake.closed == []


async def test_close_when_run_ends_closes_at_close_all(tmp_path):
    from backend.window_manager import FakeWindowManager

    target = tmp_path / "temp_view.md"
    fake = FakeWindowManager()
    session = _session_with_fake_manager(fake)
    node = _make_node(
        {
            "file_path": str(target),
            "open_after_write": True,
            "close_on_run_end": True,
        }
    )
    context, _, errors = _make_context(
        inputs={"content": "body"}, run_session=session
    )

    await node.execute(context)
    assert not errors
    assert fake.opened == [(str(target.resolve()), "OS default")]
    assert fake.closed == []

    session.close_all()
    assert [ref.path for ref in fake.closed] == [str(target.resolve())]


async def test_discovery_failure_is_not_a_node_error(tmp_path):
    from backend.window_manager import FakeWindowManager

    target = tmp_path / "unplaced.md"
    fake = FakeWindowManager(discovery_fails=True)
    session = _session_with_fake_manager(fake)
    node = _make_node(
        {
            "file_path": str(target),
            "open_after_write": True,
            "window_placement": "Other monitor",
        }
    )
    context, done, errors = _make_context(
        inputs={"content": "body"}, run_session=session
    )

    await node.execute(context)

    # D4: the file opened; placement degraded; the node stays successful and
    # no WindowRef registers (FO6 then soft-errors per its own rule).
    assert not errors
    assert done and done[0]["data"]["default"]["type"] == "file"
    assert fake.opened, "The launch still happens"
    resolved = str(target.resolve())
    assert session.get_resource(f"window:file:{resolved}") is None
    session.close_all()


async def test_open_after_write_off_never_touches_the_manager(tmp_path):
    from backend.window_manager import FakeWindowManager

    fake = FakeWindowManager()
    session = _session_with_fake_manager(fake)
    node = _make_node({"file_path": str(tmp_path / "quiet.md")})
    context, _, errors = _make_context(
        inputs={"content": "body"}, run_session=session
    )

    await node.execute(context)

    assert not errors
    assert fake.opened == []
    session.close_all()

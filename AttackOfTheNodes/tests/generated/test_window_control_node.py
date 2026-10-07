"""Focused tests for window_control_node (FO6, docs/FILE_OUTPUT_BUILD_PLAN.md).

Runs against FakeWindowManager: focus/minimize/close dispatch by file
reference, and the soft-error rule — a missing window is a warning +
pass-through, never a node error.
"""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.file_refs import file_reference
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext
from backend.nodes.io.window_support import WINDOW_MANAGER_RESOURCE
from backend.run_session import RunSession
from backend.window_manager import FakeWindowManager


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("window_control_node")]


def _make_node(config_overrides=None):
    factory = NodeFactory()
    node = factory.create_node("window_control_node", "wc1")
    if config_overrides:
        node.config.update(config_overrides)
    return node


def _make_context(inputs=None, run_session=None):
    memory = MemoryBank(EventBus())
    done = []
    errors = []
    context = NodeContext(
        node_id="wc1",
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


def _session_with_open_window(fake, path):
    """A RunSession holding the fake manager and one discovered window."""
    session = RunSession("run")
    session.register_resource(WINDOW_MANAGER_RESOURCE, fake)
    ref = file_reference(str(path))
    window = fake.open_path(str(path))
    session.register_resource(f"window:{ref['ref_key']}", window)
    return session, ref, window


def test_window_control_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("window_control_node")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "window_control_node")
    assert metadata["display_name"] == 'Window Control'
    assert metadata["input_ports"] == ['file']
    assert metadata["input_port_metadata"]["file"]["data_type"] == "file"
    # Upstream/Vault only: a window target is always a workflow-owned file
    # reference, never a hand-typed value.
    assert metadata["input_port_metadata"]["file"]["sources"] == ["upstream", "vault"]


@pytest.mark.parametrize(
    ("action", "attribute"),
    [("Focus", "focused"), ("Minimize", "minimized"), ("Close", "closed")],
)
async def test_actions_dispatch_to_the_registered_window(tmp_path, action, attribute):
    fake = FakeWindowManager()
    session, ref, window = _session_with_open_window(fake, tmp_path / "doc.md")
    node = _make_node({"action": action})
    context, done, errors = _make_context(inputs={"file": ref}, run_session=session)

    await node.execute(context)

    assert not errors
    assert getattr(fake, attribute) == [window]
    assert done[0]["data"]["default"] == ref  # pass-through
    session.close_all()


async def test_missing_window_is_a_soft_pass_through(tmp_path):
    fake = FakeWindowManager()
    session = RunSession("run")
    session.register_resource(WINDOW_MANAGER_RESOURCE, fake)
    never_opened = file_reference(str(tmp_path / "never_opened.md"))
    node = _make_node({"action": "Close"})
    context, done, errors = _make_context(
        inputs={"file": never_opened}, run_session=session
    )

    await node.execute(context)

    # Never opened / discovery failed (D4) → warning + pass-through.
    assert not errors
    assert fake.closed == []
    assert done[0]["data"]["default"] == never_opened
    session.close_all()


async def test_no_run_session_is_a_soft_pass_through(tmp_path):
    ref = file_reference(str(tmp_path / "outside_run.md"))
    node = _make_node()
    context, done, errors = _make_context(inputs={"file": ref})

    await node.execute(context)

    assert not errors
    assert done[0]["data"]["default"] == ref


async def test_failed_action_is_still_soft(tmp_path):
    class StubbornFake(FakeWindowManager):
        def focus(self, ref):
            super().focus(ref)
            return False  # window vanished between discovery and control

    fake = StubbornFake()
    session, ref, _ = _session_with_open_window(fake, tmp_path / "gone.md")
    node = _make_node({"action": "Focus"})
    context, done, errors = _make_context(inputs={"file": ref}, run_session=session)

    await node.execute(context)

    assert not errors
    assert done, "A racing window is a warning, not a node error"
    session.close_all()


async def test_vault_sourced_reference_targets_the_same_window(tmp_path):
    fake = FakeWindowManager()
    session, ref, window = _session_with_open_window(fake, tmp_path / "vaulted.md")
    node = _make_node({"file_source": "Vault", "file_vault_key": "the_file"})
    context, done, errors = _make_context(run_session=session)
    context.memory_bank.store_persistent("the_file", ref, type_tag="file")

    await node.execute(context)

    assert not errors
    assert fake.focused == [window]
    session.close_all()


async def test_raw_path_resolves_to_the_writers_window_identity(tmp_path):
    # A plain path string (e.g. reconstructed cross-run) resolves to the
    # same window key the writer registered (D6).
    target = tmp_path / "raw.md"
    target.write_text("x", encoding="utf-8")
    fake = FakeWindowManager()
    session, _, window = _session_with_open_window(fake, target.resolve())
    node = _make_node()
    context, done, errors = _make_context(
        inputs={"file": str(target)}, run_session=session
    )

    await node.execute(context)

    assert not errors
    assert fake.focused == [window]
    session.close_all()


async def test_empty_file_input_is_a_node_error():
    node = _make_node()
    context, done, errors = _make_context(inputs={})

    await node.execute(context)

    assert errors and "file" in str(errors[0]).lower()
    assert not done

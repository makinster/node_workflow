"""Copied Windows paths across File Writer/Viewer input sources."""

import subprocess
from types import SimpleNamespace

import pytest

from backend.node_factory import NodeFactory
from backend.run_session import RunSession
from backend.validator import validate_workflow
from tests.generated.test_file_output_node import _make_context as writer_context
from tests.generated.test_file_view_node import _make_context as viewer_context


def make_case(kind, source, value, session):
    factory = NodeFactory()
    routed = value if source == "Configured" or isinstance(value, dict) else {"type": "file", "path": value, "ref_key": "file:fixture"}
    if kind == "writer":
        node = factory.create_node("file_output_node", "writer")
        node.config.update(file_path_source=source, file_path=value,
                           file_path_vault_key="target")
        context, done, errors = writer_context(
            inputs={"content": "copied path body", "file_path": routed},
            run_session=session,
        )
        context.memory_bank.store_persistent("target", routed, type_tag="file")
        return node, context, done, errors, []
    node = factory.create_node("file_view_node", "viewer")
    node.config.update(file_source=source, file=value, file_vault_key="target")
    context, done, errors, events = viewer_context(inputs={"file": routed})
    context.run_session = session
    context.memory_bank.store_persistent("target", routed, type_tag="file")
    return node, context, done, errors, events


@pytest.mark.parametrize("kind", ["writer", "viewer"])
@pytest.mark.parametrize("source", ["Configured", "Upstream payload", "Vault"])
@pytest.mark.parametrize("quoted", [False, True])
@pytest.mark.parametrize("session_enabled", [False, True])
async def test_windows_copied_path_uses_wsl_file(tmp_path, monkeypatch, kind, source,
                                              quoted, session_enabled):
    monkeypatch.setattr("backend.file_paths.platform.system", lambda: "Linux")
    monkeypatch.setattr("backend.file_paths.platform.release", lambda: "microsoft-WSL2")
    target = tmp_path / "sample document.md"
    if kind == "viewer":
        target.write_text("# existing file", encoding="utf-8")
    windows = r"C:\Users\name\sample document.md"
    copied = f'"{windows}"' if quoted else windows
    calls = []

    def convert(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, f"{target}\n", "")

    monkeypatch.setattr("backend.file_paths.subprocess.run", convert)
    # Exercise typed references as well as plain configured paths.
    value = copied if source == "Configured" else {
        "type": "file", "path": copied, "ref_key": "file:upstream-identity",
    }
    session = RunSession("paths") if session_enabled else None
    node, context, done, errors, events = make_case(kind, source, value, session)
    before = dict(node.config)
    try:
        await node.execute(context)
        assert not errors
        assert done
        if kind == "writer":
            assert target.read_text(encoding="utf-8") == "copied path body"
            ref = done[0]["data"]["default"]
            if isinstance(value, dict):
                assert ref == value
            else:
                assert ref["path"] == str(target.resolve())
                assert ref["ref_key"] == f"file:{target.resolve()}"
        else:
            assert events[0][1]["path"] == str(target.resolve())
            assert events[0][1]["render"] == "markdown"
            if isinstance(value, dict):
                assert done[0]["data"]["default"] == value
        assert node.config == before
        if source == "Configured":
            nodes = {"start": {"type": "start_node"}, node.node_id: {
                "type": node.node_type, "config": node.config,
            }}
            result = validate_workflow(
                SimpleNamespace(get_all_node_data=lambda: nodes), NodeFactory(),
            )
            assert not [item for item in result["errors"] + result["warnings"]
                        if "path" in item["message"].lower()
                        or "not found" in item["message"].lower()]
            assert len(calls) == 2
        else:
            assert len(calls) == 1
        assert all(call == ["wslpath", "-u", windows] for call in calls)
    finally:
        if session:
            session.close_all()


@pytest.mark.parametrize("kind", ["writer", "viewer"])
async def test_quoted_linux_file_path(tmp_path, kind):
    target = tmp_path / "local file.md"
    target.write_text("original", encoding="utf-8")
    node, context, done, errors, events = make_case(
        kind, "Configured", f'"{target}"', None,
    )
    await node.execute(context)
    assert not errors
    assert done
    assert done[0]["data"]["default"]["path"] == str(target.resolve())


@pytest.mark.parametrize("kind", ["writer", "viewer"])
@pytest.mark.parametrize("failure", ["unavailable", "timeout", "rejected"])
async def test_path_conversion_failure_is_reported(tmp_path, monkeypatch, kind, failure):
    monkeypatch.setattr("backend.file_paths.platform.system", lambda: "Linux")
    monkeypatch.setattr("backend.file_paths.platform.release", lambda: "microsoft-WSL2")

    def convert(args, **kwargs):
        if failure == "unavailable":
            raise FileNotFoundError("wslpath")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 5)
        return subprocess.CompletedProcess(args, 1, "", "failed")

    monkeypatch.setattr("backend.file_paths.subprocess.run", convert)
    node, context, done, errors, events = make_case(
        kind, "Configured", r"C:\Users\name\file.md", None,
    )
    await node.execute(context)
    assert not done and not events
    assert len(errors) == 1
    assert "Could not convert" in str(errors[0])


@pytest.mark.parametrize("source, message", [
    ("Configured", "Enter a file path in Parameters"),
    ("Vault", "Select a File path Vault key"),
    ("Upstream payload", "Connect a typed file reference"),
])
async def test_writer_missing_path_explains_selected_source(source, message):
    node, context, done, errors, _ = make_case("writer", source, "", None)
    await node.execute(context)
    assert not done
    assert source in str(errors[0])
    assert message in str(errors[0])

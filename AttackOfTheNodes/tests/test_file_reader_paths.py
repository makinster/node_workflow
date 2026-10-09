"""File Reader copied-path handling and actionable read errors."""

import subprocess
from types import SimpleNamespace

import pytest

from backend.file_paths import normalize_local_path
from backend.nodes.file_reader_node import FileReaderNode
from backend.run_session import RunSession
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("file_reader_node")]


@pytest.mark.parametrize("session", [False, True])
@pytest.mark.parametrize("quotes", ['', '"', "'"])
async def test_quoted_paths_read_text_without_changing_config(tmp_path, session, quotes):
    target = tmp_path / "sample document.txt"
    target.write_text("hello café", encoding="utf-8")
    configured = f"  {quotes}{target}{quotes}  "
    node = FileReaderNode("reader", {"file_path": configured})
    done, errors = [], []
    resources = RunSession("test") if session else None
    context = SimpleNamespace(run_session=resources, signal_done=done.append,
                              signal_error=errors.append)
    try:
        await node.execute(context)
        await node.execute(context)
        assert not errors
        assert [event["data"]["default"] for event in done] == ["hello café"] * 2
        assert node.config["file_path"] == configured
    finally:
        if resources:
            resources.close_all()


def _wsl(monkeypatch):
    monkeypatch.setattr("backend.file_paths.platform.system", lambda: "Linux")
    monkeypatch.setattr("backend.file_paths.platform.release", lambda: "microsoft-WSL2")


@pytest.mark.parametrize("quoted", [False, True])
async def test_windows_path_converted_for_execution_and_validation(tmp_path, monkeypatch, quoted):
    _wsl(monkeypatch)
    target = tmp_path / "sample document.txt"
    target.write_text("Windows file", encoding="utf-8")
    windows = r"C:\Users\name\sample document.txt"
    calls = []
    def convert(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, f"{target}\n", "")
    monkeypatch.setattr("backend.file_paths.subprocess.run", convert)
    configured = f'"{windows}"' if quoted else windows
    node = FileReaderNode("reader", {"file_path": configured})
    done, errors = [], []
    session = RunSession("test")
    try:
        await node.execute(SimpleNamespace(run_session=session, signal_done=done.append,
                                           signal_error=errors.append))
    finally:
        session.close_all()
    assert not errors
    assert done[0]["data"]["default"] == "Windows file"
    nodes = {"start": {"type": "start_node"}, "reader": {
        "type": "file_reader_node", "config": {"file_path": configured}}}
    result = validate_workflow(SimpleNamespace(get_all_node_data=lambda: nodes), NodeFactory())
    assert not [item for item in result["errors"] + result["warnings"]
                if "path" in item["message"].lower() or "not found" in item["message"].lower()]
    assert calls == [["wslpath", "-u", windows]] * 2


@pytest.mark.parametrize("kind, message", [
    ("empty", "Enter a file path"), ("missing", "file not found"),
    ("folder", "is a folder"), ("encoding", "UTF-8"), ("null", "null character"),
])
@pytest.mark.parametrize("session", [False, True])
async def test_read_errors_are_actionable(tmp_path, kind, message, session):
    target = tmp_path / "file.txt"
    if kind == "encoding":
        target.write_bytes(b"\xff\xfe")
    path = {"empty": '""', "folder": str(tmp_path), "null": "bad\x00path"}.get(kind, str(target))
    done, errors = [], []
    resources = RunSession("test") if session else None
    try:
        await FileReaderNode("reader", {"file_path": path}).execute(
            SimpleNamespace(run_session=resources, signal_done=done.append,
                            signal_error=errors.append))
        assert not done
        assert len(errors) == 1
        assert message in str(errors[0])
    finally:
        if resources:
            resources.close_all()


@pytest.mark.parametrize("failure", ["unavailable", "timeout", "rejected"])
def test_wsl_conversion_failures_are_actionable(monkeypatch, failure):
    _wsl(monkeypatch)
    def convert(args, **kwargs):
        if failure == "unavailable":
            raise FileNotFoundError("wslpath")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 5)
        return subprocess.CompletedProcess(args, 1, "", "conversion failed")
    monkeypatch.setattr("backend.file_paths.subprocess.run", convert)
    with pytest.raises(ValueError, match="Could not convert"):
        normalize_local_path(r"C:\Users\name\file.txt")


def test_windows_paths_on_other_linux_fail_clearly(monkeypatch):
    monkeypatch.setattr("backend.file_paths.platform.system", lambda: "Linux")
    monkeypatch.setattr("backend.file_paths.platform.release", lambda: "generic")
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    with pytest.raises(ValueError, match="not accessible"):
        normalize_local_path(r"C:\Users\name\file.txt")


def test_native_windows_keeps_drive_path(monkeypatch):
    monkeypatch.setattr("backend.file_paths.platform.system", lambda: "Windows")
    path = r"C:\Users\name\file.txt"
    assert str(normalize_local_path(f'"{path}"')) == path


def test_wsl_drive_relative_path_rejected(monkeypatch):
    _wsl(monkeypatch)
    with pytest.raises(ValueError, match="full Windows path"):
        normalize_local_path("C:file.txt")


def test_invalid_path_is_preflight_error(monkeypatch):
    _wsl(monkeypatch)
    nodes = {"start": {"type": "start_node"}, "reader": {
        "type": "file_reader_node", "config": {"file_path": '""'}}}
    result = validate_workflow(SimpleNamespace(get_all_node_data=lambda: nodes), NodeFactory())
    assert any("Enter a file path" in item["message"] for item in result["errors"])


async def test_permission_denied_has_clear_error(tmp_path, monkeypatch):
    session = RunSession("test")
    def denied(*args, **kwargs):
        raise PermissionError("denied")
    monkeypatch.setattr(session, "open_file", denied)
    errors = []
    done = []
    await FileReaderNode("reader", {"file_path": str(tmp_path / "file.txt")}).execute(
        SimpleNamespace(run_session=session, signal_done=done.append, signal_error=errors.append))
    assert not done
    assert "permission denied" in str(errors[0])
    session.close_all()

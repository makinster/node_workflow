"""ESP32 proof slice (distributed build plan, between steps 3 and 4).

Pipeline: `aotn run capture` -> HTTP GET /capture saves the raw bytes as a
run-owned `file` -> on failure the `error` port routes (through an Error Mux)
to a notification POST. Run-owned files (R4) are deleted when the run
succeeds and kept when it fails or is stopped.

Everything runs against a local HTTP server; no hardware is needed.
"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

import pytest

from backend import persistence
from backend.configuration_manager import ConfigurationManager
from backend.event_bus import EventBus
from backend.events import NODE_EXECUTION_UPDATE, WORKFLOW_STATE_UPDATE
from backend.file_refs import (
    LIFETIME_KEPT,
    LIFETIME_RUN,
    file_reference,
    reference_lifetime,
)
from backend.master_state import MasterState
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.output_manager import OutputManager
from backend.run_policies import TerminatePolicy
from backend.run_session import RunSession
from backend.workflow_map import WorkflowMap

from tests.test_cli import aotn


RUN_TIMEOUT = 10.0
# A JPEG-shaped body that is not valid UTF-8 anywhere near its markers.
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(range(256)) * 64 + b"\xff\xd9"


@pytest.fixture(autouse=True)
def _records_in_tmp(tmp_path, monkeypatch):
    from backend import error_handler, output_manager, run_history

    monkeypatch.setattr(error_handler, "RUN_ERRORS_DIR", tmp_path / "run_errors")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history")
    monkeypatch.setattr(output_manager, "RUN_OUTPUTS_DIR", tmp_path / "run_outputs")
    monkeypatch.setattr(persistence, "RUN_FILES_DIR", tmp_path / "run_files")


class _Camera(BaseHTTPRequestHandler):
    notifications: List[Dict[str, Any]] = []

    def do_GET(self):  # noqa: N802 - http.server API
        if self.path == "/capture":
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(JPEG)))
            self.end_headers()
            self.wfile.write(JPEG)
        else:
            self.send_response(503)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"camera busy")

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        type(self).notifications.append({
            "path": self.path,
            "content_type": self.headers.get("Content-Type"),
            "body": self.rfile.read(length),
        })
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def camera():
    _Camera.notifications = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Camera)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", _Camera.notifications
    finally:
        server.shutdown()
        server.server_close()


def _capture_workflow(workflow_map: WorkflowMap, base: str, path: str = "/capture",
                      keep: bool = False) -> Dict[str, str]:
    start = workflow_map.add_node("start_node")
    capture = workflow_map.add_node("http_request_node")
    mux = workflow_map.add_node("error_mux_node")
    notify = workflow_map.add_node("http_request_node")
    workflow_map.update_node_config(capture, {
        "url": base + path, "response_mode": "file", "keep_response_file": keep,
        "timeout_seconds": 5.0,
    })
    workflow_map.update_node_config(mux, {"path_a_codes": "http_status, network, timeout"})
    workflow_map.update_node_config(notify, {
        "url": base + "/notify", "method": "POST", "body_source": "input",
    })
    workflow_map.connect(start, "default", capture, "input")
    workflow_map.connect(capture, "error", mux, "error")
    workflow_map.connect(mux, "path_a", notify, "input")
    return {"start": start, "capture": capture, "mux": mux, "notify": notify}


def _services():
    bus = EventBus()
    workflow_map = WorkflowMap(NodeFactory(), bus)
    master = MasterState(workflow_map, MemoryBank(bus), bus,
                         output_manager=OutputManager(),
                         configuration_manager=ConfigurationManager())
    workflow_map.create_new("Capture")
    return bus, workflow_map, master


def _on_done(bus, node_id, callback):
    def handler(payload):
        if payload.get("node_id") == node_id and payload.get("status") == "done":
            callback()

    bus.subscribe(NODE_EXECUTION_UPDATE, handler)


async def _finish(master):
    await asyncio.wait_for(master.wait_for_completion(), timeout=RUN_TIMEOUT)


# ---------------------------------------------------------------------------
# Binary-safe HTTP + run-owned files
# ---------------------------------------------------------------------------


async def test_jpeg_is_saved_intact_and_deleted_when_the_run_succeeds(camera, tmp_path):
    base, notifications = camera
    bus, workflow_map, master = _services()
    ids = _capture_workflow(workflow_map, base)
    seen: Dict[str, Any] = {}

    def check_file():
        ref = master._memory_bank.read_transient(ids["capture"], "default")
        seen["ref"] = ref
        seen["bytes"] = Path(ref["path"]).read_bytes()

    # FINISHED is published just before the run is recorded and cleaned up.
    bus.subscribe(WORKFLOW_STATE_UPDATE,
                  lambda p: check_file() if p["state"] == "FINISHED" else None)
    assert await master.start_workflow(recovery_policy=TerminatePolicy("terminate_workflow"))
    await _finish(master)

    ref = seen["ref"]
    assert ref["type"] == "file" and ref["lifetime"] == LIFETIME_RUN
    assert seen["bytes"] == JPEG
    path = Path(ref["path"])
    assert path.parent == tmp_path / "run_files" / master.current_run_id
    assert path.suffix == ".jpg"
    json.dumps(ref)  # payloads stay JSON
    assert master.state.value == "FINISHED"
    assert notifications == []
    # Success: the run-owned file and its run directory are gone.
    assert not path.exists()
    assert not path.parent.exists()


async def test_kept_response_file_survives_a_successful_run(camera):
    base, _ = camera
    bus, workflow_map, master = _services()
    ids = _capture_workflow(workflow_map, base, keep=True)

    assert await master.start_workflow(recovery_policy=TerminatePolicy("terminate_workflow"))
    await _finish(master)

    ref = master._memory_bank.read_transient(ids["capture"], "default")
    assert ref["lifetime"] == LIFETIME_KEPT
    assert Path(ref["path"]).read_bytes() == JPEG


async def test_failing_endpoint_routes_the_error_to_the_notification(camera):
    base, notifications = camera
    bus, workflow_map, master = _services()
    ids = _capture_workflow(workflow_map, base, path="/broken")

    assert await master.start_workflow(recovery_policy=TerminatePolicy("terminate_workflow"))
    await _finish(master)

    assert master.state.value == "FINISHED"
    assert len(notifications) == 1
    note = notifications[0]
    assert note["path"] == "/notify"
    assert note["content_type"] == "application/json"
    sent = json.loads(note["body"])
    assert sent["code"] == "http_status"
    assert sent["node_id"] == ids["capture"]
    assert sent["run_id"] == master.current_run_id
    assert sent["details"]["status"] == 503
    assert sent["details"]["response_body"] == "camera busy"
    assert ids["notify"] in master.completed_nodes
    errors = master.error_handler.get_errors_for_run(master.current_run_id)
    assert [e["code"] for e in errors] == ["http_status"]


async def test_run_files_are_kept_when_the_run_fails(camera):
    base, _ = camera
    bus, workflow_map, master = _services()
    ids = _capture_workflow(workflow_map, base)
    failing = workflow_map.add_node("error_node")
    workflow_map.connect(ids["capture"], "default", failing, "input")

    assert await master.start_workflow(recovery_policy=TerminatePolicy("terminate_workflow"))
    await _finish(master)

    assert master.state.value == "ERROR"
    ref = master._memory_bank.read_transient(ids["capture"], "default")
    assert Path(ref["path"]).read_bytes() == JPEG


async def test_run_files_are_kept_when_the_run_finishes_with_errors(camera):
    base, _ = camera
    bus, workflow_map, master = _services()
    ids = _capture_workflow(workflow_map, base)
    failing = workflow_map.add_node("error_node")
    workflow_map.connect(ids["capture"], "default", failing, "input")

    assert await master.start_workflow(recovery_policy=TerminatePolicy("terminate_branch"))
    await _finish(master)

    assert master.state.value == "FINISHED"
    ref = master._memory_bank.read_transient(ids["capture"], "default")
    assert Path(ref["path"]).exists()


async def test_run_files_are_kept_when_the_run_is_stopped(camera):
    base, _ = camera
    bus, workflow_map, master = _services()
    ids = _capture_workflow(workflow_map, base)
    wait = workflow_map.add_node("sleep_node")
    workflow_map.update_node_config(wait, {"duration": 5})
    workflow_map.connect(ids["capture"], "default", wait, "input")
    loop = asyncio.get_running_loop()
    _on_done(bus, ids["capture"], lambda: loop.call_soon(master.stop))

    assert await master.start_workflow(recovery_policy=TerminatePolicy("terminate_workflow"))
    await _finish(master)

    ref = master._memory_bank.read_transient(ids["capture"], "default")
    assert Path(ref["path"]).exists()


# ---------------------------------------------------------------------------
# The cron entry point: `aotn run <workflow>`
# ---------------------------------------------------------------------------


def _write_capture(tmp_path: Path, base: str, path: str) -> Path:
    bus = EventBus()
    workflow_map = WorkflowMap(NodeFactory(), bus)
    workflow_map.create_new("capture")
    _capture_workflow(workflow_map, base, path=path)
    target = tmp_path / "capture.json"
    target.write_text(json.dumps(workflow_map.get_workflow_data_for_save()), encoding="utf-8")
    return target


def test_aotn_run_capture_cleans_up_after_success(camera, tmp_path):
    base, notifications = camera
    workflow = _write_capture(tmp_path, base, "/capture")
    data_dir = tmp_path / "data"

    result = aotn(str(workflow), data_dir=data_dir)

    assert result.returncode == 0, result.stderr
    assert notifications == []
    run_files = data_dir / "run_files"
    assert not run_files.exists() or not any(run_files.iterdir())


def test_aotn_run_capture_notifies_on_failure(camera, tmp_path):
    base, notifications = camera
    workflow = _write_capture(tmp_path, base, "/broken")

    result = aotn(str(workflow), data_dir=tmp_path / "data")

    # The error was handled by routing it, but it is still logged (exit 1);
    # see SESSION_LOG open items.
    assert result.returncode == 1, result.stderr
    assert len(notifications) == 1
    assert json.loads(notifications[0]["body"])["code"] == "http_status"


# ---------------------------------------------------------------------------
# RunSession and file reference units (R4)
# ---------------------------------------------------------------------------


def test_file_reference_lifetime_is_optional_and_defaults_to_kept():
    plain = file_reference("/tmp/a.bin")
    assert "lifetime" not in plain
    assert reference_lifetime(plain) == LIFETIME_KEPT
    assert reference_lifetime("/tmp/a.bin") == LIFETIME_KEPT
    assert reference_lifetime(file_reference("/tmp/a.bin", LIFETIME_RUN)) == LIFETIME_RUN
    with pytest.raises(ValueError):
        file_reference("/tmp/a.bin", "forever")


def test_run_session_names_are_safe_and_unique(tmp_path):
    session = RunSession("run_x", files_root=tmp_path)
    first = session.new_run_file("../../etc/cam shot.jpg")
    second = session.new_run_file("cam shot.jpg")
    assert first.parent == tmp_path / "run_x"
    assert first.name == "cam_shot.jpg"
    assert second.name == "cam_shot-2.jpg"
    assert session.file_lifetime(first) == LIFETIME_RUN


def test_close_deletes_only_run_lifetime_files_on_success(tmp_path):
    session = RunSession("run_x", files_root=tmp_path)
    temp = session.new_run_file("temp.bin")
    kept = session.new_run_file("kept.bin")
    temp.write_bytes(b"\x00")
    kept.write_bytes(b"\x01")
    ref = session.keep_file(session.run_file_reference(kept))
    assert ref["lifetime"] == LIFETIME_KEPT

    session.close_all(delete_run_files=True)

    assert not temp.exists()
    assert kept.read_bytes() == b"\x01"
    with pytest.raises(RuntimeError):
        session.new_run_file("late.bin")


def test_close_keeps_run_files_by_default(tmp_path):
    session = RunSession("run_x", files_root=tmp_path)
    temp = session.new_run_file("temp.bin")
    temp.write_bytes(b"\x00")
    session.close_all()
    assert temp.exists()


def test_a_run_without_run_files_creates_no_directory(tmp_path):
    session = RunSession("run_x", files_root=tmp_path)
    session.close_all(delete_run_files=True)
    assert not (tmp_path / "run_x").exists()


async def test_http_post_body_from_input_sends_text_or_json(camera):
    base, notifications = camera
    from backend.node_base import NodeContext

    node = NodeFactory().create_node("http_request_node", "n")
    node.config.update({"url": base + "/notify", "method": "POST", "body_source": "input"})
    for value in ("plain text", {"code": "x", "raw": b"\xff"}):
        done: List[Dict[str, Any]] = []
        await node.execute(NodeContext(
            node_id="n", branch_id="b", run_id="r", inputs={"input": value},
            memory_bank=MemoryBank(EventBus()), signal_done=done.append,
            signal_error=done.append, signal_waiting_for_input=lambda p: None,
            wait_for_nodes=lambda t, s: None, wait_for_merge=lambda *a: None,
        ))
        assert done and done[0]["data"]["default"] == "ok"
    assert notifications[0]["body"] == b"plain text"
    assert notifications[0]["content_type"].startswith("text/plain")
    assert json.loads(notifications[1]["body"]) == {"code": "x", "raw": "�"}


async def test_file_mode_outside_a_run_fails_cleanly(camera):
    base, _ = camera
    from backend.node_base import NodeContext

    node = NodeFactory().create_node("http_request_node", "n")
    node.config.update({"url": base + "/capture", "response_mode": "file"})
    errors: List[Exception] = []
    await node.execute(NodeContext(
        node_id="n", branch_id="b", run_id="r", inputs={},
        memory_bank=MemoryBank(EventBus()), signal_done=errors.append,
        signal_error=errors.append, signal_waiting_for_input=lambda p: None,
        wait_for_nodes=lambda t, s: None, wait_for_merge=lambda *a: None,
    ))
    assert isinstance(errors[0], RuntimeError)

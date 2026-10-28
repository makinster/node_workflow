"""Step 2 preparation only: all inference is mocked and Secrets loading fails."""

from contextlib import ExitStack
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from tools.draft_trials import __main__ as cli
from tools.draft_trials import runner
from tools.draft_trials.containment import (
    ContainmentError,
    create_run,
    preparation_record,
    validate_prepared,
)


def prepare(root):
    root.mkdir()
    (root / "library").mkdir()
    (root / "runs").mkdir()
    (root / "prepared.json").write_text(json.dumps(preparation_record(root)))
    return root


def invoke(monkeypatch, root, *flags):
    monkeypatch.setattr(
        sys, "argv", ["draft_trials", "--trial-root", str(root), *flags]
    )
    return cli.main()


@pytest.mark.parametrize("flag", ["--budget", "--time-limit"])
@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "wrong"])
def test_invalid_limits_stop_before_writes(tmp_path, monkeypatch, capsys, flag, value):
    root = tmp_path / "trial"
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, root, f"{flag}={value}")
    assert error.value.code == 2
    assert "positive finite" in capsys.readouterr().err
    assert not root.exists()


def test_real_calls_need_explicit_budget_and_preparation(tmp_path, monkeypatch, capsys):
    root = tmp_path / "trial"
    with pytest.raises(SystemExit):
        invoke(monkeypatch, root, "--real-calls")
    assert "--budget USD is required" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        invoke(monkeypatch, root, "--real-calls", "--budget", "0.50")
    assert "prepared trial root" in capsys.readouterr().err
    assert not root.exists()


@pytest.mark.parametrize("location", ["library/nested", "runs/000001/nested"])
@pytest.mark.parametrize(
    "kind", ["internal", "external", "dangling", "hardlink", "fifo", "socket"]
)
def test_all_shared_and_prior_run_entries_checked_before_imports(
    tmp_path, monkeypatch, capsys, location, kind
):
    import builtins

    root = prepare(tmp_path / "trial")
    nested = root / location
    nested.mkdir(parents=True)
    outside = tmp_path / "sentinel"
    outside.write_text("KEEP")
    entry = nested / "entry"
    sock = None
    if kind == "internal":
        entry.symlink_to(root / "library")
    elif kind == "external":
        entry.symlink_to(outside)
    elif kind == "dangling":
        entry.symlink_to(tmp_path / "absent")
    elif kind == "hardlink":
        os.link(outside, entry)
    elif kind == "fifo":
        os.mkfifo(entry)
    else:
        sock = socket.socket(socket.AF_UNIX)
        sock.bind(str(entry))
    original_import = builtins.__import__

    def no_backend(name, *args, **kwargs):
        if name == "runner" or name.startswith("backend"):
            raise AssertionError("backend import before containment check")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_backend)
    monkeypatch.setenv("AOTN_DATA_DIR", "unchanged")
    try:
        with pytest.raises(SystemExit) as error:
            invoke(monkeypatch, root, "--real-calls", "--budget", "0.50")
        assert error.value.code == 2
        assert "trial root" in capsys.readouterr().err
        assert os.environ["AOTN_DATA_DIR"] == "unchanged"
        assert outside.read_text() == "KEEP"
        assert not (root / "runs/000002").exists()
        with pytest.raises(ContainmentError):
            validate_prepared(root)
    finally:
        if sock is not None:
            sock.close()


@pytest.mark.parametrize(
    "mutation", ["extra", "missing_runs", "runs_file", "library_file", "marker_dir"]
)
def test_exact_top_level_layout(tmp_path, mutation):
    root = prepare(tmp_path / "trial")
    if mutation == "extra":
        (root / "report.json").write_text("{}")
    elif mutation == "marker_dir":
        (root / "prepared.json").unlink()
        (root / "prepared.json").mkdir()
    else:
        name = "library" if mutation == "library_file" else "runs"
        (root / name).rmdir()
        if mutation != "missing_runs":
            (root / name).write_text("wrong type")
    with pytest.raises(ContainmentError, match="prepared root"):
        validate_prepared(root)


def test_root_ancestry_escape_stops_before_creation(tmp_path, monkeypatch, capsys):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(outside)
    with pytest.raises(SystemExit):
        invoke(monkeypatch, link / "trial", "--prepare")
    assert "symlink" in capsys.readouterr().err
    assert not list(outside.iterdir())


def test_run_allocation_never_overwrites_existing_entries(tmp_path):
    root = prepare(tmp_path / "trial")
    first = create_run(root)
    (first / "sentinel").write_text("KEEP")
    (root / "runs/000002").write_text("KEEP FILE")
    assert create_run(root) == root / "runs/000003"
    assert (first / "sentinel").read_text() == "KEEP"
    assert (root / "runs/000002").read_text() == "KEEP FILE"


def test_real_path_reuses_shared_library_without_writes(tmp_path, monkeypatch):
    root = prepare(tmp_path / "trial")
    (root / "library/owner-note.txt").write_text("KEEP")
    before = runner.tree(root / "library")
    seen = []

    async def fake_batch(run_root, *args, **kwargs):
        seen.append((run_root, kwargs))
        assert Path(os.environ["AOTN_DATA_DIR"]) == run_root / "library"
        runner.write_json(
            run_root / "report.json",
            {"result": "pass", **{k: kwargs[k] for k in ("budget_usd", "time_limit")}},
        )
        return {"result": "pass", "case_count": 0}

    monkeypatch.setattr(runner, "batch", fake_batch)
    assert invoke(monkeypatch, root, "--real-calls", "--budget", "0.50") == 0
    first = runner.tree(root / "runs/000001")
    assert (
        invoke(
            monkeypatch, root, "--real-calls", "--budget", "0.75", "--time-limit", "45"
        )
        == 0
    )
    assert seen[0][0] == root / "runs/000001"
    assert seen[1][0] == root / "runs/000002"
    assert all(item[1]["shared_library"] == root / "library" for item in seen)
    assert seen[1][1]["budget_usd"] == 0.75
    assert seen[1][1]["time_limit"] == 45
    assert runner.tree(root / "library") == before
    assert runner.tree(root / "runs/000001") == first
    validate_prepared(root)


@pytest.mark.parametrize("cause", ["cost", "time", "unknown"])
@pytest.mark.asyncio
async def test_guard_stops_before_next_mocked_real_call(tmp_path, monkeypatch, cause):
    budget = runner.TrialBudget(0.50, time_limit=30)
    monkeypatch.setattr(runner, "_budget", budget)
    spec = {
        "format": "aotn-workflow/1",
        "name": "Guard proof",
        "nodes": {
            "start": {"type": "start_node", "config": {"greeting": "test"}},
            "first": {
                "type": "ask_claude_node",
                "config": {"input_source": "Upstream payload"},
            },
            "second": {
                "type": "ask_claude_node",
                "config": {"input_source": "Upstream payload"},
            },
            "end": {"type": "end_node"},
        },
        "connections": [
            {"from": "start.default", "to": "first.input"},
            {"from": "first.default", "to": "second.input"},
            {"from": "second.default", "to": "end.input"},
        ],
    }
    mock = runner.MockSDK(["first", "second"])
    before = budget.before
    checks = []

    def guard():
        if mock.succeeded:
            if cause == "cost":
                budget.cost = budget.limit
            elif cause == "time":
                budget.started -= 31
            else:
                budget.unknown = True
        checks.append(mock.succeeded)
        before()

    monkeypatch.setattr(budget, "before", guard)
    with ExitStack() as stack:
        mock.install(stack)
        await runner.run_workflow(spec, [], tmp_path / "guard.json")
    assert mock.succeeded == len(mock.calls) == 1
    assert len(mock.replies) == 1
    assert checks[-1] == 1


@pytest.mark.asyncio
async def test_budget_stop_report_retains_limits_cost_and_resets_provider(tmp_path):
    previous = runner._budget, runner._shared_library
    # Runs the real branch of the harness through a mocked SDK only. No Secrets I/O.
    mock = runner.MockSDK([runner.meaning()])
    with ExitStack() as stack:
        mock.install(stack)
        report = await runner.batch(
            tmp_path,
            real_calls=True,
            budget_usd=0.000001,
            time_limit=50,
            shared_library=tmp_path / "shared",
        )
    assert mock.succeeded == len(mock.calls) == 1
    assert report["result"] == "fail"
    assert "budget" in report["failure"]
    assert report["budget_usd"] == 0.000001
    assert report["time_limit_seconds"] == 50
    assert report["estimated_cost_usd"] > report["budget_usd"]
    assert json.loads((tmp_path / "report.json").read_text()) == report
    assert (runner._budget, runner._shared_library) == previous


def test_read_only_provider_targets_shared_library_without_loading(
    tmp_path, monkeypatch
):
    from backend.secrets_manager import SecretsManager

    shared = tmp_path / "shared"
    monkeypatch.setattr(runner, "_shared_library", shared)
    with ExitStack() as stack:
        runner.MockSDK([]).install(stack)
        service = runner.create_trial_service()
        try:
            secrets = service.master_state.secrets_manager
            assert isinstance(secrets, SecretsManager)
            assert secrets._storage_dir == shared / "secrets"
            assert not secrets._loaded
            with pytest.raises(RuntimeError, match="read-only"):
                secrets.set_secret("synthetic-name", "synthetic-value")
            with pytest.raises(RuntimeError, match="read-only"):
                secrets.delete_secret("synthetic-name")
        finally:
            service.close()
    assert not shared.exists()


def test_owner_launch_command_selects_library_before_tui_backend_imports(tmp_path):
    library = tmp_path / "library"
    # Execute the documented entry point/argument. Only replace App.run, leaving
    # run_tui and all constructor wiring real, without opening a terminal.
    script = """
import json
import sys
from pathlib import Path
from unittest.mock import patch
import main
original = main.run_tui

def launch():
    from backend import persistence
    from backend.secrets_manager import SecretsManager
    from frontend.app import App
    def opened(app):
        assert persistence.DATA_DIR == Path(sys.argv[2])
        assert app.secrets_manager._storage_dir == Path(sys.argv[2]) / "secrets"
        print(json.dumps({"library": str(persistence.DATA_DIR)}))
    with patch.object(SecretsManager, "_ensure_loaded", side_effect=AssertionError("Secrets forbidden")):
        with patch.object(App, "run", opened):
            original()
main.run_tui = launch
main.main(sys.argv[1:])
"""
    proc = subprocess.run(
        [sys.executable, "-c", script, "--data-dir", str(library)],
        cwd=runner.APP,
        env={**os.environ, "AOTN_DATA_DIR": str(tmp_path / "wrong")},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["library"] == str(library)
    assert not (tmp_path / "wrong").exists()


@pytest.mark.slow
def test_repeated_real_path_with_mock_sdk_keeps_all_artifacts_in_each_run(tmp_path):
    root = prepare(tmp_path / "trial")
    (root / "library/owner-note.txt").write_text("KEEP SHARED LIBRARY")
    shared_before = runner.tree(root / "library")
    first_before = None
    script = """
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys

root = Path(sys.argv[1])
run_root = root / "runs" / sys.argv[2]
# The CLI assigns this path before backend imports in production as well.
os.environ["AOTN_DATA_DIR"] = str(run_root / "library")
from tools.draft_trials import __main__ as cli
from tools.draft_trials import runner
from tools.draft_trials.cases import calibration_pairs, case_record, good_draft
original = runner.batch

async def mocked_transport(*args, **kwargs):
    replies = []
    for pair in calibration_pairs():
        replies.extend([runner.meaning("pass"), runner.meaning("fail")])
    case = case_record(1, run_root / "cases/1/fixtures")
    replies.extend([runner.requirements(case), good_draft(1, case["root"]), runner.meaning()])
    mock = runner.MockSDK(replies)
    with ExitStack() as stack:
        mock.install(stack)
        report = await original(*args, **kwargs)
    assert not mock.replies
    assert len(mock.calls) == 47
    return report

runner.batch = mocked_transport
sys.argv = ["draft_trials", "--trial-root", str(root), "--real-calls", "--budget", "0.50", "--cases", "1"]
raise SystemExit(cli.main())
"""
    for number in ("000001", "000002"):
        proc = subprocess.run(
            [sys.executable, "-c", script, str(root), number],
            cwd=runner.APP,
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        run_root = root / "runs" / number
        report_path = Path(json.loads(proc.stdout)["report"])
        assert report_path == run_root / "report.json"
        report = json.loads(report_path.read_text())
        assert report["mode"] == "real" and report["result"] == "pass"
        assert report["budget_usd"] == 0.50
        assert report["time_limit_seconds"] == 600
        assert report["estimated_cost_usd"] > 0
        assert list((run_root / "library/workflows").glob("*.json"))
        assert list((run_root / "library/run_history").glob("*.json"))
        # Check every emitted absolute path, including nested build and run
        # receipts, without opening any library Secrets file.
        for artifact in run_root.rglob("*.json"):

            def check_paths(value):
                if isinstance(value, str) and value.startswith(str(root)):
                    assert Path(value).is_relative_to(run_root), (artifact, value)
                elif isinstance(value, dict):
                    for item in value.values():
                        check_paths(item)
                elif isinstance(value, list):
                    for item in value:
                        check_paths(item)

            check_paths(json.loads(artifact.read_text()))
        assert runner.tree(root / "library") == shared_before
        if first_before is None:
            first_before = runner.tree(run_root)
        else:
            assert runner.tree(root / "runs/000001") == first_before
        validate_prepared(root)

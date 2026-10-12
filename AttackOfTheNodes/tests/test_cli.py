"""`aotn run` end to end (distributed build plan step 2).

The CLI runs in a subprocess against a temporary data directory, so the
owner's workflows, settings and run records are never touched.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_run_service import write_workflow


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Runs the real entry point and reports whether any Textual module was imported.
RUNNER = (
    "import sys, main\n"
    "code = main.main(sys.argv[1:])\n"
    "textual = sorted(m for m in sys.modules if m == 'textual' or m.startswith('textual.'))\n"
    "print('TEXTUAL:' + ','.join(textual[:3]) if textual else 'NO_TEXTUAL', file=sys.stderr)\n"
    "sys.exit(code)\n"
)


def aotn(*args: str, data_dir: Path, stdin: str = "") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("AOTN_DATA_DIR", None)
    return subprocess.run(
        [sys.executable, "-c", RUNNER, "run", *args, "--data-dir", str(data_dir)],
        cwd=PROJECT_ROOT,
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_run_succeeds_end_to_end_without_importing_textual(tmp_path):
    wf = write_workflow(tmp_path / "ok.json")
    result = aotn(str(wf), data_dir=tmp_path / "data")
    assert result.returncode == 0, result.stderr
    assert "Got: hello" in result.stdout
    assert "NO_TEXTUAL" in result.stderr
    assert "finished (0 error(s)" in result.stderr
    # Run records land in the data directory, not the project folder.
    assert list((tmp_path / "data" / "run_history").glob("*.json"))


def test_failed_run_prints_the_error_and_exits_non_zero(tmp_path):
    wf = write_workflow(tmp_path / "bad.json", fail=True)
    result = aotn(str(wf), data_dir=tmp_path / "data")
    assert result.returncode == 2
    assert "Got: hello" in result.stdout
    assert "error: Boom (" in result.stderr
    assert "Deliberate error from ErrorNode" in result.stderr
    assert "NO_TEXTUAL" in result.stderr
    errors = list((tmp_path / "data" / "run_errors").glob("*.json"))
    assert errors


def test_terminate_branch_policy_finishes_with_errors(tmp_path):
    wf = write_workflow(tmp_path / "bad.json", fail=True)
    result = aotn(str(wf), "--policy", "terminate_branch", data_dir=tmp_path / "data")
    assert result.returncode == 1
    assert "Got: hello" in result.stdout


def test_input_request_fails_when_not_interactive(tmp_path):
    wf = write_workflow(tmp_path / "ask.json", ask=True)
    result = aotn(str(wf), data_dir=tmp_path / "data")
    assert result.returncode == 2
    assert "unattended" in result.stderr


def test_unknown_workflow_exits_4(tmp_path):
    result = aotn("no-such-workflow", data_dir=tmp_path / "data")
    assert result.returncode == 4
    assert "No workflow matches" in result.stderr


def test_invalid_workflow_exits_3_without_running(tmp_path):
    wf = write_workflow(tmp_path / "nostart.json", start=False)
    result = aotn(str(wf), data_dir=tmp_path / "data")
    assert result.returncode == 3
    assert "failed validation" in result.stderr
    assert not (tmp_path / "data" / "run_history").exists() or not list(
        (tmp_path / "data" / "run_history").glob("*.json"))


def test_unloadable_file_exits_cleanly(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]")
    result = aotn(str(path), data_dir=tmp_path / "data")
    assert result.returncode == 4
    assert "Traceback" not in result.stderr


def test_unstartable_workflow_without_validation_exits_cleanly(tmp_path):
    wf = write_workflow(tmp_path / "nostart.json", start=False)
    result = aotn(str(wf), "--no-validate", data_dir=tmp_path / "data")
    assert result.returncode == 3
    assert "could not be started" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.skipif(not hasattr(os, "openpty"), reason="needs a pseudo-terminal")
def test_ctrl_c_at_an_interactive_prompt_exits(tmp_path):
    import signal
    import time

    wf = write_workflow(tmp_path / "ask.json", ask=True)
    controller, terminal = os.openpty()
    env = dict(os.environ)
    env.pop("AOTN_DATA_DIR", None)
    process = subprocess.Popen(
        [sys.executable, "-c", RUNNER, "run", str(wf), "--data-dir", str(tmp_path / "data")],
        cwd=PROJECT_ROOT, env=env, stdin=terminal, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    try:
        time.sleep(2.0)  # let it start and block on the input prompt
        process.send_signal(signal.SIGINT)
        _, stderr = process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
        os.close(controller)
        os.close(terminal)
    assert process.returncode == 130, stderr
    assert "stopped" in stderr


def test_data_dir_after_the_backend_is_loaded_is_refused(tmp_path):
    import aotn_cli

    with pytest.raises(SystemExit) as excinfo:
        aotn_cli.main(["whatever", "--data-dir", str(tmp_path / "elsewhere")])
    assert excinfo.value.code == 2


def test_parallel_prompts_are_answered_one_at_a_time():
    import aotn_cli
    from backend.run_policies import RecoveryRequest

    prompts = io.StringIO()
    policy, _ = aotn_cli._stdin_policies(io.StringIO("w\nb\n"), prompts)

    async def both():
        make = lambda branch: RecoveryRequest(run_id="r", branch_id=branch,
                                              node_id="n", error={})
        return await asyncio.gather(policy.decide(make("a")), policy.decide(make("b")))

    assert asyncio.run(both()) == ["TERMINATE_WORKFLOW", "TERMINATE_BRANCH"]
    assert prompts.getvalue().count("Recover how?") == 2


def test_saved_workflow_by_name_and_json_result(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "workflows").mkdir(parents=True)
    wf = json.loads(write_workflow(tmp_path / "wf.json", name="Nightly").read_text())
    (data_dir / "workflows" / f"{wf['id']}.json").write_text(json.dumps(wf))
    result = aotn("Nightly", "--json", data_dir=data_dir)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["final_state"] == "FINISHED"
    assert payload["workflow_id"] == wf["id"]
    assert payload["exit_code"] == 0


def test_bad_input_flag_is_a_usage_error(tmp_path):
    wf = write_workflow(tmp_path / "ok.json")
    result = aotn(str(wf), "--input", "novalue", data_dir=tmp_path / "data")
    assert result.returncode == 2
    assert "KEY=VALUE" in result.stderr


def test_plain_aotn_still_launches_the_tui(monkeypatch):
    import main

    launched = []
    monkeypatch.setattr(main, "run_tui", lambda: launched.append(True))
    assert main.main([]) is None
    assert launched == [True]


def test_stdin_policies_answer_on_the_terminal():
    import aotn_cli as cli
    from backend.run_policies import InputRequest, RecoveryRequest, UnattendedInputError

    prompts = io.StringIO()
    policy, provider = cli._stdin_policies(io.StringIO("x\nw\nmy answer\n"), prompts)
    request = RecoveryRequest(run_id="r", branch_id="b", node_id="n", error={"message": "m"})
    assert asyncio.run(policy.decide(request)) == "TERMINATE_WORKFLOW"
    assert policy.pause_at_breakpoints is False
    answer = asyncio.run(provider.provide(
        InputRequest(run_id="r", branch_id="b", node_id="n", prompt="Name?")))
    assert answer == "my answer"
    assert "Recover how?" in prompts.getvalue()
    assert "Name?" in prompts.getvalue()

    _, closed = cli._stdin_policies(io.StringIO(""), io.StringIO())
    with pytest.raises(UnattendedInputError):
        asyncio.run(closed.provide(
            InputRequest(run_id="r", branch_id="b", node_id="n", prompt="?")))

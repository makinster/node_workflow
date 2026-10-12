"""Run service, run policies and data directory (distributed build plan step 2)."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from backend import persistence
from backend.event_bus import EventBus
from backend.events import NODE_EXECUTION_UPDATE
from backend.node_factory import NodeFactory
from backend.run_policies import (
    InputProvider,
    InputRequest,
    NoInputProvider,
    RecoveryPolicy,
    RecoveryRequest,
    TerminatePolicy,
    UnattendedInputError,
)
from backend.events import ERROR_LOGGED
from backend.run_service import (
    EXIT_FINISHED_WITH_ERRORS,
    RunResult,
    EXIT_INTERRUPTED,
    EXIT_OK,
    EXIT_RUN_FAILED,
    RunService,
    WorkflowLoadError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from backend.workflow_map import WorkflowMap


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_TIMEOUT = 5.0


@pytest.fixture(autouse=True)
def _run_records_in_tmp(tmp_path, monkeypatch):
    """Keep run history, errors and outputs out of the project folder."""
    from backend import error_handler, output_manager, run_history

    monkeypatch.setattr(error_handler, "RUN_ERRORS_DIR", tmp_path / "run_errors")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history")
    monkeypatch.setattr(output_manager, "RUN_OUTPUTS_DIR", tmp_path / "run_outputs")


def workflow_data(name: str = "Service Smoke", *, fail: bool = False, ask: bool = False,
                  start: bool = True) -> Dict[str, Any]:
    wm = WorkflowMap(NodeFactory(), EventBus())
    wm.create_new(name)
    previous = None
    if start:
        previous = wm.add_node("start_node", alias="Start")
        wm.update_node_config(previous, {"greeting": "hello"})
    say = wm.add_node("text_output_node", alias="Say")
    wm.update_node_config(say, {"template": "Got: {input}", "request_user_input": False})
    if previous:
        wm.connect(previous, "default", say, "input")
    previous = say
    if ask:
        question = wm.add_node("user_text_input_node", alias="Ask")
        wm.connect(previous, "default", question, "input")
        previous = question
    if fail:
        boom = wm.add_node("error_node", alias="Boom")
        wm.connect(previous, "default", boom, "input")
        previous = boom
    end = wm.add_node("end_node", alias="End")
    wm.connect(previous, "default", end, "input")
    return wm.get_workflow_data_for_save()


def write_workflow(path: Path, **kwargs) -> Path:
    path.write_text(json.dumps(workflow_data(**kwargs)), encoding="utf-8")
    return path


async def run_file(path: Path, **start_kwargs):
    service = RunService.create()
    service.load(str(path))
    await service.start(**start_kwargs)
    return service, await asyncio.wait_for(service.wait(), RUN_TIMEOUT)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_load_by_file_id_and_name(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    data = workflow_data("Nightly Capture")
    persistence.save_workflow(data["id"], data)
    service = RunService.create()

    assert service.load(data["id"])["name"] == "Nightly Capture"
    assert service.load("nightly capture")["id"] == data["id"]
    file_ref = write_workflow(tmp_path / "wf.json", name="From File")
    assert service.load(str(file_ref))["name"] == "From File"


def test_unknown_and_ambiguous_references_are_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    for _ in range(2):
        data = workflow_data("Twin")
        persistence.save_workflow(data["id"], data)
    service = RunService.create()
    with pytest.raises(WorkflowNotFoundError, match="No workflow matches"):
        service.load("missing")
    with pytest.raises(WorkflowNotFoundError, match="More than one"):
        service.load("Twin")


def test_load_does_not_change_the_last_active_workflow(tmp_path):
    service = RunService.create()
    before = service.configuration.get("last_active_workflow_id")
    service.load(str(write_workflow(tmp_path / "wf.json")))
    assert service.configuration.get("last_active_workflow_id") == before


# ---------------------------------------------------------------------------
# Start, validate, result
# ---------------------------------------------------------------------------


async def test_start_validates_and_refuses_an_invalid_workflow(tmp_path):
    service = RunService.create()
    service.load(str(write_workflow(tmp_path / "wf.json", start=False)))
    with pytest.raises(WorkflowValidationError) as excinfo:
        await service.start()
    assert any("start node" in e["message"] for e in excinfo.value.result["errors"])
    assert service.current_run_id is None


async def test_successful_run_result(tmp_path):
    service, result = await run_file(write_workflow(tmp_path / "wf.json"))
    assert result.final_state == "FINISHED"
    assert result.errors == []
    assert result.exit_code == EXIT_OK
    assert result.run_id == service.current_run_id
    assert json.loads(json.dumps(result.to_dict()))["exit_code"] == EXIT_OK


@pytest.mark.parametrize("mode,state,code", [
    ("terminate_branch", "FINISHED", EXIT_FINISHED_WITH_ERRORS),
    ("terminate_workflow", "ERROR", EXIT_RUN_FAILED),
])
async def test_terminate_policy_result(tmp_path, mode, state, code):
    _, result = await run_file(
        write_workflow(tmp_path / "wf.json", fail=True),
        recovery_policy=TerminatePolicy(mode),
        input_provider=NoInputProvider(),
    )
    assert result.final_state == state
    assert [e["message"] for e in result.errors] == ["Deliberate error from ErrorNode"]
    assert result.exit_code == code


async def test_custom_recovery_policy_is_asked_for_every_error(tmp_path):
    class Scripted(RecoveryPolicy):
        def __init__(self) -> None:
            self.requests: List[RecoveryRequest] = []
            self.answers = iter(["RETRY", "TERMINATE_BRANCH"])

        async def decide(self, request: RecoveryRequest) -> str:
            self.requests.append(request)
            return next(self.answers)

    policy = Scripted()
    _, result = await run_file(write_workflow(tmp_path / "wf.json", fail=True),
                               recovery_policy=policy)
    assert len(policy.requests) == 2
    assert policy.requests[0].message == "Deliberate error from ErrorNode"
    assert policy.requests[0].run_id == result.run_id
    assert len(result.errors) == 2


async def test_invalid_policy_answer_terminates_the_branch(tmp_path):
    class Confused(RecoveryPolicy):
        async def decide(self, request: RecoveryRequest) -> str:
            return "DANCE"

    _, result = await run_file(write_workflow(tmp_path / "wf.json", fail=True),
                               recovery_policy=Confused())
    assert result.final_state == "FINISHED"


async def test_input_provider_answers_user_input(tmp_path):
    class Answers(InputProvider):
        def __init__(self) -> None:
            self.prompts: List[str] = []

        async def provide(self, request: InputRequest) -> str:
            self.prompts.append(request.prompt)
            return "typed answer"

    provider = Answers()
    service, result = await run_file(write_workflow(tmp_path / "wf.json", ask=True),
                                     input_provider=provider)
    assert len(provider.prompts) == 1
    assert result.final_state == "FINISHED"
    assert result.errors == []


async def test_input_provider_failure_fails_the_node_and_follows_the_policy(tmp_path):
    _, result = await run_file(
        write_workflow(tmp_path / "wf.json", ask=True),
        recovery_policy=TerminatePolicy("terminate_workflow"),
        input_provider=NoInputProvider(),
    )
    assert result.final_state == "ERROR"
    assert "unattended" in result.errors[0]["message"]


async def test_subscribe_and_unsubscribe(tmp_path):
    service = RunService.create()
    service.load(str(write_workflow(tmp_path / "wf.json")))
    seen: List[Dict[str, Any]] = []
    unsubscribe = service.subscribe(NODE_EXECUTION_UPDATE, seen.append)
    await service.start()
    await asyncio.wait_for(service.wait(), RUN_TIMEOUT)
    count = len(seen)
    assert count > 0
    unsubscribe()
    await service.start()
    await asyncio.wait_for(service.wait(), RUN_TIMEOUT)
    assert len(seen) == count


async def test_inputs_are_recorded_on_the_run(tmp_path):
    service = RunService.create()
    service.load(str(write_workflow(tmp_path / "wf.json")))
    await service.start(inputs={"camera": "front"})
    assert service.master_state.run_context.inputs == {"camera": "front"}
    await asyncio.wait_for(service.wait(), RUN_TIMEOUT)


async def test_stop_through_the_service(tmp_path):
    class Never(InputProvider):
        async def provide(self, request: InputRequest) -> str:
            await asyncio.Event().wait()
            return ""

    service = RunService.create()
    service.load(str(write_workflow(tmp_path / "wf.json", ask=True)))
    await service.start(input_provider=Never())
    await asyncio.sleep(0.05)
    service.stop()
    result = await asyncio.wait_for(service.wait(), RUN_TIMEOUT)
    # The engine still records FINISHED (no STOPPED state yet); the service
    # reports what actually happened.
    assert result.final_state == "STOPPED"
    assert result.exit_code == EXIT_INTERRUPTED


async def test_a_failed_run_keeps_the_outputs_it_produced(tmp_path):
    _, result = await run_file(
        write_workflow(tmp_path / "wf.json", fail=True),
        recovery_policy=TerminatePolicy("terminate_workflow"),
    )
    assert result.final_state == "ERROR"
    assert result.outputs, "outputs produced before the failure must survive"


async def test_a_provider_cancelling_its_own_future_fails_the_node(tmp_path):
    class Cancelled(InputProvider):
        async def provide(self, request: InputRequest) -> str:
            future = asyncio.get_running_loop().create_future()
            future.cancel()
            return await future

    _, result = await run_file(
        write_workflow(tmp_path / "wf.json", ask=True),
        recovery_policy=TerminatePolicy("terminate_workflow"),
        input_provider=Cancelled(),
    )
    assert result.final_state == "ERROR"
    assert "cancelled" in result.errors[0]["message"]


async def test_a_broken_recovery_policy_is_logged_and_ends_the_branch(tmp_path):
    class Broken(RecoveryPolicy):
        async def decide(self, request: RecoveryRequest) -> str:
            raise ValueError("policy blew up")

    _, result = await run_file(write_workflow(tmp_path / "wf.json", fail=True),
                               recovery_policy=Broken())
    messages = [e["message"] for e in result.errors]
    assert "policy blew up" in messages
    assert result.final_state == "FINISHED"


@pytest.mark.parametrize("content", ["[1, 2]", "{}", '{"id": "x", "nodes": 5}'])
def test_unloadable_workflow_files_raise_a_load_error(tmp_path, content):
    path = tmp_path / "broken.json"
    path.write_text(content)
    with pytest.raises(WorkflowLoadError):
        RunService.create().load(str(path))


async def test_only_the_current_runs_errors_are_kept(tmp_path):
    service = RunService.create()
    service.load(str(write_workflow(tmp_path / "wf.json", fail=True)))
    for _ in range(3):
        await service.start(recovery_policy=TerminatePolicy("terminate_branch"))
        await asyncio.wait_for(service.wait(), RUN_TIMEOUT)
    assert list(service._errors_by_run) == [service.current_run_id]


def test_unattended_shorthand_is_the_first_recovery_policy():
    policy = TerminatePolicy("terminate_branch")
    request = RecoveryRequest(run_id="r", branch_id="b", node_id="n", error={})
    assert asyncio.run(policy.decide(request)) == "TERMINATE_BRANCH"
    assert policy.pause_at_breakpoints is False
    with pytest.raises(UnattendedInputError):
        asyncio.run(NoInputProvider().provide(
            InputRequest(run_id="r", branch_id="b", node_id="n", prompt="?")))
    with pytest.raises(ValueError):
        TerminatePolicy("shrug")


# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------


def _paths_with_env(env_value):
    env = dict(os.environ)
    env.pop("AOTN_DATA_DIR", None)
    if env_value is not None:
        env["AOTN_DATA_DIR"] = env_value
    code = (
        "import json; from backend import persistence as p; "
        "from backend.secrets_manager import SecretsManager; "
        "print(json.dumps({'data': str(p.DATA_DIR), 'workflows': str(p.WORKFLOWS_DIR), "
        "'secrets': str(SecretsManager()._storage_dir), 'logs': str(p.LOGS_DIR)}))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, env=env,
                         capture_output=True, text=True, check=True, timeout=60)
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_data_directory_defaults_to_the_project_folder():
    paths = _paths_with_env(None)
    assert Path(paths["data"]) == PROJECT_ROOT
    assert Path(paths["workflows"]) == PROJECT_ROOT / "workflows"
    assert Path(paths["secrets"]) == PROJECT_ROOT / "secrets"


def test_data_directory_follows_the_environment_variable(tmp_path):
    paths = _paths_with_env(str(tmp_path / "aotn-data"))
    root = (tmp_path / "aotn-data").resolve()
    assert Path(paths["data"]) == root
    assert Path(paths["workflows"]) == root / "workflows"
    assert Path(paths["secrets"]) == root / "secrets"
    assert Path(paths["logs"]) == root / "logs"


# ---------------------------------------------------------------------------
# Handled errors: routed along an error path, they do not fail the run
# ---------------------------------------------------------------------------


def _result(state, *handled_flags):
    errors = [{"code": "node_error", "handled": flag} for flag in handled_flags]
    return RunResult("run_x", "wf", "Workflow", state, errors=errors)


@pytest.mark.parametrize("state,flags,code", [
    ("FINISHED", (), EXIT_OK),
    ("FINISHED", (True,), EXIT_OK),
    ("FINISHED", (True, True), EXIT_OK),
    ("FINISHED", (True, False), EXIT_FINISHED_WITH_ERRORS),
    ("FINISHED", (False,), EXIT_FINISHED_WITH_ERRORS),
    ("ERROR", (True,), EXIT_RUN_FAILED),
    ("STOPPED", (True,), EXIT_INTERRUPTED),
])
def test_exit_code_counts_only_unhandled_errors(state, flags, code):
    result = _result(state, *flags)
    assert result.exit_code == code
    assert result.to_dict()["unhandled_error_count"] == flags.count(False)


def test_records_without_a_handled_flag_count_as_unhandled():
    result = RunResult("run_x", "wf", "Workflow", "FINISHED",
                       errors=[{"code": "node_error"}])
    assert result.exit_code == EXIT_FINISHED_WITH_ERRORS

"""Step 4b: child runs (a workflow calling a subworkflow and waiting).

Design: docs/SUBWORKFLOWS_PROPOSAL.md C11–C20, C22 and the acceptance
scenarios in §6 that the backend can show without the TUI.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_subworkflow_calls.py -v
"""

import asyncio
import gc
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend import persistence
from backend.event_bus import EventBus
from backend.events import USER_INPUT_NEEDED
from backend.node_factory import NodeFactory
from backend.run_policies import unattended_policies
from backend.run_service import RunService
from backend.save_manager import SaveManager
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    from backend import configuration_manager, run_history

    for name in ("WORKFLOWS_DIR", "RUN_HISTORY_DIR", "RUN_ERRORS_DIR", "RUN_OUTPUTS_DIR",
                 "RUN_FILES_DIR", "SETTINGS_DIR"):
        monkeypatch.setattr(persistence, name, tmp_path / name.lower())
    # These modules bind their folders at import; settings set here must not
    # reach the real settings file.
    monkeypatch.setattr(configuration_manager, "SETTINGS_DIR", tmp_path / "settings_dir")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history_dir")
    yield


# -- building workflows --------------------------------------------------------------

def row(name, kind="string", value=None, required=False, to="Vault"):
    return {"id": name, "name": name, "type": kind, "value": value, "required": required, "to": to}


def res(name, kind="string", source="Vault key", vault_key=""):
    return {"id": name, "name": name, "type": kind, "source": source, "vault_key": vault_key or name}


class Flow:
    """A small workflow builder: nodes by handle, saved on ``save()``."""

    def __init__(self, name, callable_=False):
        self.map = WorkflowMap(FACTORY, EventBus())
        self.map.create_new(name)
        self.map.set_callable(callable_)
        self.ids = {}

    def node(self, handle, node_type, alias=None, **config):
        node_id = self.map.add_node(node_type, alias=alias or handle)
        if config:
            data = self.map.get_node_data(node_id)
            self.map.update_node_config(node_id, {**data["config"], **config})
        self.ids[handle] = node_id
        return self

    def link(self, *handles, port="default", target_port="input"):
        for source, target in zip(handles, handles[1:]):
            self.map.connect(self.ids[source], port, self.ids[target], target_port)
        return self

    def save(self):
        SaveManager(self.map).save_current_workflow()
        return self.map.workflow_id


def greeter(required=True, extra_rows=(), results=None, name="Greeter"):
    """Callable child: Start(who → Vault) → Return End(greeted ← Vault who)."""
    return (Flow(name, callable_=True)
            .node("start", "start_node", rows=[row("who", required=required), *extra_rows])
            .node("end", "end_node", return_end=True,
                  results=results if results is not None else [res("greeted", vault_key="who")])
            .link("start", "end").save())


def caller(child_id, inputs, results=None, name="Parent", alias="Call", child_result="greeted"):
    """Callable parent: Start → Subworkflow → Return End reading Vault keys."""
    return (Flow(name, callable_=True)
            .node("start", "start_node")
            .node("call", "subworkflow_node", alias=alias, workflow_id=child_id, inputs=inputs,
                  results=[{"name": child_result, "to": "Vault", "vault_key": "got"}])
            .node("end", "end_node", return_end=True, results=results or [res("got")])
            .link("start", "call", "end").save())


def configured(name, value):
    return {"id": name, "name": name, "source": "Configured", "value": value}


def run(workflow_id, inputs=None, attended=False, during=None, settings=None, timeout=20):
    """Run a saved workflow; ``during(service)`` runs while it is going."""
    service = RunService.create()
    for key, value in (settings or {}).items():
        service.configuration.set(key, value)
    service.load(workflow_id)

    async def go():
        if attended:
            await service.start(inputs=inputs or {}, validate=False)
        else:
            policy, provider = unattended_policies("terminate_branch")
            await service.start(inputs=inputs or {}, recovery_policy=policy,
                                input_provider=provider, validate=False)
        if during is not None:
            await during(service)
        return await asyncio.wait_for(service.wait(), timeout=timeout)

    try:
        return asyncio.run(go()), service
    finally:
        service.close()


def codes(result):
    return [error.get("code") for error in result.errors]


# -- calls and results -----------------------------------------------------------------

def test_a_call_returns_the_childs_results():
    child = greeter()
    parent = caller(child, [configured("who", "Kim")])
    result, _ = run(parent)
    assert result.final_state == "FINISHED", result.errors
    assert result.values == {"got": "Kim"}


def test_results_go_downstream_one_as_itself():
    child = greeter()
    parent = (Flow("Parent")
              .node("start", "start_node")
              .node("call", "subworkflow_node", workflow_id=child, inputs=[configured("who", "Ada")])
              .node("set", "set_variable_node", variable_name="seen")
              .node("end", "end_node")
              .link("start", "call", "set", "end").save())
    result, service = run(parent)
    assert result.final_state == "FINISHED", result.errors
    assert service.master_state._memory_bank.read_persistent("seen") == "Ada"


def test_configured_text_is_typed_by_the_childs_row():
    child = greeter(extra_rows=[row("times", "number", required=True)],
                    results=[res("greeted", vault_key="who"), res("times", "number")])
    parent = (Flow("Parent", callable_=True)
              .node("start", "start_node")
              .node("call", "subworkflow_node", workflow_id=child,
                    inputs=[configured("who", "Kim"), configured("times", "3")],
                    results=[{"name": "times", "to": "Vault", "vault_key": "n"}])
              .node("end", "end_node", return_end=True, results=[res("n", "number")])
              .link("start", "call", "end").save())
    result, _ = run(parent)
    assert result.values == {"n": 3}


@pytest.mark.parametrize("inputs, code", [
    ([], "child_input_missing"),
    ([configured("who", "Kim"), configured("nope", "x")], "child_input_invalid"),
])
def test_bad_inputs_fail_the_call_with_a_code(inputs, code):
    parent = caller(greeter(), inputs)
    result, _ = run(parent)
    assert code in codes(result)


def test_a_wrongly_typed_configured_value_is_child_input_invalid():
    child = greeter(extra_rows=[row("times", "number")])
    parent = caller(child, [configured("who", "Kim"), configured("times", "lots")])
    result, _ = run(parent)
    assert "child_input_invalid" in codes(result)


def test_missing_and_standard_children_are_not_found():
    standard = Flow("Plain").node("start", "start_node").save()
    for child in ("wf_missing", standard):
        result, _ = run(caller(child, []))
        assert "child_not_found" in codes(result)


def test_a_failed_child_is_routable_on_the_error_path():
    child = (Flow("Breaks", callable_=True)
             .node("start", "start_node")
             .node("boom", "error_node")
             .node("end", "end_node", return_end=True, results=[])
             .link("start", "boom", "end").save())
    parent = (Flow("Parent")
              .node("start", "start_node")
              .node("call", "subworkflow_node", workflow_id=child)
              .node("ok", "end_node")
              .node("caught", "set_variable_node", variable_name="caught")
              .node("caught_end", "end_node")
              .link("start", "call", "ok")
              .link("call", "caught", port="error")
              .link("caught", "caught_end").save())
    result, service = run(parent)
    assert result.final_state == "FINISHED"
    assert result.unhandled_errors == []
    assert [e["code"] for e in result.errors] == ["child_failed"]
    assert service.master_state._memory_bank.read_persistent("caught") is not None


def test_a_result_sent_back_twice_is_child_output_conflict():
    child = (Flow("Twice", callable_=True)
             .node("start", "start_node", rows=[row("who", required=True)])
             .node("fan", "branch_node", branch_count=2)
             .node("end", "end_node", return_end=True, results=[res("greeted", vault_key="who")])
             .link("start", "fan").save())
    flow = Flow("Twice", callable_=True)
    flow.map.load_data(__import__("backend.persistence", fromlist=["x"]).load_workflow(child))
    ids = {n["alias"]: nid for nid, n in flow.map.get_all_node_data().items()}
    flow.map.connect(ids["fan"], "path_a", ids["end"], "input")
    flow.map.connect(ids["fan"], "path_b", ids["end"], "input")
    SaveManager(flow.map).save_current_workflow()
    result, _ = run(caller(child, [configured("who", "Kim")]))
    assert "child_output_conflict" in codes(result)


# -- concurrency and limits -------------------------------------------------------------

def _two_branch_parent(child, first, second):
    return (Flow("Two calls")
            .node("start", "start_node")
            .node("fan", "branch_node", branch_count=2)
            .node("a", "subworkflow_node", workflow_id=child, inputs=[configured("who", first)],
                  results=[{"name": "greeted", "to": "Vault", "vault_key": "a"}])
            .node("b", "subworkflow_node", workflow_id=child, inputs=[configured("who", second)],
                  results=[{"name": "greeted", "to": "Vault", "vault_key": "b"}])
            .node("end_a", "end_node").node("end_b", "end_node")
            .link("start", "fan")
            .link("fan", "a", port="path_a").link("a", "end_a")
            .link("fan", "b", port="path_b").link("b", "end_b").save())


def slow_greeter(seconds=0.3):
    return (Flow("Slow", callable_=True)
            .node("start", "start_node", rows=[row("who", required=True)])
            .node("nap", "sleep_node", duration=seconds)
            .node("end", "end_node", return_end=True, results=[res("greeted", vault_key="who")])
            .link("start", "nap", "end").save())


def test_two_branches_call_one_child_at_once_with_their_own_results():
    parent = _two_branch_parent(slow_greeter(), "Ada", "Bo")
    seen = {}

    async def watch(service):
        for _ in range(100):
            await asyncio.sleep(0.02)
            tree = service.master_state.call_tree
            if tree is not None:
                seen["peak"] = max(seen.get("peak", 0), tree.live)

    result, service = run(parent, during=watch)
    memory = service.master_state._memory_bank
    assert result.final_state == "FINISHED", result.errors
    assert (memory.read_persistent("a"), memory.read_persistent("b")) == ("Ada", "Bo")
    assert seen["peak"] == 2  # at the same time, not one after the other


def test_a_call_past_the_live_limit_fails_at_once():
    parent = _two_branch_parent(slow_greeter(), "Ada", "Bo")
    result, _ = run(parent, settings={"max_live_subworkflow_runs": 1})
    assert codes(result).count("capacity_limit") == 1


def test_a_call_past_the_depth_limit_fails_at_once():
    # Level 2 → Level 1 → Level 0 → Greeter: three calls below the root.
    child = caller(greeter(), [configured("who", "Kim")], name="Level 0")
    for level in (1, 2):
        child = caller(child, [], name=f"Level {level}", child_result="got")
    result, _ = run(child, settings={"max_subworkflow_depth": 2})
    # The third call fails at once; each level above reports its child failed.
    assert "limited to 2 levels" in str(result.errors) and codes(result) == ["child_failed", "result_missing"]
    result, _ = run(child, settings={"max_subworkflow_depth": 3})
    assert result.final_state == "FINISHED" and result.values == {"got": "Kim"}


def test_repeated_calls_release_their_stacks(monkeypatch):
    from backend.master_state import MasterState

    import weakref
    created = []
    original_init = MasterState.__init__
    def track(instance, *args, **kwargs):
        original_init(instance, *args, **kwargs)
        created.append(weakref.ref(instance))
    monkeypatch.setattr(MasterState, '__init__', track)
    child = greeter()
    parent = (Flow("Loop")
              .node("start", "start_node")
              .node("one", "subworkflow_node", workflow_id=child, inputs=[configured("who", "x")]))
    previous = "one"
    for index in range(2, 21):
        parent.node(f"c{index}", "subworkflow_node", workflow_id=child, inputs=[configured("who", "x")])
        parent.link(previous, f"c{index}")
        previous = f"c{index}"
    parent.node("end", "end_node").link("start", "one").link(previous, "end")
    parent_id = parent.save()
    result, service = run(parent_id)
    assert result.final_state == "FINISHED", result.errors
    assert service.master_state.call_tree.live == 0
    gc.collect()
    assert len(created) == 21  # the parent plus all twenty real child runs
    assert sum(ref() is service.master_state for ref in created) == 1
    assert all(ref() is None or ref() is service.master_state for ref in created)


# -- files (C13) --------------------------------------------------------------------------

def _file_child():
    """Returns the HTTP response saved as a run-owned file."""
    return (Flow("Download", callable_=True)
            .node("start", "start_node")
            .node("http", "http_request_node", url="http://example.invalid/x", response_mode="file")
            .node("end", "end_node", return_end=True,
                  results=[res("body", "file", source="Incoming payload")])
            .link("start", "http", "end").save())


def _fake_response():
    response = MagicMock()
    response.read.side_effect = [b"payload", b""]
    response.headers.get.return_value = "text/plain"
    response.__enter__ = lambda s: s
    response.__exit__ = MagicMock(return_value=False)
    return response


def test_a_returned_file_is_handed_to_the_parent():
    from backend.file_refs import reference_path

    child = _file_child()
    seen = {}
    parent = (Flow("Parent")
              .node("start", "start_node")
              .node("call", "subworkflow_node", workflow_id=child,
                    results=[{"name": "body", "to": "Vault", "vault_key": "body"}])
              .node("nap", "sleep_node", duration=0.3)
              .node("end", "end_node")
              .link("start", "call", "nap", "end").save())

    async def during(service):
        for _ in range(200):
            await asyncio.sleep(0.01)
            value = service.master_state._memory_bank.read_persistent("body")
            if value is not None:
                path = Path(reference_path(value))
                seen["exists_after_child"] = path.exists()
                seen["path"] = path
                return

    with patch("urllib.request.urlopen", return_value=_fake_response()):
        result, _ = run(parent, during=during)
    assert result.final_state == "FINISHED", result.errors
    assert seen["exists_after_child"] is True  # survived the child's cleanup
    assert not seen["path"].exists()  # deleted with the parent, which succeeded


def test_a_parents_file_passed_in_is_never_deleted_by_the_child(tmp_path):
    keep = tmp_path / "mine.txt"
    keep.write_text("parent's")
    child = (Flow("Reads", callable_=True)
             .node("start", "start_node", rows=[row("f", "file", required=True)])
             .node("end", "end_node", return_end=True, results=[])
             .link("start", "end").save())
    parent = caller(child, [configured("f", str(keep))], results=[])
    result, _ = run(parent)
    assert result.final_state == "FINISHED", result.errors
    assert keep.exists()


# -- prompts, pause, stop (C19, C20) ----------------------------------------------------

def test_a_childs_prompt_reaches_the_root_and_the_answer_comes_back():
    child = (Flow("Asks", callable_=True)
             .node("start", "start_node")
             .node("ask", "user_text_input_node", prompt="Name?")
             .node("keep", "set_variable_node", variable_name="who")
             .node("end", "end_node", return_end=True, results=[res("greeted", vault_key="who")])
             .link("start", "ask", "keep", "end").save())
    parent = caller(child, [])
    prompts = []

    async def answer(service):
        service.subscribe(USER_INPUT_NEEDED, prompts.append)
        for _ in range(200):
            await asyncio.sleep(0.01)
            if prompts:
                assert service.submit_input(prompts[0]["branch_id"], "Kim")
                return

    result, _ = run(parent, attended=True, during=answer)
    assert result.final_state == "FINISHED", result.errors
    assert result.values == {"got": "Kim"}
    assert prompts[0]["call_path"] == "Parent › Call › Asks"
    assert prompts[0]["invocation_id"].startswith("call_")


def test_pause_reaches_the_child_and_resume_continues():
    parent = caller(slow_greeter(0.4), [configured("who", "Kim")])
    states = {}

    async def pause(service):
        await asyncio.sleep(0.15)
        service.pause()
        child = service.master_state.call_tree.live_masters()[0]
        states["child"] = child.state.value
        await asyncio.sleep(0.05)
        service.resume()

    result, _ = run(parent, during=pause)
    assert states["child"] == "PAUSED"
    assert result.final_state == "FINISHED" and result.values == {"got": "Kim"}


def test_stop_waits_for_every_child_to_stop():
    parent = caller(slow_greeter(5), [configured("who", "Kim")])
    seen = {}

    async def stop(service):
        await asyncio.sleep(0.15)
        seen["child"] = service.master_state.call_tree.live_masters()[0]
        service.stop()

    result, service = run(parent, during=stop, timeout=5)
    assert result.final_state == "STOPPED"
    assert seen["child"].run_context.stop_requested
    assert not seen["child"]._supervisor_tasks  # acknowledged: nothing left running
    assert service.master_state.call_tree.live == 0


# -- run records (C22) ----------------------------------------------------------------------

def test_a_child_run_records_where_it_was_called_from():
    child = greeter()
    parent = caller(child, [configured("who", "Kim")])
    result, service = run(parent)
    records = service.master_state.run_history.list_runs()
    child_records = [r for r in records if r.get("workflow_id") == child]
    assert len(child_records) == 1
    record = child_records[0]
    assert record["root_run_id"] == record["parent_run_id"] == result.run_id
    assert record["call_site_alias"] == "Call" and record["call_number"] == 1
    assert record["invocation_id"].startswith("call_") and record["workflow_revision"]


# -- validation (C12, C17, mappings) ---------------------------------------------------------

def _validate(workflow_id):
    from backend.validator import validate_workflow

    service = RunService.create()
    service.load(workflow_id)
    result = validate_workflow(service.workflow_map, FACTORY)
    service.close()
    return ([e["code"] for e in result["errors"]],
            [w["code"] for w in result["warnings"] if w["code"].startswith("subworkflow")])


def test_validation_accepts_a_good_call_and_a_shared_helper():
    helper = greeter(name="Helper")
    b = caller(helper, [configured("who", "x")], name="B")
    d = caller(helper, [configured("who", "y")], name="D")
    top = (Flow("Top")
           .node("start", "start_node")
           .node("b", "subworkflow_node", workflow_id=b)
           .node("d", "subworkflow_node", workflow_id=d)
           .node("end", "end_node")
           .link("start", "b", "d", "end").save())
    errors, warnings = _validate(top)
    assert not [code for code in errors if code.startswith("subworkflow")]


def test_validation_rejects_a_workflow_that_calls_itself():
    a = Flow("A", callable_=True).node("start", "start_node").save()
    b = caller(a, [], name="B")
    flow = Flow("A", callable_=True)
    flow.map.load_data(persistence.load_workflow(a))
    start = flow.map.find_start_node_id()
    call = flow.map.add_node("subworkflow_node", alias="Call B")
    flow.map.update_node_config(call, {**flow.map.get_node_data(call)["config"], "workflow_id": b})
    flow.map.connect(start, "default", call, "input")
    SaveManager(flow.map).save_current_workflow()
    assert "subworkflow_recursion" in _validate(a)[0]


def test_validation_checks_the_target_and_the_mapping():
    standard = Flow("Plain").node("start", "start_node").save()
    assert "subworkflow_not_found" in _validate(caller("wf_gone", []))[0]
    assert "subworkflow_not_callable" in _validate(caller(standard, []))[0]
    child = greeter(extra_rows=[row("tone", value="plain")])
    errors, warnings = _validate(caller(child, [configured("nope", "x")]))
    assert "subworkflow_input_unknown" in errors and "subworkflow_input_missing" in errors
    errors, warnings = _validate(caller(child, [configured("who", "Kim")]))
    assert not [code for code in errors if code.startswith("subworkflow")]
    assert warnings == ["subworkflow_input_unmapped"]  # tone keeps its default


# -- Review of #87 at 974af31 -----------------------------------------------------------

def _file_after_wait_child(seconds):
    """Saves a run-owned file, then waits; returns the file."""
    return (Flow("Keeps a file", callable_=True)
            .node("start", "start_node")
            .node("http", "http_request_node", url="http://example.invalid/x", response_mode="file")
            .node("nap", "sleep_node", duration=seconds)
            .node("end", "end_node", return_end=True, results=[res("body", "file", source="Incoming payload")])
            .link("start", "http", "nap", "end").save())


def test_stop_reaches_the_child_before_its_tasks_are_cancelled():
    child = _file_after_wait_child(5)
    parent = (Flow("Parent").node("start", "start_node")
              .node("call", "subworkflow_node", workflow_id=child)
              .node("end", "end_node").link("start", "call", "end").save())
    seen = {}

    async def stop(service):
        await asyncio.sleep(0.2)
        child_master = service.master_state.call_tree.live_masters()[0]
        seen["dir"] = child_master.run_context.run_session.run_files_dir
        service.stop()
        await asyncio.sleep(0)
        service.stop()  # a second Stop must not cut the child's cleanup short
        seen["child"] = child_master

    with patch("urllib.request.urlopen", return_value=_fake_response()):
        result, service = run(parent, during=stop, timeout=5)
    assert result.final_state == "STOPPED"
    assert seen["child"].run_context.stop_requested
    assert not seen["child"]._supervisor_tasks
    # A stopped run keeps its run files (R4); success would have deleted them.
    assert any(seen["dir"].iterdir())


def test_a_root_breakpoint_pauses_running_children():
    parent = (Flow("Parent")
              .node("start", "start_node")
              .node("fan", "branch_node", branch_count=2)
              .node("call", "subworkflow_node", workflow_id=slow_greeter(0.6),
                    inputs=[configured("who", "Kim")])
              .node("nap", "sleep_node", duration=0.1)
              .node("stop_here", "no_op_node")
              .node("end_a", "end_node").node("end_b", "end_node")
              .link("start", "fan")
              .link("fan", "call", port="path_a").link("call", "end_a")
              .link("fan", "nap", port="path_b").link("nap", "stop_here", "end_b"))
    parent.map.get_node_data(parent.ids["stop_here"])["breakpoint"] = True
    parent_id = parent.save()
    seen = {}

    async def watch(service):
        for _ in range(100):
            await asyncio.sleep(0.02)
            if service.master_state.state.value == "PAUSED":
                children = service.master_state.call_tree.live_masters()
                seen["child"] = children[0].state.value if children else "gone"
                service.resume()
                return

    result, _ = run(parent_id, attended=True, during=watch)
    assert seen["child"] == "PAUSED"


def test_pause_holds_a_child_that_is_waiting_for_input():
    child = (Flow("Asks", callable_=True)
             .node("start", "start_node")
             .node("ask", "user_text_input_node", prompt="Name?")
             .node("keep", "set_variable_node", variable_name="who")
             .node("nap", "sleep_node", duration=0.05)
             .node("end", "end_node", return_end=True, results=[res("greeted", vault_key="who")])
             .link("start", "ask", "keep", "nap", "end").save())
    parent = caller(child, [])
    prompts, seen = [], {}

    async def flow(service):
        service.subscribe(USER_INPUT_NEEDED, prompts.append)
        for _ in range(100):
            await asyncio.sleep(0.01)
            if prompts:
                break
        service.pause()
        child_master = service.master_state.call_tree.live_masters()[0]
        seen["paused"] = child_master.state.value
        service.submit_input(prompts[0]["branch_id"], "Kim")
        await asyncio.sleep(0.3)
        seen["still_live"] = service.master_state.call_tree.live
        service.resume()

    result, _ = run(parent, attended=True, during=flow)
    assert seen["paused"] == "PAUSED"
    assert seen["still_live"] == 1  # it did not finish while the root was paused
    assert result.values == {"got": "Kim"}


def test_validation_finds_a_cycle_below_the_root():
    a = Flow("A", callable_=True).node("start", "start_node").save()
    b = caller(a, [], name="B")
    flow = Flow("A", callable_=True)
    flow.map.load_data(persistence.load_workflow(a))
    call = flow.map.add_node("subworkflow_node", alias="Call B")
    flow.map.update_node_config(call, {**flow.map.get_node_data(call)["config"], "workflow_id": b})
    flow.map.connect(flow.map.find_start_node_id(), "default", call, "input")
    SaveManager(flow.map).save_current_workflow()
    root = caller(a, [], name="Root")  # Root → A → B → A
    assert "subworkflow_recursion" in _validate(root)[0]


def test_validation_checks_result_mappings():
    child = greeter()
    parent = (Flow("Parent").node("start", "start_node")
              .node("call", "subworkflow_node", workflow_id=child, inputs=[configured("who", "x")],
                    results=[{"name": "removed", "to": "Vault", "vault_key": "r"}])
              .node("end", "end_node").link("start", "call", "end").save())
    assert "subworkflow_result_unknown" in _validate(parent)[0]


def test_validation_matches_input_names_exactly_like_a_run():
    errors, _ = _validate(caller(greeter(), [configured("WHO", "Kim")]))
    assert "subworkflow_input_unknown" in errors and "subworkflow_input_missing" in errors


def test_validation_parses_configured_values_by_type():
    child = greeter(extra_rows=[row("times", "number", required=True)])
    errors, _ = _validate(caller(child, [configured("who", "Kim"), configured("times", "letters")]))
    assert "subworkflow_input_invalid" in errors


def test_a_child_record_names_the_parent_visit_and_attempt():
    result, service = run(caller(greeter(), [configured("who", "Kim")]))
    record = [r for r in service.master_state.run_history.list_runs()
              if r.get("parent_run_id") == result.run_id][0]
    # The calling branch's counters: Start was visit 1, the call is visit 2,
    # its first attempt.
    assert record["parent_visit"] == 2 and record["parent_attempt"] == 1


def test_a_stopped_child_is_told_it_was_stopped_when_it_closes():
    from backend.run_session import RunSession

    closes = []
    original = RunSession.close_all

    def spy(self, delete_run_files=False):
        closes.append((self.run_id, delete_run_files))
        return original(self, delete_run_files)

    child = slow_greeter(5)
    parent = caller(child, [configured("who", "Kim")])
    seen = {}

    async def stop(service):
        await asyncio.sleep(0.2)
        seen["child"] = service.master_state.call_tree.live_masters()[0].current_run_id
        service.stop()

    with patch.object(RunSession, "close_all", spy):
        result, _ = run(parent, during=stop, timeout=5)
    assert result.final_state == "STOPPED"
    assert (seen["child"], False) in closes and (seen["child"], True) not in closes


def test_cancelling_the_call_stops_the_child_before_it_closes():
    """Review of #87: the caller's cancellation used to reach the child's
    tasks before child.stop(), so the child closed as if it had succeeded."""
    from backend.master_state import MasterState
    from backend.subworkflow_calls import call_subworkflow

    holder = (Flow("Holder").node("start", "start_node")
              .node("nap", "sleep_node", duration=10).node("end", "end_node")
              .link("start", "nap", "end").save())
    child = slow_greeter(5)
    closed = []
    original = MasterState._record_run

    def spy(self, final_state):
        if self.call_depth:
            closed.append(bool(self._run and self._run.stop_requested))
        return original(self, final_state)

    async def go():
        service = RunService.create()
        service.load(holder)
        policy, provider = unattended_policies("terminate_branch")
        await service.start(recovery_policy=policy, input_provider=provider, validate=False)
        master = service.master_state
        call = asyncio.ensure_future(call_subworkflow(
            master, master.run_context, "b", master.workflow_map.find_start_node_id(),
            child, {"who": "Kim"}))
        await asyncio.sleep(0.2)
        call.cancel()
        await asyncio.sleep(0)
        call.cancel()  # a second cancel must not cut the child's cleanup short
        try:
            await call
        except asyncio.CancelledError:
            pass
        live = master.call_tree.live
        service.stop()
        await service.wait()
        service.close()
        return live

    with patch.object(MasterState, "_record_run", spy):
        live = asyncio.run(go())
    assert closed == [True]
    assert live == 0

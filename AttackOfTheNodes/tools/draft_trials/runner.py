"""RunService trials with strict inputs, immutable evidence, and safe targets.

Use ``python -m tools.draft_trials --trial-root /fresh/absolute/root``.
Backend imports are delayed until the CLI has selected the isolated library.
"""

from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import statistics
import sys
import time
from types import SimpleNamespace as NS
from unittest.mock import patch
import asyncio

from . import JUDGE_MODELS, JUDGE_EFFORTS
from .cases import case_record, fixture_variants, good_draft, PALETTE
from .rules import check_rules, RuleFailure

APP = Path(__file__).resolve().parents[2]
SPEC = APP / "docs/delivery_tests/specs/draft-a-workflow-v2.json"
OLD = SPEC.with_name("draft-a-workflow.json")


class TrialBudget:
    # A stop-before-next-call estimate guard, not a provider billing hard cap.
    def __init__(self, budget_usd, time_limit=600):
        if budget_usd is None or not math.isfinite(budget_usd) or budget_usd <= 0:
            raise ValueError("budget must be a positive finite USD amount")
        if not math.isfinite(time_limit) or time_limit <= 0:
            raise ValueError("time limit must be positive and finite")
        self.limit = budget_usd
        self.time_limit = time_limit
        self.started = time.monotonic()
        self.cost = 0.0
        self.calls = 0
        self.succeeded = 0
        self.unknown = False

    def before(self):
        if (
            self.unknown
            or self.cost >= self.limit
            or time.monotonic() - self.started >= self.time_limit
        ):
            raise ValueError("Trial estimate/time budget reached or cost unknown")

    def record(self, result, *, attempted_calls=None):
        self.succeeded += len(result.get("agent_usage", []))
        summary = result["agent_usage_summary"]
        cost = summary["estimated_cost_usd"]
        self.unknown |= bool(summary["not_reported"])
        if attempted_calls is not None:
            self.unknown |= attempted_calls > len(result.get("agent_usage", []))
        if cost is not None:
            self.cost += cost


_budget = None
_shared_library = None


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def bounded_judge_reply(raw):
    """Use run-record credential masking before bounding saved reply evidence."""
    from backend.hermes_investigations import is_sensitive_credential_key, redact
    from backend.secrets_manager import SecretsManager

    manager = SecretsManager(_shared_library / "secrets" if _shared_library else None)
    try:
        known = tuple(manager.get_secret(key) for key in manager.list_keys())
    except Exception:
        return "[reply omitted: Secrets unavailable for redaction]"

    def mask(value):
        if isinstance(value, str):
            return redact(value, known_values=known, encoded=True)
        if isinstance(value, dict):
            return {
                mask(key): "[redacted]" if is_sensitive_credential_key(key) else mask(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [mask(item) for item in value]
        return value

    try:
        parsed = json.loads(raw)
    except ValueError:
        return mask(raw)[:4000]
    safe = mask(parsed)
    text = json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    return safe if len(text) <= 4000 else text[:4000]


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prepare_files(root, variant):
    root.mkdir(parents=True, exist_ok=True)
    for name, text in variant["files"].items():
        (root / name).write_bytes(text.encode("utf-8"))


def tree(root):
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuleFailure("symlink in fixture tree")
        if path.is_file():
            result[str(path.relative_to(root))] = path.read_bytes()
    return result


def reset_files(root, files):
    # Only our freshly created fixture directory; never a library or owner path.
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_symlink():
            raise RuleFailure("symlink in fixture tree")
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    prepare_files(root, {"files": files})


class OrderedAnswers:
    """InputProvider implementation without importing the backend before isolation."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.trace = []
        self.failure = None

    async def provide(self, request):
        if not self.answers:
            self.failure = "unexpected prompt"
            self.trace.append(dict(prompt=request.prompt, answer=None,
                                   node_id=request.node_id, failure=self.failure))
            raise ValueError(self.failure)
        expected, answer = self.answers[0]
        if expected not in request.prompt:
            self.failure = "out-of-order prompt"
            self.trace.append(dict(prompt=request.prompt, answer=None,
                                   node_id=request.node_id, failure=self.failure,
                                   expected_prompt=expected))
            raise ValueError(self.failure)
        self.answers.pop(0)
        self.trace.append(
            dict(prompt=request.prompt, answer=answer, node_id=request.node_id)
        )
        return answer

    def complete(self):
        if self.failure or self.answers:
            raise ValueError(self.failure or "missing expected prompt")


class MockSDK:
    """Replace SDK transport only. Real node preparation, masking and usage run."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.succeeded = 0

    def install(self, stack):
        from backend.integrations import claude
        from backend.secrets_manager import SecretsManager

        outer = self

        class Stream:
            def __init__(self, kwargs):
                self.kwargs = kwargs

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def get_final_message(self):
                if not outer.replies:
                    raise AssertionError("unexpected SDK call")
                reply = outer.replies.pop(0)
                if isinstance(reply, dict) and reply.get("_error"):
                    raise RuntimeError("canned transport failure")
                text = (
                    reply
                    if isinstance(reply, str)
                    else json.dumps(reply, ensure_ascii=False, separators=(",", ":"))
                )
                outer.succeeded += 1
                return NS(
                    model=self.kwargs["model"],
                    stop_reason="end_turn",
                    content=[NS(type="text", text=text)],
                    usage=NS(
                        input_tokens=100,
                        output_tokens=10,
                        cache_read_input_tokens=0,
                        cache_creation_input_tokens=0,
                        cache_creation=None,
                        iterations=None,
                    ),
                )

        class Client:
            def __init__(self, **kwargs):
                def stream(**kwargs):
                    outer.calls.append(deepcopy(kwargs))
                    return Stream(kwargs)

                self.messages = NS(stream=stream)
                self.beta = NS(messages=self.messages)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        stack.enter_context(patch.object(claude.anthropic, "AsyncAnthropic", Client))
        stack.enter_context(
            patch.object(
                claude.anthropic, "DefaultAsyncHttpxClient", lambda **kw: NS(**kw)
            )
        )
        # No Secrets I/O in Step 1, even if the selected directory contains one.
        stack.enter_context(
            patch.object(
                SecretsManager,
                "_ensure_loaded",
                side_effect=AssertionError("Secrets access forbidden"),
            )
        )
        stack.enter_context(
            patch.object(
                SecretsManager,
                "get_secret",
                return_value="mock-credential-not-a-secret",
            )
        )
        stack.enter_context(patch.object(SecretsManager, "has_key", return_value=True))
        stack.enter_context(patch.object(SecretsManager, "list_keys", return_value=[]))
        import socket

        stack.enter_context(
            patch.object(
                socket.socket,
                "connect",
                side_effect=AssertionError("network forbidden"),
            )
        )
        stack.enter_context(
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("network forbidden"),
            )
        )


def requirements(case, status="ready"):
    """Canned model output, not evidence that a real model understood the case."""
    if case.get('case_set') == 2 and status == 'ready':
        status = case.get('expected_status', status)
    result = dict(
        status=status,
        requirements=[
            dict(
                id="r1",
                action=case["request"],
                source="request",
                destination="output",
                order="as requested",
                acceptance="all frozen case rules",
            )
        ],
        questions=(
            "1. Which file?\n2. What action does clean up mean?\n3. Where should the new result be saved?"
            if status == "clarify"
            else ""
        ),
        assumptions=[],
        reason="",
    )

    if case.get('case_set') == 2:
        if status == 'clarify':
            result['questions'] = '1. Which file path should I read?'
        if status in ('outside_scope', 'needs_new_node'):
            result['reason'] = ('Sending email is outside the permitted target scope.' if status == 'outside_scope'
                                else 'The palette has no word-counting operation.')
    # Canned selection is mock transport data, not retrieval evidence. Recall is
    # scored separately against frozen role alternatives, never reference identity.
    from backend.palette_selection import ROLE_TYPES
    selected = set()
    if status == 'ready':
        draft = good_draft(case.get('id', 1), case.get('root', 'ROOT'), case.get('case_set', 1))
        selected = {n['type'] for n in draft['nodes'].values()}
    candidates, roles = [], []
    for kind in sorted(selected - {'start_node', 'end_node'}):
        role = next(r for r, alts in ROLE_TYPES.items() if (kind,) in alts)
        roles.append(dict(role=role, requirement_ids=['r1'], reason='Frozen mock outcome role'))
        candidates.append(dict(type_id=kind, role=role, requirement_ids=['r1'], reason='Canned capability candidate'))
    if status == 'ready' and not roles:
        roles.append(dict(role='finish', requirement_ids=['r1'], reason='Finish the requested work'))
    result['selection'] = dict(candidates=candidates, roles=roles)
    return result


def meaning(verdict="pass"):
    return dict(
        verdict=verdict,
        coverage=[
            dict(
                requirement_id="r1",
                evidence="start -> show; complete configured draft edges and case oracle checked independently",
                met=verdict == "pass",
            )
        ],
        problems=[] if verdict == "pass" else ["Canned review problem"],
        summary="Canned review; not inference evidence",
    )


def create_trial_service():
    """Keep all persistence in this run; share only the read-only key provider."""
    from backend import run_service as runtime

    class ReadOnlySecrets(runtime.SecretsManager):
        def set_secret(self, key, value):
            raise RuntimeError("trial library Secrets are read-only")

        def delete_secret(self, key):
            raise RuntimeError("trial library Secrets are read-only")

        def _save(self):
            raise RuntimeError("trial library Secrets are read-only")

    bus = runtime.EventBus()
    factory = runtime.NodeFactory()
    workflow_map = runtime.WorkflowMap(factory, bus)
    memory = runtime.MemoryBank(bus)
    configuration = runtime.ConfigurationManager()
    secrets = ReadOnlySecrets(
        _shared_library / "secrets" if _shared_library is not None else None
    )
    master = runtime.MasterState(
        workflow_map,
        memory,
        bus,
        output_manager=runtime.OutputManager(),
        configuration_manager=configuration,
        secrets_manager=secrets,
    )
    return runtime.RunService(
        master, workflow_map, factory, bus, secrets, configuration
    )


async def run_workflow(spec, answers, artifact, timeout=30):
    # NODE_EXECUTION_UPDATE is observational: stop() there does not prevent the
    # current node from entering its adapter. Guard the actual call boundary.
    if _budget is not None:
        from backend.integrations import claude

        original = claude.ask

        async def guarded_ask(**kwargs):
            _budget.before()
            _budget.calls += 1
            return await original(**kwargs)

        with patch.object(claude, "ask", guarded_ask):
            return await _run_workflow(spec, answers, artifact, timeout)
    return await _run_workflow(spec, answers, artifact, timeout)


async def _run_workflow(spec, answers, artifact, timeout=30):
    from backend.authoring import build_workflow
    from backend.node_factory import NodeFactory
    from backend.run_policies import InputProvider, TerminatePolicy

    class Provider(OrderedAnswers, InputProvider):
        pass

    has_asks = any(n["type"] == "ask_claude_node" for n in spec["nodes"].values())
    calls_before = _budget.calls if _budget is not None else 0
    if _budget is not None and has_asks:
        _budget.before()
    built = build_workflow(NodeFactory(), spec)
    if not built["ok"]:
        raise ValueError(built)
    provider = Provider(answers)
    service = create_trial_service()
    service.load(built["path"])
    started = time.monotonic()
    handles = {value: key for key, value in built["nodes"].items()}
    steps = []

    def step(event):
        steps.append(
            dict(
                handle=handles.get(event.get("node_id")),
                status=event.get("status"),
                branch_id=event.get("branch_id"),
                seconds=time.monotonic() - started,
            )
        )

    service.subscribe("NODE_EXECUTION_UPDATE", step)
    run_cost = 0.0
    if _budget is not None:

        def usage(event):
            nonlocal run_cost
            cost = (event.get("usage") or {}).get("estimated_cost_usd")
            if cost is None:
                _budget.unknown = True
            else:
                _budget.cost += cost
                run_cost += cost

        service.subscribe("AGENT_USAGE_UPDATE", usage)
    try:
        await service.start(
            input_provider=provider,
            recovery_policy=TerminatePolicy("terminate_workflow"),
        )
        try:
            result = (await asyncio.wait_for(service.wait(), timeout)).to_dict()
        except TimeoutError:
            service.stop()
            await asyncio.wait_for(service.wait(), 5)
            raise
        vault = deepcopy(service.master_state.memory_bank.get_state()["persistent"])
        result['output_records'] = [
            dict(text=str(line), handle=handles.get(getattr(line, 'node_id', '')))
            for line in result['outputs']
        ]
        result.update(
            seconds=time.monotonic() - started, input_trace=provider.trace, steps=steps
        )
        try:
            provider.complete()
        except ValueError as exc:
            result['input_failure'] = str(exc)
        if _budget is not None and has_asks:
            _budget.cost -= run_cost
            _budget.record(result, attempted_calls=_budget.calls - calls_before)
        write_json(artifact, result)
        return result, vault
    finally:
        service.close()


def check_cli(path, library):
    proc = subprocess.run(
        [
            sys.executable,
            str(APP / "main.py"),
            "build",
            str(path),
            "--check",
            "--json",
            "--data-dir",
            str(library),
        ],
        cwd=APP,
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        report = json.loads(proc.stdout)
    except ValueError:
        raise ValueError("build --check did not return JSON") from None
    return dict(exit_code=proc.returncode, report=report, stderr=proc.stderr)


def valid_v2_shape(record, node):
    """Use Check reply's own record gate and the workflow's actual field config."""
    from backend.node_errors import NodeError
    from backend.reply_shape import check_record

    config = json.loads(SPEC.read_text())["nodes"][node]["config"]
    try:
        check_record(record, config['expected_fields'], config['allow_other_fields'], config.get('reply_schema'))
    except NodeError:
        return False
    return True


def valid_analysis(record, shape='analysis_shape'):
    if not valid_v2_shape(record, shape):
        return False
    if record["status"] not in ("ready", "clarify", "outside_scope", "needs_new_node"):
        return False
    from backend.palette_selection import validate_analysis
    from backend.node_factory import NodeFactory
    from backend.node_errors import NodeError
    try:
        validate_analysis(NodeFactory(), record)
    except NodeError:
        return False
    ids = []
    for r in record["requirements"]:
        if not isinstance(r, dict) or not all(
            isinstance(r.get(k), str) and r[k].strip()
            for k in ("id", "action", "source", "destination", "acceptance")
        ):
            return False
        order = r.get('order')
        if not (type(order) is int or isinstance(order, str) and order.strip()):
            return False
        ids.append(r["id"])
    if len(set(ids)) != len(ids):
        return False
    if record["status"] == "ready":
        return bool(ids) and not record["questions"].strip()
    if record["status"] == "clarify":
        lines = [s for s in record["questions"].splitlines() if s.strip()]
        return (
            1 <= len(lines) <= 3
            and record["questions"].count("?") <= 3
            and all(
                re.match(r"^" + str(i) + r"[.)] ", s) for i, s in enumerate(lines, 1)
            )
        )
    return True


def valid_judge(report, req):
    if not valid_v2_shape(report, 'judge_shape'):
        return False
    if report["verdict"] not in ("pass", "fail", "unsure"):
        return False
    coverage = report["coverage"]
    ids = [r["id"] for r in req["requirements"]]
    if not all(
        isinstance(r, dict)
        and isinstance(r.get("requirement_id"), str)
        and isinstance(r.get("evidence"), str)
        and r["evidence"].strip()
        and type(r.get("met")) is bool
        for r in coverage
    ):
        return False
    if Counter(r["requirement_id"] for r in coverage) != Counter(ids):
        return False
    return report["verdict"] != "pass" or (
        not report["problems"] and all(r["met"] for r in coverage)
    )


def clarification_ok(case, first, trace):
    if case.get('case_set') == 2:
        if case['expected_first_status'] != 'clarify':
            return len(trace) == 1 and first.get('status') == case['expected_first_status']
        return (len(trace) == 2 and first.get('status') == 'clarify'
                and trace[1]['answer'] == case['clarification']
                and bool(re.search(r'file|path', first.get('questions',''), re.I)))
    if case["id"] != 10:
        return len(trace) == 1 and first.get("status") == "ready"
    if (
        len(trace) != 2
        or first.get("status") != "clarify"
        or trace[1]["answer"] != case["clarification"]
    ):
        return False
    # Versioned, intentionally small synonym groups. Unknown paraphrases fail/review.
    q = first["questions"].casefold()
    return all(
        any(word in q for word in group)
        for group in [
            ("file", "which notes"),
            ("action", "clean up", "change"),
            ("where", "destination", "save"),
        ]
    )


def case_variants(case):
    return (fixture_variants(case['id'], 2) if case.get('case_set') == 2
            else fixture_variants(case['id']))


async def target_fixtures(spec, case, directory):
    """Only called after structure, rules, deeper judge shape and safety pass."""
    results = []
    root = Path(case["root"])
    for variant in case_variants(case):
        reset_files(root, variant["files"])
        before = tree(root)
        trial = deepcopy(spec)
        trial["name"] += " " + variant["name"]
        expected_prompts = []
        # Prompt order is checked by the bounded evaluator; values come from queue.
        from .rules import evaluate

        symbolic = evaluate(spec, case, variant)
        expected_prompts = list(zip(symbolic["prompts"], variant["answers"]))
        run, vault = await run_workflow(
            trial, expected_prompts, directory / (variant["name"] + ".json")
        )
        # Classify by emitter, never by text: bare content may start with
        # [END] or another node's label. Persist handles before JSON loses
        # OutputLogEntry attributes.
        from backend.output_entry import text_output_prefix
        from .rules import allows_display_framing, display_outputs_match

        bodies, completion_noise = [], []
        for record in run['output_records']:
            node = spec['nodes'].get(record['handle'], {})
            line = record['text']
            if node.get('type') == 'end_node':
                completion_noise.append(line)
            elif node.get('type') == 'text_output_node':
                prefix = text_output_prefix(node.get('config', {}).get('label', 'Output'))
                # Remove exactly this emitter's prefix; retain bracketed data.
                bodies.append(line.removeprefix(prefix))
            else:
                bodies.append(line)  # unexpected output is not completion noise
        after = tree(root)
        created = {k: v for k, v in after.items() if k not in before}
        preserved = all(after.get(k) == v for k, v in before.items())
        expected = list(variant["outputs"])
        if "@path" in expected:
            expected = [
                (
                    str(root / next(iter(created)))
                    if x == "@path" and len(created) == 1
                    else x
                )
                for x in expected
            ]
        content_ok = Counter(created.values()) == Counter(
            v.encode("utf-8") for v in variant["writes"].values()
        )
        # Missing file fixture must error rather than report successful empty output.
        ok = (
            bool(run["errors"]) == variant["error"]
            and display_outputs_match(
                [{"body": body} for body in bodies], expected, allows_display_framing(case)
            )
            and preserved
            and content_ok
        )
        results.append(
            dict(
                fixture=variant["name"],
                result="pass" if ok else "fail",
                outputs=bodies,
                created={k: v.decode("utf-8") for k, v in created.items()},
                sentinels_preserved=preserved,
                input_trace=run["input_trace"],
                completion_noise=completion_noise,
                run_artifact=str(directory / (variant["name"] + ".json")),
            )
        )
    return dict(
        result="pass" if all(r["result"] == "pass" for r in results) else "fail",
        fixtures=results,
    )


async def run_case(
    number, trial_root, library, replies=None, real_calls=False, scenario="ready",
    *, judge_model=JUDGE_MODELS[0], judge_effort=JUDGE_EFFORTS[0], case_set=1,
):
    directory = trial_root / "cases" / str(number)
    directory.mkdir(parents=True)
    case = case_record(number, directory / "fixtures", case_set)
    variants = case_variants(case)
    expected_status = case.get("expected_status", "ready")
    needs_clarification = bool(case["clarification"])
    root = Path(case["root"])
    prepare_files(root, variants[0])
    write_json(
        directory / "frozen-case.json", dict(case, fixtures=variants)
    )
    spec = json.loads(SPEC.read_text())
    spec["name"] += " case " + str(number)
    spec["nodes"]["judge"]["config"].update(model=judge_model, effort=judge_effort)
    drafts = directory / "drafts"
    drafts.mkdir()
    spec["nodes"]["write"]["config"]["file_path"] = str(drafts / "draft.json")
    write_json(directory / "trial-designer.json", spec)
    answers = [("What should the workflow do?", case["request"])]
    if needs_clarification:
        answers.append(
            (
                "Answer the questions above",
                case["clarification"] if scenario != "unhelpful" else "not sure",
            )
        )
    if replies is None:
        first = requirements(case, "clarify" if needs_clarification else expected_status)
        replies = [first]
        if needs_clarification:
            replies.append(
                requirements(case, "clarify" if scenario == "unhelpful" else "ready")
            )
        if scenario != "unhelpful" and expected_status == "ready":
            replies.extend(
                [
                    good_draft(number, case["root"], case_set),
                    meaning("fail" if scenario == "judge_fail" else "pass"),
                ]
            )
        if scenario == "error":
            replies = [{"_error": "transport"}]
    report = dict(
        case=number,
        case_set=case_set,
        expected_first_status=case.get("expected_first_status", "clarify" if needs_clarification else "ready"),
        expected_status=expected_status,
        saved_workflow_expected=expected_status == "ready",
        expected_outcome=("status_only" if expected_status != "ready" else
                          "clarified_workflow" if needs_clarification else "ready_workflow"),
        judge_model=judge_model,
        judge_effort=judge_effort,
        mode="real" if real_calls else "mock",
        scope="not_run",
        clarification="not_run",
        spec_valid="not_run",
        case_rules={"result": "not_run"},
        meaning_review="not_run",
        behavior={"result": "not_run"},
        warnings=[],
        artifacts=str(directory),
    )
    mock = MockSDK(replies)
    started = time.monotonic()
    def finish():
        report.setdefault('recall', selection_recall(case, []))
        report['fully_right'] = report.get('result') == 'pass'
        report['seconds'] = time.monotonic() - started
        if not real_calls:
            report['calls'] = dict(attempted=len(mock.calls), succeeded=mock.succeeded, remaining=len(mock.replies))
        write_json(directory / 'report.json', report)
        return report
    try:
        with ExitStack() as stack:
            if not real_calls:
                mock.install(stack)
            run, vault = await run_workflow(
                spec,
                answers,
                directory / "designer-run.json",
                timeout=180 if real_calls else 30,
            )
        # Preserve raw replies and all named evidence via public RunService memory snapshot.
        selected = {k: v for k, v in vault.items() if k not in ("output_log",)}
        write_json(directory / "evidence.json", selected)
        write_json(
            directory / "calls.json",
            (
                mock.calls
                if not real_calls
                else {"source": "agent_usage receipts", "receipts": run["agent_usage"]}
            ),
        )
        snapshot_text = vault.get('complete_contracts', '')
        if snapshot_text.startswith('Selection snapshot: '):
            from backend.palette_selection import read_snapshot
            report['selection'] = read_snapshot(snapshot_text)
            report['recall'] = selection_recall(case, report['selection']['selected_type_ids'])
        report["usage"] = run["agent_usage"]
        report["usage_summary"] = run["agent_usage_summary"]
        report["input_trace"] = run["input_trace"]
        report["errors"] = run["errors"]
        selection_errors = [e for e in run['errors'] if e.get('code') == 'selection_incomplete']
        if selection_errors:
            report['selection_stop'] = selection_errors
        report["gate_evidence"] = run["steps"]
        report['draft_retry'] = dict(
            requested='first_check_error' in vault,
            attempted=sum(e['handle'] == 'draft_retry' and e['status'] == 'running'
                          for e in run['steps']),
            succeeded=sum(e['handle'] == 'draft_retry' and e['status'] == 'done'
                          for e in run['steps']),
            check_passed=any(e['handle'] == 'check_retry' and e['status'] == 'done'
                             for e in run['steps']),
        )
        report["model_calls"] = dict(
            attempted=sum(
                e["status"] == "running"
                and spec["nodes"][e["handle"]]["type"] == "ask_claude_node"
                for e in run["steps"]
            ),
            succeeded=len(run["agent_usage"]),
        )
        if run.get('input_failure'):
            report['input_failure'] = run['input_failure']
            raise ValueError(run['input_failure'])
        if not real_calls and mock.replies:
            raise ValueError("Unused canned replies; unexpected call sequence")
        first = json.loads(vault.get("first_analysis", "null"))
        frozen = json.loads(vault.get("frozen_requirements", "null"))
        frozen_shape = 'resolved_shape' if vault.get('resolved_analysis') else 'analysis_shape'
        judge = vault.get("judge_report")
        report["scope"] = (
            first.get("status", "invalid") if isinstance(first, dict) else "invalid"
        )
        report["clarification"] = (
            "pass"
            if valid_analysis(first)
            and clarification_ok(case, first, run["input_trace"])
            else "fail"
        )
        report["meaning_review"] = (
            judge.get("verdict", "invalid")
            if isinstance(judge, dict)
            and valid_analysis(frozen, frozen_shape)
            and valid_judge(judge, frozen)
            else "not_run" if judge is None else "invalid"
        )
        report['status_check'] = dict(
            first=first.get('status') if isinstance(first, dict) else 'invalid',
            final=(frozen.get('status') if isinstance(frozen, dict) else
                   first.get('status') if isinstance(first, dict) and expected_status != 'ready' else 'not_frozen'),
            expected_first=report['expected_first_status'], expected_final=expected_status)
        if expected_status in ('outside_scope', 'needs_new_node'):
            files = list(drafts.glob('*'))
            correct = (valid_analysis(first) and first['status'] == expected_status
                       and bool(first['reason'].strip()) and not first['questions'].strip()
                       and len(run['input_trace']) == 1 and not run['errors']
                       and not files and not vault.get('draft_text') and judge is None
                       and report['model_calls']['attempted'] == 1)
            report.update(result='pass' if correct else 'fail',
                          clarification='not_required', spec_valid='not_applicable',
                          case_rules=dict(result='pass' if correct else 'fail', rules=[dict(
                              id=f'{case_set}.{number}.status_and_no_workflow',
                              result='pass' if correct else 'fail', evidence=report['status_check'])]),
                          meaning_review='not_applicable',
                          behavior=dict(result='not_applicable', fixtures=[]),
                          no_saved_workflow=not files)
            if not correct:
                report['failure'] = 'Expected status with reason and no saved workflow or target execution'
            return finish()
        structural = vault.get("spec_check")
        if isinstance(structural, dict):
            report["spec_valid"] = "pass" if structural.get("ok") else "fail"
            report["warnings"] = structural.get("problems", [])
        elif any(error.get("code") == "spec_invalid" for error in run["errors"]):
            report["spec_valid"] = "fail"
        raw = vault.get("draft_text")
        files = list(drafts.glob("*"))
        if raw:
            (directory / "raw-draft.json").write_bytes(raw.encode("utf-8"))
            report["raw_sha256"] = sha(raw)
            report["case_rules"] = check_rules(json.loads(raw), case)
        if not raw or not files:
            raise ValueError("No saved draft / no completed success gate")
        if (
            len(files) != 1
            or files[0].is_symlink()
            or not files[0].resolve().is_relative_to(drafts.resolve())
            or files[0].read_bytes() != raw.encode("utf-8")
        ):
            raise ValueError(
                "Saved draft differs from raw reply or escapes draft directory"
            )
        raw_path = files[0]
        report.update(raw_sha256=sha(raw), saved_path=str(raw_path))
        contracts = vault.get("complete_contracts", "")
        from backend.palette_selection import read_snapshot
        receipt = read_snapshot(contracts)
        report['selection'] = receipt
        report['recall'] = selection_recall(case, receipt['selected_type_ids'])
        report["contracts"] = dict(characters=len(contracts), sha256=sha(contracts))
        if len(contracts) > 50000 or not contracts:
            raise ValueError("Complete contracts outside planning budget")
        if (
            len(raw) > 8000
            or len(vault.get("first_analysis", "")) > 8000
            or len(vault.get("resolved_analysis", "")) > 8000
            or len(vault.get("judge_text", "")) > 4000
        ):
            raise ValueError("Reply exceeds frozen limit")
        if not valid_analysis(frozen, frozen_shape) or frozen["status"] != "ready":
            raise ValueError("Invalid/unresolved requirements")
        report["meaning_review"] = (
            judge.get("verdict", "invalid") if valid_judge(judge, frozen) else "invalid"
        )
        if report["meaning_review"] != "pass":
            raise ValueError("Meaning review did not pass deeper shape/coverage checks")
        checked = check_cli(raw_path, library)
        write_json(directory / "build-check.json", checked)
        report["spec_valid"] = (
            "pass" if checked["exit_code"] == 0 and checked["report"]["ok"] else "fail"
        )
        report["warnings"] = checked["report"].get("diagnostics", [])
        target = json.loads(raw)
        if needs_clarification:
            gate_order = [e["handle"] for e in run["steps"] if e["status"] == "done"]
            if (
                not (
                    "answer" in gate_order
                    and "write" in gate_order
                    and gate_order.index("answer")
                    < gate_order.index("draft")
                    < gate_order.index("write")
                )
                or "[Questions] " + first["questions"] not in run["outputs"]
            ):
                raise ValueError("Clarification display/order evidence missing")
        if (
            report["clarification"] != "pass"
            or report["spec_valid"] != "pass"
            or report["warnings"]
            or report["case_rules"]["result"] != "pass"
        ):
            raise ValueError("Case gates failed; target not executed")
        report["behavior"] = await target_fixtures(
            target, case, directory / "target-runs"
        )
        report["result"] = report["behavior"]["result"]
    except (
        ValueError,
        RuntimeError,
        TimeoutError,
        OSError,
        KeyError,
        TypeError,
    ) as exc:
        report["result"] = "fail"
        report["failure"] = str(exc)
    return finish()


def selection_recall(case, selected):
    """Frozen role alternatives/compositions, separate from behavior/rule verdicts."""
    selected = set(selected)
    roles = case.get('required_structure', {}).get('roles', {})
    covered, missing, useful = [], [], set()
    for name, rule in roles.items():
        alternatives = rule.get('one_of', [rule])
        alternatives = [{r['type']} for r in alternatives]
        viable = [alt for alt in alternatives if alt <= selected]
        if viable:
            covered.append(name)
            useful.update(set.union(*viable))
        else:
            missing.append(dict(role=name, acceptable_compositions=[sorted(a) for a in alternatives]))
    useful.update({'start_node', 'end_node'} & selected)
    return dict(roles_covered=covered, candidate_count=len(selected), missing_roles=missing,
                unnecessary_candidates=sorted(selected - useful),
                status_only=case.get('expected_status', 'ready') != 'ready',
                evidence='Frozen role recall; mock responses do not demonstrate semantic retrieval')


async def contract_inventory():
    from backend import node_catalogue
    from backend.node_factory import NodeFactory

    factory = NodeFactory()
    spec = json.loads(SPEC.read_text())
    values = {}
    inventory = {}
    defaults = factory.metadata_for_type("node_catalogue_node")["default_config"]
    for handle, node in spec["nodes"].items():
        if not handle.startswith("catalogue_"):
            continue
        config = {**deepcopy(defaults), **node["config"]}
        values[config["vault_write_key"]] = await node_catalogue.build(factory, config)
        records = await node_catalogue.build(factory, dict(config, format="JSON"))
        inventory[handle] = [e["type"] for e in records["entries"]]
    text = spec["nodes"]["contracts"]["config"]["template"].format_map(values)
    if set(t for ts in inventory.values() for t in ts) != PALETTE or len(text) > 50000:
        raise ValueError("Palette drift or excessive contracts")
    return text, inventory


async def calibrate(
    trial_root, real_calls=False, judge_replies=None, *,
    judge_model=JUDGE_MODELS[0], judge_effort=JUDGE_EFFORTS[0],
):
    from backend.agent_usage import usage_summary
    from backend.meta_workflow import check
    from backend.node_errors import NodeError
    from backend.node_factory import NodeFactory

    workflow = json.loads(SPEC.read_text())
    factory = NodeFactory()

    calls_before = _budget.calls if _budget else 0
    succeeded_before = _budget.succeeded if _budget else 0
    cost_before = _budget.cost if _budget else 0
    contracts, inventory = await contract_inventory()
    write_json(
        trial_root / "artifacts" / "contracts.json",
        dict(
            inventory=inventory,
            characters=len(contracts),
            sha256=sha(contracts),
            text=contracts,
        ),
    )
    pairs = json.loads(
        (Path(__file__).parent / "fixtures/calibration.json").read_text()
    )
    rows = []
    mock_replies = iter(judge_replies) if judge_replies is not None else None
    failure = None
    try:
        for pair in pairs:
            directory = trial_root / "calibration" / pair["id"]
            case = case_record(pair["case"], directory / "fixtures")
            prepare_files(Path(case["root"]), fixture_variants(pair["case"])[0])
            for variant in ("good", "bad"):
                target = json.loads(json.dumps(pair[variant]).replace("ROOT", case["root"]))
                expected = variant == "good"
                rules = check_rules(target, case)
                write_json(directory / (variant + "-draft.json"), target)
                raw_draft = json.dumps(target)
                try:
                    _, structural = await check(
                        factory, raw_draft, workflow["nodes"]["check"]["config"]["max_spec"],
                        fail_on_unreachable=workflow["nodes"]["check"]["config"].get("fail_on_unreachable", False),
                        fail_on_disabled_output=workflow["nodes"]["check"]["config"].get("fail_on_disabled_output", False)
                    )
                except NodeError as exc:
                    # Negative calibration fixtures still reach the judge, with
                    # the same check's error evidence instead of a success report.
                    structural = dict(ok=False, code=exc.code, message=str(exc), **exc.details)
                template = workflow["nodes"]["judge_question"][
                    "config"
                ]["template"]
                req = requirements(case)
                question = template.format_map(
                    dict(
                        draft_request=case["request"],
                        clarification_answer=case["clarification"],
                        frozen_requirements=json.dumps(req),
                        draft_text=raw_draft,
                        spec_check=json.dumps(structural),
                    )
                )
                (directory / (variant + "-judge-question.txt")).write_text(
                    question, encoding="utf-8"
                )
                judge_node = deepcopy(json.loads(SPEC.read_text())["nodes"]["judge"])
                judge_node["config"].update(
                    model=judge_model,
                    effort=judge_effort,
                    context_source="Configured",
                    context=contracts,
                    vault_write_key="judge_text",
                    details_vault_key="judge_details",
                )
                spec = dict(
                    format="aotn-workflow/1",
                    name="Calibration " + pair["id"] + " " + variant,
                    nodes={
                        "start": {"type": "start_node", "config": {"greeting": question}},
                        "judge": judge_node,
                        "end": {"type": "end_node", "config": {"record_line": False}},
                    },
                    connections=[
                        {"from": "start.default", "to": "judge.input"},
                        {"from": "judge.default", "to": "end.input"},
                    ],
                )
                reply = (
                    next(mock_replies)
                    if mock_replies is not None
                    else meaning("pass" if expected else "fail")
                )
                with ExitStack() as stack:
                    if not real_calls:
                        MockSDK([reply]).install(stack)
                    run, vault = await run_workflow(
                        spec,
                        [],
                        directory / (variant + "-judge-run.json"),
                        timeout=180 if real_calls else 30,
                    )
                    judge_reply = bounded_judge_reply(vault.get("judge_text", ""))
                try:
                    judge = json.loads(vault.get("judge_text", "null"))
                except ValueError:
                    judge = None
                verdict = judge.get("verdict") if valid_judge(judge, req) else "invalid"
                false_pass = not expected and verdict == "pass"
                false_failure = expected and verdict != "pass"
                rows.append(
                    dict(
                        fixture=pair["id"],
                        variant=variant,
                        expected="pass" if expected else "fail",
                        case_rules=rules["result"],
                        rules=rules["rules"],
                        judge_verdict=verdict,
                        judge_reply=judge_reply,
                        model_calls=dict(
                            attempted=sum(
                                e["handle"] == "judge" and e["status"] == "running"
                                for e in run["steps"]
                            ),
                            succeeded=len(run["agent_usage"]),
                        ),
                        judge_false_pass=false_pass,
                        judge_false_failure=false_failure,
                        usage=run["agent_usage"],
                        result=(
                            "pass"
                            if (rules["result"] == "pass") == expected
                            and not false_pass
                            and not false_failure
                            else "fail"
                        ),
                    )
                )
                if run.get('errors'):
                    raise ValueError('Calibration judge run failed; inspect its run evidence')
    except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
        failure = type(exc).__name__ + ": " + str(exc)
    receipts = [receipt for row in rows for receipt in row["usage"]]
    calls = {
        key: sum(r["model_calls"][key] for r in rows)
        for key in ("attempted", "succeeded")
    }
    if _budget is not None:
        calls = dict(
            attempted=_budget.calls - calls_before,
            succeeded=_budget.succeeded - succeeded_before,
        )
    result = dict(
        judge_model=judge_model,
        judge_effort=judge_effort,
        model_calls=calls,
        estimated_cost_usd=(
            _budget.cost - cost_before if _budget is not None
            else usage_summary(receipts)["estimated_cost_usd"]
        ),
        mode="real" if real_calls else "mock",
        result=(
            "pass" if not failure and all(r["result"] == "pass" for r in rows)
            else "fail"
        ),
        judge_false_passes=sum(r["judge_false_pass"] for r in rows),
        judge_false_failures=sum(r["judge_false_failure"] for r in rows),
        fixtures=rows,
    )
    if failure:
        result["failure"] = failure
    write_json(trial_root / "calibration-report.json", result)
    return result


async def _batch(
    trial_root,
    case_ids=range(1, 11),
    real_calls=False,
    calibrate_only=False,
    scenario="ready",
    replies_file=None,
    judge_model=JUDGE_MODELS[0],
    judge_effort=JUDGE_EFFORTS[0],
    cases_even_if_calibration_fails=False,
    case_set=1,
):
    from backend.authoring import build_workflow
    from backend.node_factory import NodeFactory

    start = time.monotonic()
    library = trial_root / "library"
    artifacts = trial_root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    # Both versions built in the isolated library; only v2 executes.
    for path in (OLD, SPEC):
        built = build_workflow(NodeFactory(), json.loads(path.read_text()))
        write_json(artifacts / (path.stem + "-build.json"), built)
        if not built["ok"]:
            raise ValueError(built)
    calibration = {"result": "not_run"}
    rows = []
    failure = None
    try:
        calibration = await calibrate(
            trial_root, real_calls, judge_model=judge_model, judge_effort=judge_effort
        )
        failure = calibration.get("failure")
        if (calibration["result"] == "pass" or cases_even_if_calibration_fails) and not calibrate_only:
            overrides = (
                json.loads(Path(replies_file).read_text()) if replies_file else {}
            )
            for number in case_ids:
                if _budget is not None:
                    _budget.before()
                rows.append(
                    await run_case(
                        number,
                        trial_root,
                        library,
                        overrides.get(str(number)),
                        real_calls,
                        scenario,
                        judge_model=judge_model,
                        judge_effort=judge_effort,
                        **({"case_set": case_set} if case_set != 1 else {}),
                    )
                )
    except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
        failure = type(exc).__name__ + ": " + str(exc)
    calls = {
        key: calibration.get("model_calls", {}).get(key, 0)
        + sum(r.get("model_calls", {}).get(key, 0) for r in rows)
        for key in ("attempted", "succeeded")
    }
    if _budget is not None:
        calls = dict(attempted=_budget.calls, succeeded=_budget.succeeded)
    summary = dict(
        judge_model=judge_model,
        judge_effort=judge_effort,
        model_calls=calls,
        mode="real" if real_calls else "mock",
        input_transport="RunService InputProvider (not CLI interactive proof)",
        case_set=case_set,
        case_count=len(rows),
        fully_right=sum(r["result"] == "pass" for r in rows),
        fixture_count=sum(len(r.get("behavior", {}).get("fixtures", [])) for r in rows),
        calibration=calibration["result"],
        cases_even_if_calibration_fails=cases_even_if_calibration_fails,
        cases=rows,
        result=(
            "pass"
            if not failure
            and calibration["result"] == "pass"
            and all(r["result"] == "pass" for r in rows)
            else "fail"
        ),
        seconds=time.monotonic() - start,
    )
    elapsed = [r["seconds"] for r in rows]
    summary["timing"] = {
        "p50": statistics.median(elapsed) if elapsed else None,
        "min": min(elapsed) if elapsed else None,
        "max": max(elapsed) if elapsed else None,
    }
    summary["separate_results"] = {
        key: dict(
            Counter(
                (
                    r[key].get("result")
                    if isinstance(r.get(key), dict)
                    else r.get(key, "not_run")
                )
                for r in rows
            )
        )
        for key in ("spec_valid", "case_rules", "meaning_review", "behavior")
    }
    summary["failures"] = dict(
        Counter(
            r.get("failure", "behavior failure") for r in rows if r["result"] != "pass"
        )
    )
    if failure:
        summary["failure"] = failure
    summary["estimated_cost_usd"] = _budget.cost if _budget is not None else None
    summary["cost_note"] = (
        "Mock token counts do not measure inference cost"
        if not real_calls
        else "Estimate/time guard includes calibration; stops before further calls at the recorded limits or unknown cost. Not a billing hard cap."
    )
    return summary


async def batch(
    trial_root,
    case_ids=range(1, 11),
    real_calls=False,
    calibrate_only=False,
    scenario="ready",
    replies_file=None,
    *,
    budget_usd=None,
    time_limit=600,
    shared_library=None,
    judge_model=JUDGE_MODELS[0],
    judge_effort=JUDGE_EFFORTS[0],
    cases_even_if_calibration_fails=False,
    case_set=1,
):
    global _budget, _shared_library
    previous = _budget, _shared_library
    try:
        if case_set not in (1, 2):
            raise ValueError("case_set must be 1 or 2")
        _budget = TrialBudget(budget_usd, time_limit) if real_calls else None
        if real_calls and shared_library is None:
            raise ValueError("real calls require a prepared shared library")
        _shared_library = Path(shared_library) if real_calls else None
        summary = await _batch(
            trial_root, case_ids, real_calls, calibrate_only, scenario, replies_file,
            judge_model, judge_effort,
            cases_even_if_calibration_fails, case_set,
        )
        summary.update(budget_usd=budget_usd, time_limit_seconds=time_limit)
        write_json(trial_root / "report.json", summary)
        return summary
    finally:
        _budget, _shared_library = previous

"""Step 1 only. No provider access, credentials, owner workflows or PTY."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.draft_trials import runner
from tools.draft_trials.cases import (
    PALETTE,
    case_record,
    good_draft,
    fixture_variants,
    calibration_pairs,
)
from tools.draft_trials.rules import check_rules


@pytest.fixture
def case(tmp_path):
    def make(number):
        root = tmp_path / ("case-" + str(number))
        root.mkdir(exist_ok=True)
        runner.prepare_files(root, fixture_variants(number)[0])
        return case_record(number, root)

    return make


def test_v2_structural_gate_and_contracts():
    from backend.authoring import check_workflow_spec
    from backend.node_factory import NodeFactory

    spec = json.loads(runner.SPEC.read_text())
    report = check_workflow_spec(NodeFactory(), spec)
    assert report["ok"] and not report["diagnostics"]
    nodes = spec["nodes"]
    edges = spec["connections"]
    assert nodes["write"]["config"]["content_vault_key"] == "draft_text"
    assert {"from": "pass.true", "to": "write.content"} in edges
    assert {"from": "check.default", "to": "judge_question.input"} in edges
    assert nodes["pass"]["config"]["right_value"] == "pass"
    assert nodes["answer"]["config"]["prompt"] == "Answer the questions above"
    calls = [n for n in nodes.values() if n["type"] == "ask_claude_node"]
    assert len(calls) == 4
    assert all(
        n["config"]["model"] == "claude-haiku-5-5"
        and n["config"]["effort"] == "low"
        and n["config"]["reply_json"]
        for n in calls
    )

    # No errors can rejoin a success path, no cycles/retries, and save needs pass.
    def walk(h, blocked=None, seen=frozenset()):
        assert h not in seen
        reachable = {h}
        for edge in edges:
            if edge["from"].split(".")[0] == h and edge["from"] != blocked:
                reachable |= walk(edge["to"].split(".")[0], blocked, seen | {h})
        return reachable

    assert walk("start") == set(nodes)
    assert "write" not in walk("start", "pass.true")
    assert "write" not in walk("error_message")


@pytest.mark.asyncio
async def test_complete_palette_and_planning_budget():
    text, inventory = await runner.contract_inventory()
    assert set(t for types in inventory.values() for t in types) == PALETTE
    assert all(
        inventory[h]
        for h in ("catalogue_conditional", "catalogue_concat", "catalogue_json_path")
    )
    assert 8000 < len(text) < 50000


@pytest.mark.parametrize("pair", calibration_pairs(), ids=lambda p: p["id"])
def test_each_calibration_pair(pair, case):
    c = case(pair["case"])
    for variant, expected in [("good", "pass"), ("bad", "fail")]:
        spec = json.loads(json.dumps(pair[variant]).replace("ROOT", c["root"]))
        report = check_rules(spec, c)
        assert report["result"] == expected, report
    # Frozen fixture artifact and programmatic definitions cannot drift.
    assert (
        json.loads(
            (Path(runner.__file__).parent / "fixtures/calibration.json").read_text()
        )
        == calibration_pairs()
    )


@pytest.mark.parametrize(
    "mutation", ["outside", "symlink", "dynamic", "type", "vault_race"]
)
def test_path_type_and_unproven_vault_safety(mutation, case, tmp_path):
    c = case(5)
    spec = good_draft(5, c["root"])
    config = spec["nodes"]["write"]["config"]
    if mutation == "outside":
        config["file_path"] = str(tmp_path / "outside.txt")
    elif mutation == "dynamic":
        config["file_path_source"] = "Vault"
        config["file_path_vault_key"] = "unknown"
    elif mutation == "symlink":
        outside = tmp_path / "escape"
        outside.mkdir()
        link = Path(c["root"]) / "link"
        link.symlink_to(outside, target_is_directory=True)
        config["file_path"] = str(link / "agenda-copy.txt")
    elif mutation == "type":
        spec["nodes"]["read"]["type"] = "ask_claude_node"
    else:
        config["content_source"] = "Vault"
        config["content_vault_key"] = "not_written"
    assert check_rules(spec, c)["result"] == "fail"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "number,scenario,expected",
    [
        (1, "ready", "pass"),
        (10, "ready", "pass"),
        (1, "judge_fail", "fail"),
        (1, "error", "fail"),
        (10, "unhelpful", "fail"),
    ],
)
async def test_designer_and_runner_paths(
    tmp_path, number, scenario, expected, monkeypatch
):
    # The autouse backend fixture supplies an isolated library before imports.
    # MockSDK itself refuses any Secrets lazy load and any socket connection.
    trial = tmp_path / "trial"
    trial.mkdir()
    report = await runner.run_case(
        number, trial, tmp_path / "library", scenario=scenario
    )
    assert report["result"] == expected, report
    files = list((trial / "cases" / str(number) / "drafts").glob("*"))
    if expected == "pass":
        assert len(files) == 1 and report["behavior"]["result"] == "pass"
        assert report["calls"]["attempted"] == (4 if number == 10 else 3)
        assert report["calls"]["remaining"] == 0
        assert report["clarification"] == "pass"
        evidence = json.loads(
            (trial / "cases" / str(number) / "evidence.json").read_text()
        )
        assert files[0].read_bytes() == evidence["draft_text"].encode("utf-8")
        assert "confidence" not in evidence["judge_text"]
    else:
        assert files == [] and report["behavior"]["result"] == "not_run"
        if scenario == "judge_fail":
            assert report["meaning_review"] == "fail"
            assert (
                report["spec_valid"] == "pass"
                and report["case_rules"]["result"] == "pass"
            )
        assert report["calls"]["attempted"] == (
            1 if scenario == "error" else 2 if scenario == "unhelpful" else 3
        )


@pytest.mark.asyncio
async def test_false_pass_and_deep_shape_are_not_accepted(tmp_path):
    c = case_record(1, tmp_path / "trial/cases/1/fixtures")
    judge = runner.meaning()
    judge["coverage"][0]["requirement_id"] = "invented"
    report = await runner.run_case(
        1,
        tmp_path / "trial",
        tmp_path / "library",
        replies=[runner.requirements(c), good_draft(1, c["root"]), judge],
    )
    assert report["result"] == "fail" and report["meaning_review"] == "invalid"
    assert report["behavior"]["result"] == "not_run"
    req = runner.requirements(c, "clarify")
    req["questions"] = "1. A?\n2. B?\n3. C?\n4. D?"
    assert not runner.valid_analysis(req)


@pytest.mark.asyncio
async def test_ordered_input_queue_rejects_extra_missing_and_reordered():
    from backend.run_policies import InputRequest

    request = InputRequest("run", "branch", "node", "Second question")
    queue = runner.OrderedAnswers([("First", "one")])
    with pytest.raises(ValueError, match="out-of-order"):
        await queue.provide(request)
    with pytest.raises(ValueError):
        queue.complete()
    queue = runner.OrderedAnswers([])
    with pytest.raises(ValueError, match="unexpected"):
        await queue.provide(request)
    queue = runner.OrderedAnswers([("Second", "two")])
    with pytest.raises(ValueError, match="missing"):
        queue.complete()


@pytest.mark.slow
def test_full_mock_batch_and_all_target_fixtures(tmp_path):
    root = tmp_path / "batch"
    proc = subprocess.run(
        [sys.executable, "-m", "tools.draft_trials", "--trial-root", str(root)],
        cwd=runner.APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    run_root = Path(json.loads(proc.stdout)["report"]).parent
    assert run_root == root / "runs" / "000001"
    report = json.loads((run_root / "report.json").read_text())
    assert report["result"] == "pass" and report["case_count"] == 10
    assert report["fixture_count"] == 21
    calibration = json.loads((run_root / "calibration-report.json").read_text())
    assert len(calibration["fixtures"]) == 44 and calibration["result"] == "pass"
    assert calibration["judge_false_passes"] == calibration["judge_false_failures"] == 0
    assert all(r["case_rules"] == r["expected"] for r in calibration["fixtures"])
    assert not (root / "library/secrets/secrets.json").exists()
    assert all(c["calls"]["remaining"] == 0 for c in report["cases"])
    assert all(
        c["usage_summary"]["reported"] == c["calls"]["attempted"]
        for c in report["cases"]
    )
    # Reuse creates a new run without touching any previous evidence.
    before = runner.tree(run_root)
    again = subprocess.run(
        [sys.executable, "-m", "tools.draft_trials", "--trial-root", str(root)],
        cwd=runner.APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert again.returncode == 0, again.stdout + again.stderr
    assert Path(json.loads(again.stdout)["report"]).parent == root / "runs" / "000002"
    assert runner.tree(run_root) == before
    assert not list((root / "library").iterdir())


@pytest.mark.slow
@pytest.mark.asyncio
async def test_calibration_detects_judge_false_passes_and_failures(tmp_path):
    replies = []
    for _ in calibration_pairs():
        replies += [runner.meaning("fail"), runner.meaning("pass")]
    result = await runner.calibrate(tmp_path, judge_replies=replies)
    assert result["result"] == "fail"
    assert result["judge_false_passes"] == result["judge_false_failures"] == 22
    assert all(r["case_rules"] == r["expected"] for r in result["fixtures"])


def test_mock_sdk_never_reads_secrets_or_connects():
    from contextlib import ExitStack
    from backend.secrets_manager import SecretsManager
    import socket

    with ExitStack() as stack:
        runner.MockSDK([]).install(stack)
        with pytest.raises(AssertionError, match="Secrets"):
            SecretsManager()._ensure_loaded()
        with pytest.raises(AssertionError, match="network"):
            socket.create_connection(("example.invalid", 443))


def test_budget_stops_on_estimate_time_or_unknown_cost(monkeypatch):
    budget = runner.TrialBudget(0.10)
    budget.before()
    budget.record(
        {
            "agent_usage_summary": {"estimated_cost_usd": 0.10, "not_reported": 0},
            "errors": [],
        }
    )
    with pytest.raises(ValueError):
        budget.before()
    budget = runner.TrialBudget(0.10)
    budget.unknown = True
    with pytest.raises(ValueError):
        budget.before()
    budget = runner.TrialBudget(0.10)
    budget.started -= 601
    with pytest.raises(ValueError):
        budget.before()


@pytest.mark.asyncio
async def test_structural_error_stops_before_judge_or_save(tmp_path):
    c = case_record(1, tmp_path / "trial/cases/1/fixtures")
    bad = good_draft(1, c["root"])
    bad["nodes"]["show"]["type"] = "imaginary_node"
    report = await runner.run_case(
        1,
        tmp_path / "trial",
        tmp_path / "library",
        replies=[runner.requirements(c), bad],
    )
    assert report["result"] == "fail" and report["calls"]["attempted"] == 2
    assert report["behavior"]["result"] == "not_run"
    assert list((tmp_path / "trial/cases/1/drafts").glob("*")) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", ["unsure", "PASS", "unknown"])
async def test_only_exact_pass_can_save(tmp_path, verdict):
    c = case_record(1, tmp_path / "trial/cases/1/fixtures")
    report = await runner.run_case(
        1,
        tmp_path / "trial",
        tmp_path / "library",
        replies=[
            runner.requirements(c),
            good_draft(1, c["root"]),
            runner.meaning(verdict),
        ],
    )
    assert report["result"] == "fail"
    assert list((tmp_path / "trial/cases/1/drafts").glob("*")) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("number,adapter", [(5, "path"), (3, "vault")])
async def test_equivalent_adapters_pass_rules_and_real_targets(
    tmp_path, number, adapter
):
    c = case_record(number, tmp_path / f"trial/cases/{number}/fixtures")
    spec = good_draft(number, c["root"])
    if adapter == "path":
        spec["nodes"]["path"] = {"type": "json_path_node", "config": {"path": "path"}}
        spec["nodes"]["show"]["config"]["template"] = "{input}"
        spec["connections"] = [
            e for e in spec["connections"] if e["from"] != "write.default"
        ] + [
            {"from": "write.default", "to": "path.input"},
            {"from": "path.default", "to": "show.input"},
        ]
    else:
        spec["nodes"]["ask"]["config"]["membank_outputs"] = [
            {"id": "note", "output": "note", "data_type": "string"}
        ]
        spec["nodes"]["join"] = {
            "type": "concat_node",
            "config": {"template": "{note}"},
        }
        spec["connections"] = [
            e for e in spec["connections"] if e["from"] != "ask.default"
        ] + [
            {"from": "ask.default", "to": "join.input"},
            {"from": "join.default", "to": "transform.input"},
        ]
    report = await runner.run_case(
        number,
        tmp_path / "trial",
        tmp_path / "library",
        replies=[runner.requirements(c), spec, runner.meaning()],
    )
    assert report["result"] == "pass", report


def test_parallel_allows_proven_preceding_vault_writer(case):
    c = case(8)
    spec = good_draft(8, c["root"])
    spec["nodes"]["ask"]["config"]["membank_outputs"] = [
        {"id": "original", "output": "original", "data_type": "string"}
    ]
    assert check_rules(spec, c)["result"] == "pass"

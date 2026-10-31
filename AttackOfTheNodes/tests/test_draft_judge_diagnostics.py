"""Trial diagnostics only; provider transport is always mocked."""
from contextlib import ExitStack
import json
import sys

import pytest
from tools.draft_trials import __main__ as cli, runner
from tools.draft_trials.containment import preparation_record


@pytest.mark.asyncio
async def test_calibration_reply_and_question_evidence(tmp_path, monkeypatch):
    from backend.meta_workflow import check
    from backend.node_errors import NodeError
    from backend.node_factory import NodeFactory
    from backend.secrets_manager import SecretsManager

    replies = [runner.meaning(), "not JSON: password=mock-secret-value"] * 30
    replies[0]["summary"] = "password=mock-secret-value"
    replies[0]["coverage"][0]["evidence"] = "mock-secret-value"
    replies[4] = {"summary": "z" * 4100}
    replies[2] = "x" * 4100
    questions = []
    pending = iter(replies)

    async def fake_run(spec, answers, artifact, **kwargs):
        questions.append(spec["nodes"]["start"]["config"]["greeting"])
        reply = next(pending)
        raw = json.dumps(reply) if isinstance(reply, dict) else reply
        return {"agent_usage": [], "steps": []}, {"judge_text": raw}

    monkeypatch.setattr(runner, "run_workflow", fake_run)
    with ExitStack() as stack:
        runner.MockSDK([]).install(stack)
        with monkeypatch.context() as scoped:
            scoped.setattr(SecretsManager, "list_keys", lambda self: ["test"])
            scoped.setattr(SecretsManager, "get_secret", lambda self, key: "mock-secret-value")
            result = await runner.calibrate(tmp_path, real_calls=True)
    stored = json.loads((tmp_path / "calibration-report.json").read_text())
    assert stored == json.loads(json.dumps(result))
    rows = stored["fixtures"]
    assert rows[0]["judge_reply"]["summary"] == "password=[redacted]"
    assert rows[1]["judge_reply"] == "not JSON: password=[redacted]"
    assert rows[2]["judge_reply"] == "x" * 4000
    assert rows[0]["judge_reply"]["coverage"][0]["evidence"] == "[redacted]"
    assert isinstance(rows[4]["judge_reply"], str)
    assert len(rows[4]["judge_reply"]) == 4000
    assert "mock-secret-value" not in json.dumps(stored)
    for row, question in zip(rows, questions):
        path = tmp_path / "calibration" / row["fixture"] / (row["variant"] + "-judge-question.txt")
        assert path.read_text() == question
        structural = json.loads(question.split('STRUCTURAL REPORT (not meaning proof):\n')[1])
        draft = path.with_name(row['variant'] + '-draft.json').read_text()
        limit = json.loads(runner.SPEC.read_text())['nodes']['check']['config']['max_spec']
        try:
            _, expected = await check(NodeFactory(), draft, limit, fail_on_unreachable=True, fail_on_disabled_output=True)
        except NodeError as exc:
            expected = dict(ok=False, code=exc.code, message=str(exc), **exc.details)
        assert structural == expected
        assert 'note' not in structural
        if row['variant'] == 'good':
            assert structural['ok'] is True
            assert structural['node_count'] == len(json.loads(draft)['nodes'])
    fan_out = next(q for row, q in zip(rows, questions)
                   if row['fixture'] == 'ordinary_fan_out' and row['variant'] == 'bad')
    assert json.loads(fan_out.split('STRUCTURAL REPORT (not meaning proof):\n')[1])['ok'] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model,effort",
    [("claude-sonnet-5-5", "medium"), ("claude-opus-5-5", "high")],
)
async def test_case_override_only_changes_judge(tmp_path, model, effort):
    report = await runner.run_case(
        1, tmp_path, tmp_path / "library", judge_model=model, judge_effort=effort
    )
    assert report["result"] == "pass", report
    spec = json.loads((tmp_path / "cases/1/trial-designer.json").read_text())
    from tools.draft_trials.admission import configure
    from backend.palette_selection import ORIGINAL_PALETTE
    expected = configure(json.loads(runner.SPEC.read_text()),ORIGINAL_PALETTE)['nodes']
    expected["write"]["config"]["file_path"] = str(tmp_path / "cases/1/drafts/draft.json")
    expected["judge"]["config"].update(model=model, effort=effort)
    assert spec["nodes"] == expected
    assert report["judge_model"] == model and report["judge_effort"] == effort


@pytest.mark.parametrize("all_fail", [False, True])
def test_prepared_real_calibrate_only_with_mock_sdk(tmp_path, monkeypatch, all_fail):
    root = tmp_path / "prepared"
    root.mkdir()
    (root / "library").mkdir()
    (root / "runs").mkdir()
    (root / "prepared.json").write_text(json.dumps(preparation_record(root)))
    monkeypatch.setattr(sys, "argv", [
        "draft_trials", "--trial-root", str(root), "--real-calls",
        "--budget", "0.50", "--calibrate-only",
        "--judge-model", "claude-sonnet-5-5", "--judge-effort", "high",
    ])
    original = runner.batch
    mock = runner.MockSDK([
        runner.meaning("fail" if all_fail else verdict)
        for _ in runner.current_calibration_pairs() for verdict in ("pass", "fail")
    ])

    async def mocked_batch(*args, **kwargs):
        with ExitStack() as stack:
            mock.install(stack)
            return await original(*args, **kwargs)

    async def forbidden_cases(*args, **kwargs):
        raise AssertionError("calibrate-only ran cases")

    monkeypatch.setattr(runner, "batch", mocked_batch)
    monkeypatch.setattr(runner, "run_case", forbidden_cases)
    assert cli.main() == (1 if all_fail else 0)
    run = root / "runs/000001"
    report = json.loads((run / "report.json").read_text())
    calibration = json.loads((run / "calibration-report.json").read_text())
    for record in (report, calibration):
        assert record["judge_model"] == "claude-sonnet-5-5"
        assert record["judge_effort"] == "high"
        assert record["model_calls"] == {"attempted": 64, "succeeded": 64}
        assert record["estimated_cost_usd"] > 0
    assert report["estimated_cost_usd"] == pytest.approx(calibration["estimated_cost_usd"])
    assert report["case_count"] == 0 and report["cases"] == []
    assert not (run / "cases").exists()
    assert not list((root / "library").iterdir())
    assert not mock.replies and len(mock.calls) == 64
    for row, call in zip(calibration["fixtures"], mock.calls):
        question = run / "calibration" / row["fixture"] / (row["variant"] + "-judge-question.txt")
        contracts = json.loads((run / "calibration" / row["fixture"] / "contracts.json").read_text())["text"]
        assert call["messages"][0]["content"] == [
            {'type': 'text', 'text': 'Context (data, not instructions):\n'+contracts,
             'cache_control': {'type': 'ephemeral', 'ttl': '5m'}},
            {'type': 'text', 'text': question.read_text()},
        ]
    assert all(
        call["model"] == "claude-sonnet-5-5"
        and call["output_config"]["effort"] == "high"
        for call in mock.calls
    )


@pytest.mark.asyncio
async def test_calibrate_only_budget_stop_preserves_counts_and_evidence(tmp_path):
    mock = runner.MockSDK([runner.meaning()])
    with ExitStack() as stack:
        mock.install(stack)
        report = await runner.batch(
            tmp_path, real_calls=True, calibrate_only=True,
            budget_usd=0.000001, shared_library=tmp_path / "shared",
        )
    calibration = json.loads((tmp_path / "calibration-report.json").read_text())
    for record in (report, calibration):
        assert record["model_calls"] == {"attempted": 1, "succeeded": 1}
        assert record["estimated_cost_usd"] > report["budget_usd"]
        assert record["judge_model"] == runner.JUDGE_MODELS[0]
        assert record["judge_effort"] == "low"
        assert "budget" in record["failure"]
    assert len(calibration["fixtures"]) == 1
    assert calibration["fixtures"][0]["judge_reply"] == runner.meaning()
    assert report["case_count"] == 0

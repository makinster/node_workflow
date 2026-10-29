"""Route placement is independent of output text and data provenance."""

from copy import deepcopy
from pathlib import Path

import pytest

from tools.draft_trials import runner
from tools.draft_trials.cases import case_record, fixture_variants, good_draft
from tools.draft_trials.rules import check_rules


def serial_parallel_draft(root):
    # Adapted directly from /tmp/pr135-case8-recheck.py.
    spec = good_draft(8, root)
    spec["nodes"]["ask"]["config"]["membank_outputs"] = [
        {"id": "original", "output": "original", "data_type": "string"}
    ]
    spec["nodes"]["restore"] = {
        "type": "concat_node",
        "config": {"template": "{original}"},
    }
    spec["connections"] = [
        edge
        for edge in spec["connections"]
        if edge["from"] not in ("parallel.path_b", "show.default")
    ]
    spec["connections"] += [
        {"from": "parallel.path_b", "to": "end.input"},
        {"from": "show.default", "to": "restore.input"},
        {"from": "restore.default", "to": "lower.input"},
    ]
    return spec


def hoisted_uppercase_draft(root):
    spec = good_draft(9, root)
    spec["connections"] = [
        edge
        for edge in spec["connections"]
        if edge["from"] not in ("strip.default", "if.false", "upper.default")
    ]
    spec["connections"] += [
        {"from": "strip.default", "to": "upper.input"},
        {"from": "upper.default", "to": "if.input"},
        {"from": "if.false", "to": "write.content"},
    ]
    return spec


def early_messages_draft(root):
    import json
    from tools.draft_trials.cases import calibration_pairs

    pair = next(
        pair
        for pair in calibration_pairs()
        if pair["id"] == "conditional_work_before_choice"
    )
    return json.loads(json.dumps(pair["bad"]).replace("ROOT", root))


@pytest.mark.parametrize(
    "number,make",
    [
        (8, serial_parallel_draft),
        (9, hoisted_uppercase_draft),
        (7, early_messages_draft),
    ],
)
def test_required_work_must_follow_declared_route(tmp_path, number, make):
    case = case_record(number, tmp_path / "fixtures")
    runner.prepare_files(Path(case["root"]), fixture_variants(number)[0])
    report = check_rules(make(case["root"]), case)
    assert report["result"] == "fail", report
    shape = next(
        row for row in report["rules"] if row["id"].endswith(".required_structure")
    )
    assert shape["result"] == "fail"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "number,make",
    [
        (8, serial_parallel_draft),
        (9, hoisted_uppercase_draft),
        (7, early_messages_draft),
    ],
)
async def test_full_mock_trial_rejects_work_on_wrong_route(tmp_path, number, make):
    case = case_record(number, tmp_path / f"trial/cases/{number}/fixtures")
    spec = make(case["root"])
    report = await runner.run_case(
        number,
        tmp_path / "trial",
        tmp_path / "library",
        replies=[runner.requirements(case), spec, runner.meaning()],
    )
    assert report["spec_valid"] == "pass"
    assert report["case_rules"]["result"] == "fail"
    assert report["behavior"]["result"] == "not_run"
    assert report["result"] == "fail"


@pytest.mark.parametrize("number", [7, 8, 9])
def test_declared_route_work_accepts_good_graphs_and_renamed_handles(tmp_path, number):
    case = case_record(number, tmp_path / "fixtures")
    runner.prepare_files(Path(case["root"]), fixture_variants(number)[0])
    spec = good_draft(number, case["root"])
    renamed = {handle: "step_" + str(i) for i, handle in enumerate(spec["nodes"])}
    spec["nodes"] = {renamed[handle]: node for handle, node in spec["nodes"].items()}
    for edge in spec["connections"]:
        for side in ("from", "to"):
            handle, port = edge[side].split(".")
            edge[side] = renamed[handle] + "." + port
    assert check_rules(spec, case)["result"] == "pass"


def test_parallel_work_may_swap_ports(tmp_path):
    case = case_record(8, tmp_path / "fixtures")
    spec = good_draft(8, case["root"])
    for edge in spec["connections"]:
        if edge["from"].startswith("parallel."):
            edge["from"] = "parallel." + (
                "path_b" if edge["from"] == "parallel.path_a" else "path_a"
            )
    report = check_rules(spec, case)
    assert report["result"] == "pass", report
    shape = next(
        row["evidence"]
        for row in report["rules"]
        if row["id"].endswith(".required_structure")
    )
    assert {row["port"] for row in shape["routes"]} == {"path_a", "path_b"}


def test_correct_data_cannot_borrow_another_operations_route(tmp_path):
    from tools.draft_trials.rules import evaluate
    from tools.draft_trials.structure_rules import check_required_structure

    case = case_record(8, tmp_path / "fixtures")
    spec = good_draft(8, case["root"])
    results = [evaluate(spec, case, variant) for variant in fixture_variants(8)]
    assert (
        check_required_structure(spec, case["required_structure"], results)["result"]
        == "pass"
    )
    for result in results:
        for visit in result["visits"]:
            if visit["handle"] == "show":
                visit["data_lineage"] = ("ask",)
    assert (
        check_required_structure(spec, case["required_structure"], results)["result"]
        == "fail"
    )


@pytest.mark.parametrize("number", [7, 9])
def test_each_conditional_route_requires_its_own_work(tmp_path, number):
    from tools.draft_trials.cases import calibration_pairs

    case = case_record(number, tmp_path / "fixtures")
    runner.prepare_files(Path(case["root"]), fixture_variants(number)[0])
    name = (
        "conditional_work_before_choice"
        if number == 7
        else "empty_choice_still_saves"
    )
    pair = next(pair for pair in calibration_pairs() if pair["id"] == name)
    import json

    bad = json.loads(json.dumps(pair["bad"]).replace("ROOT", case["root"]))
    report = check_rules(bad, case)
    shape = next(
        row for row in report["rules"] if row["id"].endswith(".required_structure")
    )
    assert shape["result"] == "fail"


def test_end_only_work_cannot_satisfy_a_declared_branch(tmp_path):
    from tools.draft_trials.rules import evaluate
    from tools.draft_trials.structure_rules import check_required_structure

    case = case_record(8, tmp_path / "fixtures")
    spec = serial_parallel_draft(case["root"])
    declaration = deepcopy(case["required_structure"])
    declaration["roles"]["finish"] = {"type": "end_node"}
    declaration["forks"][0]["work"] = [
        ["upper", "upper_message", "lower", "lower_message"],
        ["finish"],
    ]
    result = evaluate(spec, case, fixture_variants(8)[0])
    assert check_required_structure(spec, declaration, [result])["result"] == "fail"


def test_linear_case_structure_is_declarative_too(tmp_path):
    case = case_record(3, tmp_path / "fixtures")
    spec = good_draft(3, case["root"])
    assert check_rules(spec, case)["result"] == "pass"
    # This test changes the frozen test declaration, not the generated draft:
    # the common matcher must enforce declarations without knowing a case id.
    case["required_structure"]["before"].append(("message", "upper"))
    assert check_rules(spec, case)["result"] == "fail"

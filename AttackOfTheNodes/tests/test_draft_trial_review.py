"""Review probes: no inference, backend-library escapes, or Secrets access."""

import asyncio
import json
import os
from pathlib import Path
import sys

import pytest

from tools.draft_trials import __main__ as cli
from tools.draft_trials import runner
from tools.draft_trials.cases import case_record, fixture_variants, good_draft
from tools.draft_trials.rules import check_rules


def prepared_root(tmp_path):
    root = tmp_path / "trial"
    root.mkdir()
    (root / "library").mkdir()
    (root / "prepared.json").write_text(
        json.dumps(
            {
                "version": 1,
                "library": str(root / "library"),
                "note": "Step 2 requires separate owner approval. Owner adds key through app. Harness never copies Secrets.",
            }
        )
    )
    return root


def invoke(monkeypatch, root, *flags):
    monkeypatch.setattr(
        sys, "argv", ["draft_trials", "--trial-root", str(root), *flags]
    )
    return cli.main()


def test_review_symlink_library_cannot_write_outside(tmp_path, monkeypatch, capsys):
    # Adapted from /tmp/pr135-root-probe.py; fake batch makes no API calls.
    root = prepared_root(tmp_path)
    outside = tmp_path / "outside-library"
    outside.mkdir()
    (root / "library").rmdir()
    (root / "library").symlink_to(outside, target_is_directory=True)
    calls = []

    async def fake_batch(trial_root, *args):
        calls.append(trial_root)
        (trial_root / "library" / "probe.json").write_text("escaped write")
        return {"result": "pass", "case_count": 0}

    monkeypatch.setattr(runner, "batch", fake_batch)
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, root, "--real-calls")
    assert error.value.code == 2
    assert "symlink" in capsys.readouterr().err
    assert not calls and not list(outside.iterdir())


def test_review_symlink_marker_cannot_overwrite_sentinel(tmp_path, monkeypatch, capsys):
    # The second review probe used --real-calls --prepare without any API call.
    root = prepared_root(tmp_path)
    sentinel = tmp_path / "outside-sentinel.txt"
    sentinel.write_text("KEEP OUTSIDE SENTINEL")
    (root / "prepared.json").unlink()
    (root / "prepared.json").symlink_to(sentinel)
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, root, "--real-calls", "--prepare")
    assert error.value.code == 2
    assert sentinel.read_text() == "KEEP OUTSIDE SENTINEL"
    assert "error" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_review_hardcoded_heading_fails_full_mock_case(tmp_path):
    # Adapted from /tmp/pr135-loose-probe.py; original passes rules + behavior.
    case = case_record(2, tmp_path / "trial/cases/2/fixtures")
    bad = good_draft(2, case["root"])
    bad["nodes"]["start"]["config"]["greeting"] = ""
    bad["nodes"]["show"]["config"]["template"] = "{input}monday update"
    report = await runner.run_case(
        2,
        tmp_path / "trial",
        tmp_path / "library",
        replies=[runner.requirements(case), bad, runner.meaning()],
    )
    assert report["result"] == "fail"
    assert report["case_rules"]["result"] == "fail"
    assert report["behavior"]["result"] == "not_run"


@pytest.mark.parametrize("number", [4, 5, 10])
def test_partial_file_dependency_is_not_full_source_provenance(tmp_path, number):
    root = tmp_path / "case"
    case = case_record(number, root)
    runner.prepare_files(root, fixture_variants(number)[0])
    bad = good_draft(number, str(root))
    if number == 4:
        bad["nodes"]["show"]["config"][
            "template"
        ] = "{input[0]}udget: €20\nBring notes.\n"
    else:
        # Keep a real file-derived character and the right operation names,
        # then supply the rest of the known answer as literals.
        before = "read" if number == 5 else "transform"
        text = (
            "{input[0]}ine one\nLine two\n" if number == 5 else "{input[0]}ello\nworld"
        )
        bad["nodes"]["partial"] = {"type": "concat_node", "config": {"template": text}}
        bad["connections"] = [
            e for e in bad["connections"] if e["from"] != before + ".default"
        ]
        bad["connections"] += [
            {"from": before + ".default", "to": "partial.input"},
            {"from": "partial.default", "to": "write.content"},
        ]
    assert check_rules(bad, case)["result"] == "fail"


@pytest.mark.parametrize(
    "entry", ["internal_link", "external_link", "dangling_link", "fifo", "hard_link"]
)
def test_entire_prepared_tree_is_checked_before_imports_or_writes(
    tmp_path, monkeypatch, capsys, entry
):
    import builtins

    root = prepared_root(tmp_path)
    nested = root / "library" / "nested"
    nested.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("KEEP")
    if entry == "internal_link":
        (nested / "entry").symlink_to(root / "prepared.json")
    elif entry == "external_link":
        (nested / "entry").symlink_to(outside)
    elif entry == "dangling_link":
        (nested / "entry").symlink_to(tmp_path / "missing")
    elif entry == "fifo":
        os.mkfifo(nested / "entry")
    else:
        os.link(outside, nested / "entry")
    imports = builtins.__import__

    def no_backend_import(name, *args, **kwargs):
        if name == "runner" or name.startswith("backend"):
            raise AssertionError("import happened before containment validation")
        return imports(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_backend_import)
    monkeypatch.setenv("AOTN_DATA_DIR", "unchanged")
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, root, "--real-calls")
    assert error.value.code == 2
    assert "trial root" in capsys.readouterr().err
    assert os.environ["AOTN_DATA_DIR"] == "unchanged"
    assert outside.read_text() == "KEEP"
    assert not (root / "report.json").exists()


@pytest.mark.parametrize(
    "content",
    [
        "{}",
        "invalid",
        '{"version":1,"version":1}',
        '{"version":true}',
        '{"library":"/outside"}',
    ],
)
def test_invalid_preparation_records_stop_before_batch(
    tmp_path, monkeypatch, capsys, content
):
    root = prepared_root(tmp_path)
    (root / "prepared.json").write_text(content)

    async def forbidden(*args):
        raise AssertionError("batch reached an invalid marker")

    monkeypatch.setattr(runner, "batch", forbidden)
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, root, "--real-calls")
    assert error.value.code == 2
    assert "prepared.json" in capsys.readouterr().err
    assert (root / "prepared.json").read_text() == content


def test_prepare_is_exclusive_and_valid_marker_is_accepted_without_calls(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "trial"
    assert invoke(monkeypatch, root, "--prepare") == 0
    marker = (root / "prepared.json").read_bytes()
    with pytest.raises(SystemExit):
        invoke(monkeypatch, root, "--real-calls", "--prepare")
    assert (root / "prepared.json").read_bytes() == marker
    called = []

    async def fake_batch(trial_root, *args):
        called.append(trial_root)
        (trial_root / "library" / "probe.txt").write_text("contained")
        return {"result": "pass", "case_count": 0}

    monkeypatch.setattr(runner, "batch", fake_batch)
    assert invoke(monkeypatch, root, "--real-calls") == 0
    assert called == [root]
    assert (root / "library" / "probe.txt").read_text() == "contained"
    assert (root / "prepared.json").read_bytes() == marker


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", 2),
        ("version", True),
        ("library", "library"),
        ("library", "/outside"),
        ("note", "wrong"),
    ],
)
def test_marker_fields_must_match_actual_root(
    tmp_path, monkeypatch, capsys, field, value
):
    root = prepared_root(tmp_path)
    marker = root / "prepared.json"
    record = json.loads(marker.read_text())
    record[field] = value
    marker.write_text(json.dumps(record))
    with pytest.raises(SystemExit):
        invoke(monkeypatch, root, "--real-calls")
    assert "prepared.json" in capsys.readouterr().err


@pytest.mark.parametrize("number", range(1, 11))
def test_every_case_has_source_and_operation_provenance(tmp_path, number):
    from tools.draft_trials.rules import evaluate, provenance_matches

    case = case_record(number, tmp_path / "case")
    runner.prepare_files(Path(case["root"]), fixture_variants(number)[0])
    variant = fixture_variants(number)[0]
    result = evaluate(good_draft(number, case["root"]), case, variant)
    assert provenance_matches(result, case, variant)
    if number == 1:
        # Ready is an explicitly requested fixed message: a literal is valid.
        return
    if number in (7, 9):
        # Literal status messages must depend on the real tested input.
        for output in result["outputs"]:
            output["controls"] = ()
    elif result["writes"]:
        for write in result["writes"]:
            write["expression"] = ("literal", write["content"])
    else:
        for output in result["outputs"]:
            output["expression"] = ("literal", output["body"])
    assert not provenance_matches(result, case, variant)


def test_correct_heading_can_come_from_concat_and_either_operation_order(tmp_path):
    case = case_record(2, tmp_path / "case")
    spec = good_draft(2, case["root"])
    spec["nodes"]["start"]["config"]["greeting"] = ""
    spec["nodes"]["heading"] = {
        "type": "concat_node",
        "config": {"template": "  Monday Update  "},
    }
    spec["connections"] = [
        edge for edge in spec["connections"] if edge["from"] != "start.default"
    ]
    spec["connections"] += [
        {"from": "start.default", "to": "heading.input"},
        {"from": "heading.default", "to": "strip.input"},
    ]
    assert check_rules(spec, case)["result"] == "pass"
    spec["nodes"]["strip"]["config"]["operation"] = "lowercase"
    spec["nodes"]["transform"]["config"]["operation"] = "strip"
    assert check_rules(spec, case)["result"] == "pass"


def test_trial_tools_use_multiline_statements():
    import ast
    import io
    import tokenize

    for path in (runner.APP / "tools" / "draft_trials").glob("*.py"):
        source = path.read_text()
        assert not any(
            token.type == tokenize.OP and token.string == ";"
            for token in tokenize.generate_tokens(io.StringIO(source).readline)
        ), path
        for node in ast.walk(ast.parse(source)):
            if isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.With,
                    ast.Try,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):
                assert all(statement.lineno > node.lineno for statement in node.body), (
                    path,
                    node.lineno,
                )

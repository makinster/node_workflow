"""System nodes (AI coordination decision C7, owner 2026-10-20): Disk space,
Git status and File age each run one fixed operation; only their folder or
file changes, and that must be inside a folder allowed in Options
(``system_node_folders``).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_system_nodes.py -v
"""

import os
import shutil
import subprocess
import time

import pytest

from backend.node_errors import NodeError
from backend.system_access import allowed_folders, checked_path
from tests.test_subworkflow_calls import Flow, _isolated, run  # noqa: F401


def shown(node_type, settings, **config):
    """Run Start → node → Text Output and return (outputs, errors)."""
    flow = (Flow("System").node("start", "start_node").node("probe", node_type, **config)
            .node("show", "text_output_node", template="{input}", input_source="Upstream payload",
                  request_user_input=False, label="Value")
            .node("end", "end_node", record_line=False).link("start", "probe", "show", "end"))
    result, _ = run(flow.save(), settings=settings)
    values = [str(o.get("value") if isinstance(o, dict) else o).split("] ", 1)[-1] for o in result.outputs]
    codes = [str(e.get("code")) for e in result.errors]
    return values, codes


# -- where they may look -------------------------------------------------------------------

def test_allowed_folders_default_to_home_and_split_on_semicolons(tmp_path):
    assert allowed_folders(None) == [os.path.realpath(os.path.expanduser("~"))] or \
        [str(f) for f in allowed_folders(None)] == [os.path.realpath(os.path.expanduser("~"))]
    two = allowed_folders(lambda key: f"{tmp_path} ; {tmp_path / 'b'}")
    assert [str(f) for f in two] == [str(tmp_path.resolve()), str((tmp_path / "b").resolve())]


def test_outside_or_missing_paths_are_coded_errors(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    setting = lambda key: str(allowed)  # noqa: E731
    with pytest.raises(NodeError) as outside:
        checked_path(tmp_path, setting)
    with pytest.raises(NodeError) as escaped:
        checked_path(allowed / ".." / "elsewhere", setting)
    with pytest.raises(NodeError) as missing:
        checked_path(allowed / "nope", setting)
    assert (outside.value.code, escaped.value.code, missing.value.code) == \
        ("not_allowed", "not_allowed", "folder_missing")
    assert checked_path(allowed, setting) == allowed.resolve()


# -- Disk space -------------------------------------------------------------------------------

def test_disk_space_reports_numbers(tmp_path):
    settings = {"system_node_folders": str(tmp_path)}
    free, codes = shown("disk_space_node", settings, folder=str(tmp_path), report="Free space", unit="GB")
    used, _ = shown("disk_space_node", settings, folder=str(tmp_path), report="Used percent")
    total, _ = shown("disk_space_node", settings, folder=str(tmp_path), report="Total size", unit="MB")
    assert codes == []
    expected = shutil.disk_usage(tmp_path)
    assert abs(float(free[0]) - expected.free / 1024 ** 3) < 1
    assert 0 <= float(used[0]) <= 100
    assert abs(float(total[0]) - expected.total / 1024 ** 2) < 1024


def test_disk_space_outside_the_allowed_folders_fails(tmp_path):
    (tmp_path / "ok").mkdir()
    values, codes = shown("disk_space_node", {"system_node_folders": str(tmp_path / "ok")}, folder=str(tmp_path))
    assert values == [] and "not_allowed" in codes


# -- File age ---------------------------------------------------------------------------------

def test_file_age_in_the_chosen_unit(tmp_path):
    target = tmp_path / "report.txt"
    target.write_text("x")
    two_hours_ago = time.time() - 7200
    os.utime(target, (two_hours_ago, two_hours_ago))
    settings = {"system_node_folders": str(tmp_path)}
    hours, codes = shown("file_age_node", settings, path=str(target), unit="Hours")
    minutes, _ = shown("file_age_node", settings, path=str(target), unit="Minutes")
    missing, missing_codes = shown("file_age_node", settings, path=str(tmp_path / "gone.txt"))
    assert codes == [] and abs(float(hours[0]) - 2) < 0.05 and abs(float(minutes[0]) - 120) < 3
    assert missing == [] and "folder_missing" in missing_codes


# -- Git status -------------------------------------------------------------------------------

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))


@needs_git
def test_git_status_reports_clean_branch_and_changed_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "a.txt").write_text("1")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-q", "-m", "one")
    settings = {"system_node_folders": str(tmp_path)}
    clean, codes = shown("git_status_node", settings, folder=str(repo), report="Clean")
    branch, _ = shown("git_status_node", settings, folder=str(repo), report="Branch")
    (repo / "a.txt").write_text("2")
    (repo / "new.txt").write_text("n")
    dirty, _ = shown("git_status_node", settings, folder=str(repo), report="Clean")
    changed, _ = shown("git_status_node", settings, folder=str(repo), report="Changed files")
    tracked_only, _ = shown("git_status_node", settings, folder=str(repo), report="Changed files",
                            include_untracked=False)
    assert codes == [] and clean == ["True"] and branch == ["main"] and dirty == ["False"]
    assert "a.txt" in changed[0] and "new.txt" in changed[0]
    assert "a.txt" in tracked_only[0] and "new.txt" not in tracked_only[0]


@needs_git
def test_git_status_outside_a_repository_is_a_coded_error(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    values, codes = shown("git_status_node", {"system_node_folders": str(tmp_path)}, folder=str(plain))
    assert values == [] and "not_a_repository" in codes


def test_git_status_output_type_follows_report():
    from backend.nodes.io.git_status_node import GitStatusNode

    assert {report: GitStatusNode.describe_output_ports({"report": report})["default"]["data_type"]
            for report in GitStatusNode.REPORT_TYPES} == {
        "Clean": "bool", "Branch": "string", "Changed files": "var", "Commits ahead": "number"}

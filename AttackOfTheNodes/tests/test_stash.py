"""Stash S1: StashManager, the paste parser and accepted_types.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_stash.py -v
"""

import json
from pathlib import Path

import pytest

from backend import persistence
from backend.field_types import accepted_types
from backend.paste_parser import looks_like_path, parse_paste, split_pieces
from backend.stash_manager import FORMAT, StashError, StashManager, looks_like_secret


@pytest.fixture
def stash(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "STASH_DIR", tmp_path / "stash")
    return StashManager()


@pytest.fixture
def files(tmp_path):
    """Two real files, one with a space in its name."""
    folder = tmp_path / "data"
    folder.mkdir()
    plain = folder / "march.csv"
    spaced = folder / "q1 notes.txt"
    plain.write_text("a,b\n")
    spaced.write_text("notes\n")
    return plain, spaced


# -- paste parser ---------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    # Windows Terminal into WSL: quoted only when the path has spaces.
    ('"C:\\Users\\me\\a b.txt" C:\\Users\\me\\c.txt', ["C:\\Users\\me\\a b.txt", "C:\\Users\\me\\c.txt"]),
    # UNC paths keep both leading backslashes.
    ("\\\\wsl.localhost\\Ubuntu\\home\\me\\x.txt", ["\\\\wsl.localhost\\Ubuntu\\home\\me\\x.txt"]),
    # GNOME-style single quotes and POSIX escapes.
    ("'/home/me/a b.txt' /home/me/c\\ d.txt", ["/home/me/a b.txt", "/home/me/c d.txt"]),
    # Newline-separated drops.
    ("/a/one.txt\n/a/two.txt\n", ["/a/one.txt", "/a/two.txt"]),
])
def test_split_pieces_per_terminal(text, expected):
    assert [piece for piece, _ in split_pieces(text)] == expected


def test_looks_like_path():
    for piece in ("/x", "~/x", "~", "C:\\x", "c:/x", "\\\\server\\share", "file:///x"):
        assert looks_like_path(piece), piece
    for piece in ("notes.txt", "./x", "hello", "C:x"):
        assert not looks_like_path(piece), piece


def test_existing_files_become_file_candidates(files):
    plain, spaced = files
    result = parse_paste(f"'{spaced}' {plain}")
    assert result.files == [spaced, plain] and result.text is None and not result.rejected


def test_file_uri_is_decoded(files):
    _, spaced = files
    result = parse_paste("file://" + str(spaced).replace(" ", "%20"))
    assert result.files == [spaced]


def test_missing_and_folder_paths_are_reported_not_stored(files, tmp_path):
    plain, _ = files
    result = parse_paste(f"{plain} /nowhere/gone.txt {tmp_path}")
    assert result.files == [plain]
    assert [(r.piece, r.reason) for r in result.rejected] == [
        ("/nowhere/gone.txt", "not found on this machine"),
        (str(tmp_path), "is a folder; folder import comes later (S4)"),
    ]


def test_prose_that_mentions_a_path_stays_text():
    result = parse_paste("see /etc/hosts for details")
    assert result.text == "see /etc/hosts for details" and not result.files


def test_blank_paste_is_empty():
    assert parse_paste("   \n").empty


# -- StashManager ---------------------------------------------------------------

def test_add_file_and_text_round_trip(stash, files):
    plain, _ = files
    entry = stash.add_file(str(plain))
    assert entry["id"].startswith("stash_") and entry["name"] == "march"
    assert entry["type"] == "file"
    assert entry["value"] == {"type": "file", "ref_key": f"file:{plain}", "path": str(plain)}
    note = stash.add_text("Summarise in three bullets", name="summary prompt")
    assert note["type"] == "string" and note["value"] == "Summarise in three bullets"
    reloaded = StashManager()
    assert [e["name"] for e in reloaded.list_entries()] == ["march", "summary prompt"]
    assert [e["name"] for e in reloaded.list_entries("file")] == ["march"]
    on_disk = json.loads(stash.path.read_text())
    assert on_disk["format"] == FORMAT and len(on_disk["entries"]) == 2


def test_add_file_accepts_an_unquoted_argument_with_spaces(stash, files):
    _, spaced = files
    assert stash.add_file(str(spaced))["value"]["path"] == str(spaced)


def test_add_file_refuses_missing_paths_and_folders(stash, tmp_path):
    with pytest.raises(StashError, match="not found on this machine"):
        stash.add_file("/nowhere/gone.txt")
    with pytest.raises(StashError, match="is a folder"):
        stash.add_file(str(tmp_path))
    assert stash.list_entries() == []


def test_names_are_unique_ignoring_case(stash, files):
    plain, _ = files
    stash.add_file(str(plain))
    assert stash.add_text("x", name="march 2")["name"] == "march 2"
    with pytest.raises(StashError, match="already named 'MARCH'"):
        stash.add_text("y", name="MARCH")  # a chosen name must be free
    with pytest.raises(StashError, match="can't be blank"):
        stash.add_text("z", name="  ")


def test_rename_keeps_the_id_and_remove_by_name(stash, files):
    plain, _ = files
    entry = stash.add_file(str(plain))
    renamed = stash.rename(entry["id"], "  March report ")
    assert (renamed["id"], renamed["name"]) == (entry["id"], "March report")
    assert stash.get("march REPORT")["id"] == entry["id"]
    assert stash.remove("March report")["id"] == entry["id"]
    assert stash.list_entries() == []
    with pytest.raises(StashError, match="No Stash entry"):
        stash.remove("March report")


def test_add_paste_stores_files_or_one_text_entry(stash, files):
    plain, spaced = files
    entries, result = stash.add_paste(f"'{spaced}' {plain} /nowhere/x.txt")
    assert [e["name"] for e in entries] == ["q1 notes", "march"]
    assert [r.piece for r in result.rejected] == ["/nowhere/x.txt"]
    entries, _ = stash.add_paste("Use British spelling throughout please")
    assert entries[0]["type"] == "string" and entries[0]["name"] == "Use British spelling throughout"


def test_key_like_text_is_warned_about_not_refused(stash):
    entry = stash.add_text("sk-abcdefghijklmnopqrstuv", name="oops")
    assert stash.warnings_for(entry) == [
        "'oops' looks like a key or password; secrets belong in Settings > Secrets, not the Stash"]
    assert looks_like_secret("api_key = 123") and not looks_like_secret("a normal sentence")


def test_unreadable_stash_file_is_never_overwritten(stash):
    stash.path.parent.mkdir(parents=True)
    stash.path.write_text("{ not json")
    with pytest.raises(StashError, match="Cannot read the Stash"):
        stash.add_text("x")
    assert stash.path.read_text() == "{ not json"


# -- export / import ------------------------------------------------------------

def test_export_then_import_into_another_stash(stash, files, tmp_path, monkeypatch):
    plain, _ = files
    stash.add_file(str(plain))
    stash.add_text("password: hunter2", name="careful")
    warnings = stash.export_to(tmp_path / "out.json")
    assert warnings == ["'careful' looks like a key or password; secrets belong in "
                        "Settings > Secrets, not the Stash"]
    exported = json.loads((tmp_path / "out.json").read_text())
    assert exported["format"] == FORMAT and len(exported["entries"]) == 2

    other = StashManager(tmp_path / "other")
    other.add_text("already here", name="march")
    report = other.import_from(tmp_path / "out.json")
    assert report == {"added": ["careful", "march (as march 2)"], "skipped": []}
    # Importing again skips what is already present (same id).
    assert other.import_from(tmp_path / "out.json")["added"] == []


def test_import_skips_files_missing_on_this_machine_and_bad_entries(stash, tmp_path):
    doc = {"format": FORMAT, "entries": [
        {"id": "stash_aaaaaaaaaaaa", "name": "gone", "type": "file",
         "value": {"type": "file", "ref_key": "file:/nowhere/x", "path": "/nowhere/x"}},
        {"id": "stash_bbbbbbbbbbbb", "name": "blob", "type": "json", "value": {}},
        {"id": "nope", "name": "bad id", "type": "string", "value": "x"},
        {"id": "stash_cccccccccccc", "name": "ok", "type": "string", "value": "fine"},
    ]}
    (tmp_path / "in.json").write_text(json.dumps(doc))
    report = stash.import_from(tmp_path / "in.json")
    assert report["added"] == ["ok"]
    assert report["skipped"] == [
        "gone: /nowhere/x is not on this machine",
        "blob: unsupported type 'json'",
        "bad id: missing or invalid id",
    ]


def test_import_refuses_other_formats(stash, tmp_path):
    (tmp_path / "wf.json").write_text(json.dumps({"format": "aotn-workflow/1"}))
    with pytest.raises(StashError, match="not a Stash export"):
        stash.import_from(tmp_path / "wf.json")


# -- accepted_types --------------------------------------------------------------

def test_accepted_types_one_rule():
    assert accepted_types({"type": "string", "path_hint": "file"}) == {"file"}
    assert accepted_types({"type": "string"}) == {"string"}
    assert accepted_types({"type": "multiline"}) == {"string"}
    for field in ({"type": "boolean"}, {"type": "select"}, {"type": "integer"}, {"type": "object_list"}):
        assert accepted_types(field) == set(), field
    # A declared data_type wins over the hint (STASH_PROPOSAL.md §9 note 2).
    assert accepted_types({"type": "string", "path_hint": "file", "data_type": "string"}) == {"string"}


def test_real_file_path_fields_accept_file_entries():
    from backend.node_factory import NodeFactory

    found = {}
    for meta in NodeFactory().get_node_types_metadata():
        for key, field in (meta.get("config_schema") or {}).items():
            if field.get("path_hint") == "file":
                found[(meta["type"], key)] = accepted_types(field)
    assert found and all(types == {"file"} for types in found.values()), found


# -- aotn stash (S3b) -------------------------------------------------------------

def _cli(*argv):
    import io

    import aotn_stash

    out = io.StringIO()
    code = aotn_stash.main(list(argv), stdout=out)
    return code, out.getvalue()


def test_cli_add_list_rename_rm(stash, files):
    plain, spaced = files
    code, text = _cli("add", f"'{spaced}' {plain} /nowhere/x.txt")
    assert code == 0
    assert "Added file 'q1 notes'" in text and "Added file 'march'" in text
    assert _cli("add", "a sentence, not a path")[1].startswith("Added text 'a sentence, not a'")
    assert "a sentence" not in _cli("list", "--type", "file")[1]
    assert "Not stored: /nowhere/x.txt: not found on this machine" in text
    code, text = _cli("list")
    assert code == 0 and "march" in text and text.count("/data/") == 2  # paths keep their end
    assert _cli("rename", "march", "March report")[0] == 0
    code, text = _cli("rm", "march report")
    assert code == 0 and text.startswith("Removed 'March report'")
    assert [e["name"] for e in stash.list_entries()] == ["a sentence, not a", "q1 notes"]


def test_cli_refusals_exit_1_and_suggest_text(stash):
    code, text = _cli("add", "/nowhere/x.txt")
    assert code == 1 and "Use --text to store it as text instead." in text
    assert _cli("add", "/nowhere/x.txt", "--text")[0] == 0
    code, text = _cli("rm", "missing")
    assert code == 1 and text.startswith("Refused: No Stash entry")


def test_cli_add_with_name_and_json(stash, files):
    _, spaced = files
    code, text = _cli("--json", "add", str(spaced), "--name", "notes")
    data = json.loads(text)
    assert code == 0 and data["ok"] and data["added"][0]["name"] == "notes"
    code, text = _cli("--json", "add", "sk-abcdefghijklmnopqrstuv", "--name", "k")
    assert code == 0 and json.loads(text)["warnings"]


def test_cli_export_import(stash, files, tmp_path):
    plain, _ = files
    _cli("add", str(plain))
    code, text = _cli("export", str(tmp_path / "s.json"))
    assert code == 0 and text.startswith("Exported 1 entry")
    stash.remove("march")
    code, text = _cli("import", str(tmp_path / "s.json"))
    assert code == 0 and text.startswith("Imported 1, skipped 0")


def test_aotn_dispatches_stash(stash, capsys):
    import main

    assert main.main(["stash", "list"]) == 0
    assert "The Stash is empty" in capsys.readouterr().out


@pytest.mark.skipif(not __import__("os").environ.get("WSL_DISTRO_NAME"), reason="WSL only")
def test_windows_drop_into_wsl_resolves(tmp_path, stash):
    # A real Windows Terminal drop: a quoted Windows path to this WSL file.
    import subprocess

    target = tmp_path / "from windows.txt"
    target.write_text("x")
    windows = subprocess.run(["wslpath", "-w", str(target)], capture_output=True,
                             text=True, check=True).stdout.strip()
    result = parse_paste(f'"{windows}"')
    assert result.files and result.files[0].resolve() == target.resolve()


# -- duplicates (owner, 2026-10-17: same reference, no second entry) ---------------

def test_the_same_file_is_not_added_twice(stash, files):
    from backend.stash_manager import StashDuplicate

    plain, _ = files
    first = stash.add_file(str(plain))
    with pytest.raises(StashDuplicate) as caught:
        stash.add_file(f"'{plain}'")  # same file, other spelling
    assert caught.value.entry["id"] == first["id"]
    assert str(caught.value) == "Duplicate found: already in the Stash as 'march'"
    assert len(stash.list_entries()) == 1


def test_the_same_text_is_not_added_twice(stash):
    from backend.stash_manager import StashDuplicate

    stash.add_text("Plain British English", name="tone")
    with pytest.raises(StashDuplicate):
        stash.add_text("  Plain British English \n", name="voice")
    assert [e["name"] for e in stash.list_entries()] == ["tone"]


def test_a_paste_reports_duplicates_and_adds_the_rest(stash, files):
    from backend.stash_manager import duplicates_message

    plain, spaced = files
    existing = stash.add_file(str(plain))
    entries, result = stash.add_paste(f"'{spaced}' {plain}")
    assert [e["name"] for e in entries] == ["q1 notes"]
    assert [e["id"] for e in result.duplicates] == [existing["id"]]
    assert duplicates_message(result.duplicates) == "Duplicate found: 'march'"
    _, again = stash.add_paste(f"'{spaced}' {plain}")
    assert duplicates_message(again.duplicates) == "2 duplicates found: 'q1 notes', 'march'"


def test_a_different_file_with_the_same_name_is_named_after_its_folder(stash, tmp_path):
    first = tmp_path / "reports" / "march.csv"
    second = tmp_path / "archive" / "march.csv"
    for path in (first, second):
        path.parent.mkdir()
        path.write_text("x")
    assert stash.add_file(str(first))["name"] == "march"
    assert stash.add_file(str(second))["name"] == "march (archive)"


def test_import_skips_values_already_in_the_stash(stash, tmp_path):
    stash.add_text("fine", name="mine")
    doc = {"format": FORMAT, "entries": [
        {"id": "stash_dddddddddddd", "name": "theirs", "type": "string", "value": "fine"}]}
    (tmp_path / "in.json").write_text(json.dumps(doc))
    report = stash.import_from(tmp_path / "in.json")
    assert report == {"added": [], "skipped": ["theirs: duplicate of 'mine'"]}


def test_cli_reports_a_duplicate_without_failing(stash, files):
    plain, _ = files
    _cli("add", str(plain))
    code, text = _cli("add", str(plain))
    assert code == 0 and text.strip() == "Duplicate found: 'march'"
    assert len(stash.list_entries()) == 1

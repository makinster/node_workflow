"""Command-line Stash: ``aotn stash list|add|rename|rm|export|import``, and
``aotn stash saved list|show|set|forget`` for saved values (C2).

A thin adapter over ``backend/stash_manager.py`` (Stash S1 + S3b). Prints a
readable summary, or JSON with ``--json``. Exit code 0 on success, 1 when
something was refused (a missing file, a taken name), 2 for usage errors.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, TextIO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aotn stash",
        description="Machine-local reusable file paths and text (the Stash).",
    )
    parser.add_argument("--data-dir", help="data directory; overrides $AOTN_DATA_DIR")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    sub = parser.add_subparsers(dest="action", required=True)

    listing = sub.add_parser("list", help="list entries")
    listing.add_argument("--type", choices=["file", "string"], help="only one type")

    add = sub.add_parser("add", help="add a file path (or several, as a terminal drop) or text")
    add.add_argument("value", help="a path, a pasted drop of paths, or text with --text")
    add.add_argument("--name", help="entry name (default: the file name or the first words)")
    add.add_argument("--text", action="store_true", help="store the value as text, even if it is a path")

    rename = sub.add_parser("rename", help="rename an entry")
    rename.add_argument("entry", help="entry id or name")
    rename.add_argument("new_name")

    remove = sub.add_parser("rm", help="remove an entry")
    remove.add_argument("entry", help="entry id or name")

    export = sub.add_parser("export", help="write all entries to a JSON file")
    export.add_argument("path")

    imported = sub.add_parser("import", help="merge entries from an export")
    imported.add_argument("path")

    # Saved values (C2): what workflows keep for their next run.
    saved = sub.add_parser("saved", help="values workflows keep between runs")
    saved_sub = saved.add_subparsers(dest="saved_action", required=True)
    saved_list = saved_sub.add_parser("list", help="list saved values")
    saved_list.add_argument("--workflow", help="only this workflow's values")
    for verb, text in (("show", "show one value in full"), ("set", "set a value"),
                       ("forget", "forget a value")):
        one = saved_sub.add_parser(verb, help=text)
        one.add_argument("name")
        if verb == "set":
            one.add_argument("value", help="typed as --type (JSON for var and file)")
            one.add_argument("--type", choices=["string", "number", "bool", "var", "file"],
                             help="default: the saved value's type, else string")
        where = one.add_mutually_exclusive_group(required=True)
        where.add_argument("--workflow", help="the workflow the value belongs to")
        where.add_argument("--all", action="store_true", help="a value kept for all workflows")
    return parser


def main(argv: Optional[List[str]] = None, stdout: Optional[TextIO] = None) -> int:
    """Entry point for ``aotn stash``; returns the exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    if args.data_dir:
        # Data paths resolve once, when the backend is first imported.
        loaded = sys.modules.get("backend.persistence")
        wanted = os.path.realpath(os.path.expanduser(args.data_dir))
        if loaded is not None and os.path.realpath(loaded.DATA_DIR) != wanted:
            parser.error("--data-dir must be set before the backend is loaded")
        os.environ["AOTN_DATA_DIR"] = wanted

    if args.action == "saved":
        from backend.saved_values import SavedValuesError

        try:
            data, text = _run_saved(args)
        except SavedValuesError as exc:
            _emit(out, args.json, {"ok": False, "error": str(exc)}, f"Refused: {exc}")
            return 1
        _emit(out, args.json, data, text)
        return 0

    from backend.stash_manager import StashDuplicate, StashError, StashManager, duplicates_message

    stash = StashManager()
    try:
        data, text = _run(stash, args)
    except StashDuplicate as exc:
        message = duplicates_message([exc.entry])
        _emit(out, args.json, {"ok": True, "added": [], "duplicates": [exc.entry]}, message)
        return 0
    except StashError as exc:
        _emit(out, args.json, {"ok": False, "error": str(exc)}, f"Refused: {exc}")
        return 1
    _emit(out, args.json, data, text)
    return 0 if data.get("ok", True) else 1


def _run(stash, args: argparse.Namespace) -> tuple[Dict[str, Any], str]:
    from backend.stash_manager import type_word

    if args.action == "list":
        entries = stash.list_entries(args.type)
        return {"ok": True, "entries": entries}, _list_text(entries)
    if args.action == "add":
        result = None
        if args.text:
            entries, rejected = [stash.add_text(args.value, args.name)], []
        elif args.name:
            # A chosen name names one thing: the value must be a single file.
            entries, rejected = [_add_one(stash, args.value, args.name)], []
        else:
            entries, result = stash.add_paste(args.value)
            rejected = result.rejected
        from backend.stash_manager import duplicates_message

        duplicates = result.duplicates if not (args.text or args.name) else []
        warnings = [w for e in entries for w in stash.warnings_for(e)]
        lines = [f"Added {type_word(e['type'])} '{e['name']}' ({e['id']})" for e in entries]
        if duplicates:
            lines.append(duplicates_message(duplicates))
        lines += [f"Not stored: {r.piece}: {r.reason}" for r in rejected]
        if rejected and not entries:
            lines.append("Use --text to store it as text instead.")
        lines += [f"Warning: {w}" for w in warnings]
        data = {"ok": bool(entries or duplicates), "added": entries, "duplicates": duplicates,
                "warnings": warnings,
                "rejected": [{"piece": r.piece, "reason": r.reason} for r in rejected]}
        return data, "\n".join(lines)
    if args.action == "rename":
        entry = stash.rename(args.entry, args.new_name)
        return {"ok": True, "entry": entry}, f"Renamed to '{entry['name']}' ({entry['id']})"
    if args.action == "rm":
        entry = stash.remove(args.entry)
        return {"ok": True, "removed": entry}, f"Removed '{entry['name']}' ({entry['id']})"
    if args.action == "export":
        warnings = stash.export_to(args.path)
        count = len(stash.list_entries())
        text = "\n".join([f"Exported {count} entr{'y' if count == 1 else 'ies'} to {args.path}"]
                         + [f"Warning: {w}" for w in warnings])
        return {"ok": True, "count": count, "warnings": warnings}, text
    report = stash.import_from(args.path)
    lines = [f"Imported {len(report['added'])}, skipped {len(report['skipped'])}"]
    lines += [f"  added: {line}" for line in report["added"]]
    lines += [f"  skipped: {line}" for line in report["skipped"]]
    return {"ok": True, **report}, "\n".join(lines)


def _run_saved(args: argparse.Namespace) -> tuple[Dict[str, Any], str]:
    from backend import saved_values as saved

    store = saved.SavedValues()
    if args.saved_action == "list":
        values = store.list_values()
        if args.workflow:
            values = [v for v in values if saved.place_label(v["place"]) == args.workflow.strip()]
        if not values:
            return {"ok": True, "values": []}, "Nothing is saved yet."
        lines, shown = [], None
        for value in values:
            label = saved.place_label(value["place"])
            if label != shown:
                lines.append(label)
                shown = label
            lines.append(f"  {value['name']:<22} {'[' + value['type'] + ']':<9} "
                         f"{saved.preview(value, 36):<38} {value['updated']}")
        return {"ok": True, "values": values}, "\n".join(lines)
    place = saved.all_place() if args.all else saved.workflow_place(args.workflow)
    where = saved.place_label(place)
    if args.saved_action == "show":
        value = store.get(place, args.name)
        if value is None:
            raise saved.SavedValuesError(f"Nothing is saved as '{args.name}' in {where}", "not_saved")
        return {"ok": True, "value": value}, json.dumps(value, indent=2, ensure_ascii=False)
    if args.saved_action == "set":
        current = store.get(place, args.name)
        value_type = args.type or (current["type"] if current else "string")
        record = store.save(place, args.name, saved.parse_typed(args.value, value_type),
                            {"node": "", "node_id": "", "run_id": "", "from": "command line"})
        return {"ok": True, "value": record}, f"Saved '{record['name']}' in {where}"
    record = store.forget(place, args.name)
    return {"ok": True, "forgotten": record}, f"Forgot '{record['name']}' in {where}"


def _add_one(stash, value: str, name: str) -> Dict[str, Any]:
    from backend.paste_parser import parse_paste

    if parse_paste(value).text is not None:
        return stash.add_text(value, name)
    return stash.add_file(value, name)


def _list_text(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return "The Stash is empty. Add one with: aotn stash add <path>"
    from backend.stash_manager import preview, type_word

    return "\n".join(f"  {e['name']:<24} {'[' + type_word(e['type']) + ']':<7} {preview(e)}"
                     for e in entries)


def _emit(out: TextIO, as_json: bool, data: Any, text: str) -> None:
    out.write((json.dumps(data, indent=2, default=str) if as_json else text) + "\n")

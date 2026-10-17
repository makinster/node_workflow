"""Command-line Stash: ``aotn stash list|add|rename|rm|export|import``.

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
    listing.add_argument("--type", choices=["file", "text"], help="only one type")

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

    from backend.stash_manager import StashError, StashManager

    stash = StashManager()
    try:
        data, text = _run(stash, args)
    except StashError as exc:
        _emit(out, args.json, {"ok": False, "error": str(exc)}, f"Refused: {exc}")
        return 1
    _emit(out, args.json, data, text)
    return 0 if data.get("ok", True) else 1


# What people read; JSON keeps the canonical data type names.
_TYPE_LABELS = {"file": "file", "string": "text"}


def _run(stash, args: argparse.Namespace) -> tuple[Dict[str, Any], str]:
    if args.action == "list":
        entries = stash.list_entries({"text": "string"}.get(args.type, args.type))
        return {"ok": True, "entries": entries}, _list_text(entries)
    if args.action == "add":
        if args.text:
            entries, rejected = [stash.add_text(args.value, args.name)], []
        elif args.name:
            # A chosen name names one thing: the value must be a single file.
            entries, rejected = [_add_one(stash, args.value, args.name)], []
        else:
            entries, result = stash.add_paste(args.value)
            rejected = result.rejected
        warnings = [w for e in entries for w in stash.warnings_for(e)]
        lines = [f"Added {_TYPE_LABELS[e['type']]} '{e['name']}' ({e['id']})" for e in entries]
        lines += [f"Not stored: {r.piece}: {r.reason}" for r in rejected]
        if rejected and not entries:
            lines.append("Use --text to store it as text instead.")
        lines += [f"Warning: {w}" for w in warnings]
        data = {"ok": bool(entries), "added": entries, "warnings": warnings,
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


def _add_one(stash, value: str, name: str) -> Dict[str, Any]:
    from backend.paste_parser import parse_paste

    if parse_paste(value).text is not None:
        return stash.add_text(value, name)
    return stash.add_file(value, name)


def _list_text(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return "The Stash is empty. Add one with: aotn stash add <path>"
    from backend.file_refs import reference_path

    lines = []
    for entry in entries:
        shown = reference_path(entry["value"]) if entry["type"] == "file" else entry["value"]
        shown = " ".join(str(shown).split())
        if len(shown) > 60:
            # A path keeps its end (the file name); text keeps its start.
            shown = "..." + shown[-57:] if entry["type"] == "file" else shown[:57] + "..."
        lines.append(f"  {entry['name']:<24} {_TYPE_LABELS[entry['type']]:<5} {shown}")
    return "\n".join(lines)


def _emit(out: TextIO, as_json: bool, data: Any, text: str) -> None:
    out.write((json.dumps(data, indent=2, default=str) if as_json else text) + "\n")

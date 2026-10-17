"""Command-line authoring: ``aotn nodes``, ``describe``, ``build``, ``inspect``.

A thin adapter over ``backend/authoring.py``. Every command prints a readable
summary, or JSON with ``--json`` (for agents and scripts). ``build`` writes a
new saved workflow only when every check passes; ``--check`` builds and checks
without writing. Running a workflow stays ``aotn run``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, TextIO

COMMANDS = ("nodes", "describe", "build", "inspect")


def build_parser(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"aotn {command}")
    if command == "nodes":
        parser.description = "List the node types a workflow can use."
    elif command == "describe":
        parser.description = "Describe a node type: config fields, ports, Vault effects, errors."
        parser.add_argument("node_type", help="node type, e.g. sleep_node")
        parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                            help="config override (repeatable; VALUE is JSON when it parses, else text)")
    elif command == "inspect":
        parser.description = ("Explain a saved workflow: execution paths, Vault writers and "
                              "readers with ordering, data-flow types, unchecked keys, validation.")
        parser.add_argument("workflow", help="saved workflow id or name, or a workflow .json file")
    else:
        parser.description = "Build a workflow from an aotn-workflow/1 spec and save it."
        parser.add_argument("spec", help="path to the spec .json file, or - for stdin")
        parser.add_argument("--check", action="store_true",
                            help="build and check without writing a saved workflow")
    parser.add_argument("--data-dir", help="data directory; overrides $AOTN_DATA_DIR")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    return parser


def main(command: str, argv: Optional[List[str]] = None,
         stdin: Optional[TextIO] = None, stdout: Optional[TextIO] = None) -> int:
    """Entry point for one authoring command; returns the exit code."""
    parser = build_parser(command)
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    if args.data_dir:
        # Data paths resolve once, when the backend is first imported.
        loaded = sys.modules.get("backend.persistence")
        wanted = os.path.realpath(os.path.expanduser(args.data_dir))
        if loaded is not None and os.path.realpath(loaded.DATA_DIR) != wanted:
            parser.error("--data-dir must be set before the backend is loaded")
        os.environ["AOTN_DATA_DIR"] = wanted

    # stdout carries only the result (JSON stays parseable); stray backend
    # prints and warnings go to stderr.
    with contextlib.redirect_stdout(sys.stderr):
        return _run(command, args, parser, out, stdin)


def _run(command: str, args: argparse.Namespace, parser: argparse.ArgumentParser,
         out: TextIO, stdin: Optional[TextIO]) -> int:
    from backend import authoring
    from backend.node_factory import NodeFactory

    factory = NodeFactory()
    if command == "nodes":
        rows = authoring.list_node_types(factory)
        _emit(out, args.json, rows, _nodes_text(rows))
        return 0
    if command == "describe":
        try:
            overrides = _parse_sets(args.set)
            description = authoring.describe_node_type(factory, args.node_type, overrides)
        except ValueError as exc:
            parser.error(str(exc))
        _emit(out, args.json, description, _describe_text(description))
        return 0
    if command == "inspect":
        from backend.event_bus import EventBus
        from backend.run_service import WorkflowNotFoundError, resolve_workflow_data
        from backend.workflow_map import WorkflowMap

        try:
            data = resolve_workflow_data(args.workflow)
        except WorkflowNotFoundError as exc:
            parser.error(str(exc))
        workflow_map = WorkflowMap(factory, EventBus())
        workflow_map.load_data(data)
        report = authoring.inspect_workflow(factory, workflow_map)
        _emit(out, args.json, report, _inspect_text(report))
        return 0
    try:
        text = (stdin or sys.stdin).read() if args.spec == "-" else open(args.spec, encoding="utf-8").read()
        spec = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read spec: {exc}")
    report = authoring.build_workflow(factory, spec, write=not args.check)
    _emit(out, args.json, report, _build_text(report, args.check))
    return 0 if report["ok"] else 1


def _parse_sets(pairs: List[str]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"--set needs KEY=VALUE (got {pair!r})")
        try:
            overrides[key.strip()] = json.loads(value)
        except json.JSONDecodeError:
            overrides[key.strip()] = value
    return overrides


def _emit(out: TextIO, as_json: bool, data: Any, text: str) -> None:
    out.write((json.dumps(data, indent=2, default=str) if as_json else text) + "\n")


def _nodes_text(rows: List[Dict[str, Any]]) -> str:
    lines, family = [], None
    for row in rows:
        if row["family"] != family:
            family = row["family"]
            lines.append(f"{family or 'Other'}:")
        lines.append(f"  {row['type']:<24} {row['name']}")
    return "\n".join(lines)


def _describe_text(info: Dict[str, Any]) -> str:
    lines = [f"{info['name']} ({info['type']}) · {info['family']}", info["description"], ""]
    lines.append("Inputs:" if info["inputs"] else "Inputs: none")
    for port in info["inputs"]:
        source = f"  source: {port['source_field']} {port['source_options']}" if port["source_field"] else ""
        lines.append(f"  {port['port']} [{port['data_type']}]{' required' if port['required'] else ''}{source}")
    lines.append("Outputs:")
    for port in info["outputs"]:
        lines.append(f"  {port['port']} [{port['data_type']}]  {port['name']}")
    lines.append("Config:")
    for field in info["fields"]:
        hidden = "" if field["visible"] else "  (hidden with this config)"
        limits = "".join(f" {k}={field[k]}" for k in ("min", "max") if k in field)
        options = f" options={field['options']}" if "options" in field else ""
        lines.append(f"  {field['key']} ({field['type']}{limits}{options}) default={field['default']!r}{hidden}")
    if info["unchecked_keys"]:
        lines.append(f"Unchecked keys (no schema): {', '.join(info['unchecked_keys'])}")
    if info["node_reference_fields"]:
        lines.append(f"Node references (give handles): {', '.join(info['node_reference_fields'])}")
    if info["vault_reads"] or info["vault_writes"]:
        reads = ", ".join(f"{r['source_id']}{'' if r['required'] else ' (optional)'}" for r in info["vault_reads"])
        writes = ", ".join(f"{w['key']} [{w['data_type']}]" for w in info["vault_writes"])
        lines.append(f"Vault: reads {reads or '-'}; writes {writes or '-'}")
    if info["errors"]:
        lines.append("Errors: " + ", ".join(str(e.get("code")) for e in info["errors"]))
    return "\n".join(lines)


def _build_text(report: Dict[str, Any], check_only: bool) -> str:
    lines = []
    if report["ok"]:
        if check_only:
            lines.append(f"OK (checked, not written): {report.get('name')}")
        else:
            lines.append(f"Saved {report.get('name')!r} as {report.get('workflow_id')}")
            lines.append(f"  {report.get('path')}")
    else:
        lines.append("Not written: fix the errors below.")
    for diagnostic in report["diagnostics"]:
        where = f"[{diagnostic['node']}] " if diagnostic.get("node") else ""
        lines.append(f"  {diagnostic['level']}: {where}{diagnostic['code']}: {diagnostic['message']}")
    if report.get("nodes"):
        lines.append("Nodes: " + ", ".join(f"{h}={i}" for h, i in report["nodes"].items()))
    return "\n".join(lines)


def _inspect_text(report: Dict[str, Any]) -> str:
    lines = [f"{report['name']} ({report['workflow_id']})", "", "Execution:"]
    lines += [f"  {line}" for line in report["execution"]]
    if report["vault"]:
        lines += ["", "Vault:"]
        for entry in report["vault"]:
            writers = ", ".join(f"{w['name']} [{w['data_type']}]" for w in entry["writers"]) or "no writer"
            lines.append(f"  {entry['key']}: written by {writers}")
            for reader in entry["readers"]:
                need = "required" if reader["required"] else "optional"
                lines.append(f"    read by {reader['name']} ({need}): {reader['order']}")
    flows = [f for f in report["data_flow"] if f["status"] in ("mismatch", "unchecked")]
    if flows:
        lines += ["", "Data flow (unchecked or mismatched):"]
        for flow in flows:
            lines.append(f"  {flow['from_name']} -> {flow['to_name']}.{flow['port']}: "
                         f"sends {'/'.join(flow['sends'])}, expects {flow['expects']}: {flow['status']}")
    if report["unchecked"]:
        lines += ["", "Config the contract cannot check:"]
        for item in report["unchecked"]:
            lines.append(f"  {item['name']}: {', '.join(item['keys'])}")
    lines += ["", "Validation:" if report["validation"] else "Validation: clean"]
    for issue in report["validation"]:
        where = f"{issue['name']}: " if issue.get("name") else ""
        lines.append(f"  {issue['level']}: {where}{issue['code']}: {issue['message']}")
    return "\n".join(lines)

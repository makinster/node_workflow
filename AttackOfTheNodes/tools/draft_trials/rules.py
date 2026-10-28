"""Bounded pure evaluator for the frozen cases. Never executes draft node code.

Unsupported forms fail with a rule id; adding equivalents requires versioning
this oracle, rather than weakening expectations after a generated failure.
"""

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from string import Formatter

from .cases import PALETTE, fixture_variants


class RuleFailure(ValueError):
    pass


@dataclass
class Value:
    data: object
    expression: tuple = ()

    def __post_init__(self):
        if not self.expression:
            self.expression = ("literal", self.data)


def safe_path(raw, root):
    if (
        not isinstance(raw, str)
        or not Path(raw).is_absolute()
        or any(character in raw for character in "{}\x00")
    ):
        raise RuleFailure("path must be a literal absolute path")
    path = Path(raw).resolve()
    if not path.is_relative_to(Path(root).resolve()) or path == Path(root).resolve():
        raise RuleFailure("path escapes case root (including symlinks)")
    return path


def project(expression, key):
    if expression[0] == "file_reference" and key == "path":
        return ("saved_path", *expression[1:])
    return ("project", key, expression)


def format_value(template, values):
    """Preserve a whole value only for one unmodified field, never substrings.

    Presence of a source token is insufficient: a partial field plus literal
    answer text is a different expression from that source's transformed value.
    """
    fields = []
    for _, field, specification, conversion in Formatter().parse(template):
        if field is None:
            continue
        if (
            not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(?:\[[A-Za-z_0-9-]+\])*", field)
            or specification
            or conversion
        ):
            raise RuleFailure("unsupported format field")
        key = field.split("[")[0]
        if key not in values:
            raise RuleFailure("missing template value " + key)
        expression = values[key].expression
        for part in re.findall(r"\[([^]]+)\]", field):
            expression = project(expression, part)
        fields.append((field, expression))
    rendered = template.format_map({key: value.data for key, value in values.items()})
    if not fields:
        return Value(rendered)
    if len(fields) == 1 and template == "{" + fields[0][0] + "}":
        return Value(rendered, fields[0][1])
    return Value(rendered, ("format", template, tuple(fields)))


def effective_nodes(spec):
    from backend.node_factory import NodeFactory

    factory = NodeFactory()
    return {
        h: dict(
            node,
            config={
                **deepcopy(factory.metadata_for_type(node["type"])["default_config"]),
                **node.get("config", {}),
            },
        )
        for h, node in spec["nodes"].items()
    }


def safety(spec, case):
    """Inspect ALL nodes, including error routes, before any target execution."""
    if spec.get("format") != "aotn-workflow/1" or spec.get("callable"):
        raise RuleFailure("unsupported spec/callable")
    if len(spec.get("nodes", {})) > 64:
        raise RuleFailure("too many nodes")
    if any(n.get("type") not in PALETTE for n in spec["nodes"].values()):
        raise RuleFailure("outside 12-type palette")
    nodes = effective_nodes(spec)
    out = defaultdict(list)
    for edge in spec["connections"]:
        out[edge["from"]].append(edge["to"])
    if any(len(targets) > 1 for targets in out.values()):
        raise RuleFailure("ordinary output fan-out")
    reads = {
        4: "agenda.txt",
        5: "agenda.txt",
        9: "note-source.txt",
        10: "raw-notes.txt",
    }
    writes = {
        5: "agenda-copy.txt",
        6: "note.txt",
        9: "clean-note.txt",
        10: "tidy-notes.txt",
    }
    for h, node in nodes.items():
        t = node["type"]
        c = node["config"]
        if c.get("membank_inputs") or c.get("transient_outputs"):
            raise RuleFailure("legacy source/routing overrides need review")
        if c.get("node_errors") or c.get("breakpoint"):
            raise RuleFailure("unsupported recovery/breakpoint")
        if t == "start_node" and (c.get("rows") or c.get("no_inputs")):
            raise RuleFailure("unsupported Start contract")
        if t == "text_output_node" and c.get("request_user_input"):
            raise RuleFailure("legacy output prompt needs review")
        if t == "branch_node":
            if (
                case["id"] != 8
                or c.get("branch_count") != 2
                or c.get("branch_payload_sources")
                or c.get("condition", "always_branch") != "always_branch"
            ):
                raise RuleFailure("unsupported branch behavior")
        if t == "conditional_node":
            if (
                case["id"] not in (7, 9)
                or c["condition_type"] != "equals"
                or c["left_value_source"] != "input"
                or c["right_value"] != ("yes" if case["id"] == 7 else "")
            ):
                raise RuleFailure("wrong conditional comparison/source")
        if t == "user_text_input_node":
            if case["id"] not in (3, 6, 7, 8):
                raise RuleFailure("unrequested runtime prompt")
            if not re.search(
                (
                    "continue"
                    if case["id"] == 7
                    else "phrase" if case["id"] == 8 else "note"
                ),
                c["prompt"],
                re.I,
            ):
                raise RuleFailure("wrong prompt subject")
        if (
            t == "text_transform_node"
            and c["operation"] not in case["required_operations"]
        ):
            raise RuleFailure("unrequested transform")
        if t == "file_reader_node":
            if c["input_source"] != "Configured" or case["id"] not in reads:
                raise RuleFailure("unresolved/unrequested reader")
            path = safe_path(c["file_path"], case["root"])
            if path != Path(case["root"]) / reads[case["id"]]:
                raise RuleFailure("wrong read path")
        if t == "file_output_node":
            if c["file_path_source"] != "Configured" or case["id"] not in writes:
                raise RuleFailure("unresolved/unrequested writer")
            path = safe_path(c["file_path"], case["root"])
            if path != Path(case["root"]) / writes[case["id"]]:
                raise RuleFailure("wrong write path")
            if (
                c["write_mode"] != "Create unique"
                or any(
                    c.get(k)
                    for k in (
                        "binary_content",
                        "interpret_newlines",
                        "open_after_write",
                        "close_on_run_end",
                        "dead_drop_passthrough",
                    )
                )
                or not c["transient_output"]
            ):
                raise RuleFailure("unsafe writer flags")
    if case["id"] == 8 and not any(n["type"] == "branch_node" for n in nodes.values()):
        raise RuleFailure("parallel node required")
    return nodes, out


def evaluate(spec, case, variant):
    nodes, outgoing = safety(spec, case)
    root = Path(case["root"])
    vault = {}
    outputs = []
    writes = []
    prompts = []
    visited = []
    ends = []
    answers = iter(variant["answers"])
    pending = [
        (handle, Value(""), frozenset(), ())
        for handle, node in nodes.items()
        if node["type"] == "start_node"
    ]
    if len(pending) != 1:
        raise RuleFailure("one Start required")

    def source(config, port, incoming):
        mode = config.get(port + "_source", "Upstream payload")
        if mode == "Vault":
            key = config.get(port + "_vault_key", "")
            if key not in vault:
                raise RuleFailure("Vault read without preceding writer")
            return vault[key]
        if mode == "Configured":
            return Value(config.get(port, ""))
        if mode != "Upstream payload":
            raise RuleFailure("unknown input source")
        return incoming

    while pending:
        handle, value, ancestors, controls = pending.pop()
        if handle in ancestors:
            raise RuleFailure("cycle")
        visited.append(handle)
        config = nodes[handle]["config"]
        kind = nodes[handle]["type"]
        port = "default"
        ancestors = ancestors | {handle}
        if len(visited) > 128:
            raise RuleFailure("step bound exceeded")
        if kind == "start_node":
            value = Value(config["greeting"])
        elif kind in ("end_node", "branch_end_node"):
            if kind != "end_node":
                raise RuleFailure("route must end at End")
            ends.append(handle)
            continue
        elif kind == "user_text_input_node":
            try:
                answer = next(answers)
            except StopIteration:
                raise RuleFailure("extra prompt") from None
            prompts.append(config["prompt"])
            value = Value(answer, ("answer", handle))
        elif kind == "file_reader_node":
            filename = Path(config["file_path"]).name
            if filename not in variant["files"]:
                return dict(
                    outputs=outputs,
                    writes=writes,
                    prompts=prompts,
                    visited=visited,
                    error=True,
                )
            value = Value(
                variant["files"][filename],
                ("file", str(safe_path(config["file_path"], root)), handle),
            )
        elif kind == "text_transform_node":
            operation = config["operation"]
            functions = {
                "uppercase": str.upper,
                "lowercase": str.lower,
                "strip": str.strip,
            }
            value = Value(
                functions[operation](str(value.data or "")),
                ("operation", operation, value.expression),
            )
        elif kind == "conditional_node":
            port = "true" if str(value.data) == config["right_value"] else "false"
            controls += (dict(handle=handle, port=port, expression=value.expression),)
        elif kind == "branch_node":
            # Only guaranteed preceding writes can be read safely by both paths.
            if any(
                (
                    node["config"].get("vault_write")
                    or node["config"].get("membank_outputs")
                )
                and key not in ancestors
                for key, node in nodes.items()
            ):
                raise RuleFailure("parallel Vault writes need review")
            for branch in ("path_a", "path_b"):
                target = outgoing.get(handle + "." + branch)
                if not target:
                    raise RuleFailure("missing branch")
                pending.append((target[0].split(".")[0], value, ancestors, controls))
            continue
        elif kind == "concat_node":
            value = format_value(config["template"], dict(vault, input=value))
        elif kind == "json_path_node":
            data = json.loads(value.data) if isinstance(value.data, str) else value.data
            expression = value.expression
            for part in config["path"].split("."):
                if not part:
                    continue
                if isinstance(data, dict):
                    data = data.get(part, config["default_value"])
                else:
                    data = data[int(part)]
                expression = project(expression, part)
            value = Value(data, expression)
        elif kind == "text_output_node":
            value = source(config, "input", value)
            body = format_value(config["template"], {"input": value})
            outputs.append(
                dict(
                    handle=handle,
                    body=body.data,
                    expression=body.expression,
                    controls=controls,
                )
            )
            value = Value(
                "[" + config["label"] + "] " + body.data,
                ("label", config["label"], body.expression),
            )
        elif kind == "file_output_node":
            content = source(config, "content", value)
            destination = str(safe_path(config["file_path"], root))
            path = str(
                root
                / (
                    Path(destination).stem
                    + " (trial unique)"
                    + Path(destination).suffix
                )
            )
            writes.append(
                dict(
                    handle=handle,
                    path=path,
                    requested=Path(destination).name,
                    content=content.data,
                    expression=content.expression,
                    controls=controls,
                )
            )
            value = Value(
                {"path": path, "kind": "file"},
                ("file_reference", handle, destination, content.expression),
            )
        else:
            raise RuleFailure("unsupported type")
        if config.get("vault_write"):
            vault[config["vault_write_key"]] = value
        for declaration in config.get("membank_outputs", []):
            vault[declaration.get("output") or declaration["id"]] = value
        if kind == "file_reader_node" and not config["transient_output"]:
            value = Value(None)
        target = outgoing.get(handle + "." + port)
        if not target:
            raise RuleFailure("nonterminal route ends before End")
        pending.append((target[0].split(".")[0], value, ancestors, controls))
    try:
        next(answers)
        raise RuleFailure("missing prompt")
    except StopIteration:
        pass
    if not ends:
        raise RuleFailure("no End")
    return dict(
        outputs=outputs, writes=writes, prompts=prompts, visited=visited, error=False
    )


def source_matches(expression, source, case):
    if source == "heading":
        return expression == ("literal", "  Monday Update  ")
    if source == "answer":
        return len(expression) == 2 and expression[0] == "answer"
    filename = {
        4: "agenda.txt",
        5: "agenda.txt",
        9: "note-source.txt",
        10: "raw-notes.txt",
    }[case["id"]]
    return (
        len(expression) == 3
        and expression[0] == "file"
        and expression[1] == str(Path(case["root"]) / filename)
    )


def chain_matches(expression, operations, source, case):
    # Peel exactly the requested operations, in order, down to the WHOLE source.
    for operation in reversed(operations):
        if len(expression) != 3 or expression[:2] != ("operation", operation):
            return False
        expression = expression[2]
    return source_matches(expression, source, case)


def control_matches(witness, port, operations, source, case):
    return any(
        control["port"] == port
        and chain_matches(control["expression"], operations, source, case)
        for control in witness["controls"]
    )


def provenance_matches(result, case, variant):
    """Separate data lineage from control dependence and literal status messages."""
    if result["error"]:
        return True
    number = case["id"]
    outputs = result["outputs"]
    writes = result["writes"]
    if number == 1:
        # The requested message itself is a valid literal in this one case.
        return all(output["expression"] == ("literal", "Ready") for output in outputs)
    if number == 2:
        return all(
            any(
                chain_matches(output["expression"], order, "heading", case)
                for order in (("strip", "lowercase"), ("lowercase", "strip"))
            )
            for output in outputs
        )
    if number in (3, 4):
        operations = ("uppercase",) if number == 3 else ()
        source = "answer" if number == 3 else "file"
        return all(
            chain_matches(output["expression"], operations, source, case)
            for output in outputs
        )
    if number == 7:
        port = "true" if variant["answers"][0] == "yes" else "false"
        text = "Continuing" if port == "true" else "Stopping"
        return all(
            output["expression"] == ("literal", text)
            and control_matches(output, port, (), "answer", case)
            for output in outputs
        )
    if number == 8:
        actual = []
        sources = []
        for output in outputs:
            for operation in ("uppercase", "lowercase"):
                if chain_matches(output["expression"], (operation,), "answer", case):
                    actual.append(operation)
                    sources.append(output["expression"][2])
                    break
            else:
                return False
        return (
            Counter(actual) == Counter(("uppercase", "lowercase"))
            and len(set(sources)) == 1
        )
    if number == 9 and not writes:
        return all(
            output["expression"] == ("literal", "Empty note")
            and control_matches(output, "true", ("strip",), "file", case)
            for output in outputs
        )
    operations = {
        5: (),
        6: ("uppercase",),
        9: ("strip", "uppercase"),
        10: ("strip", "lowercase"),
    }[number]
    source = "answer" if number == 6 else "file"
    for write in writes:
        if not chain_matches(write["expression"], operations, source, case):
            return False
        if number == 9 and not control_matches(
            write, "false", ("strip",), "file", case
        ):
            return False
    # Display the same writer's actual reference path, not a reconstructed path.
    if len(writes) != 1:
        return False
    write = writes[0]
    destination = str(Path(case["root"]) / write["requested"])
    path_expression = ("saved_path", write["handle"], destination, write["expression"])
    return all(output["expression"] == path_expression for output in outputs)


def check_rules(spec, case):
    from backend.authoring import check_workflow_spec
    from backend.node_factory import NodeFactory

    rows = []

    def record(rule, ok, evidence):
        rows.append(
            dict(
                id=str(case["id"]) + "." + rule,
                result="pass" if ok else "fail",
                evidence=evidence,
            )
        )

    try:
        structural = check_workflow_spec(NodeFactory(), spec)
        record(
            "structure",
            structural["ok"] and not structural["diagnostics"],
            structural["diagnostics"],
        )
        safety(spec, case)
        record("path_type_safety", True, "All nodes, including error routes, inspected")
        for variant in fixture_variants(case["id"]):
            result = evaluate(spec, case, variant)
            writes = result["writes"]
            outputs = result["outputs"]
            expected = [
                writes[0]["path"] if x == "@path" and writes else x
                for x in variant["outputs"]
            ]
            ok = result["error"] == variant["error"] and Counter(
                o["body"] for o in outputs
            ) == Counter(expected)
            ok = (
                ok
                and {w["requested"]: w["content"] for w in writes} == variant["writes"]
                and len(writes) == len(variant["writes"])
            )
            ok = ok and len(result["prompts"]) == len(variant["answers"])
            provenance = provenance_matches(result, case, variant)
            record(
                "provenance." + variant["name"],
                provenance,
                dict(outputs=outputs, writes=writes),
            )
            ok = ok and provenance
            record("semantics." + variant["name"], ok, result)
    except (
        RuleFailure,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
    ) as exc:
        record("bounded_evaluation", False, str(exc))
    return dict(
        result="pass" if rows and all(r["result"] == "pass" for r in rows) else "fail",
        rules=rows,
    )

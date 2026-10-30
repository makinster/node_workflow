"""Frozen ten-case oracle v3. Reference drafts are hand-authored calibration."""

from copy import deepcopy
from pathlib import Path

PALETTE = frozenset(
    "start_node end_node branch_end_node branch_node user_text_input_node text_output_node text_transform_node file_reader_node file_output_node conditional_node concat_node json_path_node".split()
)
REQUESTS = [
    "When I run it, show Ready in the output.",
    "Take the text '  Monday Update  ', remove spaces at the start and end, make it lowercase, and show it.",
    "Ask me for a note each time I run it, make my note uppercase, and show the uppercase note.",
    "Read ROOT/agenda.txt as UTF-8 and show all of its text unchanged.",
    "Copy all text from ROOT/agenda.txt into a new ROOT/agenda-copy.txt. Keep any existing copy unchanged, and show the path that was actually saved.",
    "Ask me for a note, uppercase it, save it as ROOT/note.txt without overwriting an old note, then show the saved path.",
    "Ask me whether to continue. If I type exactly yes, show Continuing. For any other answer, show Stopping. Take only one path.",
    "Ask me for a phrase. On two parallel paths, show one uppercase version and one lowercase version of that same phrase.",
    "Read ROOT/note-source.txt and trim spaces and newlines from both ends. If nothing remains, show Empty note and save nothing. Otherwise uppercase the trimmed text, save a new ROOT/clean-note.txt without replacing an existing file, and show the actual saved path.",
    "Clean up my notes and save the result.",
]
ANSWER = "Use ROOT/raw-notes.txt. Remove whitespace only at the start and end of the whole text, then make it lowercase. Save it as a new ROOT/tidy-notes.txt, keep any older file, and show the actual saved path."
OPERATIONS = {
    2: ["strip", "lowercase"],
    3: ["uppercase"],
    6: ["uppercase"],
    8: ["uppercase", "lowercase"],
    9: ["strip", "uppercase"],
    10: ["strip", "lowercase"],
}


def role(kind, **criteria):
    return dict(type=kind + "_node", **criteria)


def structure(roles, *, before=(), data_from=(), forks=()):
    return dict(
        roles=roles, before=list(before), data_from=list(data_from), forks=list(forks)
    )


# Frozen, handle-independent obligations. A case specifies the work, its data
# producers, and the route where it belongs; the matcher has no case-id logic.
STRUCTURES = {
    1: structure(
        {
            "start": role("start"),
            "message": role("text_output", output_literal="Ready"),
        },
        before=[("start", "message")],
    ),
    2: structure(
        {
            "source": {
                "one_of": [
                    role("start", config={"greeting": "  Monday Update  "}),
                    role("concat", config={"template": "  Monday Update  "}),
                ]
            },
            "strip": role("text_transform", config={"operation": "strip"}),
            "lower": role("text_transform", config={"operation": "lowercase"}),
            "message": role("text_output"),
        },
        data_from=[
            ("source", "strip"),
            ("source", "lower"),
            ("strip", "message"),
            ("lower", "message"),
        ],
    ),
    3: structure(
        {
            "ask": role("user_text_input"),
            "upper": role("text_transform", config={"operation": "uppercase"}),
            "message": role("text_output"),
        },
        data_from=[("ask", "upper"), ("upper", "message")],
    ),
    4: structure(
        {"read": role("file_reader"), "message": role("text_output")},
        data_from=[("read", "message")],
    ),
    5: structure(
        {
            "read": role("file_reader"),
            "write": role("file_output"),
            "path": role("text_output", output_kind="saved_path"),
        },
        data_from=[("read", "write"), ("write", "path")],
    ),
    6: structure(
        {
            "ask": role("user_text_input"),
            "upper": role("text_transform", config={"operation": "uppercase"}),
            "write": role("file_output"),
            "path": role("text_output", output_kind="saved_path"),
        },
        data_from=[("ask", "upper"), ("upper", "write"), ("write", "path")],
    ),
    7: structure(
        {
            "ask": role("user_text_input"),
            "choice": role(
                "conditional",
                config={
                    "condition_type": "equals",
                    "left_value_source": "input",
                    "right_value": "yes",
                },
            ),
            "continue": role("text_output", output_literal="Continuing"),
            "stop": role("text_output", output_literal="Stopping"),
        },
        data_from=[("ask", "choice")],
        forks=[
            dict(
                role="choice",
                ports=["true", "false"],
                work=[["continue"], ["stop"]],
                permutable=False,
            )
        ],
    ),
    8: structure(
        {
            "ask": role("user_text_input"),
            "split": role("branch"),
            "upper": role("text_transform", config={"operation": "uppercase"}),
            "lower": role("text_transform", config={"operation": "lowercase"}),
            "upper_message": role("text_output", output_operation="uppercase"),
            "lower_message": role("text_output", output_operation="lowercase"),
        },
        data_from=[
            ("ask", "split"),
            ("upper", "upper_message"),
            ("lower", "lower_message"),
        ],
        forks=[
            dict(
                role="split",
                ports=["path_a", "path_b"],
                work=[["upper", "upper_message"], ["lower", "lower_message"]],
                permutable=True,
            )
        ],
    ),
    9: structure(
        {
            "read": role("file_reader"),
            "strip": role("text_transform", config={"operation": "strip"}),
            "choice": role(
                "conditional",
                config={
                    "condition_type": "equals",
                    "left_value_source": "input",
                    "right_value": "",
                },
            ),
            "empty": role("text_output", output_literal="Empty note"),
            "upper": role("text_transform", config={"operation": "uppercase"}),
            "write": role("file_output"),
            "path": role("text_output", output_kind="saved_path"),
        },
        data_from=[
            ("read", "strip"),
            ("strip", "choice"),
            ("upper", "write"),
            ("write", "path"),
        ],
        forks=[
            dict(
                role="choice",
                ports=["true", "false"],
                work=[["empty"], ["upper", "write", "path"]],
                permutable=False,
            )
        ],
    ),
    10: structure(
        {
            "read": role("file_reader"),
            "strip": role("text_transform", config={"operation": "strip"}),
            "lower": role("text_transform", config={"operation": "lowercase"}),
            "write": role("file_output"),
            "path": role("text_output", output_kind="saved_path"),
        },
        data_from=[
            ("read", "strip"),
            ("strip", "lower"),
            ("lower", "write"),
            ("write", "path"),
        ],
    ),
}


def case_record(number, root, case_set=1):
    if case_set == 3:
        from .case_set_three import case_record as third
        return third(number, root)
    if case_set == 2:
        from .case_set_two import case_record as second
        return second(number, root)
    if case_set != 1:
        raise ValueError("case_set must be 1, 2 or 3")
    return dict(
        version=3,
        id=number,
        root=str(Path(root).resolve()),
        request=REQUESTS[number - 1].replace("ROOT", str(root)),
        clarification=ANSWER.replace("ROOT", str(root)) if number == 10 else "",
        required_operations=OPERATIONS.get(number, []),
        required_structure=deepcopy(STRUCTURES[number]),
    )


def fixture_variants(number, case_set=1):
    if case_set == 3:
        from .case_set_three import fixture_variants as third
        return third(number)
    if case_set == 2:
        from .case_set_two import fixture_variants as second
        return second(number)
    def v(name, files=None, answers=(), outputs=(), writes=None, error=False):
        return dict(
            name=name,
            files=files or {},
            answers=list(answers),
            outputs=list(outputs),
            writes=writes or {},
            error=error,
        )

    if number == 1:
        return [v("ready", outputs=["Ready"])]
    if number == 2:
        return [v("heading", outputs=["monday update"])]
    if number == 3:
        return [
            v("note", answers=["Meeting at two!"], outputs=["MEETING AT TWO!"]),
            v("unicode", answers=["café"], outputs=["CAFÉ"]),
        ]
    if number == 4:
        return [
            v(
                "unicode",
                {"agenda.txt": "Budget: €20\nBring notes.\n"},
                outputs=["Budget: €20\nBring notes.\n"],
            ),
            v("missing", error=True),
        ]
    if number == 5:
        return [
            v(
                "collision" if c else "new",
                {
                    "agenda.txt": "Line one\nLine two\n",
                    **({"agenda-copy.txt": "KEEP THIS COPY"} if c else {}),
                },
                outputs=["@path"],
                writes={"agenda-copy.txt": "Line one\nLine two\n"},
            )
            for c in [True, False]
        ]
    if number == 6:
        return [
            v(
                "collision",
                {"note.txt": "KEEP OLD NOTE"},
                ["Call Sam\nthen email"],
                ["@path"],
                {"note.txt": "CALL SAM\nTHEN EMAIL"},
            ),
            v(
                "new",
                answers=["different note"],
                outputs=["@path"],
                writes={"note.txt": "DIFFERENT NOTE"},
            ),
        ]
    if number == 7:
        return [
            v(
                "answer-" + str(i),
                answers=[a],
                outputs=["Continuing" if a == "yes" else "Stopping"],
            )
            for i, a in enumerate(["yes", "no", "YES", "yesterday", ""])
        ]
    if number == 8:
        return [
            v("phrase-" + str(i), answers=[a], outputs=[a.upper(), a.lower()])
            for i, a in enumerate(["MiXeD Phrase", "AbC 123"])
        ]
    if number == 9:
        return [
            v(
                "empty",
                {"note-source.txt": " \n\t ", "clean-note.txt": "KEEP ORIGINAL"},
                outputs=["Empty note"],
            ),
            v(
                "nonempty",
                {"note-source.txt": "  Call Ana\n ", "clean-note.txt": "KEEP ORIGINAL"},
                outputs=["@path"],
                writes={"clean-note.txt": "CALL ANA"},
            ),
            v(
                "interior",
                {"note-source.txt": "  a  b  ", "clean-note.txt": "KEEP ORIGINAL"},
                outputs=["@path"],
                writes={"clean-note.txt": "A  B"},
            ),
        ]
    if number == 10:
        return [
            v(
                "clarified",
                {
                    "raw-notes.txt": "  HELLO\nWORLD  \n",
                    "tidy-notes.txt": "KEEP ORIGINAL",
                },
                outputs=["@path"],
                writes={"tidy-notes.txt": "hello\nworld"},
            )
        ]
    raise ValueError("Unknown case")


def good_draft(number, root="ROOT", case_set=1):
    if case_set == 3:
        from .case_set_three import good_draft as third
        return third(number, root)
    if case_set == 2:
        from .case_set_two import good_draft as second
        return second(number, root)
    n = {}
    e = []

    def node(h, t, **c):
        n[h] = {"type": t + "_node", "config": c}

    def edge(a, b, port="default", target="input"):
        e.append({"from": a + "." + port, "to": b + "." + target})

    node("start", "start", greeting="  Monday Update  " if number == 2 else "")
    node("end", "end", record_line=False)
    node("show", "text_output", label="", template="{input}")
    source = "start"
    if number in (3, 6, 7, 8):
        node(
            "ask",
            "user_text_input",
            prompt=(
                "Enter a phrase:"
                if number == 8
                else "Continue?" if number == 7 else "Enter a note:"
            ),
        )
        edge(source, "ask")
        source = "ask"
    if number in (4, 5, 9, 10):
        node(
            "read",
            "file_reader",
            input_source="Configured",
            file_path=root
            + "/"
            + {
                4: "agenda.txt",
                5: "agenda.txt",
                9: "note-source.txt",
                10: "raw-notes.txt",
            }[number],
            transient_output=True,
        )
        edge(source, "read")
        source = "read"
    if number in (2, 9, 10):
        node("strip", "text_transform", operation="strip")
        edge(source, "strip")
        source = "strip"
    if number in (2, 3, 6, 10):
        node(
            "transform",
            "text_transform",
            operation="lowercase" if number in (2, 10) else "uppercase",
        )
        edge(source, "transform")
        source = "transform"
    if number in (7, 9):
        node(
            "if",
            "conditional",
            condition_type="equals",
            left_value_source="input",
            right_value="yes" if number == 7 else "",
        )
        edge(source, "if")
        if number == 7:
            n["show"]["config"]["template"] = "Continuing"
            node("stop", "text_output", label="", template="Stopping")
            edge("if", "show", "true")
            edge("if", "stop", "false")
            edge("stop", "end")
            source = None
        else:
            node("empty", "text_output", label="", template="Empty note")
            edge("if", "empty", "true")
            edge("empty", "end")
            node("upper", "text_transform", operation="uppercase")
            edge("if", "upper", "false")
            source = "upper"
    if number in (5, 6, 9, 10):
        node(
            "write",
            "file_output",
            content_source="Upstream payload",
            file_path_source="Configured",
            file_path=root
            + "/"
            + {
                5: "agenda-copy.txt",
                6: "note.txt",
                9: "clean-note.txt",
                10: "tidy-notes.txt",
            }[number],
            write_mode="Create unique",
            binary_content=False,
            interpret_newlines=False,
            open_after_write=False,
            close_on_run_end=False,
            transient_output=True,
            dead_drop_passthrough=False,
        )
        edge(source, "write", target="content")
        source = "write"
        n["show"]["config"]["template"] = "{input[path]}"
    if number == 8:
        node("parallel", "branch", branch_count=2)
        edge(source, "parallel")
        node("upper", "text_transform", operation="uppercase")
        node("lower", "text_transform", operation="lowercase")
        node("low_show", "text_output", label="", template="{input}")
        edge("parallel", "upper", "path_a")
        edge("parallel", "lower", "path_b")
        edge("upper", "show")
        edge("lower", "low_show")
        edge("show", "end")
        edge("low_show", "end")
        source = None
    if number == 1:
        n["show"]["config"]["template"] = "Ready"
    if source:
        edge(source, "show")
    if number != 8:
        edge("show", "end")
    return dict(format="aotn-workflow/1", name=f"Case {number}", nodes=n, connections=e)


def calibration_pairs():
    pairs = []

    def pair(name, case, mutate):
        good = good_draft(case)
        bad = deepcopy(good)
        mutate(bad)
        pairs.append(dict(id=name, case=case, good=good, bad=bad))

    pair(
        "broken_braces",
        1,
        lambda s: s["nodes"]["show"]["config"].update(template="{input"),
    )
    pair(
        "wrong_transform",
        2,
        lambda s: s["nodes"]["transform"]["config"].update(operation="uppercase"),
    )

    def order(s):
        s["connections"] = [
            {"from": "start.default", "to": "show.input"},
            {"from": "show.default", "to": "strip.input"},
            {"from": "strip.default", "to": "transform.input"},
            {"from": "transform.default", "to": "end.input"},
        ]

    pair("wrong_order", 2, order)
    pair(
        "disabled_transient",
        5,
        lambda s: s["nodes"]["read"]["config"].update(transient_output=False),
    )
    pair(
        "wrong_path",
        5,
        lambda s: s["nodes"]["write"]["config"].update(
            file_path="ROOT/unrequested.txt"
        ),
    )
    pair(
        "overwrite",
        5,
        lambda s: s["nodes"]["write"]["config"].update(write_mode="Overwrite"),
    )

    def reverse(s):
        for e in s["connections"]:
            if e["from"].startswith("if."):
                e["from"] = "if." + ("false" if e["from"] == "if.true" else "true")

    pair("reversed_true_false", 7, reverse)

    def fan(s):
        s["connections"] = [
            e
            for e in s["connections"]
            if not e["from"].startswith("parallel.") and e["to"] != "parallel.input"
        ]
        del s["nodes"]["parallel"]
        s["connections"] += [
            {"from": "ask.default", "to": "upper.input"},
            {"from": "ask.default", "to": "lower.input"},
        ]

    pair("ordinary_fan_out", 8, fan)
    pair(
        "ignored_clarification",
        10,
        lambda s: s["nodes"]["transform"]["config"].update(operation="uppercase"),
    )

    def unreachable(s):
        s["nodes"]["show"]["config"]["template"] = "Wrong"
        s["nodes"]["decorative"] = {
            "type": "text_output_node",
            "config": {"template": "Ready"},
        }

    pair("unreachable_correct_node", 1, unreachable)
    pair(
        "double_brace_path",
        6,
        lambda s: s["nodes"]["show"]["config"].update(template="{{input}}"),
    )
    pair(
        "whole_file_dict",
        6,
        lambda s: s["nodes"]["show"]["config"].update(template="{input}"),
    )
    pair(
        "configured_content_override",
        5,
        lambda s: s["nodes"]["write"]["config"].update(
            content_source="Configured", content="invented"
        ),
    )

    def labelled(s):
        s["nodes"]["label"] = {
            "type": "text_output_node",
            "config": {"template": "{input}"},
        }
        s["connections"] = [
            e for e in s["connections"] if e["to"] != "write.content"
        ] + [
            {"from": "read.default", "to": "label.input"},
            {"from": "label.default", "to": "write.content"},
        ]

    pair("label_in_saved_content", 5, labelled)
    pair(
        "contains_empty",
        9,
        lambda s: s["nodes"]["if"]["config"].update(condition_type="contains"),
    )

    def hardcoded_heading(spec):
        spec["nodes"]["start"]["config"]["greeting"] = ""
        spec["nodes"]["show"]["config"]["template"] = "{input}monday update"

    pair("hardcoded_heading", 2, hardcoded_heading)
    pair(
        "partial_file_display",
        4,
        lambda spec: spec["nodes"]["show"]["config"].update(
            template="{input[0]}udget: €20\nBring notes.\n"
        ),
    )

    def partial_content(spec, source, template):
        spec["nodes"]["partial"] = {
            "type": "concat_node",
            "config": {"template": template},
        }
        spec["connections"] = [
            edge for edge in spec["connections"] if edge["from"] != source + ".default"
        ]
        spec["connections"] += [
            {"from": source + ".default", "to": "partial.input"},
            {"from": "partial.default", "to": "write.content"},
        ]

    pair(
        "partial_file_copy",
        5,
        lambda spec: partial_content(spec, "read", "{input[0]}ine one\nLine two\n"),
    )
    pair(
        "partial_clarified_content",
        10,
        lambda spec: partial_content(spec, "transform", "{input[0]}ello\nworld"),
    )

    def serial_parallel(spec):
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

    pair("serial_parallel_work", 8, serial_parallel)

    def conditional_before_choice(spec):
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
            if edge["from"]
            not in (
                "ask.default",
                "show.default",
                "stop.default",
                "if.true",
                "if.false",
            )
        ]
        spec["connections"] += [
            {"from": "ask.default", "to": "show.input"},
            {"from": "show.default", "to": "stop.input"},
            {"from": "stop.default", "to": "restore.input"},
            {"from": "restore.default", "to": "if.input"},
            {"from": "if.true", "to": "end.input"},
            {"from": "if.false", "to": "end.input"},
        ]

    pair("conditional_work_before_choice", 7, conditional_before_choice)

    def empty_choice_saves(spec):
        # The empty route shows its message, then still uppercases and saves it.
        spec["connections"] = [
            edge for edge in spec["connections"] if edge["from"] != "empty.default"
        ]
        spec["connections"].append({"from": "empty.default", "to": "upper.input"})

    pair("empty_choice_still_saves", 9, empty_choice_saves)
    def spare_end(spec):
        spec['nodes']['spare_end'] = {'type': 'end_node', 'config': {'record_line': False}}

    pair('unconnected_end', 8, spare_end)
    # End completion framing cannot excuse displaying the wrong user value.
    good = good_draft(1)
    good['nodes']['start']['config']['greeting'] = 'Waiting'
    good['nodes']['end']['config'].update(record_line=True)
    bad = deepcopy(good)
    bad['nodes']['show']['config']['template'] = '{input}'
    pairs.append(dict(id='end_framing_does_not_hide_missing_value', case=1, good=good, bad=bad))
    # Held out from judge-prompt tuning: the same swap on a different request
    # (empty check), so a fix fitted only to case 7 would still miss it.
    pair("reversed_empty_check", 9, reverse)
    from .case_set_three import calibration_pairs as helpers
    return pairs + helpers()

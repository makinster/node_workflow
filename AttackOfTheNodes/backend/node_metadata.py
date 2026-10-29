"""Node metadata record v1: the one editable record of what each node is for.

Design: agent_channel/node-metadata-plan (owner-approved 2026-10-28) and
docs/integrations/NODE_METADATA.md. Records say what a node does, when to
choose it, the closest wrong use, its possible effects, its prerequisites and
rough cost/time, plus the verified ``execution_contract`` that used to live in
``node_execution_contracts.py`` (now a derived projection of this registry).

Records only describe code. Identity, ports, config schemas, defaults and
errors keep their owners in the node classes; nothing here drives execution,
validation or approval. A record, an empty effect list or a matching purpose
is never permission to run anything. Common engine bookkeeping (run history,
the output log, timing) and within-run Vault/transient values are not effects;
explicit files, cross-run saved values and queues are.

Every registered type is either in ``NODE_METADATA`` with a reviewed record or
in the ``PENDING_REVIEW`` migration ledger. A pending type has *no* record: its
effects are unknown, never "Read-only". Debug nodes and the tombstone get the
lighter record (purpose, side_effects, needs) the owner approved.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from copy import deepcopy
from typing import Any, Dict, List, Optional

RECORD_SCHEMA_VERSION = 1

EFFECTS = (
    "writes_files", "sends_messages", "spends_money", "runs_external_commands",
    "changes_external_state", "controls_windows", "sends_data",
)
NEEDS = (
    "network", "browser", "login", "credentials", "model", "local_files",
    "user_input", "external_program", "background_service",
)
COST_CLASSES = ("no_usage_fee", "metered", "variable", "unknown")
TIME_CLASSES = ("quick", "seconds", "slow", "waits", "variable", "unknown")
LEARNABLE_FROM = ("example", "recording")
MAX_RECORD_BYTES = 4096

#: Plain phrases for effect flags; UI and catalogue text use these.
EFFECT_PHRASES = {
    "writes_files": "writes files",
    "sends_messages": "sends messages",
    "spends_money": "may spend money",
    "runs_external_commands": "runs external commands",
    "changes_external_state": "changes external state",
    "controls_windows": "controls windows",
    "sends_data": "sends data to a service",
}
NEED_PHRASES = {
    "network": "network",
    "browser": "browser",
    "login": "signed-in login",
    "credentials": "credentials",
    "model": "model",
    "local_files": "local files",
    "user_input": "a person to answer",
    "external_program": "external program",
    "background_service": "background service",
}
COST_PHRASES = {
    "no_usage_fee": "no usage fee", "metered": "metered", "variable": "variable",
    "unknown": "unknown",
}

#: Debug nodes and the tombstone: purpose, side_effects and needs only.
LIGHT_RECORD_TYPES = frozenset({
    "echo_node", "logger_node", "sleep_node", "counter_node",
    "memory_snapshot_node", "probe_node", "error_node", "random_branch_node",
    "deep_branch_node", "no_op_node", "repeat_counter_node", "tombstone_node",
})

_TEXT_LIMITS = {
    "purpose": 120, "use_when": 200, "not_for": 200, "cost_note": 160,
    "time_note": 160,
}
_FULL_REQUIRED = (
    "schema_version", "purpose", "use_when", "not_for", "side_effects", "needs",
    "cost_class", "time_class", "execution_contract",
)
_FULL_OPTIONAL = ("cost_note", "time_note", "learnable_from")
_LIGHT_REQUIRED = ("schema_version", "purpose", "side_effects", "needs")


# --- records ------------------------------------------------------------------------

def _none():
    return {"required": [], "optional": [], "unresolved": False}


def _read_only():
    return {"possible": [], "delegated": False}


#: Batch 1 (2026-10-29): the twelve Draft a workflow v2 palette types. Each
#: sentence was checked against the node's execute/config code and its helpers;
#: the review manifest (node_metadata_review.json) lists those sources.
NODE_METADATA: Dict[str, Dict[str, Any]] = {
    "start_node": {
        "schema_version": 1,
        "purpose": "Begin a run by passing the greeting, or configured input values, to the next node as its input.",
        "use_when": "Every workflow starts here. Set the greeting to the text the first step should receive, or add Inputs for values a caller supplies.",
        "not_for": "Showing text: Start itself shows nothing. Use Text Output to show the value passed to the next node.",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": 'default port passes to the next node as input; with rows absent/empty, greeting string verbatim (default "Workflow started"); transient_output=false suppresses it. Nonempty rows replace greeting: one downstream value as-is, several as name:value object, none/no_inputs emits no payload.',
            "notes": 'The next step runs even with no payload. An empty greeting "" still starts it and arrives as empty text; with no payload the next input is absent (most nodes then read empty text).',
        },
    },
    "end_node": {
        "schema_version": 1,
        "purpose": "Finish a path, adding an [END] completion line to the run output unless that line is turned off.",
        "use_when": "A path is done: end each path with an End so its finish is recorded. Turn on Return End when a calling workflow needs this workflow's results.",
        "not_for": "Showing the requested answer: its [END] line is completion framing. Use Text Output for text the request asks to show.",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": "None; ends branch. record_line logs [END] completion as normal run framing, not an unrequested effect. return_end publishes workflow results only.",
            "notes": 'Several paths may share one End input (normal End, return_end=false). Each arriving path runs End separately and finishes there; this is normal and complete, not unconnected. Return End publishes results only once; repeat publication errors. record_line on (default) logs only "[END] <message>"; input is never echoed. Off adds nothing.',
        },
    },
    "branch_end_node": {
        "schema_version": 1,
        "purpose": "Pass a parallel path's value on unchanged and mark that path as ready for a Merge.",
        "use_when": "A path started by Parallel Branch should be joined: place this as the path's last step and connect it to a Merge.",
        "not_for": "Ending a path (use End) or changing the value. It does not stop the path or wait for other paths.",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": "default: input unchanged; absent: empty text.",
        },
    },
    "branch_node": {
        "schema_version": 1,
        "purpose": "Run the same input down 2 to 64 parallel paths at the same time.",
        "use_when": "The request explicitly asks for parallel or simultaneous paths, such as two different results made from one value at once.",
        "not_for": "Steps that run one after another, or choosing one path (use Conditional). Only for requested parallel paths; never add an unrequested split.",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": "Each parallel path gets input, or its branch_payload_sources Vault value (missing key: input).",
            "notes": "With branch_count set (the default) every path starts; condition settings apply only to legacy configs without branch_count. A path with no connection is skipped. Paths run independently.",
        },
    },
    "user_text_input_node": {
        "schema_version": 1,
        "purpose": "Pause the run, ask a person for text, and send their answer to the next step.",
        "use_when": "The request says to ask the user for a value while the workflow runs, such as a note or a yes/no answer.",
        "not_for": "Text already known when building the workflow (use Start's greeting or Concat). Unattended runs fail here instead of waiting.",
        "side_effects": _read_only(),
        "needs": {"required": ["user_input"], "optional": [], "unresolved": False},
        "cost_class": "no_usage_fee",
        "time_class": "waits",
        "time_note": "Waits until a person answers; a run with nobody to answer fails instead.",
        "execution_contract": {
            "output_payload": "default: unchanged user answer string; incoming input triggers prompt only.",
            "notes": 'Optional membank_outputs copies the answer to Vault before continuing: [{id:"key",output:"key",data_type:"string"}]. Concat can read {key} alongside its current {input}.',
        },
    },
    "text_output_node": {
        "schema_version": 1,
        "purpose": "Show formatted text in this run's output and pass the same text to the next step.",
        "use_when": "The request wants text shown. Leave the label empty to show plain text with no [label] prefix.",
        "not_for": "Saving text to a file (use File Write) or sending a message to another app or person.",
        "side_effects": _read_only(),
        "needs": {
            "required": [], "optional": ["user_input"], "unresolved": False,
            "note": "With request_user_input on, it pauses to ask a person for the value to show.",
        },
        "cost_class": "no_usage_fee",
        "time_class": "variable",
        "time_note": "Formatting is quick; with request_user_input on it waits for a person.",
        "execution_contract": {
            "output_payload": 'default/log: empty or whitespace-only label = bare formatted text; a set label adds "[label] " unchanged. Label is display framing. The same downstream payload includes any set label (also when saved). {input[path]}: path; {{input}}: literal.',
            "notes": "After File Write, {input} shows the whole file record {type, ref_key, path}, NOT just its path. To show the saved path, use {input[path]}. The default label is Output. Template names other than input, a missing [key] or .attribute, or bad braces, error. A missing input Vault key errors; request_user_input replaces the input with the answer.",
        },
    },
    "text_transform_node": {
        "schema_version": 1,
        "purpose": "Change text in one fixed way: uppercase, lowercase, trim both ends, title case, reverse, or tidy Markdown.",
        "use_when": "One value needs a simple text change. Chain two Text Transform steps for two changes, such as trim then lowercase.",
        "not_for": "Find-and-replace, removing spaces inside the text, or joining values (use Concat). strip trims only the two ends.",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": "default: transformed string. strip trims whole-input boundary whitespace. Falsy input becomes empty text.",
            "notes": "Other input is converted with str(): a file reference becomes its dict text, not the file contents. Default operation is uppercase; an unknown operation also uppercases.",
        },
    },
    "file_reader_node": {
        "schema_version": 1,
        "purpose": "Read all text from a UTF-8 file and send it to the next step.",
        "use_when": "You have a local text file path, or a file reference from File Write, and need the file's contents.",
        "not_for": "Reading a web page, choosing a file in a window, or writing a file (use File Write).",
        "side_effects": _read_only(),
        "needs": {"required": ["local_files"], "optional": [], "unresolved": False},
        "cost_class": "no_usage_fee",
        "time_class": "variable",
        "time_note": "Small files are quick; file size and storage decide the wait.",
        "execution_contract": {
            "output_payload": "default: whole UTF-8 file as string (text mode: line endings become \\n); missing/unreadable file errors.",
            "notes": "Upstream and Vault sources must hold a typed file reference such as File Write's output; a plain path string errors. Configured (default) reads file_path.",
        },
    },
    "file_output_node": {
        "schema_version": 1,
        "purpose": "Write text, or Base64-decoded bytes, to a file and pass on a file reference holding the actual saved path.",
        "use_when": "The request asks to save or create a file. Create unique keeps existing files by saving under a new name.",
        "not_for": "Showing text to the user (use Text Output) or reading a file. The default mode, Overwrite, replaces an existing file.",
        "side_effects": {
            "possible": ["writes_files", "runs_external_commands", "controls_windows"],
            "delegated": False,
            "note": "Every successful run writes the file and creates missing folders. Open after write (off by default) starts the system file opener, may place its window, and with Close when run ends closes it.",
        },
        "needs": {
            "required": ["local_files"], "optional": ["external_program"], "unresolved": False,
            "note": "Open after write needs a desktop app that opens the file type.",
        },
        "cost_class": "no_usage_fee",
        "time_class": "variable",
        "time_note": "Small writes are quick; file size decides the wait. Open after write can add up to about 5 s finding the window.",
        "execution_contract": {
            "output_payload": 'default: {type:"file",ref_key:string,path:"actual saved absolute path"}; new ref_key="file:"+path; reused identity/lifetime retained. dead_drop_passthrough forwards input; transient_output=false suppresses normal output.',
            "notes": "After File Write, Text Output {input} shows the whole file record {type, ref_key, path}, NOT just its path. To show the saved path, use {input[path]}. Create unique: name.ext if absent; else name (1).ext, name (2).ext, etc.; keeps existing files. Not atomic.",
        },
    },
    "conditional_node": {
        "schema_version": 1,
        "purpose": "Choose one of two paths, true or false, by comparing a value with fixed text.",
        "use_when": "What happens next depends on a value, such as continuing only when an answer is exactly yes.",
        "not_for": "Running both paths (use Parallel Branch), joining paths, or waiting for another step. Only one path continues.",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": "Only the selected port (true if matched, false otherwise) emits the unchanged left value: input, or Vault value when left_value_source=variable; never the comparison boolean.",
            "notes": "equals compares str(left) == str(right_value): case-sensitive, whitespace preserved; no trimming. Default contains: right_value in left (empty right_value always matches). regex uses re.search; an invalid pattern errors. not_equals inverts equals. A missing Vault variable compares as empty text.",
        },
    },
    "concat_node": {
        "schema_version": 1,
        "purpose": "Build one text from a template filled with the input and saved Vault values.",
        "use_when": "The next step needs fixed text, or text that combines the input with words or Vault values.",
        "not_for": "Showing text to the user (use Text Output) or changing case or trimming (use Text Transform).",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": "default: format_map string from Vault + inputs (inputs win). {input[path]} reads the path key. vault_write saves this formatted string as string; dead_drop_passthrough forwards the unchanged input instead.",
            "notes": "A missing Vault name, [key] or .attribute errors; missing names never become empty text. {{ and }} give literal braces. A template without {input} ignores the input for formatting. transient_output=false sends no payload unless dead_drop_passthrough=true; Vault writes still happen.",
        },
    },
    "json_path_node": {
        "schema_version": 1,
        "purpose": "Pick one value out of JSON data by a dot path such as user.name or items.0.",
        "use_when": "The input is JSON text or an object, such as an API reply or File Write's file reference, and you need one field from it.",
        "not_for": "Searching text that is not JSON, or changing values. A missing path gives default_value, not an error.",
        "side_effects": _read_only(),
        "needs": _none(),
        "cost_class": "no_usage_fee",
        "time_class": "quick",
        "execution_contract": {
            "output_payload": "default: extracted typed value, or default_value on miss. Input: JSON text or parsed value; invalid JSON errors.",
            "notes": "Empty or absent input is not JSON and errors. An empty path returns the whole parsed input. Number segments index lists; -1 is the last item.",
        },
    },
}

#: Migration ledger: registered types still waiting for a reviewed record.
#: They have no record and no effect claims. Remove a type from here in the
#: same change that adds its record; a new node type needs a record, not a
#: ledger entry. The ledger must be empty before the hard gate closes.
PENDING_REVIEW = frozenset({
    # Batch 2: data, control, meta and state
    "merge_node", "wait_until_node", "error_mux_node", "set_variable_node",
    "get_variable_node", "variable_setter_node", "variable_reader_node",
    "random_number_node", "find_lines_node", "read_lines_node", "check_reply_node",
    "context_pack_node", "node_catalogue_node", "check_workflow_spec_node",
    "remember_node", "recall_node", "if_changed_node",
    # Batch 3: system, file, service, model and delegated
    "disk_space_node", "file_age_node", "git_status_node", "file_view_node",
    "window_control_node", "http_request_node", "record_event_node",
    "hermes_notify_node", "hermes_ask_node", "hermes_investigate_node",
    "hermes_investigation_result_node", "ask_local_model_node", "ask_claude_node",
    "chat_completion_node", "image_generation_node", "embedding_node",
    "pick_one_node", "subworkflow_node",
    # Batch 4: diagnostic, loop and hidden (lighter record)
    "echo_node", "logger_node", "sleep_node", "counter_node", "memory_snapshot_node",
    "probe_node", "error_node", "random_branch_node", "deep_branch_node",
    "no_op_node", "repeat_counter_node", "tombstone_node",
})


# --- access ---------------------------------------------------------------------------

def record_for(node_type: str) -> Optional[Dict[str, Any]]:
    """An independent copy of the type's record, or None while it is pending."""
    record = NODE_METADATA.get(node_type)
    return deepcopy(record) if record is not None else None


def execution_contracts() -> Dict[str, Dict[str, Any]]:
    """Derived ``execution_contract`` projection for legacy clients."""
    return {
        node_type: deepcopy(record["execution_contract"])
        for node_type, record in NODE_METADATA.items()
        if "execution_contract" in record
    }


def is_read_only(record: Optional[Dict[str, Any]]) -> bool:
    """Derived only from a reviewed explicit empty list and no delegation.

    A missing record is never read-only.
    """
    if not isinstance(record, dict):
        return False
    effects = record.get("side_effects")
    return (isinstance(effects, dict) and effects.get("possible") == []
            and effects.get("delegated") is False)


def selection(record: Dict[str, Any]) -> Dict[str, Any]:
    """The Brief projection: what is needed to choose a type, without notes."""
    effects = record["side_effects"]
    needs = record["needs"]
    result: Dict[str, Any] = {"purpose": record["purpose"]}
    for key in ("use_when", "not_for"):
        if key in record:
            result[key] = record[key]
    result["side_effects"] = {"possible": list(effects["possible"]),
                              "delegated": effects["delegated"]}
    result["needs"] = {"required": list(needs["required"]),
                       "optional": list(needs["optional"]),
                       "unresolved": needs["unresolved"]}
    for key in ("cost_class", "time_class"):
        if key in record:
            result[key] = record[key]
    return result


def effects_text(record: Dict[str, Any]) -> str:
    """"Read-only" or plain possible-effect phrases; never from missing data."""
    effects = record["side_effects"]
    if is_read_only(record):
        return "Read-only"
    phrases = [EFFECT_PHRASES[e] for e in effects["possible"]]
    if effects["delegated"]:
        phrases.append("delegated work with its own effects")
    return "possibly " + "; ".join(phrases)


def needs_text(record: Dict[str, Any]) -> str:
    needs = record["needs"]
    parts = []
    if needs["required"]:
        parts.append(", ".join(NEED_PHRASES[n] for n in needs["required"]))
    if needs["optional"]:
        parts.append("in some modes " + ", ".join(NEED_PHRASES[n] for n in needs["optional"]))
    if needs["unresolved"]:
        parts.append("more depending on delegated work")
    return "; ".join(parts) or "nothing beyond the engine"


def note_lines(record: Dict[str, Any]) -> List[str]:
    """Explanatory notes, for full records only (Brief omits them)."""
    notes = [("Effects note", record["side_effects"].get("note")),
             ("Needs note", record["needs"].get("note")),
             ("Cost note", record.get("cost_note")), ("Time note", record.get("time_note"))]
    return [f"{label}: {text}" for label, text in notes if text]


def standard_key_docs(defaults):
    """Shared config behavior, derived for every type declaring the option."""
    if 'transient_output' not in defaults:
        return {}
    default = str(defaults['transient_output']).lower()
    return {'transient_output': 'true passes the output on to the next node; false sends no output on. Default: ' + default + '.'}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True, allow_nan=False)


def content_sha256(record: Dict[str, Any]) -> str:
    """Digest of a record's content; a text edit invalidates its review."""
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


# --- validation ---------------------------------------------------------------------

def _text_problems(field: str, value: Any, limit: int) -> List[str]:
    if type(value) is not str:
        return [f"{field}: must be text"]
    problems = []
    if not value:
        problems.append(f"{field}: must not be empty")
    if value != value.strip():
        problems.append(f"{field}: no leading or trailing space")
    if any(unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp") for ch in value):
        problems.append(f"{field}: single line, no control characters")
    normalized = unicodedata.normalize("NFC", value)
    if normalized != value:
        problems.append(f"{field}: must be NFC-normalized")
    if len(normalized) > limit:
        problems.append(f"{field}: {len(normalized)} characters over the {limit} limit")
    return problems


def _enum_list_problems(field: str, value: Any, allowed: tuple, max_items: int,
                        min_items: int = 0) -> List[str]:
    if type(value) is not list:
        return [f"{field}: must be a list"]
    problems = []
    if not min_items <= len(value) <= max_items:
        problems.append(f"{field}: {min_items}-{max_items} items")
    unknown = [v for v in value if v not in allowed]
    if unknown:
        problems.append(f"{field}: unknown values {unknown!r}")
    elif len(set(value)) != len(value):
        problems.append(f"{field}: duplicate values")
    elif value != sorted(value, key=allowed.index):
        problems.append(f"{field}: not in canonical order")
    return problems


def _keys_problems(field: str, value: Dict[str, Any], required, optional=()) -> List[str]:
    problems = [f"{field}: missing {key}" for key in required if key not in value]
    extra = sorted(set(value) - set(required) - set(optional))
    if extra:
        problems.append(f"{field}: unknown keys {extra!r}")
    return problems


def _effects_problems(value: Any) -> List[str]:
    if not isinstance(value, dict):
        return ["side_effects: must be an object"]
    problems = _keys_problems("side_effects", value, ("possible", "delegated"), ("note",))
    if "possible" in value:
        problems += _enum_list_problems("side_effects.possible", value["possible"], EFFECTS, 7)
    if "delegated" in value and type(value["delegated"]) is not bool:
        problems.append("side_effects.delegated: must be true or false")
    if "note" in value:
        problems += _text_problems("side_effects.note", value["note"], 240)
    elif value.get("delegated") is True:
        problems.append("side_effects.note: required when delegated is true")
    return problems


def _needs_problems(value: Any) -> List[str]:
    if not isinstance(value, dict):
        return ["needs: must be an object"]
    problems = _keys_problems("needs", value, ("required", "optional", "unresolved"), ("note",))
    for key in ("required", "optional"):
        if key in value:
            problems += _enum_list_problems(f"needs.{key}", value[key], NEEDS, 9)
    if isinstance(value.get("required"), list) and isinstance(value.get("optional"), list):
        overlap = set(value["required"]) & set(value["optional"])
        if overlap:
            problems.append(f"needs: {sorted(overlap)!r} both required and optional")
    if "unresolved" in value and type(value["unresolved"]) is not bool:
        problems.append("needs.unresolved: must be true or false")
    if "note" in value:
        problems += _text_problems("needs.note", value["note"], 240)
    elif value.get("optional") or value.get("unresolved") is True:
        problems.append("needs.note: required for optional needs or unresolved=true")
    return problems


def _contract_problems(value: Any) -> List[str]:
    if not isinstance(value, dict):
        return ["execution_contract: must be an object"]
    problems = _keys_problems("execution_contract", value, ("output_payload",), ("notes",))
    if "output_payload" in value:
        problems += _text_problems("execution_contract.output_payload", value["output_payload"], 512)
    if "notes" in value:
        problems += _text_problems("execution_contract.notes", value["notes"], 512)
    return problems


def _version_problems(record: Dict[str, Any]) -> List[str]:
    version = record.get("schema_version")
    if type(version) is not int or version != RECORD_SCHEMA_VERSION:
        return [f"schema_version: expected {RECORD_SCHEMA_VERSION}, got {version!r}"]
    return []


def record_problems(node_type: str, record: Any) -> List[str]:
    """Every rule the record breaks; empty when valid. Never clips or fills."""
    if not isinstance(record, dict):
        return ["record: must be an object"]
    version = _version_problems(record)
    if version:
        # An unknown version is an error, never read as a familiar record.
        return version
    if node_type in LIGHT_RECORD_TYPES:
        problems = _keys_problems("record", record, _LIGHT_REQUIRED)
    else:
        problems = _keys_problems("record", record, _FULL_REQUIRED, _FULL_OPTIONAL)
    for field in ("purpose", "use_when", "not_for", "cost_note", "time_note"):
        if field in record:
            problems += _text_problems(field, record[field], _TEXT_LIMITS[field])
    if "side_effects" in record:
        problems += _effects_problems(record["side_effects"])
    if "needs" in record:
        problems += _needs_problems(record["needs"])
    if "cost_class" in record:
        if record["cost_class"] not in COST_CLASSES:
            problems.append(f"cost_class: unknown value {record['cost_class']!r}")
        elif record["cost_class"] in ("variable", "unknown") and "cost_note" not in record:
            problems.append("cost_note: required for variable/unknown cost")
    if "time_class" in record:
        if record["time_class"] not in TIME_CLASSES:
            problems.append(f"time_class: unknown value {record['time_class']!r}")
        elif (record["time_class"] in ("waits", "variable", "unknown")
              and "time_note" not in record):
            problems.append("time_note: required for waits/variable/unknown time")
    if "learnable_from" in record:
        problems += _enum_list_problems("learnable_from", record["learnable_from"],
                                        LEARNABLE_FROM, 2, 1)
    if "execution_contract" in record:
        problems += _contract_problems(record["execution_contract"])
    if not problems:
        size = len(json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if size > MAX_RECORD_BYTES:
            problems.append(f"record: {size} bytes over the {MAX_RECORD_BYTES}-byte limit")
    return problems


def selection_problems(node_type: str, value: Any) -> List[str]:
    """The Brief projection's own schema; a full record never passes it."""
    if not isinstance(value, dict):
        return ["selection: must be an object"]
    if node_type in LIGHT_RECORD_TYPES:
        required: tuple = ("purpose", "side_effects", "needs")
    else:
        required = ("purpose", "use_when", "not_for", "side_effects", "needs",
                    "cost_class", "time_class")
    problems = _keys_problems("selection", value, required)
    for field in ("purpose", "use_when", "not_for"):
        if field in value:
            problems += _text_problems(field, value[field], _TEXT_LIMITS[field])
    effects = value.get("side_effects")
    if isinstance(effects, dict):
        problems += _keys_problems("selection.side_effects", effects, ("possible", "delegated"))
        problems += _effects_problems({**effects, **({"note": "-"} if effects.get("delegated") else {})})
    elif "side_effects" in value:
        problems.append("selection.side_effects: must be an object")
    needs = value.get("needs")
    if isinstance(needs, dict):
        problems += _keys_problems("selection.needs", needs, ("required", "optional", "unresolved"))
        problems += _needs_problems({**needs, "note": "-"})
    elif "needs" in value:
        problems.append("selection.needs: must be an object")
    if "cost_class" in value and value["cost_class"] not in COST_CLASSES:
        problems.append(f"cost_class: unknown value {value['cost_class']!r}")
    if "time_class" in value and value["time_class"] not in TIME_CLASSES:
        problems.append(f"time_class: unknown value {value['time_class']!r}")
    return problems

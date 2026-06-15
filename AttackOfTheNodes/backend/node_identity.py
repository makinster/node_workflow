"""Transitional node identity metadata for Phase 17."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Type

from .node_base import Node


INPUTS = "Inputs"
FLOW_CONTROL = "Flow Control"
OUTPUTS = "Outputs"
COMPLEX = "Complex"

TRIGGERED = "Triggered"
FILE_IO = "File I/O"
INTERNET = "Internet"
AI = "AI"
PASSIVE_OUTPUT = "Passive Output"
ACTIVE_OUTPUT = "Active Output"
PARALLEL = "Parallel"
CONDITIONAL = "Conditional"
RUNTIME_RESOURCE = "Runtime Resource"
UTILITY = "Utility"

FAMILY_COLOR_HINTS = {
    INPUTS: "green",
    FLOW_CONTROL: "blue",
    OUTPUTS: "amber",
    COMPLEX: "violet",
}


TRANSITIONAL_NODE_IDENTITY: Dict[str, Dict[str, Any]] = {
    "start_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [TRIGGERED],
        "icon_name": "play",
    },
    "end_node": {
        "primary_family": OUTPUTS,
        "tags": [PASSIVE_OUTPUT],
        "icon_name": "circle-stop",
    },
    "branch_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL],
        "icon_name": "git-branch",
    },
    "branch_end_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL, UTILITY],
        "icon_name": "milestone",
    },
    "conditional_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [CONDITIONAL],
        "icon_name": "split",
    },
    "merge_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL],
        "icon_name": "git-merge",
    },
    "wait_until_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL, CONDITIONAL, UTILITY],
        "icon_name": "hourglass",
    },
    "set_variable_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "database-zap",
    },
    "get_variable_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "database",
    },
    "concat_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "combine",
    },
    "variable_setter_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "database-zap",
    },
    "variable_reader_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "database",
    },
    "text_output_node": {
        "primary_family": OUTPUTS,
        "tags": [PASSIVE_OUTPUT, ACTIVE_OUTPUT],
        "icon_name": "message-square-text",
    },
    "user_text_input_node": {
        "primary_family": INPUTS,
        "tags": [ACTIVE_OUTPUT],
        "icon_name": "keyboard",
    },
    "file_reader_node": {
        "primary_family": INPUTS,
        "tags": [FILE_IO],
        "icon_name": "file-text",
    },
    "chat_completion_node": {
        "primary_family": COMPLEX,
        "tags": [AI],
        "icon_name": "bot-message-square",
    },
    "image_generation_node": {
        "primary_family": COMPLEX,
        "tags": [AI],
        "icon_name": "image",
    },
    "embedding_node": {
        "primary_family": COMPLEX,
        "tags": [AI, UTILITY],
        "icon_name": "braces",
    },
    "tombstone_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "file-x",
    },
    "echo_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "repeat",
    },
    "logger_node": {
        "primary_family": OUTPUTS,
        "tags": [PASSIVE_OUTPUT, UTILITY],
        "icon_name": "scroll-text",
    },
    "sleep_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "timer",
    },
    "counter_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "badge-plus",
    },
    "memory_snapshot_node": {
        "primary_family": OUTPUTS,
        "tags": [PASSIVE_OUTPUT, UTILITY],
        "icon_name": "clipboard-list",
    },
    "probe_node": {
        "primary_family": OUTPUTS,
        "tags": [PASSIVE_OUTPUT, UTILITY],
        "icon_name": "scan-search",
    },
    "error_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "triangle-alert",
    },
    "random_branch_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [CONDITIONAL],
        "icon_name": "shuffle",
    },
    "deep_branch_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL],
        "icon_name": "git-fork",
    },
    "no_op_node": {
        "primary_family": COMPLEX,
        "tags": [UTILITY],
        "icon_name": "circle",
    },
    "repeat_counter_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [CONDITIONAL, UTILITY],
        "icon_name": "refresh-cw",
    },
}


def apply_transitional_node_identity(node_classes: Iterable[Type[Node]]) -> None:
    """Attach Phase 17 identity metadata to existing registered nodes."""
    for node_class in node_classes:
        identity = TRANSITIONAL_NODE_IDENTITY.get(node_class.node_type)
        if not identity:
            continue
        primary_family = str(identity["primary_family"])
        node_class.primary_family = primary_family
        node_class.tags = list(identity.get("tags", []))
        node_class.icon_name = str(identity.get("icon_name", ""))
        node_class.color_hint = str(
            identity.get("color_hint") or FAMILY_COLOR_HINTS.get(primary_family, "")
        )

"""Transitional node identity metadata for Phase 17.

Families, groups, and sections follow the 2026-06-12 taxonomy revision:
five families (Inputs, Outputs, Flow Control, Utility, Complex), frontend
`group` entries that open a Group Picker, and `selector_section` headers
inside each selector tab. See docs/PHASE_17_NODE_VISUAL_IDENTITY.md and
docs/NODE_CATALOG.md.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Type

from .node_base import Node


INPUTS = "Inputs"
OUTPUTS = "Outputs"
FLOW_CONTROL = "Flow Control"
UTILITY_FAMILY = "Utility"
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
    OUTPUTS: "amber",
    FLOW_CONTROL: "blue",
    UTILITY_FAMILY: "grey",
    COMPLEX: "violet",
}


TRANSITIONAL_NODE_IDENTITY: Dict[str, Dict[str, Any]] = {
    # Structural runtime types. Start is auto-generated and End is replaced by
    # terminate-branch output config; both are hidden from the selector.
    "start_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [TRIGGERED],
        "icon_name": "play",
    },
    "end_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [UTILITY],
        "icon_name": "circle-stop",
    },
    # Flow Control — Branching section
    "branch_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL],
        "icon_name": "git-branch",
        "group": "Branch",
        "selector_section": "Branching",
    },
    "conditional_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [CONDITIONAL],
        "icon_name": "split",
        "group": "Branch",
        "selector_section": "Branching",
    },
    "random_branch_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [CONDITIONAL],
        "icon_name": "shuffle",
        "group": "Branch",
        "selector_section": "Branching",
    },
    "deep_branch_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL],
        "icon_name": "git-fork",
        "group": "Branch",
        "selector_section": "Branching",
    },
    "merge_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL],
        "icon_name": "git-merge",
        "group": "Merge",
        "selector_section": "Branching",
    },
    "branch_end_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL, UTILITY],
        "icon_name": "milestone",
        "selector_section": "Branching",
    },
    # Flow Control — Timing section
    "wait_until_node": {
        "primary_family": FLOW_CONTROL,
        "tags": [PARALLEL, CONDITIONAL, UTILITY],
        "icon_name": "hourglass",
        "group": "Wait / Timer",
        "selector_section": "Timing",
    },
    # Utility — Transform section
    "set_variable_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "database-zap",
        "group": "Data Transform",
        "selector_section": "Transform",
    },
    "get_variable_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "database",
        "group": "Data Transform",
        "selector_section": "Transform",
    },
    "variable_setter_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "database-zap",
        "group": "Data Transform",
        "selector_section": "Transform",
    },
    "variable_reader_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "database",
        "group": "Data Transform",
        "selector_section": "Transform",
    },
    "concat_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "combine",
        "group": "Data Transform",
        "selector_section": "Transform",
    },
    # Utility — Debug section (direct-add)
    "echo_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "repeat",
        "selector_section": "Debug",
    },
    "probe_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [PASSIVE_OUTPUT, UTILITY],
        "icon_name": "scan-search",
        "selector_section": "Debug",
    },
    "logger_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [PASSIVE_OUTPUT, UTILITY],
        "icon_name": "scroll-text",
        "selector_section": "Debug",
    },
    "sleep_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "timer",
        "selector_section": "Debug",
    },
    "memory_snapshot_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [PASSIVE_OUTPUT, UTILITY],
        "icon_name": "clipboard-list",
        "selector_section": "Debug",
    },
    "no_op_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "circle",
        "selector_section": "Debug",
    },
    "error_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "triangle-alert",
        "selector_section": "Debug",
    },
    # Utility — Loop Helpers section (direct-add)
    "counter_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "badge-plus",
        "selector_section": "Loop Helpers",
    },
    "repeat_counter_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [CONDITIONAL, UTILITY],
        "icon_name": "refresh-cw",
        "selector_section": "Loop Helpers",
    },
    # I/O — Input side
    "user_text_input_node": {
        "primary_family": INPUTS,
        "tags": [ACTIVE_OUTPUT],
        "icon_name": "keyboard",
        "group": "Text Input",
        "selector_section": "Text & Data",
    },
    "file_reader_node": {
        "primary_family": INPUTS,
        "tags": [FILE_IO],
        "icon_name": "file-text",
        "group": "File Reader",
        "selector_section": "Files",
    },
    # I/O — Output side (flat — no sections while the list is short)
    "text_output_node": {
        "primary_family": OUTPUTS,
        "tags": [PASSIVE_OUTPUT, ACTIVE_OUTPUT],
        "icon_name": "message-square-text",
        "group": "Text Output",
    },
    # Complex — AI section
    "chat_completion_node": {
        "primary_family": COMPLEX,
        "tags": [AI],
        "icon_name": "bot-message-square",
        "group": "AI Processing",
        "selector_section": "AI",
    },
    "image_generation_node": {
        "primary_family": COMPLEX,
        "tags": [AI],
        "icon_name": "image",
        "group": "AI Processing",
        "selector_section": "AI",
    },
    "embedding_node": {
        "primary_family": COMPLEX,
        "tags": [AI, UTILITY],
        "icon_name": "braces",
        "group": "AI Processing",
        "selector_section": "AI",
    },
    # Editor-only deleted-node record; hidden from the selector.
    "tombstone_node": {
        "primary_family": UTILITY_FAMILY,
        "tags": [UTILITY],
        "icon_name": "file-x",
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
        node_class.group = identity.get("group")
        node_class.selector_section = identity.get("selector_section")

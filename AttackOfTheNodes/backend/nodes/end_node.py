"""End Node: terminates a branch and records a completion message."""

from typing import Any, ClassVar, Dict, List

from ..contracts import RESULT_SOURCES, ROW_TYPES, collect_results, return_rows
from ..node_base import Node, NodeContext
from ..node_errors import NodeError
from ..node_category import NodeCategory
from ..output_entry import OutputLogEntry


class EndNode(Node):
    """Terminates a workflow branch by signaling done with no continuation."""

    terminates_branch: ClassVar[bool] = True

    node_type: ClassVar[str] = "end_node"
    display_name: ClassVar[str] = "End"
    description: ClassVar[str] = "Finish a path, adding an [END] completion line to the run output unless that line is turned off."
    category: ClassVar[str] = NodeCategory.FLOW

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = []

    default_config: ClassVar[Dict[str, Any]] = {
        "record_line": True, "message": "Branch completed", "return_end": False, "results": []}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        # Owner, 2026-10-20: an End can stay silent, so a scheduled check that
        # finds nothing prints nothing. On by default; saved Ends without the
        # key keep their line.
        "record_line": {
            "type": "boolean", "label": "Add a line to the output",
            "description": "Off: this End adds nothing to the output (good for runs that should stay silent)",
        },
        "message": {
            "type": "string", "label": "Line",
            "description": 'The output gets "[END] <line>", plus the incoming value when there is one',
            "required": True,
            "visible_when": {"record_line": True},
        },
        # Step 4a (C3): in a callable workflow, exactly one End is the Return
        # End; its rows are the workflow's results.
        "return_end": {
            "type": "boolean", "label": "Return End",
            "description": "This End fills the workflow result when it is called",
        },
        "results": {
            "type": "object_list", "label": "Results",
            "add_label": "Add result", "remove_label": "Remove result", "id_prefix": "out_",
            "visible_when": {"return_end": True},
            "item_schema": {
                "id": {"type": "string", "label": "Stable id"},
                "name": {"type": "string", "label": "Name"},
                "type": {"type": "select", "label": "Type", "options": list(ROW_TYPES)},
                "required": {"type": "boolean", "label": "Required"},
                "source": {"type": "select", "label": "Comes from", "options": list(RESULT_SOURCES)},
                "vault_key": {"type": "string", "label": "Vault key (blank = the name)"},
                "description": {"type": "string", "label": "Description"},
            },
        },
    }
    error_definitions: ClassVar[List[Dict[str, Any]]] = [
        {"code": "result_missing", "description": "A required result has no value when the Return End runs.",
         "retryable": False},
        {"code": "result_invalid", "description": "A result's value is not of its declared type.",
         "retryable": False},
        {"code": "result_conflict", "description": "The Return End ran a second time in one run.",
         "retryable": False},
    ]

    async def execute(self, context: NodeContext) -> None:
        if self.config.get("record_line", True):
            message = self.config.get("message", "Branch completed")
            full = f"[END] {message}"

            log = list(context.memory_bank.read_persistent("output_log", default=[]))
            log.append(
                OutputLogEntry(
                    full,
                    branch_id=context.branch_id,
                    node_id=context.node_id,
                )
            )
            context.memory_bank.store_persistent("output_log", log)

        # The engine offers publish_result only in a callable workflow.
        if self.config.get("return_end") and context.publish_result is not None:
            values, missing, invalid = collect_results(
                return_rows(self.config),
                lambda key: context.memory_bank.read_persistent(key),
                context.inputs.get("input"),
            )
            if missing:
                context.signal_error(NodeError(
                    "result_missing", "Required result(s) have no value: " + ", ".join(missing)))
                return
            if invalid:
                context.signal_error(NodeError(
                    "result_invalid", "; ".join(f"result '{n}': {why}" for n, why in invalid.items())))
                return
            if not context.publish_result(values):
                context.signal_error(NodeError(
                    "result_conflict", "The Return End ran a second time; a run returns one result"))
                return

        context.signal_done({"data": {}, "next_node_id": None, "terminate_branch": True})

"""Logger node — writes a timestamped entry to the output log."""

import datetime
from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory
from ...output_entry import OutputLogEntry


class LoggerNode(Node):
    """Appends a formatted line to the output log and passes input through."""

    node_type: ClassVar[str] = "logger_node"
    display_name: ClassVar[str] = "Logger"
    description: ClassVar[str] = "Logs the input value and passes it through"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "label": "",
        "include_input": True,
        "include_timestamp": False,
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "label": {"type": "string", "label": "Label", "required": False},
        "include_input": {"type": "boolean", "label": "Include Input", "required": False},
        "include_timestamp": {"type": "boolean", "label": "Include Timestamp", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        value = context.inputs.get("input", "")
        label = self.config.get("label", "") or self.display_name
        parts: List[str] = []
        if self.config.get("include_timestamp"):
            parts.append(datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
        parts.append(f"[{label}]")
        if self.config.get("include_input", True):
            parts.append(str(value))
        log_line = " ".join(parts)

        log = list(context.memory_bank.read_persistent("output_log", default=[]))
        log.append(
            OutputLogEntry(log_line, branch_id=context.branch_id, node_id=context.node_id)
        )
        context.memory_bank.store_persistent("output_log", log)

        context.signal_done({"data": {"default": value}})

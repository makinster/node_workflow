"""Probe node — logs detailed type and value info about the incoming value."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory
from ...output_entry import OutputLogEntry


class ProbeNode(Node):
    """Logs the type and repr of the input value then passes it through."""

    node_type: ClassVar[str] = "probe_node"
    display_name: ClassVar[str] = "Probe"
    description: ClassVar[str] = "Inspects and logs the incoming value with type info"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {"label": ""}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "label": {"type": "string", "label": "Label", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        value = context.inputs.get("input", "")
        label = self.config.get("label", "") or "Probe"
        line = f"[{label}] type={type(value).__name__} value={value!r}"

        log = list(context.memory_bank.read_persistent("output_log", default=[]))
        log.append(OutputLogEntry(line, branch_id=context.branch_id, node_id=context.node_id))
        context.memory_bank.store_persistent("output_log", log)

        context.signal_done({"data": {"default": value}})

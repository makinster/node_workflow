"""Memory snapshot node — dumps the persistent memory bank to the output log."""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory
from ...output_entry import OutputLogEntry


class MemorySnapshotNode(Node):
    """Writes all persistent memory keys/values to the output log."""

    node_type: ClassVar[str] = "memory_snapshot_node"
    display_name: ClassVar[str] = "Memory Snapshot"
    description: ClassVar[str] = "Dumps the persistent memory bank to the output log"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {"label": ""}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "label": {"type": "string", "label": "Label", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        label = self.config.get("label", "") or "Memory Snapshot"
        snapshot = context.memory_bank.get_state()["persistent"]
        lines = [f"{label}:"]
        for key, value in sorted(snapshot.items()):
            lines.append(f"  {key} = {value!r}")
        text = "\n".join(lines)

        log = list(context.memory_bank.read_persistent("output_log", default=[]))
        log.append(OutputLogEntry(text, branch_id=context.branch_id, node_id=context.node_id))
        context.memory_bank.store_persistent("output_log", log)

        context.signal_done({"data": {"default": context.inputs.get("input", "")}})

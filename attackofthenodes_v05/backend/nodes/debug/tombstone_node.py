"""Tombstone node — placeholder left behind when a node is deleted.

The tombstone preserves all existing connections so the validator can report
exactly which ports are now orphaned, rather than silently dropping wires.
Editing a tombstone in the TUI opens the NodeSelector to pick a replacement.
"""

from typing import Any, ClassVar, Dict, List

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class TombstoneNode(Node):
    """Deleted-node stub. Blocks execution and surfaces orphaned connections."""

    node_type: ClassVar[str] = "tombstone_node"
    display_name: ClassVar[str] = "Deleted Node"
    description: ClassVar[str] = "Placeholder for a deleted node — open to choose a replacement"
    category: ClassVar[str] = NodeCategory.DEBUG

    # Empty ports so every surviving connection is flagged by port-validity check
    input_ports: ClassVar[List[str]] = []
    output_ports: ClassVar[List[str]] = []

    # No user-editable schema — the config screen is replaced by NodeSelector
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    # original_* fields are written at delete-time; not schema-validated
    default_config: ClassVar[Dict[str, Any]] = {
        "original_type": "",
        "original_display_name": "",
        "original_input_ports": [],
        "original_output_ports": [],
    }

    async def execute(self, context: NodeContext) -> None:
        original = self.config.get("original_display_name") or self.config.get("original_type") or "unknown"
        context.signal_error(
            RuntimeError(
                f"Workflow contains a deleted node stub (was: {original}). "
                "Open it in the editor and choose a replacement."
            )
        )

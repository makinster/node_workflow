"""Wait-until node: blocks until configured nodes complete."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class WaitUntilNode(Node):
    """Pass input through after all configured target nodes complete."""

    node_type: ClassVar[str] = "wait_until_node"
    display_name: ClassVar[str] = "Wait Until"
    description: ClassVar[str] = "Waits for selected nodes before continuing"
    category: ClassVar[str] = NodeCategory.FLOW
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    default_config: ClassVar[Dict[str, Any]] = {
        "target_node_ids": "",
        "timeout_seconds": 0.0,
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "target_node_ids": {
            "type": "string",
            "label": "Target node ids",
            "description": "Comma-separated node ids to wait for",
            "required": False,
        },
        "timeout_seconds": {
            "type": "float",
            "label": "Timeout seconds",
            "description": "0 waits forever (default); a positive value limits the wait",
            "required": False,
            "min": 0.0,
        },
    }

    async def execute(self, context: NodeContext) -> None:
        target_ids = self._target_node_ids()
        timeout = float(self.config.get("timeout_seconds") or 0.0)
        try:
            # Pass zero explicitly: None means use the Supervisor's global
            # timeout, while zero disables the completion-wait timeout.
            await context.wait_for_nodes(target_ids, timeout)
        except asyncio.TimeoutError:
            context.signal_error(
                TimeoutError(f"Timed out waiting for nodes: {', '.join(target_ids)}")
            )
            return
        except Exception as exc:
            context.signal_error(exc)
            return
        context.signal_done({"data": {"default": context.inputs.get("input", "")}})

    def _target_node_ids(self) -> List[str]:
        configured = self.config.get("target_node_ids", "")
        if isinstance(configured, list):
            return [str(item).strip() for item in configured if str(item).strip()]
        return [
            item.strip()
            for item in str(configured).replace("\n", ",").split(",")
            if item.strip()
        ]

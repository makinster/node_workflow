"""Start Node: entry point for workflow execution."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory
from ..vault_declarations import legacy_output_keys


class StartNode(Node):
    """Entry point node. Emits a configurable greeting."""

    node_type: ClassVar[str] = "start_node"
    display_name: ClassVar[str] = "Start"
    description: ClassVar[str] = "Entry point for workflow execution"
    category: ClassVar[str] = NodeCategory.FLOW

    input_ports: ClassVar[List[str]] = []
    output_ports: ClassVar[List[str]] = ["default"]

    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {"name": "Greeting", "data_type": "string", "required": True,
                    "to": ["downstream", "vault"], "pass_through": False}
    }
    ui_hints: ClassVar[Dict[str, Any]] = {"standard_output": True, "output_value_fields": {"default": "greeting"}}

    default_config: ClassVar[Dict[str, Any]] = {
        "greeting": "Workflow started", "transient_output": True,
        "transient_outputs": [], "vault_write": False, "vault_write_key": "",
        "vault_write_description": "",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "greeting": {
            "type": "string",
            "description": "Message to emit when the workflow begins",
            "required": True,
        }
    }

    async def execute(self, context: NodeContext) -> None:
        greeting = str(self.config.get("greeting", "Workflow started"))
        if self.config.get("vault_write"):
            key = str(self.config.get("vault_write_key") or "").strip()
            if not key:
                context.signal_error(ValueError("Start Vault output requires a key"))
                return
            context.memory_bank.store_persistent(key, greeting, type_tag="string")
        for legacy_key in legacy_output_keys(self.config):
            context.memory_bank.store_persistent(legacy_key, greeting, type_tag="string")
        data = {"default": greeting} if self.config.get("transient_output", True) else {}
        context.signal_done({"data": data, "next_node_id": None})

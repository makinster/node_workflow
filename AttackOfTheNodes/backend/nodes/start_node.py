"""Start Node: entry point for workflow execution.

Step 4a: Start's **rows** are the workflow's inputs (its contract). Each row
has a name, a data type, a value (the default when the workflow runs
directly; a caller or ``aotn run --input`` fills it otherwise), ``required``,
and where it goes: downstream, the Vault, or both. One downstream row is sent
as itself, several as one object. A Start with no rows behaves as before: its
greeting is one string row (see ``backend/contracts.py``).
"""

from typing import Any, ClassVar, Dict, List, Optional

from ..contracts import (
    DEFAULT_GREETING, DESTINATIONS, ROW_TYPES, ContractError, downstream_payload,
    downstream_type, resolve_inputs, sends_downstream, sends_to_vault, start_rows,
    vault_key_for,
)
from ..node_base import Node, NodeContext
from ..node_category import NodeCategory
from ..vault_declarations import legacy_output_keys


class StartNode(Node):
    """Entry point node. Emits its rows (by default, a greeting)."""

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
        "greeting": DEFAULT_GREETING, "transient_output": True,
        "transient_outputs": [], "vault_write": False, "vault_write_key": "",
        "vault_write_description": "",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "greeting": {
            "type": "string",
            "description": "Message to emit when the workflow begins (used while Inputs is empty)",
            "required": True,
        },
        "rows": {
            "type": "object_list", "label": "Inputs",
            "description": "The workflow's inputs. When set, they replace the greeting.",
            "add_label": "Add input", "remove_label": "Remove input", "id_prefix": "in_",
            "item_schema": {
                "id": {"type": "string", "label": "Stable id"},
                "name": {"type": "string", "label": "Name"},
                "type": {"type": "select", "label": "Type", "options": list(ROW_TYPES)},
                "value": {"type": "string", "label": "Value (default when run directly)"},
                "required": {"type": "boolean", "label": "Required"},
                "to": {"type": "select", "label": "Send to", "options": list(DESTINATIONS)},
                "vault_key": {"type": "string", "label": "Vault key (blank = the name)"},
                "description": {"type": "string", "label": "Description"},
            },
        },
    }

    @classmethod
    def describe_output_ports(cls, config: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        rows = start_rows(config or {})
        if rows and rows[0].get("_legacy"):
            return {}
        data_type = downstream_type(rows)
        routed = [row["name"] for row in rows if sends_downstream(row)]
        name = routed[0] if len(routed) == 1 else "Inputs"
        return {"default": {"name": name, "data_type": data_type or "any",
                            "to": ["downstream", "vault"], "pass_through": False}}

    async def execute(self, context: NodeContext) -> None:
        rows = start_rows(self.config)
        values = context.run_inputs
        if values is None:
            # Outside a run started by MasterState (tests, direct execution).
            try:
                values = resolve_inputs(rows, {}, strict=False)
            except ContractError as exc:
                context.signal_error(exc)
                return
        if rows and rows[0].get("_legacy"):
            greeting = values.get("greeting", self.config.get("greeting", DEFAULT_GREETING))
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
            return
        for row in rows:
            if sends_to_vault(row) and row["name"] in values:
                context.memory_bank.store_persistent(vault_key_for(row), values[row["name"]], type_tag=row["type"])
        has_payload, payload = downstream_payload(rows, values)
        context.signal_done({"data": {"default": payload} if has_payload else {}, "next_node_id": None})

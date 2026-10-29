"""Node that formats inputs and persistent variables into one string."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory
from ..saved_values import finish


class ConcatNode(Node):
    """Combines input and memory values through a format template."""

    node_type: ClassVar[str] = "concat_node"
    display_name: ClassVar[str] = "Concat"
    description: ClassVar[str] = "Build one text from a template filled with the input and saved Vault values."
    category: ClassVar[str] = NodeCategory.DATA
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    output_port_metadata = {"default": {"name": "Text", "data_type": "string",
                                       "to": ["downstream", "vault"], "pass_through": True}}
    default_config: ClassVar[Dict[str, Any]] = {
        "template": "{input}",
        "vault_write": False, "vault_write_key": "", "vault_write_description": "",
        "transient_output": True, "dead_drop_passthrough": False,
        "transient_outputs": [],
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "template": {"type": "multiline", "required": True},
    }
    ui_hints = {"standard_output": True}

    async def execute(self, context: NodeContext) -> None:
        values = dict(context.memory_bank.get_state().get("persistent", {}))
        values.update(context.inputs)
        values["input"] = context.inputs.get("input", "")
        try:
            result = str(self.config.get("template", "{input}")).format_map(values)
        except (KeyError, IndexError, AttributeError, ValueError, TypeError) as exc:
            context.signal_error(ValueError(f"Concat template failed: {exc}"))
            return
        finish(self, context, result, "string")

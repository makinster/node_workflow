"""Branch Node: conditionally spawns execution paths."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext


class BranchNode(Node):
    """Routes execution based on a string comparison against its input."""

    node_type: ClassVar[str] = "branch_node"
    display_name: ClassVar[str] = "Branch"
    description: ClassVar[str] = "Routes execution based on string matching"

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["path_a", "path_b"]

    default_config: ClassVar[Dict[str, Any]] = {
        "condition": "string_match",
        "match_value": "yes",
        "match_mode": "equals",
        "case_sensitive": False,
        "on_match": "path_a",
        "on_no_match": "path_b",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "condition": {
            "type": "string",
            "description": "always_branch | path_a_only | path_b_only | string_match",
            "required": True,
            "options": ["string_match", "always_branch", "path_a_only", "path_b_only"],
        },
        "match_value": {
            "type": "string",
            "description": "String to compare against the input",
            "required": False,
        },
        "match_mode": {
            "type": "string",
            "description": "equals | contains",
            "required": False,
            "options": ["equals", "contains"],
        },
        "case_sensitive": {
            "type": "boolean",
            "description": "Whether string matching should respect case",
            "required": False,
        },
        "on_match": {
            "type": "string",
            "description": "Output port used when the match succeeds",
            "required": False,
            "options": ["path_a", "path_b"],
        },
        "on_no_match": {
            "type": "string",
            "description": "Output port used when the match fails",
            "required": False,
            "options": ["path_a", "path_b"],
        }
    }

    async def execute(self, context: NodeContext) -> None:
        condition = self.config.get("condition", "always_branch")
        input_value = context.inputs.get("input", "")

        if condition == "path_a_only":
            ports = ["path_a"]
        elif condition == "path_b_only":
            ports = ["path_b"]
        elif condition == "string_match":
            ports = [self._choose_string_match_port(input_value)]
        else:
            ports = ["path_a", "path_b"]

        for port in ports:
            context.memory_bank.store_transient(context.node_id, port, input_value)

        branches = [
            {"output_port": port, "initial_data": {"input": input_value}}
            for port in ports
        ]
        context.signal_done({"data": {}, "branches": branches})

    def _choose_string_match_port(self, input_value: Any) -> str:
        """Return on_match or on_no_match based on input string comparison."""
        input_text = str(input_value)
        match_text = str(self.config.get("match_value", ""))
        if not self.config.get("case_sensitive", False):
            input_text = input_text.lower()
            match_text = match_text.lower()

        match_mode = self.config.get("match_mode", "equals")
        if match_mode == "contains":
            matched = match_text in input_text
        else:
            matched = input_text == match_text

        port = self.config.get("on_match" if matched else "on_no_match", "")
        return port if port in self.output_ports else ("path_a" if matched else "path_b")

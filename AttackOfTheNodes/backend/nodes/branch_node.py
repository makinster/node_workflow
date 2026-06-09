"""Branch node: spawns parallel execution paths."""

from typing import Any, ClassVar, Dict, List

from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class BranchNode(Node):
    """Spawns parallel execution paths seeded from selected payloads."""

    node_type: ClassVar[str] = "branch_node"
    display_name: ClassVar[str] = "Branch"
    description: ClassVar[str] = "Spawns branching paths"
    category: ClassVar[str] = NodeCategory.FLOW

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["path_a", "path_b", "path_c", "path_d", "path_e"]

    default_config: ClassVar[Dict[str, Any]] = {
        "branch_count": 2,
        "branch_payload_sources": {},
        "condition": "always_branch",
        "match_value": "yes",
        "match_mode": "equals",
        "case_sensitive": False,
        "on_match": "path_a",
        "on_no_match": "path_b",
        "path_a_label": "Branch 1",
        "path_b_label": "Branch 2",
        "path_c_label": "Branch 3",
        "path_d_label": "Branch 4",
        "path_e_label": "Branch 5",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "branch_count": {
            "type": "integer",
            "label": "Branches",
            "description": "Number of parallel branch paths to spawn",
            "required": False,
            "min": 2,
            "max": 5,
        },
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
        },
        "path_a_label": {
            "type": "string",
            "label": "Branch 1 name",
            "description": "Editor display name for path_a",
            "required": False,
            "group": "Branch Names",
        },
        "path_b_label": {
            "type": "string",
            "label": "Branch 2 name",
            "description": "Editor display name for path_b",
            "required": False,
            "group": "Branch Names",
        },
        "path_c_label": {
            "type": "string",
            "label": "Branch 3 name",
            "description": "Editor display name for path_c",
            "required": False,
            "group": "Branch Names",
        },
        "path_d_label": {
            "type": "string",
            "label": "Branch 4 name",
            "description": "Editor display name for path_d",
            "required": False,
            "group": "Branch Names",
        },
        "path_e_label": {
            "type": "string",
            "label": "Branch 5 name",
            "description": "Editor display name for path_e",
            "required": False,
            "group": "Branch Names",
        },
    }

    async def execute(self, context: NodeContext) -> None:
        condition = self.config.get("condition", "always_branch")
        input_value = context.inputs.get("input", "")

        if condition == "path_a_only" and "branch_count" not in self.config:
            ports = ["path_a"]
        elif condition == "path_b_only" and "branch_count" not in self.config:
            ports = ["path_b"]
        elif condition == "string_match" and "branch_count" not in self.config:
            ports = [self._choose_string_match_port(input_value)]
        else:
            ports = self.output_ports[: self._branch_count()]

        seeded_values: Dict[str, Any] = {}
        for port in ports:
            value = self._seed_value_for_port(port, input_value, context)
            seeded_values[port] = value
            context.memory_bank.store_transient(context.node_id, port, value)

        branches = [
            {
                "output_port": port,
                "initial_data": {"input": seeded_values[port]},
            }
            for port in ports
        ]
        context.signal_done({"data": {}, "branches": branches})

    def _branch_count(self) -> int:
        try:
            count = int(self.config.get("branch_count", 2))
        except (TypeError, ValueError):
            count = 2
        return max(2, min(5, count))

    def _seed_value_for_port(
        self,
        port: str,
        input_value: Any,
        context: NodeContext,
    ) -> Any:
        sources = self.config.get("branch_payload_sources") or {}
        source = ""
        if isinstance(sources, dict):
            source = str(sources.get(port) or "").strip()
        if source.startswith("vault:"):
            return context.memory_bank.read_persistent(source.removeprefix("vault:"), input_value)
        return input_value

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

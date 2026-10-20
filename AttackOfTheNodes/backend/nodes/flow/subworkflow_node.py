"""Subworkflow node: run a saved subworkflow and wait for its results (Step 4b).

Design C11–C16 (``docs/SUBWORKFLOWS_PROPOSAL.md``). The node refers to the
child by workflow id (C12), maps each child input from a configured value,
the incoming payload, a Vault key or a Stash entry (by name, 4d), and continues on one ``default`` output
(C11). Each result goes downstream, to the Vault, or both: ``default``
carries the results marked downstream (one as itself, several as one
object). Failures are coded (``CALL_ERROR_DEFINITIONS``) and routable on
``error``. A cancelled call ends the node stopped, never as an error (C20).
"""

from typing import Any, ClassVar, Dict, List

from ...contracts import DESTINATIONS
from ...node_base import Node, NodeContext
from ...node_category import NodeCategory
from ...node_errors import NodeError
from ...stash_manager import StashManager, input_value
from ...subworkflow_calls import CALL_ERROR_DEFINITIONS

INPUT_SOURCES = ("Configured", "Upstream payload", "Vault", "Stash")


class SubworkflowNode(Node):
    """Call a subworkflow and continue with its results."""

    node_type: ClassVar[str] = "subworkflow_node"
    display_name: ClassVar[str] = "Subworkflow"
    default_alias: ClassVar[str] = "Subworkflow"
    description: ClassVar[str] = "Run a saved subworkflow and continue with its results"
    category: ClassVar[str] = NodeCategory.FLOW

    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["default"]
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {"name": "Results", "description": "The results sent to the next node", "data_type": "any"},
    }

    default_config: ClassVar[Dict[str, Any]] = {"workflow_id": "", "inputs": [], "results": []}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "workflow_id": {
            "type": "string", "label": "Subworkflow",
            "description": "The saved subworkflow's id (shown by name in the editor)",
        },
        "inputs": {
            "type": "object_list", "label": "Inputs",
            "add_label": "Add input", "remove_label": "Remove input", "id_prefix": "map_",
            "item_schema": {
                "id": {"type": "string", "label": "Stable id"},
                "name": {"type": "string", "label": "Subworkflow input"},
                "source": {"type": "select", "label": "From", "options": list(INPUT_SOURCES)},
                "value": {"type": "string", "label": "Value (Configured)"},
                "vault_key": {"type": "string", "label": "Vault key (Vault)"},
                "stash_entry": {"type": "string", "label": "Stash entry name (Stash)"},
            },
        },
        "results": {
            "type": "object_list", "label": "Results",
            "add_label": "Add result", "remove_label": "Remove result", "id_prefix": "res_",
            "item_schema": {
                "id": {"type": "string", "label": "Stable id"},
                "name": {"type": "string", "label": "Subworkflow result"},
                "to": {"type": "select", "label": "Send to", "options": list(DESTINATIONS)},
                "vault_key": {"type": "string", "label": "Vault key (blank = the result name)"},
            },
        },
    }
    error_definitions: ClassVar[List[Dict[str, Any]]] = [dict(d) for d in CALL_ERROR_DEFINITIONS]

    def _call_inputs(self, context: NodeContext) -> tuple[Dict[str, Any], List[str]]:
        values: Dict[str, Any] = {}
        text_names: List[str] = []
        for row in self.config.get("inputs") or []:
            if not isinstance(row, dict) or not str(row.get("name") or "").strip():
                continue
            name = str(row["name"]).strip()
            source = row.get("source") or "Configured"
            if source == "Upstream payload":
                if "input" in context.inputs:
                    values[name] = context.inputs["input"]
            elif source == "Vault":
                key = str(row.get("vault_key") or "").strip()
                missing = object()
                value = context.memory_bank.read_persistent(key, default=missing) if key else missing
                if value is not missing:
                    values[name] = value
            elif source == "Stash":
                entry_name = str(row.get("stash_entry") or "").strip()
                entry = StashManager().get(entry_name) if entry_name else None
                if entry is None:
                    raise NodeError("child_input_missing", f"Input '{name}': no Stash entry "
                                    f"{entry_name!r}", details={"input": name, "stash_entry": entry_name})
                values[name] = input_value(entry)
                if entry["type"] != "file":
                    text_names.append(name)
            else:
                values[name] = row.get("value", "")
                if isinstance(values[name], str):
                    text_names.append(name)
        return values, text_names

    async def execute(self, context: NodeContext) -> None:
        if context.call_subworkflow is None:
            context.signal_error(NodeError("child_failed", "A subworkflow can only be called during a run"))
            return
        try:
            inputs, text_names = self._call_inputs(context)
            results = await context.call_subworkflow(
                str(self.config.get("workflow_id") or ""), inputs, text_names)
        except NodeError as exc:
            context.signal_error(exc)
            return
        routes = {str(row.get("name") or ""): row for row in self.config.get("results") or []
                  if isinstance(row, dict)}
        downstream: Dict[str, Any] = {}
        for name, value in results.items():
            route = routes.get(name) or {}
            to = route.get("to") or "Downstream"
            if to in ("Vault", "Both"):
                key = str(route.get("vault_key") or "").strip() or name
                context.memory_bank.store_persistent(key, value)
            if to in ("Downstream", "Both"):
                downstream[name] = value
        if not downstream:
            context.signal_done({"data": {}})
        elif len(downstream) == 1:
            context.signal_done({"data": {"default": next(iter(downstream.values()))}})
        else:
            context.signal_done({"data": {"default": downstream}})

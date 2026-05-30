"""
Validator for AttackOfTheNodes v0.5.

Runs static checks on a loaded workflow. Errors block execution; warnings are
informational, such as loose nodes unreachable from the start node.
"""

from typing import Any, Dict, List, Set

from .node_factory import NodeFactory
from .workflow_map import WorkflowMap

def derive_input_sources(
    all_nodes: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, str]]]:
    """Derive node and membank input sources from workflow structure."""
    input_sources: Dict[str, List[Dict[str, str]]] = {}
    for node_id, data in all_nodes.items():
        sources: List[Dict[str, str]] = []
        for conn in data.get("connections", {}).get("inputs", []):
            source_id = conn.get("source_node_id")
            if source_id:
                sources.append(
                    {
                        "type": "node",
                        "source_id": source_id,
                        "port": conn.get("source_port", "default"),
                    }
                )

        config = data.get("config") or {}
        membank_inputs = config.get("membank_inputs") or []
        if isinstance(membank_inputs, list):
            for entry in membank_inputs:
                source_id = _membank_source_id(entry)
                if source_id:
                    sources.append({"type": "membank", "source_id": source_id})
        input_sources[node_id] = sources
    return input_sources


def validate_workflow(workflow_map: WorkflowMap, factory: NodeFactory) -> Dict[str, Any]:
    """Validate the loaded workflow structure."""
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    all_nodes = workflow_map.get_all_node_data()

    start_ids = [
        node_id for node_id, data in all_nodes.items() if data["type"] == "start_node"
    ]
    if len(start_ids) == 0:
        errors.append({"node_id": "", "message": "Workflow has no start node"})
    elif len(start_ids) > 1:
        errors.append(
            {
                "node_id": "",
                "message": f"Workflow has {len(start_ids)} start nodes; expected exactly 1",
            }
        )

    for node_id, data in all_nodes.items():
        if not factory.is_valid_node_type(data["type"]):
            errors.append(
                {"node_id": node_id, "message": f"Unknown node type: {data['type']}"}
            )

    node_ids = set(all_nodes.keys())
    for node_id, data in all_nodes.items():
        for conn in data.get("connections", {}).get("outputs", []):
            target = conn.get("target_node_id")
            if target and target not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Output connection targets missing node: {target}",
                    }
                )
        for conn in data.get("connections", {}).get("inputs", []):
            source = conn.get("source_node_id")
            if source and source not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Input connection from missing node: {source}",
                    }
                )

    declared_membank_outputs = _declared_membank_outputs(all_nodes)
    for node_id, sources in derive_input_sources(all_nodes).items():
        for source in sources:
            source_type = source.get("type")
            source_id = source.get("source_id", "")
            if source_type == "node" and source_id not in node_ids:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Input source missing node: {source_id}",
                    }
                )
            elif source_type == "membank" and source_id not in declared_membank_outputs:
                errors.append(
                    {
                        "node_id": node_id,
                        "message": f"Membank input source not declared: {source_id}",
                    }
                )

    if len(start_ids) == 1:
        reachable: Set[str] = set()
        _dfs_reachable(start_ids[0], all_nodes, reachable)
        for node_id in node_ids:
            if node_id not in reachable:
                warnings.append(
                    {
                        "node_id": node_id,
                        "message": "Node is not reachable from the start node",
                    }
                )

    return {"success": not errors, "errors": errors, "warnings": warnings}


def _dfs_reachable(
    node_id: str, all_nodes: Dict[str, Dict[str, Any]], visited: Set[str]
) -> None:
    """Record every node reachable from node_id."""
    if node_id in visited:
        return
    visited.add(node_id)
    data = all_nodes.get(node_id)
    if data is None:
        return
    for conn in data.get("connections", {}).get("outputs", []):
        target = conn.get("target_node_id")
        if target and target in all_nodes:
            _dfs_reachable(target, all_nodes, visited)

def _declared_membank_outputs(all_nodes: Dict[str, Dict[str, Any]]) -> Set[str]:
    """Collect declared memory-bank output ids from node configs."""
    declared: Set[str] = set()
    for data in all_nodes.values():
        config = data.get("config") or {}
        membank_outputs = config.get("membank_outputs") or []
        if not isinstance(membank_outputs, list):
            continue
        for entry in membank_outputs:
            source_id = _membank_source_id(entry)
            if source_id:
                declared.add(source_id)
    return declared


def _membank_source_id(entry: Any) -> str:
    """Normalize a membank input/output entry to an id string."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return str(entry.get("source_id") or entry.get("id") or "")
    return ""

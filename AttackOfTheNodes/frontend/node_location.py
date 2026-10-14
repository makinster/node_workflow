"""Where a node is, in words people use (owner, 2026-10-14).

Error and validation messages open with a plain line naming the node, its
type, its depth from Start and the branch it sits on, for example
``Fetch (HTTP Request) · depth 1 · Main path``; the node ID goes on the line
below.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Optional

from frontend.node_io_display import metadata_for_type, node_display_name

MAIN_PATH = "Main path"


def node_depth(workflow_map, node_id: str) -> Optional[int]:
    """Steps from Start along connections (Start is 0); None if unreachable."""
    start_id = workflow_map.find_start_node_id()
    if not start_id:
        return None
    depths = {start_id: 0}
    queue = deque([start_id])
    while queue:
        current = queue.popleft()
        if current == node_id:
            return depths[current]
        node = workflow_map.get_node_data(current) or {}
        for conn in (node.get("connections") or {}).get("outputs") or []:
            target = str(conn.get("target_node_id") or "")
            if target and target not in depths:
                depths[target] = depths[current] + 1
                queue.append(target)
    return None


def node_branch(workflow_map, node_id: str) -> str:
    """The branch path the node sits on, or "Main path"."""
    from frontend.screens.node_config import _branch_contexts_by_node

    contexts = _branch_contexts_by_node(workflow_map).get(node_id) or []
    paths = [str(context.get("branch_path") or context.get("branch_label") or "")
             for context in contexts]
    paths = [path for path in paths if path]
    return " / ".join(dict.fromkeys(paths)) if paths else MAIN_PATH


def node_heading(workflow_map, factory, node_id: str) -> str:
    """``<name> (<type>) · depth <n> · <branch>``; parts that are unknown are left out."""
    node = workflow_map.get_node_data(node_id) if node_id else None
    if not node:
        return f"Unknown node {node_id}" if node_id else "Workflow"
    name = node_display_name(node_id, node)
    metadata: Any = metadata_for_type(factory, str(node.get("type") or "")) if factory else None
    type_name = str((metadata or {}).get("display_name") or node.get("type") or "")
    parts = [f"{name} ({type_name})" if type_name and type_name != name else name]
    depth = node_depth(workflow_map, node_id)
    if depth is not None:
        parts.append(f"depth {depth}")
        parts.append(node_branch(workflow_map, node_id))
    else:
        parts.append("not reachable from Start")
    return " · ".join(parts)

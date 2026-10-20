"""What the editor shows about a called subworkflow (Step 4c).

``describe(workflow_id)`` gives the child's name, inputs, results and the
nodes that may ask for input (``backend.contracts.call_contract``). Results
are cached by the saved file's modification time, so map refreshes do not
re-read every child; a saved edit is picked up on the next look.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend import persistence
from backend.contracts import call_contract

#: workflow id -> (saved-file times of it and every subworkflow it calls, info)
_cache: Dict[str, Tuple[Dict[str, float], Optional[Dict[str, Any]]]] = {}


def _stamp(workflow_id: str) -> float:
    try:
        return (persistence.WORKFLOWS_DIR / f"{workflow_id}.json").stat().st_mtime
    except OSError:
        return -1.0


def describe(workflow_id: str) -> Optional[Dict[str, Any]]:
    """The subworkflow as a caller sees it, or None when it is not saved."""
    workflow_id = str(workflow_id or "").strip()
    if not workflow_id:
        return None
    cached = _cache.get(workflow_id)
    if cached is not None and all(_stamp(wid) == stamp for wid, stamp in cached[0].items()):
        return cached[1]
    # A nested edit (a prompt added or removed deeper down) changes "may ask",
    # so every file read is part of the cache key.
    stamps = {workflow_id: _stamp(workflow_id)}

    def load(wid: str) -> Optional[Dict[str, Any]]:
        stamps[wid] = _stamp(wid)
        return persistence.load_workflow(wid)

    data = persistence.load_workflow(workflow_id) if stamps[workflow_id] >= 0 else None
    info = call_contract(data, load) if data else None
    _cache[workflow_id] = (stamps, info)
    return info


def subworkflows(exclude: str = "") -> List[Dict[str, Any]]:
    """Saved subworkflows by name, without ``exclude`` (the workflow being edited)."""
    return [entry for entry in persistence.list_workflows()
            if entry.get("callable") and entry.get("id") != exclude]


def input_mapping(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The node's input rows by input name."""
    return {str(row.get("name") or "").strip(): dict(row) for row in config.get("inputs") or []
            if isinstance(row, dict) and str(row.get("name") or "").strip()}


def result_routes(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The node's result rows by result name."""
    return {str(row.get("name") or "").strip(): dict(row) for row in config.get("results") or []
            if isinstance(row, dict) and str(row.get("name") or "").strip()}


def source_text(row: Dict[str, Any], mapping: Optional[Dict[str, Any]]) -> str:
    """Where an input's value comes from, in the owner-approved words."""
    if mapping is None:
        value = row.get("value")
        if value is None or value == "":
            return "needs a value" if row.get("required") else "left empty"
        shown = f'"{value}"' if row.get("type") == "string" else str(value)
        return f"its default: {shown}"
    source = mapping.get("source") or "Configured"
    if source == "Upstream payload":
        return "the incoming payload"
    if source == "Vault":
        return f'Vault key "{mapping.get("vault_key") or ""}"'
    value = mapping.get("value", "")
    if row.get("type") == "string":
        return f'typed: "{value}"'
    from frontend.widgets.contract_rows import default_text

    return f"typed: {default_text(value)}"


def route_text(name: str, route: Optional[Dict[str, Any]]) -> str:
    """Where a result goes."""
    to = (route or {}).get("to") or "Downstream"
    key = str((route or {}).get("vault_key") or "").strip() or name
    return {"Downstream": "next node", "Vault": f'Vault key "{key}"',
            "Both": f'next node and Vault key "{key}"'}.get(to, "next node")


def next_node_text(results: List[Dict[str, Any]], routes: Dict[str, Dict[str, Any]]) -> str:
    """"The next node receives: a" (several go as one object)."""
    names = [row["name"] for row in results
             if ((routes.get(row["name"]) or {}).get("to") or "Downstream") in ("Downstream", "Both")]
    if not names:
        return "The next node receives: nothing"
    if len(names) == 1:
        return f"The next node receives: {names[0]}"
    return f"The next node receives: {', '.join(names)} (as one object)"


def vault_count(config: Dict[str, Any], info: Optional[Dict[str, Any]]) -> int:
    """How many results go to the Vault (the map's ➥ count)."""
    routes = result_routes(config)
    names = [row["name"] for row in (info or {}).get("results") or []] or list(routes)
    return sum(1 for name in names if ((routes.get(name) or {}).get("to") or "Downstream") in ("Vault", "Both"))

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


Parts = List[Tuple[str, str]]


def _shown(row: Dict[str, Any], value: Any) -> str:
    if row.get("type") == "string":
        return f'"{value}"'
    from frontend.widgets.contract_rows import default_text

    return default_text(value)


def source_parts(row: Dict[str, Any], mapping: Optional[Dict[str, Any]]) -> Parts:
    """Where an input's value comes from, as (text, colour role) parts:
    the words in SOURCE, a Vault key name in KEY, a value in VALUE."""
    if mapping is None:
        value = row.get("value")
        if value is None or value == "":
            return [("needs a value" if row.get("required") else "left empty", "SOURCE")]
        return [("its default: ", "SOURCE"), (_shown(row, value), "VALUE")]
    source = mapping.get("source") or "Configured"
    if source == "Upstream payload":
        return [("the incoming payload", "SOURCE")]
    if source == "Vault":
        return [("Vault key ", "SOURCE"), (f'"{mapping.get("vault_key") or ""}"', "KEY")]
    if source == "Stash":
        return stash_parts(str(mapping.get("stash_entry") or ""))
    return [("typed: ", "SOURCE"), (_shown(row, mapping.get("value", "")), "VALUE")]


def stash_parts(entry_name: str, check: bool = True) -> Parts:
    """``Stash entry "name"``, plus ``✗ no such Stash entry`` when this
    machine's Stash has no entry by that name (4d: a validation error)."""
    parts: Parts = [("Stash entry ", "SOURCE"), (f'"{entry_name}"', "KEY")]
    if check:
        from backend.stash_manager import StashManager

        if not entry_name or StashManager().get_by_name(entry_name) is None:
            parts += [("  ", "SOURCE"), ("✗ no such Stash entry", "ERROR")]
    return parts


def route_parts(name: str, route: Optional[Dict[str, Any]]) -> Parts:
    """Where a result goes, as (text, colour role) parts."""
    to = (route or {}).get("to") or "Downstream"
    key = str((route or {}).get("vault_key") or "").strip() or name
    if to == "Vault":
        return [("Vault key ", "SOURCE"), (f'"{key}"', "KEY")]
    if to == "Both":
        return [("next node and Vault key ", "SOURCE"), (f'"{key}"', "KEY")]
    return [("next node", "SOURCE")]


def source_text(row: Dict[str, Any], mapping: Optional[Dict[str, Any]]) -> str:
    """Where an input's value comes from, in the owner-approved words."""
    return "".join(text for text, _ in source_parts(row, mapping))


def route_text(name: str, route: Optional[Dict[str, Any]]) -> str:
    """Where a result goes."""
    return "".join(text for text, _ in route_parts(name, route))


def parts_text(parts: Parts) -> "Text":
    """Coloured Rich text for parts (colours read when drawn)."""
    from rich.text import Text

    from frontend import colors

    out = Text()
    for text, role in parts:
        out.append(text, style=getattr(colors, role))
    return out


def parts_markup(parts: Parts) -> str:
    """The same parts as escaped Rich markup."""
    from rich.markup import escape

    from frontend import colors

    return "".join(f"[{getattr(colors, role)}]{escape(text)}[/]" for text, role in parts)


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

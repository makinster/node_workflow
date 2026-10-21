"""Where System nodes may look (AI coordination decision C7, owner 2026-10-20).

System nodes (Disk space, Git status, File age) read the state of this
machine. Each one runs a fixed operation; only its folder or file changes.
The folders they may look in are listed in Options as ``system_node_folders``
(separated by ``;``, ``~`` allowed; default: the home folder), so a workflow
received from someone else cannot inspect the rest of the machine.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, List, Optional

from .node_errors import NodeError

SETTING = "system_node_folders"
DEFAULT_FOLDERS = "~"


def allowed_folders(get_setting: Optional[Callable[[str], Any]]) -> List[Path]:
    """The allowed folders. An absent setting means the default (home); an
    empty or non-text value means none (#104 review: clearing the field must
    remove access, not restore the home folder)."""
    raw = get_setting(SETTING) if get_setting is not None else None
    if raw is None:
        raw = DEFAULT_FOLDERS
    if not isinstance(raw, str):
        return []
    text = raw
    folders = []
    for part in text.split(";"):
        part = part.strip()
        if part:
            folders.append(Path(os.path.expanduser(part)).resolve())
    return folders


def checked_path(raw: Any, get_setting: Optional[Callable[[str], Any]], what: str = "folder") -> Path:
    """The resolved path, if it exists and lies inside an allowed folder;
    otherwise a NodeError coded ``folder_missing`` or ``not_allowed``."""
    text = str(raw or "").strip()
    if not text:
        raise NodeError("folder_missing", f"Choose a {what}")
    path = Path(os.path.expanduser(text)).resolve()
    allowed = allowed_folders(get_setting)
    if not any(path == folder or folder in path.parents for folder in allowed):
        listed = "; ".join(str(folder) for folder in allowed) or "none"
        raise NodeError("not_allowed", f"{path} is outside the folders allowed in Options ({listed})",
                        details={"path": str(path), "allowed": [str(f) for f in allowed]})
    if not path.exists():
        raise NodeError("folder_missing", f"{path} does not exist", details={"path": str(path)})
    return path


def finish(node: Any, context: Any, value: Any, type_tag: str) -> None:
    """Standard output routing: optional Vault copy, then the next node."""
    config = node.config
    if config.get("vault_write"):
        key = str(config.get("vault_write_key") or "").strip()
        if not key:
            context.signal_error(ValueError(f"{node.display_name}: enter a Vault output key."))
            return
        context.memory_bank.store_persistent(key, value, type_tag=type_tag)
    context.signal_done({"data": {"default": value} if config.get("transient_output", True) else {}})

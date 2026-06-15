"""
Run-scoped resource session for AttackOfTheNodes.

One RunSession exists per workflow run. It opens and caches resource handles
(files now; streams, listeners, and browser sessions later) so nodes in the
same run share access, then closes everything at run finalization.

MasterState owns the lifecycle: create at run start, close_all() at run end.
Nodes reach the session only through NodeContext while executing. The session
is UI-agnostic and must never import from frontend code.

Design note: docs/archive/plans/RUNTIME_RESOURCE_SESSION.md
"""

import logging
from pathlib import Path
from typing import IO, Any, Callable, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


class RunSession:
    """Holds open resource handles for the duration of one workflow run."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._closed = False
        self._files: Dict[Tuple[str, str], IO] = {}
        self._resources: Dict[str, Any] = {}
        self._close_hooks: List[Tuple[Any, Callable[[Any], None]]] = []

    @property
    def run_id(self) -> str:
        """Run this session belongs to."""
        return self._run_id

    @property
    def is_closed(self) -> bool:
        """True after close_all() has run."""
        return self._closed

    def open_file(self, path: str, mode: str = "r", encoding: str = "utf-8") -> IO:
        """Open a file handle, caching it by (resolved path, mode) for reuse."""
        self._ensure_open()
        resolved = str(Path(str(path)).expanduser().resolve())
        key = (resolved, mode)
        cached = self._files.get(key)
        if cached is not None and not cached.closed:
            return cached
        if "b" in mode:
            handle = open(resolved, mode)
        else:
            handle = open(resolved, mode, encoding=encoding)
        self._files[key] = handle
        self._close_hooks.append((handle, lambda h: h.close()))
        return handle

    def register_resource(
        self,
        key: str,
        handle: Any,
        close: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """Register an arbitrary handle under a key, with an optional close hook."""
        self._ensure_open()
        self._resources[key] = handle
        if close is not None:
            self._close_hooks.append((handle, close))

    def get_resource(self, key: str) -> Optional[Any]:
        """Return a previously registered resource, or None."""
        return self._resources.get(key)

    def validate_path(self, path: str) -> Tuple[bool, str]:
        """Return (ok, reason) for a path without opening it."""
        text = str(path).strip()
        if not text:
            return False, "Path is empty"
        resolved = Path(text).expanduser()
        if not resolved.exists():
            return False, f"Path not found: {resolved}"
        return True, ""

    def close_all(self) -> None:
        """Close every registered handle. Safe to call more than once."""
        if self._closed:
            return
        self._closed = True
        for handle, close in reversed(self._close_hooks):
            try:
                close(handle)
            except Exception:
                logger.exception(
                    "Error closing resource for run %s: %r", self._run_id, handle
                )
        self._close_hooks.clear()
        self._files.clear()
        self._resources.clear()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError(
                f"RunSession for run {self._run_id} is closed; "
                "resources are only available while the run is active"
            )

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
import re
from copy import deepcopy
from pathlib import Path
from typing import IO, Any, Callable, Dict, List, Optional, Tuple

from . import persistence
from .file_refs import LIFETIME_KEPT, LIFETIME_RUN, file_reference, reference_path


logger = logging.getLogger(__name__)


class RunSession:
    """Holds open resource handles for the duration of one workflow run."""

    def __init__(self, run_id: str, files_root: Optional[Path] = None) -> None:
        self._run_id = run_id
        self._closed = False
        # R4: run-owned files live under <files_root>/<run_id>/. The root is
        # read at first use so AOTN_DATA_DIR / tests can redirect it.
        self._files_root = Path(files_root) if files_root is not None else None
        self._run_files: Dict[str, str] = {}
        self._files: Dict[Tuple[str, str], IO] = {}
        self._resources: Dict[str, Any] = {}
        self._close_hooks: List[Tuple[Any, Callable[[Any], None]]] = []
        self._chat_sessions: Dict[str, List[Dict[str, str]]] = {}

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

    def get_or_create_chat_session(self, session_key: str) -> List[Dict[str, str]]:
        """Return the named chat history list, creating an empty one if needed."""
        self._ensure_open()
        if session_key not in self._chat_sessions:
            self._chat_sessions[session_key] = []
        return self._chat_sessions[session_key]

    def append_chat_message(self, session_key: str, role: str, content: str) -> None:
        """Append a message to the named chat session."""
        history = self.get_or_create_chat_session(session_key)
        history.append({"role": role, "content": content})

    def get_chat_history(self, session_key: str) -> List[Dict[str, str]]:
        """Return a deep copy of the named chat session's history."""
        return deepcopy(self._chat_sessions.get(session_key, []))

    # -- run-owned temporary files (R4) ----------------------------------------

    @property
    def run_files_dir(self) -> Path:
        """Directory holding this run's run-owned files (may not exist yet)."""
        root = self._files_root if self._files_root is not None else persistence.RUN_FILES_DIR
        return Path(root) / self._run_id

    def new_run_file(self, name: str) -> Path:
        """Reserve a new run-owned file path (lifetime ``run``) and return it.

        The name is reduced to safe characters; a counter keeps it unique.
        The caller writes the file.
        """
        self._ensure_open()
        directory = self.run_files_dir
        directory.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(str(name)).name).strip("._") or "file"
        stem, dot, suffix = safe.partition(".")
        candidate = directory / safe
        counter = 2
        while candidate.exists() or str(candidate.resolve()) in self._run_files:
            candidate = directory / f"{stem}-{counter}{dot}{suffix}"
            counter += 1
        resolved = str(candidate.resolve())
        self._run_files[resolved] = LIFETIME_RUN
        return Path(resolved)

    def run_file_reference(self, path: Any) -> Dict[str, str]:
        """The `file` reference for a run-owned file, with its lifetime."""
        resolved = str(Path(reference_path(path) or str(path)).resolve())
        return file_reference(resolved, self._run_files.get(resolved, LIFETIME_KEPT))

    def keep_file(self, value: Any) -> Dict[str, str]:
        """Mark a run-owned file ``kept`` so it survives the run; return its ref."""
        resolved = str(Path(reference_path(value) or str(value)).resolve())
        if resolved in self._run_files:
            self._run_files[resolved] = LIFETIME_KEPT
        return file_reference(resolved, LIFETIME_KEPT)

    def file_lifetime(self, value: Any) -> Optional[str]:
        """Lifetime of a file this run created, or None if it is not run-owned."""
        resolved = str(Path(reference_path(value) or str(value)).resolve())
        return self._run_files.get(resolved)

    def _delete_run_files(self) -> None:
        for path, lifetime in self._run_files.items():
            if lifetime != LIFETIME_RUN:
                continue
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not delete run file %s (run %s)", path, self._run_id)
        directory = self.run_files_dir
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        except OSError:
            logger.exception("Could not remove run files directory %s", directory)

    def validate_path(self, path: str) -> Tuple[bool, str]:
        """Return (ok, reason) for a path without opening it."""
        text = str(path).strip()
        if not text:
            return False, "Path is empty"
        resolved = Path(text).expanduser()
        if not resolved.exists():
            return False, f"Path not found: {resolved}"
        return True, ""

    def close_all(self, delete_run_files: bool = False) -> None:
        """Close every registered handle. Safe to call more than once.

        With ``delete_run_files`` (the run succeeded), run-owned files whose
        lifetime is still ``run`` are deleted after the handles close. By
        default they are kept, so a failed, stopped or abandoned run leaves
        them for debugging (R4).
        """
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
        if delete_run_files:
            self._delete_run_files()
        elif any(lifetime == LIFETIME_RUN for lifetime in self._run_files.values()):
            logger.info(
                "Run %s did not succeed; keeping its run files in %s",
                self._run_id, self.run_files_dir,
            )
        self._files.clear()
        self._resources.clear()
        self._chat_sessions.clear()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError(
                f"RunSession for run {self._run_id} is closed; "
                "resources are only available while the run is active"
            )

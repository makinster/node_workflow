"""Typed `file` reference helpers (D2, docs/FILE_OUTPUT_BUILD_PLAN.md).

A `file` reference is the JSON-serializable dict that travels between nodes
and into the vault in place of a Python file handle:

    {"type": "file", "ref_key": "file:<resolved path>", "path": "<resolved path>"}

R4 (distributed plan): a reference may carry ``lifetime``: ``"run"`` for a
run-owned temporary file (deleted when the run succeeds, kept when it fails)
or ``"kept"``. An absent lifetime means ``"kept"``, so older references are
unchanged.

The ref key doubles as the RunSession resource key, keyed by file identity so
every node touching the same file resolves the same registration (D6). The
path rides along for cross-run reconstruction and for consumers that only
need the location (D2 cross-run note: references die with the run; the path
string is the durable part).
"""

from typing import Any, Dict, Optional


FILE_REF_TYPE = "file"
LIFETIME_RUN = "run"
LIFETIME_KEPT = "kept"


def file_reference(path: str, lifetime: Optional[str] = None) -> Dict[str, str]:
    """Build the typed `file` reference for a resolved path."""
    ref = {"type": FILE_REF_TYPE, "ref_key": f"file:{path}", "path": path}
    if lifetime is not None:
        if lifetime not in (LIFETIME_RUN, LIFETIME_KEPT):
            raise ValueError(f"Unknown file lifetime {lifetime!r}")
        ref["lifetime"] = lifetime
    return ref


def reference_lifetime(value: Any) -> str:
    """The lifetime of a file reference; absent (or a raw path) means kept."""
    if is_file_reference(value) and value.get("lifetime") == LIFETIME_RUN:
        return LIFETIME_RUN
    return LIFETIME_KEPT


def is_file_reference(value: Any) -> bool:
    """Whether *value* is a typed `file` reference dict."""
    return isinstance(value, dict) and value.get("type") == FILE_REF_TYPE


def reference_path(value: Any) -> str:
    """Extract a filesystem path from a file reference or raw path value.

    Accepts a `file` reference dict (returns its `path`) or a raw path string. Returns "" for None/empty input.
    """
    if is_file_reference(value):
        value = value.get("path")
    return value.strip() if isinstance(value, str) else ""


def reference_key(value: Any) -> str:
    """Extract the RunSession ref key from a file reference or path value.

    A raw path derives the same identity key `file_reference` would build,
    so path-configured consumers and reference-fed consumers agree.
    """
    if is_file_reference(value):
        return str(value.get("ref_key") or "").strip()
    path = reference_path(value)
    return f"file:{path}" if path else ""

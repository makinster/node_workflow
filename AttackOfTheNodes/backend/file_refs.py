"""Typed `file` reference helpers (D2, docs/FILE_OUTPUT_BUILD_PLAN.md).

A `file` reference is the JSON-serializable dict that travels between nodes
and into the vault in place of a Python file handle:

    {"type": "file", "ref_key": "file:<resolved path>", "path": "<resolved path>"}

The ref key doubles as the RunSession resource key, keyed by file identity so
every node touching the same file resolves the same registration (D6). The
path rides along for cross-run reconstruction and for consumers that only
need the location (D2 cross-run note: references die with the run; the path
string is the durable part).
"""

from typing import Any, Dict


FILE_REF_TYPE = "file"


def file_reference(path: str) -> Dict[str, str]:
    """Build the typed `file` reference for a resolved path."""
    return {"type": FILE_REF_TYPE, "ref_key": f"file:{path}", "path": path}


def is_file_reference(value: Any) -> bool:
    """Whether *value* is a typed `file` reference dict."""
    return isinstance(value, dict) and value.get("type") == FILE_REF_TYPE


def reference_path(value: Any) -> str:
    """Extract a filesystem path from a file reference or raw path value.

    Accepts a `file` reference dict (returns its `path`) or any raw value
    (stringified). Returns "" for None/empty input.
    """
    if is_file_reference(value):
        value = value.get("path")
    return str(value or "").strip()


def reference_key(value: Any) -> str:
    """Extract the RunSession ref key from a file reference or path value.

    A raw path derives the same identity key `file_reference` would build,
    so path-configured consumers and reference-fed consumers agree.
    """
    if is_file_reference(value):
        return str(value.get("ref_key") or "").strip()
    path = reference_path(value)
    return f"file:{path}" if path else ""

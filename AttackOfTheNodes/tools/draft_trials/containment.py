"""Validate a trial tree before importing backend services or creating artifacts.

This is a preflight over an owner-controlled directory, not an OS sandbox against
concurrent directory replacement. It never opens library files or Secrets.
"""

import json
from pathlib import Path
import stat

PREPARATION_NOTE = (
    "Step 2 requires separate owner approval. Owner adds key through app. "
    "Harness never copies Secrets."
)


class ContainmentError(ValueError):
    """The trial path or preparation record cannot safely be used."""


def checked_root(raw):
    root = Path(raw)
    if not root.is_absolute() or ".." in root.parts:
        raise ContainmentError("trial root must be absolute without '..' components")
    # lstat, not exists/is_dir, also catches dangling symlinks and special files.
    for path in (root, *root.parents):
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ContainmentError(f"symlink in trial-root ancestry: {path}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ContainmentError(f"trial-root component is not a directory: {path}")
    return root.resolve()


def validate_tree(root):
    """Reject links, special entries and resolved escapes without reading files."""
    root = checked_root(root)
    pending = [root]
    while pending:
        path = pending.pop()
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ContainmentError(f"symlink in trial root: {path}")
        if not path.resolve(strict=True).is_relative_to(root):
            raise ContainmentError(f"resolved path escapes trial root: {path}")
        if stat.S_ISDIR(metadata.st_mode):
            pending.extend(path.iterdir())
        elif not stat.S_ISREG(metadata.st_mode):
            raise ContainmentError(f"non-regular entry in trial root: {path}")
        elif metadata.st_nlink != 1:
            # A hard link can mutate an outside inode despite resolving inside.
            raise ContainmentError(f"hard-linked file in trial root: {path}")
    return root


def preparation_record(root):
    return {
        "version": 1,
        "library": str(root / "library"),
        "note": PREPARATION_NOTE,
    }


def unique_fields(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise ContainmentError("duplicate field in prepared.json")
        record[key] = value
    return record


def validate_prepared(root):
    """Call only after validate_tree has inspected every entry in the root."""
    if {path.name for path in root.iterdir()} != {"prepared.json", "library"}:
        raise ContainmentError("trial root must be fresh or an untouched prepared root")
    marker = root / "prepared.json"
    library = root / "library"
    if not library.is_dir() or not marker.is_file():
        raise ContainmentError(
            "prepared root needs a regular prepared.json and library directory"
        )
    if marker.stat().st_size > 4096:
        raise ContainmentError("prepared.json exceeds the preparation-record limit")
    try:
        record = json.loads(
            marker.read_text(encoding="utf-8"), object_pairs_hook=unique_fields
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContainmentError(
            "prepared.json is not a valid preparation record"
        ) from exc
    if (
        not isinstance(record, dict)
        or type(record.get("version")) is not int
        or record != preparation_record(root)
    ):
        raise ContainmentError(
            "prepared.json does not match this trial root and version"
        )
    # No credentials are inspected; only this marker's explicit library path.
    if Path(record["library"]).resolve(strict=True) != library:
        raise ContainmentError("prepared.json library escapes the trial root")

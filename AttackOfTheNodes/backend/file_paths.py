"""Normalize configured local paths without opening files or picking paths."""

import os
import platform
import re
import subprocess
from pathlib import Path


def normalize_local_path(value: str) -> Path:
    """Accept copied quotes and translate absolute Windows paths under WSL."""
    path = value.strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in {'"', "'"}:
        path = path[1:-1]
    if not path or not path.strip():
        raise ValueError("Enter a file path in Parameters.")
    if "\x00" in path:
        raise ValueError("The file path contains an invalid null character.")
    windows_path = bool(re.match(r"^[A-Za-z]:", path)) or path.startswith("\\\\")
    if windows_path and platform.system() != "Windows":
        if not (os.environ.get("WSL_DISTRO_NAME") or
                "microsoft" in platform.release().lower()):
            raise ValueError("This Windows path is not accessible on this system. "
                             "Use a local path or run the workflow on Windows/WSL.")
        if re.match(r"^[A-Za-z]:($|[^\\/])", path):
            raise ValueError("Use a full Windows path, such as C:\\Users\\name\\file.txt.")
        try:
            result = subprocess.run(
                ["wslpath", "-u", path], capture_output=True, text=True,
                timeout=5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("Could not convert the Windows path under WSL. "
                             "Enter its /mnt/c/... equivalent instead.") from exc
        if result.returncode != 0 or not result.stdout.strip():
            raise ValueError("Could not convert the Windows path under WSL. "
                             "Check the path or enter its Linux equivalent.")
        path = result.stdout.strip()
    return Path(path).expanduser()

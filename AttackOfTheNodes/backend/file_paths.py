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
    # Drive-relative paths depend on per-drive working directories and cannot
    # be resolved portably. Detect syntax before deciding which OS handles it.
    if re.match(r"^[A-Za-z]:($|[^\\/])", path):
        raise ValueError("Use a full Windows path, such as C:\\Users\\name\\file.txt.")
    windows_path = bool(re.match(r"^[A-Za-z]:[\\/]", path)) or path.startswith("\\\\")
    if windows_path and platform.system() != "Windows":
        if path.startswith("\\\\?\\UNC\\"):
            path = "\\\\" + path[8:]
        elif path.startswith("\\\\?\\"):
            path = path[4:]
        # WSL UNC shares name a distro; only the running distro maps locally.
        share = re.match(r"^\\\\(?:wsl\.localhost|wsl\$)\\([^\\]+)(.*)$", path, re.IGNORECASE)
        if share:
            distro = os.environ.get("WSL_DISTRO_NAME", "")
            if not distro or share.group(1).casefold() != distro.casefold():
                raise ValueError("The WSL share belongs to another or unknown distro; use a path accessible in this distro.")
            path = share.group(2).replace("\\", "/") or "/"
            return Path(path)

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
        converted = result.stdout.rstrip("\r\n")
        if not converted.startswith("/") or "\n" in converted or "\r" in converted or "\x00" in converted:
            raise ValueError("Windows path conversion did not return an absolute local Linux path.")
        path = converted
    return Path(path).expanduser()

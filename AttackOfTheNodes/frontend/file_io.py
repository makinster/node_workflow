"""Frontend-only filesystem picker and reveal helpers."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Sequence


JsonFileTypes = Sequence[tuple[str, str]]


class FilePickerUnavailable(RuntimeError):
    """Raised when no OS file picker is available in this session."""


JSON_FILE_TYPES: tuple[tuple[str, str], ...] = (
    ("JSON files", "*.json"),
    ("All files", "*.*"),
)


def pick_open_file(
    title: str,
    filetypes: JsonFileTypes = JSON_FILE_TYPES,
) -> str | None:
    """Return a selected file path, None for cancel, or raise if unavailable."""
    if _is_wsl():
        return _pick_with_windows_dialog("open", title, "", filetypes)
    return _pick_with_tkinter("open", title, "", filetypes)


def pick_save_file(
    title: str,
    default_name: str = "",
    filetypes: JsonFileTypes = JSON_FILE_TYPES,
) -> str | None:
    """Return a selected save path, None for cancel, or raise if unavailable."""
    if _is_wsl():
        return _pick_with_windows_dialog("save", title, default_name, filetypes)
    return _pick_with_tkinter("save", title, default_name, filetypes)


def reveal_path(path: str | Path, select: bool = False) -> bool:
    """Open a path in the host file manager without blocking Textual."""
    target = Path(path)
    try:
        command = _reveal_command(target, select)
    except FilePickerUnavailable:
        return False
    try:
        subprocess.Popen(command)
    except OSError:
        return False
    return True


def _pick_with_tkinter(
    mode: str,
    title: str,
    default_name: str,
    filetypes: JsonFileTypes,
) -> str | None:
    if platform.system() == "Linux" and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        raise FilePickerUnavailable("No GUI display is available")
    try:
        from tkinter import Tk, filedialog
    except Exception as exc:  # pragma: no cover - depends on Python build
        raise FilePickerUnavailable(str(exc)) from exc

    root = None
    try:
        root = Tk()
        root.withdraw()
        if mode == "open":
            path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        else:
            path = filedialog.asksaveasfilename(
                title=title,
                initialfile=default_name,
                filetypes=filetypes,
                defaultextension=".json",
            )
        root.destroy()
    except Exception as exc:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
        raise FilePickerUnavailable(str(exc)) from exc
    return str(path) if path else None


def _pick_with_windows_dialog(
    mode: str,
    title: str,
    default_name: str,
    filetypes: JsonFileTypes,
) -> str | None:
    if shutil.which("powershell.exe") is None:
        raise FilePickerUnavailable("powershell.exe is not available")
    dialog = "OpenFileDialog" if mode == "open" else "SaveFileDialog"
    filter_text = _windows_filter(filetypes)
    escaped_title = _ps_quote(title)
    escaped_filter = _ps_quote(filter_text)
    escaped_name = _ps_quote(default_name)
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        f"$dialog = New-Object System.Windows.Forms.{dialog};"
        f"$dialog.Title = {escaped_title};"
        f"$dialog.Filter = {escaped_filter};"
        f"$dialog.FileName = {escaped_name};"
        "$result = $dialog.ShowDialog();"
        "if ($result -eq [System.Windows.Forms.DialogResult]::OK) "
        "{ [Console]::Out.Write($dialog.FileName) }"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FilePickerUnavailable(str(exc)) from exc
    if completed.returncode != 0:
        raise FilePickerUnavailable(completed.stderr.strip() or "Windows dialog failed")
    windows_path = completed.stdout.strip()
    if not windows_path:
        return None
    return _wsl_to_posix_path(windows_path)


def _reveal_command(path: Path, select: bool) -> list[str]:
    system = platform.system()
    if _is_wsl():
        windows_path = _posix_to_windows_path(path)
        if select:
            return ["explorer.exe", f"/select,{windows_path}"]
        return ["explorer.exe", windows_path]
    if system == "Windows":
        if select:
            return ["explorer", f"/select,{str(path)}"]
        return ["explorer", str(path)]
    if system == "Darwin":
        if select:
            return ["open", "-R", str(path)]
        return ["open", str(path)]
    if system == "Linux":
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            raise FilePickerUnavailable("No GUI display is available")
        opener = shutil.which("xdg-open")
        if opener is None:
            raise FilePickerUnavailable("xdg-open is not available")
        return [opener, str(path.parent if select else path)]
    raise FilePickerUnavailable(f"Unsupported platform: {system}")


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _windows_filter(filetypes: Iterable[tuple[str, str]]) -> str:
    parts: list[str] = []
    for label, pattern in filetypes:
        parts.extend([label, pattern])
    return "|".join(parts)


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _posix_to_windows_path(path: Path) -> str:
    try:
        completed = subprocess.run(
            ["wslpath", "-w", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FilePickerUnavailable(str(exc)) from exc
    if completed.returncode != 0:
        raise FilePickerUnavailable(completed.stderr.strip() or "wslpath failed")
    return completed.stdout.strip()


def _wsl_to_posix_path(path: str) -> str:
    try:
        completed = subprocess.run(
            ["wslpath", "-u", path],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FilePickerUnavailable(str(exc)) from exc
    if completed.returncode != 0:
        raise FilePickerUnavailable(completed.stderr.strip() or "wslpath failed")
    return completed.stdout.strip()

"""Shared modal helpers."""

import tkinter as tk


def center_window(window, parent) -> None:
    """Center a Toplevel over its parent."""
    window.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - window.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - window.winfo_height()) // 2
    window.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def safe_grab(window) -> None:
    """
    Grab focus for a modal after it is viewable.

    Some WSL/X11 Tk builds raise "grab failed: window not viewable" if grab_set
    runs immediately after Toplevel construction. Waiting for visibility fixes
    that path, and falling back keeps the modal usable even if the window
    manager does not support grabs cleanly.
    """
    try:
        window.update_idletasks()
        window.wait_visibility(window)
        window.grab_set()
    except tk.TclError:
        window.after(50, lambda: _try_grab(window))


def _try_grab(window) -> None:
    try:
        if window.winfo_exists() and window.winfo_viewable():
            window.grab_set()
    except tk.TclError:
        pass

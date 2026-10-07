"""Run-scoped window-manager access shared by the file/window io nodes.

The adapter itself (backend/window_manager.py) stays free of run-state
coupling (D11); this is the one place node land maps a run to its manager.
Tests inject a FakeWindowManager under WINDOW_MANAGER_RESOURCE before
executing; production lazily caches the platform manager per run.
"""

from typing import TYPE_CHECKING

from ...window_manager import WindowManager, get_window_manager


if TYPE_CHECKING:
    from ...node_base import NodeContext


WINDOW_MANAGER_RESOURCE = "window_manager"


def run_window_manager(context: "NodeContext") -> WindowManager:
    """The run's window manager: injected/cached in RunSession, else platform."""
    if context.run_session is not None:
        cached = context.run_session.get_resource(WINDOW_MANAGER_RESOURCE)
        if cached is not None:
            return cached
    manager = get_window_manager()
    if context.run_session is not None:
        context.run_session.register_resource(WINDOW_MANAGER_RESOURCE, manager)
    return manager
